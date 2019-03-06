from utils import converter, DSUserNotFound, GuildUserNotFound, DontPingMe
from data.naruto import *
from discord.ext import commands
from PIL import Image, ImageChops
from bs4 import BeautifulSoup
from data.cogs import cmds
import asyncpg
import datetime
import operator
import aiohttp
import asyncio
import discord
import imgkit
import random
import json
import time
import math
import os
import io
import re

options = {
    # "xvfb": "",
    "quiet": "",
    "format": "png",
    "quality": 100,
    "encoding": "UTF-8"
}

fml = '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0' \
      ' Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">' \
      '<html xmlns="http://www.w3.org/1999/xhtml">'


class Player:
    def __init__(self, dct):
        self.id = dct['id']
        self.alone = True
        self.name = converter(dct['name'])
        self.tribe_id = dct['tribe_id']
        self.villages = dct['villages']
        self.points = dct['points']
        self.rank = dct['rank']
        self.att_bash = dct['att_bash']
        self.att_rank = dct['att_rank']
        self.def_bash = dct['def_bash']
        self.def_rank = dct['def_rank']
        self.all_bash = dct['all_bash']
        self.all_rank = dct['all_rank']
        self.ut_bash = self.all_bash - self.def_bash - self.att_bash


class Tribe:
    def __init__(self, dct):
        self.id = int(dct['id'])
        self.alone = False
        self.name = converter(dct['name'])
        self.tag = converter(dct['tag'])
        self.member = dct['member']
        self.villages = dct['villages']
        self.points = dct['points']
        self.all_points = dct['all_points']
        self.rank = dct['rank']
        self.att_bash = dct['att_bash']
        self.att_rank = dct['att_rank']
        self.def_bash = dct['def_bash']
        self.def_rank = dct['def_rank']
        self.all_bash = dct['all_bash']
        self.all_rank = dct['all_rank']


class Village:
    def __init__(self, dct):
        self.id = int(dct['id'])
        self.name = converter(dct['name'])
        self.x = dct['x']
        self.y = dct['y']
        self.player_id = dct['player']
        self.points = dct['points']


