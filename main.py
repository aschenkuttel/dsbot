from discord.ext import commands
import data.naruto as secret
import concurrent.futures
import functools
import operator
import discord
import asyncpg
import aiohttp
import asyncio
import random
import utils
import json
import os


# gets called every message to gather the custom prefix
def prefix(bot, message):
    if message.guild is None:
        return bot.prefix
    idc = message.guild.id
    custom = bot.config.get_prefix(idc)
    return custom


# implementation of own class / overwrites
class DSBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.worlds = {}
        self.ress = None
        self.pool = None
        self.conn = None
        self.session = None
        self.last_message = set()
        self.prefix = secret.prefix
        self.white = secret.pm_commands
        self.owner_id = 211836670666997762
        self.path = os.path.dirname(__file__)
        self.data_path = f"{self.path}/data"
        self.logger = utils.create_logger('dsbot', self.path)
        self.msg = json.load(open(f"{self.data_path}/msg.json"))
        self.activity = discord.Activity(type=0, name=self.msg['status'])
        self.add_check(self.global_world)
        self.config = utils.Config(self)
        self.cache = utils.Cache(self)
        self._lock = asyncio.Event()
        self.remove_command("help")
        self.setup_cogs()

    # setup functions
    async def on_ready(self):
        # db / aiohttp setup
        if not self.session or not self.pool:
            self.session = aiohttp.ClientSession(loop=self.loop)
            self.pool, self.ress = await self.db_connect()

            # adds needed option for vps
            if os.name != "nt":
                utils.imgkit['xvfb'] = ''

            await self.refresh_worlds()

        if not self.conn:
            self.conn = await self.pool.acquire()
            await self.conn.add_listener("log", self.callback)

        self._lock.set()
        print("Erfolgreich Verbunden!")

    async def wait_until_unlocked(self):
        return await self._lock.wait()

    # global check and ctx.world implementation
    async def global_world(self, ctx):
        if "help" in str(ctx.command):
            return True

        cmd = str(ctx.command).lower()
        if cmd == "set world":
            return True

        if ctx.guild is None:
            if cmd in self.white:
                return True
            else:
                raise commands.NoPrivateMessage

        server = self.config.get_world(ctx.channel)
        ctx.world = self.worlds.get(server)

        if ctx.world:
            return True
        else:
            raise utils.WorldMissing()

    # custom context implementation
    async def on_message(self, message):
        if not self._lock.is_set():
            return

        ctx = await self.get_context(message, cls=utils.DSContext)
        await self.invoke(ctx)

    async def report_to_owner(self, msg):
        owner = self.get_user(self.owner_id)
        await owner.send(msg)

    def callback(self, *args):
        payload = args[-1]
        self.logger.debug(f"payload received: {payload}")
        if payload == "404":
            msg = "database script ended with a failure"
        elif payload == "400":
            msg = "engine broke once, restarting"
        else:
            msg = "unknown payload"
        self.loop.create_task(self.report_to_owner(msg))

    # defaul executor somehow leaks RAM
    async def execute(self, func, *args):
        with concurrent.futures.ThreadPoolExecutor() as pool:
            package = functools.partial(func, *args)
            result = await self.loop.run_in_executor(pool, package)

        pool.shutdown()
        return result

    async def db_connect(self):
        result = []
        databases = 'tribaldata', 'userdata'
        for db in databases:
            conn_data = {'host': secret.db_adress, 'port': secret.db_port,
                         'user': secret.db_user, 'password': secret.db_key,
                         'database': db, 'loop': self.loop, 'max_size': 50}
            cache = await asyncpg.create_pool(**conn_data)
            result.append(cache)
        return result

    async def update_iron(self, user_id, iron):
        async with self.ress.acquire() as conn:
            query = 'INSERT INTO iron_data(id, amount) VALUES($1, $2) ' \
                    'ON CONFLICT (id) DO UPDATE SET amount = iron_data.amount + $2'
            await conn.execute(query, user_id, iron)

    async def subtract_iron(self, user_id, iron, supress=False):
        async with self.ress.acquire() as conn:
            query = 'UPDATE iron_data SET amount = amount - $2 ' \
                    'WHERE id = $1 AND amount >= $2 RETURNING TRUE'
            response = await conn.fetchrow(query, user_id, iron)

            if response is None and not supress:
                purse = await self.fetch_iron(user_id)
                raise utils.MissingGucci(purse)

            return response

    async def fetch_iron(self, user_id, info=False):
        async with self.ress.acquire() as conn:
            if info:
                query = 'SELECT * FROM iron_data'
                data = await conn.fetch(query)
            else:
                query = 'SELECT * FROM iron_data WHERE id = $1'
                data = await conn.fetchrow(query, user_id)

        if not info:
            return data['amount'] if data else 0

        rank = "Unknown"
        cache = {rec['id']: rec['amount'] for rec in data}
        money = cache.get(user_id, 0)

        sort = sorted(cache.items(), key=lambda kv: kv[1], reverse=True)
        for index, (idc, cash) in enumerate(sort):
            if idc == user_id:
                rank = index + 1

        return money, rank

    async def fetch_iron_list(self, amount, guild=None):
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

    async def save_usage(self, cmd):
        cmd = cmd.lower()
        query = 'SELECT * FROM usage_data WHERE name = $1'

        async with self.ress.acquire() as conn:
            data = await conn.fetchrow(query, cmd)
            new_usage = data['usage'] + 1 if data else 1

            query = 'INSERT INTO usage_data(name, usage) VALUES($1, $2) ' \
                    'ON CONFLICT (name) DO UPDATE SET usage=$2'
            await conn.execute(query, cmd, new_usage)

    async def fetch_usage(self):
        statement = 'SELECT * FROM usage_data'
        async with self.ress.acquire() as conn:
            data = await conn.fetch(statement)

        cache = {r['name']: r['usage'] for r in data}
        return sorted(cache.items(), key=operator.itemgetter(1), reverse=True)

    # DS Database Methods
    async def refresh_worlds(self):
        query = 'SELECT * FROM world GROUP BY world'
        async with self.pool.acquire() as conn:
            data = await conn.fetch(query)

        if not data:
            return

        cache = {}
        for record in data:
            world = utils.DSWorld(record)
            cache[world.server] = world

        for server in self.worlds:
            if server not in cache:
                self.config.remove_world(server)

        self.worlds = cache

    async def fetch_all(self, world, table=None, dic=False):
        dsobj = utils.DSType(table or 0)
        async with self.pool.acquire() as conn:
            query = f'SELECT * FROM {dsobj.table} WHERE world = $1'
            cache = await conn.fetch(query, world)
            result = [dsobj.Class(rec) for rec in cache]

            if dic:
                result = {obj.id: obj for obj in result}

            return result

    async def fetch_random(self, world, **kwargs):
        amount = kwargs.get('amount', 1)
        top = kwargs.get('top', 500)
        dsobj = utils.DSType(kwargs.get('tribe', 0))
        least = kwargs.get('least', False)

        statement = f'SELECT * FROM {dsobj.table} WHERE world = $1 AND rank <= $2'
        async with self.pool.acquire() as conn:
            data = await conn.fetch(statement, world, top)

        if len(data) < amount:
            if kwargs.get('max'):
                amount = len(data)
            else:
                return

        result = []
        while len(result) < amount:
            ds = random.choice(data)
            data.remove(ds)

            if not least:
                result.append(dsobj.Class(ds))
            elif ds['member'] > 3:
                result.append(dsobj.Class(ds))

        return result[0] if amount == 1 else result

    async def fetch_player(self, world, searchable, *, name=False, archive=None):
        table = f"player{archive}" if archive else "player"

        if name:
            searchable = utils.converter(searchable, True)
            query = f'SELECT * FROM {table} WHERE world = $1 AND LOWER(name) = $2'
        else:
            query = f'SELECT * FROM {table} WHERE world = $1 AND id = $2'

        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(query, world, searchable)
        return utils.Player(result) if result else None

    async def fetch_tribe(self, world, searchable, *, name=False, archive=None):
        table = f"tribe{archive}" if archive else "tribe"

        if name:
            searchable = utils.converter(searchable, True)
            query = f'SELECT * FROM {table} WHERE world = $1 ' \
                    f'AND (LOWER(tag) = $2 OR LOWER(name) = $2)'
        else:
            query = f'SELECT * FROM {table} WHERE world = $1 AND id = $2'

        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(query, world, searchable)
        return utils.Tribe(result) if result else None

    async def fetch_village(self, world, searchable, *, coord=False, archive=None):
        table = f"village{archive}" if archive else "village"

        if coord:
            x, y = searchable.split('|')
            query = f'SELECT * FROM {table} WHERE world = $1 AND x = $2 AND y = $3'
            searchable = [int(x), int(y)]
        else:
            query = f'SELECT * FROM {table} WHERE world = $1 AND id = $2'
            searchable = [searchable]

        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(query, world, *searchable)
        return utils.Village(result) if result else None

    async def fetch_both(self, world, searchable, *, name=True, archive=None):
        kwargs = {'name': name, 'archive': archive}
        player = await self.fetch_player(world, searchable, **kwargs)
        if player:
            return player

        tribe = await self.fetch_tribe(world, searchable, **kwargs)
        return tribe

    async def fetch_top(self, world, table=None, till=10, balanced=False):
        dsobj = utils.DSType(table or 0)
        till = 100 if balanced else till
        query = f'SELECT * FROM {dsobj.table} WHERE world = $1 AND rank <= $2'

        async with self.pool.acquire() as conn:
            top10 = await conn.fetch(query, world, till)
            dsobj_list = [dsobj.Class(rec) for rec in top10]

        if not balanced:
            return dsobj_list

        else:
            cache = sorted(dsobj_list, key=lambda t: t.points, reverse=True)
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

    # imports all cogs at startup
    def setup_cogs(self):
        for file in secret.default_cogs:
            try:
                self.load_extension(f"cogs.{file}")
            except commands.ExtensionNotFound:
                print(f"module {file} not found")

    async def logout(self):
        await self.session.close()
        await self.ress.close()
        await self.pool.close()
        await self.close()


# instance creation and bot start
dsbot = DSBot(command_prefix=prefix, case_insensitive=True)
dsbot.run(secret.TOKEN)
