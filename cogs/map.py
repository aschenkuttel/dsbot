from PIL import Image, ImageFont, ImageDraw
from datetime import datetime, timedelta
from discord.ext import commands
from zipfile import ZipFile
from utils import keyword
import numpy as np
import discord
import asyncio
import utils
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

    def __init__(self, ctx):
        self.ctx = ctx
        self.bot = ctx.bot
        self.message = None
        self.embed = None
        self.zoom = 0
        self.center = "500|500"
        self.tribes = []
        self.player = []
        self.highlight = 0
        self.bb = True
        self.color = utils.DSColor()
        self.dead = False

    async def setup(self, restart=False):
        options = []
        for icon, value in self.ctx.lang.map_menue.items():
            title = value['title']
            default = value.get('default')
            if default is not None:
                message = f"{icon} {title} `[{default}]`"
            else:
                message = f"\n{icon} {title}"
            options.append(message)

        self.embed = discord.Embed(title="Custom Map Tool", description="\n".join(options))
        example = f"Für eine genaue Erklärung und Beispiele: {self.ctx.prefix}help custom"
        self.embed.set_footer(text=example)

        if restart is True:
            for index in range(5):
                self.update_embed(index)

        self.message = await self.ctx.send(embed=self.embed)

        for icon in self.icons:
            await self.message.add_reaction(icon)

    async def reinstall(self, ctx):
        self.dead = False
        self.ctx = ctx
        await self.setup(restart=True)

    async def change(self, emoji):
        try:
            index = self.icons.index(emoji)
        except ValueError:
            return

        # index 0: zoom
        if index == 0:
            if self.zoom == 5:
                self.zoom = 0
            else:
                self.zoom += 1

        # index 1,2,3: center, player, tribe
        elif index in (1, 2, 3):
            name = ('center', 'player', 'tribes')[index - 1]

            if getattr(self, name) is False:
                return
            else:
                setattr(self, name, False)

            listen = self.bot.get_cog('Listen')
            listen.blacklist.append(self.ctx.author.id)

            if index == 1:
                msg = "**Gebe bitte die gewünschte Koordinate an:**"

            else:
                obj = "Spieler" if index == 2 else "Stämme"
                msg = f"**Gebe jetzt bis zu 10 {obj} an:**\n" \
                      f"(Mit neuer Zeile getrennt | Shift Enter)"

            guide_msg = await self.ctx.send(msg)

            def check(m):
                return self.ctx.author == m.author and self.ctx.channel == m.channel

            try:
                result = await self.ctx.bot.wait_for('message', check=check, timeout=300)

                if index == 1:
                    coords = re.findall(r'\d\d\d\|\d\d\d', result.content)
                    self.center = coords[0] if coords else "500|500"

                else:
                    iterable = result.content.split("\n")
                    args = (self.ctx.server, iterable, index - 2)
                    data = await self.bot.fetch_bulk(*args, name=True)
                    setattr(self, name, data[:10])

                listen.blacklist.remove(self.ctx.author.id)
                await utils.silencer(result.delete())

            except asyncio.TimeoutError:
                return

            finally:
                await utils.silencer(guide_msg.delete())

        # index 4 highlight: none, mark, label + mark, label
        elif index == 4:
            if self.highlight == 3:
                self.highlight = 0
            else:
                self.highlight += 1

        # index 5: bb
        elif index == 5:
            self.bb = not self.bb

        # map creation
        elif index == 6:
            await self.ctx.trigger_typing()

            if self.tribes is False:
                self.tribes = []
            if self.player is False:
                self.player = []
            if self.center is False:
                self.center = "500|500"

            idc = [tribe.id for tribe in self.tribes]
            members = await self.bot.fetch_tribe_member(self.ctx.server, idc)
            colors = self.color.top()

            players = {player.id: player for player in self.player}
            tribes = {tribe.id: tribe for tribe in self.tribes}

            for member in members:
                if member.id not in players:
                    players[member.id] = member

            for dsobj in self.tribes + self.player:
                if dsobj not in members:
                    dsobj.color = colors.pop(0)

            village = await self.bot.fetch_all(self.ctx.server, 'map')
            args = (village, tribes, players)

            center = [int(c) for c in self.center.split('|')]
            label = self.highlight in [2, 3]
            kwargs = {'zoom': self.zoom, 'center': center, 'label': label}
            return args, kwargs

        self.update_embed(index)
        await self.message.edit(embed=self.embed)
        return True

    def update_embed(self, index):
        values = [self.zoom, self.center,
                  self.player, self.tribes,
                  self.highlight, self.bb]

        value = values[index]
        options = self.embed.description
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
        self.embed.description = options.replace(field, new_field)


