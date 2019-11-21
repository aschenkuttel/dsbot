import discord
from discord.ext import commands
from utils import error_embed, DSObject, DSUserNotFound, casual
from load import load


class Akte(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="akte", aliases=["twstats"])
    async def akte_(self, ctx, *, user: DSObject):
        akte = discord.Embed(title=user.name, url=user.twstats_url)
        await ctx.send(embed=akte)

    @commands.command(name="player", aliases=["spieler", "tribe", "stamm"])
    async def ingame_(self, ctx, *, username):
        if ctx.invoked_with.lower() in ("player", "spieler"):
            dsobj = await load.fetch_player(ctx.world, username, True)
        else:
            dsobj = await load.fetch_tribe(ctx.world, username, True)
        if not dsobj:
            raise DSUserNotFound(username)
        profile = discord.Embed(title=dsobj.name, url=dsobj.ingame_url)
        await ctx.send(embed=profile)

    @commands.command(name="guest")
    async def guest_(self, ctx, *, user: DSObject):
        guest = discord.Embed(title=user.name, url=user.guest_url)
        await ctx.send(embed=guest)

    @commands.command(name="visit", aliases=["besuch"])
    async def visit_(self, ctx, world: int):
        if not load.is_valid(world):
            return await ctx.send(embed=error_embed("Diese Welt existiert nicht"))
        desc = f"https://de{casual(world)}.die-staemme.de/guest.php"
        await ctx.send(embed=discord.Embed(description=f"[{world}]({desc})"))


def setup(bot):
    bot.add_cog(Akte(bot))
