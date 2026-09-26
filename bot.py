"""Ponto de entrada do bot. Toda a lógica fica nos módulos importados abaixo."""

import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Cada entrada corresponde a um arquivo em cogs/, sem a extensão .py
EXTENSIONS = [
    "cogs.voice_tracker",
    "cogs.tempo",
    "cogs.rank",
    "cogs.recrutar",
]


async def main():
    async with bot:
        for extension in EXTENSIONS:
            await bot.load_extension(extension)
        await bot.start(os.getenv("TOKEN"))




if __name__ == "__main__":
    asyncio.run(main())
