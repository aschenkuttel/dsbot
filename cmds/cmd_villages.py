from load import load
from discord.ext import commands
from utils import converter, error_embed
import discord
import io


class Villages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["dörfer"])
    async def villages(self, ctx, amount: str, *, args):

        if not amount.isdigit() and amount != "all":
            msg = "Die Anzahl der gewünschten Dörfer muss entweder eine Zahl oder `all` sein."
            return await ctx.send(embed=error_embed(msg))

        player, con = await load.vil_handler(ctx.world, args)

        res = await load.get_villages(player, amount, ctx.world, con)

        if isinstance(res, tuple):
            obd = "Spieler" if res[0] else "Stamm"
            if res[2]:
                msg = f"Der {obd} `{converter(res[1])}` hat leider nur " \
                    f"`{res[3]}` Dörfer auf dem Kontinent `{res[2].upper()}`"
                return await ctx.send(embed=error_embed(msg))
            else:
                msg = f"So viele Dörfer hat der {obd} " \
                    f"`{converter(res[1])}` leider nicht."
                return await ctx.send(embed=error_embed(msg))

        await ctx.message.add_reaction("📨")

        if isinstance(res, io.StringIO):
            await ctx.author.send(file=discord.File(res, 'villages.txt'))
            return res.close()

        fin = '\n'.join([f"{r['x']}|{r['y']}" for r in res])
        if len(fin) <= 2000:
            await ctx.author.send(fin)
        else:
            counter = 0
            while len(fin) > counter:
                stuff = counter + 2000
                await ctx.author.send(fin[counter:stuff])
                counter = stuff

    @villages.error
    async def villages_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            msg = "Fehlerhafte Eingabe - Beispiel:\n**!villages Knueppel-Kutte 10 (K55)**"
            return await ctx.send(embed=error_embed(msg))
        if isinstance(error, ValueError):
            msg = "Fehlerhafte Eingabe - Beispiel:\n**!villages Knueppel-Kutte 10 (K55)**"
            return await ctx.send(embed=error_embed(msg))
        if isinstance(error, AttributeError):
            return


def setup(bot):
    bot.add_cog(Villages(bot))
