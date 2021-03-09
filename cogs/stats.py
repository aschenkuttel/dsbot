from utils import DSUserNotFound, MissingRequiredKey
from utils import seperator as sep
from discord.ext import commands
from bs4 import BeautifulSoup
import asyncpg
import discord
import utils


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.type = 1
        self.in_a_day = "https://{}/guest.php?village=null&" \
                        "screen=ranking&mode=in_a_day&type={}"
        self.bashtypes = {'offensive': "att_bash",
                          'general': "all_bash",
                          'defensive': "def_bash",
                          'support': "sup_bash"}

    @commands.command(name="bash")
    async def bash(self, ctx, *, arguments):
        args = arguments.split("/")
        if len(args) != 2:
            dsobj = await self.bot.fetch_both(ctx.server, arguments)
            if dsobj is None:
                raise utils.DSUserNotFound(arguments)
            else:
                user = [dsobj]

        else:
            player1 = args[0].strip()
            player2 = args[1].strip()

            if player1.lower() == player2.lower():
                await ctx.send("Dein Witz :arrow_right: Unlustig")
                return

            s1 = await self.bot.fetch_both(ctx.server, player1)
            s2 = await self.bot.fetch_both(ctx.server, player2)
            user = [s1, s2]

            if s1 is None or s2 is None:
                wrong_name = player1 if s1 is None else player2
                raise utils.DSUserNotFound(wrong_name)

        for dsobj in user:
            if isinstance(dsobj, utils.Tribe):
                dsobj.sup_bash = 0
                members = await self.bot.fetch_tribe_member(ctx.server, dsobj.id)

                for member in members:
                    dsobj.sup_bash += member.sup_bash

        embed = discord.Embed()

        for dsobj in user:
            attributes = {"att_bash": "`OFF` | {}",
                          "def_bash": "`DEF` | {}",
                          "sup_bash": "`SUP` | {}",
                          "all_bash": "`ALL` | {}"}

            if len(user) == 2:
                user_copy = user.copy()
                user_copy.remove(dsobj)
                other_user = user_copy[0]
            else:
                other_user = None

            result = []
            for key, represent in attributes.items():
                value = getattr(dsobj, key)

                if other_user and getattr(other_user, key) > value:
                    string_value = f"{value}"
                else:
                    string_value = f"**{value}**"

                result.append(represent.format(string_value))

            embed.add_field(name=f"{dsobj}", value="\n".join(result))

        await ctx.send(embed=embed)

    @commands.command(name="bashrank")
    async def bashrank_(self, ctx, tribe: utils.DSConverter('tribe'), bashtype=None):
        bashtype = bashtype.lower() or "offensive"

        if bashtype not in self.bashtypes:
            raise MissingRequiredKey(self.bashtypes.keys(), "tribe")

        bashstat = self.bashtypes.get(bashtype)
        members = await self.bot.fetch_tribe_member(ctx.server, tribe.id)
        members.sort(key=lambda m: getattr(m, bashstat), reverse=True)

        result = [f"**Stammesinterne Rangliste {tribe.mention}**",
                  f"**Bashtype:** `{bashtype.capitalize()}`", ""]
        for member in members[:15]:
            value = getattr(member, bashstat)
            line = f"`{utils.seperator(value)}` | {member}"
            result.append(line)

        embed = discord.Embed(description="\n".join(result))
        await ctx.send(embed=embed)

    @commands.command(name="recap")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def recap(self, ctx, *, args):
        dsobj = None
        parts = args.split(' ')
        if parts[-1].isdigit():
            dsobj = await self.bot.fetch_both(ctx.server, ' '.join(parts[:-1]))

        if dsobj is None:
            dsobj = await self.bot.fetch_both(ctx.server, args)
            time = 7
        else:
            time = int(parts[-1])

        if not dsobj:
            raise DSUserNotFound(args)
        else:
            utils.valid_range(time, 1, 30, "day")

        try:
            dsobj8 = await self.bot.fetch_both(ctx.server, dsobj.id, name=False, archive=time)

            if dsobj8 is None:
                obj = "Spieler" if dsobj.alone else "Stamm"
                msg = f"Der {obj}: `{dsobj.name}` ist noch keine {time} Tage auf der Welt!"
                await ctx.send(msg)
                return

            current_day = dsobj.points, dsobj.villages, dsobj.all_bash
            day_in_past = dsobj8.points, dsobj8.villages, dsobj8.all_bash

        # upon database reset we use twstats as temporary workaround
        except asyncpg.UndefinedTableError:
            history_url = f"{dsobj.twstats_url}&mode=history"
            async with self.bot.session.get(history_url) as r:
                soup = BeautifulSoup(await r.read(), "html.parser")

            try:
                data = soup.find(id='export').text.split("\n")
                current_day = data[0].split(",")[4:7]
                day_in_past = data[time].split(",")[4:7]

            except (IndexError, ValueError, AttributeError):
                obj = "Spieler" if dsobj.alone else "Stamm"
                msg = f"Der {obj}: `{dsobj.name}` ist noch keine {time} Tage auf der Welt!"
                await ctx.send(msg)
                return

        result = []

        for index, current in enumerate(current_day):
            past = int(day_in_past[index])
            value = sep(int(current) - past)

            if index == 1:
                result[-1] += ","

                # preregister accounts have no villages
                # hence we ignore the first "conquer"
                if past == 0:
                    value = sep(int(current) - past - 1)

            if value.startswith("-"):
                result.append(f"`{value[1:]}` {ctx.lang.recap[index][0]}")
            else:
                result.append(f"`{value}` {ctx.lang.recap[index][1]}")

        since = "seit gestern" if time == 1 else f"in den letzten {time} Tagen"
        answer = f"`{dsobj.name}` hat {since} {' '.join(result)}"
        await ctx.send(answer)

    @commands.group(name="top")
    async def top_(self, ctx, state):
        key = ctx.lang.top_options.get(state.lower())

        if key is None:
            raise MissingRequiredKey(ctx.lang.top_options)

        url = self.in_a_day.format(ctx.world.url, key)
        async with self.bot.session.get(url) as r:
            soup = BeautifulSoup(await r.read(), "html.parser")

        table = soup.find("table", id='in_a_day_ranking_table')
        rows = table.find_all("tr")
        result = []

        try:
            datapack = {}
            cache = soup.find("option", selected=True)
            for row in rows[1:6]:
                vanity = row.find("a")['href']
                player_id = int(vanity.split("=")[-1])
                points = row.findAll("td")[3].text
                datapack[player_id] = points

            players = await self.bot.fetch_bulk(ctx.server, datapack.keys(), dictionary=True)
            for player_id, points in datapack.items():
                player = players.get(player_id)
                if player:
                    result.append(f"`{points}` **|** {player.guest_mention}")

            msg = "\n".join(result)
            title = f"{cache.text}\n(an einem Tag)"
            embed = discord.Embed(title=title, description=msg)

        except (AttributeError, TypeError):
            msg = "Aktuell liegen noch keine Daten vor"
            embed = discord.Embed(description=msg, color=discord.Color.red())

        await ctx.send(embed=embed)

    @commands.command(name="daily", aliases=["dailytribe"])
    async def daily_(self, ctx, award_type=None):
        if award_type is not None:
            award = award_type.lower()

            if award not in ctx.lang.daily_options:
                raise MissingRequiredKey(ctx.lang.daily_options)
            else:
                ds_types = [award]

        else:
            ds_types = ("points", "conquerer", "loser", "basher", "defender")

        amount = 3 if award_type is None else 5
        tribe = ctx.invoked_with.lower() == "dailytribe"
        dstype = utils.DSType('tribe' if tribe else 'player')
        batch = []

        async with self.bot.tribal_pool.acquire() as conn:
            for award in ds_types:
                award_data = ctx.lang.daily_options.get(award)

                if tribe and award == "supporter":
                    query = '(SELECT tribe_id, SUM(sup_bash) AS sup FROM player ' \
                            'WHERE world = $1 AND tribe_id != 0 GROUP BY tribe_id ' \
                            f'ORDER BY sup DESC LIMIT {amount}) ' \
                            'UNION ALL ' \
                            '(SELECT tribe_id, SUM(sup_bash) AS sup FROM player1 ' \
                            'WHERE world = $1 AND tribe_id != 0 GROUP BY tribe_id ' \
                            f'ORDER BY sup DESC LIMIT {amount})'

                    cache = await conn.fetch(query, ctx.server)
                    all_values = {rec['tribe_id']: [] for rec in cache}

                    for record in cache:
                        tribe_id, points = list(record.values())
                        all_values[tribe_id].append(points)

                    value_list = [(k, v) for k, v in all_values.items() if len(v) == 2]
                    value_list.sort(key=lambda tup: tup[1][0] - tup[1][1], reverse=True)

                    tribe_ids = [tup[0] for tup in value_list]
                    kwargs = {'table': dstype.table, 'dictionary': True}
                    tribes = await self.bot.fetch_bulk(ctx.server, tribe_ids, **kwargs)
                    data = [tribes[idc] for idc in tribe_ids]

                else:
                    base = 'SELECT * FROM {0} INNER JOIN {1} ON {0}.id = {1}.id ' \
                           'WHERE {0}.world = $1 AND {1}.world = $1 ' \
                           'ORDER BY ({0}.{2} - {1}.{2}{5}) {3} LIMIT {4}'

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
                    data = await conn.fetch(query, ctx.server)

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

                    line = f"`{sep(value)} {item}` | {dsobj.guest_mention}"
                    ranking.append(line)

                if ranking:
                    title = f"{award_data['title']} des Tages"
                    body = "\n".join(ranking)

                    if award_type is None:
                        body = f"**{title}**\n{body}"

                    batch.append(body)

        if batch:
            world_title = ctx.world.represent(plain=True)

            if award_type is None:
                batch.insert(0, f"**Ranglisten des Tages der {world_title}**")
            else:
                batch.insert(0, f"**{award_data['title']} des Tages {world_title}**")

            description = "\n\n".join(batch)
            embed = discord.Embed(description=description)
            footer = "Daten aufgrund von Inno nur stündlich aktualisiert"
            embed.colour = discord.Color.blue()
            embed.set_footer(text=footer)

        else:
            msg = "Aktuell liegen noch keine Daten vor"
            embed = discord.Embed(description=msg, color=discord.Color.red())

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Stats(bot))
