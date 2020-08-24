from discord.ext import commands
import discord
import utils


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {'Word': ["hangman", "anagram"],
                      'Card': ["quiz", "tribalcard"],
                      'Poker': ["blackjack", "videopoker"]}

    async def cog_check(self, ctx):
        if ctx.guild is None:
            raise commands.NoPrivateMessage

        if ctx.author.guild_permissions.administrator:
            return True

        raise commands.MissingPermissions(['administrator'])

    @commands.group(name="reset", invoke_without_command=True)
    async def reset(self, ctx):
        msg = f"`{ctx.prefix} <game|conquer|config>`"
        await ctx.send(embed=utils.error_embed(msg))

    @reset.command(name="game")
    async def games_(self, ctx):
        for game, caches in self.games.items():
            cog = self.bot.get_cog(game)
            for cache_name in caches:
                cache = getattr(cog, cache_name)
                try:
                    cache.pop(ctx.guild.id)
                except KeyError:
                    pass

        msg = "Alle Minigames wurden zurückgesetzt"
        await ctx.send(embed=utils.complete_embed(msg))

    @reset.command(name="conquer")
    async def conquer_(self, ctx):
        self.bot.config.change_item(ctx.guild.id, 'conquer', {})
        msg = "Die Conquereinstellungen wurden zurückgesetzt"
        await ctx.send(embed=utils.complete_embed(msg))

    @reset.command(name="config")
    async def config_(self, ctx):
        self.bot.config.remove_config(ctx.guild.id)
        msg = "Die Servereinstellungen wurden zurückgesetzt"
        await ctx.send(embed=utils.complete_embed(msg))

    @commands.command(name="world")
    async def world_(self, ctx):
        server = self.bot.config.get_related_world(ctx.channel)
        relation = "Channel" if server == ctx.server else "Server"
        embed = utils.complete_embed(f"{ctx.world} [{relation}]")
        await ctx.send(embed=embed)

    @commands.command(name="worlds")
    async def worlds_(self, ctx):
        worlds = sorted(self.bot.worlds)
        result = utils.show_list(worlds, line_break=3)
        description = f"**Aktuelle Welten:**\n{result}"
        embed = discord.Embed(description=description)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Admin(bot))
