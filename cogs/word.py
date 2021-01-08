from discord.ext import commands
import datetime
import asyncio
import random
import utils
import os
import re


class Word(utils.DSGames):
    def __init__(self, bot):
        self.bot = bot
        self.type = 3
        self.anagram = {}
        self.hangman = {}

    async def victory_royale(self, ctx, data):
        length = len(data['solution'])
        amount = int(200 * length * (data['life'] / 8 + 0.5) + 2500)

        base = "Herzlichen Glückwunsch `{}`\n" \
               "Du hast `{} Eisen` gewonnen :trophy: (15s Cooldown)"
        msg = base.format(ctx.author.display_name, amount)

        async with self.end_game(ctx):
            await self.bot.update_iron(ctx.author.id, amount)
            await ctx.send(msg)

    async def wrong_choice(self, ctx, title, loss=1):
        data = self.hangman[ctx.guild.id]
        data['life'] -= loss

        if data['life'] <= 0:
            base = "**Game Over** | Lösungswort:{}`{}` (15s Cooldown)"
            msg = base.format(os.linesep, data['solution'])
            async with self.end_game(ctx):
                await ctx.send(msg)

        else:
            guessed = "` `".join(data['guessed'])
            base = "{}: `noch {} Leben`\nBereits versucht: `{}`"
            msg = base.format(title, data['life'], guessed)
            await ctx.send(msg)

    def show_blanks(self, id_or_blanks):
        if isinstance(id_or_blanks, int):
            blanks = self.hangman[id_or_blanks]['blanks']
        else:
            blanks = id_or_blanks

        return f"`{' '.join(blanks)}`"

    @utils.game_channel_only()
    @commands.command(name="anagram", aliases=["ag"])
    async def anagram_(self, ctx):
        data = self.get_game_data(ctx)

        if data is not None:
            comment = f"| `{data['hint']}` " if data.get('hint') else ""
            now = (datetime.datetime.now() - data['time']).seconds
            content = f"`{data['word']}` {comment}*(noch {60 - now}s)*"
            data['msg'] = await ctx.send(content)
            return

        word = ""
        while not word:
            cache = random.choice(ctx.lang.tribal_words)
            if cache.count(" ") == 0:
                word = cache.strip()

        word_list = list(word)
        while "".join(word_list) == word:
            random.shuffle(word_list)

        show = " ".join(word_list).upper()
        data = {'word': show, 'win': word, 'time': datetime.datetime.now()}
        self.anagram[ctx.guild.id] = data

        start_msg = await ctx.send(f"`{show}` (60s Timeout)")
        self.anagram[ctx.guild.id]['msg'] = start_msg

        def check(m):
            if m.channel == ctx.channel:
                return m.content.lower() == word.lower()

        try:
            win_msg = await self.bot.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError:

            try:
                hint_list = word[:int(len(word) / 4)].upper()
                hint = f"{' '.join(hint_list)} . . ."
                self.anagram[ctx.guild.id]['hint'] = hint
                await data['msg'].edit(content=f"`{show}` | `{hint}` (noch 30s)")
                win_msg = await self.bot.wait_for('message', check=check, timeout=30)

            except asyncio.TimeoutError:
                async with self.end_game(ctx):
                    await ctx.send(f"Die Zeit ist abgelaufen: `{word}`")
                    return

        end_time = datetime.datetime.now()
        raw_diff = (end_time - data['time']).total_seconds()
        float_diff = float("%.1f" % raw_diff)
        percent = (1 - float_diff / 60 + 1)
        amount = int((200 * len(word) + 100 * percent ** 2) * percent)

        base = "`{}` hat das Wort in `{} Sekunden` erraten.\n" \
               "`{} Eisen` gewonnen (15s Cooldown)"
        msg = base.format(win_msg.author.display_name, float_diff, amount)

        async with self.end_game(ctx):
            await self.bot.update_iron(win_msg.author.id, amount)
            await ctx.send(msg)

    @utils.game_channel_only()
    @commands.command(name="hangman", aliases=["hg"])
    async def hangman(self, ctx):
        data = self.get_game_data(ctx)

        if data is None:
            word = random.choice(ctx.lang.tribal_words)
            blanks = list(re.sub(r'[\w]', '_', word))
            data = {'guessed': [], 'blanks': blanks, 'solution': word, 'life': 8}
            self.hangman[ctx.guild.id] = data

            base = "Das Spiel wurde gestartet, errate mit **{}guess**:\n{}"
            board = f"{self.show_blanks(blanks)} - `8 Leben`"
            msg = base.format(ctx.prefix, board)
            await ctx.send(msg)

        else:
            base = "Es läuft bereits ein Spiel:\n{}"
            msg = base.format(self.show_blanks(ctx.guild.id))
            await ctx.send(msg)

    @utils.game_channel_only()
    @commands.command(name="guess", hidden=True)
    async def guess(self, ctx, *, args):
        data = self.get_game_data(ctx)

        if data is None:
            base = "Aktuell ist kein Spiel im Gange.\nStarte mit `{}hangman`"
            msg = base.format(ctx.prefix)
            await ctx.send(msg)
            return

        guess = args.lower()
        win = data['solution']

        # checks for direct win
        if guess == win.lower():
            await self.victory_royale(ctx, data)
            return

        check = data['guessed']
        blanks = data['blanks']

        # checks for valid input (1 character)
        if not len(guess) == 1:
            msg = "Falsches Lösungswort"
            await self.wrong_choice(ctx, msg, 2)
            return

        # checks if character was already guessed
        if guess in check:
            msg = "Der Buchstabe wurde bereits versucht"
            await self.wrong_choice(ctx, msg)
            return

        data['guessed'].append(guess)

        word_list = list(win.lower())
        positions = []
        while guess in word_list:
            pos = ''.join(word_list).find(guess)
            positions.append(pos + len(positions))
            word_list.remove(guess)

        # replaces placeholders with guess characters
        for num in positions:
            blanks[num] = list(win)[num]

        # nothing was found
        if not positions:
            msg = "Leider nicht der richtige Buchstabe"
            await self.wrong_choice(ctx, msg)
            return

        # last character was found
        if blanks == list(win):
            await self.victory_royale(ctx, data)

        else:
            # sends new blanks with the found chars in it
            await ctx.send(self.show_blanks(blanks))


def setup(bot):
    bot.add_cog(Word(bot))
