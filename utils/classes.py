from discord.ext import commands
from datetime import datetime
import discord
import utils
import re

twstats = "https://de.twstats.com/de{}/index.php?page={}&id={}"
ingame = "https://de{}.die-staemme.de/{}.php?screen=info_{}&id={}"
guest = "https://de{}.die-staemme.de/guest.php"


# custom context for simple world implementation
class DSContext(commands.Context):
    def __init__(self, **attrs):
        super().__init__(**attrs)
        self._world = None

    @property
    def world(self):
        return self._world

    @world.setter
    def world(self, world):
        self._world = world

    @property
    def url(self):
        return utils.casual(self._world)

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
        except discord.Forbidden:
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
            ctx.world = ctx.get_guild_world(ctx.guild)

        obj = await ctx.bot.fetch_both(ctx.world, searchable)
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
        self.url = utils.casual(self.world)
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
        return ingame.format(self.url, 'guest', 'player', self.id)

    @property
    def ingame_url(self):
        return ingame.format(self.url, 'game', 'player', self.id)

    @property
    def twstats_url(self):
        return twstats.format(self.url, 'player', self.id)


class Tribe:
    def __init__(self, data):
        self.id = int(data['id'])
        self.alone = False
        self.world = data['world']
        self.url = utils.casual(self.world)
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
        return ingame.format(self.url, 'guest', 'ally', self.id)

    @property
    def ingame_url(self):
        return ingame.format(self.url, 'game', 'ally', self.id)

    @property
    def twstats_url(self):
        return twstats.format(self.url, 'tribe', self.id)


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
        self.url = utils.casual(self.world)

    @property
    def coords(self):
        return f"{self.x}|{self.y}"

    @property
    def guest_url(self):
        return ingame.format(self.url, 'guest', 'village', self.id)

    @property
    def ingame_url(self):
        return ingame.format(self.url, 'game', 'village', self.id)

    @property
    def twstats_url(self):
        return twstats.format(self.url, 'village', self.id)


class MapVillage:
    def __init__(self, data):
        self.id = data['id']
        self.x = 1501 + 5 * (data['x'] - 500)
        self.y = 1501 + 5 * (data['y'] - 500)
        self.player_id = data['player']

    def reposition(self, difference):
        self.x -= difference[0]
        self.y -= difference[1]
        return self.x, self.y


class World(commands.Converter):
    def __init__(self, number=None):
        self.number = number
        self.casual = False
        self.pronoun = "Welt"

        if self.number:
            self.gender()

    def __str__(self):
        return f"{self.pronoun} {self.number}"

    def __eq__(self, other):
        return self.number == other

    @property
    def guest_url(self):
        return guest.format(self.url())

    def url(self):
        cas = "p" if self.casual else ""
        return f"{cas}{self.number}"

    def gender(self):
        # we don't talk about this
        if self.number < 50:
            self.casual = True
            self.pronoun = "Casual"

    def parse_world(self, raw_world):
        if isinstance(raw_world, int):
            self.number = raw_world
        if isinstance(raw_world, str):
            if raw_world.isdigit():
                world = int(raw_world)
            else:
                basket = re.findall(r'\D+(\d{2,3})', raw_world)
                if not basket:
                    return
                world = int(basket[0])
            self.number = world

        self.gender()

    def is_active(self, bot):
        return self.number in bot.worlds

    async def convert(self, ctx, searchable):
        self.parse_world(searchable)
        if self.is_active(ctx.bot):
            return self
        else:
            raise utils.UnknownWorld(searchable)


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


class DSColor:
    def __init__(self):
        self.blue = [16, 52, 166]
        self.red = [230, 40, 0]
        self.turquoise = [64, 224, 208]
        self.yellow = [255, 189, 32]
        self.orange = [253, 106, 2]
        self.pink = [255, 8, 127]
        self.green = [152, 251, 152]
        self.purple = [128, 0, 128]  # [192, 5, 248]
        self.white = [245, 245, 245]
        self.dark_green = [0, 51, 0]
        self.bright_yellow = [254, 254, 127]
        self.bright_red = [254, 127, 127]
        self.bright_blue = [0, 127, 254]
        self.bg_green = [88, 118, 27]
        self.bg_forrest = [73, 103, 21]
        self.vil_brown = [130, 60, 10]
        self.sector_green = [48, 73, 14]
        self.field_green = [67, 98, 19]
        self.bb_grey = [150, 150, 150]
        self.fortress_green = [10, 150, 150]
        self.fortress_yellow = [240, 200, 0]

    def top(self):
        palette = [self.red, self.blue, self.yellow, self.turquoise, self.pink,
                   self.orange, self.green, self.purple, self.white, self.dark_green,
                   self.bright_yellow, self.bright_red, self.bright_blue]
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
