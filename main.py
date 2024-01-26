import data.credentials as secret
from utils import DSTree
from discord.ext import commands
from discord import app_commands
from bs4 import BeautifulSoup
import concurrent.futures
import functools
import discord
import asyncpg
import aiohttp
import asyncio
import random
import utils
import os


class DSBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        kwargs['intents'] = discord.Intents.default()
        super().__init__(*args, **kwargs)

        path = os.path.dirname(__file__)
        self.data_path = f"{path}/data"

        self.worlds = {}
        self.players = {}
        self.tribes = {}

        # age of player and tribe cache
        self.cache_age = {}

        # discord member cache
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

        self._lock = None
        self.config = utils.Config(self)
        self.owner_id = 211836670666997762
        self.activity = discord.Activity(type=0, name=secret.status)
        self.remove_command("help")

    async def setup_hook(self):
        self._lock = asyncio.Event()

        await self.setup_cogs()
        self.set_global_param_description()

        if secret.dev:
            guild = discord.Object(id=213992901263228928)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

    async def on_ready(self):
        # db / aiohttp setup
        if not self._lock.is_set():
            # initiates session object and db conns
            self.session = aiohttp.ClientSession()
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
            self.logger.debug("Initiaton Done")
            self._lock.set()

        print("Erfolgreich Verbunden!")

    def is_locked(self):
        return not self._lock.is_set()

    async def wait_until_unlocked(self):
        return await self._lock.wait()

    async def on_message(self, message) -> None:
        if message.author.id == self.owner_id:
            await self.process_commands(message)

    async def report_to_owner(self, msg):
        owner = await self.fetch_user(self.owner_id)
        await owner.send(msg)

    async def callback(self, *args):
        payload = args[-1]
        self.logger.debug(f"payload received: {payload}")

        if payload == "200":
            await self.loop_per_hour()
            return
        elif payload == "400":
            msg = "engine broke once, restarting"
        elif payload == "404":
            msg = "database script ended with a failure"
        else:
            msg = "unknown payload"

        await self.loop.create_task(self.report_to_owner(msg))

    # defaul executor somehow leaks RAM
    async def execute(self, func, *args, **kwargs):
        with concurrent.futures.ThreadPoolExecutor() as pool:
            package = functools.partial(func, *args, **kwargs)
            result = await self.loop.run_in_executor(pool, package)

        return result

    # get's called after db update
    async def loop_per_hour(self):
        await self._lock.wait()

        self.logger.debug("loop called")
        await self.update_worlds()

        for cog in self.cogs.values():
            loop = getattr(cog, "called_per_hour", None)

            try:
                if loop is not None:
                    await loop()
            except Exception as error:
                self.logger.debug(f"{cog.qualified_name} Cog Error: {error}")

    async def get_tribal_cache(self, interaction, ds_type=None):
        timestamp = interaction.created_at.timestamp()
        age = self.cache_age.get(interaction.server)

        if ds_type is not None:
            # either client.players or client.tribes
            world_cache = getattr(self, f"{ds_type}s")
            cached_objects = world_cache.get(interaction.server)

        else:
            player_cache = self.players.get(interaction.server, {})
            tribe_cache = self.tribes.get(interaction.server, {})

            if not tribe_cache and not player_cache:
                cached_objects = None
            else:
                cached_objects = (player_cache, tribe_cache)

        if not cached_objects or (timestamp - age) > 14400:
            player_query = f'SELECT * FROM player_{interaction.server}'
            tribe_query = f'SELECT * FROM tribe_{interaction.server}'

            async with interaction.client.tribal_pool.acquire() as conn:
                players = {rec['id']: utils.Player(rec) for rec in await conn.fetch(player_query)}
                tribes = {rec['id']: utils.Tribe(rec) for rec in await conn.fetch(tribe_query)}

                self.players[interaction.server] = players
                self.tribes[interaction.server] = tribes
                self.cache_age[interaction.server] = timestamp

                if ds_type == 'player':
                    return players
                elif ds_type == 'tribe':
                    return tribes
                else:
                    return tribes, players

        return cached_objects

    async def db_connect(self):
        result = []

        for db, db_data in secret.databases.items():
            conn_data = {'host': db_data['ip'],
                         'port': db_data['port'],
                         'user': db_data['user'],
                         'password': db_data['key'],
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

        cmd_tasks = 'CREATE TABLE IF NOT EXISTS tasks' \
                    '(id SERIAL PRIMARY KEY, guild_id BIGINT,' \
                    'channel_id BIGINT, command TEXT,' \
                    'arguments TEXT, time TIME)'

        querys = (reminder, iron, usage,
                  slot, member, cmd_tasks)

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
            # __eq__ checks for name/nick
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
            self.logger.error("no worlds found in database")
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

    def get_query(self, table_type, server, archive, placeholder_amount=1):
        placeholders = list(f"${n}" for n in range(1, placeholder_amount + 1))

        if archive is not None:
            table = f"{table_type}_{archive}"
            clause = "world = $1 AND"
            placeholders.remove("$1")
            placeholders.append(f"${placeholder_amount + 1}")
        else:
            table = f"{table_type}_{server}"
            clause = ""

        return table, clause, placeholders if placeholder_amount > 1 else placeholders[0]

    async def fetch_all(self, server, table=0, dictionary=False):
        dsobj = utils.DSType(table, server=server)

        async with self.tribal_pool.acquire() as conn:
            cache = await conn.fetch(f'SELECT * FROM {dsobj.table}')

            if dictionary:
                result = {rec['id']: dsobj.Class(rec) for rec in cache}
            else:
                result = [dsobj.Class(rec) for rec in cache]

            return result

    async def fetch_random(self, server, **kwargs):
        amount = kwargs.get('amount', 1)
        top = kwargs.get('top', 500)
        dsobj = utils.DSType(kwargs.get('tribe', 0), server=server)
        least = kwargs.get('least', False)

        query = f'SELECT * FROM {dsobj.table} WHERE rank <= $1'
        async with self.tribal_pool.acquire() as conn:
            data = await conn.fetch(query, top)

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

    async def fetch_player(self, server, searchable, *, name=False, archive=None):
        table, clause, placeholder = self.get_query('player', server, archive)

        if name:
            searchable = utils.encode(searchable)
            query = f'SELECT * FROM {table} WHERE {clause} LOWER(name) = {placeholder}'
        else:
            query = f'SELECT * FROM {table} WHERE {clause} id = {placeholder}'

        if archive is not None:
            arguments = (server, searchable)
        else:
            arguments = (searchable,)

        async with self.tribal_pool.acquire() as conn:
            result = await conn.fetchrow(query, *arguments)
            return utils.Player(result) if result else None

    async def fetch_tribe(self, server, searchable, *, name=False, archive=None):
        table, clause, placeholder = self.get_query('tribe', server, archive)

        if name:
            searchable = utils.encode(searchable)
            query = f'SELECT * FROM {table} WHERE {clause} (LOWER(tag) = {placeholder} OR LOWER(name) = {placeholder})'
        else:
            query = f'SELECT * FROM {table} WHERE {clause} id = {placeholder}'

        if archive is not None:
            arguments = (server, searchable)
        else:
            arguments = (searchable,)

        async with self.tribal_pool.acquire() as conn:
            result = await conn.fetchrow(query, *arguments)

        return utils.Tribe(result) if result else None

    async def fetch_village(self, server, searchable, *, coord=False, archive=None):
        table, clause, placeholders = self.get_query('village', server, archive, placeholder_amount=2)

        if coord:
            x, y = searchable.split('|')
            query = f'SELECT * FROM {table} WHERE {clause} x = {placeholders[0]} AND y = {placeholders[1]}'
            searchable = [int(x), int(y)]
        else:
            query = f'SELECT * FROM {table} WHERE {clause} id = {placeholders}'
            searchable = [searchable]

        if archive is not None:
            searchable.insert(0, server)

        async with self.tribal_pool.acquire() as conn:
            result = await conn.fetchrow(query, *searchable)

        return utils.Village(result) if result else None

    async def fetch_both(self, server, searchable, *, name=True, archive=None):
        kwargs = {'name': name, 'archive': archive}
        player = await self.fetch_player(server, searchable, **kwargs)
        if player:
            return player

        tribe = await self.fetch_tribe(server, searchable, **kwargs)
        return tribe

    async def fetch_top(self, server, top, table=None, **kwargs):
        dsobj = utils.DSType(table or 0, server=server)
        attribute = kwargs.get('attribute', 'rank')
        way = "ASC" if attribute == "rank" else "DESC"

        query = f'SELECT * FROM {dsobj.table} ' \
                f'ORDER BY {attribute} {way} LIMIT $1'

        async with self.tribal_pool.acquire() as conn:
            top10 = await conn.fetch(query, top)

            if kwargs.get('dictionary') is True:
                return {rec[1]: dsobj.Class(rec) for rec in top10}
            else:
                return [dsobj.Class(rec) for rec in top10]

    async def fetch_tribe_member(self, server, allys, name=False):
        if not isinstance(allys, (tuple, list)):
            allys = [allys]
        if name:
            tribes = await self.fetch_bulk(server, allys, table=1, name=True)
            allys = [tribe.id for tribe in tribes]

        query = f'SELECT * FROM player_{server} WHERE tribe_id = ANY($1)'
        async with self.tribal_pool.acquire() as conn:
            res = await conn.fetch(query, allys)
            return [utils.Player(rec) for rec in res]

    async def fetch_bulk(self, server, iterable, table=None, **kwargs):
        ds_type = utils.DSType(table or 0)
        table, clause, placeholder = self.get_query(ds_type.base_table, server, kwargs.get('archive'))
        base = f'SELECT * FROM {table} WHERE {clause} '

        if not kwargs.get('name'):
            query = f'{base} id = ANY({placeholder})'
        else:
            if ds_type.base_table == "village":
                iterable = [vil.replace("|", "") for vil in iterable]
                query = f'{base} CAST(x AS TEXT)||CAST(y as TEXT) = ANY({placeholder})'

            else:
                iterable = [utils.encode(obj) for obj in iterable]
                if ds_type.base_table == "tribe":
                    query = f'{base} ARRAY[LOWER(name), LOWER(tag)] && {placeholder}'
                else:
                    query = f'{base} LOWER(name) = ANY({placeholder})'

        if kwargs.get('archive') is not None:
            arguments = (server, iterable)
        else:
            arguments = (iterable,)

        async with self.tribal_pool.acquire() as conn:
            res = await conn.fetch(query, *arguments)
            if kwargs.get('dictionary'):
                return {rec[1]: ds_type.Class(rec) for rec in res}
            else:
                return [ds_type.Class(rec) for rec in res]

    async def fetch_profile_picture(self, dsobj, default_avatar=False):
        async with self.session.get(dsobj.guest_url) as resp:
            soup = BeautifulSoup(await resp.read(), "html.parser")

            tbody = soup.find(id='content_value')
            tables = tbody.findAll('table')
            tds = tables[1].findAll('td', attrs={'valign': 'top'})
            images = tds[1].findAll('img')

            if not images or 'badge' in images[0]['src']:
                return

            endings = ['large']
            if default_avatar is True:
                endings.append('jpg')

            if images[0]['src'].endswith(tuple(endings)):
                return images[0]['src']

    def set_global_param_description(self):
        params = self.languages['german'].params

        for command in self.tree.walk_commands():
            if isinstance(command, app_commands.Command):
                for param, description in params.items():
                    # noinspection PyProtectedMember
                    command_parameters = command._params

                    if param in command_parameters:
                        if str(command_parameters[param].description) == "…":
                            command_parameters[param].description = description

    # imports all cogs at startup
    async def setup_cogs(self):
        for file in secret.default_cogs:
            try:
                await self.load_extension(f"cogs.{file}")
            except commands.ExtensionNotFound:
                print(f"module {file} not found")

    async def logout(self):
        await self.session.close()
        await self.member_pool.close()
        await self.tribal_pool.close()
        await self.close()


dsbot = DSBot(command_prefix="!", tree_cls=DSTree)
dsbot.run(secret.TOKEN)