class Load:
    def __init__(self):

        self.config = {}
        self.session = None
        self.ress = None
        self.pool = None
        self.secrets = {"CMDS": cmds, "TOKEN": TOKEN, "PRE": pre}
        self.data_loc = f"{os.path.dirname(__file__)}/data/"
        self.url_val = "https://de{}.die-staemme.de/map/ally.txt"
        self.url_set = "https://de{}.die-staemme.de/page/settings"
        self.msg = json.load(open(f"{self.data_loc}msg.json"))

    # Setup
    async def setup(self, loop):
        self.start_up()
        self.session = aiohttp.ClientSession(loop=loop)
        connections = await self.db_connect(loop)
        self.pool, self.ress = connections
        return self.session

    # DB Connect
    async def db_connect(self, loop):
        result = []
        database = 'tribaldata', 'userdata'
        for table in database:
            conn_data = {"host": '46.101.105.115', "port": db_port, "user": db_user,
                         "password": db_key, "database": table, "loop": loop}
            cache = await asyncpg.create_pool(**conn_data)
            result.append(cache)
        return result

    # Casual
    def casual(self, world):
        return world if world > 50 else f"p{world}"

    # Config Load at Start
    def config_loader(self):
        cache = json.load(open(f"{self.data_loc}config.json"))
        data = {int(key): value for key, value in cache.items()}
        self.config.update(data)

    # Get Config Entry
    def get_config(self, guild_id, item):
        config = self.config.get(guild_id)
        if config is None:
            return
        return config.get(item)

    # Change Config Entry
    def change_config(self, guild_id, item, value):
        if guild_id not in self.config:
            self.config[guild_id] = {}
        self.config[guild_id][item] = value
        self.save_config()

    # Remove Config Entry
    def remove_config(self, guild_id, item):
        config = self.config.get(guild_id)
        if not config:
            return
        job = config.pop(item, None)
        self.save_config()
        return job

    # Get Server Sub or Main World
    def get_world(self, channel, url=False):
        con = self.config.get(channel.guild.id)
        if con is None:
            return
        chan = con.get("channel")
        main = con.get("world")
        idc = str(channel.id)

        world = chan.get(idc, main) if chan else main

        if url and world:
            return self.casual(world)
        return world

    # Get Server Main World
    def get_guild_world(self, guild, url=False):
        con = self.config.get(guild.id)
        if con is None:
            return
        world = con.get('world')
        if url and world:
            return self.casual(world)
        return world

    # Get Server Prefix
    def pre_fix(self, guild_id):
        config = self.config.get(guild_id)
        if config is None:
            return self.secrets["PRE"]
        default = self.secrets["PRE"]
        return config.get("prefix", default)

    # --- Saves Config in File --- #
    def save_config(self):
        json.dump(self.config, open(f"{self.data_loc}config.json", 'w'))

    # --- Ram Save --- #
    async def save_user_data(self, user_id, amount):
        statement = "SELECT * FROM iron_data WHERE id = {}"
        conn = await self.ress.acquire()
        data = await conn.fetchrow(statement.format(user_id))
        statement = "INSERT INTO iron_data(id, amount) VALUES({0}, {1}) " \
                    "ON CONFLICT (id) DO UPDATE SET id={0}, amount={1}"
        new_amount = data["amount"] + amount if data else amount
        await conn.execute(statement.format(user_id, new_amount))
        await self.ress.release(conn)

    # --- Ram Data Search --- #
    async def get_user_data(self, user_id, info=False):
        statement = "SELECT * FROM iron_data"
        conn = await self.ress.acquire()
        data = await conn.fetch(statement)
        cache = {cur["id"]: cur["amount"] for cur in data}
        await self.ress.release(conn)
        rank = "Unknown"
        sort = sorted(cache.items(), key=lambda kv: kv[1], reverse=True)
        for index, (idc, cash) in enumerate(sort):
            if idc == user_id:
                rank = index + 1
        money = cache.get(user_id, 0)
        return (money, rank) if info else money

    # --- Ram Data Search Top --- #
    async def get_user_top(self, amount, guild=None):
        conn = await self.ress.acquire()
        if guild:
            statement = "SELECT * FROM iron_data WHERE id IN ({}) " \
                        "ORDER BY amount DESC LIMIT $1"
            member = ', '.join([str(mem.id) for mem in guild.members])
            data = await conn.fetch(statement.format(member), amount)
            return data
        else:
            statement = "SELECT * FROM iron_data ORDER BY amount DESC LIMIT $1"
            data = await conn.fetch(statement, amount)
        await self.ress.release(conn)
        return data

    # Download Settings / World Data
    async def data_getter(self, world, settings=False):
        url = (self.url_set if settings else self.url_val).format(world)
        async with self.session as cs:
            async with cs.get(url) as r:
                return await r.text()

    # Conquer Data Download
    async def conquer_data(self, world):
        cur = time.time() - 3600
        base = "http://de{}.die-staemme.de/interface.php?func=get_conquer&since={}"
        url = base.format(self.casual(world), cur)
        async with self.session.get(url) as r:
            data = await r.read()
        return data.decode("utf-8").split("\n")

    # Download Report Data
    async def get_report(self, url):
        try:
            resp = await self.session.get(url)
            return await resp.text()
        except (aiohttp.InvalidURL, ValueError):
            return None

    # Save Command Usage
    async def save_usage_cmd(self, cmd):
        cmd = cmd.lower()
        conn = await self.ress.acquire()

        statement = "SELECT * FROM usage_data WHERE name = $1"
        data = await conn.fetchrow(statement, cmd)

        query = "INSERT INTO usage_data(name, usage) VALUES($1, $2) " \
                "ON CONFLICT (name) DO UPDATE SET name=$1, usage=$2"

        new_usage = data['usage'] + 1 if data else 1
        await conn.execute(query, cmd, new_usage)
        await self.ress.release(conn)

    # Return Sorted Command Usage Stats
    async def get_usage(self):
        conn = await self.ress.acquire()
        statement = "SELECT * FROM usage_data"
        data = await conn.fetch(statement)
        cache = {r['name']: r['usage'] for r in data}
        return sorted(cache.items(), key=operator.itemgetter(1), reverse=True)

    # World Valid Check
    async def is_valid(self, world):
        query = "SELECT table_name FROM information_schema.tables " \
                "WHERE table_schema='public' AND table_type='BASE TABLE';"
        conn = await self.pool.acquire()
        result = await conn.fetch(query)
        await self.pool.release(conn)
        worlds = [dct["table_name"][2:] for dct in result]
        return True if str(world) in worlds else False

    # Random Player
    async def random_id(self, world, **kwargs):

        amount = kwargs.get("amount", 1)
        top = kwargs.get("top", 500)
        tribe = kwargs.get("tribe", False)
        least = kwargs.get("least", False)

        state = "t" if tribe else "p"

        statement = f"SELECT * FROM {state}_{world} WHERE rank < {top + 1}"
        conn = await self.pool.acquire()
        data = await conn.fetch(statement)
        await self.pool.release(conn)

        result = []
        while len(result) < amount:
            ds_obj = random.choice(data)
            cur = [p.id for p in result]
            if ds_obj['id'] not in cur:
                if not tribe:
                    result.append(Player(ds_obj))
                    continue
                if least and int(ds_obj['member']) > 3:
                    result.append(Tribe(ds_obj))
                if not least:
                    result.append(Tribe(ds_obj))

        return result[0] if amount == 1 else result

    # Find Village
    async def find_village_data(self, world, coord=None, idc=None):
        if coord:
            x, y = coord.partition("|")[0], coord.partition("|")[2]
            statement = "SELECT * FROM v_{} WHERE x = $1 AND y = $2;"
            query, searchable = statement.format(world), [int(x), int(y)]
        else:
            statement = "SELECT * FROM v_{} WHERE id = $1;"
            query, searchable = statement.format(world), [idc]

        conn = await self.pool.acquire()
        result = await conn.fetchrow(query, *searchable)
        await self.pool.release(conn)
        return Village(result) if result else None

    # Find Player
    async def find_player_data(self, world, name=None, idc=None):
        if name:
            name = converter(name.lower(), True)
            statement = "SELECT * FROM p_{} WHERE LOWER(name) = $1;"
            query = statement.format(world)
        else:
            statement = "SELECT * FROM p_{} WHERE id = $1;"
            query = statement.format(world)

        searchable = name if name else idc
        conn = await self.pool.acquire()
        result = await conn.fetchrow(query, searchable)
        await self.pool.release(conn)
        return Player(result) if result else None

    # Find Tribe
    async def find_ally_data(self, world, name=None, idc=None):
        if name:
            name = converter(name.lower(), True)
            statement = "SELECT * FROM t_{0} WHERE LOWER(name) = $1 OR LOWER(tag) = $1;"
            query = statement.format(world)
        else:
            statement = "SELECT * FROM t_{} WHERE id = $1;"
            query = statement.format(world)

        searchable = name if name else idc
        conn = await self.pool.acquire()
        result = await conn.fetchrow(query, searchable)
        await self.pool.release(conn)
        return Tribe(result) if result else None

    # Find Tribe/Player
    async def find_both_data(self, name, world):
        player = await self.find_player_data(world, name=name)
        tribe = await self.find_ally_data(world, name=name)
        if player and tribe or player:
            return player
        if tribe:
            return tribe

    # Find Tribe Players
    async def find_ally_player(self, allys, world, idc=False):
        if idc is False:
            tribes = []
            for ally in allys:
                tribe = await self.find_ally_data(world, name=ally)
                if not tribe:
                    return ally
                if tribe.id not in tribes:
                    tribes.append(tribe.id)
        else:
            tribes = allys
        result = []
        for ally in tribes:
            statement = "SELECT * FROM p_{} WHERE tribe_id = {};"
            query = statement.format(world, ally)
            conn = await self.pool.acquire()
            res = await conn.fetch(query)
            await self.pool.release(conn)
            for cur in res:
                result.append(converter(cur['name']))

        return result

    # Get Specific Village Set
    async def get_villages(self, obj, num, world, k=None):
        res = []
        conn = await self.pool.acquire()

        if isinstance(obj, Tribe):
            statement = "SELECT * FROM p_{} WHERE tribe_id = {};"
            query = statement.format(world, obj.id)
            cache = await conn.fetch(query)
            for cur in cache:
                res.append(cur["id"])

        else:
            res.append(obj.id)

        statement = "SELECT * FROM v_{} WHERE player IN ({})"
        if k:
            temp = " AND LEFT(CAST(x AS TEXT), 1) = '{}'" \
                   " AND LEFT(CAST(y AS TEXT), 1) = '{}'"
            statement = statement + temp.format(k[2], k[1])

        query = statement.format(world, ', '.join([str(c) for c in res]))
        result = await conn.fetch(query)
        await self.pool.release(conn)
        random.shuffle(result)
        en_lis = result

        state = k if k else False
        if str(num).isdigit():
            en_lis = result[:int(num)]
            if len(result) < int(num):
                return obj.alone, obj.name, state, len(result)
        if len(result) == 0:
            return obj.alone, obj.name, state, len(result)
        if not len(en_lis) > 1000:
            return en_lis
        file = io.StringIO()
        file.write(f'{os.linesep}'.join(en_lis))
        file.seek(0)
        return file

    # Coord Converter
    async def coordverter(self, coord_list, guild_id):
        world = self.get_world(guild_id)
        result = []
        double = []
        fail = []

        for coord in coord_list:

            res = await self.find_village_data(world, coord=coord)
            if not res:
                fail.append(coord) if coord not in fail else None
                continue

            if coord in double:
                continue

            url = "https://de{}.die-staemme.de/game.php?&screen=info_village&id={}"
            if res.player_id:
                player = await self.find_player_data(world, idc=res.player_id)
                v1 = f"[{player.name}]"
            else:
                v1 = "[Barbarendorf]"
            result.append(f"[{coord}]({url.format(world, res.id)}) {v1}")
            double.append(coord)

        shit = '\n'.join(result) if result else None
        piss = ', '.join(fail) if fail else None
        found = f"**Gefundene Koordinaten:**\n{shit}" if shit else ""
        lost = f"**Nicht gefunden:**\n{piss}" if piss else ""
        return found, lost

    # Conquer Main Function
    async def conquer_feed(self, guilds):
        for guild in guilds:
            world = self.get_guild_world(guild)
            if not world:
                continue
            channel_id = self.get_config(guild.id, "conquer")
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            tribe = self.get_config(guild.id, "tribe")
            data = await self.conquers(world, tribe)
            if not data:
                continue

            res_cache = []
            once = data[0]
            for sen in data[1]:
                res_cache.append(sen)
                if len(res_cache) == 5:
                    embed = discord.Embed(title=once, description='\n'.join(res_cache))
                    await self.silencer(channel.send(embed=embed))
                    res_cache.clear()
                    once = ""
                    await asyncio.sleep(1)
            if res_cache:
                embed = discord.Embed(title=once, description='\n'.join(res_cache))
                await self.silencer(channel.send(embed=embed))

    # Parse Conquer Data
    async def conquers(self, world, tribe):
        data = await self.conquer_data(world)
        id_list = None
        if not data:
            return None
        if tribe:
            id_list = await self.find_ally_ids(world, tribe)
        res_lis = []
        date = None
        for line in data:
            if line.count(",") != 3:
                continue
            vil_id, unix_time, new_owner, old_owner = line.split(",")
            player_idc = [int(new_owner), int(old_owner)]
            if tribe and not any(idc in id_list for idc in player_idc):
                continue
            vil = await self.find_village_data(world, idc=int(vil_id))
            if not vil:
                continue

            ally = self.find_ally_data
            base = f"https://de{world}.die-staemme.de/game.php?&screen="
            res_vil = f"[{vil.x}|{vil.y}]({base}info_village&id={vil.id})"

            res_new = "Barbarendorf"
            res_old = "(Barbarendorf)"

            new = await self.find_player_data(world, idc=int(new_owner))
            if new:
                url_n = f"[{new.name}]({base}info_player&id={new.id})"
                cache = await ally(world, idc=new.tribe_id) if new.tribe_id else None
                new_tribe = f" **{cache.tag}**" if cache else f""
                res_new = f"{url_n}{new_tribe}"

            old = await self.find_player_data(world, idc=int(old_owner))
            if old:
                url_o = f"[{old.name}]({base}info_player&id={old.id})"
                cache = await ally(world, idc=old.tribe_id) if old.tribe_id else None
                old_tribe = f" **{cache.tag}**" if cache else ""
                res_old = f"von {url_o}{old_tribe}"

            now = datetime.datetime.utcfromtimestamp(int(unix_time)) + datetime.timedelta(hours=1)
            date, now = now.strftime('%d-%m-%Y'), now.strftime('%H:%M')
            res_lis.append(f"`{now}` | {res_new} adelt {res_vil} {res_old}")
        return date, res_lis

    # Find Player from Ally
    async def find_ally_ids(self, world, tribe_id):
        statement = "SELECT * FROM p_{} WHERE tribe_id = {};"
        query = statement.format(world, tribe_id)
        conn = await self.pool.acquire()
        res = await conn.fetch(query)
        await self.pool.release(conn)
        return [cur['id'] for cur in res]

    # Recap Argument Handler
    async def re_handler(self, world, args):
        days = 7
        if ' ' not in args:
            player = await self.find_both_data(args, world)
        elif args.split(" ")[-1].isdigit():
            player = await self.find_both_data(' '.join(args.split(" ")[:-1]), world)
            if not player:
                player = await self.find_both_data(args, world)
            else:
                days = int(args.split(" ")[-1])
        else:
            player = await self.find_both_data(args, world)
        if not player:
            raise DSUserNotFound(args, world)
        return player, days

    # Village Argument Handler
    async def vil_handler(self, world, args):
        con = None
        args = args.split(" ")
        if len(args) == 1:
            name = args[0]
        elif re.match(r'[k, K]\d\d', args[-1]):
            con = args[-1]
            name = ' '.join(args[:-1])
        else:
            name = ' '.join(args)
        player = await self.find_both_data(name, world)
        if not player:
            if con:
                player = await self.find_both_data(f"{name}{con}", world)
                if not player:
                    raise DSUserNotFound(name, world)
            else:
                raise DSUserNotFound(name, world)
        return player, con

    # Report HTML Converting
    async def html_lover(self, raw_data):
        soup = BeautifulSoup(raw_data, 'html.parser')
        tiles = soup.body.find_all(class_="vis")
        if len(tiles) < 2:
            return

        main = tiles[1]
        main = f"{fml}<head></head>{main}"  # don't ask me why...

        css = f"{os.path.dirname(__file__)}/data/report.css"

        img = imgkit.from_string(main, False, options=options, css=css)
        return img

    # Barbershop
    async def trim(self, im):
        bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
        diff = ImageChops.difference(im, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        bbox = diff.getbbox()
        if bbox:
            return im.crop(bbox)

    # Main Report Func
    async def report_func(self, url):
        if not url.startswith("http"):
            url = f"http{url.split('http')[1]}"

        data = await self.get_report(url)
        if not data:
            return

        img_bytes = await self.html_lover(data)
        if not img_bytes:
            return False

        data_io = io.BytesIO(img_bytes)
        image = Image.open(data_io)
        img = await self.trim(image)
        img = img.crop((2, 2, img.width - 2, img.height - 2))
        file = io.BytesIO()
        img.save(file, "png")
        file.seek(0)
        return file

    def get_seconds(self):
        now = datetime.datetime.now()
        clean = now + datetime.timedelta(hours=1)
        goal_time = clean.replace(minute=0, second=0, microsecond=0)
        start_time = now.replace(microsecond=0)
        goal = (goal_time - start_time).seconds
        return goal

    # Scavenge Maths
    def scavenge(self, state, troops):
        sca1 = []
        sca2 = []
        sca3 = []
        sca4 = []
        if state == 3:
            for element in troops:
                sca1.append(str(math.floor((5 / 8) * element)))
                sca2.append(str(math.floor((2 / 8) * element)))
                sca3.append(str(math.floor((1 / 8) * element)))
        if state == 4:
            for element in troops:
                sca1.append(str(math.floor(0.5765 * element)))
                sca2.append(str(math.floor(0.23 * element)))
                sca3.append(str(math.floor(0.1155 * element)))
                sca4.append(str(math.floor(0.077 * element)))

        return sca1, sca2, sca3, sca4

    # Silence Method
    async def silencer(self, coro):
        try:
            await coro
        except discord.Forbidden:
            pass

    # Start Up Function
    def start_up(self):
        self.config_loader()


class GuildUser(commands.Converter):
    def __init__(self):
        self.id = None
        self.name = None
        self.display_name = None
        self.avatar_url = None

    async def convert(self, ctx, arg):
        if re.match(r'<@!?([0-9]+)>$', arg):
            raise DontPingMe
        for m in ctx.guild.members:
            if m.display_name.lower() == arg.lower():
                return m
            if m.name.lower() == arg.lower():
                return m
        else:
            raise GuildUserNotFound(arg)


class DSObject(commands.Converter):

    def __init__(self):
        self.id = None
        self.name = None
        self.alone = None
        self.tribe_id = None
        self.villages = None
        self.points = None
        self.rank = None
        self.att_bash = None
        self.att_rank = None
        self.def_bash = None
        self.def_rank = None
        self.all_bash = None
        self.all_rank = None
        self.ut_bash = None
        self.member = None
        self.world = None

    async def convert(self, ctx, searchable):
        world = load.get_world(ctx.channel)
        obj = await load.find_both_data(searchable, world)
        if not obj:
            raise DSUserNotFound(searchable, world)
        return obj


# Main Class
load = Load()
