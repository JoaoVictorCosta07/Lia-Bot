"""Cog do comando !tempo."""

import time

import discord
from discord.ext import commands

from storage import user_total_time, user_voice_times
from utils import format_duration, get_last_7_days_total, get_rank_info, make_progress_bar


class Tempo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="tempo")
    async def check_time(self, ctx: commands.Context, member: discord.Member = None):
        """Mostra o tempo em call, progresso de patente e afins."""
        target = member or ctx.author

        total_secs = user_total_time.get(target.id, 0)
        last_7_days = get_last_7_days_total(target.id)

        # Se estiver em call agora, soma a sessão em andamento nos dois totais (só exibição)
        if target.id in user_voice_times:
            ongoing = int(time.time() - user_voice_times[target.id])
            total_secs += ongoing
            last_7_days += ongoing

        current, next_ = get_rank_info(total_secs)

        embed = discord.Embed(
            title=f"⏱️ Estatísticas de Voz — {target.display_name}",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        embed.add_field(name="Tempo total", value=format_duration(total_secs), inline=True)
        embed.add_field(name="Últimos 7 dias", value=format_duration(last_7_days), inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # espaçador pra alinhar a grid

        if current:
            role = ctx.guild.get_role(current[1])
            embed.add_field(
                name="Cargo atual",
                value=role.mention if role else "Cargo não encontrado",
                inline=False,
            )
        else:
            embed.add_field(name="Cargo atual", value="Nenhum ainda", inline=False)

        if next_:
            role = ctx.guild.get_role(next_[1])
            remaining = max(0, next_[0] - total_secs)
            progress_pct = int(min(100, (total_secs / next_[0]) * 100))
            bar = make_progress_bar(progress_pct)
            role_name = role.name if role else "cargo desconhecido"
            embed.add_field(
                name=f"Progresso até '{role_name}'",
                value=f"`{bar}` {progress_pct}%\nFaltam **{format_duration(remaining)}**",
                inline=False,
            )
        else:
            embed.add_field(name="Progresso", value="🎉 Você atingiu o rank máximo!", inline=False)

        if target.id in user_voice_times:
            embed.set_footer(text="🎙️ Atualmente em uma chamada de voz")

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tempo(bot))
