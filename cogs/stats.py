from collections import OrderedDict
from utils import MissingRequiredKey
from utils import seperator as sep
from discord.ext import commands
from discord import app_commands
from matplotlib import ticker, patheffects
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
import pandas as pd
import asyncpg
import discord
import utils
import io


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
        self.bash_names = {'all_bash': "ALL",
                           'att_bash': "OFF",
                           'def_bash': "DEF",
                           'sup_bash': "SUP"}

    def create_figure(self):
        fig = plt.figure(figsize=(10, 4))
        plt.rc(f'xtick', labelsize=16)
        plt.rc(f'ytick', labelsize=18)

        axes = fig.add_axes([0.1, 0.1, 0.8, 0.8])
        plt.xticks([0, 7, 14, 21])
        axes.margins(x=0)

        for direction in ("bottom", "top", "left", "right"):
            axes.spines[direction].set_color('white')

        for coord in ("x", "y"):
            coord_axe = getattr(axes, f"{coord}axis")
            coord_axe.label.set_color('white')
            axes.tick_params(axis=coord, colors='white')

        def x_format(num, _):
            weeknum = int((28 - num) / 7)
            if weeknum not in (0, 4):
                return f"-{weeknum} Woche"

        def y_format(num, _):
            magnitude = 0
            while abs(num) >= 1000:
                magnitude += 1
                num /= 1000.0

            if magnitude == 0:
                return int(num)
            else:
                return '%.1f%s' % (num, ['', 'K', 'M'][magnitude])

        axes.yaxis.set_major_formatter(ticker.FuncFormatter(y_format))
        axes.xaxis.set_major_formatter(ticker.FuncFormatter(x_format))

        return axes

    @app_commands.command(name="bash", description="Bashpunkte oder ein Vergleich zwischen 2 Parteien")
    async def bash(self, interaction, first_dsobj: utils.DSConverter, second_dsobj: utils.DSConverter = None):
        if second_dsobj is None:
            user = [first_dsobj]
        else:
            user = [first_dsobj, second_dsobj]

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

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="bashrank", description="Bashrangliste eines Stammes")
    @app_commands.describe(tribe="Der gewünschte Stamm", bashtype="<general|offensive|defensive|support>")
    async def bashrank_(self, interaction, tribe: utils.DSConverter('tribe'), bashtype: str = "offensive"):
        bashtype = bashtype.lower()
        bashstat = self.bashtypes.get(bashtype)

        if bashstat is None:
            raise MissingRequiredKey(self.bashtypes.keys(), "tribe")

        members = await self.bot.fetch_tribe_member(interaction.server, tribe.id)
        members.sort(key=lambda m: getattr(m, bashstat), reverse=True)
        result = [f"**Stammesinterne Rangliste {tribe.mention}**",
                  f"**Bashtype:** `{bashtype.capitalize()}`", ""]

        for member in members[:15]:
            value = getattr(member, bashstat)
            line = f"`{utils.seperator(value)}` | {member}"
            result.append(line)

        embed = discord.Embed(description="\n".join(result))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="player", description="Statistiken eines Spielers")
    @app_commands.rename(player="name")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.guild_id)
    async def player(self, interaction, player: utils.DSConverter('player')):
        await self.ingame_stats(interaction, player, 'player')

    @app_commands.command(name="tribe", description="Statistiken eines Stammes")
    @app_commands.rename(tribe="name")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.guild_id)
    async def tribe(self, interaction, tribe: utils.DSConverter('tribe')):
        await self.ingame_stats(interaction, tribe, 'tribe')

    async def ingame_stats(self, interaction, dsobj, raw_ds_type):
        await interaction.response.defer()
        ds_type = utils.DSType(raw_ds_type)

        title = f"**{dsobj.name}** | {interaction.world.represent(True)} {interaction.world.icon}"
        rows = [title]

        urls = []
        for url_type in ("ingame", "guest", "twstats", "ds_ultimate"):
            if "_" in url_type:
                parts = url_type.split("_")
                name = f"{parts[0].upper()}-{parts[1].capitalize()}"
            else:
                name = url_type.capitalize()

            url = getattr(dsobj, f"{url_type}_url")
            urls.append(f"[{name}]({url})")

        rows.append(" | ".join(urls))

        if hasattr(dsobj, 'tribe_id'):
            tribe = await self.bot.fetch_tribe(interaction.server, dsobj.tribe_id)
            desc = tribe.mention if tribe else "None"
            villages = f"**Stamm:** {desc}"
        else:
            villages = f"**Mitglieder:** `{dsobj.member}`"

        villages += f" | **Dörfer:** `{utils.seperator(dsobj.villages)}`"
        points = f"**Punkte:** `{utils.seperator(dsobj.points)}` | **Rang:** `{dsobj.rank}`"
        rows.extend(["", points, villages, "", "**Besiegte Gegner:**"])

        bash_rows = OrderedDict()
        for index, stat in enumerate(['all_bash', 'att_bash', 'def_bash', 'sup_bash']):
            value = getattr(dsobj, stat)
            rank_stat = f"{stat.split('_')[0]}_rank"
            rank_value = getattr(dsobj, rank_stat)

            stat_title = self.bash_names[stat]
            represent = f"{stat_title}: `{sep(value)}`"

            if rank_value:
                represent += f" | Rang: `{rank_value}`"

            bash_rows[represent] = value

        clean = sorted(bash_rows.items(), key=lambda l: l[1], reverse=True)
        rows.extend([line[0] for line in clean])

        profile = discord.Embed(description="\n".join(rows))
        profile.colour = discord.Color.blue()

        image_url = await self.bot.fetch_profile_picture(dsobj)
        if image_url is not None:
            profile.set_thumbnail(url=image_url)

        queries = []
        for num in range(29):
            table = ds_type.table if not num else f"{ds_type.table}_{num}"
            base = f'SELECT * FROM {table} WHERE ' \
                   f'{table}.world = $1 AND {table}.id = $2'

            queries.append(base)

        query = ' UNION ALL '.join(queries)
        async with self.bot.tribal_pool.acquire() as conn:
            records = await conn.fetch(query, interaction.server, dsobj.id)
            data = [ds_type.Class(rec) for rec in records]
            data.reverse()

        filled = [0] * (29 - len(data)) + [d.points for d in data]
        plot_data = pd.DataFrame({'x_coord': range(29), 'y_coord': filled})

        config = {'color': '#3498db',
                  'linewidth': 5,
                  'path_effects': [patheffects.SimpleLineShadow(linewidth=8),
                                   patheffects.Normal()]}

        figure = self.create_figure()

        if not data:
            plt.ylim(top=50, bottom=-3)

        figure.plot('x_coord', 'y_coord', data=plot_data, **config)
        figure.grid(axis='y', zorder=1, alpha=0.3)

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, transparent=True)
        buf.seek(0)
        plt.close()

        file = discord.File(buf, "graph.png")
        profile.set_image(url="attachment://graph.png")
        await interaction.followup.send(embed=profile, file=file)

    @app_commands.command(name="recap", description="Fasst die letzten X Tage eines Spielers oder Stammes zusammen")
    @app_commands.describe(dsobj="Spieler oder Stamm", time="Dauer des Recaps in Tagen")
    @app_commands.checks.cooldown(1, 10, key=lambda i: (i.guild.id, i.user.id))
    async def recap(self, interaction, dsobj: utils.DSConverter, time: app_commands.Range[int, 1, 30] = 7):
        try:
            dsobj8 = await self.bot.fetch_both(interaction.server, dsobj.id, name=False, archive=time)

            if dsobj8 is None:
                obj = "Spieler" if dsobj.alone else "Stamm"
                msg = f"Der {obj}: `{dsobj.name}` ist noch keine {time} Tage auf der Welt!"
                await interaction.response.send_message(msg)
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
                await interaction.response.send_message(msg)
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
                result.append(f"`{value[1:]}` {interaction.lang.recap[index][0]}")
            else:
                result.append(f"`{value}` {interaction.lang.recap[index][1]}")

        since = "seit gestern" if time == 1 else f"in den letzten {time} Tagen"
        answer = f"`{dsobj.name}` hat {since} {' '.join(result)}"
        await interaction.response.send_message(answer)

    @app_commands.command(name="top", description="Erhalte unterschiedliche \"An einem Tag\" Ranglisten")
    @app_commands.describe(state="/help state")
    async def top_(self, interaction, state: str):
        key = interaction.lang.top_options.get(state.lower())

        if key is None:
            raise MissingRequiredKey(interaction.lang.top_options)

        url = self.in_a_day.format(interaction.world.url, key)
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

            players = await self.bot.fetch_bulk(interaction.server, datapack.keys(), dictionary=True)

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

        await interaction.followup.send(embed=embed)

    async def daily_award(self, interaction, award_type: str, tribe: bool = False):
        award = award_type.lower()

        if award not in interaction.lang.daily_options:
            raise MissingRequiredKey(interaction.lang.daily_options)

        dstype = utils.DSType('tribe' if tribe else 'player')
        # TODO optimize partitioned table fetch
        async with self.bot.tribal_pool.acquire() as conn:
            award_data = interaction.lang.daily_options.get(award)

            base = 'SELECT * FROM {0} INNER JOIN {1} ON {0}.id = {1}.id ' \
                   'WHERE {0}.world = $1 AND {1}.world = $1 ' \
                   'ORDER BY ({0}.{2} - {1}.{2}) {3} LIMIT 5'

            switch = "ASC" if award in ["loser"] else "DESC"
            args = [dstype.table, f"{dstype.table}_1",
                    award_data['value'], switch]

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
            data = await conn.fetch(query, interaction.server)

            ranking = []
            for record in data:
                records = utils.unpack_join(record)
                dsobj = dstype.Class(records[0])
                old_dsobj = dstype.Class(records[1])
                cur_value = getattr(dsobj, award_data['value'], 0)
                old_value = getattr(old_dsobj, award_data['value'], 0)

                if award in ("loser",):
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
                world_title = interaction.world.represent(plain=True)

                batch = [
                    f"**{award_data['title']} des Tages {world_title}**",
                    "\n".join(ranking)
                ]

                description = "\n\n".join(batch)
                embed = discord.Embed(description=description)
                footer = "Daten aufgrund von Inno nur stündlich aktualisiert"
                embed.colour = discord.Color.blue()
                embed.set_footer(text=footer)
            else:
                msg = "Aktuell liegen noch keine Daten vor"
                embed = discord.Embed(description=msg, color=discord.Color.red())

            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="daily", description="Tägliche Spielerawards")
    @app_commands.describe(award="Mehr unter /help award")
    async def daily(self, interaction, award: str):
        await self.daily_award(interaction, award)

    @app_commands.command(name="dailytribe", description="Tägliche Stammesawards")
    @app_commands.describe(award="Mehr unter /help award")
    async def dailytribe(self, interaction, award: str):
        await self.daily_award(interaction, award, True)


async def setup(bot):
    await bot.add_cog(Stats(bot))
