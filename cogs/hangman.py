from utils import error_embed, game_channel_only
from discord.ext import commands
from load import load
import asyncio
import random
import re


class Hangman(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = {}

    # returns item of game data via key
    def get_item(self, guild_id, key, raw=False):
        data = self.data[guild_id][key]
        return self.wrap(data) if raw else data

    # saves item in guild game data
    def save_item(self, guild_id, key, new):
        data = self.data[guild_id]
        if key != "guessed":
            data[key] = new
        else:
            data[key].append(new)

    # joins blank list
    def wrap(self, res):
        return f"`{' '.join(res)}`"

    # ends game and pops it after the cooldown
    async def game_end(self, guild_id):
        self.data[guild_id] = False
        await asyncio.sleep(15)
        self.data.pop(guild_id)

    # calculates price and saves it / calls the end
    async def victory_royale(self, ctx):
        word_length = len(self.get_item(ctx.guild.id, 'solution'))
        rest_life = self.get_item(ctx.guild.id, 'life')
        amount_won = int(250 * word_length * float(rest_life / word_length + 1))
        await ctx.send(
            f"Herzlichen Glückwunsch `{ctx.author.display_name}`\n"
            f"Du hast `{amount_won} Eisen` gewonnen "
            f":trophy: *(15s Cooldown)*")
        await load.save_user_data(ctx.author.id, amount_won)
        return await self.game_end(ctx.guild.id)

    # subtracts 1 life and ends the game if no lifes left
    async def wrong_choice(self, ctx, msg, minus=1):
        idc = ctx.guild.id
        life = self.get_item(idc, 'life')
        life -= minus
        if life <= 0:
            await ctx.send(f"**Game Over** | Lösungswort:\n"
                           f"`{self.get_item(idc, 'solution')}` "
                           f"*(15s Cooldown)*")
            await self.game_end(idc)
        else:
            await ctx.send(
                f"{msg} | `noch {life} Leben`\nBereits versucht: "
                f"`{'` `'.join(self.get_item(idc, 'guessed'))}`")
            self.save_item(idc, 'life', life)

    @commands.command(name="hangman", aliases=["galgenmännchen"])
    @game_channel_only()
    async def hangman(self, ctx):

        data = self.data.get(ctx.guild.id)
        if data is False:
            return
        if data is None:
            word = random.choice(load.msg["hangman"])
            life = int(len(word) * (50 - len(word)) / 50)
            blanks = list(re.sub(r'[\w]', '_', word))
            game = {'guessed': [], 'blanks': blanks, 'solution': word, 'life': life}
            self.data[ctx.guild.id] = game

            msg = f"Das Spiel wurde gestartet, errate mit **{ctx.prefix}guess**:" \
                  f"\n\n{self.wrap(blanks)} - `{life} Leben`"
            await ctx.send(msg)
        else:
            msg = "Es läuft bereits ein Spiel, errate mit " \
                  f"`{ctx.prefix}guess Buchstabe` oder löse sofort!\n\n" \
                  f"{self.get_item(ctx.guild.id, 'blanks', True)}"
            await ctx.send(msg)

    @commands.command(name="guess", aliases=["raten"])
    @game_channel_only()
    async def guess(self, ctx, *, args):
        data = self.data.get(ctx.guild.id)
        if data is False:
            return
        if data is None:
            msg = f"Aktuell ist kein Spiel im Gange.\n" \
                  f"Starte mit `{ctx.prefix}hangman`"
            return await ctx.send(msg)

        guess = args.lower()
        win = self.get_item(ctx.guild.id, 'solution')
        check = self.get_item(ctx.guild.id, 'guessed')
        blanks = self.get_item(ctx.guild.id, 'blanks')

        # checks for direct win
        if guess == win.lower():
            return await self.victory_royale(ctx)

        # checks for valid input (1 character)
        if not len(guess) == 1:
            msg = "Falsches Lösungswort"
            return await self.wrong_choice(ctx, msg, 2)

        # checks if character was already guessed
        if guess in check:
            msg = "Der Buchstabe wurde bereits versucht"
            return await self.wrong_choice(ctx, msg)

        self.save_item(ctx.guild.id, 'guessed', guess)

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
            return await self.wrong_choice(ctx, msg)

        # last character was found
        if blanks == list(win):
            return await self.victory_royale(ctx)

        # sends new blanks with the found chars in it
        self.save_item(ctx.guild.id, 'blanks', blanks)
        await ctx.send(self.wrap(blanks))

    @commands.command(name="guessed")
    @game_channel_only()
    async def guessed(self, ctx):
        if ctx.guild.id not in self.data:
            msg = f"Aktuell ist kein Spiel im Gange. Starte mit `{ctx.prefix}hangman`"
            return await ctx.send(embed=error_embed(msg))
        guessed = '` `'.join(self.get_item('guessed', ctx.guild.id))
        if not guessed:
            guessed = "Keine bisherigen Versuche"
        msg = f"{self.get_item(ctx.guild.id, 'blanks', True)}" \
              f" - Bereits versucht: `{guessed}`"
        await ctx.send(msg)


def setup(bot):
    bot.add_cog(Hangman(bot))
