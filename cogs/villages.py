from discord.ext import commands
import discord
import random
import utils
import io
import re
import os


class Villages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_coords(self, ctx, result):
        coords = [f"{i}. {r['x']}|{r['y']}" for i, r in enumerate(result, 1)]

        if len(coords) < 181:
            await ctx.author.send('\n'.join(coords))
        else:
            file = io.StringIO()
            file.write(f'{os.linesep}'.join(coords))
            file.seek(0)
            await ctx.author.send(file=discord.File(file, 'villages.txt'))

        await ctx.private_hint()

    @commands.command(name="villages")
    async def villages_(self, ctx, amount: str, *args):
        if not amount.isdigit() and amount.lower() != "all":
            msg = "Die Anzahl der gewünschten Dörfer muss entweder eine Zahl oder `all` sein."
            return await ctx.send(embed=utils.error_embed(msg))

        if not args:
            msg = "Fehlerhafte Eingabe - Beispiel:\n**!villages 10 Knueppel-Kutte K55**"
            return await ctx.send(embed=utils.error_embed(msg))

        con = None
        if len(args) == 1:
            name = args[0]
        elif re.match(r'[k, K]\d\d', args[-1]):
            con = args[-1]
            name = ' '.join(args[:-1])
        else:
            name = ' '.join(args)
        dsobj = await self.bot.fetch_both(ctx.server, name)
        if not dsobj:
            if con:
                dsobj = await self.bot.fetch_both(ctx.server, f"{name} {con}")
                if not dsobj:
                    raise utils.DSUserNotFound(name)
            else:
                raise utils.DSUserNotFound(name)

        if isinstance(dsobj, utils.Tribe):
            query = "SELECT * FROM player WHERE world = $1 AND tribe_id = $2;"
            async with self.bot.pool.acquire() as conn:
                cache = await conn.fetch(query, ctx.server, dsobj.id)
            id_list = [rec['id'] for rec in cache]
        else:
            id_list = [dsobj.id]

        arguments = [ctx.server, id_list]
        query = "SELECT * FROM village WHERE world = $1 AND player = ANY($2)"
        if con:
            query = query + ' AND LEFT(CAST(x AS TEXT), 1) = $3' \
                            ' AND LEFT(CAST(y AS TEXT), 1) = $4'
            arguments.extend([con[2], con[1]])

        async with self.bot.pool.acquire() as conn:
            result = await conn.fetch(query, *arguments)

        random.shuffle(result)
        if amount != "all":
            if len(result) < int(amount):
                ds_type = "Spieler" if dsobj.alone else "Stamm"
                raw = "Der {} `{}` hat leider nur `{}` Dörfer"
                if con:
                    raw += "auf dem Kontinent `{}`"
                    msg = raw.format(ds_type, dsobj.name, len(result), con)
                else:
                    msg = raw.format(ds_type, dsobj.name, len(result))
                return await ctx.send(embed=utils.error_embed(msg))
            else:
                result = result[:int(amount)]

        await self.send_coords(ctx, result)

    @commands.command(name="bb")
    async def bb_(self, ctx, center, *, options=None):
        coord = re.match(r'\d\d\d\|\d\d\d', center)
        if not coord:
            msg = "Du musst eine gültige Koordinate eingeben"
            await ctx.send(msg)
            return

        radius, points = utils.keyword(options, radius=20, points=None)

        x = int(coord.string.split("|")[0])
        y = int(coord.string.split("|")[1])
        x_coords = list(range(x - radius, x + radius + 1))
        y_coords = list(range(y - radius, y + radius + 1))

        arguments = [ctx.server, x_coords, y_coords]
        query = 'SELECT * FROM village WHERE world = $1 AND ' \
                'x = ANY($2) AND y = ANY($3) AND player = 0 '
        if points:
            query += 'AND points <= $4'
            arguments.append(points)

        async with self.bot.pool.acquire() as conn:
            result = await conn.fetch(query, *arguments)

        if not result:
            msg = "Es sind keine Barbarendörfer in Reichweite"
            await ctx.send(msg)
        else:
            await self.send_coords(ctx, result)


def setup(bot):
    bot.add_cog(Villages(bot))
