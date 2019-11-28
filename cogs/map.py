import io

import discord
from PIL import Image, ImageFont, ImageDraw
from discord.ext import commands
from load import load
import numpy as np
import functools


class Map(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def create_basic_map(self, world_villages, tribes, players):
        image = np.array(Image.open(f"{load.data_loc}map.png"))

        low, high = 0, 3001
        colors = load.colors.top()
        map_space = 20

        tribe_cache = []
        village_cache = {t.id: [] for t in tribes.values()}
        brown, grey = load.colors.vil_brown, load.colors.bb_grey

        # compute image boundaries with safe space
        x_coords = [v.x for v in world_villages if low < v.x < high]
        y_coords = [v.y for v in world_villages if low < v.y < high]
        first, second = min(x_coords), min(y_coords)
        third, fourth = max(x_coords), max(y_coords)
        a1 = low if (first - map_space) < low else first - map_space
        a2 = low if (second - map_space) < low else second - map_space
        b1 = high if (third + map_space) > high else third + map_space
        b2 = high if (fourth + map_space) > high else fourth + map_space
        bounds = [a1, a2, b1, b2]

        # create overlay image for highlighting
        overlay = np.zeros((image.shape[0], image.shape[1], 4), dtype='uint8')

        for vil in world_villages:

            if not low <= vil.x < high:
                continue

            if not low <= vil.y < high:
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

        fontsize = int(75 * (third / high - 0.2))
        font = ImageFont.truetype('verdanab', fontsize)

        reservation = []
        for tribe in tribes.values():
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


def setup(bot):
    bot.add_cog(Map(bot))
