from utils import DSConverter, DSUserNotFound, error_embed, seperator
from discord.ext import commands
from bs4 import BeautifulSoup
import asyncpg
import discord
import utils


class Bash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.never = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.base = "https://{}/guest.php?village" \
                    "=null&screen=ranking&mode=in_a_day&type={}"
        self.attribute = {'bash': "kill_att", 'def': "kill_def", 'sup': "kill_sup",
                          'farm': "loot_res", 'villages': "loot_vil",
                          'scavenge': "scavenge", 'conquer': "conquer"}
        self.values = {
            'angreifer': {'value': "att_bash", 'item': "Bashpoints"},
            'verteidiger': {'value': "def_bash", 'item': "Bashpoints"},
            'unterstützer': {'value': "sup_bash", 'item': "Bashpoints"},
            'kämpfer': {'value': "all_bash", 'item': "Bashpoints"},
            'verlierer': {'value': "villages", 'item': "Dörfer"},
            'eroberer': {'value': "villages", 'item': "Dörfer"}}
        self.translate = {'defbash': "verteidiger",
                          'offbash': "angreifer",
                          'supbash': "unterstützer",
                          'allbash': "kämpfer"}

    @commands.command(name="bash")
    async def bash(self, ctx, *, user: DSConverter):
        title = f"Besiegte Gegner von {user.name}"
        result = [f"`OFF` | **{seperator(user.att_bash)} Bashpoints**",
                  f"`DEF` | **{seperator(user.def_bash)} Bashpoints**"]

        if isinstance(user, utils.Player):
            result.append(f"`SUP` | **{seperator(user.sup_bash)} Bashpoints**")

        result.append(f"`INS` | **{seperator(user.all_bash)} Bashpoints**")
        embed = discord.Embed(title=title, description='\n'.join(result))
        await ctx.send(embed=embed)

    @commands.command(name="allbash", aliases=["offbash", "defbash", "supbash"])
    async def allbash(self, ctx, *, args):
        if not args.__contains__("/"):
            msg = "Du musst die beiden Spielernamen mit `/` trennen"
            return await ctx.send(msg)

        player1 = args.partition("/")[0].strip()
        player2 = args.partition("/")[2].strip()

        if player1.lower() == player2.lower():
            await ctx.send("Dein Witz :arrow_right: Unlustig")
            return

        s1 = await self.bot.fetch_both(ctx.server, player1)
        s2 = await self.bot.fetch_both(ctx.server, player2)

        if not s1 and not s2:
            msg = f"Auf der {ctx.world} gibt es weder einen Stamm noch " \
                  f"einen Spieler, der `{player1}` oder `{player2}` heißt"
            await ctx.send(msg)
            return

        elif not s1 or not s2:
            player = player1 if not s1 else player2
            msg = f"Auf der {ctx.world} gibt es einen Stamm oder Spieler " \
                  f"namens `{player}` nicht!"
            await ctx.send(msg)
            return

        keyword = self.translate[ctx.invoked_with.lower()]
        attribute = self.values[keyword]['value']

        values = {dsobj.id: 0 for dsobj in (s1, s2)}
        tribe_ids = [ds.id for ds in (s1, s2) if isinstance(ds, utils.Tribe)]
        if tribe_ids:
            member_cache = {tribe_id: [] for tribe_id in tribe_ids}
            members = await self.bot.fetch_tribe_member(ctx.server, tribe_ids)

            for member in members:
                member_cache[member.tribe_id].append(member)

            for tribe_id in member_cache:
                for member in member_cache[tribe_id]:
                    values[tribe_id] += member.sup_bash

        for dsobj in (s1, s2):
            if isinstance(dsobj, utils.Player):
                value = getattr(dsobj, attribute)
                values[dsobj.id] = value

        if values[s1.id] == values[s2.id]:
            arrow = ":left_right_arrow:"
        elif values[s1.id] > values[s2.id]:
            arrow = ":arrow_left:"
        else:
            arrow = ":arrow_right:"

        msg = f"`{seperator(values[s1.id])}` {arrow} `{seperator(values[s2.id])}`"
        await ctx.send(embed=discord.Embed(description=msg))

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

        if not 30 > time > 0:
            msg = "Das Maximum für den Recap Command sind 29 Tage"
            return await ctx.send(embed=error_embed(msg))
        try:
            dsobj8 = await self.bot.fetch_both(ctx.server, dsobj.id, name=False, archive=time)

            if dsobj8 is None:
                obj = "Spieler" if dsobj.alone else "Stamm"
                msg = f"Der {obj}: `{dsobj.name}` ist noch keine {time} Tage auf der Welt!"
                return await ctx.send(msg)

            point1, villages1, bash1 = dsobj.points, dsobj.villages, dsobj.all_bash
            point8, villages8, bash8 = dsobj8.points, dsobj8.villages, dsobj8.all_bash

        # upon database reset we use twstats as temporary workaround
        except asyncpg.UndefinedTableError:
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
                return await ctx.send(msg)

        p_done = seperator(int(point1) - int(point8))
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

        b_done = seperator(int(bash1) - int(bash8))
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
        key = self.attribute.get(state.lower())

        if key is None:
            msg = f"`{ctx.prefix}top <{'|'.join(self.attribute.keys())}>`"
            await ctx.send(embed=error_embed(msg, ctx))
            return

        res_link = self.base.format(ctx.world.url, key)
        async with self.bot.session.get(res_link) as r:
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

            players = await self.bot.fetch_bulk(ctx.server, datapack.keys(), dic=True)
            for player_id, points in datapack.items():
                player = players.get(player_id)
                if player:
                    result.append(f"`{points}` **|** {player.guest_mention}")

            msg = '\n'.join(result)
            embed = discord.Embed(title=cache.text, description=msg)

        except (AttributeError, TypeError):
            msg = "Aktuell liegen noch keine Daten vor"
            embed = discord.Embed(description=msg, color=discord.Color.red())

        await ctx.send(embed=embed)

    @commands.command(name="daily", aliases=["aktueller"])
    async def daily_(self, ctx, award_type):
        award = award_type.lower()
        award_data = self.values.get(award)

        if award_data is None:
            msg = f"`{ctx.prefix}daily <{'|'.join(self.values.keys())}>`"
            await ctx.send(embed=error_embed(msg, ctx))
            return

        tribe = ctx.invoked_with.lower() == "aktueller"
        dstype = utils.DSType(int(tribe))
        negative = award in ["verlierer"]

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
                    tribe_id = arguments.pop(0)
                    points = int(arguments[0])
                    if tribe_id != 0:
                        all_values[tribe_id].append(points)

                value_list = [(k, v) for k, v in all_values.items() if len(v) == 2]
                value_list.sort(key=lambda tup: tup[1][0] - tup[1][1], reverse=True)

                tribe_ids = [tup[0] for tup in value_list[:5]]
                tribes = await self.bot.fetch_bulk(ctx.server, tribe_ids,
                                                   table='tribe', dic=True)
                data = [tribes[idc] for idc in tribe_ids]

            else:
                base = 'SELECT * FROM {0} INNER JOIN {1} ON {0}.id = {1}.id ' \
                       'WHERE {0}.world = $1 AND {1}.world = $1 ' \
                       'ORDER BY ({0}.{2} - {1}.{2}) {3} LIMIT 5'

                switch = "ASC" if negative else "DESC"
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

            if negative:
                value = old_value - cur_value
            else:
                value = cur_value - old_value

            if value < 1:
                continue

            item = award_data['item']
            if value == 1 and item == "Dörfer":
                item = "Dorf"

            line = f"`{utils.seperator(value)} {item}` | {dsobj.guest_mention}"
            ranking.append(line)

        if ranking:
            description = "\n".join(ranking)
            title = f"{award.capitalize()} des Tages ({ctx.world.show(True)})"
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
