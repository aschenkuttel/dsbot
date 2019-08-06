from discord.ext import commands
from load import load
from utils import error_embed, game_channel_only
import asyncio
import random


class Hangman(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = {}

    # --- Game Setup Func--- #
    def game_setup(self, guild_id):

        word = random.choice(load.msg["hangman"])
        word = word.strip()

        if len(word) >= 6:
            life = int(0.75 * len(word))
        else:
            life = len(word)

        blanks = []
        for char in word:
            if char in [" ", "-"]:
                blanks.append(char)
            else:
                blanks.append("_")

        game = {'guessed': [], 'blanks': blanks, 'solution': word, 'life': life}
        self.data.update({guild_id: game})

    # --- Info Getter --- #
    def get_info(self, guild_id, info, raw=False):
        data = self.data[guild_id][info]
        return self.wrap(data) if raw else data

    # --- Info Saver --- #
    def get_saved(self, guild_id, info, new):
        data = self.data[guild_id]
        if info != "guessed":
            data[info] = new
        else:
            data[info].append(new)

    # --- Disc Converter ---#
    def wrap(self, res):
        return f"`{' '.join(res)}`"

    # --- Hangman Function ---#
    def hangman_func(self, guild_id, inp):
        guess = inp.lower()
        win = self.get_info(guild_id, 'solution')
        check = self.get_info(guild_id, 'guessed')
        blanks = self.get_info(guild_id, 'blanks')

        # --- Only 1 Char! ---#
        if guess == win.lower():
            return 1

        if not len(guess) == 1:
            return 0

        if guess in check:
            return 3

        self.get_saved(guild_id, 'guessed', guess)
        win_c = list(win.lower())
        pos_list = []
        found = 0
        while win_c.__contains__(guess):
            pos = ''.join(win_c).find(guess)
            pos_list.append(pos + found)
            found += 1
            win_c.remove(guess)

        if not pos_list:
            return 2
        for num in pos_list:
            blanks[num] = list(win)[num]
        if set(blanks) == set(win):
            return 1

        self.get_saved(guild_id, 'blanks', blanks)
        return self.wrap(blanks)

    # --- Game Ending --- #
    async def game_end(self, guild_id):
        self.data[guild_id] = False
        await asyncio.sleep(15)
        self.data.pop(guild_id)

    # --- Life Edit --- #
    def life_edit(self, guild_id, normal=1):
        life_now = self.get_info(guild_id, 'life')
        life_now -= normal
        if life_now <= 0:
            return False
        self.get_saved(guild_id, 'life', life_now)
        return True

    @commands.command(name="hangman", aliases=["galgenmännchen"])
    @game_channel_only()
    async def hangman(self, ctx):

        data = self.data.get(ctx.guild.id)
        if data is False:
            return
        if data is None:
            self.game_setup(ctx.guild.id)
            pref = await self.bot.get_prefix(ctx.message)
            msg = f"Das Spiel wurde gestartet, errate mit **{pref}guess**:" \
                f"\n\n{self.get_info(ctx.guild.id, 'blanks', True)}" \
                f" - `{self.get_info(ctx.guild.id, 'life')} Leben`"
            return await ctx.send(msg)

        msg = "Es läuft bereits ein Spiel, errate mit " \
              "`!guess Buchstabe` oder löse sofort!\n\n" \
            f"{self.get_info(ctx.guild.id, 'blanks', True)}"
        await ctx.send(msg)

    @commands.command(name="guess", aliases=["raten"])
    @game_channel_only()
    async def guess(self, ctx, *, args):

        data = self.data.get(ctx.guild.id)
        if data is False:
            return
        if data is None:
            msg = "Aktuell ist kein Spiel im Gange. Starte mit `!hangman`"
            return await ctx.send(msg)

        # -- Guess --#
        guild = ctx.guild.id
        hang = self.hangman_func(guild, args)
        if hang == 0:
            if self.life_edit(guild, 2):
                msg = f"Falsches Lösungswort! `noch" \
                    f"{self.get_info(guild, 'life')} Leben`"
                await ctx.send(msg)
            else:

                msg = f"**Game Over** - Lösungswort: " \
                    f"`{self.get_info(guild, 'solution')}` *(15s Cooldown)*"
                await ctx.send(msg)
                await self.game_end(guild)

        elif hang == 1:

            word_length = len(self.get_info(guild, 'solution'))
            rest_life = self.get_info(guild, 'life')
            amount_won = int(250 * word_length * float(rest_life / word_length + 1))
            await ctx.send(
                f"Herzlichen Glückwunsch `{ctx.author.display_name}`\n"
                f"Du hast `{int(amount_won)} Eisen` gewonnen "
                f":trophy: *(15s Cooldown)*")
            await load.save_user_data(ctx.author.id, int(amount_won))
            await self.game_end(guild)

        elif hang == 2:

            if self.life_edit(guild):
                await ctx.send(
                    f"Leider nicht der richtige Buchstabe! "
                    f"`noch {self.get_info(guild, 'life')} Leben`\n"
                    f"Bereits versucht: "
                    f"`{'` `'.join(self.get_info(guild, 'guessed'))}`")
            else:

                await ctx.send(f"**Game Over** - Lösungswort: "
                               f"`{self.get_info(guild, 'solution')}` "
                               f"*(15s Cooldown)*")
                await self.game_end(guild)

        elif hang == 3:

            if self.life_edit(guild):
                await ctx.send(
                    f"Der Buchstabe wurde schon verwendet! "
                    f"`noch {self.get_info(guild, 'life')} Leben`\n"
                    f"Bereits versucht: "
                    f"`{'` `'.join(self.get_info(guild, 'guessed'))}`")
            else:

                await ctx.send(f"**Game Over** - Lösungswort: "
                               f"`{self.get_info(guild, 'solution')}` "
                               f"*(15s Cooldown)*")
                await self.game_end(guild)

        else:
            return await ctx.send(hang)

    @commands.command(name="guessed")
    @game_channel_only()
    async def guessed(self, ctx):
        if ctx.guild.id not in self.data:
            msg = "Aktuell ist kein Spiel im Gange. Starte mit `!hangman`"
            return await ctx.send(embed=error_embed(msg))
        guessed = '` `'.join(self.get_info('guessed', ctx.guild.id))
        if not guessed:
            guessed = "Keine bisherigen Versuche!"
        msg = f"{self.get_info(ctx.guild.id, 'blanks', True)}" \
            f" - Bereits versucht: `{guessed}`"
        await ctx.send(msg)


def setup(bot):
    bot.add_cog(Hangman(bot))
