from async_timeout import timeout
import data.credentials as secret
from discord.ext import commands
import concurrent.futures
import functools
import datetime
import discord
import asyncpg
import aiohttp
import asyncio
import random
import utils
import os


def prefix(bot, message):
    if message.guild is None:
        return secret.default_prefix

    guild_prefix = bot.config.get_prefix(message.guild.id)
    return guild_prefix or secret.default_prefix


class DSBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        path = os.path.dirname(__file__)
        self.data_path = f"{path}/data"

        self.worlds = {}
        self.members = {}

        self.session = None
        self.tribal_pool = None
        self.member_pool = None

        # active connection listening for database callbacks
        self._conn = None

        # creation of own logging and discord logging
        self.logger = utils.create_logger("dsbot", self.data_path)
        utils.create_logger("discord", self.data_path)

        self.languages = {}
        path = f"{self.data_path}/language"
        for filename in os.listdir(path):
            name = filename.split(".")[0]
            self.languages[name] = utils.Language(path, filename)

        # update lock which waits for external database script and setup lock
        self._update = asyncio.Event()
        self._lock = asyncio.Event()

        self.config = utils.Config(self)
        self.owner_id = 211836670666997762
        self.default_prefix = secret.default_prefix
        self.activity = discord.Activity(type=0, name=secret.status)
        self.add_check(self.global_check)
        self.remove_command("help")

        # initiate main loop and load modules
        self.loop.create_task(self.loop_per_hour())
        self.setup_cogs()

    async def on_ready(self):
        # db / aiohttp setup
        if not self._lock.is_set():

            # initiates session object and db conns
            self.session = aiohttp.ClientSession(loop=self.loop)
            self.tribal_pool, self.member_pool = await self.db_connect()
            await self.setup_tables()

            # initiate logging connection for discord callback
            self._conn = await self.tribal_pool.acquire()
            await self._conn.add_listener("log", self.callback)

            # adds needed option for vps
            if os.name != "nt":
                utils.imgkit['xvfb'] = ""

            # loads active worlds from database
            await self.update_worlds()
            await self.load_members()
            self._lock.set()

        print("Erfolgreich Verbunden!")

    def is_locked(self):
        return not self._lock.is_set()

    async def wait_until_unlocked(self):
        return await self._lock.wait()

    # global check and ctx.world inject
    async def global_check(self, ctx):
        cmds = {str(ctx.command), str(ctx.command.parent)}

        if bool(cmds & secret.pm_commands):
            return True
        elif ctx.guild is None:
            raise commands.NoPrivateMessage()
        else:
            self.update_member(ctx.author)

        world_prefix = self.config.get_world(ctx.channel)
        world = self.worlds.get(world_prefix)

        if world:
            ctx.world = world
            return True
        else:
            raise utils.WorldMissing()

    # custom context implementation
    async def on_message(self, message):
        if not self._lock.is_set():
            return

        if message.author.bot:
            return

        ctx = await self.get_context(message, cls=utils.DSContext)
        await self.invoke(ctx)

    async def report_to_owner(self, msg):
        owner = await self.fetch_user(self.owner_id)
        await owner.send(msg)

    def callback(self, *args):
        payload = args[-1]

        if payload == "200":
            self._update.set()
            return

        elif payload == "400":
            msg = "engine broke once, restarting"
        elif payload == "404":
            msg = "database script ended with a failure"
        else:
            msg = "unknown payload"

        self.logger.debug(f"payload received: {payload}")
        self.loop.create_task(self.report_to_owner(msg))

    # defaul executor somehow leaks RAM
    async def execute(self, func, *args, **kwargs):
        with concurrent.futures.ThreadPoolExecutor() as pool:
            package = functools.partial(func, *args, **kwargs)
            result = await self.loop.run_in_executor(pool, package)

        return result

    async def loop_per_hour(self):
        await self._lock.wait()

        while not self.is_closed():
            seconds = self.get_seconds()
            await asyncio.sleep(seconds)
            self.logger.debug("loop per hour")

            task_cog = self.get_cog("Tasks")
            await task_cog.task_engine()

            try:
                async with timeout(120, loop=self.loop):
                    await self._update.wait()
                    await self.update_worlds()
            except asyncio.TimeoutError:
                self.logger.error("update timeout")

            for cog in self.cogs.values():
                loop = getattr(cog, "called_per_hour", None)

                try:
                    if loop is not None:
                        await loop()

                except Exception as error:
                    self.logger.debug(f"{cog.qualified_name} Cog Error: {error}")

            self._update.clear()

    # current workaround since library update will support that with tasks in short future
    def get_seconds(self, added_hours=1, timestamp=False):
        now = datetime.datetime.now()
        clean = now + datetime.timedelta(hours=added_hours)
        goal_time = clean.replace(minute=0, second=0, microsecond=0)
        start_time = now.replace(microsecond=0)

        if added_hours < 1:
            goal_time, start_time = start_time, goal_time

        if timestamp is True:
            return start_time.timestamp()
        else:
            return (goal_time - start_time).seconds

    async def db_connect(self):
        result = []

        for db in secret.databases:
            conn_data = {'host': secret.db_adress,
                         'port': secret.db_port,
                         'user': secret.db_user,
                         'password': secret.db_key,
                         'database': db,
                         'loop': self.loop,
                         'max_size': 50}

            cache = await asyncpg.create_pool(**conn_data)
            result.append(cache)

        return result

    async def setup_tables(self):
        reminder = 'CREATE TABLE IF NOT EXISTS reminder' \
                   '(id SERIAL PRIMARY KEY, author_id BIGINT,' \
                   'channel_id BIGINT, creation TIMESTAMP,' \
                   'expiration TIMESTAMP, reason TEXT)'

        iron = 'CREATE TABLE IF NOT EXISTS iron' \
               '(id BIGINT PRIMARY KEY, amount BIGINT)'

        usage = 'CREATE TABLE IF NOT EXISTS usage' \
                '(name TEXT PRIMARY KEY, amount BIGINT)'

        slot = 'CREATE TABLE IF NOT EXISTS slot' \
               '(id BIGINT PRIMARY KEY, amount BIGINT)'

        member = 'CREATE TABLE IF NOT EXISTS member' \
                 '(id BIGINT, guild_id BIGINT, name TEXT, nick TEXT, ' \
                 'last_update TIMESTAMP, PRIMARY KEY (id, guild_id))'

        tasks = 'CREATE TABLE IF NOT EXISTS tasks' \
                '(id SERIAL PRIMARY KEY, guild_id BIGINT,' \
                'channel_id BIGINT, command TEXT,' \
                'arguments TEXT, time TIME)'

        querys = [reminder, iron, usage,
                  slot, member, tasks]

        async with self.member_pool.acquire() as conn:
            await conn.execute(";".join(querys))

    async def load_members(self):
        for guild in self.guilds:
            self.members[guild.id] = {}

        async with self.member_pool.acquire() as conn:
            data = await conn.fetch('SELECT * FROM member')

            for record in data:
                member = utils.DSMember(record)
                if member.guild_id in self.members:
                    self.members[member.guild_id][member.id] = member

    def get_member(self, member_id):
        for members in self.members.values():
            member = members.get(member_id)
            if member is not None:
                return member

    def get_guild_member(self, guild_id, member_id):
        members = self.members.get(guild_id)
        if members is None:
            return

        return members.get(member_id)

    def get_member_by_name(self, guild_id, name):
        members = self.members.get(guild_id)
        if members is None:
            return

        for member in members.values():
            if member.nick and member.nick.lower() == name.lower():
                return member
            if member.name.lower() == name.lower():
                return member

    def update_member(self, member):
        dc_member = utils.DSMember.from_object(member)
        cache = self.members.get(member.guild.id)

        if cache is None:
            self.members[member.guild.id] = {member.id: dc_member}
        else:
            old = cache.get(member.id)
            if not old or old != member:
                cache[member.id] = dc_member

    async def update_iron(self, user_id, iron):
        async with self.member_pool.acquire() as conn:
            query = 'INSERT INTO iron(id, amount) VALUES($1, $2) ' \
                    'ON CONFLICT (id) DO UPDATE SET amount = iron.amount + $2'
            await conn.execute(query, user_id, iron)

    async def subtract_iron(self, user_id, iron, supress=False):
        async with self.member_pool.acquire() as conn:
            query = 'UPDATE iron SET amount = amount - $2 ' \
                    'WHERE id = $1 AND amount >= $2 RETURNING TRUE'
            response = await conn.fetchrow(query, user_id, iron)

            if response is None and not supress:
                purse = await self.fetch_iron(user_id)
                raise utils.MissingGucci(purse)

            return response

    async def fetch_iron(self, user_id, rank=False):
        async with self.member_pool.acquire() as conn:
            if rank is False:
                query = 'SELECT * FROM iron WHERE id = $1'
                data = await conn.fetchrow(query, user_id)
                return data['amount'] if data else 0

            else:
                query = 'SELECT amount, (SELECT COUNT(*) FROM iron WHERE ' \
                        'amount >= (SELECT amount FROM iron WHERE id = $1)) ' \
                        'AS count FROM iron WHERE id = $1'
                data = await conn.fetchrow(query, user_id)
                return data or (0, 0)

    async def fetch_usage(self, amount=None):
        statement = 'SELECT * FROM usage ORDER BY amount DESC'

        if amount is not None:
            statement += f' LIMIT {amount}'

        async with self.member_pool.acquire() as conn:
            data = await conn.fetch(statement)
            return [r.values() for r in data]

    async def update_worlds(self):
        query = 'SELECT * FROM world GROUP BY world'
        async with self.tribal_pool.acquire() as conn:
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
        self.logger.debug("worlds updated")

    async def fetch_all(self, world, table=0, dictionary=False):
        dsobj = utils.DSType(table)

        async with self.tribal_pool.acquire() as conn:
            query = f'SELECT * FROM {dsobj.table} WHERE world = $1'
            cache = await conn.fetch(query, world)

            if dictionary:
                result = {rec['id']: dsobj.Class(rec) for rec in cache}
            else:
                result = [dsobj.Class(rec) for rec in cache]

            return result

    async def fetch_random(self, world, **kwargs):
        amount = kwargs.get('amount', 1)
        top = kwargs.get('top', 500)
        dsobj = utils.DSType(kwargs.get('tribe', 0))
        least = kwargs.get('least', False)

        statement = f'SELECT * FROM {dsobj.table} WHERE world = $1 AND rank <= $2'
        async with self.tribal_pool.acquire() as conn:
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
            searchable = utils.encode(searchable)
            query = f'SELECT * FROM {table} WHERE world = $1 AND LOWER(name) = $2'
        else:
            query = f'SELECT * FROM {table} WHERE world = $1 AND id = $2'

        async with self.tribal_pool.acquire() as conn:
            result = await conn.fetchrow(query, world, searchable)
            return utils.Player(result) if result else None

    async def fetch_tribe(self, world, searchable, *, name=False, archive=None):
        table = f"tribe{archive}" if archive else "tribe"

        if name:
            searchable = utils.encode(searchable)
            query = f'SELECT * FROM {table} WHERE world = $1 ' \
                    f'AND (LOWER(tag) = $2 OR LOWER(name) = $2)'
        else:
            query = f'SELECT * FROM {table} WHERE world = $1 AND id = $2'

        async with self.tribal_pool.acquire() as conn:
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

        async with self.tribal_pool.acquire() as conn:
            result = await conn.fetchrow(query, world, *searchable)

        return utils.Village(result) if result else None

    async def fetch_both(self, world, searchable, *, name=True, archive=None):
        kwargs = {'name': name, 'archive': archive}
        player = await self.fetch_player(world, searchable, **kwargs)
        if player:
            return player

        tribe = await self.fetch_tribe(world, searchable, **kwargs)
        return tribe

    async def fetch_top(self, world, top, table=None, **kwargs):
        dsobj = utils.DSType(table or 0)
        attribute = kwargs.get('attribute', 'rank')
        way = "ASC" if attribute == "rank" else "DESC"

        query = f'SELECT * FROM {dsobj.table} WHERE world = $1 ' \
                f'ORDER BY {attribute} {way} LIMIT $2'

        async with self.tribal_pool.acquire() as conn:
            top10 = await conn.fetch(query, world, top)

            if kwargs.get('dictionary') is True:
                return {rec[1]: dsobj.Class(rec) for rec in top10}
            else:
                return [dsobj.Class(rec) for rec in top10]

    async def fetch_tribe_member(self, world, allys, name=False):
        if not isinstance(allys, (tuple, list)):
            allys = [allys]
        if name:
            tribes = await self.fetch_bulk(world, allys, table=1, name=True)
            allys = [tribe.id for tribe in tribes]

        query = f'SELECT * FROM player WHERE world = $1 AND tribe_id = ANY($2)'
        async with self.tribal_pool.acquire() as conn:
            res = await conn.fetch(query, world, allys)
            return [utils.Player(rec) for rec in res]

    async def fetch_bulk(self, world, iterable, table=None, **kwargs):
        dsobj = utils.DSType(table or 0, archive=kwargs.get('archive'))
        base = f'SELECT * FROM {dsobj.table} WHERE world = $1'

        if not kwargs.get('name'):
            query = f'{base} AND id = ANY($2)'
        else:
            if dsobj.table == "village":
                iterable = [vil.replace("|", "") for vil in iterable]
                query = f'{base} AND CAST(x AS TEXT)||CAST(y as TEXT) = ANY($2)'

            else:
                iterable = [utils.encode(obj) for obj in iterable]
                if dsobj.table == "tribe":
                    query = f'{base} AND ARRAY[LOWER(name), LOWER(tag)] && $2'
                else:
                    query = f'{base} AND LOWER(name) = ANY($2)'

        async with self.tribal_pool.acquire() as conn:
            res = await conn.fetch(query, world, iterable)
            if kwargs.get('dictionary'):
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
        await self.member_pool.close()
        await self.tribal_pool.close()
        await self.close()


intents = discord.Intents.default()
intents.presences = False
intents.typing = False

dsbot = DSBot(command_prefix=prefix, intents=intents)
dsbot.run(secret.TOKEN)
