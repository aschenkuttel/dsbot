from discord.ext import commands


class GameChannelMissing(commands.CheckFailure):
    pass


class WrongChannel(commands.CheckFailure):
    def __init__(self, channeltype):
        self.type = channeltype


class WorldMissing(commands.CheckFailure):
    pass


class UnknownWorld(commands.CheckFailure):
    def __init__(self, possible):
        self.possible = possible


class MissingGucci(commands.CheckFailure):
    def __init__(self, purse):
        self.purse = purse


class InvalidBet(commands.CheckFailure):
    def __init__(self, low, high):
        self.low = low
        self.high = high


class IngameError(commands.CheckFailure):
    def __init__(self, ingame):
        self.ingame = not ingame


class DontPingMe(commands.CheckFailure):
    pass


class DSUserNotFound(commands.CheckFailure):
    def __init__(self, searchable):
        self.name = searchable


class GuildUserNotFound(commands.CheckFailure):
    def __init__(self, searchable):
        self.name = searchable
