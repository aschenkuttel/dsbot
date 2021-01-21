from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
import discord
import logging
import utils

logger = logging.getLogger('dsbot')


class Task:
    def __init__(self, bot, row):
        self.bot = bot
        self.id = row['id']
        self.guild_id = row['guild_id']
        self.channel_id = row['channel_id']
        self.cmd = row['command']
        self.arguments = row['arguments']
        self.time = row['time']
        self.callback = getattr(self, f"{self.cmd}_task")

    @property
    def rep_time(self):
        return self.time.strftime("%H:%M")

    async def run(self):
        try:
            channel = self.bot.get_channel(self.channel_id)
            server = self.bot.config.get_world(channel)
            if server is None:
                return

            tribe = self.cmd == "dailytribe"
            await self.callback(channel, server, self.arguments, tribe)
            logger.debug(f"TASK {self.id} ran successfully")
            return True
        except discord.Forbidden:
            logger.error(f"TASK {self.id} was forbidden")
        except Exception as error:
            logger.error(f"TASK {self.id} crashed: {error}")

    async def dailytribe_task(self, *args):
        await self.daily(*args)

    async def daily_task(self, *args):
        await self.daily(*args)

    async def daily(self, channel, world, arguments, tribe=True):
        lang = self.bot.languages['german']

        if arguments:
            award = arguments.lower()

            if award not in lang.daily_options:
                logger.error(f"TASK {self.id} has an invalid daily")
                return
            else:
                ds_types = [award]

        else:
            ds_types = ("points", "conquerer", "loser", "basher", "defender")

        amount = 3 if not arguments else 5
        dstype = utils.DSType('tribe' if tribe else 'player')
        batch = []

        async with self.bot.pool.acquire() as conn:
            for award in ds_types:
                award_data = lang.daily_options.get(award)

                if tribe and award == "supporter":
                    query = '(SELECT tribe_id, SUM(sup_bash) AS sup FROM player ' \
                            'WHERE world = $1 AND tribe_id != 0 GROUP BY tribe_id ' \
                            f'ORDER BY sup DESC LIMIT {amount}) ' \
                            'UNION ALL ' \
                            '(SELECT tribe_id, SUM(sup_bash) AS sup FROM player1 ' \
                            'WHERE world = $1 AND tribe_id != 0 GROUP BY tribe_id ' \
                            f'ORDER BY sup DESC LIMIT {amount})'

                    cache = await conn.fetch(query, world)
                    all_values = {rec['tribe_id']: [] for rec in cache}

                    for record in cache:
                        tribe_id, points = list(record.values())
                        all_values[tribe_id].append(points)

                    value_list = [(k, v) for k, v in all_values.items() if len(v) == 2]
                    value_list.sort(key=lambda tup: tup[1][0] - tup[1][1], reverse=True)

                    tribe_ids = [tup[0] for tup in value_list]
                    kwargs = {'table': dstype.table, 'dictionary': True}
                    tribes = await self.bot.fetch_bulk(world, tribe_ids, **kwargs)
                    data = [tribes[idc] for idc in tribe_ids]

                else:
                    base = 'SELECT * FROM {0} INNER JOIN {1} ON {0}.id = {1}.id ' \
                           'WHERE {0}.world = $1 AND {1}.world = $1 ' \
                           'ORDER BY ({0}.{2} - {1}.{2}{4}) {3} LIMIT {5}'

                    switch = "ASC" if award in ["loser"] else "DESC"
                    args = [dstype.table, f"{dstype.table}1",
                            award_data['value'], switch, amount]

                    if tribe and award in ("loser", "conquerer"):
                        if award == "loser":
                            head = " + "
                        else:
                            head = " - "

                        member_loss = f"{head}({dstype.table}.member - {dstype.table}1.member)"
                        args.append(member_loss)
                    else:
                        args.append('')

                    query = base.format(*args)
                    data = await conn.fetch(query, world)

                ranking = []
                for record in data:
                    if isinstance(record, utils.Tribe):
                        values = all_values[record.id]
                        cur_value, old_value = values
                        dsobj = record

                    else:
                        records = utils.unpack_join(record)
                        dsobj = dstype.Class(records[0])
                        old_dsobj = dstype.Class(records[1])
                        cur_value = getattr(dsobj, award_data['value'], 0)
                        old_value = getattr(old_dsobj, award_data['value'], 0)

                    if award in ["loser"]:
                        value = old_value - cur_value
                    else:
                        value = cur_value - old_value

                    if tribe and award in ("loser", "conquerer"):
                        if award == "loser":
                            value += dsobj.member - old_dsobj.member
                        else:
                            value -= dsobj.member - old_dsobj.member

                    if value < 1:
                        continue

                    item = award_data['item']
                    if value == 1 and item == "Dörfer":
                        item = "Dorf"

                    line = f"`{utils.seperator(value)} {item}` | {dsobj.guest_mention}"
                    ranking.append(line)

                if ranking:
                    title = f"{award_data['title']} des Tages"
                    body = "\n".join(ranking)

                    if arguments is None:
                        body = f"**{title}**\n{body}"

                    batch.append(body)

        if batch:
            world_obj = self.bot.worlds[world]
            world_title = world_obj.show(plain=True)

            if arguments is None:
                batch.insert(0, f"**Ranglisten des Tages der {world_title}**")
            else:
                batch.insert(0, f"**{award_data['title']} des Tages {world_title}**")

            description = "\n\n".join(batch)
            embed = discord.Embed(description=description)
            embed.colour = discord.Color.blue()
            await channel.send(embed=embed)

    async def map_task(self, channel, world, command_query, _):
        cog = self.bot.get_cog('Map')
        file = cog.top10_cache.get(world)

        if not command_query and file is not None:
            file.seek(0)
            dc_file = discord.File(file, 'map.png')
            await channel.send(file=dc_file)
            return

        zoom, top, player, label, center = utils.keyword(command_query, **cog.default_options)

        ds_type = "player" if player else "tribe"
        ds_objects = await self.bot.fetch_top(world, top.value, ds_type)

        colors = cog.colors.top()
        for tribe in ds_objects.copy():
            tribe.color = colors.pop(0)

        all_villages = await self.bot.fetch_all(world, "map")
        if not all_villages:
            return

        ds_dict = {dsobj.id: dsobj for dsobj in ds_objects}

        if player:
            args = (all_villages, {}, ds_dict)
        else:
            result = await self.bot.fetch_tribe_member(world, list(ds_dict))
            players = {pl.id: pl for pl in result}
            args = (all_villages, ds_dict, players)

        text = label.value in [2, 3]
        highlight = label.value in [1, 2]
        kwargs = {'zoom': zoom.value, 'label': text,
                  'highlight': highlight, 'center': center.value}
        file = await cog.send_map(channel, *args, **kwargs)

        if not command_query:
            cog.top10_cache[world] = file
        else:
            file.close()


class Tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.example = "{}tasks add 12 map player=True"
        self.commands = ("daily", "dailytribe", "map")

    async def task_engine(self):
        self.bot.loop.create_task(self.run_tasks())

    async def run_tasks(self):
        now = datetime.now()
        query = 'SELECT * FROM tasks WHERE EXTRACT(HOUR FROM time) = $1'
        async with self.bot.ress.acquire() as conn:
            cache = await conn.fetch(query, now.hour)
            tasks = [Task(self.bot, rec) for rec in cache]

        guild_cache = {t.guild_id: [] for t in tasks}
        for task in tasks:
            guild_cache[task.guild_id].append(task)

        minute_shards = {n: [] for n in range(11)}
        dead_tasks = []
        minute = 0

        for guild_id, tasks in guild_cache.items():
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                dead_tasks.extend(tasks)
                continue

            inactive = self.bot.config.get('inactive', guild.id)
            if inactive is True:
                continue

            for task in tasks:
                minute_shards[minute].append(task)
                minute += 1

                if minute == 11:
                    minute = 0

        counter = 0
        for minute in range(11):
            minute_tasks = minute_shards[minute]

            if not minute_tasks:
                continue

            for task in minute_tasks:
                resp = await task.run()
                if resp is True:
                    counter += 1

            now = datetime.now()
            next_minute = timedelta(minutes=1)
            next_begin = (now + next_minute).replace(second=0)
            seconds = (next_begin - now).total_seconds()
            await asyncio.sleep(seconds)

        logger.debug(f"Tasks finished: {counter} Tasks")

        if dead_tasks:
            query = 'DELETE FROM tasks WHERE id = ANY($1)'
            dead_ids = [t.id for t in dead_tasks]

            async with self.bot.ress.acquire() as conn:
                await conn.execute(query, dead_ids)

            logger.debug(f"Deleted {len(dead_ids)} Tasks")

    def task_embed(self, description, title=''):
        embed = discord.Embed(title=title, description=description)
        embed.colour = 0xD8E0BB
        return embed

    async def fetch_tasks(self, guild_id, ext=None):
        query = 'SELECT * FROM tasks WHERE guild_id = $1'
        if ext is None:
            conn = await self.bot.ress.acquire()
        else:
            conn = ext

        cache = await conn.fetch(query, guild_id)
        tasks = [Task(self.bot, rec) for rec in cache]

        if ext is None:
            await self.bot.ress.release(conn)

        return tasks

    @commands.group(name="tasks", invoke_without_command=True)
    async def tasks(self, ctx):
        tasks = await self.fetch_tasks(ctx.guild.id)
        result = []

        for task in tasks:
            channel = ctx.guild.get_channel(task.channel_id)
            head = f"`ID {task.id}` | `{task.rep_time} Uhr`"
            body = f"{channel.mention} | {task.cmd} {task.arguments}"
            result.append(f"{head} | {body}")

        if result:
            description = "\n".join(result)
        else:
            description = "Der Server hat keine aktiven Tasks"

        await ctx.send(embed=self.task_embed(description))

    @tasks.command(name="add")
    async def add_(self, ctx, time_int: int, *, command_query):
        if not 0 <= time_int <= 24:
            sample = self.example.format(ctx.prefix)
            msg = f"**Fehlerhafte Eingabe | Beispiel:**\n{sample}"
            await ctx.send(embed=utils.error_embed(msg))
            return

        time = datetime.strptime(str(time_int), "%H")
        parts = command_query.split(" ")
        command = parts.pop(0)

        if command not in self.commands:
            example = ", ".join(self.commands)
            msg = f"**Dieser Command wird nicht unterstützt:**\n{example}"
            await ctx.send(embed=utils.error_embed(msg))
            return

        query = 'INSERT INTO tasks(guild_id, channel_id, command, arguments, time)' \
                'VALUES ($1, $2, $3, $4, $5) RETURNING id'
        async with self.bot.ress.acquire() as conn:
            tasks = await self.fetch_tasks(ctx.guild.id, conn)

            if len(tasks) == 3:
                msg = "Dieser Server hat bereits 3 registrierte Tasks"
                await ctx.send(embed=utils.error_embed(msg))
                return

            cmd_args = " ".join(parts)
            args = [ctx.guild.id, ctx.channel.id, command, cmd_args, time]
            cache = await conn.fetchrow(query, *args)

        msg = f"Task **{cache['id']}** wurde erfolgreich registriert"
        await ctx.send(embed=self.task_embed(description=msg))

    @tasks.command(name="remove")
    async def remove_(self, ctx, task_id: int):
        query = 'DELETE FROM tasks WHERE guild_id = $1 AND id = $2 RETURNING TRUE'
        async with self.bot.ress.acquire() as conn:
            resp = await conn.fetchrow(query, ctx.guild.id, task_id)

            if resp is None:
                msg = "Der Task gehört entweder nicht diesem Server oder die ID existiert nicht"
                await ctx.send(embed=utils.error_embed(msg))
            else:
                msg = "Der Task wurde erfolgreich gelöscht"
                await ctx.send(embed=self.task_embed(msg))

    @tasks.command(name="clear")
    async def clear_(self, ctx):
        query = 'DELETE FROM tasks WHERE guild_id = $1'
        async with self.bot.ress.acquire() as conn:
            await conn.execute(query, ctx.guild.id)

        msg = "Alle Tasks wurden erfolgreich gelöscht"
        await ctx.send(embed=self.task_embed(msg))

    @commands.is_owner()
    @tasks.command(name="preview")
    async def preview_(self, ctx, task_id: int):
        query = 'SELECT * FROM tasks WHERE id = $1'
        async with self.bot.ress.acquire() as conn:
            cache = await conn.fetchrow(query, task_id)
            await ctx.send(cache)


def setup(bot):
    bot.add_cog(Tasks(bot))
