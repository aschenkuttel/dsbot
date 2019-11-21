from data.naruto import pm_commands, default_cogs
from utils import WorldMissing, DSContext
from discord.ext import commands
from load import load
import discord
import asyncio
import os


# gets called every message to gather the custom prefix
def prefix(_, message):
    if message.guild is None:
        return load.secrets["PRE"]
    custom = load.get_prefix(message.guild.id)
    return custom


# implementation of own class / overwrites
class DSBot(commands.Bot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.load = load
        self.white = pm_commands
        self.owner_id = 211836670666997762
        self.path = os.path.dirname(__file__)
        self.activity = discord.Activity(type=1, name="!help [1.6]")
        self.loop.create_task(self.conquer_loop())
        self.add_check(self.global_world)
        self.remove_command("help")
        self.session = None
        self._lock = True
        self.conn = None
        self.setup_cogs()

    # setup functions
    async def on_ready(self):

        # db / aiohttp setup
        if not self.session:
            session = await self.load.setup(self.loop)
            self.session = session

        if not self.conn:
            self.conn = await load.pool.acquire()
            await self.conn.add_listener("log", self.callback)

        self._lock = False
        print("Erfolgreich Verbunden!")

    # global check and ctx.world implementation
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

    # custom context implementation
    async def on_message(self, message):
        if self._lock:
            return
        ctx = await self.get_context(message, cls=DSContext)
        await self.invoke(ctx)

    def callback(self, conn, pid, channel, payload):
        print(conn)
        print(pid)
        print(channel)
        print(payload)
        owner = self.get_user(self.owner_id)

    # main conquer feed loop every new hour / world cache refresh
    async def conquer_loop(self):
        seconds = self.load.get_seconds()
        await asyncio.sleep(seconds)
        while not self.is_closed():
            await load.refresh_worlds()
            await self.load.conquer_feed(self.guilds)
            wait_pls = self.load.get_seconds()
            await asyncio.sleep(wait_pls)

    # imports all cogs at startup
    def setup_cogs(self):
        for file in default_cogs:
            try:
                self.load_extension(f"cogs.{file}")
            except commands.ExtensionNotFound:
                print(f"module {file} not found")

    async def logout(self):
        await self.session.close()
        await load.close_db()
        await self.close()


# instance creation and bot start
dsbot = DSBot(command_prefix=prefix, case_insensitive=True)
dsbot.run(load.secrets["TOKEN"])
