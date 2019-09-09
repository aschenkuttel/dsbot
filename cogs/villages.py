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
    async def villages(self, ctx, amount: str, *, args):

        if not amount.isdigit() and amount.lower() != "all":
            msg = "Die Anzahl der gewünschten Dörfer muss entweder eine Zahl oder `all` sein."
            await ctx.send(embed=utils.error_embed(msg))
            return

        con = None
        args = args.split(" ")
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
                    raise utils.DSUserNotFound(name, ctx.world)
            else:
                raise utils.DSUserNotFound(name, ctx.world)

        res = await load.fetch_villages(player, amount, ctx.ctx.world, con)
        if isinstance(res, tuple):
            obd = "Spieler" if res[0] else "Stamm"
            if res[2]:
                msg = f"Der {obd} `{utils.converter(res[1])}` hat leider nur " \
                    f"`{res[3]}` Dörfer auf dem Kontinent `{res[2].upper()}`"
                await ctx.send(embed=utils.error_embed(msg))
                return
            else:
                msg = f"So viele Dörfer hat der {obd} " \
                    f"`{utils.converter(res[1])}` leider nicht"
                await ctx.send(embed=utils.error_embed(msg))
                return

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
            msg = "Fehlerhafte Eingabe - Beispiel:\n**!villages 10 Knueppel-Kutte (K55)**"
            await ctx.send(embed=utils.error_embed(msg))
        elif isinstance(error, ValueError):
            msg = "Fehlerhafte Eingabe - Beispiel:\n**!villages 10 Knueppel-Kutte (K55)**"
            await ctx.send(embed=utils.error_embed(msg))
        elif isinstance(error, AttributeError):
            return


def setup(bot):
    bot.add_cog(Villages(bot))
