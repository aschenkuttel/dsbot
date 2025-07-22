from data.credentials import allowed_pm_commands
from contextlib import asynccontextmanager
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import asyncio
import discord
import utils
import json
import yaml
import re

world_data = {
    'de': {'domain': "die-staemme.de", 'icon': ":flag_de:"},
    'ch': {'domain': "staemme.ch", 'icon': ":flag_ch:"},
    'en': {'domain': "tribalwars.net", 'icon': ":flag_gb:"},
    'nl': {'domain': 'tribalwars.nl', 'icon': ":flag_cz:"},
    'pl': {'domain': 'plemiona.pl', 'icon': ":flag_pl:"},
    'br': {'domain': 'tribalwars.com.br', 'icon': ":flag_br:"},
    'pt': {'domain': 'tribalwars.com.pt', 'icon': ":flag_pt:"},
    'cs': {'domain': 'divokekmeny.cz', 'icon': ":flag_cz:"},
    'ro': {'domain': 'triburile.ro', 'icon': ":flag_ro:"},
    'ru': {'domain': 'voynaplemyon.com', 'icon': ":flag_ua:"},
    'gr': {'domain': 'fyletikesmaxes.gr', 'icon': ":flag_gr:"},
    'sk': {'domain': 'divoke-kmene.sk', 'icon': ":flag_sk:"},
    'hu': {'domain': 'klanhaboru.hu', 'icon': ":flag_hu:"},
    'it': {'domain': 'tribals.it', 'icon': ":flag_it:"},
    'tr': {'domain': 'klanlar.org', 'icon': ":flag_tr:"},
    'fr': {'domain': 'guerretribale.fr', 'icon': ":flag_fr:"},
    'es': {'domain': 'guerrastribales.es', 'icon': ":flag_es:"},
    'ae': {'domain': 'tribalwars.ae', 'icon': ":flag_ae:"},
    'uk': {'domain': 'tribalwars.co.uk', 'icon': ":flag_uk:"},
    'zz': {'domain': 'tribalwars.works', 'icon': ":flag_fm:"},
    'us': {'domain': 'tribalwars.us', 'icon': ":flag_us:"}
}


# custom interaction for simple world implementation
class DSInteraction:
    def __init__(self, _interaction: discord.Interaction):
        self._interaction = _interaction
        self._world = None
        self.server = None
        self.full_command_name = None
        self.command_name = None
        self.is_command = self._interaction.type == discord.InteractionType.application_command

        if self.is_command:
            if self._interaction.command.parent:
                self.command_name = self._interaction.command.parent.name
                self.full_command_name = f"{self._interaction.command.parent.name} {self._interaction.command.name}"
            else:
                self.command_name = self._interaction.command.name
                self.full_command_name = self._interaction.command.name

    # note that this must be getattr, not getattribute
    # this implements the discord.Interaction interface to our class
    def __getattr__(self, attr: str):
        return getattr(self._interaction, attr)

    @property
    def world(self):
        return self._world

    @world.setter
    def world(self, world):
        self._world = world
        self.server = world.server


class DSTree(app_commands.CommandTree):
    def __init__(self, client):
        super().__init__(client)
        self._world = None
        self.server = None
        self.valid_interactions = (
            discord.InteractionType.application_command,
            discord.InteractionType.autocomplete
        )

    async def interaction_check(self, interaction: DSInteraction):
        if interaction.type not in self.valid_interactions:
            return True

        if interaction.guild is None:
            if interaction.is_command and interaction.command_name not in allowed_pm_commands:
                msg = f"Der Bot kann momentan keine privaten Commands"
                await interaction.response.send_message(embed=utils.error_embed(msg))
                return False
            else:
                return True

        interaction.lang = interaction.client.languages['german']
        world_prefix = interaction.client.config.get_world(interaction.channel)
        world = interaction.client.worlds.get(world_prefix)

        if world is not None:
            interaction.world = world
            return True

        elif interaction.full_command_name == "set world":
            return True

        elif interaction.is_command:
            msg = f"Der Server hat keine zugeordnete Welt.\nEin Admin kann dies mit `/set world <world>`"
            await interaction.response.send_message(msg)
            return False
        else:
            return True

    async def _call(self, interaction: discord.Interaction) -> None:
        await super()._call(DSInteraction(interaction))  # noqa (ignore error)


