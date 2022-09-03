from discord import app_commands


class MissingRequiredKey(app_commands.AppCommandError):
    def __init__(self, keys, arg=None):
        self.keys = list(keys)
        self.pos_arg = arg
        super().__init__('missing required key')


class GameChannelMissing(app_commands.AppCommandError):
    def __init__(self):
        super().__init__('missing game channel')


class ConquerChannelMissing(app_commands.AppCommandError):
    def __init__(self):
        super().__init__('missing conquer channel')


class WrongChannel(app_commands.AppCommandError):
    def __init__(self, channeltype):
        self.type = channeltype
        super().__init__('cmd not in game channel')


class WorldMissing(app_commands.AppCommandError):
    def __init__(self):
        super().__init__('no guild world')


class UnknownWorld(app_commands.AppCommandError):
    def __init__(self, possible):
        self.possible_world = possible
        super().__init__('unknown world')


class InvalidCoordinate(app_commands.AppCommandError):
    def __init__(self):
        super().__init__('invalid coordinate')


class MissingGucci(app_commands.AppCommandError):
    def __init__(self, purse):
        self.purse = purse
        super().__init__('not enough iron')


class SilentError(app_commands.AppCommandError):
    pass


class DontPingMe(app_commands.AppCommandError):
    def __init__(self):
        super().__init__('discord mention instead of username')


class DSUserNotFound(app_commands.AppCommandError):
    def __init__(self, searchable):
        self.name = searchable
        super().__init__('dsobj not found')


class MemberNotFound(app_commands.AppCommandError):
    def __init__(self, searchable):
        self.name = searchable
        super().__init__('discord user not found')
