from discord import app_commands
import datetime
import asyncio
import random
import utils
import os
import re


class Word(utils.DSGames):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.type = 3
        self.anagram = {}
        self.hangman = {}

    async def victory_royale(self, interaction, data):
        length = len(data['solution'])
        amount = int(200 * length * (data['life'] / 8 + 0.5) + 2500)

        base = "Herzlichen Glückwunsch `{}`\n" \
               "Du hast `{} Eisen` gewonnen :trophy: (10s Cooldown)"
        msg = base.format(interaction.user.display_name, amount)

        async with self.end_game(interaction):
            await self.bot.update_iron(interaction.user.id, amount)
            await interaction.response.send_message(msg)

    async def wrong_choice(self, interaction, title, loss=1):
        data = self.hangman[interaction.guild.id]
        data['life'] -= loss

        if data['life'] <= 0:
            base = "**Game Over** | Lösungswort:{}`{}` (10s Cooldown)"
            msg = base.format(os.linesep, data['solution'])
            async with self.end_game(interaction):
                await interaction.response.send_message(msg)

        else:
            guessed = "` `".join(data['guessed'])
            base = "{}: `noch {} Leben`\nBereits versucht: `{}`"
            msg = base.format(title, data['life'], guessed)
            await interaction.response.send_message(msg)

    def show_blanks(self, id_or_blanks):
        if isinstance(id_or_blanks, int):
            blanks = self.hangman[id_or_blanks]['blanks']
        else:
            blanks = id_or_blanks

        return f"`{' '.join(blanks)}`"

    @utils.game_channel_only()
    @app_commands.command(name="ag", description="Anagram Ratespiel mit Worten aus DS")
    @app_commands.describe(guess="Das Lösungswort")
    async def anagram(self, interaction, guess: str = None):
        data = self.get_game_data(interaction)

        if data is None:
            if guess is None:
                word = ""
                while not word:
                    cache = random.choice(interaction.lang.tribal_words)
                    if cache.count(" ") == 0:
                        word = cache.strip()

                word_list = list(word)
                while "".join(word_list) == word:
                    random.shuffle(word_list)

                anagram = " ".join(word_list).upper()
                data = {'id': interaction.id, 'word': word, 'anagram': anagram, 'time': datetime.datetime.now()}
                self.anagram[interaction.guild.id] = data

                await interaction.response.send_message(f"`{anagram}` (60s Timeout)")
                await asyncio.sleep(30)

                current = self.anagram.get(interaction.guild.id)
                if current and current['id'] == data['id']:
                    hint_list = word[:int(len(word) / 4)].upper()
                    hint = f"{' '.join(hint_list)} . . ."
                    current['hint'] = hint
                    await interaction.edit_original_response(content=f"`{anagram}` | `{hint}` (noch 30s)")
                    await asyncio.sleep(30)

                    current = self.anagram.get(interaction.guild.id)
                    if current and current['id'] == data['id']:
                        async with self.end_game(interaction):
                            await interaction.channel.send(f"Die Zeit ist abgelaufen: `{word}`")

            else:
                msg = "Aktuell ist kein Spiel im Gange.\nStarte mit `/ag`"
                await interaction.response.send_message(msg, ephemeral=True)

        else:
            word, anagram = data['word'], data['anagram']
            hint, time = data.get('hint'), data['time']

            if guess is None:
                comment = f"| `{hint}` " if hint else ""
                now = (datetime.datetime.now() - time).seconds
                msg = f"`{anagram}` {comment}*(noch {60 - now}s)*"
                await interaction.response.send_message(msg, ephemeral=True)

            elif guess.lower() == word.lower():
                end_time = datetime.datetime.now()
                raw_diff = (end_time - time).total_seconds()
                float_diff = float("%.1f" % raw_diff)
                percent = (1 - float_diff / 60 + 1)
                amount = int((200 * len(word) + 100 * percent ** 2) * percent)

                base = "`{}` hat das Wort in `{} Sekunden` erraten.\n" \
                       "`{} Eisen` gewonnen (10s Cooldown)"
                msg = base.format(interaction.user.display_name, float_diff, amount)

                async with self.end_game(interaction):
                    await self.bot.update_iron(interaction.user.id, amount)
                    await interaction.response.send_message(msg)

            else:
                msg = "Leider die falsche Antwort..."
                await interaction.response.send_message(msg, ephemeral=True)

    @utils.game_channel_only()
    @app_commands.command(name="hg", description="Hangman mit Worten aus DS")
    @app_commands.describe(guess="Ein Buchstabe oder das gewünschte Lösungswort")
    async def hangman(self, interaction, guess: str = None):
        data = self.get_game_data(interaction)

        if data is None:
            if guess is None:
                word = random.choice(interaction.lang.tribal_words)
                blanks = list(re.sub(r'[\w]', '_', word))
                data = {'guessed': [], 'blanks': blanks, 'solution': word, 'life': 8}
                self.hangman[interaction.guild.id] = data

                base = "Das Spiel wurde gestartet, errate mit **/guess**:\n{}"
                board = f"{self.show_blanks(blanks)} - `8 Leben`"
                await interaction.response.send_message(base.format(board))

            else:
                msg = "Aktuell ist kein Spiel im Gange.\nStarte mit `/hg`"
                await interaction.response.send_message(msg)

        elif guess is None:
            base = "Es läuft bereits ein Spiel:\n{}"
            msg = base.format(self.show_blanks(interaction.guild.id))
            await interaction.response.send_message(msg)

        else:
            guess = guess.lower()
            win = data['solution']

            # checks for direct win
            if guess == win.lower():
                await self.victory_royale(interaction, data)
                return

            check = data['guessed']
            blanks = data['blanks']

            # checks for valid input (1 character)
            if not len(guess) == 1:
                msg = "Falsches Lösungswort"
                await self.wrong_choice(interaction, msg, 2)
                return

            # checks if character was already guessed
            if guess in check:
                msg = "Der Buchstabe wurde bereits versucht"
                await self.wrong_choice(interaction, msg)
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
                await self.wrong_choice(interaction, msg)
                return

            # last character was found
            if blanks == list(win):
                await self.victory_royale(interaction, data)

            else:
                # sends new blanks with the found chars in it
                await interaction.response.send_message(self.show_blanks(blanks))


async def setup(bot):
    await bot.add_cog(Word(bot))
