from utils import CoordinateConverter
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
        self.base_options = {'radius': [10, 20], 'points': None}

    async def send_result(self, ctx, result, object_name):
        if not result:
            msg = f"Es sind keine {object_name} in Reichweite"
            await ctx.send(msg)
            return

        coordinate = isinstance(result[0], utils.Village)
        attribute = "string" if coordinate else "mention"

        represent = []
        for index, obj in enumerate(result, 1):
            line = f"{index}. {getattr(obj, attribute)}"
            represent.append(line)

        msg = "\n".join(represent)

        if len(msg) <= 2000:
            if not coordinate:
                embed = discord.Embed(description=msg)
                await ctx.author.send(embed=embed)
            else:
                await ctx.author.send(msg)

        else:
            file = io.StringIO()
            file.write(f'{os.linesep}'.join(represent))
            file.seek(0)
            await ctx.author.send(file=discord.File(file, 'villages.txt'))

        await ctx.private_hint()

    async def fetch_in_radius(self, world, village, **kwargs):
        radius = kwargs.get('radius', 20)
        points = kwargs.get('points', None)
        extra_query = kwargs.get('extra', None)

        arguments = [world, village.x, village.y, radius]

        query = 'SELECT * FROM village WHERE world = $1 ' \
                'AND SQRT(POWER(ABS($2 - x), 2) + POWER(ABS($3 - y), 2)) <= $4'

        if points:
            query += ' AND points <= $5'
            arguments.append(points)

        if extra_query:
            query += extra_query

        async with self.bot.pool.acquire() as conn:
            result = await conn.fetch(query, *arguments)
            return [utils.Village(rec) for rec in result]

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
            cache = await conn.fetch(query, *arguments)
            result = [utils.Village(rec) for rec in cache]

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

        await self.send_result(ctx, result, "Dörfer")

    @commands.command(name="bb")
    async def bb_(self, ctx, village: utils.CoordinateConverter, *, options=None):
        radius, points = utils.keyword(options, **self.base_options)
        kwargs = {'radius': radius, 'points': points,
                  'extra': ' AND village.player = 0'}

        result = await self.fetch_in_radius(ctx.server, village, **kwargs)

        if not result:
            msg = "Es sind keine Barbarendörfer in Reichweite"
            await ctx.send(msg)
        else:
            await self.send_result(ctx, result, "Barbarendörfer")

    @commands.command(name="inactive", aliases=["graveyard"])
    async def graveyard_(self, ctx, village: utils.CoordinateConverter, *, options=None):
        args = utils.keyword(options, **self.base_options, since=[3, 14], tribe=None)
        radius, points, inactive_since = args

        all_villages = await self.fetch_in_radius(ctx.server, village, radius=radius)
        player_ids = set([vil.player_id for vil in all_villages])

        arguments = [ctx.server, player_ids]
        base = 'SELECT * FROM player WHERE world = $1 AND player.id'

        query_pkg = {}
        for num in range(inactive_since + 1):
            arch = f"player{num or ''}"

            if num == 0:
                query_pkg[arch] = 'SELECT player.id FROM {} WHERE ' \
                                  'player.world = $1 AND ' \
                                  'player.id = ANY($2)'

                if points is not None:
                    query_pkg[arch] += ' AND player.points <= $3'
                    arguments.append(points)

            else:
                previous = num - 1 if num - 1 else ""
                query_pkg[arch] = f'{arch}.world = $1 AND {arch}.id = player.id ' \
                                  f'AND {arch}.points >= player{previous}.points'

        tables = ", ".join(query_pkg.keys())
        clauses = " AND ".join(query_pkg.values())
        query = f'{base} IN ({clauses.format(tables)})'
        print(query)
        # query = f'SELECT * FROM player, {arch} WHERE ' \
        #         f'player.world = $1 AND player.id = ANY($2) AND ' \
        #         f'{arch}.world = $1 AND player.id = {arch}.id AND ' \
        #         f'player.points <= {arch}.points'

        async with self.bot.pool.acquire() as conn:
            cache = await conn.fetch(query, *arguments)
            result = [utils.Player(rec) for rec in cache]

        await self.send_result(ctx, result, "Spieler")

    @commands.command(name="pusherradar")
    async def pusherradar_(self, ctx, village: utils.CoordinateConverter):
        pass


def setup(bot):
    bot.add_cog(Villages(bot))
