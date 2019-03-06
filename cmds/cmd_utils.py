from discord.ext import commands
from load import load
from utils import error_embed
import discord
import re


class Rm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.error_txt = "Das Maximum von 7 verschiedenen " \
                         "Truppentypen wurde überschritten."
        self.base = "javascript: var settings = Array" \
                    "(0, 0, 0, 0, {0}, {1}, 0, 0, 0, 0," \
                    " 0, 0, {2}, {3}, 'attack'); $.getScript" \
                    "('https://media.innogamescdn.com/com_DS_DE/" \
                    "scripts/qb_main/scriptgenerator.js%27); void(0);"

    @commands.command(aliases=["rundmail"])
    async def rm(self, ctx, *tribes: str):

        if len(tribes) > 10:
            msg = "Der RM Command unterstützt aktuell nur " \
                  "maximal `10 Stämme` per Command."
            return await ctx.send(msg)

        world = load.get_world(ctx.channel)
        data = await load.find_ally_player(tribes, world)
        if isinstance(data, str):
            return await ctx.send(f"Der Stamm `{data}` existiert so nicht.")
        await ctx.message.add_reaction("📨")
        return await ctx.author.send(f"```\n{';'.join(data)}\n```")

    @commands.command(name="rz3", aliases=["scavenge3"])
    async def rz3_(self, ctx, *args: int):
        if len(args) > 7:
            return await ctx.send(embed=error_embed(self.error_txt))
        data = load.scavenge(3, args)
        cache = []
        for index, ele in enumerate(data):
            cache.append(f"**Raubzug {index + 1}:** `[{', '.join(ele)}]`")
        em = discord.Embed(description='\n'.join(cache))
        return await ctx.send(embed=em)

    @commands.command(name="rz4", aliases=["scavenge4"])
    async def rz4_(self, ctx, *args: int):
        if len(args) > 7:
            return await ctx.send(embed=error_embed(self.error_txt))
        data = load.scavenge(4, args)
        cache = []
        for index, ele in enumerate(data):
            cache.append(f"**Raubzug {index + 1}:** `[{', '.join(ele)}]`")
        em = discord.Embed(description='\n'.join(cache))
        return await ctx.send(embed=em)

    @commands.command(name="sl")
    async def sl_(self, ctx, spy: int, kav: int, *, args):
        result = re.findall(r'\d\d\d\|\d\d\d', args)
        if not result:
            return
        cache = []
        for coord in result:
            x, y = coord.split("|")[0], coord.split("|")[1]
            res = self.base.format(spy, kav, x, y)
            cache.append(res) if coord else None

        await ctx.send(embed=discord.Embed(description='\n'.join(cache)))

    @rz3_.error
    async def rz3_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            msg = "Truppenangaben dürfen nur aus Zahlen bestehen."
            return await ctx.send(embed=error_embed(msg))

    @rz4_.error
    async def rz4_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            msg = "Truppenangaben dürfen nur aus Zahlen bestehen."
            return await ctx.send(embed=error_embed(msg))

    @sl_.error
    async def sl_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            return await ctx.send(
                embed=error_embed("!sl <spys> <lkav> <coord list>"))
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(
                embed=error_embed("!sl <spys> <lkav> <coord list>"))


def setup(bot):
    bot.add_cog(Rm(bot))
