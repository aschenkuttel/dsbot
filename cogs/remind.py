from discord.ext import commands
import asyncio
import asyncpg


# id / author_id / channel_id / created / expire / reason


class Reminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._task = self.bot.loop.create_task()

    async def remind_loop(self):
        while not self.bot.is_closed():
            pass

    @commands.group(name="remind", aliases=["time"])
    async def remind(self, ctx, time, reason=None):

        pass

        # query = 'INSERT INTO reminders'
        # async with self.bot.ress.acquire() as conn:
        #     idc = await conn.execute(query)

    @remind.command(name="list")
    async def list_(self, ctx):

        query = 'SELECT * FROM reminders WHERE author_id = $1'
        async with self.bot.ress.acquire() as conn:
            data = await conn.execute(query, ctx.author.id)

        if not data:
            msg = "Du hast keine aktiven Reminder offen"
        else:
            pass

    @remind.command(name="remove", aliases=["delete"])
    async def remove_(self, ctx, number):
        pass


def setup(bot):
    bot.add_cog(Reminder(bot))

    # def check_time(self, input_time):
    #     if input_time.__contains__(":"):
    #         try:
    #             datetime.strptime(input_time, '%H:%M:%S')
    #             return True
    #
    #         except ValueError:
    #             try:
    #                 datetime.strptime(input_time, '%H:%M')
    #                 return True
    #             except ValueError:
    #                 return False
    #     options = {"hms", "hm", "hs", "ms", "h", "m", "s"}
    #     if re.sub(r'\d', '', input_time) in options:
    #         if len(input_time) > 9:
    #             return False
    #         return True
    #     else:
    #         return False

    # @commands.dm_only()
    # @commands.command(name="time", aliases=["eieruhr"])
    # async def time_(self, ctx, thyme: str, *reason: str):
    #     reason = ' '.join(reason)
    #
    #     # ----- Time Input Valid Check ----- #
    #     if not self.check_time(thyme):
    #         msg = "Benutze folgende Zeitangaben: " \
    #               "`!time 9h23m14s` oder `!time 18:45:24`"
    #         return await ctx.send(embed=utils.error_embed(msg))
    #     num = 0
    #
    #     # ----- Max Cap Check ----- #
    #     cap_num = self.cap_dict.get(ctx.author.id, 0)
    #     if cap_num >= 5:
    #         msg = "Du hast dein Limit erreicht - " \
    #               "Pro User nur maximal 5 aktive Timer!"
    #         return await ctx.author.send(embed=utils.error_embed(msg))
    #
    #     if thyme.__contains__(":"):
    #         thym = thyme.split(":")
    #         sec = int(thym[2]) if len(thym) == 3 else 0
    #         begin = datetime.now()
    #         end = begin.replace(hour=int(thym[0]),
    #                             minute=int(thym[1]),
    #                             second=sec)
    #         sec = (end - begin).total_seconds()
    #         if sec.__str__().startswith("-"):
    #             sec = 24 * 3600 - (-sec)
    #         num = int(sec)
    #
    #     if not thyme.__contains__(":"):
    #         thymes = re.findall(r'\d*\D+', thyme)
    #         for thy in thymes:
    #             if thy.endswith("h"):
    #                 hour = int(thy[:-1])
    #                 num += hour * 3600
    #             if thy.endswith("m"):
    #                 minute = int(thy[:-1])
    #                 num += minute * 60
    #             if thy.endswith("s"):
    #                 second = int(thy[:-1])
    #                 num += second
    #
    #     if num > 36000:
    #         return await ctx.send(
    #             "Du kannst dich maximal bis in 10 Stunden erinnern lassen!")
    #
    #     self.cap_dict.update({ctx.author.id: cap_num + 1})
    #     await ctx.message.add_reaction("⏰")
    #     await asyncio.sleep(num)
    #     reason = reason or "Du hast keinen Grund angegeben"
    #     await ctx.author.send(f"ERINNERUNG <@{ctx.author.id}> | `{reason}`")
    #     await ctx.message.remove_reaction("⏰", ctx.bot.user)
    #
    #     cur = self.cap_dict.get(ctx.author.id)
    #     if cur == 1:
    #         self.cap_dict.pop(ctx.author.id)
    #     else:
    #         self.cap_dict.update({ctx.author.id: cap_num - 1})
