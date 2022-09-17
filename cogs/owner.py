from discord.ext import commands
from typing import Optional, Literal
import discord


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config

    @commands.command(name="servers")
    async def servers(self, ctx):
        counter = 0
        global_config = self.bot.config._config  # noqa

        for k, v in global_config.items():
            if v.get('inactive') is None:
                counter += 1

        await ctx.send(f"{counter}/{len(global_config)} active guilds")

    @commands.command(name="desync")
    async def desync_(self, ctx):
        self.bot.tree.clear_commands(guild=None)
        await self.bot.tree.sync()
        await ctx.send("DeSync Completed")

    @commands.command(name="sync")
    async def sync(self, ctx, guild: discord.Object = None, spec: Optional[Literal["~", "*", "^"]] = None):
        if spec == "~":
            synced = await ctx.bot.tree.sync(guild=guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=guild)
            synced = await ctx.bot.tree.sync(guild=guild)
        elif spec == "^":
            ctx.bot.tree.clear_commands(guild=guild)
            await ctx.bot.tree.sync(guild=guild)
            synced = []
        else:
            synced = await ctx.bot.tree.sync()

        await ctx.send(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )

    @commands.command(name="presence")
    async def presence_(self, ctx, *, args):
        await self.bot.change_presence(status=discord.Status.online,
                                       activity=discord.Game(name=args))
        await ctx.send("Presence verändert")

    @commands.command(name="reload")
    async def reload_(self, ctx, cog):
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await ctx.send("Extension erfolgreich neu geladen")
            print("-- Extension reloaded --")
        except Exception as error:
            await ctx.send(error)

    @commands.command(name="guild_reset")
    async def guild_reset_(self, ctx, guild_id: int):
        response = self.bot.config.remove_config(guild_id)
        if response:
            msg = "Serverdaten zurückgesetzt"
        else:
            msg = "Keine zugehörige Config gefunden"
        await ctx.send(msg)

    @commands.command(name="stats")
    async def stats_(self, ctx):
        cache = await self.bot.fetch_usage()

        data = []
        for record in cache:
            line = f"`{record['name']}` [{record['amount']}]"
            data.append(line)

        embed = discord.Embed(description="\n".join(data))
        await ctx.send(embed=embed)

    @commands.command(name="change")
    async def change_(self, ctx, guild_id: int, item, value):
        if item.lower() not in ('prefix', 'world', 'game'):
            await ctx.send("Fehlerhafte Eingabe")
            return

        value = int(value) if item == "game" else value
        self.bot.config.update(item, value, guild_id)
        await ctx.send(f"`{item}` registriert")

    @commands.command(name="update_iron")
    async def res_(self, ctx, idc: int, iron: int):
        await self.bot.update_iron(idc, iron)
        await ctx.send(f"Dem User wurden `{iron} Eisen` hinzugefügt")

    @commands.command(name="execute")
    async def sql_(self, ctx, *, query):
        try:
            async with self.bot.tribal_pool.acquire() as conn:
                await conn.execute(query)
        except Exception as error:
            await ctx.send(error)

    @commands.command(name="fetch")
    async def fetch(self, ctx, *, query):
        try:
            async with self.bot.tribal_pool.acquire() as conn:
                response = await conn.fetch(query)
                await ctx.send(response)
        except Exception as error:
            await ctx.send(error)


async def setup(bot):
    await bot.add_cog(Owner(bot))
