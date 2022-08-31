from utils.error import WrongChannel, GameChannelMissing, ArgumentOutOfRange
from urllib.parse import quote_plus, unquote_plus
from discord import app_commands
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
def encode(name):
    encoded = quote_plus(name)
    encoded = encoded.replace('~', '%7E')
    return encoded.lower()


def decode(name):
    return unquote_plus(name)


def keyword(options, strip=False, dct=False, **kwargs):
    raw_input = options or ''
    troops = re.findall(r'[^=\W]{3,}[<=>][^=\s]+', raw_input)
    cache = {}

    for troop in troops:
        if strip:
            raw_input = raw_input.replace(troop, '')

        sign = re.findall(r'[<=>]', troop.lower())[0]
        if troop.count(sign) != 1:
            continue

        orig_key, input_value = troop.split(sign)
        key, value = orig_key.lower(), input_value.lower()
        coords = re.findall(r'(\d{3})\|(\d{3})', value)

        if coords:
            x, y = coords[0]
            true_value = int(x), int(y)

        elif input_value.isdigit():
            true_value = int(value)

        elif value in ("true", "false"):
            true_value = value == "true"

        else:
            true_value = input_value

        cache[key] = [sign, true_value]

    for argument, default_value in kwargs.items():
        input_pkg = cache.get(argument)

        if input_pkg is None:
            if isinstance(default_value, list):
                num = 1 if len(default_value) == 3 else 0
                default_value = default_value[num]

            kwargs[argument] = Keyword(default_value)
            continue

        else:
            sign, user_input = input_pkg

        new_value = user_input
        if default_value is True or default_value is False:
            if not isinstance(user_input, bool):
                new_value = default_value

        elif isinstance(default_value, tuple):
            if not isinstance(user_input, tuple):
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

    result = []
    if strip:
        result.append(raw_input.strip())

    if dct:
        result.append(kwargs)
    else:
        values = list(kwargs.values())
        result.extend(values)

    if len(result) == 1:
        return result[0]
    else:
        return result


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


def valid_range(value, low, high, item):
    if not low <= value <= high:
        raise ArgumentOutOfRange(low, high, item)
