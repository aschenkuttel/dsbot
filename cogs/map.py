from utils import WorldConverter, DSColor, MapVillage, silencer, keyword
from PIL import Image, ImageFont, ImageDraw
from discord.ext import commands
import numpy as np
import discord
import asyncio
import io
import re


class MapMenue:
    icons = [
        '<:center:672875546773946369>',
        '<:dsmap:672912316240756767>',
        '<:friend:672875516117778503>',
        '<:tribe:672862439074693123>',
        '<:report:672862439242465290>',
        '<:old:672862439112441879>',
        '<:button:672910606700904451>',
    ]

    def __init__(self, ctx, message):
        self.ctx = ctx
        self.message = message
        self.zoom = 0
        self.center = "500|500"
        self.tribes = []
        self.player = []
        self.highlight = 0
        self.bb = True

    def change(self, emoji):
        try:
            index = self.icons.index(emoji)
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


class Map(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.low = 0
        self.high = 3001
        self.space = 20
        self.map_cache = {}
        self.custom_cache = {}
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

    # async def cog_check(self, ctx):
    #     bucket = self._cd.get_bucket(ctx.message)
    #     retry_after = bucket.update_rate_limit()
    #
    #     if retry_after:
    #         raise commands.CommandOnCooldown(self._cd, retry_after)
    #     else:
    #         return True

    async def timeout(self, cache, user_id, time):
        current = self.custom_cache.get(user_id)
        if current is False:
            return

        if current['ctx'] != cache['ctx']:
            return

        embed = cache['msg'].embeds[0]
        embed.title = f"**Timeout:** Zeitüberschreitung({time}s)"
        await silencer(cache['msg'].edit(embed=embed))
        await silencer(cache['msg'].clear_reactions())
        self.custom_cache.pop(user_id)

    def convert_to_255(self, iterable):
        result = []
        for color in iterable:
            rgb = []
            for v in color.rgb:
                rgb.append(int(v * 255))
            result.append(rgb)
        return result

    def overlap(self, reservation, x, y, width, height):
        zone = [(x, y), (x + width, y + height)]

        for area in reservation:
            if zone[0][0] > area[1][0] or area[0][0] > zone[1][0]:
                continue
            elif zone[0][1] > area[1][1] or area[0][1] > zone[1][1]:
                continue
            else:
                return True
        else:
            return zone

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

    def in_bounds(self, vil):
        if not self.low <= vil.x < self.high:
            return False
        elif not self.low <= vil.y < self.high:
            return False
        else:
            return True

    def create_base(self, villages, **kwargs):
        bounds = self.get_bounds(villages)
        zoom = kwargs.get('zoom', 0)
        center = kwargs.get('center', (500, 500))

        if zoom:
            # 1, 2, 3, 4, 5 | 80% ,65%, 50%, 35%, 20%
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

    def label_map(self, result, village_cache, zoom=0, player=False):
        reservation = []
        font_size = int(self.max_font_size * ((result.size[0] - 50) / self.high))

        if player:
            font_size *= 0.42

        most_villages = len(sorted(village_cache.items(), key=lambda l: len(l[1]))[-1][1])

        bound_size = tuple([int(c * 1.5) for c in result.size])
        legacy = Image.new('RGBA', bound_size, (255, 255, 255, 0))
        image = ImageDraw.Draw(legacy)

        for dsobj, villages in village_cache.items():
            if not villages:
                continue

            vil_x = [int(v[0] * 1.5) for v in villages]
            vil_y = [int(v[1] * 1.5) for v in villages]
            centroid = sum(vil_y) / len(villages), sum(vil_x) / len(villages)

            factor = int((len(villages) / most_villages) * (font_size / 4))
            size = int(font_size - (font_size / 4) + factor + (zoom * 3.5))

            font = ImageFont.truetype(f'{self.bot.data_path}/bebas.ttf', size)
            font_width, font_height = image.textsize(str(dsobj), font=font)
            position = [int(centroid[0] - font_width / 2), int(centroid[1] - font_height / 2)]

            while True:
                args = [*position, font_width, font_height]
                response = self.overlap(reservation, *args)
                if response is True:
                    position[1] -= 5
                else:
                    reservation.append(response)
                    break

            # draw title and shadow / index tribe color
            dist = int((result.size[0] / self.high) * 10 + 1)
            image.text([position[0] + dist, position[1] + dist], str(dsobj), (0, 0, 0, 255), font)
            image.text(position, str(dsobj), tuple(dsobj.color + [255]), font)

        legacy = legacy.resize(result.size, Image.LANCZOS)
        result.paste(legacy, mask=legacy)
        legacy.close()

    def draw_map(self, all_villages, tribes, players, **options):
        base, difference = self.create_base(all_villages, **options)

        village_cache = {}
        for dsobj in list(tribes.values()) + list(players.values()):
            village_cache[dsobj] = []

        # create overlay image for highlighting
        overlay = np.zeros((base.shape[0], base.shape[1], 4), dtype='uint8')

        label = options.get('label')
        # full_size = difference == [0, 0]
        for vil in all_villages:

            # repositions coords based on base crop
            x, y = vil.reposition(difference)

            if not self.in_bounds(vil):
                continue

            player = players.get(vil.player_id)
            if vil.player_id == 0:
                color = self.colors.bb_grey

            elif not player:
                color = self.colors.vil_brown

            else:

                tribe = tribes.get(player.tribe_id)
                if tribe is None or hasattr(player, 'color'):
                    color = player.color
                    tribe = player
                else:
                    color = tribe.color

                overlay[y - 6:y + 10, x - 6:x + 10] = color + [75]
                village_cache[tribe].append([y, x])

            base[y: y + 4, x: x + 4] = color

        # append highligh overlay to base image
        result = Image.fromarray(base)
        with Image.fromarray(overlay) as foreground:
            result.paste(foreground, mask=foreground)

        # create legacy which is double in size for improved text quality
        if label is True and tribes or label is True and players:
            self.label_map(result, village_cache, options['zoom'], player=not tribes)

        self.watermark(result)
        return result

    # def create_basic_map(self, world_villages, tribes, players):
    #     base, diff = self.create_base(world_villages)
    #     village_cache = {t: [] for t in tribes.values()}
    #
    #     # create overlay image for highlighting
    #     overlay = np.zeros((base.shape[0], base.shape[1], 4), dtype='uint8')
    #
    #     full_size = diff == [0, 0]
    #     for vil in world_villages:
    #
    #         # repositions coords based on base crop
    #         x, y = vil.reposition(diff)
    #
    #         if full_size and not self.outta_bounds(vil):
    #             continue
    #
    #         player = players.get(vil.player_id)
    #         if vil.player_id == 0:
    #             color = self.colors.bb_grey
    #
    #         elif not player:
    #             color = self.colors.vil_brown
    #
    #         else:
    #             tribe = tribes[player.tribe_id]
    #             color = tribe.color
    #             overlay[y - 6:y + 10, x - 6:x + 10] = color + [75]
    #             village_cache[tribe].append([y, x])
    #
    #         base[y: y + 4, x: x + 4] = color
    #
    #     # append highligh overlay to base image
    #     result = Image.fromarray(base)
    #     with Image.fromarray(overlay) as foreground:
    #         result.paste(foreground, mask=foreground)
    #
    #     # create legacy which is double in size for improved text quality
    #     if tribes:
    #         self.label_map(result, village_cache)
    #
    #     self.watermark(result)
    #     return result
    #
    # def create_custom_map(self, world_villages, tribes, players, cache):
    #     zoom = cache['values'][0]
    #     coord = cache['values'][1].split('|')
    #     center = [int(c) for c in coord]
    #
    #     base, difference = self.create_base(world_villages, zoom=zoom, center=center)
    #     print(difference)
    #
    #     overlay = np.zeros((base.shape[0], base.shape[1], 4), dtype='uint8')
    #     mark, bb = cache['values'][4:6]
    #     highlight = mark in [1, 2]
    #     label = mark in [2, 3]
    #
    #     village_cache = {}
    #
    #     for vil in world_villages:
    #
    #         # repositions coords based on base crop
    #         x, y = vil.reposition(difference)
    #
    #         if not self.outta_bounds(vil):
    #             continue
    #
    #         elif vil.player_id == 0:
    #             if bb:
    #                 color = self.colors.bb_grey
    #             else:
    #                 continue
    #
    #         elif vil.player_id not in players:
    #             color = self.colors.vil_brown
    #
    #         else:
    #             player = players[vil.player_id]
    #             tribe = tribes.get(player.tribe_id)
    #             if tribe is None:
    #                 color = player.color
    #                 tribe = player
    #             else:
    #                 color = tribe.color
    #
    #             if highlight:
    #                 overlay[y - 6:y + 10, x - 6:x + 10] = color + [75]
    #             if label:
    #                 if tribe in village_cache:
    #                     village_cache[tribe].append([y, x])
    #                 else:
    #                     village_cache[tribe] = [[y, x]]
    #
    #         base[y: y + 4, x: x + 4] = color
    #
    #     # append highligh overlay to base image
    #     result = Image.fromarray(base)
    #     with Image.fromarray(overlay) as foreground:
    #         result.paste(foreground, mask=foreground)
    #
    #     # create legacy which is double in size for improved text quality
    #     if label and village_cache:
    #         self.label_map(result, village_cache, zoom)
    #
    #     self.watermark(result)
    #     return result

    @commands.command(name="map")
    async def map_(self, ctx, *, arguments=None):
        options = {'zoom': [0, 5], 'top': [5, 10, 20], 'player': False, 'label': True}
        tribe_names, zoom, top, player, label = keyword(arguments, strip=True, **options)

        await ctx.trigger_typing()

        color_map = []
        if not tribe_names:

            file = self.map_cache.get(ctx.server)
            if arguments is None and file is not None:
                file.seek(0)
                await ctx.send(file=discord.File(file, 'map.png'))
                return

            ds_type = "player" if player else "tribe"
            ds_objects = await self.bot.fetch_top(ctx.server, ds_type, till=top.value)

        else:
            all_tribes = []
            raw_fractions = tribe_names.split('&')
            fractions = [f for f in raw_fractions if f]

            for index, team in enumerate(fractions):
                names = []
                quoted = re.findall(r'\"(.+)\"', team)
                for res in quoted:
                    team = team.replace(f'"{res}"', ' ')
                    names.append(res)

                for name in team.split():
                    if not name:
                        continue
                    names.append(name)

                all_tribes.extend(names)

                if len(fractions) == 1:
                    color_map.extend([obj] for obj in names)
                else:
                    color_map.append(names)

            ds_objects = await self.bot.fetch_bulk(ctx.server, all_tribes, 1, name=True)

        if len(color_map) > 20:
            return await ctx.send("Du kannst nur bis zu 20 Stämme/Gruppierungen angeben")

        colors = self.colors.top()
        for tribe in ds_objects.copy():
            if not tribe_names:
                tribe.color = colors.pop(0)
                continue

            for index, group in enumerate(color_map):
                names = [t.lower() for t in group]
                if tribe.tag.lower() in names:
                    tribe.color = colors[index]
                    break

            else:
                print("triggered")
                ds_objects.remove(tribe)

        all_villages = await self.bot.fetch_all(ctx.server, "map")
        if not all_villages:
            msg = "Auf der Welt gibt es noch keine Dörfer :/"
            return await ctx.send(msg)

        ds_dict = {dsobj.id: dsobj for dsobj in ds_objects}
        if player:
            args = (all_villages, {}, ds_dict)

        else:
            result = await self.bot.fetch_tribe_member(ctx.server, list(ds_dict))
            players = {pl.id: pl for pl in result}
            args = (all_villages, ds_dict, players)

        kwargs = {'zoom': zoom.value, 'label': label.value}
        image = await self.bot.execute(self.draw_map, *args, **kwargs)

        file = io.BytesIO()
        image.save(file, "png", quality=100)
        image.close()
        file.seek(0)

        await ctx.send(file=discord.File(file, "map.png"))

        if arguments is None:
            self.map_cache[ctx.server] = file

    async def update_menue(self, cache, index):
        embed = cache['msg'].embeds[0]
        value = cache['values'][index]
        options = embed.description
        field = options.split("\n")[index]
        old_value = re.findall(r'\[.*]', field)[0]

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

        cache = self.custom_cache.get(user.id)
        if cache is None:
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

            for member in members:
                if member.id not in players:
                    players[member.id] = member

            for dsobj in t_list + p_list:
                if dsobj not in members:
                    dsobj.color = colors.pop(0)

            village = await self.bot.fetch_all(ctx.server, 'map')
            args = (village, tribes, players)

            coord = cache['values'][1].split('|')
            center = [int(c) for c in coord]
            label = cache['values'][4] in [2, 3]
            kwargs = {'zoom': cache['values'][0], 'center': center, 'label': label}
            image = await self.bot.execute(self.draw_map, *args, **kwargs)

            with io.BytesIO() as file:
                image.save(file, "png", quality=100)
                image.close()
                file.seek(0)
                await ctx.send(file=discord.File(file, "map.png"))

            return self.custom_cache.pop(user.id)

        await self.update_menue(cache, index)

    @commands.command(name="custom")
    async def custom_(self, ctx, world: WorldConverter = None):
        if ctx.author.id in self.custom_cache:
            msg = "Du hast noch eine offene Karte"
            return await ctx.send(msg)
        else:
            cache = self.custom_cache[ctx.author.id] = {}

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

        current = self.custom_cache.get(ctx.author.id)
        if current is None:
            return

        if ctx.message.id == current['ctx'].message.id:
            await self.timeout(cache, ctx.author.id, 600)


def setup(bot):
    bot.add_cog(Map(bot))
