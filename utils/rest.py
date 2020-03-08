from utils.error import WrongChannel, GameChannelMissing
from urllib.parse import quote_plus, unquote_plus
from discord.ext import commands
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


# quote_plus doesn't convert tildes somehow :(
def converter(name, php=False):
    if php:
        encoded = quote_plus(name)
        encoded = encoded.replace('~', '%7E')
        return encoded.lower()
    else:
        return unquote_plus(name)


def keyword(options, **kwargs):
    troops = re.findall(r'[A-z]*=\d*', options or "")
    cache = {}
    for troop in troops:
        key, value = troop.split("=")
        try:
            cache[key.lower()] = int(value)
        except ValueError:
            continue

    for key, value in kwargs.items():
        user_input = cache.get(key)
        new_value = user_input
        if isinstance(value, list):
            default, maximum = value
            if user_input is None:
                new_value = default
            elif user_input > maximum:
                new_value = maximum
        elif user_input is None:
            new_value = value

        kwargs[key] = new_value
    return kwargs.values()


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
        config = ctx.bot.config
        chan = config.get_item(ctx.guild.id, "game")
        if not chan:
            raise GameChannelMissing()
        if chan == ctx.channel.id:
            return True
        raise WrongChannel()

    return commands.check(predicate)
