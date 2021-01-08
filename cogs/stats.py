from utils import DSUserNotFound, MissingRequiredKey
from utils import seperator as sep
from discord.ext import commands
from bs4 import BeautifulSoup
import asyncpg
import discord
import utils


class Bash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.type = 1
        self.in_a_day = "https://{}/guest.php?village=null&" \
                        "screen=ranking&mode=in_a_day&type={}"

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

            user_copy = user.copy()
            user_copy.remove(dsobj)
            other_user = user_copy[0]

            result = []
            for key, represent in attributes.items():
                value = getattr(dsobj, key)

                if len(user) == 2 and getattr(other_user, key) > value:
                    string_value = f"{value}"
                else:
                    string_value = f"**{value}**"

                result.append(attributes[key].format(string_value))

            embed.add_field(name=f"{dsobj}", value="\n".join(result))

        await ctx.send(embed=embed)

    @commands.command(name="recap")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def recap(self, ctx, *, args):
        time = 7
        args = args.split(' ')
        if args[-1].isdigit():
            dsobj = await self.bot.fetch_both(ctx.server, ' '.join(args[:-1]))
            if dsobj:
                time = int(args[-1])
            else:
                dsobj = await self.bot.fetch_both(ctx.server, ' '.join(args))
        else:
            dsobj = await self.bot.fetch_both(ctx.server, ' '.join(args))

        if not dsobj:
            raise DSUserNotFound(' '.join(args))

        if not 31 > time > 0:
            msg = "Das Maximum für den Recap Command sind 30 Tage"
            await ctx.send(msg)
            return

        try:
            dsobj8 = await self.bot.fetch_both(ctx.server, dsobj.id, name=False, archive=time)

            if dsobj8 is None:
                obj = "Spieler" if dsobj.alone else "Stamm"
                msg = f"Der {obj}: `{dsobj.name}` ist noch keine {time} Tage auf der Welt!"
                await ctx.send(msg)
                return

            point1, villages1, bash1 = dsobj.points, dsobj.villages, dsobj.all_bash
            point8, villages8, bash8 = dsobj8.points, dsobj8.villages, dsobj8.all_bash

        # upon database reset we use twstats as temporary workaround
        except asyncpg.UndefinedTableError:
            time = 29
            page_link = f"{dsobj.twstats_url}&mode=history"
            async with self.bot.session.get(page_link) as r:
                soup = BeautifulSoup(await r.read(), "html.parser")

            try:
                data = soup.find(id='export').text.split("\n")
                point1, villages1, bash1 = data[0].split(",")[4:7]
                point8, villages8, bash8 = data[time].split(",")[4:7]

            except (IndexError, ValueError, AttributeError):
                obj = "Spieler" if dsobj.alone else "Stamm"
                msg = f"Der {obj}: `{dsobj.name}` ist noch keine {time} Tage auf der Welt!"
                await ctx.send(msg)
                return

        p_done = sep(int(point1) - int(point8))
        if p_done.startswith("-"):
            points_done = f"`{p_done[1:]}` Punkte verloren,"
        else:
            points_done = f"`{p_done}` Punkte gemacht,"

        v_done = int(villages1) - int(villages8)
        vil = "Dorf" if v_done == 1 or v_done == -1 else "Dörfer"
        if v_done < 0:
            villages_done = f"`{str(v_done)[1:]}` {vil} verschenkt"
        else:
            villages_done = f"`{v_done}` {vil} geholt"

        b_done = sep(int(bash1) - int(bash8))
        if b_done.startswith("-"):
            bashpoints_done = f"`{b_done[1:]}` Bashpoints verloren"
        else:
            bashpoints_done = f"sich `{b_done}` Bashpoints erkämpft"

        has = "hat" if dsobj.alone else "haben"
        since = "seit gestern" if time == 1 else f"in den letzten {time} Tagen:"

        answer = f"`{dsobj.name}` {has} {since} {points_done} " \
                 f"{villages_done} und {bashpoints_done}"

        await ctx.send(answer)

    @commands.group(name="top")
    async def top_(self, ctx, state):
        key = ctx.lang.top_options.get(state.lower())

        if key is None:
            raise MissingRequiredKey(ctx.lang.top_options)

        url = self.in_a_day.format(ctx.world.url, key)
        async with self.bot.session.get(url) as r:
            soup = BeautifulSoup(await r.read(), "html.parser")

        table = soup.find('table', id='in_a_day_ranking_table')
        rows = table.find_all('tr')
        result = []

        try:
            datapack = {}
            cache = soup.find('option', selected=True)
            for row in rows[1:6]:
                vanity = row.find('a')['href']
                player_id = int(vanity.split("=")[-1])
                points = row.findAll("td")[3].text
                datapack[player_id] = points

            players = await self.bot.fetch_bulk(ctx.server, datapack.keys(), dictionary=True)
            for player_id, points in datapack.items():
                player = players.get(player_id)
                if player:
                    result.append(f"`{points}` **|** {player.guest_mention}")

            msg = '\n'.join(result)
            title = f"{cache.text}\n(an einem Tag)"
            embed = discord.Embed(title=title, description=msg)

        except (AttributeError, TypeError):
            msg = "Aktuell liegen noch keine Daten vor"
            embed = discord.Embed(description=msg, color=discord.Color.red())

        await ctx.send(embed=embed)

    @commands.command(name="daily", aliases=["dailytribe"])
    async def daily_(self, ctx, award_type):
        award = award_type.lower()
        award_data = ctx.lang.daily_options.get(award)

        if award_data is None:
            raise MissingRequiredKey(ctx.lang.daily_options)

        tribe = ctx.invoked_with.lower() == "dailytribe"
        dstype = utils.DSType('tribe' if tribe else 'player')

        async with self.bot.pool.acquire() as conn:
            if tribe and award == "unterstützer":
                query = '(SELECT tribe_id, SUM(sup_bash) AS sup FROM player WHERE ' \
                        'world = $1 GROUP BY tribe_id ORDER BY sup DESC) ' \
                        'UNION ALL ' \
                        '(SELECT tribe_id, SUM(sup_bash) AS sup FROM player1 WHERE ' \
                        'world = $1 GROUP BY tribe_id ORDER BY sup DESC)'

                cache = await conn.fetch(query, ctx.server)
                all_values = {rec['tribe_id']: [] for rec in cache}
                all_values.pop(0)

                for record in cache:
                    arguments = list(record.values())
                    tribe_id = arguments[0]
                    points = arguments[1]
                    if tribe_id != 0:
                        all_values[tribe_id].append(points)

                value_list = [(k, v) for k, v in all_values.items() if len(v) == 2]
                value_list.sort(key=lambda tup: tup[1][0] - tup[1][1], reverse=True)

                tribe_ids = [tup[0] for tup in value_list[:5]]
                kwargs = {'table': dstype.table, 'dictionary': True}
                tribes = await self.bot.fetch_bulk(ctx.server, tribe_ids, **kwargs)
                data = [tribes[idc] for idc in tribe_ids]

            else:
                base = 'SELECT * FROM {0} INNER JOIN {1} ON {0}.id = {1}.id ' \
                       'WHERE {0}.world = $1 AND {1}.world = $1 ' \
                       'ORDER BY ({0}.{2} - {1}.{2}) {3} LIMIT 5'

                switch = "ASC" if award in ["verlierer"] else "DESC"
                query = base.format(dstype.table, f"{dstype.table}1", award_data['value'], switch)
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

            if award in ["verlierer"]:
                value = old_value - cur_value
            else:
                value = cur_value - old_value

            if value < 1:
                continue

            item = award_data['item']
            if value == 1 and item == "Dörfer":
                item = "Dorf"

            line = f"`{sep(value)} {item}` | {dsobj.guest_mention}"
            ranking.append(line)

        if ranking:
            description = "\n".join(ranking)
            title = f"{award_data['title']} des Tages ({ctx.world.show(True)})"
            footer = "Daten aufgrund von Inno nur stündlich aktualisiert"
            embed = discord.Embed(title=title, description=description)
            embed.colour = discord.Color.blue()
            embed.set_footer(text=footer)

        else:
            msg = "Aktuell liegen noch keine Daten vor"
            embed = discord.Embed(description=msg, color=discord.Color.red())

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Bash(bot))
