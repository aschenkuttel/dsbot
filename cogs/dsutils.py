from matplotlib import patheffects, ticker
from collections import OrderedDict
from utils import seperator as sep
from discord.ext import commands
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import discord
import utils
import re
import io


class MemberMenue:
    def __init__(self, ctx, msg, pages, base):
        self.last = ctx.message.created_at
        self.owner = ctx.author
        self.bot = ctx.bot
        self.msg = msg
        self.pages = pages
        self.base = base
        self.emojis = []
        self.current = 0

    async def add_buttons(self):
        numbers = []
        for num in range(1, len(self.pages) + 1):
            button = f"{num}\N{COMBINING ENCLOSING KEYCAP}"
            numbers.append(button)

        self.emojis = ["⏪", *numbers, "⏩"]

        for emoji in self.emojis:
            await self.msg.add_reaction(emoji)

    async def update(self, reaction, user):
        now = datetime.utcnow()

        if self.owner is not None:
            if (now - self.last).total_seconds() > 10:
                self.owner = None

            elif user != self.owner:
                return

        if str(reaction.emoji) not in self.emojis:
            return

        self.last = now
        last_index = len(self.pages) - 1

        index = self.emojis.index(str(reaction.emoji))
        if index - 1 == self.current:
            return

        if index in [0, len(self.emojis) - 1]:
            direction = -1 if index == 0 else 1
            self.current += direction

            if self.current < 0:
                self.current = last_index

            elif self.current > last_index:
                self.current = 0

        else:
            self.current = index - 1

        embed = self.msg.embeds[0]
        embed.title = self.base.format(self.current + 1)
        page = self.pages[self.current]
        embed.description = "\n".join(page)

        await self.msg.edit(embed=embed)


