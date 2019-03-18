from discord.ext import commands
from utils import WorldMissing
from load import load
import discord
import asyncio


async def prefix(_, message):
    if message.guild is None:
        return load.secrets["PRE"]
    custom = load.pre_fix(message.guild.id)
    return custom


class DSBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loop.create_task(self.conquer_loop())
        self.white = ["help", "play", "time"]
        self.owner_id = 211836670666997762
        self.add_check(self.global_world)
        self.remove_command("help")
        self.session = None
        self.load = load
        self.setup_cogs()

    # ----- Connected -----#
    async def on_ready(self):

        # ----- Log In Check -----#
        session = await self.load.setup(self.loop)
        self.session = session

        # ----- Playing Status -----#
        await self.change_presence(activity=discord.Activity(type=1, name="!help [1.5]"))
        print("Erfolgreich Verbunden!")

    # -------- Global Checks --------#
    async def global_world(self, ctx):
        cmd = ctx.invoked_with.lower()
        if ctx.guild is None:
            if cmd in self.white:
                return True
            if str(ctx.command).startswith("help"):
                return True
            raise commands.NoPrivateMessage
        if cmd in ["world", "help"]:
            return True
        if self.load.get_guild_world(ctx.guild):
            return True
        else:
            raise WorldMissing

    # ----- Update every Hour -----#
    async def conquer_loop(self):
        await self.wait_until_ready()
        till = self.load.get_seconds()
        await asyncio.sleep(till)
        while not self.is_closed():
            # --- Conquer Feed --- #
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
