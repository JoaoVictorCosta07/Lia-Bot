"""Cog responsável por rastrear tempo em call e atribuir cargos automaticamente."""

import time

import discord
from discord.ext import commands, tasks

from config import (
    ANNOUNCE_CHANNEL_ID,
    CHECK_INTERVAL_SECONDS,
    IGNORED_VOICE_CHANNELS,
    RECRUTA_ROLE_ID,
    ROLE_REWARDS,
)
from storage import (
    add_time,
    load_daily_data,
    load_data,
    save_daily_data,
    save_data,
    user_total_time,
    user_voice_times,
)


def is_trackable_channel(channel):
    """Retorna True se o canal deve contar tempo (não é None e não está na lista de ignorados)."""
    return channel is not None and channel.id not in IGNORED_VOICE_CHANNELS


class VoiceTracker(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        if not self.check_voice_sessions.is_running():
            self.check_voice_sessions.start()

    def cog_unload(self):
        self.check_voice_sessions.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        load_data()
        load_daily_data()

        # DEBUG: lista todos os servidores e cargos visíveis pelo bot
        print("=== DEBUG: Servidores e cargos ===")
        for guild in self.bot.guilds:
            print(f"--- Servidor: {guild.name} (ID: {guild.id}) ---")
            for role in guild.roles:
                print(f"  {role.id} -> {role.name}")
        print("=== FIM DEBUG ===")

        # Popula sessões de quem já está em call no momento em que o bot conecta/reconecta
        now = time.time()
        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                if vc.id in IGNORED_VOICE_CHANNELS:
                    continue
                for member in vc.members:
                    if not member.bot and member.id not in user_voice_times:
                        user_voice_times[member.id] = now
                        print(f"[INFO] {member.display_name} já estava em call, sessão iniciada agora.")

        print(f"Bot {self.bot.user.name} conectado e pronto para servir o esquadrão!")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        was_tracking = is_trackable_channel(before.channel)
        will_track = is_trackable_channel(after.channel)

        # Estava fora (ou em canal ignorado) e entrou num canal que conta
        if not was_tracking and will_track:
            user_voice_times[member.id] = time.time()

        # Estava numa call que conta e agora saiu dela (foi pra fora ou pra um canal ignorado)
        elif was_tracking and not will_track:
            if member.id in user_voice_times:
                start_time = user_voice_times.pop(member.id)
                duration = int(time.time() - start_time)

                add_time(member.id, duration)
                save_data()
                save_daily_data()

                await check_and_assign_roles(self.bot, member, user_total_time[member.id])

        # Se estava e continua numa call que conta (trocou de canal normal pra outro normal),
        # não faz nada — a sessão continua contando sem interrupção.

    @tasks.loop(seconds=CHECK_INTERVAL_SECONDS)
    async def check_voice_sessions(self):
        """Verifica periodicamente quem está em call, soma o tempo e checa cargos."""
        now = time.time()

        for member_id, start_time in list(user_voice_times.items()):
            elapsed = int(now - start_time)
            if elapsed <= 0:
                continue

            add_time(member_id, elapsed)
            user_voice_times[member_id] = now

            total = user_total_time[member_id]

            member = None
            for guild in self.bot.guilds:
                member = guild.get_member(member_id)
                if member:
                    break

            if member:
                await check_and_assign_roles(self.bot, member, total)

        if user_voice_times:
            save_data()
            save_daily_data()

    @check_voice_sessions.before_loop
    async def before_check_voice_sessions(self):
        await self.bot.wait_until_ready()


async def check_and_assign_roles(bot: commands.Bot, member: discord.Member, total_seconds: int):
    guild = member.guild

    earned_role_id = None
    earned_time = -1
    for required_time, role_id in ROLE_REWARDS.items():
        if total_seconds >= required_time and required_time > earned_time:
            earned_time = required_time
            earned_role_id = role_id

    if earned_role_id is None:
        return  # Ainda não atingiu nenhum patamar (continua só com Recruta)

    earned_role = guild.get_role(earned_role_id)
    if earned_role is None:
        print(f"[ERRO] Cargo com ID {earned_role_id} não encontrado no servidor.")
        return

    all_reward_role_ids = set(ROLE_REWARDS.values()) | {RECRUTA_ROLE_ID}
    roles_to_remove = [
        r for r in member.roles
        if r.id in all_reward_role_ids and r.id != earned_role_id
    ]

    try:
        is_new = earned_role not in member.roles

        if is_new:
            await member.add_roles(earned_role)
            print(f"Cargo '{earned_role.name}' atribuído a {member.display_name} ({total_seconds}s em voz).")

        if roles_to_remove:
            await member.remove_roles(*roles_to_remove)
            print(f"Removidos de {member.display_name}: {[r.name for r in roles_to_remove]}")

        if is_new:
            await announce_role(bot, member, earned_role)

    except discord.Forbidden as e:
        print(f"[ERRO Forbidden] {e}")
    except discord.HTTPException as e:
        print(f"[ERRO HTTP] {e}")
        
async def announce_role(bot: commands.Bot, member: discord.Member, role: discord.Role):
    """Envia uma mensagem marcando o membro no canal de anúncios ao conquistar um novo cargo."""
    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if channel is None:
        print(f"[ERRO] Canal de anúncios (ID {ANNOUNCE_CHANNEL_ID}) não encontrado.")
        return

    try:
        await channel.send(f"🎉 {member.mention} conquistou o cargo {role.mention} por tempo em call! 🎙️")
    except discord.Forbidden as e:
        print(f"[ERRO Forbidden] Não foi possível enviar mensagem no canal de anúncios: {e}")
    except discord.HTTPException as e:
        print(f"[ERRO HTTP] Não foi possível enviar mensagem no canal de anúncios: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceTracker(bot))
