import discord
from discord.ext import commands
from utils import error_embed, DSObject
from load import load


class Akte(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="akte", aliases=["twstats"])
    async def akte_(self, ctx, *, user: DSObject):
        akte = discord.Embed(title=user.name, url=user.twstats_url)
        await ctx.send(embed=akte)

    @commands.command(name="ingame")
    async def ingame_(self, ctx, *, user: DSObject):
        profile = discord.Embed(title=user.name, url=user.ingame_url)
        await ctx.send(embed=profile)

    @commands.command(name="guest")
    async def guest_(self, ctx, *, user: DSObject):
        guest = discord.Embed(title=user.name, url=user.guest_url)
        await ctx.send(embed=guest)

    @commands.command(name="visit", aliases=["besuch"])
    async def visit_(self, ctx, world: int):
        if not load.is_valid(world):
            return await ctx.send(embed=error_embed("Diese Welt existiert nicht"))
        desc = f"https://de{load.casual(world)}.die-staemme.de/guest.php"
        await ctx.send(embed=discord.Embed(description=f"[{world}]({desc})"))

    @visit_.error
    async def visit_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=error_embed(f"Die gewünschte Welt fehlt"))

    @akte_.error
    async def akte_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            msg = "Der gewünschte Spieler/Stamm fehlt"
            await ctx.send(embed=error_embed(msg))


def setup(bot):
    bot.add_cog(Akte(bot))
