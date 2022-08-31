from discord import app_commands
from bs4 import BeautifulSoup
from collections import Counter
import asyncio
import discord
import random
import utils


class Quiz:
    format = (
        "points",
        "att_bash",
        "def_bash",
        "sup_bash",
        "all_bash"
    )

    def __init__(self, interaction, rounds):
        self.interaction = interaction
        self.client = interaction.client
        self.rounds = rounds
        self.rounds_played = 0
        self.current_answer = None
        self.points = Counter()

        # game cache
        self.guess_cache = []
        self.correct_guesser = []

        self.game_pool = (
            self.top_entity,
            self.general_ask,
            self.tribe_quiz,
            self.image_guess
        )

    @property
    def is_active(self):
        return self.rounds_played < self.rounds

    async def prepare_next_round(self):
        await asyncio.sleep(5)
        self.correct_guesser.clear()
        self.guess_cache.clear()

    def quiz_embed(self, desc, done=False):
        rounds = f"{self.rounds_played + 1} / {self.rounds}"
        title = "Frage " + rounds if not done else "Quiz beendet!"
        embed = discord.Embed(color=0x206694, title=title, description=desc)
        return embed

    def rankings(self, iterable):
        cache = []
        for index, name in enumerate(iterable):
            cache.append(f"`{index + 1}` | **{name}**")
        return '\n'.join(cache)

    async def play_round(self):
        game = random.choice(self.game_pool)
        response = await game()

        if response is None:
            return

        self.rounds_played += 1
        self.current_answer, solution = response
        await asyncio.sleep(20)
        result = self.correct_guesser if self.guess_cache else None
        return result, solution

    def guess(self, interaction, guess):
        if interaction.user in self.guess_cache:
            return False
        else:
            self.guess_cache.append(interaction.user)

        if guess.lower() == self.current_answer.lower():
            self.correct_guesser.append(interaction.user)

        return True

    # Module One
    async def top_entity(self):
        switch = random.choice([True, False])
        gravity = random.choice([True, False])
        top = 15 if switch else 100
        data = await self.client.fetch_random(self.interaction.server, top=top, amount=5, tribe=switch)
        base = f"Welcher dieser 5 {'Stämme' if switch else 'Spieler'} hat"

        pkg_name = 'tribe_options' if switch else 'player_options'
        pkg = self.interaction.lang.quiz[pkg_name]
        key = random.choice(list(pkg))

        listed = []
        for entry in data:
            value = getattr(entry, key)
            listed.append((value, entry))

        lowest = key in ("rank", "id")
        reverse = lowest if gravity else not lowest
        value, obj = sorted(listed, key=lambda x: x[0], reverse=reverse)[0]

        options = self.rankings([u.name for u in data])
        which = self.interaction.lang.quiz['either'][key][gravity]
        question = f"{base} {pkg[key].format(which)}\n\n{options}"
        index = str(data.index(obj) + 1)

        if lowest:
            sweet = f"{self.interaction.lang.quiz['name'][key]} {value}"
        else:
            sweet = f"{utils.seperator(value)} {self.interaction.lang.quiz['name'][key]}"

        answer_str = f"{obj.name} | {sweet}"
        embed = self.quiz_embed(question)
        await self.interaction.channel.send(embed=embed)
        return index, answer_str

    # Module Two
    async def general_ask(self):
        raw_question, answer = random.choice(self.interaction.lang.quiz['questions'])
        splitted = raw_question.split(" ")
        mid = int((len(splitted) + 1) / 2)
        first_half, second_half = ' '.join(splitted[:mid]), ' '.join(splitted[mid:])
        question = f"{first_half}\n{second_half}"
        await self.interaction.channel.send(embed=self.quiz_embed(question))
        return str(answer), answer

    # Module Three
    async def tribe_quiz(self):
        tribes = await self.client.fetch_random(self.interaction.server, amount=5, top=15, tribe=True)
        positive = random.choice([True, False])
        target, rest = tribes[0].id, [obj.id for obj in tribes[1:]]
        foo, bar = (rest, target) if positive else (target, rest)
        data = await self.client.fetch_tribe_member(self.interaction.server, foo)
        random.shuffle(data)

        if len(data) < 4:
            return

        fake_list = []
        while len(fake_list) < 4:
            player = data.pop(0)
            fake_list.append(player)

        data = await self.client.fetch_tribe_member(self.interaction.server, bar)
        target_player = random.choice(data)
        result = fake_list + [target_player]
        random.shuffle(result)

        answer, guessable = target_player.name, [obj.name for obj in result]

        options = self.rankings(guessable)
        no = " " if positive else " nicht "
        msg = f"Welcher dieser Spieler ist{no}bei `{tribes[0].name}`?"
        question = "{}\n{}".format(msg, options)
        index = str(guessable.index(answer) + 1)
        embed = self.quiz_embed(question)
        await self.interaction.channel.send(embed=embed)
        return index, answer

    # Module Four
    async def image_guess(self):
        state = random.choice([True, False])
        top = 15 if state else 100
        kwargs = {'amount': top, 'top': top, 'tribe': state, 'max': True}
        obj_list = await self.client.fetch_random(self.interaction.server, **kwargs)
        random.shuffle(obj_list)

        if len(obj_list) < 5:
            return

        for obj in obj_list:
            async with self.client.session.get(obj.guest_url) as resp:
                data = await resp.read()

            soup = BeautifulSoup(data, "html.parser")
            keyword = 'img' if not state else 'Profilbild'
            result = soup.find(alt=keyword)

            if result and "/avatar/" not in str(result):
                title = "Stamm" if state else "Spieler"
                options = [obj]

                while len(options) < 4:
                    dude = random.choice(obj_list)
                    if dude not in options:
                        options.append(dude)

                random.shuffle(options)
                index = str(options.index(obj) + 1)
                formatted = self.rankings([u.name for u in options])
                msg = f"Welchem {title} gehört dieses Bild?\n{formatted}"
                embed = self.quiz_embed(msg)
                embed.set_image(url=result['src'])
                await self.interaction.channel.send(embed=embed)
                break
        else:
            return

        return index, obj.name


