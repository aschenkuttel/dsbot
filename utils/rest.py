from utils.error import WrongChannel, GameChannelMissing
from urllib.parse import quote_plus, unquote_plus
from discord.ext import commands
from utils import Keyword
import logging
import discord
import re

imgkit = {
    'quiet': "",
    'format': "png",
    'quality': 100,
    'encoding': "UTF-8",
}

whymtl = '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE html PUBLIC "' \
         '-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/' \
         'TR/xhtml1/DTD/xhtml1-transitional.dtd"> <html xmlns=' \
         '"http://www.w3.org/1999/xhtml">'


def seperator(number):
    return "{0:,}".format(int(number)).replace(",", ".")


# ignores missing perm error
async def silencer(coro):
    try:
        response = await coro
        return response
    except (discord.Forbidden, discord.HTTPException):
        return False


# quote_plus doesn't convert tildes somehow :(
def converter(name, php=False):
    if php:
        encoded = quote_plus(name)
        encoded = encoded.replace('~', '%7E')
        return encoded.lower()
    else:
        return unquote_plus(name)


def keyword(options, **kwargs):
    troops = re.findall(r'[A-z]*[<=>]\S*', options or "")
    cache = {}

    for troop in troops:
        sign = re.findall(r'[<=>]', troop.lower())[0]
        if troop.count(sign) != 1:
            continue

        orig_key, input_value = troop.split(sign)
        key, value = orig_key.lower(), input_value.lower()

        if input_value.isdigit():
            true_value = int(value)

        elif value in ["true", "false"]:
            true_value = value == "true"

        else:
            true_value = input_value

        cache[key] = [sign, true_value]

    for argument, default_value in kwargs.items():
        input_pkg = cache.get(argument)

        if input_pkg is None:
            if isinstance(default_value, list):
                num = 1 if len(default_value) == 3 else 0
                default_value = num

            kwargs[argument] = Keyword(default_value)
            continue

        else:
            sign, user_input = input_pkg

        new_value = user_input
        if default_value in [False, True]:
            if not isinstance(user_input, bool):
                new_value = default_value

        elif isinstance(default_value, list):
            if len(default_value) == 3:
                minimum, default, maximum = default_value
            else:
                minimum, maximum = default_value
                default = minimum

            new_value = parse_integer(user_input, default, [minimum, maximum])

        elif isinstance(default_value, int):
            new_value = parse_integer(user_input, default_value)

        kwargs[argument] = Keyword(new_value, sign)

    return list(kwargs.values())


def parse_integer(user_input, default, boundaries=None):
    if not isinstance(user_input, int):
        result = default
    else:
        result = user_input

    if boundaries:
        minimum, maximum = boundaries
        if user_input < minimum:
            result = minimum
        elif user_input > maximum:
            result = maximum

    return result


# default embeds
def error_embed(text, ctx=None):
    embed = discord.Embed(description=text, color=discord.Color.red())
    if ctx:
        command = ctx.command.parent or ctx.command
        help_text = f"Erklärung und Beispiel mit {ctx.prefix}help {command}"
        embed.set_footer(text=help_text)
    return embed


def complete_embed(text):
    return discord.Embed(description=text, color=discord.Color.green())


def show_list(iterable, sep=", ", line_break=2):
    cache = []
    result = ""
    for word in iterable:
        cache.append(word)
        last = word == iterable[-1]
        if len(cache) == line_break or last:
            enter = "" if last else "\n"
            line = f"{sep}".join(cache)
            result += f"{line}{enter}"
            cache.clear()

    return result


def game_channel_only():
    def predicate(ctx):
        config = ctx.bot.config
        chan = config.get_item(ctx.guild.id, "game")
        if not chan:
            raise GameChannelMissing()
        if chan == ctx.channel.id:
            return True
        raise WrongChannel('game')

    return commands.check(predicate)


def create_logger(name, halfway):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    path = f"{halfway}/data/{name}.log"
    handler = logging.FileHandler(filename=path, encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    return logger
