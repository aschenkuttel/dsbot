from discord.ext import commands
import discord

dc = {
    "!": "%21",
    "#": "%23",
    "$": "%24",
    "&": "%26",
    "'": "%27",
    "(": "%28",
    ")": "%29",
    "*": "%2a",
    "+": "%2b",
    "/": "%2f",
    ":": "%3a",
    ";": "%3b",
    "<": "%3c",
    "=": "%3d",
    ">": "%3e",
    "?": "%3f",
    "@": "%40",
    "{": "%7b",
    "|": "%7c",
    "}": "%7d",
    "~": "%7e",
    "[": "%5b",
    "]": "%5d",
    "¢": "%c2%a2",
    "£": "%c2%a3",
    "¥": "%c2%a5",
    "¦": "%c2%a6",
    "§": "%c2%a7",
    "¨": "%c2%a8",
    "©": "%c2%a9",
    "ª": "%c2%aa",
    "«": "%c2%ab",
    "¬": "%c2%ac",
    "®": "%c2%ae",
    "¯": "%c2%af",
    "°": "%c2%b0",
    "±": "%c2%b1",
    "²": "%c2%b2",
    "³": "%c2%b3",
    "´": "%c2%b4",
    "µ": "%c2%b5",
    "¶": "%c2%b6",
    "·": "%c2%b7",
    "¸": "%c2%b8",
    "¹": "%c2%b9",
    "º": "%c2%ba",
    "»": "%c2%bb",
    "¼": "%c2%bc",
    "½": "%c2%bd",
    "¾": "%c2%be",
    "¿": "%c2%bf",
    "À": "%c3%80",
    "Á": "%c3%81",
    "Â": "%c3%82",
    "Ã": "%c3%83",
    "Ä": "%c3%84",
    "Å": "%c3%85",
    "Æ": "%c3%86",
    "Ç": "%c3%87",
    "È": "%c3%88",
    "É": "%c3%89",
    "Ê": "%c3%8a",
    "Ë": "%c3%8b",
    "Ì": "%c3%8c",
    "Í": "%c3%8d",
    "Î": "%c3%8e",
    "Ï": "%c3%8f",
    "Ð": "%c3%90",
    "Ñ": "%c3%91",
    "Ò": "%c3%92",
    "Ó": "%c3%93",
    "Ô": "%c3%94",
    "Õ": "%c3%95",
    "Ö": "%c3%96",
    "×": "%c3%97",
    "Ø": "%c3%98",
    "Ù": "%c3%99",
    "Ú": "%c3%9a",
    "Û": "%c3%9b",
    "Ü": "%c3%9c",
    "Ý": "%c3%9d",
    "Þ": "%c3%9e",
    "ß": "%c3%9f",
    "ã": "%c3%a3",
    "ä": "%c3%a4",
    "å": "%c3%a5",
    "æ": "%c3%a6",
    "ç": "%c3%a7",
    "è": "%c3%a8",
    "é": "%c3%a9",
    "ê": "%c3%aa",
    "ë": "%c3%ab",
    "ì": "%c3%ac",
    "í": "%c3%ad",
    "î": "%c3%ae",
    "ï": "%c3%af",
    "ð": "%c3%b0",
    "ñ": "%c3%b1",
    "ò": "%c3%b2",
    "ó": "%c3%b3",
    "ô": "%c3%b4",
    "õ": "%c3%b5",
    "ö": "%c3%b6",
    "÷": "%c3%b7",
    "ø": "%c3%b8",
    "ù": "%c3%b9",
    "ú": "%c3%ba",
    "û": "%c3%bb",
    "ü": "%c3%bc",
    "ý": "%c3%bd",
    "þ": "%c3%be",
    "ÿ": "%c3%bf"
}


def pcv(number):
    return "{0:,}".format(number).replace(",", ".")


def converter(name, state=False):
    for key, value in dc.items():
        key, value = (key, value) if state else (value, key)
        if name.lower().__contains__(key):
            name = name.replace(key, value).replace(key.upper(), value)
    return name.replace(" ", "+") if state else name.replace("+", " ")


def error_embed(text):
    return discord.Embed(description=text, color=discord.Color.red())


def complete_embed(text):
    return discord.Embed(description=text, color=discord.Color.green())


# Decorator


def private_message_only():
    def predicate(ctx):
        if ctx.guild:
            raise PrivateOnly()
        else:
            return True

    return commands.check(predicate)


def game_channel_only(load):
    def predicate(ctx):
        chan = load.get_config(ctx.guild.id, "game")
        if chan:
            if chan == ctx.channel.id:
                return True
            else:
                raise WrongChannel()
        else:
            raise GameChannelMissing()

    return commands.check(predicate)


# Custom Error


class GameChannelMissing(commands.CheckFailure):
    pass


class WrongChannel(commands.CheckFailure):
    pass


class WorldMissing(commands.CheckFailure):
    pass


class PrivateOnly(commands.CheckFailure):
    pass


class IngameError(commands.CheckFailure):
    pass


class DontPingMe(commands.CheckFailure):
    pass


class DSUserNotFound(commands.CheckFailure):
    def __init__(self, searchable, world):
        self.name = searchable
        self.world = world


class GuildUserNotFound(commands.CheckFailure):
    def __init__(self, searchable):
        self.name = searchable
