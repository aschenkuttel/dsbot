from discord.ext import commands


class GameChannelMissing(commands.CheckFailure):
    def __str__(self):
        return "missing channel"


class WrongChannel(commands.CheckFailure):
    def __str__(self):
        return "wrong channel"


class WorldMissing(commands.CheckFailure):
    def __str__(self):
        return "missing world"


class UnknownWorld(commands.CheckFailure):
    def __init__(self, searchable):
        self.name = searchable


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
