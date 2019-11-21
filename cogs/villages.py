from load import load
from discord.ext import commands
import utils
import discord
import io
import re


class Villages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["dörfer"])
    async def villages(self, ctx, amount: str, *args):

        if not amount.isdigit() and amount.lower() != "all":
            msg = "Die Anzahl der gewünschten Dörfer muss entweder eine Zahl oder `all` sein."
            await ctx.send(embed=utils.error_embed(msg))
            return

        if not args:
            msg = "Fehlerhafte Eingabe - Beispiel:\n**!villages 10 Knueppel-Kutte K55**"
            await ctx.send(embed=utils.error_embed(msg))

        con = None
        if len(args) == 1:
            name = args[0]
        elif re.match(r'[k, K]\d\d', args[-1]):
            con = args[-1]
            name = ' '.join(args[:-1])
        else:
            name = ' '.join(args)
        player = await load.fetch_both(ctx.world, name)
        if not player:
            if con:
                player = await load.fetch_both(ctx.world, f"{name} {con}")
                if not player:
                    raise utils.DSUserNotFound(name)
            else:
                raise utils.DSUserNotFound(name)

        result = await load.fetch_villages(player, amount, ctx.world, con)
        if isinstance(result, tuple):
            ds_type = "Spieler" if player.alone else "Stamm"
            if con:
                msg = f"Der {ds_type} `{player.name}` hat leider nur " \
                      f"`{result}` Dörfer auf dem Kontinent `{con}`"
            else:
                msg = f"Der {ds_type} `{player.name}` hat leider nur `{result}` Dörfer"
            await ctx.send(embed=utils.error_embed(msg))
            return

        await utils.private_hint(ctx)
        if isinstance(result, io.StringIO):
            await ctx.author.send(file=discord.File(result, 'villages.txt'))
            return result.close()
        else:
            await ctx.author.send('\n'.join(result))

    @commands.command(name="bb")
    async def bb_(self, ctx, center, radius=20):
        pass

    @villages.error
    async def villages_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            msg = "Fehlerhafte Eingabe - Beispiel:\n**!villages 10 Knueppel-Kutte K55**"
            await ctx.send(embed=utils.error_embed(msg))


def setup(bot):
    bot.add_cog(Villages(bot))
