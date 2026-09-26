import os
import json
import time
import discord
from datetime import datetime, timedelta
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Timestamp de início da sessão atual de cada usuário em call
user_voice_times = {}

RECRUTA_ROLE_ID = 1552057504601608313  # <-- troque pelo ID do cargo "Recruta"

IGNORED_VOICE_CHANNELS = {
    1552060896770134106,  # <-- troque pelo ID do canal AFK
    # pode adicionar mais IDs aqui, separados por vírgula
}

ANNOUNCE_CHANNEL_ID = 1552060059813421187

'''
🪖 Recruta — 0h
🎖️ Soldado — 3h
🎖️ Cabo — 10h
🎖️ 3º Sargento — 20h
🎖️ 2º Sargento — 35h
🎖️ 1º Sargento — 50h
🏅 Subtenente — 75h
⭐ Aspirante — 100h
⭐ Tenente — 150h
🦅 Capitão — 200h
🦅 Major — 300h
🏆 Coronel — 450h
🏆 Veterano Expedicionário — 600h
'''

ROLE_REWARDS = {

    10800: 1552058050796458045, # soldado 1552058050796458045
    36000: 1552058132321271909, # cabo
    72000: 1552058207155789905, # 3º sargento
    126000: 1552058275644710922, # 2º sargento
    180000: 1552058333920235552, # 1º sargento
    270000: 1552058311090896916, # subtenente
    360000: 1552058326173487135, # aspirante
    540000: 1552058340270407730, # tenente
    720000: 1552058632982630424, # capitão
    1080000: 1552058625986527252, # major
    1620000: 1552058803300732948, # coronel
    2160000: 1552058795335884912, # veterano expedicionário
}

# Versão para exibição no !tempo, incluindo o Recruta como patamar inicial (0h)
ALL_RANKS_DISPLAY = {0: RECRUTA_ROLE_ID, **ROLE_REWARDS}



DATA_FILE = "voice_times.json"
DAILY_DATA_FILE = "voice_daily.json"

# Tempo total acumulado (all-time) em segundos: {member_id: total_seconds}
user_total_time = {}

# Tempo por dia, pra calcular "últimos 7 dias": {member_id: {"YYYY-MM-DD": seconds}}
user_daily_time = {}


# ---------- Persistência ----------

def load_data():
    global user_total_time
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
                user_total_time = {int(k): v for k, v in raw.items()}
            print(f"Dados totais carregados: {len(user_total_time)} usuário(s).")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Erro ao carregar {DATA_FILE}: {e}. Iniciando com dados vazios.")
            user_total_time = {}
    else:
        print("Nenhum arquivo de dados totais encontrado. Iniciando do zero.")


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in user_total_time.items()}, f, indent=4)
    except Exception as e:
        print(f"Erro ao salvar {DATA_FILE}: {e}")


def load_daily_data():
    global user_daily_time
    if os.path.exists(DAILY_DATA_FILE):
        try:
            with open(DAILY_DATA_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
                user_daily_time = {int(k): v for k, v in raw.items()}
            print(f"Dados diários carregados: {len(user_daily_time)} usuário(s).")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Erro ao carregar {DAILY_DATA_FILE}: {e}. Iniciando com dados vazios.")
            user_daily_time = {}
    else:
        print("Nenhum arquivo de dados diários encontrado. Iniciando do zero.")


def save_daily_data():
    try:
        with open(DAILY_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in user_daily_time.items()}, f, indent=4)
    except Exception as e:
        print(f"Erro ao salvar {DAILY_DATA_FILE}: {e}")


# ---------- Lógica de tempo ----------

def add_time(member_id, duration):
    """Soma 'duration' segundos ao total e ao dia de hoje do usuário."""
    if duration <= 0:
        return

    user_total_time[member_id] = user_total_time.get(member_id, 0) + duration

    today_str = datetime.now().strftime("%Y-%m-%d")
    if member_id not in user_daily_time:
        user_daily_time[member_id] = {}
    user_daily_time[member_id][today_str] = user_daily_time[member_id].get(today_str, 0) + duration


