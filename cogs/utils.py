from utils import seperator as sep
from matplotlib import patheffects
from discord.ext import commands
import matplotlib.pyplot as plt
from matplotlib import ticker
from bs4 import BeautifulSoup
from datetime import datetime
import parsedatetime
import pandas as pd
import discord
import asyncio
import utils
import math
import re
import io


class Rm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.maximum = 0
        self.duration = 300
        self.cap_dict = {}
        self.troops = self.bot.msg['troops']
        self.movement = self.bot.msg['movement']
        self.number = "{}\N{COMBINING ENCLOSING KEYCAP}"
        self.base = "javascript: var settings = Array" \
                    "({0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}, {9}," \
                    " {10}, {11}, {12}, {13}, 'attack'); $.getScript" \
                    "('https://media.innogamescdn.com/com_DS_DE/" \
                    "scripts/qb_main/scriptgenerator.js'); void(0);"

    # temporary fix
    async def fetch_oldest_tableday(self, conn):
        query = 'SELECT table_name FROM information_schema.tables ' \
                'WHERE table_schema=\'public\' AND table_type=\'BASE TABLE\' ' \
                'AND table_name LIKE \'player%\''

        cache = await conn.fetch(query)
        tables = [rec['table_name'] for rec in cache]
        return int(sorted(tables)[-1][-1])

    def create_figure(self):
        fig = plt.figure(figsize=(10, 4))
        plt.rc(f'xtick', labelsize=16)
        plt.rc(f'ytick', labelsize=18)

        # plt.locator_params(axis='x', nbins=4)

        axes = fig.add_axes([0.1, 0.1, 0.8, 0.8])
        plt.xticks([0, 7, 14, 21])
        axes.margins(x=0)

        for direction in ["bottom", "top", "left", "right"]:
            axes.spines[direction].set_color('white')

        for coord in ["x", "y"]:
            coord_axe = getattr(axes, f"{coord}axis")
            coord_axe.label.set_color('white')
            axes.tick_params(axis=coord, colors='white')

        def x_format(num, _):
            return f"-{int((28 - num) / 7)} Woche"

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

    @commands.command(name="rm")
    async def rm_(self, ctx, *tribes: str):
        if len(tribes) > 10:
            msg = "Nur bis zu `10 Stämme` aufgrund der maximalen Zeichenlänge"
            return await ctx.send(msg)

        data = await self.bot.fetch_tribe_member(ctx.server, tribes, name=True)
        if isinstance(data, str):
            return await ctx.send(f"Der Stamm `{data}` existiert so nicht")

        result = [obj.name for obj in data]
        await ctx.author.send(';'.join(result))
        await ctx.message.add_reaction("📨")

    @commands.command(name="twstats")
    async def akte_(self, ctx, *, user: utils.DSConverter):
        akte = discord.Embed(title=user.name, url=user.twstats_url)
        await ctx.send(embed=akte)

    @commands.command(name="player", aliases=["tribe"])
    async def ingame_(self, ctx, *, username):
        ds_type = utils.DSType(ctx.invoked_with.lower())

        async with self.bot.pool.acquire() as conn:
            latest = await self.fetch_oldest_tableday(conn)

            queries = []
            for num in range(0, latest + 1):
                placeholder = '{0}'
                num = num or ''
                base = f'SELECT * FROM {placeholder}{num} WHERE ' \
                       f'{placeholder}{num}.world = $1 AND '

                if ds_type.table == "player":
                    base += f'LOWER({placeholder}{num}.name) = $2'
                else:
                    base += f'(LOWER({placeholder}{num}.tag) = $2 OR ' \
                            f'LOWER({placeholder}{num}.name) = $2)'

                queries.append(base)

        query = " UNION ALL ".join(queries).format(ds_type.table)

        async with self.bot.pool.acquire() as conn:
            searchable = utils.converter(username, True)
            cache = await conn.fetch(query, ctx.server, searchable)
            data = [ds_type.Class(rec) for rec in cache]

        if not data:
            raise utils.DSUserNotFound(username)
        else:
            dsobj = data[0]

        rows = [f"**{dsobj.name}** | {ctx.world.show(clean=True)} {ctx.world.icon}"]

        urls = []
        for url_type in ["ingame", "guest", "twstats"]:
            url = getattr(dsobj, f"{url_type}_url")
            urls.append(f"[{url_type.capitalize()}]({url})")

        rows.append(" | ".join(urls))

        points = f"**Punkte:** `{utils.seperator(dsobj.points)}` | **Rang:** `{dsobj.rank}`"
        villages = f"**Dörfer:** `{utils.seperator(dsobj.villages)}`"

        if getattr(dsobj, 'tribe_id', None):
            tribe = await self.bot.fetch_tribe(ctx.server, dsobj.tribe_id)
            desc = tribe.mention if tribe else "Stammeslos"
            villages += f" | **Stamm:** {desc}"

        rows.extend(["", points, villages, "", "**Besiegte Gegner:**"])

        bash_rows = {}
        for index, stat in enumerate(['all_bash', 'att_bash', 'def_bash', 'sup_bash']):
            value = getattr(dsobj, stat, None)
            if value is not None:
                rank_stat = f"{stat.split('_')[0]}_rank"
                rank_value = getattr(dsobj, rank_stat)
                stat_title = self.bot.msg['statTitle'][stat]
                represent = f"{stat_title}: `{sep(value)}`"

                if rank_value:
                    represent += f" | Rang: `{rank_value}`"

                bash_rows[value] = represent

        clean = sorted(bash_rows.items(), key=lambda l: l[0], reverse=True)
        rows.extend([line[1] for line in clean])

        profile = discord.Embed(description="\n".join(rows))
        profile.colour = discord.Color.blue()

        async with self.bot.session.get(dsobj.guest_url) as resp:
            soup = BeautifulSoup(await resp.read(), "html.parser")

            tbody = soup.find(id='content_value')
            tables = tbody.findAll('table')
            tds = tables[1].findAll('td', attrs={'valign': 'top'})
            images = tds[1].findAll('img')

            if images and images[0]['src'].endswith(("large", "jpg")):
                profile.set_thumbnail(url=images[0]['src'])

        filled = [0] * (28 - len(data)) + [d.points for d in data[::-1]]
        plot_data = pd.DataFrame({'x_coord': range(1, 29), 'y_coord': filled})

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

        file = discord.File(buf, "example.png")
        profile.set_image(url="attachment://example.png")

        await ctx.send(embed=profile, file=file)

    @commands.command(name="guest")
    async def guest_(self, ctx, *, user: utils.DSConverter):
        guest = discord.Embed(title=user.name, url=user.guest_url)
        await ctx.send(embed=guest)

    @commands.command(name="visit")
    async def visit_(self, ctx, world: utils.WorldConverter = None):
        if world is None:
            world = ctx.world

        description = f"[{world.show(True)}]({world.guest_url})"
        await ctx.send(embed=discord.Embed(description=description))

    @commands.command(name="sl")
    async def sl_(self, ctx, *, args):
        troops = re.findall(r'[A-z]*=\d*', args)
        coordinates = re.findall(r'\d\d\d\|\d\d\d', args)

        if not troops or not coordinates:
            msg = f"Du musst mindestens eine Truppe und ein Dorf angeben\n" \
                  f"**Erklärung und Beispiele unter:** {ctx.prefix}help sl"
            return await ctx.send(msg)

        data = [0 for _ in range(12)]
        for kwarg in troops:
            name, amount = kwarg.split("=")
            try:
                wiki = list(self.troops.keys())
                index = wiki.index(name.lower())
            except ValueError:
                continue
            data[index] = int(amount)

        if not sum(data):
            troops = ', '.join([o.capitalize() for o in self.troops])
            msg = f"Du musst einen gültigen Truppennamen angeben:\n`{troops}`"
            return await ctx.send(msg)

        result = []
        counter = 0
        cache = []
        for coord in coordinates:
            if coord in cache:
                continue
            cache.append(coord)
            x, y = coord.split("|")
            script = self.base.format(*data, x, y)
            if counter + len(script) > 2000:
                msg = "\n".join(result)
                await ctx.author.send(f"```js\n{msg}\n```")
            else:
                result.append(script)
                counter += len(script)

        if result:
            msg = "\n".join(result)
            await ctx.author.send(f"```js\n{msg}\n```")

        if ctx.guild:
            await ctx.private_hint()

    @commands.command(name="rz", aliases=["rz3", "rz4"])
    async def rz3_(self, ctx, *args: int):
        if len(args) > 7:
            msg = "Das Maximum von 7 verschiedenen Truppentypen wurde überschritten"
            return await ctx.send(embed=utils.error_embed(msg))

        three = ctx.invoked_with.lower() == "rz3"

        sca1, sca2, sca3, sca4 = [], [], [], []
        if three:
            for element in args:
                sca1.append(str(math.floor((5 / 8) * element)))
                sca2.append(str(math.floor((2 / 8) * element)))
                sca3.append(str(math.floor((1 / 8) * element)))
        else:
            for element in args:
                sca1.append(str(math.floor(0.5765 * element)))
                sca2.append(str(math.floor(0.23 * element)))
                sca3.append(str(math.floor(0.1155 * element)))
                sca4.append(str(math.floor(0.077 * element)))

        cache = []
        for index, ele in enumerate([sca1, sca2, sca3, sca4]):
            cache.append(f"**Raubzug {index + 1}:** `[{', '.join(ele)}]`")
        em = discord.Embed(description='\n'.join(cache))
        await ctx.send(embed=em)

    @commands.command(name="retime")
    async def retime_(self, ctx, *, inc):
        coords = re.findall(r'\d{3}\|\d{3}', inc)
        datestring = re.findall(r'\d{2}:\d{2}:\d{2}:\d{3}', inc)

        if not datestring or len(coords) != 2:
            msg = "**Ungültiger Input** - Gesamte Angriffszeile kopieren:\n" \
                  "`?retime Ramme Dorf (335|490) K43 Dorf (338|489) K43 " \
                  "Knueppel-Kutte 3.2 heute um 21:09:56:099`"
            return await ctx.send(msg)

        now = datetime.now()
        calendar = parsedatetime.Calendar()
        date, status = calendar.parseDT(datestring[0])

        if now > date:
            date = date.replace(day=now.day + 1)

        args = inc.split()

        value = args[0].lower()
        unit = self.troops.get(value)

        if unit is None:
            value = args[-1].lower()
            unit = self.troops.get(value, value)

            if unit not in self.movement:
                unit = 'ram'

        unit_speed = self.movement.get(unit)

        origin, target = coords
        target = list(map(int, f"{origin}|{target}".split("|")))
        x, y = abs(target[0] - target[2]), abs(target[1] - target[3])

        diff = (x * x + y * y) ** 0.5
        raw_seconds = diff * unit_speed * ctx.world.speed
        seconds = round(raw_seconds * 60)

        target_date = datetime.fromtimestamp(date.timestamp() + seconds)
        time = target_date.strftime('%H:%M:%S')
        msg = f"**Rückkehr:** {time}:000 `[{value.upper()}]`"
        await ctx.send(msg)

    @commands.command(name="settings")
    async def settings_(self, ctx, world: utils.WorldConverter = None):
        world = world or ctx.world
        title = f"Settings der {world.show(clean=True)} {world.icon}"
        embed = discord.Embed(title=title, url=world.settings_url)

        cache = []
        for key, data in self.bot.msg['settings'].items():
            parent, title, description = data.values()
            value = None
            if "|" in key:
                keys = key.split("|")[::-1]
                raw_value = [f"{world.config[parent][k]}:00" for k in keys]
                value = description.format(*raw_value)
            elif parent:
                raw_value = world.config[parent][key]
                if key == "fake_limit":
                    index = 1 if int(raw_value) else 0
                    value = description[index].format(raw_value)
                elif description:
                    try:
                        value = description[int(raw_value)]
                    except IndexError:
                        pass

            else:
                raw_value = getattr(world, key, None)
                if str(raw_value)[-1] == "0":
                    value = int(raw_value)
                elif key == "moral":
                    value = description[int(raw_value)]
                else:
                    value = round(float(raw_value), 3)

            cache.append(f"**{title}:** {value or raw_value}")

        embed.description = "\n".join(cache)
        await ctx.send(embed=embed)

    @commands.command(name="poll")
    async def poll_(self, ctx, question, *options):
        if len(options) > 9:
            msg = "Die maximale Anzahl der Auswahlmöglichkeiten beträgt 9"
            return await ctx.send(utils.error_embed(msg))

        parsed_options = ""
        for index, opt in enumerate(options):
            choice = f"\n`{index + 1}.` {opt}"
            parsed_options += choice

        title = f"**Abstimmung von {ctx.author.display_name}:**"
        description = f"{title}\n{question}{parsed_options}"
        embed = discord.Embed(description=description, color=discord.Color.purple())
        embed.set_footer(text="Abstimmung endet in 15 Minuten")
        poll = await ctx.send(embed=embed)

        for num in range(len(options)):
            emoji = self.number.format(num + 1)
            await poll.add_reaction(emoji)

        await ctx.safe_delete()
        await asyncio.sleep(self.duration)

        for time in [2, 1]:
            cur = int(self.duration / 60) * time
            embed.set_footer(text=f"Abstimmung endet in {cur} Minuten")
            await poll.edit(embed=embed)
            await asyncio.sleep(self.duration)

        refetched = await ctx.channel.fetch_message(poll.id)
        votes = sorted(refetched.reactions, key=lambda r: r.count, reverse=True)
        color = discord.Color.red()

        if [r.count for r in votes].count(1) == len(votes):
            msg = "`Niemand hat an der Abstimmung teilgenommen`"

        elif votes[0].count > votes[1].count:
            color = discord.Color.green()
            winner = refetched.reactions.index(votes[0])
            msg = f"`{options[winner]} hat gewonnen`"

        else:
            msg = "`Es konnte kein klares Ergebnis erzielt werden`"

        result = f"{title}\n{question}\n{msg}"
        wimbed = discord.Embed(description=result, color=color)
        wimbed.set_footer(text="Abstimmung beendet")
        await poll.edit(embed=wimbed)


def setup(bot):
    bot.add_cog(Rm(bot))