class Map(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.type = 1
        self.minimum_size = 0
        self.maximum_size = 3001
        self.borderspace = 20
        self.top10_cache = {}
        self.menue_cache = {}
        self.bound_cache = {}
        self.colors = utils.DSColor()
        self.max_font_size = 300
        self.img = Image.open(f"{self.bot.data_path}/map.png")
        self.default_options = {'zoom': [0, 5],
                                'top': [5, 10, 20],
                                'player': False,
                                'label': [0, 2, 3],
                                'center': (500, 500)}

    async def called_per_hour(self):
        self.top10_cache.clear()

        for key in self.menue_cache.copy():
            menue = self.menue_cache[key]
            now = datetime.utcnow()
            creation = menue.message.created_at

            if menue.dead is True and (now - creation).total_seconds() > 600:
                self.menue_cache.pop(key)

    async def send_map(self, ctx, *args, **kwargs):
        image = await self.bot.execute(self.draw_map, *args, **kwargs)

        file = io.BytesIO()
        image.save(file, "png", quality=100)
        image.close()
        file.seek(0)

        await ctx.send(file=discord.File(file, "map.png"))
        return file

    async def timeout(self, user_id, time):
        current = self.menue_cache.get(user_id)
        if current is None:
            return

        current.dead = True
        embed = current.message.embeds[0]
        embed.title = f"**Timeout:** Zeitüberschreitung({time}s)"
        await utils.silencer(current.message.edit(embed=embed))
        await utils.silencer(current.message.clear_reactions())

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
        x_coords = []
        y_coords = []

        for vil in villages:
            if vil.rank == 22:
                continue

            if self.minimum_size < vil.x < self.maximum_size:
                x_coords.append(vil.x)
            if self.minimum_size < vil.y < self.maximum_size:
                y_coords.append(vil.y)

        iterable = [min(x_coords), min(y_coords),
                    max(x_coords), max(y_coords)]
        return self.calculate_bounds(iterable, self.borderspace)

    def calculate_bounds(self, iterable, space):
        bounds = []

        if isinstance(space, tuple):
            min_space, max_space = space
        else:
            min_space = space
            max_space = space

        for min_coord in iterable[:2]:
            if (min_coord - min_space) < self.minimum_size:
                bounds.append(self.minimum_size)
            else:
                bounds.append(min_coord - min_space)

        for max_coord in iterable[2:]:
            if (max_coord + max_space) > self.maximum_size:
                bounds.append(self.maximum_size)
            else:
                bounds.append(max_coord + max_space)

        return bounds

    def in_bounds(self, vil):
        if not self.minimum_size <= vil.x < self.maximum_size:
            return False
        elif not self.minimum_size <= vil.y < self.maximum_size:
            return False
        else:
            return True

    def create_base(self, villages, **kwargs):
        base_id = kwargs.get('base')
        bounds = self.bound_cache.get(base_id)

        if bounds is None:
            bounds = self.get_bounds(villages)

            if base_id is not None:
                self.bound_cache[base_id] = bounds

        center = kwargs.get('center', (500, 500))
        zoom = kwargs.get('zoom')

        if zoom or center != (500, 500):
            if zoom != 0:
                # 1, 2, 3, 4, 5 | 80% ,65%, 50%, 35%, 20%
                percentages = [0.8, 0.65, 0.5, 0.35, 0.2]
                percentage = percentages[zoom - 1]
            else:
                percentage = 1

            length = int((bounds[2] - bounds[0]) * percentage / 2)
            shell = {'id': 0, 'player': 0, 'x': center[0], 'y': center[1], 'rank': 0}
            vil = utils.MapVillage(shell)
            iterable = [vil.x, vil.y, vil.x, vil.y]
            bounds = self.calculate_bounds(iterable, length)

        with self.img.copy() as cache:
            img = cache.crop(bounds)
            return np.array(img), bounds[0:2]

    def watermark(self, image):
        watermark = Image.new('RGBA', image.size, (255, 255, 255, 0))
        board = ImageDraw.Draw(watermark)

        percentage = image.size[0] / self.maximum_size
        font = ImageFont.truetype(f'{self.bot.data_path}/water.otf', int(150 * percentage))
        position = int(image.size[0] - 400 * percentage), int(image.size[1] - 232 * percentage)
        board.text(position, "dsBot", (255, 255, 255, 50), font)
        image.paste(watermark, mask=watermark)
        watermark.close()

    def label_map(self, result, village_cache, zoom=0):
        reservation = []
        base_size = int(self.max_font_size * ((result.size[0] - 50) / self.maximum_size))
        sorted_cache = sorted(village_cache.items(), key=lambda l: len(l[1]))
        most_villages = len(sorted_cache[-1][1])

        bound_size = tuple([int(c * 1.5) for c in result.size])
        legacy = Image.new('RGBA', bound_size, (255, 255, 255, 0))
        image = ImageDraw.Draw(legacy)

        for dsobj, villages in village_cache.items():
            if not villages:
                continue

            font_size = base_size
            if isinstance(dsobj, utils.Player):
                font_size *= 0.4

            vil_x = [int(v[0] * 1.5) for v in villages]
            vil_y = [int(v[1] * 1.5) for v in villages]
            centroid = sum(vil_y) / len(villages), sum(vil_x) / len(villages)

            factor = len(villages) / most_villages * font_size / 4
            size = int(font_size - (font_size / 4) + factor + (zoom * 3.5))
            font = ImageFont.truetype(f'{self.bot.data_path}/bebas.ttf', size)
            font_width, font_height = image.textsize(str(dsobj), font=font)
            position = [int(centroid[0] - font_width / 2), int(centroid[1] - font_height / 2)]

            fwd = True
            while True:
                args = [*position, font_width, font_height]
                response = self.overlap(reservation, *args)

                if response is True:
                    if fwd:
                        position[1] -= 5
                    else:
                        position[1] += 5

                    if position[1] < self.minimum_size:
                        fwd = False

                else:
                    reservation.append(response)
                    break

            # draw title and shadow / index tribe color
            dist = int((result.size[0] / self.maximum_size) * 10 + 1)
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
        highlight = options.get('highlight')

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

                # if color != [112, 128, 144]:
                village_cache[tribe].append([y, x])

                if highlight is True:
                    overlay[y - 6:y + 10, x - 6:x + 10] = color + [75]

            base[y: y + 4, x: x + 4] = color

        result = Image.fromarray(base)

        if highlight is True:
            # append highligh overlay to base image
            with Image.fromarray(overlay) as foreground:
                result.paste(foreground, mask=foreground)

        # create legacy which is double in size for improved text quality
        if label is True and (tribes or players):
            zoom = options.get('zoom', 0)
            self.label_map(result, village_cache, zoom)

        self.watermark(result)
        return result

    @commands.cooldown(1, 30, commands.BucketType.guild)
    @commands.command(name="map")
    async def map_(self, ctx, *, arguments=None):
        tribe_names, options, = keyword(arguments, strip=True, dct=True, **self.default_options)

        await ctx.trigger_typing()

        color_map = []
        if not tribe_names:

            file = self.top10_cache.get(ctx.server)
            if arguments is None and file is not None:
                file.seek(0)
                await ctx.send(file=discord.File(file, 'map.png'))
                return

            ds_type = "player" if options['player'] else "tribe"
            ds_objects = await self.bot.fetch_top(ctx.server, options['top'].value, ds_type)

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

                if len(fractions) == 1 and '&' not in tribe_names:
                    color_map.extend([obj] for obj in names)
                else:
                    color_map.append(names)

            ds_objects = await self.bot.fetch_bulk(ctx.server, all_tribes, 1, name=True)

        if len(color_map) > 20:
            await ctx.send("Du kannst nur bis zu 20 Stämme/Gruppierungen angeben")
            return

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
                ds_objects.remove(tribe)

        all_villages = await self.bot.fetch_all(ctx.server, "map")
        if not all_villages:
            msg = "Auf der Welt gibt es noch keine Dörfer :/"
            await ctx.send(msg)
            return

        ds_dict = {dsobj.id: dsobj for dsobj in ds_objects}
        if options['player']:
            args = (all_villages, {}, ds_dict)

        else:
            result = await self.bot.fetch_tribe_member(ctx.server, list(ds_dict))
            players = {pl.id: pl for pl in result}
            args = (all_villages, ds_dict, players)

        zoom = options['zoom'].value
        center = options['center'].value
        label = options['label'].value in (2, 3)
        hightlight = options['label'].value in (1, 2)
        kwargs = {'zoom': zoom, 'label': label, 'highlight': hightlight, 'center': center}
        file = await self.send_map(ctx, *args, **kwargs)

        if arguments is None:
            self.top10_cache[ctx.server] = file
        else:
            file.close()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self.menue_handler(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        await self.menue_handler(payload)

    async def menue_handler(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        menue = self.menue_cache.get(payload.user_id)
        if menue is None:
            return

        elif payload.message_id != menue.message.id:
            return

        else:
            resp = await menue.change(str(payload.emoji))
            if resp is None:
                await self.timeout(payload.user_id, 300)

            elif isinstance(resp, tuple):
                await self.send_map(menue.ctx, *resp[0], **resp[1])
                menue.dead = True

    @commands.cooldown(1, 60, commands.BucketType.guild)
    @commands.command(name="custom", aliases=["last"])
    async def custom_(self, ctx, world: utils.WorldConverter = None):
        menue = self.menue_cache.get(ctx.author.id)

        if menue is not None and menue.dead is False:
            msg = "Du hast bereits eine offene Karte"
            return await ctx.send(msg)

        elif ctx.invoked_with.lower() == "last":
            if menue is None:
                msg = "Du hast keine alte Karte mehr im Cache"
                return await ctx.send(msg)

            elif menue.is_dead():
                await menue.reinstall(ctx)

        else:
            if world is not None:
                ctx.world = world

            menue = MapMenue(ctx)
            self.menue_cache[ctx.author.id] = menue
            await menue.setup()

        await asyncio.sleep(600)

        menue = self.menue_cache.get(ctx.author.id)
        if menue is None:
            return

        if ctx.message.id == menue.ctx.message.id:
            await self.timeout(ctx.author.id, 600)

    @commands.cooldown(2, 1800, commands.BucketType.guild)
    @commands.command(name="timelapse")
    async def timelapse(self, ctx, *, options=None):
        rest, days = keyword(options, strip=True, days=[7, 7, 60])

        if rest:
            world = await utils.WorldConverter().convert(ctx, rest)
            ctx.world = world

        await ctx.send("Daten werden geladen...")

        day_rankings = {}
        async with self.bot.pool.acquire() as conn:
            for n in range(1, days.value + 1):
                query = f'SELECT * FROM tribe{n} WHERE world = $1 ORDER BY rank LIMIT 10'
                cache = await conn.fetch(query, ctx.server)
                tribes = {rec[1]: utils.Tribe(rec) for rec in cache}

                query = f'SELECT * FROM player{n} WHERE world = $1 AND tribe_id = ANY($2)'
                cache = await conn.fetch(query, ctx.server, list(tribes))
                player = {rec[1]: utils.Player(rec) for rec in cache}

                query = f'SELECT * FROM village{n} WHERE world = $1'
                cache = await conn.fetch(query, ctx.server)
                villages = [utils.MapVillage(rec) for rec in cache]

                if len(villages) != 0:
                    day_rankings[n] = {'village': villages,
                                       'tribe': tribes,
                                       'player': player}

        self.bot.loop.create_task(self.zip_task(ctx, day_rankings, days.value))
        await ctx.send("Bilder werden generiert...")

    async def zip_task(self, ctx, *args):
        files = await self.bot.execute(self.zip_timelapse, *args)
        for file in files:
            await ctx.send(file=file)
            await asyncio.sleep(1)

    def zip_timelapse(self, day_rankings, last_day):
        palette = {}
        colors = self.colors.top()

        for tribe in day_rankings[1]['tribe'].values():
            palette[tribe.id] = colors.pop(0)

        files = []
        archive = io.BytesIO()
        zip_archive = ZipFile(archive, 'w')
        today = datetime.now()

        for index, (day, package) in enumerate(day_rankings.items(), start=1):

            for tribe in package['tribe'].values():
                color = palette.get(tribe.id, [112, 128, 144])
                tribe.color = color

            args = list(package.values())
            kwargs = {'label': True, 'highlight': True, 'base': today.timestamp()}
            image = self.draw_map(*args, **kwargs)

            shell = io.BytesIO()
            image.save(shell, "png", quality=100)
            image.close()
            shell.seek(0)

            date = today - timedelta(days=index)
            date_pars = date.strftime('%d.%m.%Y')
            zip_archive.writestr(f"{date_pars}.png", shell.read())

            if day % 10 == 0 or day == last_day:
                zip_archive.close()
                archive.seek(0)

                file = discord.File(archive, f'images_{len(files) + 1}.zip')
                files.append(file)

                archive = io.BytesIO()
                zip_archive = ZipFile(archive, 'w')

        self.bound_cache.pop(today.timestamp())
        return files


def setup(bot):
    bot.add_cog(Map(bot))
