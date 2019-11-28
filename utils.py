from discord.ext import commands
from load import load
import datetime
import discord
import asyncio
import re

twstats = "https://de.twstats.com/de{}/index.php?page={}&id={}"
ingame = "https://de{}.die-staemme.de/{}.php?screen=info_{}&id={}"

dc = {
    "!": "%21",
    "#": "%23",
    "$": "%24",
    "&": "%26",
    "'": "%27",
    "(": "%28",
    ")": "%29",
    "*": "%2A",
    "+": "%2B",
    "/": "%2F",
    ":": "%3A",
    ";": "%3B",
    "<": "%3C",
    "=": "%3D",
    ">": "%3E",
    "?": "%3F",
    "@": "%40",
    "{": "%7B",
    "|": "%7C",
    "}": "%7D",
    "~": "%7E",
    "[": "%5B",
    "]": "%5D",
    "¢": "%C2%A2",
    "£": "%C2%A3",
    "¥": "%C2%A5",
    "¦": "%C2%A6",
    "§": "%C2%A7",
    "¨": "%C2%A8",
    "©": "%C2%A9",
    "ª": "%C2%AA",
    "«": "%C2%AB",
    "¬": "%C2%AC",
    "®": "%C2%AE",
    "¯": "%C2%AF",
    "°": "%C2%B0",
    "±": "%C2%B1",
    "²": "%C2%B2",
    "³": "%C2%B3",
    "´": "%C2%B4",
    "µ": "%C2%B5",
    "¶": "%C2%B6",
    "·": "%C2%B7",
    "¸": "%C2%B8",
    "¹": "%C2%B9",
    "º": "%C2%BA",
    "»": "%C2%BB",
    "¼": "%C2%BC",
    "½": "%C2%BD",
    "¾": "%C2%BE",
    "¿": "%C2%BF",
    "À": "%C3%80",
    "Á": "%C3%81",
    "Â": "%C3%82",
    "Ã": "%C3%83",
    "Ä": "%C3%84",
    "Å": "%C3%85",
    "Æ": "%C3%86",
    "Ç": "%C3%87",
    "È": "%C3%88",
    "É": "%C3%89",
    "Ê": "%C3%8A",
    "Ë": "%C3%8B",
    "Ì": "%C3%8C",
    "Í": "%C3%8D",
    "Î": "%C3%8E",
    "Ï": "%C3%8F",
    "Ð": "%C3%90",
    "Ñ": "%C3%91",
    "Ò": "%C3%92",
    "Ó": "%C3%93",
    "Ô": "%C3%94",
    "Õ": "%C3%95",
    "Ö": "%C3%96",
    "×": "%C3%97",
    "Ø": "%C3%98",
    "Ù": "%C3%99",
    "Ú": "%C3%9A",
    "Û": "%C3%9B",
    "Ü": "%C3%9C",
    "Ý": "%C3%9D",
    "Þ": "%C3%9E",
    "ß": "%C3%9F",
    "ã": "%C3%A3",
    "ä": "%C3%A4",
    "å": "%C3%A5",
    "æ": "%C3%A6",
    "ç": "%C3%A7",
    "è": "%C3%A8",
    "é": "%C3%A9",
    "ê": "%C3%AA",
    "ë": "%C3%AB",
    "ì": "%C3%AC",
    "í": "%C3%AD",
    "î": "%C3%AE",
    "ï": "%C3%AF",
    "ð": "%C3%B0",
    "ñ": "%C3%B1",
    "ò": "%C3%B2",
    "ó": "%C3%B3",
    "ô": "%C3%B4",
    "õ": "%C3%B5",
    "ö": "%C3%B6",
    "÷": "%C3%B7",
    "ø": "%C3%B8",
    "ù": "%C3%B9",
    "ú": "%C3%BA",
    "û": "%C3%BB",
    "ü": "%C3%BC",
    "ý": "%C3%BD",
    "þ": "%C3%BE",
    "ÿ": "%C3%BF"
}


def pcv(number):
    return "{0:,}".format(number).replace(",", ".")


def casual(world):
    return str(world) if world > 50 else f"p{world}"


# ignores missing perm error
async def silencer(coro):
    try:
        await coro
    except discord.Forbidden:
        return


# adds reaction hint and deletes it afterwards
async def private_hint(ctx):
    try:
        await ctx.message.add_reaction("📨")
    except discord.Forbidden:
        pass
    await asyncio.sleep(10)
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass


# converts names to innos version / normal
def converter(name, dirty=False):
    dic = {value: key for key, value in dc.items()}
    destination = dc if dirty else dic
    for key, value in destination.items():
        if key in name:
            name = name.replace(key, value)
    repl = (" ", "+") if dirty else ("+", " ")
    result = name.replace(*repl)
    return result.lower() if dirty else result


# default embeds
def error_embed(text, ctx=None):
    embed = discord.Embed(description=text, color=discord.Color.red())
    if ctx:
        help_text = f"Erklärung und Beispiel mit {ctx.prefix}help {ctx.command}"
        embed.set_footer(text=help_text)
    return embed


def complete_embed(text):
    return discord.Embed(description=text, color=discord.Color.green())


def game_channel_only():
    def predicate(ctx):
        chan = load.get_item(ctx.guild.id, "game")
        if not chan:
            raise GameChannelMissing()
        if chan == ctx.channel.id:
            return True
        raise WrongChannel()

    return commands.check(predicate)


# custom errors
class GameChannelMissing(commands.CheckFailure):
    def __str__(self):
        return "missing channel"


class WrongChannel(commands.CheckFailure):
    def __str__(self):
        return "wrong channel"


class WorldMissing(commands.CheckFailure):
    def __str__(self):
        return "missing world"


class PrivateOnly(commands.CheckFailure):
    pass


class IngameError(commands.CheckFailure):
    pass


class DontPingMe(commands.CheckFailure):
    pass


class DSUserNotFound(commands.CheckFailure):
    def __init__(self, searchable):
        self.name = searchable


class GuildUserNotFound(commands.CheckFailure):
    def __init__(self, searchable):
        self.name = searchable


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
        return casual(self._world)

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


# typhint converter which convertes to either tribe or player
class DSObject(commands.Converter):
    __slots__ = (
        'id', 'x', 'y', 'world', 'url', 'alone', 'name', 'tag', 'tribe_id', 'villages', 'points',
        'rank', 'player', 'att_bash', 'att_rank', 'def_bash', 'def_rank', 'all_bash', 'all_rank',
        'ut_bash', 'member', 'all_points', 'guest_url', 'ingame_url', 'twstats_url')

    async def convert(self, ctx, searchable):
        obj = await load.fetch_both(ctx.world, searchable)
        if not obj:
            raise DSUserNotFound(searchable)
        return obj


# own case insensitive member converter
class GuildUser(commands.Converter):
    def __init__(self):
        self.id = None
        self.name = None
        self.display_name = None
        self.avatar_url = None

    async def convert(self, ctx, arg):
        if re.match(r'<@!?([0-9]+)>$', arg):
            raise DontPingMe
        for m in ctx.guild.members:
            if m.display_name.lower() == arg.lower():
                return m
            if m.name.lower() == arg.lower():
                return m
        else:
            raise GuildUserNotFound(arg)


# default tribal wars classes
class Player:
    def __init__(self, data):
        self.id = data['id']
        self.alone = True
        self.world = data['world']
        self.url = casual(self.world)
        self.name = converter(data['name'])
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
        self.url = casual(self.world)
        self.name = converter(data['name'])
        self.tag = converter(data['tag'])
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
        self.name = converter(data['name'])
        self.x = data['x']
        self.y = data['y']
        self.player_id = data['player']
        self.points = data['points']
        self.rank = data['rank']
        self.world = data['world']
        self.url = casual(self.world)

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
        self.player = data['player']


class Conquer:
    def __init__(self, world, data):
        self.id = data[0]
        self.unix = data[1]
        self.new = data[2]
        self.old = data[3]
        self.world = world
        self.old_tribe = None
        self.new_tribe = None
        self.old_player = None
        self.new_player = None
        self.village = None

    @property
    def time(self):
        date = datetime.datetime.fromtimestamp(self.unix)
        return date

    @property
    def player_ids(self):
        return self.new, self.old

    @property
    def grey(self):
        return 0 in (self.new, self.old)

    @property
    def coords(self):
        return f"{self.village.x}|{self.village.y}"


class DSColor:

    def __init__(self):
        self.red = [230, 40, 0]
        self.blue = [16, 52, 166]
        self.yellow = [255, 189, 32]
        self.turquoise = [64, 224, 208]
        self.pink = [255, 8, 127]
        self.orange = [253, 106, 2]
        self.green = [152, 251, 152]
        self.purple = [192, 5, 248]
        self.white = [245, 245, 245]
        self.dark_green = [0, 51, 0]
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
                   self.orange, self.green, self.purple, self.white, self.dark_green]
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