class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.type = 1
        self.maximum = 0
        self.cap_dict = {}
        self.active_pager = {}
        self.base = "javascript: var settings = Array" \
                    "({0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}, {9}," \
                    " {10}, {11}, {12}, {13}, 'attack'); $.getScript" \
                    "('https://media.innogamescdn.com/com_DS_DE/" \
                    "scripts/qb_main/scriptgenerator.js'); void(0);"
        self.units = {'speer': "spear",
                      'schwert': "sword",
                      'axt': "axe",
                      'bogen': "archer",
                      'späher': "spy",
                      'lkav': "light",
                      'berittene': "marcher",
                      'skav': "heavy",
                      'ramme': "ram",
                      'katapult': "catapult",
                      'paladin': "knight",
                      'ag': "snob"}

        self.bash_names = {'all_bash': "ALL",
                           'att_bash': "OFF",
                           'def_bash': "DEF",
                           'sup_bash': "SUP"}

        self.same_scavenge_2 = (0.714285, 0.285714)
        self.same_scavenge_3 = (0.625, 0.25, 0.125)
        self.same_scavenge_4 = (0.5765, 0.231, 0.1155, 0.077)
        # self.best_scavenge_4 = (0.223, 0.244, 0.261, 0.272)
        # (((factor * loot) ** 2 * 100) ** 0.45 + 1800) * 0.8845033719

    async def called_per_hour(self):
        now = datetime.utcnow()
        tmp = self.active_pager.copy()
        for message_id, pager in tmp.items():
            if (now - pager.last).total_seconds() > 6:
                self.active_pager.pop(message_id)
                try:
                    await pager.msg.clear_reactions()
                except (discord.Forbidden, discord.NotFound):
                    pass

    # temporary fix
    async def fetch_oldest_tableday(self, conn):
        query = 'SELECT table_name FROM information_schema.tables ' \
                'WHERE table_schema=\'public\' AND table_type=\'BASE TABLE\' ' \
                'AND table_name LIKE \'player%\''

        cache = await conn.fetch(query)
        tables = " ".join([rec['table_name'] for rec in cache])
        numbers = [int(n) for n in re.findall(r'\d+', tables)]
        return sorted(numbers)[-1]

    async def fetch_profile_picture(self, dsobj, default_avatar=False):
        async with self.bot.session.get(dsobj.guest_url) as resp:
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

    def create_figure(self):
        fig = plt.figure(figsize=(10, 4))
        plt.rc(f'xtick', labelsize=16)
        plt.rc(f'ytick', labelsize=18)

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

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot or reaction.message.guild is None:
            return

        pager = self.active_pager.get(reaction.message.id)
        if pager is not None:
            await pager.update(reaction, user)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if user.bot or reaction.message.guild is None:
            return

        pager = self.active_pager.get(reaction.message.id)
        if pager is not None:
            await pager.update(reaction, user)

    @commands.command(name="members")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def members_(self, ctx, tribe: utils.DSConverter('tribe'), url_type="ingame"):
        members = await self.bot.fetch_tribe_member(ctx.server, tribe.id)
        sorted_members = sorted(members, key=lambda obj: obj.rank)

        if not sorted_members:
            msg = "Der angegebene Stamm hat keine Mitglieder"
            await ctx.send(msg)
            return

        elif url_type not in ["ingame", "guest", "twstats"]:
            msg = "Der angegebene Url Typ ist nicht vorhanden:\n" \
                  "`(ingame[default], guest, twstats)`"
            await ctx.send(msg)
            return

        tribe_url = getattr(tribe, f"{url_type}_url")

        if url_type == "ingame":
            url_type = "mention"
        else:
            url_type += "_mention"

        pages = [[]]
        for index, member in enumerate(sorted_members, 1):
            number = f"0{index}" if index < 10 else index
            line = f"`{number}` | {getattr(member, url_type)}"

            if len(pages[-1]) == 15:
                pages.append([line])
            else:
                pages[-1].append(line)

        placeholder = "{}"
        base = f"Member von {tribe.tag} ({placeholder}/{len(pages)})"
        embed = discord.Embed(title=base.format(1), url=tribe_url)
        embed.description = "\n".join(pages[0])

        msg = await ctx.send(embed=embed)

        pager = MemberMenue(ctx, msg, pages, base)
        self.active_pager[msg.id] = pager
        await pager.add_buttons()

    @commands.command(name="circular", aliases=["rm"])
    async def rundmail_(self, ctx, *tribes: str):
        if not tribes:
            raise utils.MissingRequiredArgument()

        if len(tribes) > 10:
            msg = "Nur bis zu `10 Stämme` aufgrund der maximalen Zeichenlänge"
            await ctx.send(msg)
            return

        data = await self.bot.fetch_tribe_member(ctx.server, tribes, name=True)
        if not data:
            await ctx.send("Die angegebenen Stämme haben keine Mitglieder")

        else:
            result = [obj.name for obj in data]
            await ctx.author.send(';'.join(result))
            await ctx.message.add_reaction("📨")

    @commands.command(name="player", aliases=["tribe"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def ingame_(self, ctx, *, username):
        ds_type = utils.DSType(ctx.invoked_with.lower())
        dsobj = await ds_type.fetch(ctx, username, name=True)

        queries = []
        for num in range(29):
            table = f"{ds_type.table}{num or ''}"
            base = f'SELECT * FROM {table} WHERE ' \
                   f'{table}.world = $1 AND {table}.id = $2'

            queries.append(base)

        query = " UNION ALL ".join(queries)
        async with self.bot.pool.acquire() as conn:
            records = await conn.fetch(query, ctx.server, dsobj.id)
            data = [ds_type.Class(rec) for rec in records]
            data.reverse()

        rows = [f"**{dsobj.name}** | {ctx.world.represent(True)} {ctx.world.icon}"]

        urls = []
        for url_type in ["ingame", "guest", "twstats", "ds_ultimate"]:
            if "_" in url_type:
                parts = url_type.split("_")
                name = f"{parts[0].upper()}-{parts[1].capitalize()}"
            else:
                name = url_type.capitalize()

            url = getattr(dsobj, f"{url_type}_url")
            urls.append(f"[{name}]({url})")

        rows.append(" | ".join(urls))

        if hasattr(dsobj, 'tribe_id'):
            tribe = await self.bot.fetch_tribe(ctx.server, dsobj.tribe_id)
            desc = tribe.mention if tribe else "None"
            villages = f"**Stamm:** {desc}"
        else:
            villages = f"**Mitglieder:** `{dsobj.member}`"

        villages += f" | **Dörfer:** `{utils.seperator(dsobj.villages)}`"
        points = f"**Punkte:** `{utils.seperator(dsobj.points)}` | **Rang:** `{dsobj.rank}`"
        rows.extend(["", points, villages, "", "**Besiegte Gegner:**"])

        bash_rows = OrderedDict()
        for index, stat in enumerate(['all_bash', 'att_bash', 'def_bash', 'sup_bash']):

            if index == 3 and isinstance(dsobj, utils.Tribe):
                value = await dsobj.fetch_supbash(ctx)
                rank_value = None
            else:
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

        image_url = await self.fetch_profile_picture(dsobj)
        if image_url is not None:
            profile.set_thumbnail(url=image_url)

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

        file = discord.File(buf, "example.png")
        profile.set_image(url="attachment://example.png")
        await ctx.send(embed=profile, file=file)

    @commands.command(name="nude")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def nude_(self, ctx, *, dsobj: utils.DSConverter = None):
        await ctx.trigger_typing()

        if dsobj is None:
            players = await self.bot.fetch_random(ctx.server, amount=30, max=True)
        else:
            players = [dsobj]

        for player in players:
            result = await self.fetch_profile_picture(player, bool(dsobj))

            if result is not None:
                break

        else:
            if dsobj:
                msg = f"Glaub mir, die Nudes von `{dsobj.name}` willst du nicht!"
            else:
                msg = "Die maximale Anzahl von Versuchen wurden erreicht"

            await ctx.send(msg)
            return

        async with self.bot.session.get(result) as res2:
            image = io.BytesIO(await res2.read())
            file = discord.File(image, "userpic.gif")
            await ctx.send(file=file)

    @commands.command(name="visit")
    async def visit_(self, ctx, world: utils.WorldConverter = None):
        if world is None:
            world = ctx.world

        description = f"[{world.represent(True)}]({world.guest_url})"
        await ctx.send(embed=discord.Embed(description=description))

    @commands.command(name="quickbar", aliases=["sl"])
    async def quickbar_(self, ctx, *, args):
        troops = re.findall(r'[A-z]*=\d*', args)
        coordinates = re.findall(r'\d\d\d\|\d\d\d', args)

        if not troops or not coordinates:
            msg = f"Du musst mindestens eine Truppe und ein Dorf angeben\n" \
                  f"**Erklärung und Beispiele unter:** {ctx.prefix}help sl"
            await ctx.send(msg)
            return

        wiki = list(self.units)
        data = [0 for _ in range(12)]
        for kwarg in troops:
            name, amount = kwarg.split("=")
            try:
                index = wiki.index(name.lower())
                data[index] = int(amount)
            except ValueError:
                continue

        if not sum(data):
            troops = ', '.join([o.capitalize() for o in wiki])
            msg = f"Du musst einen gültigen Truppennamen angeben:\n`{troops}`"
            await ctx.send(msg)
            return

        result = []
        counter = 0
        package = []
        iteratable = set(coordinates)
        for index, coord in enumerate(iteratable):
            x, y = coord.split("|")
            script = self.base.format(*data, x, y)

            if counter + len(script) > 2000 or index == len(iteratable) - 1:
                result.append(package)
            else:
                package.append(script)
                counter += len(script)

        for package in result:
            msg = "\n".join(package)
            await ctx.author.send(f"```js\n{msg}\n```")

        if ctx.guild is not None:
            await ctx.private_hint()

    @commands.command(name="scavenge", aliases=["rz", "rz2", "rz3", "rz4"])
    async def scavenge_(self, ctx, *args: int):
        if not args:
            raise utils.MissingRequiredArgument()

        last = ctx.invoked_with[-1]
        if last.isdigit():
            factors = getattr(self, f"same_scavenge_{last}")
        else:
            factors = getattr(self, "same_scavenge_4")

        scavenge_batches = ([], [], [], [])

        for troop_amount in args[:10]:
            for index, appendix in enumerate(factors):
                troops = str(round(appendix * troop_amount))
                scavenge_batches[index].append(troops)

        result = []
        for index, troops in enumerate(scavenge_batches, start=1):
            if troops:
                troop_str = ", ".join(troops)
                result.append(f"`Raubzug {index}:` **[{troop_str}]**")

        embed = discord.Embed(description="\n".join(result))
        await ctx.send(embed=embed)

    @commands.command(name="settings")
    async def settings_(self, ctx, world: utils.WorldConverter = None):
        world = world or ctx.world
        title = f"Settings der {world.represent(clean=True)} {world.icon}"
        embed = discord.Embed(title=title, url=world.settings_url)

        cache = []
        for key, data in ctx.lang.settings.items():
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


def setup(bot):
    bot.add_cog(Utils(bot))