def get_last_7_days_total(member_id):
    """Soma o tempo dos últimos 7 dias (incluindo hoje) a partir do histórico diário."""
    if member_id not in user_daily_time:
        return 0

    cutoff = datetime.now().date() - timedelta(days=6)
    total = 0
    for date_str, secs in user_daily_time[member_id].items():
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            if d >= cutoff:
                total += secs
        except ValueError:
            continue
    return total


def format_duration(total_secs):
    hours, remainder = divmod(int(total_secs), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"


def make_progress_bar(pct, length=12):
    pct = max(0, min(100, pct))
    filled = int(length * pct / 100)
    return "█" * filled + "░" * (length - filled)


def get_rank_info(total_seconds):
    """Retorna (cargo_atual, proximo_cargo) como tuplas (required_time, role_id) ou None."""
    sorted_rewards = sorted(ALL_RANKS_DISPLAY.items())  # <-- mudou aqui
    current = None
    next_ = None
    for required, role_id in sorted_rewards:
        if total_seconds >= required:
            current = (required, role_id)
        else:
            next_ = (required, role_id)
            break
    return current, next_


# ---------- Eventos ----------

@bot.event
async def on_ready():
    load_data()
    load_daily_data()

    # Popula sessões de quem já está em call no momento em que o bot conecta/reconecta
    now = time.time()
    for guild in bot.guilds:
        for vc in guild.voice_channels:
            if vc.id in IGNORED_VOICE_CHANNELS:
                continue  # pula o canal AFK (e outros ignorados)
            for member in vc.members:
                if not member.bot and member.id not in user_voice_times:
                    user_voice_times[member.id] = now
                    print(f"[INFO] {member.display_name} já estava em call, sessão iniciada agora.")

    if not check_voice_sessions.is_running():
        check_voice_sessions.start()
    print(f"Bot {bot.user.name} conectado e pronto para servir o esquadrão!")


def is_trackable_channel(channel):
    """Retorna True se o canal deve contar tempo (ou seja, não é None e não está na lista de ignorados)."""
    return channel is not None and channel.id not in IGNORED_VOICE_CHANNELS


@bot.event
async def on_voice_state_update(member, before, after):
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

            await check_and_assign_roles(member, user_total_time[member.id])

    # Se estava e continua numa call que conta (ex: trocou de canal normal pra outro canal normal),
    # não faz nada — a sessão continua contando normalmente sem interrupção.

@tasks.loop(seconds=5)  # Suba pra 60+ em produção, com limiares em horas
async def check_voice_sessions():
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
        for guild in bot.guilds:
            member = guild.get_member(member_id)
            if member:
                break

        if member:
            await check_and_assign_roles(member, total)

    if user_voice_times:
        save_data()
        save_daily_data()


@check_voice_sessions.before_loop
async def before_check_voice_sessions():
    await bot.wait_until_ready()


async def check_and_assign_roles(member, total_seconds):
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
            await announce_role(member, earned_role)

    except discord.Forbidden as e:
        print(f"[ERRO Forbidden] {e}")
    except discord.HTTPException as e:
        print(f"[ERRO HTTP] {e}")


async def announce_role(member, role):
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


# ---------- Comando !tempo ----------

@bot.command(name="tempo")
async def check_time(ctx, member: discord.Member = None):
    target = member or ctx.author

    total_secs = user_total_time.get(target.id, 0)
    last_7_days = get_last_7_days_total(target.id)

    # Se estiver em call agora, soma a sessão em andamento nos dois totais (exibição, sem salvar ainda)
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
    
@bot.command(name="rank")
async def show_rank(ctx):
    """Mostra o Top 3 em tempo de voz, e a posição do autor caso não esteja no Top 3."""
    guild = ctx.guild

    # Monta a lista de (member_id, total_secs) considerando sessões em andamento
    now = time.time()
    all_ids = set(user_total_time.keys()) | set(user_voice_times.keys())

    ranking = []
    for member_id in all_ids:
        total_secs = user_total_time.get(member_id, 0)
        if member_id in user_voice_times:
            total_secs += int(now - user_voice_times[member_id])
        if total_secs > 0:
            ranking.append((member_id, total_secs))

    if not ranking:
        await ctx.send("📊 Ainda não há ninguém no ranking.")
        return

    # Ordena do maior pro menor tempo
    ranking.sort(key=lambda x: x[1], reverse=True)

    medals = ["🥇", "🥈", "🥉"]
    embed = discord.Embed(
        title="📊 Ranking — Tempo em Chamadas de Voz",
        color=discord.Color.gold(),
    )

    top3 = ranking[:3]
    description_lines = []
    author_in_top3 = False

    for i, (member_id, total_secs) in enumerate(top3):
        member = guild.get_member(member_id)
        name = member.display_name if member else f"Usuário desconhecido ({member_id})"

        if member_id == ctx.author.id:
            author_in_top3 = True

        description_lines.append(f"{medals[i]} **{name}** — {format_duration(total_secs)}")

    embed.description = "\n".join(description_lines)

    # Se o autor não estiver no Top 3, mostra a posição dele separadamente
    if not author_in_top3:
        author_position = None
        author_total = None
        for i, (member_id, total_secs) in enumerate(ranking):
            if member_id == ctx.author.id:
                author_position = i + 1
                author_total = total_secs
                break

        if author_position:
            embed.add_field(
                name="Sua posição",
                value=f"**#{author_position}** — {ctx.author.display_name} — {format_duration(author_total)}",
                inline=False,
            )
        else:
            embed.add_field(
                name="Sua posição",
                value="Você ainda não tem tempo registrado em call.",
                inline=False,
            )

    await ctx.send(embed=embed)

@bot.command(name="recrutar")
@commands.has_permissions(administrator=True)
async def recrutar_todos(ctx):
    """Atribui o cargo Recruta a todos os membros do servidor que ainda não o possuem."""
    guild = ctx.guild
    role = guild.get_role(RECRUTA_ROLE_ID)

    if role is None:
        await ctx.send(f"❌ Cargo com ID `{RECRUTA_ROLE_ID}` não foi encontrado neste servidor.")
        return

    if role >= guild.me.top_role:
        await ctx.send(
            f"❌ Não consigo atribuir o cargo **{role.name}** porque ele está no mesmo nível "
            f"ou acima do meu cargo mais alto. Ajuste a hierarquia de cargos primeiro."
        )
        return

    status_msg = await ctx.send(f"⏳ Atribuindo cargo **{role.name}** a todos os membros...")

    added = 0
    already_had = 0
    skipped_bots = 0
    failed = 0

    for member in guild.members:
        if member.bot:
            skipped_bots += 1
            continue

        if role in member.roles:
            already_had += 1
            continue

        try:
            await member.add_roles(role, reason=f"Recrutamento em massa por {ctx.author}")
            added += 1
        except discord.Forbidden:
            failed += 1
        except discord.HTTPException:
            failed += 1

    await status_msg.edit(
        content=(
            f"✅ **Recrutamento concluído!**\n"
            f"• Cargo atribuído a **{added}** membro(s)\n"
            f"• Já possuíam o cargo: **{already_had}**\n"
            f"• Bots ignorados: **{skipped_bots}**\n"
            f"• Falhas: **{failed}**"
        )
    )


@recrutar_todos.error
async def recrutar_todos_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 Você não tem permissão para usar esse comando (requer Administrador).")
    else:
        print(f"[ERRO] Comando !recrutar: {error}")
        await ctx.send("❌ Ocorreu um erro ao executar o comando. Veja o console para detalhes.")


if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"))