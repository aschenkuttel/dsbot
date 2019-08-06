from load import load
from utils import game_channel_only
from discord.ext import commands
import datetime
import asyncio
import random


class Anagram(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = {}

    def get_word(self, guild_id, solution=False):
        if solution:
            return self.data[guild_id]["win"]
        else:
            return self.data[guild_id]["word"]

    @commands.command(name="anagram", aliases=["ag"])
    @game_channel_only()
    async def anagram_(self, ctx):

        game_data = self.data.get(ctx.guild.id)
        if game_data is False:
            return
        if game_data:
            ag_time = self.data[ctx.guild.id]["time"]
            now = (datetime.datetime.now() - ag_time).seconds
            hint = self.data[ctx.guild.id].get('hint')
            comment = f"| `{hint}` " if hint else ""
            msg = f"`{self.get_word(ctx.guild.id)}` {comment}*(noch {60 - now}s)*"
            return await ctx.send(msg)

        word = None
        while not word:
            cache = random.choice(load.msg["hangman"])
            if len(cache.split()) == 1:
                word = cache.strip()

        word_list = list(word)
        while ''.join(word_list) == word:
            random.shuffle(word_list)

        show = ' '.join(word_list).upper()
        start_time = datetime.datetime.now()
        hint_list = list(word[:int(len(word) / 4)].upper())
        hint = f"{' '.join(hint_list)} . . ."
        data = {"word": show, "win": word, "time": start_time}
        self.data[ctx.guild.id] = data
        start_msg = await ctx.send(f"`{show}` *(60s Timeout)*")

        def check(m):
            if m.channel == start_msg.channel:
                result = self.get_word(m.guild.id, True)
                if result.lower() == m.content.lower():
                    return True

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError:
            try:
                self.data[ctx.guild.id]["hint"] = hint
                stuff = f"`{show}` | `{hint}`"
                await start_msg.edit(content=f"{stuff}(noch 30s)")
                msg = await self.bot.wait_for('message', check=check, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send(f"Die Zeit ist abgelaufen: `{word}`")
                self.data.pop(ctx.guild.id)
                return

        end_time = datetime.datetime.now()
        fin_time = str((end_time - start_time).total_seconds()).split(".")
        fin_time = f"{fin_time[0]}.{fin_time[1][0]}"
        amount_won = int(250*(len(word)) * (1 - float(fin_time) / 60 + 1))
        await msg.channel.send(
            f"`{msg.author.display_name}` hat das Wort in "
            f"`{fin_time} Sekunden` erraten.\n"
            f"`{amount_won} Eisen` gewonnen *(15s Cooldown)*")
        await load.save_user_data(msg.author.id, amount_won)
        self.data.update({ctx.guild.id: False})
        await asyncio.sleep(15)
        self.data.pop(ctx.guild.id)


def setup(bot):
    bot.add_cog(Anagram(bot))
