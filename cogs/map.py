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
        self.image = Image.open(f"{load.data_path}/map.png")

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

    def create_basic_map(self, world_villages, tribes, players):

        image = np.array(self.image)
        colors = load.colors.top()

        tribe_cache = []
        village_cache = {t.id: [] for t in tribes.values()}
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

                    if tribe not in tribe_cache:
                        tribe_cache.append(tribe)

                    index = tribe_cache.index(tribe)
                    color = colors[index]

                    overlay[vil.y - 6:vil.y + 10, vil.x - 6:vil.x + 10] = color + [75]

                    village_cache[player.tribe_id].append([vil.y, vil.x])

                else:
                    color = brown
            else:
                color = grey

            image[vil.y: vil.y + 4, vil.x: vil.x + 4] = color

        # append highligh overlay to base image
        background = Image.fromarray(image)
        foreground = Image.fromarray(overlay)
        background.paste(foreground, mask=foreground)

        legacy = Image.new('RGBA', background.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(legacy)

        # FONTSIZE PROBLEM
        fontsize = int(75 * (bounds[0] / bounds[2] - 0.2))
        font = ImageFont.truetype('data/bebas.ttf', fontsize)

        reservation = []
        for tribe in tribes.values():
            print(tribe.name)
            villages = village_cache[tribe.id]
            if not villages:
                continue

            vil_x = [v[0] for v in villages]
            vil_y = [v[1] for v in villages]
            first, second = min(vil_x), max(vil_x)
            third, fourth = min(vil_y), max(vil_y)

            posi = [int((third + fourth) / 2) - 80, int((first + second) / 2) - 20]
            for pos in reservation:

                for n in range(2):
                    if posi[n] in range(pos[n], pos[n] + 25):
                        posi[n] = pos[n] + 50
                    elif posi[n] in range(pos[n] - 25, pos[n]):
                        posi[n] = pos[n] - 50

            # draw title and shadow / index tribe color
            index = tribe_cache.index(tribe)
            draw.text((posi[0] + 3, posi[1] + 3), tribe.tag, font=font, fill=(0, 0, 0, 255))
            draw.text(tuple(posi), tribe.tag, font=font, fill=tuple(colors[index] + [255]))

            reservation.append(posi)

        # append legace overlay to base image
        background.paste(legacy, mask=legacy)
        return background.crop(bounds)

    def create_bash_map(self, all_villages, player, state):
        top = sorted(player.values(), key=lambda p: getattr(p, state))
        top_bash = int(sum([getattr(p, state) for p in top][-25:]) / 25)

        first = list(self.white.range_to(self.yellow, 11))
        second = list(self.yellow.range_to(self.red, 10))
        color_scheme = self.convert_to_255(first[:-1] + second)

        percentage = {}
        for pl in player.values():
            bash = getattr(pl, state)
            per = int((bash / top_bash) * len(color_scheme))
            if per > 19:
                per = 19
            elif per > 0:
                per -= 1

            percentage[pl.id] = per

        image = np.array(self.image)
        for vil in all_villages:

            per = percentage.get(vil.player)
            if per is None:
                color = load.colors.bb_grey
            else:
                color = color_scheme[per]

            image[vil.y: vil.y + 4, vil.x: vil.x + 4] = color

        background = Image.fromarray(image)
        bounds = self.get_bounds(all_villages)
        return background.crop(bounds)

    async def create_diplomacy_map(self, tribes, conquers):
        pass

    @commands.command(name="map", aliases=["karte"])
    async def map_(self, ctx, *tribe_names):
        if not tribe_names:
            tribes = await load.fetch_top(ctx.world, "tribe")
        else:
            tribes = await load.fetch_bulk(ctx.world, tribe_names, "tribe", name=True)

        tribes = {tribe.id: tribe for tribe in tribes}
        result = await load.fetch_tribe_member(ctx.world, tribes.keys())
        all_villages = await load.fetch_all(ctx.world, "map")
        players = {pl.id: pl for pl in result}

        func = functools.partial(self.create_basic_map, all_villages, tribes, players)
        image = await self.bot.loop.run_in_executor(None, func)
        file = io.BytesIO()
        image.save(file, "png", quality=100)
        file.seek(0)
        await ctx.send(file=discord.File(file, "map.png"))

    @commands.command(name="bashmap")
    async def bashmap_(self, ctx, bashstate="all_bash"):

        cache = await load.fetch_all(ctx.world)
        players = {pl.id: pl for pl in cache}
        all_villages = await load.fetch_all(ctx.world, "map")

        func = functools.partial(self.create_bash_map, all_villages, players, bashstate)
        image = await self.bot.loop.run_in_executor(None, func)
        file = io.BytesIO()
        image.save(file, "png", quality=100)
        file.seek(0)
        await ctx.send(file=discord.File(file, "map.png"))


def setup(bot):
    bot.add_cog(Map(bot))
