from utils import error_embed, private_message_only
from discord.ext import commands
import datetime
import asyncio
import time
import re


class Time(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cap_dict = {}

    def max_time(self, thy):
        if thy.endswith("h"):
            return int(thy[:-1]) > 9
        if thy.endswith("m"):
            return int(thy[:-1]) > 59
        if thy.endswith("s"):
            return int(thy[:-1]) > 59

    def check_time(self, input_time):
        if input_time.__contains__(":"):
            try:
                time.strptime(input_time, '%H:%M:%S')
                return True

            except ValueError:
                try:
                    time.strptime(input_time, '%H:%M')
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

    @private_message_only()
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
        try:
            cap_num = self.cap_dict[ctx.author.id]
            if self.cap_dict[ctx.author.id] >= 5:
                msg = "Du hast dein Limit erreicht - " \
                      "Pro User nur maximal 5 aktive Timer!"
                return await ctx.author.send(embed=error_embed(msg))
        except KeyError:
            cap_num = 0
            pass

        if thyme.__contains__(":"):
            thym = thyme.split(":")
            sec = 0
            if len(thym) is 3:
                sec = int(thym[2])
            act = datetime.datetime.now().replace(hour=int(thym[0]),
                                                  minute=int(thym[1]),
                                                  second=sec)
            rn = datetime.datetime.now()
            sec = (act - rn).total_seconds()
            if sec.__str__().startswith("-"):
                sec = 24 * 3600 - (-sec)
            if int(sec) > 36000:
                msg = "Du kannst dich maximal bis in 10h erinnern lassen."
                return await ctx.send(msg)
            else:
                num = int(sec)

        if not thyme.__contains__(":"):
            thymes = re.findall('\d*\D+', thyme)
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
        cap_num += 1
        self.cap_dict.update({ctx.author.id: cap_num})
        await ctx.message.add_reaction("⏰")
        await asyncio.sleep(num)
        if not reason:
            reason = "Du hast keinen Grund angegeben."
        await ctx.author.send(f"ERINNERUNG <@{ctx.author.id}> | `{reason}`")
        await ctx.message.remove_reaction("⏰", ctx.bot.user)

        cap_num -= 1
        if cap_num == 0:
            return self.cap_dict.pop(ctx.author.id, None)
        self.cap_dict.update({ctx.author.id: cap_num})

    @time_.error
    async def time_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            msg = f"Die gewünschte Uhrzeit/Dauer fehlt."
            await ctx.send(embed=error_embed(msg))


def setup(bot):
    bot.add_cog(Time(bot))