class DSButton(discord.ui.Button):
    def __init__(self, custom_id, row, _callback, emoji=None, label=None, style=None, disabled=False):
        super().__init__()
        self.custom_id = custom_id

        if emoji is not None:
            self.emoji = emoji
        elif label is not None:
            self.label = label

        if style is not None:
            self.style = style

        self.row = row
        self._callback = _callback
        self.disabled = disabled

    async def callback(self, interaction):
        await self._callback(self.custom_id, interaction)


# default tribal wars classes
class DSObject:
    twstats = "https://{0.lang}.twstats.com/{0.world}/index.php?page={0.type}&id={0.id}"
    ds_ultimate = "https://www.ds-ultimate.de/{0.lang}/{1}/{2}/{0.id}"
    ingame = "https://{}/{}.php?screen=info_{}&id={}"

    def __init__(self, data):
        self.id = data['id']
        self.world = data['world']
        self.lang = self.world[:2]
        self.name = utils.decode(data['name'])
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
        return self.twstats.format(self)

    @property
    def ds_ultimate_url(self):
        dstype = "ally" if self.type == "tribe" else self.type
        return self.ds_ultimate.format(self, self.world[2:], dstype)

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
        return self.ingame.format(header, url_type, dstype, self.id)


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
        self.tag = utils.decode(data['tag'])
        self.member = data['member']
        self.villages = data['villages']
        self.all_points = data['all_points']
        self.att_bash = data['att_bash']
        self.att_rank = data['att_rank']
        self.def_bash = data['def_bash']
        self.def_rank = data['def_rank']
        self.sup_bash = data['sup_bash']
        self.sup_rank = data['sup_rank']
        self.all_bash = data['all_bash']
        self.all_rank = data['all_rank']


class Village(DSObject):
    def __init__(self, data):
        super().__init__(data)
        self.x = data['x']
        self.y = data['y']
        self.player_id = data['player_id']
        self.coords = f"{self.x}|{self.y}"


class MapVillage:
    def __init__(self, data):
        self.data = data
        self.id = data['id']
        self.x = 1501 + 5 * (data['x'] - 500)
        self.y = 1501 + 5 * (data['y'] - 500)
        self.player_id = data['player_id']
        self.rank = data['rank']

    def reposition(self, difference):
        self.x -= difference[0]
        self.y -= difference[1]
        return self.x, self.y


class Conquer:
    def __init__(self, world, data):
        self.world = world
        self.village_id = data[0]
        self.unix = data[1]
        self.new_player_id = data[2]
        self.old_player_id = data[3]
        self.village = None

    @property
    def time(self):
        return utils.from_timestamp(self.unix)

    @property
    def player_ids(self):
        return self.new_player_id, self.old_player_id

    @property
    def coords(self):
        return f"{self.village.x}|{self.village.y}"

    @property
    def grey_conquer(self):
        return self.old_player_id == 0

    @property
    def self_conquer(self):
        return self.old_player_id == self.new_player_id


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
    world_title = {
        'def': "Welt",
        'p': "Casual",
        'c': "Sonderwelt",
        's': "SDS"
    }

    def __init__(self, data=None):
        self.server = data['world']
        self.speed = data['speed']
        self.unit_speed = data['unit_speed']
        self.moral = data['moral']
        self.config = json.loads(data['config'])

        self.lang, self.type, self.number = self.parse(self.server)
        self.title = self.world_title.get(self.type)

        pkg = world_data.get(self.lang)
        self.domain, self.icon = pkg.values()
        self.url = f"{self.server}.{self.domain}"

    def __str__(self):
        return self.represent()

    def __eq__(self, other):
        if isinstance(other, DSWorld):
            return self.server == other.server
        else:
            return False

    def represent(self, clean=False, plain=True):
        name = f"{self.title} {self.number}"
        if clean is True:
            return name
        elif plain is True:
            return f"{name} {self.icon}"
        else:
            return f"`{name}` {self.icon}"

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
        return lang, world_type or "def", int(number)


class DSType:
    classes = {'player': Player, 'tribe': Tribe, 'village': Village, 'map': MapVillage}

    def __init__(self, arg, server=None, archive=None):
        self.arg = arg
        self.Class = None
        self.table = None
        self.base_table = None

        response = self.try_convers(self.arg)
        if not response:
            raise ValueError(f"argument: {self.arg} needs to be either enum or tablename")

        self.base_table = self.table

        if archive is not None:
            self.table = f"{self.table}_{archive}"
        elif server is not None:
            self.table = f"{self.table}_{server}"

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
        table = re.match(r'(\D+)\d*', arg)
        if not table:
            return

        self.Class = self.classes.get(table.string)
        if self.Class:

            if arg == "map":
                self.table = "village"
            else:
                self.table = arg

    async def fetch(self, interaction, *args, **kwargs):
        method = getattr(interaction.client, f"fetch_{self.table}")
        response = await method(interaction.server, *args, **kwargs)

        if response is None:
            raise utils.DSUserNotFound(args[0])
        else:
            return response


