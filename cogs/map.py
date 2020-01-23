from PIL import Image, ImageFont, ImageDraw
from discord.ext import commands
from colour import Color
from load import load
import numpy as np
import discord
import io
from utils import MapVillage


class Map(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.low = 0
        self.high = 3001
        self.space = 20
        self.white = Color('white')
        self.yellow = Color('yellow')
        self.red = Color('red')
        self.max_font_size = 300
        self.img = Image.open(f"{load.data_path}/map.png")
        self.conquer_cache = {}
        user = commands.BucketType.user
        self._cd = commands.CooldownMapping.from_cooldown(1.0, 60.0, user)

    async def cog_check(self, ctx):
        bucket = self._cd.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()

        if retry_after:
            raise commands.CommandOnCooldown(self._cd, retry_after)
        else:
            return True

    async def map_creation(self):

        for world in load.worlds:

            tribes = await load.fetch_top(world, "tribe", till=10)

            colors = load.colors.top().copy()
            for tribe in tribes:
                tribe.color = colors.pop(0)

            tribes = {tribe.id: tribe for tribe in tribes}
            result = await load.fetch_tribe_member(world, tribes.keys())
            all_villages = await load.fetch_all(world, "map")
            players = {pl.id: pl for pl in result}

            history = {}
            for day in range(20):
                query = f'SELECT * FROM village{day + 1} WHERE world = $1'
                async with load.pool.acquire() as conn:
                    res = await conn.fetch(query, world)
                    old_villages = {rec[1]: MapVillage(rec) for rec in res}

                    another = f'SELECT * FROM player{day + 1} WHERE world = $1'
                    res = await conn.fetch(another, world)
                    old_player = {rec[1]: rec for rec in res}

                history[day + 1] = {'village': old_villages, 'player': old_player}

            args = (all_villages, tribes, players, history)
            image = await self.bot.execute(self.create_conquer_map, *args)

            file = io.BytesIO()
            image.save(file, "png", quality=100)
            image.close()
            file.seek(0)

            self.conquer_cache[world] = file

    def convert_to_255(self, iterable):
        result = []
        for color in iterable:
            rgb = []
            for v in color.rgb:
                rgb.append(int(v * 255))
            result.append(rgb)
        return result

    def get_bounds(self, villages):
        x_coords = [v.x for v in villages if self.low < v.x < self.high]
        y_coords = [v.y for v in villages if self.low < v.y < self.high]
        first, second = min(x_coords), min(y_coords)
        third, fourth = max(x_coords), max(y_coords)
        a1 = self.low if (first - self.space) < self.low else first - self.space
        a2 = self.low if (second - self.space) < self.low else second - self.space
        b1 = self.high if (third + self.space) > self.high else third + self.space
        b2 = self.high if (fourth + self.space) > self.high else fourth + self.space
        return [a1, a2, b1, b2]

    def outta_bounds(self, vil):
        if not self.low <= vil.x < self.high:
            return False
        if not self.low <= vil.y < self.high:
            return False
        return True

    def create_base(self, villages):
        bounds = self.get_bounds(villages)
        with self.img.copy() as cache:
            img = cache.crop(bounds)
            return np.array(img), bounds[0:2]

    def watermark(self, image):
        watermark = Image.new('RGBA', image.size, (255, 255, 255, 0))
        board = ImageDraw.Draw(watermark)

        font = ImageFont.truetype(f'{load.data_path}/water.otf', 75)
        position = image.size[0] - 200, image.size[1] - 116
        board.text(position, "dsBot", (255, 255, 255, 50), font)

        image.paste(watermark, mask=watermark)
        watermark.close()

    def label_map(self, result, village_cache):
        reservation = []
        font_size = int(self.max_font_size * (result.size[0] - 250) / self.high)
        most_villages = len(sorted(village_cache.items(), key=lambda l: len(l[1]))[-1][1])

        bound_size = tuple([int(c * 1.5) for c in result.size])
        legacy = Image.new('RGBA', bound_size, (255, 255, 255, 0))
        image = ImageDraw.Draw(legacy)

        for tribe, villages in village_cache.items():
            if not villages:
                continue

            # 1,5 bigger textsize for improved quality = 1,5 * coords for right position
            vil_x = [int(v[0] * 1.5) for v in villages]
            vil_y = [int(v[1] * 1.5) for v in villages]
            centroid = sum(vil_y) / len(villages), sum(vil_x) / len(villages)

            # font creation
            factor = (len(villages) / most_villages) * (font_size / 3)
            size = int(font_size - (font_size / 3) + factor)
            font = ImageFont.truetype(f'{load.data_path}/bebas.ttf', size)
            font_widht, font_height = image.textsize(tribe.tag, font=font)
            position = int(centroid[0] - font_widht / 2), int(centroid[1] - font_height / 2)

            area = []
            space = int(centroid[0] - font_widht / 2), int(centroid[1] - font_height / 2)
            for y in range(space[0], space[0] + font_widht):
                for x in range(space[1], space[1] + font_height):
                    area.append((y, x))

            y, x = position
            shared = set(reservation).intersection(area)
            if shared:
                collision = set([pl[1] for pl in shared])
                if min(area, key=lambda c: c[1]) in shared:
                    position = y, x + len(collision)
                else:
                    position = y, x - len(collision)

            # draw title and shadow / index tribe color
            image.text([position[0] + 6, position[1] + 6], tribe.tag, (0, 0, 0, 255), font)
            image.text(position, tribe.tag, tuple(tribe.color + [255]), font)

            reservation.extend(area)

        legacy = legacy.resize(result.size, Image.LANCZOS)
        result.paste(legacy, mask=legacy)
        legacy.close()

    def create_basic_map(self, world_villages, tribes, players):
        base, difference = self.create_base(world_villages)
        village_cache = {t: [] for t in tribes.values()}

        # create overlay image for highlighting
        overlay = np.zeros((base.shape[0], base.shape[1], 4), dtype='uint8')

        for vil in world_villages:

            # repositions coords based on base crop
            x, y = vil.reposition(difference)

            if not self.outta_bounds(vil):
                continue

            elif vil.player == 0:
                color = load.colors.bb_grey

            elif vil.player not in players:
                color = load.colors.vil_brown

            else:
                player = players[vil.player]
                tribe = tribes[player.tribe_id]
                color = tribe.color
                overlay[y - 6:y + 10, x - 6:x + 10] = color + [75]
                village_cache[tribe].append([y, x])

            base[y: y + 4, x: x + 4] = color

        # append highligh overlay to base image
        result = Image.fromarray(base)
        with Image.fromarray(overlay) as foreground:
            result.paste(foreground, mask=foreground)

        # create legacy which is double in size for improved text quality
        if tribes:
            self.label_map(result, village_cache)

        self.watermark(result)
        return result

    def create_conquer_map(self, new_villages, tribes, newbies, history):
        base, difference = self.create_base(new_villages)
        overlay = np.zeros((base.shape[0], base.shape[1], 4), dtype='uint8')
        highlight = np.zeros((base.shape[0], base.shape[1], 4), dtype='uint8')

        old_tribe_tree = {}
        for day in history:
            old_tribe_tree[day] = {}
            for player in history[day]['player'].values():
                trid = player['tribe_id']
                if trid not in tribes:
                    continue
                if trid not in old_tribe_tree[day]:
                    old_tribe_tree[day][trid] = [player['id']]
                else:
                    old_tribe_tree[day][trid].append(player['id'])

        for vil in new_villages:

            # repositions coords based on base crop
            x, y = vil.reposition(difference)

            opac = [111]
            if not self.outta_bounds(vil):
                continue

            if vil.player == 0:
                color = load.colors.bb_grey

            elif vil.player not in newbies:
                color = load.colors.vil_brown

            else:
                player = newbies[vil.player]
                tribe = tribes[player.tribe_id]
                color = tribe.color

                for day in history:

                    old = history[day]['village'].get(vil.id)
                    if old and old.player != vil.player:

                        for idc, pids in old_tribe_tree[day].items():
                            if player.tribe_id == idc:
                                continue
                            if old.player in pids:
                                opac = [255]
                                highlight[y - 6:y + 10, x - 6:x + 10] = color + [100]

            overlay[y: y + 4, x: x + 4] = color + opac

        # append highligh overlay to base image
        result = Image.fromarray(base)
        with Image.fromarray(overlay) as foreground:
            result.paste(foreground, mask=foreground)

        with Image.fromarray(highlight) as ovv:
            result.paste(ovv, mask=ovv)

        self.watermark(result)
        return result

    @commands.command(name="map", aliases=["karte"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def map_(self, ctx, *, tribe_names=None):

        await ctx.trigger_typing()

        color_map = []
        if not tribe_names:
            tribes = await load.fetch_top(ctx.world, "tribe", till=10)
        else:
            all_tribes = []
            fractions = tribe_names.split('&')

            if len(fractions) == 1:
                fractions = fractions[0].split(' ')

            for index, team in enumerate(fractions):

                if not team:
                    continue

                names = team.split(' ')
                color_map.append(names)
                all_tribes.extend(names)

            tribes = await load.fetch_bulk(ctx.world, all_tribes, "tribe", name=True)

        if len(color_map) > 10:
            return await ctx.send("Du kannst nur bis zu 10 Stämme angeben")

        colors = load.colors.top().copy()
        for tribe in tribes:
            for index, group in enumerate(color_map):
                names = [t.lower() for t in group]
                if tribe.tag.lower() in names:
                    tribe.color = colors[index]
                    break
            else:
                if tribe_names:
                    tribes.remove(tribe)
                else:
                    tribe.color = colors.pop(0)

        tribes = {tribe.id: tribe for tribe in tribes}
        result = await load.fetch_tribe_member(ctx.world, tribes.keys())
        all_villages = await load.fetch_all(ctx.world, "map")
        players = {pl.id: pl for pl in result}

        args = (all_villages, tribes, players)
        image = await self.bot.execute(self.create_basic_map, *args)

        with io.BytesIO() as file:
            image.save(file, "png", quality=100)
            image.close()
            file.seek(0)
            await ctx.send(file=discord.File(file, "map.png"))


def setup(bot):
    bot.add_cog(Map(bot))
