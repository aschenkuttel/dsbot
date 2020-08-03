from utils.error import WrongChannel, GameChannelMissing
from urllib.parse import quote_plus, unquote_plus
from discord.ext import commands
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
    troops = re.findall(r'[A-z]*=\S*', options or "")
    cache = {}
    for troop in troops:

        if troop.count("=") != 1:
            continue

        orig_key, input_value = troop.split("=")
        key, value = orig_key.lower(), input_value.lower()

        try:
            cache[key] = int(value)
        except ValueError:
            if value in ["true", "false"]:
                cache[key] = value == "true"
            else:
                cache[key] = input_value

    for argument, default_value in kwargs.items():
        user_input = cache.get(argument)
        new_value = user_input

        if isinstance(default_value, (list, int)):
            if isinstance(default_value, int):
                default_value = [default_value, default_value]

            minimum, maximum = default_value
            if not isinstance(user_input, int) or user_input < minimum:
                new_value = minimum

            elif user_input > maximum:
                new_value = maximum

        elif user_input is None:
            new_value = default_value

        kwargs[argument] = new_value

    return kwargs.values()


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