class DSGames(commands.Cog):
    def __init__(self):
        for command in self.walk_app_commands():
            if isinstance(command, app_commands.Command):
                command.add_check(self.command_check)

    def command_check(self, interaction):
        container = self.get_container(interaction)

        # if it's a list it is a simple cooldown container, and we need to check
        # it since commands with dictionarys need to grab their data on begin
        if isinstance(container, list):
            self.get_game_data(interaction, container)

        return True

    @asynccontextmanager
    async def end_game(self, interaction, time=10):
        container = self.get_container(interaction)
        if isinstance(container, list):
            container.append(interaction.guild.id)
            method = container.remove
        else:
            container[interaction.guild.id] = False
            method = container.pop

        try:
            yield
        finally:
            await asyncio.sleep(time)

            if interaction.guild.id in container:
                method(interaction.guild.id)

    def get_container(self, interaction):
        if interaction.command.parent is not None:
            command_name = f"{interaction.command.parent.name} {interaction.command.name}"
        else:
            command_name = interaction.command.name

        if command_name == "bl":
            container_name = "blackjack"
        elif command_name in ("hg", "guess"):
            container_name = "hangman"
        elif command_name in ("vp start", "vp draw"):
            container_name = "videopoker"
        elif command_name == "ag":
            container_name = "anagram"
        elif command_name in ("dice start", "dice accept"):
            container_name = "dice"
        elif command_name in ("quiz start", "quiz guess"):
            container_name = "quiz"
        else:
            container_name = command_name

        return getattr(self, container_name, {})

    def get_game_data(self, interaction, container=None):
        if container is None:
            container = self.get_container(interaction)

        # no running game
        if interaction.guild.id not in container:
            return

        # list just acts as cooldown container
        if isinstance(container, list):
            raise utils.SilentError

        else:
            data = container[interaction.guild.id]
            # False is the cooldown value
            if data is False:
                raise utils.SilentError
            else:
                return data


class Keyword:
    def __init__(self, sign, value):
        self.sign = sign
        self.value = int(value)

    @classmethod
    def from_str(cls, value):
        match = re.findall(r'([<=>])(\d+)', value)
        if not match:
            return

        self = cls.__new__(cls)
        self.__init__(*match[0])
        return self

    def compare(self, other):
        if self.value is None:
            return True

        if self.sign == "<":
            return other < self.value
        elif self.sign == ">":
            return other > self.value
        else:
            return other == self.value

    def __bool__(self):
        return bool(self.value)

    def to_sql(self, _):
        return f"{self.sign} {self.sign}"


class DSMember:
    def __init__(self, record):
        self.id = record['id']
        self.guild_id = record['guild_id']
        self.name = record['name']
        self.nick = record['nick']
        self.last_update = record['last_update']

    def __eq__(self, other):
        return self.name == other.name and self.nick == other.nick

    @classmethod
    def from_object(cls, member):
        self = cls.__new__(cls)
        self.id = member.id
        self.guild_id = member.guild.id
        self.name = member.name
        self.nick = member.nick
        self.last_update = datetime.now()  # timezone doesn't matter
        return self

    @property
    def arguments(self):
        return (self.id, self.guild_id, self.name,
                self.nick, self.last_update)

    @property
    def display_name(self):
        return self.nick or self.name


class Language:
    def __init__(self, path, name):
        self.params = None

        with open(f"{path}/{name}", encoding='utf-8') as parameters:
            self._dict = yaml.safe_load(parameters)

        cmds = self._dict.pop('commands')
        iterable = list(self._dict.items()) + list(cmds.items())

        for key, value in iterable:
            setattr(self, key, value)


class Coordinate:
    def __init__(self, x=None, y=None):
        self.x = x
        self.y = y

    def __str__(self):
        return f"{self.x}|{self.y}"

    @classmethod
    def from_str(cls, value):
        coord = re.match(r'\d\d\d\|\d\d\d', value)

        if not coord:
            return None

        self = cls.__new__(cls)
        raw_x, raw_y = coord.string.split("|")
        self.x = int(raw_x)
        self.y = int(raw_y)
        return self

    @classmethod
    def from_known_str(cls, value):
        self = cls.__new__(cls)
        raw_x, raw_y = value.split("|")
        self.x = int(raw_x)
        self.y = int(raw_y)
        return self
