from utils.error import WrongChannel, GameChannelMissing
from urllib.parse import quote_plus, unquote_plus
from discord import app_commands
import logging
import discord

imgkit = {
    'quiet': "",
    'quality': 100,
    'format': "png",
    'encoding': "UTF-8"
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
def encode(name):
    encoded = quote_plus(name)
    encoded = encoded.replace('~', '%7E')
    return encoded.lower()


def decode(name):
    return unquote_plus(name)


def parse_integer(user_input, default, boundaries=None):
    if not isinstance(user_input, int):
        return default
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
def error_embed(text, interaction=None):
    embed = discord.Embed(description=text, color=discord.Color.red())
    if interaction:
        command = interaction.command.parent or interaction.command
        help_text = f"Erklärung und Beispiel mit /help {command.name}"
        embed.set_footer(text=help_text)

    return embed


def complete_embed(text):
    return discord.Embed(description=text, color=discord.Color.green())


def show_list(iterable, sep=", ", line_break=2, return_iter=False):
    cache = []

    if return_iter is True:
        result = []
    else:
        result = ""

    for word in iterable:
        cache.append(word)
        last = word == iterable[-1]

        if len(cache) == line_break or last:
            enter = "" if last else "\n"
            line = f"{sep}".join(cache)

            if return_iter is True:
                result.append(line)
            else:
                result += f"{line}{enter}"

            cache.clear()

    return result


def unpack_join(record):
    rows = []
    tmp_row = {}
    for key, value in record.items():
        if key in tmp_row:
            rows.append(tmp_row.copy())
            tmp_row.clear()

        tmp_row[key] = value

    if tmp_row:
        rows.append(tmp_row)

    return rows


def game_channel_only():
    def predicate(interaction):
        config = interaction.client.config
        chan = config.get('game', interaction.guild.id)
        if not chan:
            raise GameChannelMissing()
        if chan == interaction.channel_id:
            return True
        raise WrongChannel('game')

    return app_commands.check(predicate)


def bot_has_permissions(**perms):
    invalid = set(perms) - set(app_commands.checks.Permissions.VALID_FLAGS)
    if invalid:
        raise TypeError(f"Invalid permission(s): {', '.join(invalid)}")

    def predicate(interaction) -> bool:
        if interaction.guild is None:
            return True

        permissions = interaction.app_permissions
        missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]

        if not missing:
            return True

        raise app_commands.BotMissingPermissions(missing)

    return app_commands.check(predicate)


def create_logger(name, datapath):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename=f"{datapath}/{name}.log", encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    return logger


def sort_list(iterable):
    cache = []
    result = []
    sorted_by_length = sorted(iterable, key=lambda v: len(v))
    for value in sorted_by_length + [""]:

        if cache:
            if len(value) == len(cache[0]):
                cache.append(value)

            elif (value + cache[0]).count("[") > 1:
                cache.append(value)

            else:
                abc = sorted(cache.copy())
                result.extend(abc)
                cache = []
                if value:
                    cache.append(value)

        else:
            cache.append(value)

    return result
