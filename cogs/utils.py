from utils import error_embed, DSColor
from datetime import datetime
from discord.ext import commands
from load import load
import discord
import asyncio
import typing
import math
import re


class Rm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.duration = 300
        self.cap_dict = {}
        self.color = load.colors
        self.number = "{}\N{COMBINING ENCLOSING KEYCAP}"
        # self.numbers = {1: "", 2: ":two:", 3: ":three:",
        #                 4: ":four:", 5: ":five:", 6: ":six:"}
        self.troops = ["speer", "schwert", "axt", "bogen", "späher", "lkav", "berittene",
                       "skav", "ramme", "katapult", "paladin", "ag"]
        self.base = "javascript: var settings = Array" \
                    "({0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}, {9}," \
                    " {10}, {11}, {12}, {13}, 'attack'); $.getScript" \
                    "('https://media.innogamescdn.com/com_DS_DE/" \
                    "scripts/qb_main/scriptgenerator.js'); void(0);"

    @commands.command(aliases=["rundmail"])
    async def rm(self, ctx, *tribes: str):

        if len(tribes) > 10:
            msg = "Der RM Command unterstützt aktuell nur " \
                  "maximal `10 Stämme` per Command"
            return await ctx.send(msg)

        data = await load.fetch_tribe_member(ctx.world, tribes, True)
        if isinstance(data, str):
            return await ctx.send(f"Der Stamm `{data}` existiert so nicht")
        result = [obj.name for obj in data]
        await ctx.author.send(f"```\n{';'.join(result)}\n```")
        await ctx.message.add_reaction("📨")

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
                index = self.troops.index(name.lower())
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

    @commands.command(name="rz3", aliases=["rz4"])
    async def rz3_(self, ctx, *args: int):
        if len(args) > 7:
            msg = "Das Maximum von 7 verschiedenen Truppentypen wurde überschritten"
            await ctx.send(embed=error_embed(msg))
            return

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

    def check_time(self, input_time):
        if input_time.__contains__(":"):
            try:
                datetime.strptime(input_time, '%H:%M:%S')
                return True

            except ValueError:
                try:
                    datetime.strptime(input_time, '%H:%M')
                    return True
                except ValueError:
                    return False
        options = {"hms", "hm", "hs", "ms", "h", "m", "s"}
        if re.sub(r'\d', '', input_time) in options:
            if len(input_time) > 9:
                return False
            return True
        else:
            return False

    @commands.dm_only()
    @commands.command(name="time", aliases=["eieruhr"])
    async def time_(self, ctx, thyme: str, *reason: str):
        reason = ' '.join(reason)

        # ----- Time Input Valid Check ----- #
        if not self.check_time(thyme):
            msg = "Benutze folgende Zeitangaben: " \
                  "`!time 9h23m14s` oder `!time 18:45:24`"
            return await ctx.send(embed=error_embed(msg))
        num = 0

        # ----- Max Cap Check ----- #
        cap_num = self.cap_dict.get(ctx.author.id, 0)
        if cap_num >= 5:
            msg = "Du hast dein Limit erreicht - " \
                  "Pro User nur maximal 5 aktive Timer!"
            return await ctx.author.send(embed=error_embed(msg))

        if thyme.__contains__(":"):
            thym = thyme.split(":")
            sec = int(thym[2]) if len(thym) == 3 else 0
            begin = datetime.now()
            end = begin.replace(hour=int(thym[0]),
                                minute=int(thym[1]),
                                second=sec)
            sec = (end - begin).total_seconds()
            if sec.__str__().startswith("-"):
                sec = 24 * 3600 - (-sec)
            num = int(sec)

        if not thyme.__contains__(":"):
            thymes = re.findall(r'\d*\D+', thyme)
            for thy in thymes:
                if thy.endswith("h"):
                    hour = int(thy[:-1])
                    num += hour * 3600
                if thy.endswith("m"):
                    minute = int(thy[:-1])
                    num += minute * 60
                if thy.endswith("s"):
                    second = int(thy[:-1])
                    num += second

        if num > 36000:
            return await ctx.send(
                "Du kannst dich maximal bis in 10 Stunden erinnern lassen!")

        self.cap_dict.update({ctx.author.id: cap_num + 1})
        await ctx.message.add_reaction("⏰")
        await asyncio.sleep(num)
        reason = reason or "Du hast keinen Grund angegeben"
        await ctx.author.send(f"ERINNERUNG <@{ctx.author.id}> | `{reason}`")
        await ctx.message.remove_reaction("⏰", ctx.bot.user)

        cur = self.cap_dict.get(ctx.author.id)
        if cur == 1:
            self.cap_dict.pop(ctx.author.id)
        else:
            self.cap_dict.update({ctx.author.id: cap_num - 1})

    @commands.command(name="poll", aliases=["abstimmung"])
    async def poll_(self, ctx, question, *options):

        if len(options) > 9:
            msg = "Die maximale Anzahl der Auswahlmöglichkeiten beträgt 9"
            return await ctx.send(error_embed(msg))

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

    @rz3_.error
    async def rz3_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            msg = "Truppenangaben dürfen nur aus Zahlen bestehen"
            await ctx.send(embed=error_embed(msg))


def setup(bot):
    bot.add_cog(Rm(bot))
