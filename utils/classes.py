from contextlib import asynccontextmanager
from discord.ext import commands
from datetime import datetime
import asyncio
import discord
import utils
import json
import re

twstats = "https://{}.twstats.com/{}/index.php?page={}&id={}"
ingame = "https://{}/{}.php?screen=info_{}&id={}"

world_title = {'def': "Welt", 'p': "Casual", 'c': "Sonderwelt", 's': "SDS"}
world_data = {
    'de': {'domain': "die-staemme.de", 'icon': ":flag_de:"},
    'ch': {'domain': "staemme.ch", 'icon': ":flag_ch:"}
}


# custom context for simple world implementation
class DSContext(commands.Context):
    def __init__(self, **attrs):
        super().__init__(**attrs)
        self._world = None
        self.server = None

    @property
    def world(self):
        return self._world

    @world.setter
    def world(self, world):
        self._world = world
        self.server = world.server

    async def safe_send(self, content=None, *, embed=None, file=None, delete_after=None):
        try:
            await self.send(content, embed=embed, file=file, delete_after=delete_after)
        except discord.Forbidden:
            return

    async def safe_delete(self):
        try:
            await self.message.delete()
        except discord.Forbidden:
            return

    async def private_hint(self):
        if self.guild is None:
            return
        try:
            await self.message.add_reaction("📨")
            return True
        except (discord.Forbidden, discord.NotFound):
            pass


# default tribal wars classes
class DSObject:
    def __init__(self, data):
        self.id = data['id']
        self.world = data['world']
        self.lang = self.world[:2]
        self.name = utils.converter(data['name'])
        self.points = data['points']
        self.rank = data['rank']

    def __str__(self):
        if isinstance(self, Village):
            represent = self.coords
        elif isinstance(self, Tribe):
            represent = self.tag
        else:
            represent = self.name

        return represent.replace("*", "\\*")

    @property
    def type(self):
        return self.__class__.__name__.lower()

    @property
    def guest_url(self):
        return self.get_ingame_url(visit=True)

    @property
    def ingame_url(self):
        return self.get_ingame_url()

    @property
    def twstats_url(self):
        return twstats.format(self.lang, self.world, self.type, self.id)

    @property
    def mention(self):
        return f"[{self}]({self.ingame_url})"

    @property
    def guest_mention(self):
        return f"[{self}]({self.guest_url})"

    @property
    def twstats_mention(self):
        return f"[{self}]({self.twstats_url})"

    def get_ingame_url(self, visit=False):
        url_type = 'guest' if visit else 'game'
        header = f"{self.world}.{world_data[self.lang]['domain']}"
        dstype = "ally" if self.type == "tribe" else self.type
        return ingame.format(header, url_type, dstype, self.id)


class Player(DSObject):
    def __init__(self, data):
        super().__init__(data)
        self.alone = True
        self.tribe_id = data['tribe_id']
        self.villages = data['villages']
        self.att_bash = data['att_bash']
        self.att_rank = data['att_rank']
        self.def_bash = data['def_bash']
        self.def_rank = data['def_rank']
        self.sup_bash = data['sup_bash']
        self.sup_rank = data['sup_rank']
        self.all_bash = data['all_bash']
        self.all_rank = data['all_rank']


class Tribe(DSObject):
    def __init__(self, data):
        super().__init__(data)
        self.alone = False
        self.tag = utils.converter(data['tag'])
        self.member = data['member']
        self.villages = data['villages']
        self.all_points = data['all_points']
        self.att_bash = data['att_bash']
        self.att_rank = data['att_rank']
        self.def_bash = data['def_bash']
        self.def_rank = data['def_rank']
        self.all_bash = data['all_bash']
        self.all_rank = data['all_rank']


class Village(DSObject):
    def __init__(self, data):
        super().__init__(data)
        self.x = data['x']
        self.y = data['y']
        self.player_id = data['player']
        self.coords = f"{self.x}|{self.y}"


class MapVillage:
    def __init__(self, data):
        self.id = data['id']
        self.x = 1501 + 5 * (data['x'] - 500)
        self.y = 1501 + 5 * (data['y'] - 500)
        self.player_id = data['player']
        self.rank = data['rank']

    def reposition(self, difference):
        self.x -= difference[0]
        self.y -= difference[1]
        return self.x, self.y


class Conquer:
    def __init__(self, world, data):
        self.id = data[0]
        self.unix = data[1]
        self.new_id = data[2]
        self.old_id = data[3]
        self.world = world
        self.old_tribe = None
        self.new_tribe = None
        self.village = None

    @property
    def time(self):
        return datetime.fromtimestamp(self.unix)

    @property
    def player_ids(self):
        return self.new_id, self.old_id

    @property
    def grey(self):
        return 0 in (self.new_id, self.old_id)

    @property
    def coords(self):
        return f"{self.village.x}|{self.village.y}"

    def self_conquer(self):
        return self.old_id == self.new_id


