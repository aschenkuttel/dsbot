from discord.ext import commands
from datetime import datetime
import discord
import utils
import re

twstats = "https://de.twstats.com/{}/index.php?page={}&id={}"
ingame = "https://{}.die-staemme.de/{}.php?screen=info_{}&id={}"
guest = "https://{}.die-staemme.de/guest.php"

world_titles = {'de': "Welt", 'dep': "Casual", 'dec': "Sonderwelt", 'des': "SDS"}


# custom context for simple world implementation
class DSContext(commands.Context):
    def __init__(self, **attrs):
        super().__init__(**attrs)

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


# typhint converter which converts to either tribe or player
class DSObject(commands.Converter):
    __slots__ = (
        'id', 'x', 'y', 'world', 'url', 'alone',
        'name', 'tag', 'tribe_id', 'villages',
        'points', 'rank', 'player', 'att_bash',
        'att_rank', 'def_bash', 'def_rank',
        'all_bash', 'all_rank', 'ut_bash',
        'member', 'all_points', 'guest_url',
        'ingame_url', 'twstats_url')

    async def convert(self, ctx, searchable):
        # conquer add/remove needs guild world
        if str(ctx.command).startswith("conquer"):
            raw_world = ctx.bot.config.get_related_world(ctx.guild)
            ctx.world = utils.World(raw_world)

        obj = await ctx.bot.fetch_both(ctx.server, searchable)
        if not obj:
            raise utils.DSUserNotFound(searchable)
        return obj


# own case insensitive member converter / don't judge about slots ty
class GuildUser(commands.Converter):
    __slots__ = ('id', 'name', 'display_name', 'avatar_url')

    async def convert(self, ctx, arg):
        if re.match(r'<@!?([0-9]+)>$', arg):
            raise utils.DontPingMe
        name = arg.lower()
        for m in ctx.guild.members:
            if name == m.display_name.lower():
                return m
            if name == m.name.lower():
                return m
        else:
            raise utils.GuildUserNotFound(arg)


# default tribal wars classes
class Player:
    def __init__(self, data):
        self.id = data['id']
        self.alone = True
        self.world = data['world']
        self.name = utils.converter(data['name'])
        self.tribe_id = data['tribe_id']
        self.villages = data['villages']
        self.points = data['points']
        self.rank = data['rank']
        self.att_bash = data['att_bash']
        self.att_rank = data['att_rank']
        self.def_bash = data['def_bash']
        self.def_rank = data['def_rank']
        self.all_bash = data['all_bash']
        self.all_rank = data['all_rank']
        self.ut_bash = self.all_bash - self.def_bash - self.att_bash

    @property
    def guest_url(self):
        return ingame.format(self.world, 'guest', 'player', self.id)

    @property
    def ingame_url(self):
        return ingame.format(self.world, 'game', 'player', self.id)

    @property
    def twstats_url(self):
        return twstats.format(self.world, 'player', self.id)


class Tribe:
    def __init__(self, data):
        self.id = int(data['id'])
        self.alone = False
        self.world = data['world']
        self.name = utils.converter(data['name'])
        self.tag = utils.converter(data['tag'])
        self.member = data['member']
        self.villages = data['villages']
        self.points = data['points']
        self.all_points = data['all_points']
        self.rank = data['rank']
        self.att_bash = data['att_bash']
        self.att_rank = data['att_rank']
        self.def_bash = data['def_bash']
        self.def_rank = data['def_rank']
        self.all_bash = data['all_bash']
        self.all_rank = data['all_rank']

    @property
    def guest_url(self):
        return ingame.format(self.world, 'guest', 'ally', self.id)

    @property
    def ingame_url(self):
        return ingame.format(self.world, 'game', 'ally', self.id)

    @property
    def twstats_url(self):
        return twstats.format(self.world, 'tribe', self.id)


class Village:
    def __init__(self, data):
        self.id = int(data['id'])
        self.name = utils.converter(data['name'])
        self.x = data['x']
        self.y = data['y']
        self.player_id = data['player']
        self.points = data['points']
        self.rank = data['rank']
        self.world = data['world']

    @property
    def coords(self):
        return f"{self.x}|{self.y}"

    @property
    def guest_url(self):
        return ingame.format(self.world, 'guest', 'village', self.id)

    @property
    def ingame_url(self):
        return ingame.format(self.world, 'game', 'village', self.id)

    @property
    def twstats_url(self):
        return twstats.format(self.world, 'village', self.id)


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


class World(commands.Converter):
    def __init__(self, searchable=None):
        self.prefix = None
        self.number = None
        self.title = None
        self.server = None

        if searchable:
            self.parse_world(searchable)

    def __str__(self):
        return f"{self.title} {self.number}"

    def __eq__(self, other):
        return self.server == other

    @property
    def guest_url(self):
        return guest.format(self.server)

    def parse_world(self, searchable):
        result = re.findall(r'(de[\D]?)(\d+)', searchable)
        if not result:
            return

        self.prefix, self.number = result[0]
        self.title = world_titles.get(self.prefix)
        self.server = f"{self.prefix}{self.number}"

    async def convert(self, ctx, searchable):
        self.parse_world(searchable)
        if self.server in ctx.bot.worlds:
            return self
        else:
            possible = ""
            numbers = re.findall(r'\d+', searchable)
            if numbers and not self.number:
                for world in ctx.bot.worlds:
                    if numbers[0] in world:
                        possible = world

            raise utils.UnknownWorld(possible)


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
            res = self.try_enum(arg)
            return res
        elif isinstance(arg, str):
            arg = arg.lower()
            res = self.try_name(arg)
            return res
        return False

    def try_enum(self, arg):
        for index, (name, dstype) in enumerate(self.classes.items()):
            if arg == index:
                self.Class = dstype
                self.table = name
                return True
        else:
            return False

    def try_name(self, arg):
        self.Class = self.classes.get(arg)
        if self.Class:
            self.table = arg
            if arg == 'map':
                self.table = 'village'
            return True
        return False
