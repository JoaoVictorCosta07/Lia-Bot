"""Cog do comando !recrutar."""

import discord
from discord.ext import commands

from config import RECRUTA_ROLE_ID


class Recrutar(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="recrutar")
    @commands.has_permissions(administrator=True)
    async def recrutar_todos(self, ctx: commands.Context):
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
    async def recrutar_todos_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 Você não tem permissão para usar esse comando (requer Administrador).")
        else:
            print(f"[ERRO] Comando !recrutar: {error}")
            await ctx.send("❌ Ocorreu um erro ao executar o comando. Veja o console para detalhes.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Recrutar(bot))
