from PIL import Image, ImageChops
from bs4 import BeautifulSoup
from data.cogs import cmds
from data.naruto import *
import asyncpg
import datetime
import operator
import aiohttp
import asyncio
import discord
import imgkit
import random
import utils
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


class Load:
    def __init__(self):
        self.config = {}
        self.worlds = []
        self.conquer = {}
        self.ress = None
        self.pool = None
        self.session = None
        self.secrets = {"CMDS": cmds, "TOKEN": TOKEN, "PRE": pre}
        self.data_loc = f"{os.path.dirname(__file__)}/data/"
        self.url_val = "https://de{}.die-staemme.de/map/ally.txt"
        self.url_set = "https://de{}.die-staemme.de/page/settings"
        self.msg = json.load(open(f"{self.data_loc}msg.json"))

    # Setup
    async def setup(self, loop):
        self.session = aiohttp.ClientSession(loop=loop)
        connections = await self.db_connect(loop)
        self.pool, self.ress = connections
        self.worlds = await self.fetch_table_worlds()
        self.config_loader()
        return self.session

    # DB Connect
    async def db_connect(self, loop):
        result = []
        database = 'tribaldata', 'userdata'
        for table in database:
            conn_data = {"host": '46.101.105.115', "port": db_port, "user": db_user,
                         "password": db_key, "database": table, "loop": loop, "max_size": 50}
            cache = await asyncpg.create_pool(**conn_data)
            result.append(cache)
        return result

    # Casual
    def casual(self, world):
        return str(world) if world > 50 else f"p{world}"

    # World Check
    def is_valid(self, world):
        return world in self.worlds

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

    # Get World if Main World
    def get_world(self, channel):
        con = self.config.get(channel.guild.id)
        if con is None:
            return
        main = con.get('world')
        if not main:
            return
        chan = con.get("channel")
        idc = str(channel.id)
        world = chan.get(idc, main) if chan else main
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
        default = self.secrets["PRE"]
        if config is None:
            return default
        return config.get("prefix", default)

    # Save Config File
    def save_config(self):
        json.dump(self.config, open(f"{self.data_loc}config.json", 'w'))

    # Ress Data Update
    async def save_user_data(self, user_id, amount):
        statement = "SELECT * FROM iron_data WHERE id = {}"
        conn = await self.ress.acquire()
        data = await conn.fetchrow(statement.format(user_id))
        statement = "INSERT INTO iron_data(id, amount) VALUES({0}, {1}) " \
                    "ON CONFLICT (id) DO UPDATE SET id={0}, amount={1}"
        new_amount = data["amount"] + amount if data else amount
        await conn.execute(statement.format(user_id, new_amount))
        await self.ress.release(conn)

    # Ress Data Fetch
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

    # Search Top
    async def get_user_top(self, amount, guild=None):
        conn = await self.ress.acquire()
        if guild:
            statement = "SELECT * FROM iron_data WHERE id IN " \
                        "({}) ORDER BY amount DESC LIMIT $1"
            member = ', '.join([str(mem.id) for mem in guild.members])
            data = await conn.fetch(statement.format(member), amount)
        else:
            statement = "SELECT * FROM iron_data ORDER BY amount DESC LIMIT $1"
            data = await conn.fetch(statement, amount)
        await self.ress.release(conn)
        return data

    # Download Settings / World Data
    async def data_getter(self, world, settings=False):
        url = (self.url_set if settings else self.url_val).format(world)
        async with self.session.get(url) as r:
            return await r.text()

    # Conquer Data Download
    async def fetch_conquer(self, world, sec=3600):
        cur = time.time() - sec
        base = "http://de{}.die-staemme.de/interface.php?func=get_conquer&since={}"
        url = base.format(self.casual(world), cur)
        async with self.session.get(url) as r:
            data = await r.text("utf-8")
        return data.split("\n")

    # Download Report Data
    async def fetch_report(self, url):
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
        await self.ress.release(conn)
        return sorted(cache.items(), key=operator.itemgetter(1), reverse=True)

    # World Valid Check
    async def fetch_table_worlds(self):
        query = "SELECT table_name FROM information_schema.tables " \
                "WHERE table_schema='public' AND table_type='BASE TABLE';"
        conn = await self.pool.acquire()
        result = await conn.fetch(query)
        await self.pool.release(conn)
        worlds = [dct["table_name"][2:] for dct in result]
        return sorted([int(obj) for obj in set(worlds)])

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
                    result.append(utils.Player(world, ds_obj))
                    continue
                if least and int(ds_obj['member']) > 3:
                    result.append(utils.Tribe(world, ds_obj))
                if not least:
                    result.append(utils.Tribe(world, ds_obj))

        return result[0] if amount == 1 else result

    # Find Village
    async def find_village_data(self, world, searchable, coord=False):
        if coord:
            x, y = searchable.partition("|")[0], searchable.partition("|")[2]
            statement = "SELECT * FROM v_{} WHERE x = $1 AND y = $2;"
            query, searchable = statement.format(world), [int(x), int(y)]
        else:
            statement = "SELECT * FROM v_{} WHERE id = $1;"
            query, searchable = statement.format(world), [searchable]

        conn = await self.pool.acquire()
        result = await conn.fetchrow(query, *searchable)
        await self.pool.release(conn)
        return utils.Village(world, result) if result else None

    # Find Player
    async def find_player_data(self, world, searchable, name=False):
        if name:
            searchable = utils.converter(searchable, True)
            statement = "SELECT * FROM p_{} WHERE LOWER(name) = $1;"
            query = statement.format(world)
        else:
            statement = "SELECT * FROM p_{} WHERE id = $1;"
            query = statement.format(world)

        conn = await self.pool.acquire()
        result = await conn.fetchrow(query, searchable)
        await self.pool.release(conn)
        return utils.Player(world, result) if result else None

    # Find Tribe
    async def find_ally_data(self, world, searchable, name=False):
        if name:
            searchable = utils.converter(searchable, True)
            statement = "SELECT * FROM t_{} WHERE LOWER(tag) = $1 OR LOWER(name) = $1;"
            query = statement.format(world)
        else:
            statement = "SELECT * FROM t_{} WHERE id = $1;"
            query = statement.format(world)

        conn = await self.pool.acquire()
        result = await conn.fetchrow(query, searchable)
        await self.pool.release(conn)
        return utils.Tribe(world, result) if result else None

    # Find Tribe/Player
    async def find_both_data(self, world, name):
        player = await self.find_player_data(world, name, True)
        tribe = await self.find_ally_data(world, name, True)
        if player and tribe or player:
            return player
        if tribe:
            return tribe

    # Find Tribe Players
    async def find_ally_player(self, world, allys, name=False):
        if not isinstance(allys, (tuple, list)):
            allys = [allys]
        if name:
            cache = []
            for ally in allys:
                tribe = await self.find_ally_data(world, ally, True)
                if not tribe:
                    continue
                if tribe.id not in cache:
                    cache.append(tribe.id)
        else:
            cache = allys
        result = []
        conn = await self.pool.acquire()
        for tribe in cache:
            statement = "SELECT * FROM p_{} WHERE tribe_id = {};"
            query = statement.format(world, tribe)
            res = await conn.fetch(query)
            for cur in res:
                result.append(utils.Player(world, cur))
        await self.pool.release(conn)
        return result

    # Find multiple Ally Objects
    async def find_allys(self, world, iterable, name=False):
        conn = await self.pool.acquire()
        if name:
            iterable = [utils.converter(obj, True) for obj in iterable]
            statement = "SELECT * FROM t_{} WHERE ARRAY[LOWER(name), LOWER(tag)] && $1;"
            query = statement.format(world)
        else:
            iterable = [int(obj) for obj in iterable]
            statement = "SELECT * FROM t_{} WHERE id = any($1);"
            query = statement.format(world)

        res = await conn.fetch(query, iterable)
        await self.pool.release(conn)
        return [utils.Tribe(world, cur) for cur in res]

    # Get Specific Village Set
    async def get_villages(self, obj, num, world, k=None):
        res = []
        conn = await self.pool.acquire()

        if isinstance(obj, utils.Tribe):
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
    async def coordverter(self, coord_list, world):
        result = []
        double = []
        fail = []

        for coord in coord_list:

            res = await self.find_village_data(world, coord, True)
            if not res:
                fail.append(coord) if coord not in fail else None
                continue

            if coord in double:
                continue

            url = "https://de{}.die-staemme.de/game.php?&screen=info_village&id={}"
            if res.player_id:
                player = await self.find_player_data(world, res.player_id)
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
        await self.update_conquer()
        for guild in guilds:
            world = self.get_guild_world(guild)
            if not world:
                continue
            print(world)
            channel_id = self.get_config(guild.id, "conquer")
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            tribes = self.get_config(guild.id, "filter")
            grey = self.get_config(guild.id, "bb")
            data = await self.conquer_parse(world, tribes, grey)
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

    async def update_conquer(self):
        for world in self.worlds:
            sec = self.get_seconds(True)
            data = await self.fetch_conquer(world, sec)
            if not data[0]:
                continue
            if data[0].startswith("<"):
                continue
            cache = []
            for line in data:
                int_list = [int(num) for num in line.split(",")]
                cache.append(int_list)
            old_data = self.conquer.get(world, [])
            old_unix = self.get_seconds(True, 1)
            result = []
            for entry in cache:
                vil_id, unix_time, new_owner, old_owner = entry
                if entry in old_data:
                    continue
                if unix_time > old_unix:
                    continue
                result.append(entry)
            self.conquer[world] = result

    # Parse Conquer Data
    async def conquer_parse(self, world, tribes, bb=False):
        data = self.conquer.get(world)
        if not data:
            return
        id_list = []
        res_lis = []
        if tribes:
            tribe_list = await self.find_ally_player(world, tribes)
            id_list = [obj.id for obj in tribe_list]

        date = None
        for line in data:
            vil_id, unix_time, new_owner, old_owner = line
            player_idc = [new_owner, old_owner]
            if tribes and not any(idc in id_list for idc in player_idc):
                continue
            if not bb and 0 in player_idc:
                continue
            vil = await self.find_village_data(world, vil_id)
            if not vil:
                continue

            ally = self.find_ally_data
            base = f"https://de{world}.die-staemme.de/game.php?&screen="
            res_vil = f"[{vil.x}|{vil.y}]({base}info_village&id={vil.id})"

            res_new = "Barbarendorf"
            res_old = "(Barbarendorf)"

            new = await self.find_player_data(world, new_owner)
            if new:
                url_n = f"[{new.name}]({base}info_player&id={new.id})"
                cache = await ally(world, new.tribe_id) if new.tribe_id else None
                new_tribe = f" **{cache.tag}**" if cache else f""
                res_new = f"{url_n}{new_tribe}"

            old = await self.find_player_data(world, old_owner)
            if old:
                url_o = f"[{old.name}]({base}info_player&id={old.id})"
                cache = await ally(world, old.tribe_id) if old.tribe_id else None
                old_tribe = f" **{cache.tag}**" if cache else ""
                res_old = f"von {url_o}{old_tribe}"

            now = datetime.datetime.utcfromtimestamp(int(unix_time)) + datetime.timedelta(hours=1)
            date, now = now.strftime('%d-%m-%Y'), now.strftime('%H:%M')
            res_lis.append(f"`{now}` | {res_new} adelt {res_vil} {res_old}")
        return date, res_lis

    # Recap Argument Handler
    async def re_handler(self, world, args):
        days = 7
        if ' ' not in args:
            player = await self.find_both_data(world, args)
        elif args.split(" ")[-1].isdigit():
            player = await self.find_both_data(world, ' '.join(args.split(" ")[:-1]))
            if not player:
                player = await self.find_both_data(world, args)
            else:
                days = int(args.split(" ")[-1])
        else:
            player = await self.find_both_data(world, args)
        if not player:
            raise utils.DSUserNotFound(args, world)
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
        player = await self.find_both_data(world, name)
        if not player:
            if con:
                player = await self.find_both_data(world, f"{name} {con}")
                if not player:
                    raise utils.DSUserNotFound(name, world)
            else:
                raise utils.DSUserNotFound(name, world)
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
    async def report_func(self, content):

        data = await self.fetch_report(content)
        if not data:
            return

        img_bytes = await self.html_lover(data)
        if not img_bytes:
            return

        data_io = io.BytesIO(img_bytes)
        image = Image.open(data_io)
        img = await self.trim(image)
        img = img.crop((2, 2, img.width - 2, img.height - 2))
        file = io.BytesIO()
        img.save(file, "png")
        file.seek(0)
        return file

    # Seconds till next Hour
    def get_seconds(self, reverse=False, only=0):
        now = datetime.datetime.now()
        hours = -1 if reverse else 1
        clean = now + datetime.timedelta(hours=hours + only)
        goal_time = clean.replace(minute=0, second=0, microsecond=0)
        start_time = now.replace(microsecond=0)
        if reverse:
            goal_time, start_time = start_time, goal_time
        goal = (goal_time - start_time).seconds
        return goal if not only else start_time.timestamp()

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
        except:
            pass

    # Database Update
    async def update(self):

        begin = datetime.datetime.now()
        await self.refresh_worlds()
        conn = await self.pool.acquire()
        survivor = await self.cleaning(conn)
        print(survivor)
        await self.create_tables(conn, survivor)
        done = []
        for world in self.worlds:
            data = utils.world_data_url(self.casual(world))
            for name, url in data.items():
                print(name)
                async with self.session.get(url) as r:
                    raw = await r.text()
                data_input = []
                if len(name) == 1:
                    sql = self.sql_is_shit(world, name)
                    for line in raw.split("\n"):
                        if not line:
                            continue
                        raw_data = line.split(",")
                        if name == "v":
                            raw_data = raw_data[:-1]
                        if name == "c":
                            raw_data = [int(num) for num in raw_data]

                        data_input.append(raw_data)
                    await self.what_is_my_purpose(conn, data_input, world, name)
                else:
                    sql = self.sql_update_shit(world, name)
                    for line in raw.text.split("\n"):
                        if not line:
                            continue
                        raw_data = line.split(",")
                        rank, idc, kills = raw_data
                        data_input.append((kills, rank, idc))

                print(sql)
                await conn.executemany(sql, data_input)

            done.append(world)

        end = datetime.datetime.now()
        print(f"Updated in Time: {end - begin}")
        print(f"{len(done)} Welten geupdated!")
        await self.pool.release(conn)

    def sql_update_shit(self, world, file):
        weird = file.split("_")
        bash_type, state = weird[-1], weird[0]
        string = f"{bash_type}_bash=$, {bash_type}_rank=$"
        update = "UPDATE {} SET {} WHERE id = $"
        result = update.format(f"{state}_{world}", string)
        return result

    def sql_is_shit(self, world, state):
        main = "INSERT INTO {}({}) VALUES({}) ON CONFLICT (id) DO UPDATE SET {}"
        columns = utils.values[state]
        column_list = columns.split(",")
        inp = ', '.join([f"${num + 1}" for num, _ in enumerate(column_list)])
        update = ', '.join([f'{k} = ${num + 1}' for num, k in enumerate(column_list)])
        query = main.format(f"{state}_{world}", columns, inp, update)
        return query

    async def refresh_worlds(self):
        url_val = "https://de{}.die-staemme.de/map/ally.txt"
        ran_nor = [f"{num}" for num in range(135, 175)]
        ran_cas = [f"p{num}" for num in range(7, 15)]
        cache_worlds = []
        for world in ran_cas + ran_nor:
            async with self.session.get(url_val.format(world)) as cache:
                data = await cache.text()
            if data.startswith("<!DOCTYPE"):
                continue
            if not data:
                continue
            world = int(world[1:]) if "p" in world else int(world)
            cache_worlds.append(world)
        self.worlds = cache_worlds

    async def what_is_my_purpose(self, conn, new_data, world, name):
        query = f"SELECT * FROM {name}_{world}"
        data = await conn.fetch(query)
        old = [str(i[0]) for i in data]
        new = [i[0] for i in new_data]
        if not data:
            return
        delete_me = list(set(old) - set(new))
        # delete_me = [[idc] for idc in delete_me]
        if delete_me:
            query = f"DELETE FROM {name}_{world} WHERE id = $1"
            await conn.execute(query, delete_me)

    async def create_tables(self, conn, survivor):
        tables = ["p", "t", "v", "c"]
        raw = 'CREATE TABLE "{}_{}" ({})'
        new = set(self.worlds) - set(survivor)
        for world in sorted(list(new)):
            for table in tables:
                create = getattr(utils, f"{table}_create")
                query = raw.format(table, world, create)
                await conn.execute(query)

    def execute_world(self, world):
        for guild in self.config:
            cur = self.config[guild].get('world')
            if world == cur:
                self.config[guild].pop('world')
            channel = self.config[guild].get('channel', {})
            for ch_id, ch_world in list(channel.items()):
                if world == ch_world:
                    self.config[guild]['channel'].pop(ch_id)
        self.save_config()

    async def cleaning(self, conn):
        query = "DROP TABLE p_{}, t_{}, v_{}, c_{}"
        worlds = await self.fetch_table_worlds()
        survivor = worlds.copy()
        for world in worlds:
            if world in self.worlds:
                continue
            self.execute_world(world)
            await conn.execute(query.format(world))
            survivor.remove(world)
        return survivor


# Main Class
load = Load()
