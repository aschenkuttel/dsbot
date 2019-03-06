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

    def get_word(self, guild_id, sol=0):
        if sol:
            return self.data[guild_id]["win"]
        else:
            return self.data[guild_id]["word"]

    @commands.command(name="anagram", aliases=["ag"])
    @game_channel_only(load)
    async def anagram_(self, ctx):

        if ctx.guild.id in self.data:
            if self.data[ctx.guild.id] == 0:
                return
            else:
                ag_time = self.data[ctx.guild.id]["time"]
                now = (datetime.datetime.now() - ag_time).seconds
                try:
                    hint = self.data[ctx.guild.id]["hint"]
                    msg = f"`{self.get_word(ctx.guild.id)}` | `{hint}` *(noch {60 - now}s)*"
                    return await ctx.send(msg)
                except KeyError:
                    msg = f"`{self.get_word(ctx.guild.id)}` *(noch {60 - now}s)*"
                    return await ctx.send(msg)

        word = random.choice(load.msg["hangman"])
        while len(word.split(" ")) > 1:
            word = random.choice(load.msg["hangman"])
        if word.endswith("\n"):
            word = word[:-1]
        show = list(word)
        while ''.join(show).lower() == word.lower():
            random.shuffle(show)
        show = ' '.join(show).upper()
        start_time = datetime.datetime.now()
        data = {"word": show, "win": word, "time": start_time}
        self.data.update({ctx.guild.id: data})
        win_chan = load.get_config(ctx.guild.id, "game")
        start_msg = await ctx.send(f"`{show}` *(60s Timeout)*")

        def che(m):
            if not m.guild:
                return False
            if m.guild.id not in self.data:
                return False
            if m.channel.id == win_chan and m.guild == ctx.guild:
                res = self.data[m.guild.id]["win"].lower()
                if res == m.content.lower():
                    return True

        try:
            msg = await ctx.bot.wait_for('message', check=che, timeout=30)
        except asyncio.TimeoutError:
            try:
                win = self.get_word(ctx.guild.id, 1)
                hin = f"{' '.join(list(win[:int(len(win) / 4)].upper()))} . . ."
                self.data[ctx.guild.id]["hint"] = hin
                stuff = f"`{show}` | `{self.data[ctx.guild.id]['hint']}`"
                await start_msg.edit(content=f"{stuff}(noch 30s)")
                msg = await ctx.bot.wait_for('message', check=che, timeout=30)
            except asyncio.TimeoutError:
                won = self.data[ctx.guild.id]['win']
                await ctx.send(f"Die Zeit ist abgelaufen: `{won}`")
                self.data.pop(ctx.guild.id)
                return
        end_time = datetime.datetime.now()
        fin_time = str((end_time - start_time).total_seconds()).split(".")
        fin_time = f"{fin_time[0]}.{fin_time[1][0]}"
        ran = random.randint(150, 300)
        time = len(self.data[ctx.guild.id]['win'])
        amount_won = int((ran * time) * (1 - float(fin_time) / 60 + 1))
        await msg.channel.send(
            f"`{msg.author.display_name}` hat das Wort in "
            f"`{fin_time} Sekunden` erraten. "
            f"`{amount_won} Eisen` gewonnen *(15s Cooldown)*")
        await load.save_user_data(msg.author.id, amount_won)
        self.data.update({ctx.guild.id: 0})
        await asyncio.sleep(15)
        self.data.pop(ctx.guild.id)


def setup(bot):
    bot.add_cog(Anagram(bot))
