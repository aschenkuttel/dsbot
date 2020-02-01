from data.naruto import TOKEN, pre, db_key, db_port, db_user, db_adress
from PIL import Image, ImageChops
from bs4 import BeautifulSoup
import datetime
import operator
import asyncpg
import aiohttp
import asyncio
import discord
import imgkit
import random
import utils
import json
import time
import os
import io


class Load:
    def __init__(self):
        self.config = {}
        self.worlds = []
        self.conquer = {}
        self.ress = None
        self.pool = None
        self.session = None
        self.colors = None
        self.secrets = {'TOKEN': TOKEN, 'PRE': pre}
        self.data_path = f"{os.path.dirname(__file__)}/data"
        self.url_val = "https://de{}.die-staemme.de/map/ally.txt"
        self.url_set = "https://de{}.die-staemme.de/page/settings"
        self.msg = json.load(open(f"{self.data_path}/msg.json"))
        self.options = {
            'quiet': "",
            'format': "png",
            'quality': 100,
            'encoding': "UTF-8",
        }

        self.fml = '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE html PUBLIC "' \
                   '-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/' \
                   'TR/xhtml1/DTD/xhtml1-transitional.dtd"> <html xmlns=' \
                   '"http://www.w3.org/1999/xhtml">'

    async def setup(self, loop):
        self.session = aiohttp.ClientSession(loop=loop)
        connections = await self.db_connect(loop)
        self.pool, self.ress = connections
        self.colors = utils.DSColor()
        await self.refresh_worlds()
        self.config_setup()

        # adds needed option for vps
        if os.name != "nt":
            self.options['xvfb'] = ''

        return self.session

    async def db_connect(self, loop):
        result = []
        databases = 'tribaldata', 'userdata'
        for db in databases:
            conn_data = {'host': db_adress, 'port': db_port, 'user': db_user,
                         'password': db_key, 'database': db, 'loop': loop, 'max_size': 50}
            cache = await asyncpg.create_pool(**conn_data)
            result.append(cache)
        return result

    async def close_db(self):
        await self.ress.close()
        await self.pool.close()

    def is_valid(self, world):
        return world in self.worlds

    # Config Methods
    def config_setup(self):
        cache = json.load(open(f"{self.data_path}/config.json"))
        data = {int(key): value for key, value in cache.items()}
        self.config.update(data)

    def get_item(self, guild_id, item):
        config = self.config.get(guild_id)
        if config is None:
            return
        return config.get(item)

    def change_item(self, guild_id, item, value):
        if guild_id not in self.config:
            self.config[guild_id] = {}
        self.config[guild_id][item] = value
        self.save_config()

    def remove_item(self, guild_id, item):
        config = self.config.get(guild_id)
        if not config:
            return
        job = config.pop(item, None)
        if job is not None:
            self.save_config()
        return job

    def get_world(self, channel):
        con = self.config.get(channel.guild.id)
        if con is None:
            return
        main = con.get('world')
        if not main:
            return
        chan = con.get('channel')
        idc = str(channel.id)
        world = chan.get(idc, main) if chan else main
        return world

    def get_guild_world(self, guild, url=False):
        con = self.config.get(guild.id)
        if con is None:
            return
        world = con.get('world')
        if url and world:
            return utils.casual(world)
        return world

    def remove_world(self, world):
        for guild in self.config:
            config = self.config[guild]
            if config.get('world') == world:
                config.pop('world')
            channel = config.get('channel', {})
            for ch in channel.copy():
                if channel[ch] == world:
                    channel.pop(ch)
        self.save_config()

    def get_prefix(self, guild_id):
        config = self.config.get(guild_id)
        default = self.secrets['PRE']
        if config is None:
            return default
        return config.get('prefix', default)

    def save_config(self):
        json.dump(self.config, open(f"{self.data_path}/config.json", 'w'))

    # Iron Data / Cmd Usage Methods
    async def save_user_data(self, user_id, amount):
        query = 'SELECT * FROM iron_data WHERE id = $1'
        async with self.ress.acquire() as conn:
            data = await conn.fetchrow(query, user_id)
            query = 'INSERT INTO iron_data(id, amount) VALUES($1, $2) ' \
                    'ON CONFLICT (id) DO UPDATE SET amount=$2'
            new_amount = data['amount'] + amount if data else amount
            await conn.execute(query, user_id, new_amount)

    async def get_user_data(self, user_id, info=False):
        query = 'SELECT * FROM iron_data'
        async with self.ress.acquire() as conn:
            data = await conn.fetch(query)

        cache = {cur['id']: cur['amount'] for cur in data}
        rank = "Unknown"
        sort = sorted(cache.items(), key=lambda kv: kv[1], reverse=True)

        for index, (idc, cash) in enumerate(sort):
            if idc == user_id:
                rank = index + 1
        money = cache.get(user_id, 0)
        return (money, rank) if info else money

    async def get_user_top(self, amount, guild=None):
        base = 'SELECT * FROM iron_data'
        args = [amount]

        if guild:
            base += ' WHERE id = ANY($2)'
            member = [mem.id for mem in guild.members]
            args.append(member)

        query = base + ' ORDER BY amount DESC LIMIT $1'

        async with self.ress.acquire() as conn:
            data = await conn.fetch(query, *args)
            return data

    async def save_usage_cmd(self, cmd):
        cmd = cmd.lower()
        query = 'SELECT * FROM usage_data WHERE name = $1'

        async with self.ress.acquire() as conn:
            data = await conn.fetchrow(query, cmd)
            new_usage = data['usage'] + 1 if data else 1

            query = 'INSERT INTO usage_data(name, usage) VALUES($1, $2) ' \
                    'ON CONFLICT (name) DO UPDATE SET usage=$2'
            await conn.execute(query, cmd, new_usage)

    async def get_usage(self):
        statement = 'SELECT * FROM usage_data'
        async with self.ress.acquire() as conn:
            data = await conn.fetch(statement)

        cache = {r['name']: r['usage'] for r in data}
        return sorted(cache.items(), key=operator.itemgetter(1), reverse=True)

    # DS Database Methods
    async def refresh_worlds(self):
        query = 'SELECT world FROM tribe GROUP BY world'
        async with self.pool.acquire() as conn:
            data = await conn.fetch(query)

        cache = [r['world'] for r in data]
        if not cache:
            return

        old_worlds = self.worlds.copy()
        for world in old_worlds:
            if world not in cache:
                self.worlds.remove(world)
                self.remove_world(world)

        self.worlds = cache

    async def fetch_all(self, world, table=None):
        dsobj = utils.DSType(table or 0)
        async with self.pool.acquire() as conn:
            query = f'SELECT * FROM {dsobj.table} WHERE world = $1'
            cache = await conn.fetch(query, world)
            return [dsobj.Class(rec) for rec in cache]

    async def fetch_random(self, world, **kwargs):
        amount = kwargs.get('amount', 1)
        top = kwargs.get('top', 500)
        dsobj = utils.DSType(kwargs.get('tribe', 0))
        least = kwargs.get('least', False)

        statement = f'SELECT * FROM {dsobj.table} WHERE world = $1 AND rank <= $2'
        async with self.pool.acquire() as conn:
            data = await conn.fetch(statement, world, top)

        result = []
        while len(result) < amount:
            ds = random.choice(data)
            cur = [p.id for p in result]
            if ds['id'] not in cur:
                if not least:
                    result.append(dsobj.Class(ds))
                elif ds['member'] > 3:
                    result.append(dsobj.Class(ds))

        return result[0] if amount == 1 else result

    async def fetch_village(self, world, searchable, coord=False):
        if coord:
            x, y = searchable.split('|')
            query = f'SELECT * FROM village WHERE world = $1 AND x = $2 AND y = $3'
            searchable = [int(x), int(y)]
        else:
            query = f'SELECT * FROM village WHERE world = $1 AND id = $2'
            searchable = [searchable]

        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(query, world, *searchable)
        return utils.Village(result) if result else None

    async def fetch_player(self, world, searchable, name=False):
        if name:
            searchable = utils.converter(searchable, True)
            query = f'SELECT * FROM player WHERE world = $1 AND LOWER(name) = $2'
        else:
            query = f'SELECT * FROM player WHERE world = $1 AND id = $2'

        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(query, world, searchable)
        return utils.Player(result) if result else None

    async def fetch_tribe(self, world, searchable, name=False):
        if name:
            searchable = utils.converter(searchable, True)
            query = 'SELECT * FROM tribe WHERE world = $1 ' \
                    'AND (LOWER(tag) = $2 OR LOWER(name) = $2)'
        else:
            query = 'SELECT * FROM tribe WHERE world = $1 AND id = $2'

        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(query, world, searchable)
        return utils.Tribe(result) if result else None

    async def fetch_both(self, world, name):
        player = await self.fetch_player(world, name, True)
        if player:
            return player
        tribe = await self.fetch_tribe(world, name, True)
        return tribe

    async def fetch_top(self, world, table=None, till=10, balanced=False):
        dsobj = utils.DSType(table or 0)
        till = 100 if balanced else till
        query = f'SELECT * FROM {dsobj.table} WHERE world = $1 AND rank <= $2'

        async with self.pool.acquire() as conn:
            top10 = await conn.fetch(query, world, till)
            tribe_list = [dsobj.Class(rec) for rec in top10]

        if not balanced:
            return tribe_list
        else:
            cache = sorted(tribe_list, key=lambda t: t.points, reverse=True)
            balenciaga = [ds for ds in cache if (cache[0].points / 12) < ds.points]
            return balenciaga

    async def fetch_tribe_member(self, world, allys, name=False):
        if not isinstance(allys, (tuple, list)):
            allys = [allys]
        if name:
            tribes = await self.fetch_bulk(world, allys, table=1, name=True)
            allys = [tribe.id for tribe in tribes]

        query = f'SELECT * FROM player WHERE world = $1 AND tribe_id = ANY($2)'
        async with self.pool.acquire() as conn:
            res = await conn.fetch(query, world, allys)
        return [utils.Player(rec) for rec in res]

    async def fetch_bulk(self, world, iterable, table=None, *, name=False, dic=False):
        dsobj = utils.DSType(table or 0)
        base = f'SELECT * FROM {dsobj.table} WHERE world = $1'

        if not name:
            query = f'{base} AND id = ANY($2)'
        else:
            if dsobj.table == "village":
                query = f'{base} AND CAST(x AS TEXT)||CAST(y as TEXT) = ANY($2)'
            else:
                iterable = [utils.converter(obj, True) for obj in iterable]
                if dsobj.table == "tribe":
                    query = f'{base} AND ARRAY[LOWER(name), LOWER(tag)] && $2'
                else:
                    query = f'{base} AND LOWER(name) = ANY($2)'

        async with self.pool.acquire() as conn:
            res = await conn.fetch(query, world, iterable)
            if dic:
                return {rec[1]: dsobj.Class(rec) for rec in res}
            else:
                return [dsobj.Class(rec) for rec in res]

    async def fetch_archive(self, world, idc, table=None, days=7):
        dsobj = utils.DSType(table or 0)
        query = f'SELECT * FROM {dsobj.table}{days} WHERE world = $1 AND id = $2'

        async with self.pool.acquire() as conn:
            res = await conn.fetchrow(query, world, idc)
            return dsobj.Class(res) if res else None

    async def fetch_villages(self, obj, num, world, continent=None):
        if isinstance(obj, utils.Tribe):
            query = 'SELECT * FROM player WHERE world = $1 AND tribe_id = $2'
            async with self.pool.acquire() as conn:
                cache = await conn.fetch(query, world, obj.id)
            id_list = [rec['id'] for rec in cache]
        else:
            id_list = [obj.id]

        arguments = [world, id_list]
        query = 'SELECT * FROM village WHERE world = $1 AND player = ANY($2)'
        if continent:
            query = query + ' AND LEFT(CAST(x AS TEXT), 1) = $3' \
                            ' AND LEFT(CAST(y AS TEXT), 1) = $4'
            arguments.extend(list(continent))

        async with self.pool.acquire() as conn:
            result = await conn.fetch(query, *arguments)

        if not result:
            return 0

        random.shuffle(result)
        if num != "all":
            if len(result) < int(num):
                return len(result)
            result = result[:int(num)]

        coords = [f"{rec['x']}|{rec['y']}" for rec in result]
        if len(coords) < 286:
            return coords

        file = io.StringIO()
        file.write(f'{os.linesep}'.join(coords))
        file.seek(0)
        return file

    # Conquer Feed
    async def conquer_feed(self, guilds):
        await self.update_conquer()
        for guild in guilds:

            world = self.get_guild_world(guild)
            if not world:
                continue

            channel_id = self.get_item(guild.id, 'conquer')
            channel = guild.get_channel(channel_id)
            if not channel:
                continue

            tribes = self.get_item(guild.id, 'filter')
            grey = self.get_item(guild.id, 'bb')
            data = await self.conquer_parse(world, tribes, grey)
            if not data:
                continue

            res_cache = []
            once = data[0]
            counter = 0

            for sen in data[1]:
                if counter + len(sen) > 2000:
                    embed = discord.Embed(title=once, description='\n'.join(res_cache))
                    await utils.silencer(channel.send(embed=embed))
                    res_cache.clear()
                    counter = 0
                    once = ""
                    await asyncio.sleep(0.5)

                res_cache.append(sen)
                counter += len(sen)

            if res_cache:
                embed = discord.Embed(title=once, description='\n'.join(res_cache))
                await utils.silencer(channel.send(embed=embed))

    async def update_conquer(self):
        for world in self.worlds:
            sec = self.get_seconds(True)
            data = await self.fetch_conquer(world, sec)
            self.conquer[world] = []
            if not data[0]:
                continue
            if data[0].startswith('<'):
                continue
            cache = []
            for line in data:
                int_list = [int(num) for num in line.split(',')]
                cache.append(int_list)

            player_ids = []
            village_ids = []
            conquer_cache = []
            old_unix = self.get_seconds(True, 1)
            for entry in cache:
                vil_id, unix_time, new_owner, old_owner = entry

                if unix_time > old_unix:
                    continue

                village_ids.append(vil_id)
                player_ids.extend([new_owner, old_owner])
                conquer = utils.Conquer(world, entry)
                conquer_cache.append(conquer)

            # Make all the API Calls
            players = await load.fetch_bulk(world, player_ids, dic=True)
            tribe_ids = [obj.tribe_id for obj in players.values() if obj.tribe_id]
            tribes = await load.fetch_bulk(world, tribe_ids, 'tribe', dic=True)
            villages = await load.fetch_bulk(world, village_ids, 'village', dic=True)

            for conquer in conquer_cache:
                conquer.village = villages.get(conquer.id)
                conquer.old_player = players.get(conquer.old_id)
                conquer.new_player = players.get(conquer.new_id)
                if conquer.old_player:
                    conquer.old_tribe = tribes.get(conquer.old_player.tribe_id)
                if conquer.new_player:
                    conquer.new_tribe = tribes.get(conquer.new_player.tribe_id)

            self.conquer[world] = conquer_cache

    async def fetch_conquer(self, world, sec=3600):
        cur = time.time() - sec
        base = "http://de{}.die-staemme.de/interface.php?func=get_conquer&since={}"
        url = base.format(utils.casual(world), cur)
        async with self.session.get(url) as r:
            data = await r.text('utf-8')
            return data.split('\n')

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

    async def conquer_parse(self, world, only_tribes, bb):
        data = self.conquer.get(world)
        if not data:
            return

        tribe_players = {}
        if only_tribes:
            members = await self.fetch_tribe_member(world, only_tribes)
            tribe_players = {obj.id: obj for obj in members}

        date = None
        result = []
        for conquer in data:

            if only_tribes and not any(idc in tribe_players for idc in conquer.player_ids):
                continue
            if not bb and conquer.grey:
                continue
            if not conquer.village:
                continue

            old = conquer.old_player or "[Barbarendorf]"
            new = conquer.new_player or "[Barbarendorf]"
            village_hyperlink = f"[{conquer.coords}]({conquer.village.ingame_url})"

            if conquer.new_player:
                new_url = f"[{new.name}]({new.ingame_url})"
                new_tribe = f" **{conquer.new_tribe.tag}**" if conquer.new_tribe else ""
                new = f"{new_url}{new_tribe}"

            if conquer.old_player:
                old_url = f"[{old.name}]({old.ingame_url})"
                old_tribe = f" **{conquer.old_tribe.tag}**" if conquer.old_tribe else ""
                old = f"von {old_url}{old_tribe}"

            date, now = conquer.time.strftime('%d-%m-%Y'), conquer.time.strftime('%H:%M')
            result.append(f"``{now}`` | {new} adelt {village_hyperlink} {old}")

        return date, result

    # Report HTML to Image Converter
    def html_lover(self, raw_data):
        soup = BeautifulSoup(raw_data, 'html.parser')
        tiles = soup.body.find_all(class_='vis')
        if len(tiles) < 2:
            return
        main = f"{self.fml}<head></head>{tiles[1]}"  # don't ask me why...
        css = f"{self.data_path}/report.css"
        img_bytes = imgkit.from_string(main, False, options=self.options, css=css)

        # crops empty background
        im = Image.open(io.BytesIO(img_bytes))
        bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
        diff = ImageChops.difference(im, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        im = im.crop(diff.getbbox())

        # crops border and saves to FileIO
        result = im.crop((2, 2, im.width - 2, im.height - 2))
        file = io.BytesIO()
        result.save(file, 'png')
        file.seek(0)
        return file

    async def fetch_report(self, bot, content):
        try:
            async with self.session.get(content) as res:
                data = await res.text()
        except (aiohttp.InvalidURL, ValueError):
            return

        file = await bot.execute(self.html_lover, data)
        return file


# Main Class
load = Load()
