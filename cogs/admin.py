from discord.ext import commands
import discord
import utils


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {'Word': ["hangman", "anagram"],
                      'Card': ["quiz", "tc"],
                      'Poker': ["bj", "vp"]}

    async def cog_check(self, ctx):
        if ctx.guild is None:
            raise commands.NoPrivateMessage
        if ctx.author.guild_permissions.administrator:
            return True
        raise commands.MissingPermissions(['administrator'])

    @commands.command(name="refresh", aliases=["f5"])
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def rerfresh_(self, ctx):
        for game, caches in self.games.items():
            cog = self.bot.get_cog(game)
            for cache_name in caches:
                cache = getattr(cog, cache_name)
                try:
                    cache.pop(ctx.guild.id)
                except KeyError:
                    pass

        msg = "Die Spiele wurden zurückgesetzt"
        embed = utils.complete_embed(msg)
        await ctx.send(embed=embed)

    @commands.command(name="world", aliases=["welt"])
    async def get_world(self, ctx):
        embed = utils.complete_embed(f"{ctx.server}")
        await ctx.send(embed=embed)

    @commands.command(name="worlds", aliases=["welten"])
    async def worlds_(self, ctx):
        worlds = sorted(self.bot.worlds)
        result = utils.show_list(worlds, line_break=3)
        description = f"**Aktuelle Welten:**\n{result}"
        embed = discord.Embed(description=description)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Admin(bot))
