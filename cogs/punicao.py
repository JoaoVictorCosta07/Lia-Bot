import discord
from discord.ext import commands
import json
import os
from typing import Dict, List, Tuple
from config import PUNISHMENT_CHANNEL_ID

ARQUIVO_PUNICOES = "punicoes.json"

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
# Mesmos cargos de liderança usados no !criar_evento (Squad Leader, General, Fundador)
CARGOS_PERMITIDOS_IDS = [
    1548838264176115823,
    1548838382678048849,
    1548838122064973824
]
# ==============================================================================


def carregar_punicoes() -> Dict[str, int]:
    if not os.path.exists(ARQUIVO_PUNICOES):
        return {}
    try:
        with open(ARQUIVO_PUNICOES, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def salvar_punicoes(dados: Dict[str, int]):
    with open(ARQUIVO_PUNICOES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)


def obter_estagio(faltas: int) -> Tuple[str, str, str]:
    """Retorna (emoji, nome_do_estagio, descricao) de acordo com a quantidade de faltas."""
    if faltas <= 1:
        return ("🟡", "Aviso", "Cuidado com próximas infrações.")
    elif faltas == 2:
        return ("🟠", "Perda de prioridade", "Perde prioridade de vaga em próximas operações e treinos.")
    else:
        return (
            "🔴",
            "Impedimento de participação",
            "contate a liderança para saber como regularizar sua situação."
        )


class MotivoPunicaoModal(discord.ui.Modal, title="Motivo da punição"):
    motivo = discord.ui.TextInput(
        label="Motivo",
        placeholder="Descreva o motivo da punição",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    def __init__(self, cog, membros: List[discord.Member]):
        super().__init__()
        self.cog = cog
        self.membros = membros

    async def on_submit(self, interaction: discord.Interaction):
        if not self.cog.tem_permissao(interaction.user):
            await interaction.response.send_message(
                "❌ Você não tem mais permissão para aplicar punições.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        await self.cog.aplicar_punicao(interaction, self.membros, self.motivo.value.strip())


class MotivoPunicaoView(discord.ui.View):
    def __init__(self, cog, autor_id: int, membros: List[discord.Member]):
        super().__init__(timeout=300)
        self.cog = cog
        self.autor_id = autor_id
        self.membros = membros

    @discord.ui.button(label="Informar motivo", style=discord.ButtonStyle.danger)
    async def informar_motivo(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.autor_id:
            await interaction.response.send_message(
                "❌ Apenas quem executou o comando pode informar o motivo.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(MotivoPunicaoModal(self.cog, self.membros))


class Punicao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def tem_permissao(self, membro: discord.Member) -> bool:
        return any(role.id in CARGOS_PERMITIDOS_IDS for role in membro.roles)

    @commands.command(name="punicao", aliases=["punição", "punir"])
    async def punicao(self, ctx: commands.Context, membros: commands.Greedy[discord.Member] = None):
        """Aplica uma falta a cada jogador mencionado e avisa o estágio atual de punição.

        Uso: !punicao @jogador1 @jogador2 @jogador3 ...
        """
        if not self.tem_permissao(ctx.author):
            await ctx.send("❌ Você não tem permissão para aplicar punições.")
            return

        membros = [m for m in (membros or []) if not m.bot]
        if not membros:
            await ctx.send("⚠️ Marque pelo menos um jogador: `!punicao @jogador1 @jogador2 ...`")
            return

        await ctx.send(
            "Informe o motivo para confirmar a aplicação das punições:",
            view=MotivoPunicaoView(self, ctx.author.id, membros)
        )

    async def aplicar_punicao(
        self,
        interaction: discord.Interaction,
        membros: List[discord.Member],
        motivo: str
    ):
        canal = interaction.guild.get_channel(PUNISHMENT_CHANNEL_ID)
        if canal is None:
            try:
                canal = await self.bot.fetch_channel(PUNISHMENT_CHANNEL_ID)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                canal = None

        if canal is None or not hasattr(canal, "send"):
            await interaction.followup.send(
                f"❌ Não encontrei o canal de avisos configurado (ID `{PUNISHMENT_CHANNEL_ID}`).",
                ephemeral=True
            )
            return

        dados = carregar_punicoes()
        resultados = []

        for membro in membros:
            chave = str(membro.id)
            faltas = dados.get(chave, 0) + 1
            dados[chave] = faltas
            resultados.append((membro, faltas, *obter_estagio(faltas)))

        salvar_punicoes(dados)

        linhas = []
        nao_avisados: List[str] = []

        for membro, faltas, emoji, nome_estagio, descricao in resultados:
            linhas.append(
                f"{emoji} {membro.mention} — **{faltas} falta(s)** → **{nome_estagio}**\n_{descricao}_"
            )

            # Avisa o jogador também por DM, além do aviso público no canal
            try:
                await membro.send(
                    f"{emoji} Você recebeu uma falta em **{interaction.guild.name}**.\n"
                    f"Total atual: **{faltas} falta(s)** — estágio: **{nome_estagio}**.\n"
                    f"{descricao}\n**Motivo:** {motivo}"
                )
            except discord.Forbidden:
                nao_avisados.append(membro.mention)

        embed = discord.Embed(
            title="🚨 Punição aplicada",
            description="\n\n".join(linhas) + f"\n\n**Motivo:** {motivo}",
            color=discord.Color.red()
        )
        if nao_avisados:
            embed.set_footer(text=f"Não foi possível enviar DM para: {', '.join(nao_avisados)}")

        await canal.send(embed=embed)
        await interaction.followup.send(
            f"✅ Punição(ões) aplicada(s) e aviso publicado em {canal.mention}.",
            ephemeral=True
        )

    @commands.command(name="retirar_punicao", aliases=["retirar_punição"])
    async def retirar_punicao(self, ctx: commands.Context, membros: commands.Greedy[discord.Member] = None):
        """Remove uma falta de cada jogador mencionado (nunca desce abaixo de 0).

        Uso: !retirar_punicao @jogador1 @jogador2 ...
        """
        if not self.tem_permissao(ctx.author):
            await ctx.send("❌ Você não tem permissão para retirar punições.")
            return

        membros = [m for m in (membros or []) if not m.bot]
        if not membros:
            await ctx.send("⚠️ Marque pelo menos um jogador: `!retirar_punicao @jogador1 @jogador2 ...`")
            return

        dados = carregar_punicoes()
        resultados = []

        for membro in membros:
            chave = str(membro.id)
            faltas = max(0, dados.get(chave, 0) - 1)
            if faltas == 0:
                dados.pop(chave, None)  # volta ao estado "normal", sem precisar guardar 0
            else:
                dados[chave] = faltas
            resultados.append((membro, faltas, *obter_estagio(faltas)))

        salvar_punicoes(dados)

        linhas = [
            f"{emoji} {membro.mention} — **{faltas} falta(s)** → **{nome_estagio}**"
            for membro, faltas, emoji, nome_estagio, _ in resultados
        ]

        embed = discord.Embed(
            title="✅ Punição reduzida",
            description="\n".join(linhas),
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name="punicoes", aliases=["punições", "ver_punicao"])
    async def ver_punicoes(self, ctx: commands.Context, membro: discord.Member = None):
        """Mostra o estágio de punição atual de um jogador (ou de quem usar o comando)."""    
        alvo = membro or ctx.author

        if alvo != ctx.author:
            if not any(role.id in CARGOS_PERMITIDOS_IDS for role in ctx.author.roles):
                await ctx.send("❌ Você não tem permissão para ver as punições de outros jogadores.")
                return

        dados = carregar_punicoes()
        faltas = dados.get(str(alvo.id), 0)
        emoji, nome_estagio, descricao = obter_estagio(faltas)

        embed = discord.Embed(
            title=f"{emoji} Estágio de punição — {alvo.display_name}",
            description=f"**{faltas} falta(s)** → **{nome_estagio}**\n_{descricao}_",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=alvo.display_avatar.url)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Punicao(bot))