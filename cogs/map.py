import concurrent.futures

from PIL import Image, ImageFont, ImageDraw
from discord.ext import commands
from colour import Color
from load import load
import numpy as np
import functools
import discord
import io


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

    def watermark(self, image):
        with Image.new('RGBA', image.size, (255, 255, 255, 0)) as watermark:
            board = ImageDraw.Draw(watermark)
            font = ImageFont.truetype(f'{load.data_path}/water.otf', 75)
            position = image.size[0] - 200, image.size[1] - 116
            board.text(position, "dsBot", (255, 255, 255, 50), font)
            image.paste(watermark, mask=watermark)

    def label_map(self, image, village_cache, bounds):
        reservation = []
        font_size = int(self.max_font_size * (bounds[2] - bounds[0] - 250) / self.high)
        most_villages = len(sorted(village_cache.items(), key=lambda l: len(l[1]))[-1][1])
        for tribe, villages in village_cache.items():
            if not villages:
                continue

            # double textsize for improved quality = doubled coords for right position
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
                collision = set([l[1] for l in shared])
                if min(area, key=lambda c: c[1]) in shared:
                    position = y, x + len(collision)
                else:
                    position = y, x - len(collision)

            # draw title and shadow / index tribe color
            image.text([position[0] + 6, position[1] + 6], tribe.tag, (0, 0, 0, 255), font)
            image.text(position, tribe.tag, tuple(tribe.color + [255]), font)

            reservation.extend(area)

    def create_basic_map(self, world_villages, tribes, players):
        image = np.array(self.img)
        village_cache = {t: [] for t in tribes.values()}
        brown, grey = load.colors.vil_brown, load.colors.bb_grey
        bounds = self.get_bounds(world_villages)

        # create overlay image for highlighting
        overlay = np.zeros((image.shape[0], image.shape[1], 4), dtype='uint8')

        for vil in world_villages:

            if not self.outta_bounds(vil):
                continue

            if vil.player:
                if vil.player in players:
                    player = players[vil.player]
                    tribe = tribes[player.tribe_id]
                    color = tribe.color
                    overlay[vil.y - 6:vil.y + 10, vil.x - 6:vil.x + 10] = color + [75]
                    village_cache[tribe].append([vil.y, vil.x])

                else:
                    color = brown
            else:
                color = grey

            image[vil.y: vil.y + 4, vil.x: vil.x + 4] = color

        # append highligh overlay to base image
        background = Image.fromarray(image)
        with Image.fromarray(overlay) as foreground:
            background.paste(foreground, mask=foreground)

        # create legacy which is double in size for improved text quality
        if tribes:
            with Image.new('RGBA', (4501, 4501), (255, 255, 255, 0)) as legacy:
                draw = ImageDraw.Draw(legacy)
                self.label_map(draw, village_cache, bounds)
                legacy = legacy.resize(background.size, Image.LANCZOS)
                background.paste(legacy, mask=legacy)
                legacy.close()

        result = background.crop(bounds)
        background.close()

        self.watermark(result)
        return result

    def create_bash_map(self, all_villages, player, state):
        top = sorted(player.values(), key=lambda p: getattr(p, state))
        top_bash = int(sum([getattr(p, state) for p in top][-25:]) / 25)

        first = list(self.white.range_to(self.yellow, 26))
        second = list(self.yellow.range_to(self.red, 25))
        color_scheme = self.convert_to_255(first[:-1] + second)
        percentage = {}
        for pl in player.values():
            bash = getattr(pl, state)
            per = int((bash / top_bash) * len(color_scheme))
            if per > 49:
                per = 49
            elif per > 0:
                per -= 1

            percentage[pl.id] = per

        image = np.array(self.img)
        for vil in all_villages:

            per = percentage.get(vil.player)
            if per is None:
                color = load.colors.bb_grey
            else:
                color = color_scheme[per]

            image[vil.y: vil.y + 4, vil.x: vil.x + 4] = color

        with Image.fromarray(image) as background:
            bounds = self.get_bounds(all_villages)
            result = background.crop(bounds)
            self.watermark(result)

        return result

    async def create_diplomacy_map(self, tribes, conquers):
        pass

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

    @commands.command(name="bashmap")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def bashmap_(self, ctx, bashstate="all_bash"):

        cache = await load.fetch_all(ctx.world)
        players = {pl.id: pl for pl in cache}
        all_villages = await load.fetch_all(ctx.world, "map")

        args = (all_villages, players, bashstate)
        image = await self.bot.execute(self.create_bash_map, *args)

        with io.BytesIO() as file:
            image.save(file, "png", quality=100)
            image.close()
            file.seek(0)
            await ctx.send(file=discord.File(file, "map.png"))


def setup(bot):
    bot.add_cog(Map(bot))
