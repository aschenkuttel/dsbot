from utils import CoordinateConverter
from discord.ext import commands
from discord import app_commands
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

    async def send(self, interaction, message=None, defer=False, **kwargs):
        if defer is True:
            await interaction.followup.send(message, **kwargs)
        else:
            await interaction.response.send_message(message, **kwargs)

    async def send_result(self, interaction, result, object_name, defer=False):
        if not result:
            msg = f"Es sind keine {object_name} in Reichweite"
            return await self.send(interaction, msg, defer)

        represent = ["```"]
        for index, obj in enumerate(result, 1):
            line = f"{index}. {obj.coords}"
            represent.append(line)

        represent.append("```")
        msg = "\n".join(represent)

        if len(msg) <= 2000:
            await self.send(interaction, msg, defer, ephemeral=True)
            return None

        else:
            text = io.StringIO()
            text.write(f"{os.linesep}".join(represent))
            text.seek(0)
            file = discord.File(text, "villages.txt")  # noqa
            await self.send(interaction, defer=defer, file=file, ephemeral=True)
            return None

    async def fetch_in_radius(self, world, village, **kwargs):
        radius = kwargs.get('radius', 0)
        extra_query = kwargs.get('extra')

        arguments = [village.x, village.y, radius]
        query = f'SELECT * FROM village_{world} WHERE ' \
                f'SQRT(POWER(ABS($1 - x), 2) + POWER(ABS($2 - y), 2)) <= $3'

        if extra_query:
            query += extra_query

        async with self.bot.tribal_pool.acquire() as conn:
            result = await conn.fetch(query, *arguments)
            return [utils.Village(rec) for rec in result]

    @app_commands.command(name="villages", description="Alle Dörfer eines Spielers oder Stammes")
    @app_commands.describe(dsobj="Stamm oder Spieler", amount="Menge der Dörfer", points="Siehe /help points",
                           continent="Kontinent in welchem die Dörfer sich befinden müssen")
    async def villages(self, interaction, dsobj: utils.DSConverter,
                       amount: int = 0, points: str = "", continent: str = ""):
        if isinstance(dsobj, utils.Tribe):
            member = await self.bot.fetch_tribe_member(interaction.server, dsobj.id)
            ids = [m.id for m in member]
        else:
            ids = [dsobj.id]

        if continent is not None:
            match = re.match(r'[k, K]\d\d', continent)
            conti_str = match.string if match else None
        else:
            conti_str = None

        arguments = [ids]
        query = f'SELECT * FROM village_{interaction.server} WHERE player_id = ANY($1)'

        if conti_str is not None:
            query = query + ' AND LEFT(CAST(x AS TEXT), 1) = $2' \
                            ' AND LEFT(CAST(y AS TEXT), 1) = $3'
            arguments.extend([conti_str[2], conti_str[1]])

        async with self.bot.tribal_pool.acquire() as conn:
            cache = await conn.fetch(query, *arguments)
            result = [utils.Village(rec) for rec in cache]
            random.shuffle(result)

        if points := utils.Keyword.from_str(points) is not None:
            for vil in result.copy():
                if points.compare(vil.points):
                    result.remove(vil)

        if amount != 0:
            if len(result) < amount:
                ds_type = "Spieler" if dsobj.alone else "Stamm"
                raw = "Der {} `{}` hat nur `{}` Dörfer"
                args = [ds_type, dsobj.name, len(result)]

                if points != 0:
                    raw += " in dem Punktebereich"

                if continent:
                    raw += " auf Kontinent `{}`"
                    args.append(continent)

                msg = raw.format(*args)
                await interaction.response.send_message(msg)
                return

            else:
                result = result[:amount]

        await self.send_result(interaction, result, "Dörfer")

    @app_commands.command(name="bb", description="Alle Barbarendörfer im Umkreis um eine Koordinate")
    @app_commands.describe(village="Koordinate um welche die gewünschten Barbarendörfer liegen",
                           radius="Radius in welchem sich die Barbarendörfer befinden müssen",
                           points="Siehe /help points")
    async def barbarian(self, interaction, village: CoordinateConverter,
                        radius: app_commands.Range[int, 1, 25] = 10, points: str = ""):
        kwargs = {'radius': radius, 'extra': f' AND player_id = 0'}
        result = await self.fetch_in_radius(interaction.server, village, **kwargs)

        if points := utils.Keyword.from_str(points) is not None:
            for vil in result.copy():
                if not points.compare(vil.points):
                    result.remove(vil)

        await self.send_result(interaction, result, "Barbarendörfer")

    @app_commands.command(name="inactive", description="Alle inaktiven Spieler im Umkreis um eine Koordinate")
    @app_commands.describe(village="Koordinate um welche die gewünschten Dörfer liegen",
                           radius="Radius in welchem sich die Dörfer befinden müssen",
                           points="Siehe /help points", since="Tage seit dem der Spieler inaktiv sein muss",
                           tribe="True falls die Spieler einen Stamm haben sollen, False falls nicht")
    async def graveyard_(self, interaction, village: CoordinateConverter, radius: app_commands.Range[int, 1, 25] = 10,
                         points: str = "", since: app_commands.Range[int, 1, 14] = 3, tribe: bool = None):
        await interaction.response.defer()

        all_villages = await self.fetch_in_radius(interaction.server, village, radius=radius)
        player_ids = set(vil.player_id for vil in all_villages)

        base = []
        for num in range(since + 1):
            table = f"player_{interaction.server}" if num == 0 else f"player_{num}"

            query_part = f'SELECT * FROM {table} ' \
                         f'WHERE {table}.world = $1 ' \
                         f'AND {table}.id = ANY($2)'

            if tribe is True:
                query_part += f'AND {table}.tribe_id != 0'

            elif tribe is False:
                query_part += f'AND {table}.tribe_id == 0'

            base.append(query_part)

        query = ' UNION ALL '.join(base)

        async with self.bot.tribal_pool.acquire() as conn:
            cache = await conn.fetch(query, interaction.server, player_ids)
            result = [utils.Player(rec) for rec in cache]

        player_cache = {}
        day_counter = Counter()
        points = utils.Keyword.from_str(points)

        for player in result:
            last = player_cache.get(player.id)

            if last is None:
                if points is not None and not points.compare(player.points):
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
            if day_counter[player_id] >= since:
                result.extend(vil_dict[player_id])

        await self.send_result(interaction, result, "inaktiven Spielerdörfer", defer=True)


async def setup(bot):
    await bot.add_cog(Villages(bot))
