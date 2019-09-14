from discord.ext import commands
from utils import error_embed
from load import load
import discord


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        if await self.bot.is_owner(ctx.author):
            return True
        raise commands.NotOwner

    @commands.command(name="presence")
    async def presence_(self, ctx, *, args):
        await self.bot.change_presence(status=discord.Status.online,
                                       activity=discord.Game(name=args))
        await ctx.send("Presence verändert")

    @commands.command(name="guild_game")
    async def guild_game_(self, ctx, guild_id: int, new_game: int):
        load.change_game_channel(guild_id, new_game)
        return await ctx.send("Neuer Game-Channel registriert")

    @commands.command(name="guild_reset")
    async def guild_reset_(self, ctx, guild_id: int):
        if guild_id in load.config_data:
            load.config.pop(guild_id)
            await ctx.send("Serverdaten zurückgesetzt")
        else:
            await ctx.send(embed=error_embed("Keine Daten gefunden"))

    @commands.command(name="ursula_haverbeck", aliases=["ursula"])
    async def ursula_haverbeck_(self, ctx):
        res = [guild.name for guild in ctx.bot.guilds[0:10]]
        await ctx.send(f"{len(ctx.bot.guilds)}\n{', '.join(res)}")

    @commands.command(name="stats")
    async def stats_(self, ctx):
        data = await load.get_usage()
        if not data:
            return
        result = [f"`{usage}` [{cmd}]" for cmd, usage in data]
        return await ctx.send(
            embed=discord.Embed(description='\n'.join(result)))

    @commands.command(name="change")
    async def change_(self, ctx, guild_id: int, item, value):
        if item.lower() not in ["prefix", "world", "game", "conquer"]:
            return await ctx.send(embed=error_embed("Fehlerhafte Eingabe"))
        value = value if item == "prefix" else int(value)
        load.change_item(guild_id, item, value)
        load.save_config()
        return await ctx.send(f"`{item}` registriert")

    @commands.command(name="change_res")
    async def res_(self, ctx, idc: int, iron: int):
        await load.save_user_data(idc, iron)
        await ctx.send(f"Dem User wurden `{iron} Eisen` hinzugefügt")


def setup(bot):
    bot.add_cog(Admin(bot))
