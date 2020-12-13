from utils import CoordinateConverter
from discord.ext import commands
from collections import Counter
import discord
import typing
import random
import utils
import io
import re
import os


class Villages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.type = 1
        self.base_options = {'radius': [1, 10, 25], 'points': None}

    async def send_result(self, ctx, result, object_name):
        if not result:
            msg = f"Es sind keine {object_name} in Reichweite"
            await ctx.send(msg)
            return

        is_village = isinstance(result[0], utils.Village)
        attribute = 'coords' if is_village else 'mention'

        represent = []
        for index, obj in enumerate(result, 1):
            line = f"{index}. {getattr(obj, attribute)}"
            represent.append(line)

        msg = "\n".join(represent)

        if len(msg) <= 2000:
            if not is_village:
                embed = discord.Embed(description=msg)
                await ctx.author.send(embed=embed)
            else:
                await ctx.author.send(msg)

        else:
            if not is_village:
                represent = []
                for index, obj in enumerate(result, 1):
                    line = f"{index}. {getattr(obj, 'name')}"
                    represent.append(line)

            text = io.StringIO()
            text.write(f'{os.linesep}'.join(represent))
            text.seek(0)
            file = discord.File(text, 'villages.txt')
            await ctx.author.send(file=file)

        await ctx.private_hint()

    async def fetch_in_radius(self, world, village, **kwargs):
        radius = kwargs.get('radius')
        points = kwargs.get('points')
        extra_query = kwargs.get('extra')

        arguments = [world, village.x, village.y, radius.value]

        query = 'SELECT * FROM village WHERE world = $1 ' \
                'AND SQRT(POWER(ABS($2 - x), 2) + POWER(ABS($3 - y), 2)) <= $4'

        if points:
            query += f' AND points {points.sign} $5'
            arguments.append(points.value)

        if extra_query:
            query += extra_query

        async with self.bot.pool.acquire() as conn:
            result = await conn.fetch(query, *arguments)
            return [utils.Village(rec) for rec in result]

    @commands.command(name="villages")
    async def villages_(self, ctx, amount: typing.Union[int, str], *args):
        if isinstance(amount, str) and amount.lower() != "all":
            msg = "Die Anzahl muss entweder eine Zahl oder `all` sein."
            await ctx.send(msg)
            return

        if not args:
            raise commands.MissingRequiredArgument

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
        if isinstance(amount, int):
            if len(result) < amount:
                ds_type = "Spieler" if dsobj.alone else "Stamm"
                raw = "Der {} `{}` hat leider nur `{}` Dörfer"
                args = [ds_type, dsobj.name, len(result)]

                if con:
                    raw += "auf dem Kontinent `{}`"
                    args.append(con)

                await ctx.send(raw.format(*args))
                return

            else:
                result = result[:amount]

        await self.send_result(ctx, result, "Dörfer")

    @commands.command(name="barbarian", aliases=["bb"])
    async def barbarian_(self, ctx, village: CoordinateConverter, *, options=None):
        radius, points = utils.keyword(options, **self.base_options)
        kwargs = {'radius': radius, 'points': points,
                  'extra': ' AND village.player = 0'}

        result = await self.fetch_in_radius(ctx.server, village, **kwargs)
        await self.send_result(ctx, result, "Barbarendörfer")

    @commands.command(name="inactive", aliases=["graveyard"])
    async def graveyard_(self, ctx, village: CoordinateConverter, *, options=None):
        args = utils.keyword(options, **self.base_options, since=[1, 3, 14], tribe=None)
        radius, points, inactive_since, tribe = args

        all_villages = await self.fetch_in_radius(ctx.server, village, radius=radius)
        player_ids = set([vil.player_id for vil in all_villages])

        base = []
        for num in range(inactive_since.value + 1):
            table = f"player{num or ''}"
            query_part = f'SELECT * FROM {table} ' \
                         f'WHERE {table}.world = $1 ' \
                         f'AND {table}.id = ANY($2)'

            if tribe.value in [True, False]:
                state = '!=' if tribe.value else '='
                query_part += f' AND {table}.tribe_id {state} 0'

            base.append(query_part)

        query = ' UNION ALL '.join(base)
        async with self.bot.pool.acquire() as conn:
            cache = await conn.fetch(query, ctx.server, player_ids)
            result = [utils.Player(rec) for rec in cache]

        player_cache = {}
        day_counter = Counter()
        for player in result:

            last = player_cache.get(player.id)
            if last is None:

                if not points.compare(player.points):
                    player_cache[player.id] = False
                else:
                    player_cache[player.id] = player

            elif last is False:
                continue

            elif last.points <= player.points and last.att_bash == player.att_bash:
                player_cache[player.id] = player
                day_counter[player.id] += 1

            else:
                player_cache[player.id] = False

        result = []
        for player_id, player in player_cache.items():
            if day_counter[player_id] != inactive_since.value:
                continue
            else:
                result.append(player)

        await self.send_result(ctx, result, "inaktiven Spieler")


def setup(bot):
    bot.add_cog(Villages(bot))
