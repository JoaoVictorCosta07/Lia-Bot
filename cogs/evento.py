import discord
from discord.ext import commands
import json
import os
from typing import Dict, List
from datetime import datetime

ARQUIVO_EVENTOS = "eventos.json"

# ==============================================================================
# CONFIGURAÇÕES DE IDS DO SERVIDOR
# ==============================================================================
CANAL_EVENTOS_ID = 1548852627159130253   # ID do canal onde os eventos serão postados
CARGOS_PERMITIDOS_IDS = [               # IDs dos cargos que podem criar eventos
    1548838264176115823,
    1548838382678048849,
    1548838122064973824
]
CARGO_MENCIONAR_ID = 1548862704809287750  # ID do cargo que será marcado ao publicar o evento
# ==============================================================================


def carregar_eventos() -> dict:
    if not os.path.exists(ARQUIVO_EVENTOS):
        return {}
    try:
        with open(ARQUIVO_EVENTOS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def salvar_eventos(dados: dict):
    with open(ARQUIVO_EVENTOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)


# --- View Persistente do Evento ---

class EventoView(discord.ui.View):
    def __init__(
        self,
        message_id: int,
        titulo: str,
        descricao: str,
        timestamp: int,
        vagas: Dict[str, int],
        criador_nome: str,
        criador_avatar_url: str = None,
        inscritos: Dict[str, List[int]] = None
    ):
        super().__init__(timeout=None)
        self.message_id = message_id
        self.titulo = titulo
        self.descricao = descricao
        self.timestamp = timestamp
        self.vagas = vagas
        self.criador_nome = criador_nome
        self.criador_avatar_url = criador_avatar_url
        
        self.inscritos: Dict[str, List[int]] = (
            {c: [int(uid) for uid in ulist] for c, ulist in inscritos.items()}
            if inscritos else {c: [] for c in vagas.keys()}
        )

        self.add_item(ClasseSelect(self))

    def gerar_embed(self) -> discord.Embed:
        data_formatada = f"<t:{self.timestamp}:F> (<t:{self.timestamp}:R>)" if self.timestamp > 0 else "Data não definida"

        embed = discord.Embed(
            title=f"🪖 EVENTO WARDOGS: {self.titulo}",
            description=f"{self.descricao}\n\n📅 **Data/Horário:** {data_formatada}",
            color=discord.Color.dark_gold()
        )

        # Exibe o criador discretamente no campo Author (topo do Embed)
        embed.set_author(
            name=f"Organizado por {self.criador_nome}",
            icon_url=self.criador_avatar_url
        )

        for classe, max_vagas in self.vagas.items():
            lista_ids = self.inscritos.get(classe, [])
            qtd_inscritos = len(lista_ids)
            
            if lista_ids:
                lista_membros = "\n".join([f"• <@{uid}>" for uid in lista_ids])
            else:
                lista_membros = "*Nenhum inscrito*"

            status = "🔴 (ESGOTADO)" if qtd_inscritos >= max_vagas else f"🟢 ({qtd_inscritos}/{max_vagas})"
            embed.add_field(
                name=f"{classe} {status}",
                value=lista_membros,
                inline=False
            )

        embed.set_footer(text="Selecione sua classe abaixo para se inscrever ou sair")
        return embed

    def salvar_estado(self):
        dados = carregar_eventos()
        dados[str(self.message_id)] = {
            "titulo": self.titulo,
            "descricao": self.descricao,
            "timestamp": self.timestamp,
            "vagas": self.vagas,
            "criador_nome": self.criador_nome,
            "criador_avatar_url": self.criador_avatar_url,
            "inscritos": self.inscritos
        }
        salvar_eventos(dados)


class ClasseSelect(discord.ui.Select):
    def __init__(self, parent_view: EventoView):
        self.parent_view = parent_view
        
        options = [
            discord.SelectOption(
                label=f"{classe} ({len(parent_view.inscritos.get(classe, []))}/{max_vagas})",
                value=classe,
                description=f"Inscrever-se ou sair da classe {classe}"
            )
            for classe, max_vagas in parent_view.vagas.items()
        ]
        
        super().__init__(
            custom_id=f"select_classe_evento:{parent_view.message_id}",
            placeholder="Escolha sua função/classe no evento...",
            min_values=1,
            max_values=1,
            options=options
        )

    def atualizar_opcoes(self):
        self.options = [
            discord.SelectOption(
                label=f"{classe} ({len(self.parent_view.inscritos.get(classe, []))}/{max_vagas})",
                value=classe,
                description=f"Inscrever-se ou sair da classe {classe}"
            )
            for classe, max_vagas in self.parent_view.vagas.items()
        ]

    async def callback(self, interaction: discord.Interaction):
        classe_escolhida = self.values[0]
        user_id = interaction.user.id
        
        classe_atual = None
        for classe, lista_uids in self.parent_view.inscritos.items():
            if user_id in lista_uids:
                classe_atual = classe
                break

        if classe_atual == classe_escolhida:
            self.parent_view.inscritos[classe_escolhida].remove(user_id)
            msg = f"❌ Você cancelou sua presença como **{classe_escolhida}**."
        
        elif classe_atual is not None:
            max_vagas = self.parent_view.vagas[classe_escolhida]
            if len(self.parent_view.inscritos[classe_escolhida]) >= max_vagas:
                await interaction.response.send_message(f"⚠️ As vagas para **{classe_escolhida}** estão esgotadas!", ephemeral=True)
                return

            self.parent_view.inscritos[classe_atual].remove(user_id)
            self.parent_view.inscritos[classe_escolhida].append(user_id)
            msg = f"🔄 Você trocou de **{classe_atual}** para **{classe_escolhida}**!"

        else:
            max_vagas = self.parent_view.vagas[classe_escolhida]
            if len(self.parent_view.inscritos[classe_escolhida]) >= max_vagas:
                await interaction.response.send_message(f"⚠️ As vagas para **{classe_escolhida}** estão esgotadas!", ephemeral=True)
                return

            self.parent_view.inscritos[classe_escolhida].append(user_id)
            msg = f"✅ Você se inscreveu como **{classe_escolhida}**!"

        self.parent_view.salvar_estado()
        self.atualizar_opcoes()
        
        await interaction.response.edit_message(
            embed=self.parent_view.gerar_embed(), 
            view=self.parent_view
        )
        await interaction.followup.send(msg, ephemeral=True)


# --- Pop-up (Modal) para Preenchimento do Evento ---

class EventoModal(discord.ui.Modal, title="Criar Evento Wardogs"):
    titulo_input = discord.ui.TextInput(
        label="Título do Evento",
        placeholder="Ex: Operação Tempestade no Deserto",
        required=True,
        max_length=100
    )

    descricao_input = discord.ui.TextInput(
        label="Descrição",
        style=discord.TextStyle.paragraph,
        placeholder="Descreva a missão, equipamentos permitidos, regras e orientações...",
        required=True,
        max_length=1000
    )

    data_input = discord.ui.TextInput(
        label="Data e Horário (Ano-Mês-Dia Hora:Min)",
        placeholder="Ex: 2026-10-15 20:30",
        required=True,
        max_length=20
    )

    vagas_input = discord.ui.TextInput(
        label="Vagas por Classe (Nome:Qtd, Nome:Qtd)",
        style=discord.TextStyle.paragraph,
        placeholder="Ex: Assault: 3, Médico: 2, Granadeiro: 1, Piloto: 1, Sniper: 2",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        canal_destinatario = interaction.guild.get_channel(CANAL_EVENTOS_ID)
        if not canal_destinatario:
            await interaction.response.send_message(
                f"❌ **Erro:** Canal de destino (ID `{CANAL_EVENTOS_ID}`) não encontrado!",
                ephemeral=True
            )
            return

        # Processa Data e Horário
        try:
            dt = datetime.strptime(self.data_input.value.strip(), "%Y-%m-%d %H:%M")
            timestamp = int(dt.timestamp())
        except ValueError:
            await interaction.response.send_message(
                "❌ **Formato de data inválido!**\nUse exatamente o formato: `AAAA-MM-DD HH:MM` (ex: `2026-10-15 20:30`).",
                ephemeral=True
            )
            return

        # Processa as Vagas
        vagas = {}
        try:
            itens = self.vagas_input.value.split(",")
            for item in itens:
                if ":" in item:
                    nome_classe, qtd = item.split(":")
                    vagas[nome_classe.strip()] = int(qtd.strip())
        except Exception:
            await interaction.response.send_message(
                "❌ **Formato de vagas inválido!**\nUse o formato: `Assault:3, Medico:2, Piloto:1`",
                ephemeral=True
            )
            return

        if not vagas:
            await interaction.response.send_message("❌ Adicione pelo menos uma classe de vaga válida.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        mencao_cargo = f"<@&{CARGO_MENCIONAR_ID}>" if CARGO_MENCIONAR_ID else ""

        # Posta no canal configurado junto com o ping do cargo
        msg = await canal_destinatario.send(
            content=mencao_cargo,
            embed=discord.Embed(title="Carregando evento...", color=discord.Color.dark_gold())
        )

        # Captura os dados do criador
        criador = interaction.user
        criador_nome = criador.display_name
        criador_avatar_url = criador.display_avatar.url if criador.display_avatar else None

        view = EventoView(
            message_id=msg.id,
            titulo=self.titulo_input.value,
            descricao=self.descricao_input.value,
            timestamp=timestamp,
            vagas=vagas,
            criador_nome=criador_nome,
            criador_avatar_url=criador_avatar_url
        )

        await msg.edit(content=mencao_cargo, embed=view.gerar_embed(), view=view)
        view.salvar_estado()
        interaction.client.add_view(view)

        await interaction.followup.send(f"✅ Evento criado com sucesso no canal {canal_destinatario.mention}!", ephemeral=True)


# --- Botão Inicial para Abrir o Pop-up ---

class AbrirModalView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Preencher Formulário de Evento", style=discord.ButtonStyle.primary, emoji="📝")
    async def abrir_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        membro = interaction.user
        tem_permissao = any(role.id in CARGOS_PERMITIDOS_IDS for role in membro.roles)

        if not tem_permissao:
            await interaction.response.send_message("❌ Você não tem permissão para criar eventos.", ephemeral=True)
            return

        await interaction.response.send_modal(EventoModal())


# --- Cog de Evento ---

class Evento(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        dados = carregar_eventos()
        for msg_id_str, info in dados.items():
            msg_id = int(msg_id_str)
            view = EventoView(
                message_id=msg_id,
                titulo=info["titulo"],
                descricao=info["descricao"],
                timestamp=info.get("timestamp", 0),
                vagas=info["vagas"],
                criador_nome=info.get("criador_nome", "Organizador"),
                criador_avatar_url=info.get("criador_avatar_url"),
                inscritos=info["inscritos"]
            )
            self.bot.add_view(view)

    @commands.command(name="criar_evento")
    async def criar_evento(self, ctx: commands.Context):
        """Comando acionado para abrir o pop-up de criação de eventos."""
        tem_permissao = any(role.id in CARGOS_PERMITIDOS_IDS for role in ctx.author.roles)
        if not tem_permissao:
            await ctx.send("❌ Você não tem permissão para usar este comando.", delete_after=10)
            try:
                await ctx.message.delete()
            except Exception:
                pass
            return

        try:
            await ctx.message.delete()
        except Exception:
            pass

        await ctx.send(
            f"Clique no botão abaixo para abrir o formulário de criação do evento, {ctx.author.mention}:",
            view=AbrirModalView(),
            delete_after=60
        )


async def setup(bot):
    await bot.add_cog(Evento(bot))