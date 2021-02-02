from discord.ext import commands


class EmbedFailure(commands.CheckFailure):
    pass


class HelpFailure(commands.CheckFailure):
    pass


class MissingRequiredKey(HelpFailure):
    def __init__(self, keys, arg=None):
        self.keys = list(keys)
        self.pos_arg = arg
        super().__init__('missing required key')


class MissingRequiredArgument(HelpFailure):
    def __init__(self, argument):
        self.arg = argument
        super().__init__('missing required arg')


class ArgumentOutOfRange(commands.CheckFailure):
    def __init__(self, low, high, item):
        self.min = low
        self.max = high
        self.item = item
        super().__init__('out of range')


class GameChannelMissing(EmbedFailure):
    def __init__(self):
        super().__init__('missing game channel')


class WrongChannel(commands.CheckFailure):
    def __init__(self, channeltype):
        self.type = channeltype
        super().__init__('cmd not in game channel')


class WorldMissing(commands.CheckFailure):
    def __init__(self):
        super().__init__('no guild world')


class UnknownWorld(HelpFailure):
    def __init__(self, possible):
        self.possible_world = possible
        super().__init__('unknown world')


class InvalidCoordinate(commands.CheckFailure):
    def __init__(self):
        super().__init__('invalid coordinate')


class MissingGucci(commands.CheckFailure):
    def __init__(self, purse):
        self.purse = purse
        super().__init__('not enough iron')


class IngameError(commands.CheckFailure):
    def __init__(self, ingame):
        self.ingame = not ingame
        super().__init__('another game running')


class SilentError(commands.CheckFailure):
    pass


class DontPingMe(HelpFailure):
    def __init__(self):
        super().__init__('discord mention instead of username')


class DSUserNotFound(commands.CheckFailure):
    def __init__(self, searchable):
        self.name = searchable
        super().__init__('dsobj not found')


class MemberNotFound(commands.CheckFailure):
    def __init__(self, searchable):
        self.name = searchable
        super().__init__('discord user not found')