class DSColor:
    def __init__(self):
        self.blue = [16, 52, 166]
        self.red = [230, 40, 0]
        self.turquoise = [64, 224, 208]
        self.yellow = [255, 189, 32]
        self.orange = [253, 106, 2]
        self.pink = [255, 8, 127]
        self.green = [152, 251, 152]
        self.purple = [128, 0, 128]
        self.white = [245, 245, 245]
        self.bright_blue = [0, 127, 254]
        self.bright_red = [254, 127, 127]
        self.bright_yellow = [254, 254, 127]
        self.bright_orange = [239, 114, 21]
        self.bright_green = [152, 251, 152]
        self.dark_blue = [0, 49, 82]
        self.dark_red = [128, 0, 0]
        self.dark_yellow = [204, 119, 34]
        self.dark_orange = [177, 86, 15]
        self.dark_green = [0, 51, 0]
        self.bubble_gum = [254, 91, 172]

        # map colors
        self.bg_green = [88, 118, 27]
        self.bg_forrest = [73, 103, 21]
        self.vil_brown = [130, 60, 10]
        self.sector_green = [48, 73, 14]
        self.field_green = [67, 98, 19]
        self.bb_grey = [150, 150, 150]
        self.fortress_green = [10, 150, 150]
        self.fortress_yellow = [240, 200, 0]

    def top(self):
        palette = [self.blue, self.red, self.turquoise, self.yellow,
                   self.orange, self.pink, self.green, self.purple,
                   self.white, self.bright_blue, self.bright_red, self.bright_yellow,
                   self.bright_orange, self.bright_green, self.dark_blue, self.dark_red,
                   self.dark_yellow, self.dark_orange, self.dark_green, self.bubble_gum]
        return palette


class DSWorld:
    def __init__(self, data=None):
        self.server = data['world']
        self.speed = data['speed']
        self.unit_speed = data['unit_speed']
        self.moral = data['moral']
        self.config = json.loads(data['config'])
        self.lang, self.number, self.title = self.parse(self.server)
        pkg = world_data.get(self.lang)
        self.icon, self.domain = pkg['icon'], pkg['domain']
        self.url = f"{self.server}.{self.domain}"

    def __str__(self):
        return self.show()

    def __eq__(self, other):
        return self.server == other

    def show(self, clean=False):
        if clean:
            return f"{self.title} {self.number}"
        else:
            return f"`{self.title} {self.number}` {self.icon}"

    @property
    def guest_url(self):
        return f"https://{self.url}/guest.php"

    @property
    def settings_url(self):
        return f"https://{self.url}/page/settings"

    @staticmethod
    def parse(argument):
        result = re.findall(r'([a-z]{2})([a-z]?)(\d+)', argument)
        lang, world_type, number = result[0]
        title = world_title.get(world_type or 'def')
        return lang, int(number), title


class DSType:
    classes = {'player': Player, 'tribe': Tribe, 'village': Village, 'map': MapVillage}

    def __init__(self, arg):
        self.arg = arg
        self.Class = None
        self.table = None
        res = self.try_convers(self.arg)
        if not res:
            raise ValueError(f"argument: {self.arg} needs to be either enum or tablename")

    def try_convers(self, arg):
        if isinstance(arg, int):
            self.try_enum(arg)

        elif isinstance(arg, str):
            arg = arg.lower()
            self.try_name(arg)

        return bool(self.table)

    def try_enum(self, arg):
        for index, (name, dstype) in enumerate(self.classes.items()):
            if arg == index:
                self.Class = dstype
                self.table = name

    def try_name(self, arg):
        table = re.findall(r'(\D+)\d*', arg)
        if not table:
            return

        self.Class = self.classes.get(table[0])
        if self.Class:

            if arg == "map":
                self.table = "village"
            else:
                self.table = arg


class TribalGames(commands.Cog):

    async def cog_check(self, ctx):
        container = self.get_container(ctx)
        if isinstance(container, list):
            self.get_game_data(ctx, container)

        return True

    @asynccontextmanager
    async def cooldown(self, ctx, time=15):
        container = self.get_container(ctx)
        if isinstance(container, list):
            container.append(ctx.guild.id)
            method = container.remove
        else:
            container[ctx.guild.id] = False
            method = container.pop

        try:
            yield
        finally:
            await asyncio.sleep(time)

            if ctx.guild.id in container:
                method(ctx.guild.id)

    def get_container(self, ctx):
        command = str(ctx.command)
        if command == "guess":
            command = "hangman"
        elif command == "draw":
            command = "videopoker"

        return getattr(self, command)

    def get_game_data(self, ctx, container=None):
        if container is None:
            container = self.get_container(ctx)

        if ctx.guild.id not in container:
            return None

        if isinstance(container, list):
            raise utils.SilentError
        else:
            data = container[ctx.guild.id]
            if data is False:
                raise utils.SilentError
            else:
                return data
