import discord
from discord.ext import commands
from utils import error_embed
from load import load, DSObject


class Akte(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="akte", aliases=["twstats"])
    async def akte_(self, ctx, *, user: DSObject):
        world = load.get_world(ctx.channel, True)
        base = "http://de.twstats.com/de{}/index.php?page={}&id={}"
        me = "player" if user.alone else "tribe"
        result_link = base.format(world, me, user.id)
        akte = discord.Embed(title=user.name, url=result_link)
        await ctx.send(embed=akte)

    @commands.command(name="ingame")
    async def ingame_(self, ctx, *, user: DSObject):
        world = load.get_world(ctx.channel, True)
        base = f"https://de{world}.die-staemme.de/game.php?screen="
        state = "player" if user.alone else "ally"
        result_link = f"{base}info_{state}&id={user.id}"
        profile = discord.Embed(title=user.name, url=result_link)
        await ctx.send(embed=profile)

    @commands.command(name="visit", aliases=["besuch"])
    async def visit_(self, ctx, world: int):
        if not await load.is_valid(world):
            return await ctx.send(embed=error_embed("Diese Welt existiert nicht."))
        desc = f"https://de{load.casual(world)}.die-staemme.de/guest.php"
        await ctx.send(embed=discord.Embed(description=f"[{world}]({desc})"))

    @visit_.error
    async def visit_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=error_embed(f"Der gewünschte Spieler fehlt."))

    @akte_.error
    async def akte_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            msg = "Der gewünschte Spieler/Stamm fehlt."
            await ctx.send(embed=error_embed(msg))


def setup(bot):
    bot.add_cog(Akte(bot))
