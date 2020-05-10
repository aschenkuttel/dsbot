from utils import DSConverter, DSUserNotFound, error_embed, pcv
from discord.ext import commands
from bs4 import BeautifulSoup
import discord
import utils


class Bash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.never = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.base = "https://{}.die-staemme.de/guest.php?village" \
                    "=null&screen=ranking&mode=in_a_day&type={}"
        self.keys = {'bash': "kill_att", 'def': "kill_def", 'ut': "kill_sup", 'farm': "loot_res",
                     'villages': "loot_vil", 'scavenge': "scavenge", 'conquer': "conquer"}
        self.values = {
            'defbash': {'value': "def_bash", 'item': "Bashpoints", 'title': "Verteidiger"},
            'offbash': {'value': "att_bash", 'item': "Bashpoints", 'title': "Angreifer"},
            'utbash': {'value': "ut_bash", 'item': "Bashpoints", 'title': "Unterstützer"},
            'allbash': {'value': "all_bash", 'item': "Bashpoints", 'title': "Kämpfer"},
            'verlierer': {'value': "villages", 'item': "Dörfer", 'title': "Verlierer"},
            'eroberer': {'value': "villages", 'item': "Dörfer", 'title': "Eroberer"}}

    @commands.command(name="bash")
    async def bash(self, ctx, *, user: DSConverter):
        title = f"Besiegte Gegner von {user.name}"
        result = [f"`OFF` | **{pcv(user.att_bash)} Bashpoints**",
                  f"`DEF` | **{pcv(user.def_bash)} Bashpoints**"]

        if user.alone:
            result.append(f"`UNT` | **{pcv(user.ut_bash)} Bashpoints**")

        result.append(f"`INS` | **{pcv(user.all_bash)} Bashpoints**")
        embed = discord.Embed(title=title, description='\n'.join(result))
        await ctx.send(embed=embed)

    @commands.command(name="allbash", aliases=["offbash", "defbash", "utbash"])
    async def allbash(self, ctx, *, args):
        if not args.__contains__("/"):
            msg = "Du musst die beiden Spielernamen mit `/` trennen"
            return await ctx.send(msg)

        player1 = args.partition("/")[0].strip()
        player2 = args.partition("/")[2].strip()

        if player1.lower() == player2.lower():
            await ctx.send("Dein Witz :arrow_right: Unlustig")

        else:

            s1 = await self.bot.fetch_both(ctx.server, player1)
            s2 = await self.bot.fetch_both(ctx.server, player2)

            if not s1 and not s2:
                msg = f"Auf der `{ctx.world}` gibt es weder einen Stamm noch " \
                      f"einen Spieler, der `{player1}` oder `{player2}` heißt"
                return await ctx.send(msg)

            if not s1 or not s2:
                player = player1 if not s1 else player2
                msg = f"Auf der `{ctx.world}` gibt es einen Stamm oder Spieler " \
                      f"namens `{player}` nicht!"
                return await ctx.send(msg)

            attribute = self.values[ctx.invoked_with.lower()]['value']
            data_one = getattr(s1, attribute)
            data_two = getattr(s2, attribute)
            if data_one == data_two:
                arrow = ":left_right_arrow:"
            elif data_one > data_two:
                arrow = ":arrow_left:"
            else:
                arrow = ":arrow_right:"
            msg = f"{pcv(data_one)} {arrow} {pcv(data_two)}"
            await ctx.send(embed=discord.Embed(description=msg))

    @commands.command(name="recap", aliases=["tagebuch"])
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

            point1 = dsobj.points
            point8 = dsobj8.points

            villages1 = dsobj.villages
            villages8 = dsobj8.villages

            bash1 = dsobj.all_bash
            bash8 = dsobj8.all_bash

        except Exception as error:
            if "relation" not in str(error):
                print(f"RECAP ERROR: {error}")

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

        p_done = pcv(int(point1) - int(point8))
        points_done = f"`{p_done}` Punkte gemacht,"
        if p_done.startswith("-"):
            points_done = f"`{p_done[1:]}` Punkte verloren,"

        v_done = int(villages1) - int(villages8)
        vil = "Dorf" if v_done == 1 or v_done == -1 else "Dörfer"
        villages_done = f"`{v_done}` {vil} geholt"
        if v_done < 0:
            villages_done = f"`{str(v_done)[1:]}` {vil} verschenkt"

        b_done = pcv(int(bash1) - int(bash8))
        bashpoints_done = f"sich `{b_done}` Bashpoints erkämpft"
        if b_done.startswith("-"):
            bashpoints_done = f"`{b_done[1:]}` Bashpoints verloren"

        has = "hat" if dsobj.alone else "haben"
        since = "seit gestern" if time == 1 else f"in den letzten {time} Tagen:"

        intro = f"`{dsobj.name}` {has} {since}"
        answer = f"{intro} {points_done} {villages_done} und {bashpoints_done}"
        await ctx.send(answer)

    @commands.group(name="tmp", aliases=["tmpalias"])
    async def tmp_(self, ctx, state):
        key = self.keys.get(state.lower())

        if key is None:
            cmd = self.bot.get_command("help daily")
            return await ctx.invoke(cmd)

        res_link = self.base.format(ctx.server, key)
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

    @commands.command(name="daily")
    async def daily_(self, ctx, award_type):
        award = award_type.lower()
        award_data = self.values.get(award)
        if award_data is None:
            return

        table = "player"
        negative = award in ["verlierer"]

        base = 'SELECT * FROM {0} INNER JOIN {1} ON {0}.id = {1}.id ' \
               'WHERE {0}.world = $1 AND {1}.world = $1 '

        if award == "utbash":
            base += 'ORDER BY {0}.all_bash - {0}.att_bash - {0}.def_bash - ' \
                    '{1}.all_bash - {1}.att_bash - {1}.def_bash {3} LIMIT 5'
        else:
            base += 'ORDER BY {0}.{2} - {1}.{2} {3} LIMIT 5'

        switch = "ASC" if negative else "DESC"
        query = base.format(table, f"{table}1", award_data['value'], switch)

        async with self.bot.pool.acquire() as conn:
            data = await conn.fetch(query, ctx.server)

        ranking = []
        for record in data:
            num = int(len(record) / 2)
            both_data = list(record.items())
            cur_record = {key: value for key, value in both_data[:num]}
            old_record = {key: value for key, value in both_data[num:]}

            old_dsobj, dsobj = utils.Player(old_record), utils.Player(cur_record)
            cur_value = getattr(dsobj, award_data['value'])
            old_value = getattr(old_dsobj, award_data['value'])

            if negative:
                value = old_value - cur_value
            else:
                value = cur_value - old_value

            if value > 0:
                line = f"`{value} {award_data['item']}` | {dsobj.guest_mention}"
                ranking.append(line)

        if ranking:
            description = "\n".join(ranking)
            title = f"{award_data['title']} des Tages"
            embed = discord.Embed(title=title, description=description)
            embed.colour = discord.Color.blue()

        else:
            msg = "Aktuell liegen noch keine Daten vor"
            embed = discord.Embed(description=msg, color=discord.Color.red())

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Bash(bot))