class Card(utils.DSGames):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.type = 3
        self.quiz = {}

    def show_player_hand(self, hand, instruction):
        description = f"**Tribalcard | Deine Hand:**\n\n"

        for index, player in enumerate(hand):
            card = f"**{index + 1}**: {player.name}\n"
            description += card

        embed = discord.Embed(description=description)
        embed.set_footer(text=instruction)
        return embed

    quiz = app_commands.Group(name="quiz", description="xd")

    @utils.game_channel_only()
    @app_commands.checks.bot_has_permissions(send_messages=True)
    @quiz.command(name="start", description="Beginne ein Quiz rund um die Stämme mit diversen Modulen")
    @app_commands.describe(rounds="Die Anzahle der Runden zwischen 5 und 15")
    async def quiz_start(self, interaction, rounds: app_commands.Range[int, 5, 15] = 5):
        if interaction.guild.id in self.quiz:
            msg = "Auf diesem Server läuft bereits eine Runde"
            await interaction.response.send_message(msg)
            return

        title = "**Das Spiel startet in Kürze** (15s)"
        msg = "Pro Runde ein Zeitfenster von 10s,\n" \
              "nur die erste Antwort wird gewertet!"

        embed = discord.Embed(title=title, description=msg)
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(15)

        quiz = Quiz(interaction, rounds)
        self.quiz[interaction.guild.id] = quiz

        while quiz.is_active:
            response = await quiz.play_round()

            # not enough data
            if response is None:
                continue
            else:
                result, answer = response

            # nobody answered
            if result is None:
                break

            # no right answer
            elif not result:
                msg = "Leider hatte niemand die richtige Antwort."
                embed = discord.Embed(description=msg, colour=0x992d22)
                embed.set_footer(text=f"Lösung: {answer}")
                await interaction.channel.send(embed=embed)
                await quiz.prepare_next_round()
                continue

            winner = ""
            for index, obj in enumerate(result):
                quiz.points[obj] += 1

                name = getattr(obj, 'name')
                if index % 2 == 0:
                    extra = " |" if obj != result[-1] else ""
                    winner = f"{winner}**{name}**{extra}"
                else:
                    last = "" if obj == result[-1] else "\n"
                    winner = f"{winner} **{name}**{last}"

            msg = f"Folgende User hatten die richtige Antwort:\n{winner}"
            embed = discord.Embed(description=msg, color=0x1f8b4c)
            embed.set_footer(text=f"Lösung: {answer}")
            await interaction.channel.send(embed=embed)
            await quiz.prepare_next_round()

        if quiz.is_active:
            msg = "Keine Antwort, Quiz vorzeitig beendet"
            embed = utils.error_embed(msg)

        else:
            pool = self.quiz[interaction.guild.id].points
            ranking = sorted(pool.items(), key=lambda k: k[1], reverse=True)
            result_msg = []
            for user, points in ranking:
                msg = f"`{points}` | **{user.display_name}**"
                if points == ranking[0][1]:
                    amount = 1500 * points
                    msg = f"{msg} `[{amount} Eisen]`"
                    await self.bot.update_iron(user.id, amount)
                result_msg.append(msg)

            if not pool:
                description = "Nicht ein einziger Punkt. Enttäuschend!"
            else:
                description = '\n'.join(result_msg)
            embed = quiz.quiz_embed(description, done=True)

        async with self.end_game(interaction):
            await interaction.channel.send(embed=embed)

    @quiz.command(name="guess", description="Rate bei einer aktuellen Quizrunde mit")
    @app_commands.describe(guess="Dein Guess als Zahl außer es wird spezifisch nach einem Wort gefragt")
    async def quiz_guess(self, interaction, guess: str):
        quiz = self.get_game_data(interaction)

        if not quiz:
            msg = "Aktuell gibt es keine offene Runde, starte mit `/quiz start`"
            await interaction.response.send_message(msg)
            return

        response = quiz.guess(interaction, guess)

        if response is True:
            await interaction.response.send_message("Guess erhalten!", ephemeral=True)
        else:
            await interaction.response.send_message("Du hast bereits geraten", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Card(bot))
