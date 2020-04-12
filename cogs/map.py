from utils import World, DSColor, MapVillage, error_embed, silencer
from PIL import Image, ImageFont, ImageDraw
from discord.ext import commands
import numpy as np
import datetime
import discord
import asyncio
import io
import re


class Map(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.low = 0
        self.high = 3001
        self.space = 20
        self.cache = {}
        self.map_cache = {}
        self.colors = DSColor()
        self.max_font_size = 300
        self.img = Image.open(f"{self.bot.data_path}/map.png")
        self.default = [0, "500|500", [], [], 0, True]
        self.menue_icons = [
            '<:center:672875546773946369>',
            '<:dsmap:672912316240756767>',
            '<:friend:672875516117778503>',
            '<:tribe:672862439074693123>',
            '<:report:672862439242465290>',
            '<:old:672862439112441879>',
            '<:button:672910606700904451>',
        ]
        user = commands.BucketType.user
        self._cd = commands.CooldownMapping.from_cooldown(1.0, 60.0, user)
        self.bot.loop.create_task(self.map_cleanup())

    async def cog_check(self, ctx):
        bucket = self._cd.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()

        if retry_after:
            raise commands.CommandOnCooldown(self._cd, retry_after)
        else:
            return True

    # current workaround since library update will support that with tasks in short future
    def get_seconds(self, reverse=False, only=0):
        now = datetime.datetime.now()
        hours = -1 if reverse else 1
        clean = now + datetime.timedelta(hours=hours + only)
        goal_time = clean.replace(minute=0, second=0, microsecond=0)
        start_time = now.replace(microsecond=0)
        if reverse:
            goal_time, start_time = start_time, goal_time
        goal = (goal_time - start_time).seconds
        return goal if not only else start_time.timestamp()

    async def map_cleanup(self):
        seconds = self.get_seconds()
        await asyncio.sleep(seconds + 60)

        try:
            while self.bot.is_closed():
                self.map_cache.clear()
                seconds = self.get_seconds()
                await asyncio.sleep(seconds + 60)

        except Exception as error:
            print(f"MAP CACHE {error}")

    async def timeout(self, cache, user_id, time):
        current = self.cache.get(user_id)
        if current is False:
            return

        if current['ctx'] != cache['ctx']:
            return

        embed = cache['msg'].embeds[0]
        embed.title = f"**Timeout:** Zeitüberschreitung({time}s)"
        await cache['msg'].edit(embed=embed)
        await silencer(cache['msg'].clear_reactions())
        self.cache.pop(user_id)

    def convert_to_255(self, iterable):
        result = []
        for color in iterable:
            rgb = []
            for v in color.rgb:
                rgb.append(int(v * 255))
            result.append(rgb)
        return result

    def get_bounds(self, villages):
        x_coords = [v.x for v in villages if self.low < v.x < self.high if v.rank != 22]
        y_coords = [v.y for v in villages if self.low < v.y < self.high if v.rank != 22]
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

    def create_base(self, villages, zoom=0, center=(500, 500)):
        bounds = self.get_bounds(villages)

        if zoom:
            # 1, 2, 3, 4, 5 | 80% ,65%, 50%, 35% / 20%
            shell = {'id': None, 'player': None, 'x': center[0], 'y': center[1], 'rank': None}
            percentage = ((5 - zoom) * 20 + (zoom - 1) * 5) / 100
            length = int((bounds[2] - bounds[0]) * percentage / 2)

            vil = MapVillage(shell)
            bounds = [vil.x - length, vil.y - length, vil.x + length, vil.y + length]

        with self.img.copy() as cache:
            img = cache.crop(bounds)
            return np.array(img), bounds[0:2]

    def watermark(self, image):
        watermark = Image.new('RGBA', image.size, (255, 255, 255, 0))
        board = ImageDraw.Draw(watermark)

        percentage = image.size[0] / self.high
        font_size = int(150 * percentage)
        font = ImageFont.truetype(f'{self.bot.data_path}/water.otf', font_size)
        position = image.size[0] - int(400 * percentage), image.size[1] - int(232 * percentage)
        board.text(position, "dsBot", (255, 255, 255, 50), font)

        image.paste(watermark, mask=watermark)
        watermark.close()

    def label_map(self, result, village_cache, zoom=0):
        reservation = []
        font_size = int(self.max_font_size * ((result.size[0] - 50) / self.high))
        most_villages = len(sorted(village_cache.items(), key=lambda l: len(l[1]))[-1][1])

        bound_size = tuple([int(c * 1.5) for c in result.size])
        legacy = Image.new('RGBA', bound_size, (255, 255, 255, 0))
        image = ImageDraw.Draw(legacy)

        for tribe, villages in village_cache.items():
            if not villages:
                continue

            title = tribe.name if tribe.alone else tribe.tag

            vil_x = [int(v[0] * 1.5) for v in villages]
            vil_y = [int(v[1] * 1.5) for v in villages]
            centroid = sum(vil_y) / len(villages), sum(vil_x) / len(villages)

            factor = int((len(villages) / most_villages) * (font_size / 4))
            size = int(font_size - (font_size / 4) + factor + (zoom * 3.5))

            font = ImageFont.truetype(f'{self.bot.data_path}/bebas.ttf', size)
            font_width, font_height = image.textsize(title, font=font)
            position = int(centroid[0] - font_width / 2), int(centroid[1] - font_height / 2)

            area = []
            offset = font.getoffset(title)[1]
            for y in range(position[0], position[0] + font_width):
                for x in range(position[1] + offset, position[1] + font_height):
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
            dist = int((result.size[0] / self.high) * 10 + 1)
            image.text([position[0] + dist, position[1] + dist], title, (0, 0, 0, 255), font)
            image.text(position, title, tuple(tribe.color + [255]), font)

            reservation.extend(area)

        legacy = legacy.resize(result.size, Image.LANCZOS)
        result.paste(legacy, mask=legacy)
        legacy.close()

    def create_basic_map(self, world_villages, tribes, players):
        base, diff = self.create_base(world_villages)
        village_cache = {t: [] for t in tribes.values()}

        # create overlay image for highlighting
        overlay = np.zeros((base.shape[0], base.shape[1], 4), dtype='uint8')

        full_size = diff == [0, 0]
        for vil in world_villages:

            # repositions coords based on base crop
            x, y = vil.reposition(diff)

            if full_size and not self.outta_bounds(vil):
                continue

            player = players.get(vil.player_id)
            if vil.player_id == 0:
                color = self.colors.bb_grey

            elif not player:
                color = self.colors.vil_brown

            else:
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

    def create_custom_map(self, world_villages, tribes, players, cache):
        zoom = cache['values'][0]
        coord = cache['values'][1].split('|')
        center = [int(c) for c in coord]

        base, difference = self.create_base(world_villages, zoom=zoom, center=center)

        overlay = np.zeros((base.shape[0], base.shape[1], 4), dtype='uint8')
        mark, bb = cache['values'][4:6]
        highlight = mark in [1, 2]
        label = mark in [2, 3]

        village_cache = {}

        for vil in world_villages:

            # repositions coords based on base crop
            x, y = vil.reposition(difference)

            if not self.outta_bounds(vil):
                continue

            elif vil.player_id == 0:
                if bb:
                    color = self.colors.bb_grey
                else:
                    continue

            elif vil.player_id not in players:
                color = self.colors.vil_brown

            else:
                player = players[vil.player_id]
                tribe = tribes.get(player.tribe_id)
                if tribe is None:
                    color = player.color
                    tribe = player
                else:
                    color = tribe.color

                if highlight:
                    overlay[y - 6:y + 10, x - 6:x + 10] = color + [75]
                if label:
                    if tribe in village_cache:
                        village_cache[tribe].append([y, x])
                    else:
                        village_cache[tribe] = [[y, x]]

            base[y: y + 4, x: x + 4] = color

        # append highligh overlay to base image
        result = Image.fromarray(base)
        with Image.fromarray(overlay) as foreground:
            result.paste(foreground, mask=foreground)

        # create legacy which is double in size for improved text quality
        if label and village_cache:
            self.label_map(result, village_cache, zoom)

        self.watermark(result)
        return result

    @commands.command(name="map", aliases=["karte"])
    async def map_(self, ctx, *, tribe_names=None):
        await ctx.trigger_typing()

        color_map = []
        if not tribe_names:

            file = self.map_cache.get(ctx.server)
            if file is None:
                tribes = await self.bot.fetch_top(ctx.server, "tribe", till=10)

            else:
                file.seek(0)
                await ctx.send(file=discord.File(file, 'map.png'))
                return

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

            tribes = await self.bot.fetch_bulk(ctx.server, all_tribes, "tribe", name=True)

        if len(color_map) > 20:
            return await ctx.send("Du kannst nur bis zu 20 Stämme/Gruppierungen angeben")

        colors = self.colors.top()
        for tribe in tribes.copy():

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
        result = await self.bot.fetch_tribe_member(ctx.server, tribes.keys())
        all_villages = await self.bot.fetch_all(ctx.server, "map")
        players = {pl.id: pl for pl in result}

        args = (all_villages, tribes, players)
        image = await self.bot.execute(self.create_basic_map, *args)

        file = io.BytesIO()
        image.save(file, "png", quality=100)
        image.close()
        file.seek(0)
        await ctx.send(file=discord.File(file, "map.png"))

        if not tribe_names:
            self.map_cache[ctx.server] = file

    async def update_menue(self, cache, index):
        embed = cache['msg'].embeds[0]
        value = cache['values'][index]
        options = embed.description
        field = options.split("\n")[index]
        old_value = re.findall(r'\[.*\]', field)[0]

        if isinstance(value, bool):
            current_value = "An" if value else "Aus"
        elif isinstance(value, list):
            attr = 'tag' if index == 3 else 'name'
            names = [getattr(o, attr) for o in value]

            current_value = ", ".join(names)

        elif index == 4:
            names = ["Aus", "An", "mit Beschriftung", "nur Beschriftung"]
            current_value = names[value]
        else:
            current_value = str(value)

        new_field = field.replace(old_value, f"[{current_value}]")
        embed.description = options.replace(field, new_field)
        await cache['msg'].edit(embed=embed)

    @commands.Cog.listener()
    async def on_reaction_add(self, *args):
        await self.menue_handler(*args)

    @commands.Cog.listener()
    async def on_reaction_remove(self, *args):
        await self.menue_handler(*args)

    async def menue_handler(self, reaction, user):
        if user == self.bot.user:
            return

        cache = self.cache.get(user.id)
        if not cache:
            return

        elif reaction.message.id != cache['msg'].id:
            return

        try:
            index = self.menue_icons.index(str(reaction.emoji))
            values = cache['values']
            ctx = cache['ctx']
        except ValueError:
            return

        # zoom switch
        if index == 0:
            if values[index] > 4:
                values[index] = 0
            else:
                values[index] += 1

        # player, tribe or center
        elif index in (1, 2, 3):
            if values[index] is False:
                return

            values[index] = False

            listen = self.bot.get_cog('Listen')
            listen.blacklist.append(ctx.author.id)

            if index == 1:
                msg = "**Gebe bitte die gewünschte Koordinate an:**"

            else:
                obj = "Spieler" if index == 2 else "Stämme"
                msg = f"**Gebe jetzt bis zu 10 {obj} an:**\n" \
                      f"(Mit neuer Zeile getrennt | Shift Enter)"

            guide_msg = await ctx.send(msg)

            def check(message):
                return ctx.author == message.author and ctx.channel == message.channel

            try:
                result = await self.bot.wait_for('message', check=check, timeout=300)

                if index == 1:
                    coords = re.findall(r'\d\d\d\|\d\d\d', result.content)
                    if coords:
                        values[index] = coords[0]

                else:
                    iterable = result.content.split("\n")
                    data = await self.bot.fetch_bulk(ctx.server, iterable, index - 2, name=True)
                    values[index] = data[:10]

                if values[index] is False:
                    values[index] = self.default[index]

                listen.blacklist.remove(ctx.author.id)
                await silencer(result.delete())

            except asyncio.TimeoutError:
                await self.timeout(cache, user.id, 300)
                return

            finally:
                await silencer(guide_msg.delete())

        # none, mark, label + mark, label
        elif index == 4:
            if values[index] > 2:
                values[index] = 0
            else:
                values[index] += 1

        # bb switch case
        elif index == 5:
            values[index] = not values[index]

        # map creation
        elif index == 6:
            await ctx.trigger_typing()
            p_list, t_list = cache['values'][2:4]

            # short fix if ok while expecting tribe/player
            p_list = p_list or []
            t_list = t_list or []

            idc = [tribe.id for tribe in t_list]
            members = await self.bot.fetch_tribe_member(ctx.server, idc)
            colors = self.colors.top()

            players = {player.id: player for player in p_list}
            tribes = {tribe.id: tribe for tribe in t_list}

            colorable = p_list + t_list

            for member in members:
                if member.id not in players:
                    players[member.id] = member

            for dsobj in colorable:
                if dsobj not in members:
                    dsobj.color = colors.pop(0)

            village = await self.bot.fetch_all(ctx.server, 'map')
            args = (village, tribes, players, cache)
            image = await self.bot.execute(self.create_custom_map, *args)

            with io.BytesIO() as file:
                image.save(file, "png", quality=100)
                image.close()
                file.seek(0)
                await ctx.send(file=discord.File(file, "map.png"))

            return self.cache.pop(user.id)

        await self.update_menue(cache, index)

    @commands.command(name="custom")
    async def custom_(self, ctx, world: World = None):
        if ctx.author.id in self.cache:
            msg = "Du hast noch eine offene Karte"
            return await ctx.send(embed=error_embed(msg))
        else:
            cache = self.cache[ctx.author.id] = {}

        if world:
            ctx.world = world

        options = []
        for icon, value in self.bot.msg['mapOptions'].items():
            title = value['title']
            default = value.get('default')
            if default is not None:
                message = f"{icon} {title} `[{default}]`"
            else:
                message = f"\n{icon} {title}"
            options.append(message)

        embed = discord.Embed(title="Custom Map Tool", description="\n".join(options))
        example = f"Für eine genaue Erklärung und Beispiele: {ctx.prefix}help custom"
        embed.set_footer(text=example)
        builder = await ctx.send(embed=embed)

        for icon in self.menue_icons:
            await builder.add_reaction(icon)

        default = {'msg': builder, 'ctx': ctx, 'values': self.default.copy()}
        cache.update(default)

        await asyncio.sleep(600)

        current = self.cache.get(ctx.author.id)
        if current is None:
            return

        if ctx.message.id == current['ctx'].message.id:
            await self.timeout(cache, ctx.author.id, 600)


def setup(bot):
    bot.add_cog(Map(bot))
