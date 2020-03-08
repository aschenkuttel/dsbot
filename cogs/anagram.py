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
        key = 'win' if solution else 'word'
        return self.data[guild_id][key]

    @commands.command(name="anagram", aliases=["ag"])
    @game_channel_only()
    async def anagram_(self, ctx):

        game_data = self.data.get(ctx.guild.id)
        if game_data is False:
            return
        if game_data:
            ag_time = game_data['time']
            now = (datetime.datetime.now() - ag_time).seconds
            hint = game_data.get('hint')
            comment = f"| `{hint}` " if hint else ""
            msg = f"`{game_data['word']}` {comment}*(noch {60 - now}s)*"
            return await ctx.send(msg)

        word = None
        while not word:
            cache = random.choice(self.bot.msg["hangman"])
            if len(cache.split()) == 1:
                word = cache.strip()

        word_list = list(word)
        while ''.join(word_list) == word:
            random.shuffle(word_list)

        show = ' '.join(word_list).upper()
        hint_list = list(word[:int(len(word) / 4)].upper())
        hint = f"{' '.join(hint_list)} . . ."

        start_time = datetime.datetime.now()
        data = {'word': show, 'win': word, 'time': start_time}
        self.data[ctx.guild.id] = data
        start_msg = await ctx.send(f"`{show}` (60s Timeout)")

        def check(m):
            if m.channel == ctx.channel:
                if m.content.lower() == word.lower():
                    return True

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError:
            try:
                self.data[ctx.guild.id]['hint'] = hint
                stuff = f"`{show}` | `{hint}`"
                await start_msg.edit(content=f"{stuff}(noch 30s)")
                msg = await self.bot.wait_for('message', check=check, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send(f"Die Zeit ist abgelaufen: `{word}`")
                self.data.pop(ctx.guild.id)
                return

        end_time = datetime.datetime.now()
        diff = float("%.1f" % (end_time-start_time).total_seconds())
        spec_bonus = (60 - diff) * (50 * (1 - diff / 60)) * (1 - diff / 60)
        amount_won = int((150 * len(word) + spec_bonus) * (1 - diff / 60 + 1))

        await ctx.send(
            f"`{msg.author.display_name}` hat das Wort in "
            f"`{diff} Sekunden` erraten.\n"
            f"`{amount_won} Eisen` gewonnen (15s Cooldown)")
        await self.bot.save_user_data(msg.author.id, amount_won)
        self.data[ctx.guild.id] = False
        await asyncio.sleep(15)
        self.data.pop(ctx.guild.id)


def setup(bot):
    bot.add_cog(Anagram(bot))
