"""Cog do comando !rank."""

import time

import discord
from discord.ext import commands

from storage import user_total_time, user_voice_times
from utils import format_duration


class Rank(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="rank")
    async def show_rank(self, ctx: commands.Context):
        """Mostra o Top 3 em tempo de voz, e a posição do autor caso não esteja no Top 3."""
        guild = ctx.guild

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


async def setup(bot: commands.Bot):
    await bot.add_cog(Rank(bot))
