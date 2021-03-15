from utils import CoordinateConverter
from discord.ext import commands
from collections import Counter
import discord
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

        represent = ["```"]
        for index, obj in enumerate(result, 1):
            line = f"{index}. {obj.coords}"
            represent.append(line)

        represent.append("```")
        msg = "\n".join(represent)

        if len(msg) <= 2000:
            await ctx.author.send(msg)

        else:
            text = io.StringIO()
            text.write(f"{os.linesep}".join(represent))
            text.seek(0)
            file = discord.File(text, "villages.txt")
            await ctx.author.send(file=file)

        await ctx.private_hint()

    async def fetch_in_radius(self, world, village, **kwargs):
        radius = kwargs.get('radius')
        points = kwargs.get('points')
        extra_query = kwargs.get('extra')

        arguments = [world, village.x, village.y, radius.value]

        query = 'SELECT * FROM village WHERE world = $1 AND ' \
                'SQRT(POWER(ABS($2 - x), 2) + POWER(ABS($3 - y), 2)) <= $4'

        if points:
            query += f' AND points {points.sign} $5'
            arguments.append(points.value)

        if extra_query:
            query += extra_query

        async with self.bot.tribal_pool.acquire() as conn:
            result = await conn.fetch(query, *arguments)
            return [utils.Village(rec) for rec in result]

    @commands.command(name="villages")
    async def villages(self, ctx, *, arguments):
        base_options = {'points': None, 'continent': None}
        rest, points, continent = utils.keyword(arguments, strip=True, **base_options)
        user_arguments = rest.split()

        if len(user_arguments) < 2:
            raise utils.MissingRequiredArgument()

        amount = user_arguments.pop(-1)
        if not amount.isdigit() or amount == "all":
            msg = "Die Anzahl muss entweder eine Zahl oder `all` sein."
            await ctx.send(msg)
            return

        name = " ".join(user_arguments)
        dsobj = await self.bot.fetch_both(ctx.server, name)

        if dsobj is None:
            raise utils.DSUserNotFound(name)

        if isinstance(dsobj, utils.Tribe):
            member = await self.bot.fetch_tribe_member(ctx.server, dsobj.id)
            ids = [m.id for m in member]
        else:
            ids = [dsobj.id]

        if re.match(r'[k, K]\d\d', str(continent.value)):
            conti_str = continent.value
        else:
            conti_str = None

        arguments = [ctx.server, ids]
        query = 'SELECT * FROM village WHERE world = $1 AND player = ANY($2)'

        if conti_str is not None:
            query = query + ' AND LEFT(CAST(x AS TEXT), 1) = $3' \
                            ' AND LEFT(CAST(y AS TEXT), 1) = $4'
            arguments.extend([conti_str[2], conti_str[1]])

        async with self.bot.tribal_pool.acquire() as conn:
            cache = await conn.fetch(query, *arguments)
            result = [utils.Village(rec) for rec in cache]
            random.shuffle(result)

        if points.value != 0:
            for vil in result.copy():
                if not points.compare(vil.points):
                    result.remove(vil)

        if amount.isdigit():
            limit = int(amount)

            if len(result) < limit:
                ds_type = "Spieler" if dsobj.alone else "Stamm"
                raw = "Der {} `{}` hat nur `{}` Dörfer"
                args = [ds_type, dsobj.name, len(result)]

                if points.value:
                    raw += " in dem Punktebereich"

                if continent:
                    raw += " auf Kontinent `{}`"
                    args.append(continent.value)

                msg = raw.format(*args)
                await ctx.send(msg)
                return

            else:
                result = result[:limit]

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
        player_ids = set(vil.player_id for vil in all_villages)

        base = []
        for num in range(inactive_since.value + 1):
            table = f"player{num or ''}"
            query_part = f'SELECT * FROM {table} ' \
                         f'WHERE {table}.world = $1 ' \
                         f'AND {table}.id = ANY($2)'

            if tribe.value is True:
                query_part += f'AND {table}.tribe_id != 0'

            elif tribe.value is False:
                query_part += f'AND {table}.tribe_id == 0'

            base.append(query_part)

        query = ' UNION ALL '.join(base)
        async with self.bot.tribal_pool.acquire() as conn:
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

        vil_dict = {p_id: [] for p_id in player_cache}
        for vil in all_villages:
            if vil.player_id != 0:
                vil_dict[vil.player_id].append(vil)

        result = []
        for player_id in player_cache:
            if day_counter[player_id] == inactive_since.value:
                result.extend(vil_dict[player_id])

        await self.send_result(ctx, result, "inaktiven Spielerdörfer")


def setup(bot):
    bot.add_cog(Villages(bot))
