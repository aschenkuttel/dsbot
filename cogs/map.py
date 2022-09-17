from discord.ui import Modal, View, TextInput
from PIL import Image, ImageFont, ImageDraw
from discord import app_commands
from discord.ext import commands
import numpy as np
import discord
import utils
import io
import re


class MapModal(Modal):
    def __init__(self, callback, title, label, long=False):
        super().__init__(title=title)
        self.callback = callback
        self.label = label
        self.long = long

    input_text = TextInput(label="")

    def render(self):
        self.input_text.label = self.label
        self.input_text.style = discord.TextStyle.long if self.long else discord.TextStyle.short

    async def on_submit(self, interaction):
        await self.callback(interaction, self.input_text.value)


class MapMenue:
    def __init__(self, interaction):
        super().__init__()

        self.interaction = interaction
        self.bot = interaction.client
        self.callback = None
        self.view = View()
        self.embed = None
        self.zoom = 0
        self.center = "500|500"
        self.tribes = []
        self.player = []
        self.highlight = 0
        self.bb = True
        self.color = utils.DSColor()

    async def setup(self, callback):
        self.callback = callback

        options = []
        for icon, value in self.interaction.lang.map.items():
            title = value['title']
            default = value.get('default')

            if default is not None:
                message = f"{icon} {title} `[{default}]`"
            else:
                message = f"{icon} {title}"

                if len(icon) > 1:
                    message = "\n" + message

            options.append(message)

        self.embed = discord.Embed(title="Custom Map Tool", description="\n".join(options))
        example = f"Für eine genaue Erklärung und Beispiele: /help custom"
        self.embed.set_footer(text=example)

        for index, icon in enumerate(self.interaction.lang.map.keys()):
            button = utils.DSButton(
                custom_id=str(index),
                emoji=icon,
                row=0 if index < 4 else 1,
                _callback=self.change
            )

            self.view.add_item(button)

        await self.interaction.response.send_message(embed=self.embed, view=self.view)

    async def coord_callback(self, interaction, value):
        coords = re.findall(r'\d\d\d\|\d\d\d', value)
        self.center = coords[0] if coords else "500|500"
        await self.update(1, interaction)

    async def player_callback(self, interaction, value):
        iterable = value.split("\n")
        args = (self.interaction.server, iterable, 0)
        data = await self.bot.fetch_bulk(*args, name=True)
        self.player = data[:10]
        await self.update(2, interaction)

    async def tribe_callback(self, interaction, value):
        iterable = value.split("\n")
        args = (self.interaction.server, iterable, 1)
        data = await self.bot.fetch_bulk(*args, name=True)
        self.tribes = data[:10]
        await self.update(3, interaction)

    async def change(self, custom_id, interaction):
        index = int(custom_id)
        # index 0: zoom
        if index == 0:
            if self.zoom == 5:
                self.zoom = 0
            else:
                self.zoom += 1

        # index 1,2,3: center, player, tribe
        elif index in (1, 2, 3):
            if index == 1:
                msg = "Gebe bitte die gewünschte Koordinate an:"
                modal = MapModal(self.coord_callback, msg, "Center der Karte")

            else:
                obj = "Spieler" if index == 2 else "Stämme"
                msg = f"Gebe jetzt bis 10 {obj} an (1 Zeile pro)"
                callback = self.player_callback if index == 2 else self.tribe_callback
                modal = MapModal(callback, obj, msg, long=True)

            modal.render()
            await interaction.response.send_modal(modal)
            return

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
            await interaction.response.defer()
            await self.interaction.edit_original_response(embed=self.embed, view=None)

            if self.tribes is False:
                self.tribes = []
            if self.player is False:
                self.player = []
            if self.center is False:
                self.center = "500|500"

            idc = [tribe.id for tribe in self.tribes]
            members = await self.bot.fetch_tribe_member(self.interaction.server, idc)
            colors = self.color.top()

            players = {player.id: player for player in self.player}
            tribes = {tribe.id: tribe for tribe in self.tribes}

            for member in members:
                if member.id not in players:
                    players[member.id] = member

            for dsobj in self.tribes + self.player:
                if dsobj not in members:
                    dsobj.color = colors.pop(0)

            village = await self.bot.fetch_all(self.interaction.server, 'map')
            args = (village, tribes, players)

            center = [int(c) for c in self.center.split('|')]
            label = self.highlight in (2, 3)
            kwargs = {'zoom': self.zoom, 'center': center, 'label': label}
            await self.callback(interaction, *args, **kwargs)
            return

        else:
            self.zoom = 0
            self.center = "500|500"
            self.tribes = []
            self.player = []
            self.highlight = 0
            self.bb = True

        await self.update(index, interaction)
        return True

    async def update(self, index, interaction):
        self.update_embed(index)
        await interaction.response.edit_message(embed=self.embed, view=self.view)

    def update_embed(self, index):
        # reset index
        if index == 7:
            for num in range(6):
                self.update_embed(num)
            return

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

    async def send_map(self, interaction, *args, **kwargs):
        image = await self.bot.execute(self.draw_map, *args, **kwargs)

        file = io.BytesIO()
        image.save(file, "png", quality=100)
        image.close()
        file.seek(0)

        await interaction.followup.send(file=discord.File(file, "map.png"))
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
            shell = {'id': 0, 'player_id': 0, 'x': center[0], 'y': center[1], 'rank': 0}
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

    @app_commands.command(name="map", description="Weltenkarte mit unterschiedlichen Optionen")
    @app_commands.describe(names="Namen der Stämme oder Spieler die markiert werden sollen",
                           zoom="Stufe des Zooms von 0-10",
                           top="Anzahl der Top Stämme oder Spieler von 5-20",
                           player="True für Spieler, False für Stämme",
                           label="Namen über den gefärbten Objekten",
                           highlight="Schein für die gefärbten Objekte")
    @app_commands.checks.cooldown(1, 30, key=lambda i: i.guild_id)
    async def map_(self, interaction,
                   names: str = "",
                   zoom: app_commands.Range[int, 1, 10] = 0,
                   top: app_commands.Range[int, 5, 20] = 10,
                   player: bool = False,
                   label: bool = True,
                   highlight: bool = True):
        await interaction.response.defer()
        default_map = interaction.data.get('options') is None

        color_map = []
        if not names:
            file = self.top10_cache.get(interaction.server)

            if default_map is None and file is not None:
                file.seek(0)
                await interaction.followup.send(file=discord.File(file, 'map.png'))
                return

            ds_type = "player" if player else "tribe"
            ds_objects = await self.bot.fetch_top(interaction.server, top, ds_type)

        else:
            all_names = []
            raw_fractions = names.split('&')
            fractions = [f for f in raw_fractions if f]

            for index, team in enumerate(fractions):
                fraction_names = []
                quoted = re.findall(r'\"(.+)\"', team)
                for res in quoted:
                    team = team.replace(f'"{res}"', ' ')
                    fraction_names.append(res)

                for name in team.split():
                    if not name:
                        continue
                    fraction_names.append(name)

                all_names.extend(fraction_names)

                if len(fractions) == 1 and '&' not in names:
                    color_map.extend([obj] for obj in fraction_names)
                else:
                    color_map.append(names)

            ds_objects = await self.bot.fetch_bulk(interaction.server, all_names, 1, name=True)

        if len(color_map) > 20:
            await interaction.followup.send("Du kannst nur bis zu 20 Stämme/Gruppierungen angeben")
            return

        colors = self.colors.top()
        for tribe in ds_objects.copy():
            if not names:
                tribe.color = colors.pop(0)
                continue

            for index, group in enumerate(color_map):
                names = [t.lower() for t in group]
                if tribe.tag.lower() in names:
                    tribe.color = colors[index]
                    break

            else:
                ds_objects.remove(tribe)

        all_villages = await self.bot.fetch_all(interaction.server, "map")
        if not all_villages:
            msg = "Auf der Welt gibt es noch keine Dörfer :/"
            await interaction.followup.send(msg)
            return

        ds_dict = {dsobj.id: dsobj for dsobj in ds_objects}
        if player:
            args = (all_villages, {}, ds_dict)

        else:
            result = await self.bot.fetch_tribe_member(interaction.server, list(ds_dict))
            players = {pl.id: pl for pl in result}
            args = (all_villages, ds_dict, players)

        kwargs = {'zoom': zoom, 'label': label, 'highlight': highlight}
        file = await self.send_map(interaction, *args, **kwargs)

        if default_map:
            self.top10_cache[interaction.server] = file
        else:
            file.close()

    @app_commands.command(name="custom", description="Weltenkartentool mit Menü")
    @app_commands.checks.cooldown(1, 30, key=lambda i: i.guild_id)
    async def custom_(self, interaction, world: utils.WorldConverter = None):
        if world is not None:
            interaction.world = world
            interaction.server = world.server

        menue = MapMenue(interaction)
        await menue.setup(callback=self.send_map)


async def setup(bot):
    await bot.add_cog(Map(bot))
