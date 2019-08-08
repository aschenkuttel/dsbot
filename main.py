from data.naruto import pm_commands
from discord.ext import commands
from utils import WorldMissing, DSContext
from load import load
import discord
import asyncio
import os


def prefix(_, message):
    if message.guild is None:
        return load.secrets["PRE"]
    custom = load.pre_fix(message.guild.id)
    return custom


class DSBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.path = os.path.dirname(__file__)
        self.white = pm_commands
        self.owner_id = 211836670666997762
        self.add_check(self.global_world)
        self.remove_command("help")
        self.session = None
        self.load = load
        self.setup_cogs()

    # ----- Connected -----#
    async def on_ready(self):

        # Login Setup
        session = await self.load.setup(self.loop)
        self.session = session

        # Conquer Task
        self.loop.create_task(self.conquer_loop())

        # Playing Status
        activity = discord.Activity(type=1, name="!help [1.5]")
        await self.change_presence(activity=activity)
        print("Erfolgreich Verbunden!")

    # -------- Global Checks --------#
    async def global_world(self, ctx):
        if "help" in str(ctx.command):
            return True
        cmd = str(ctx.command).lower()
        if ctx.guild is None:
            if cmd in self.white:
                return True
            raise commands.NoPrivateMessage
        if cmd == "set world":
            return True
        ctx.world = load.get_world(ctx.channel)
        if ctx.world:
            return True
        raise WorldMissing

    # Custom Context Implementation
    async def on_message(self, message):
        ctx = await self.get_context(message, cls=DSContext)
        await self.invoke(ctx)

    # ----- Update every Hour -----#
    async def conquer_loop(self):
        seconds = self.load.get_seconds()
        await asyncio.sleep(seconds)
        while not self.is_closed():

            await load.re
            await self.load.conquer_feed(bot.guilds)
            wait_pls = self.load.get_seconds()
            await asyncio.sleep(wait_pls)

    def setup_cogs(self):
        enl = []
        for extension in self.load.secrets["CMDS"]:
            try:
                self.load_extension(extension)
            except ModuleNotFoundError:
                enl.append(extension[5:])
        if enl:
            print(f"Nicht geladen: {enl}")
        else:
            print("Commands vollständig geladen.")


bot = DSBot(command_prefix=prefix, case_insensitive=True)
bot.run(load.secrets["TOKEN"])
