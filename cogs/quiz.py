import asyncio
from bs4 import BeautifulSoup
from discord.ext import commands
from utils import game_channel_only, error_embed, pcv
from load import load
import random
import discord

stat = {"id": "ID",
        "rank": "Rang",
        "points": "Punkte",
        "villages": "Dörfer",
        "all_bash": "Bashpoints",
        "ut_bash": "UT Bashpoints"}

way = {"id": ["älteste", "neuste"],
       "rank": ["besten", "schlechtesten"],
       "points": ["meisten", "wenigsten"],
       "villages": ["meisten", "wenigsten"],
       "all_bash": ["meisten", "wenigsten"],
       "ut_bash": ["meisten", "wenigsten"]}

pl_options = {"id": "die {} ID?",
              "rank": "den {} Rang?",
              "points": "die {} Punkte?",
              "all_bash": "die {} besiegten Gegner?",
              "ut_bash": "die {} Unterstützer-Bashis?"}

tr_options = {"id": "die {} ID?",
              "rank": "den {} Rang?",
              "points": "die {} Punkte?",
              "villages": "die {} Dörfer?",
              "all_bash": "die {} besiegten Gegner?"}


class Quiz(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = {}
        self.game_pool = [
            self.top_entity,
            self.general_ask,
            self.tribe_quiz,
            self.image_guess
        ]

    def quiz_embed(self, desc, rounds, ingame=False):
        title = "Frage " + rounds if not ingame else rounds
        embed = discord.Embed(color=0x206694, title=title, description=desc)
        return embed

    def rankings(self, iterable):
        cache = []
        for index, name in enumerate(iterable):
            cache.append(f"`{index + 1}` | **{name}**")
        return '\n'.join(cache)

    async def wait_for_answers(self, ctx, answer, add=0):
        winner = []
        cache = []

        def check(m):
            if m.channel != ctx.channel:
                return
            if m.content.lower() == answer.lower():
                if m.author not in cache:
                    winner.append(m.author)
            if m.author not in cache:
                if add:
                    cache.append(m.author)
                    return
                if m.content.isdigit():
                    cache.append(m.author)

        try:
            await self.bot.wait_for('message', check=check, timeout=10 + add)
        except asyncio.TimeoutError:
            if not cache:
                return
            return winner

    # Module One
    async def top_entity(self, ctx, cur):
        switch = random.choice([True, False])
        gravity = random.choice([True, False])
        top = 15 if switch else 100
        data = await load.fetch_random(ctx.world, top=top, amount=5, tribe=switch)
        base = f"Welcher dieser 5 {'Stämme' if switch else 'Spieler'} hat"
        witcher = tr_options if switch else pl_options
        key = random.choice(list(witcher))

        listed = []
        for entry in data:
            value = getattr(entry, key)
            listed.append((value, entry))

        lowest = key in ("rank", "id")
        reverse = lowest if gravity else not lowest
        value, obj = sorted(listed, key=lambda x: x[0], reverse=reverse)[0]

        options = self.rankings([u.name for u in data])
        which = way[key][1] if gravity else way[key][0]
        question = f"{base} {witcher[key].format(which)}\n\n{options}"
        index = str(data.index(obj) + 1)
        sweet = f"{stat[key]} {value}" if lowest else f"{pcv(value)} {stat[key]}"
        answer_str = f"{obj.name} | {sweet}"

        await ctx.send(embed=self.quiz_embed(question, cur))
        result = await self.wait_for_answers(ctx, index)
        return result, answer_str

    # Module Two
    async def general_ask(self, ctx, rounds):
        raw_question, answer = random.choice(load.msg["generalQuestion"])
        splitted = raw_question.split(" ")
        mid = int((len(splitted) + 1) / 2)
        first_half, second_half = ' '.join(splitted[:mid]), ' '.join(splitted[mid:])
        question = f"{first_half}\n{second_half}"
        await ctx.send(embed=self.quiz_embed(question, f"{rounds} (15s)"))
        result = await self.wait_for_answers(ctx, answer, 5)
        return result, answer

    # Module Three
    async def tribe_quiz(self, ctx, rounds):
        tribes = await load.fetch_random(ctx.world, amount=5, top=15, tribe=True)
        positive = random.choice([True, False])
        target, rest = tribes[0].id, [obj.id for obj in tribes[1:]]
        foo, bar = (rest, target) if positive else (target, rest)
        data = await load.fetch_tribe_member(ctx.world, foo)

        fake_list = []
        while len(fake_list) < 4:
            player = random.choice(data)
            if player not in fake_list:
                fake_list.append(player)

        data = await load.fetch_tribe_member(ctx.world, bar)
        target_player = random.choice(data)
        result = fake_list + [target_player]
        random.shuffle(result)

        solution, guessable = target_player.name, [obj.name for obj in result]

        options = self.rankings(guessable)
        no = " " if positive else " nicht "
        msg = f"Welcher dieser Spieler ist{no}bei `{tribes[0].name}`?"
        question = "{}\n{}".format(msg, options)
        index = str(guessable.index(solution) + 1)
        await ctx.send(embed=self.quiz_embed(question, rounds))

        result = await self.wait_for_answers(ctx, index)
        return result, solution

    # Module Four
    async def image_guess(self, ctx, rounds):
        state = random.choice([True, False])
        top = 15 if state else 100
        obj_list = await load.fetch_random(ctx.world, amount=top, top=top, tribe=state)
        random.shuffle(obj_list)
        for obj in obj_list:
            async with self.bot.session.get(obj.guest_url) as resp:
                data = await resp.read()

            soup = BeautifulSoup(data, "html.parser")
            if state:
                result = soup.find('img')
            else:
                result = soup.find(alt='Profilbild')
            if not result:
                continue
            elif str(result).__contains__("/avatar/"):
                continue
            else:
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
                embed = self.quiz_embed(msg, rounds)
                embed.set_image(url=result['src'])
                await ctx.send(embed=embed)
                break
        else:
            return None, None

        result = await self.wait_for_answers(ctx, index)
        return result, obj.name

    @commands.command(name="quiz")
    @game_channel_only()
    async def quiz(self, ctx, rounds: int = 5):

        if ctx.guild.id in self.data:
            msg = "Auf diesem Server läuft bereits eine Runde"
            return await ctx.send(embed=error_embed(msg))

        if rounds < 5:
            msg = "Die Mindestanzahl der Runden beträgt 5"
            return await ctx.send(embed=error_embed(msg))

        title = "**Das Spiel startet in Kürze** (15s)"
        msg = "Pro Runde ein Zeitfenster von 10s,\n" \
              "nur die erste Antwort wird gewertet!"

        await ctx.send(embed=discord.Embed(title=title, description=msg))
        await asyncio.sleep(15)

        self.data[ctx.guild.id] = {}
        game_count = 0
        while game_count < rounds:
            game = random.choice(self.game_pool)
            cur = f"{game_count + 1} / {rounds}"
            result, answer = await game(ctx, cur)

            if result is None:
                continue

            game_count += 1
            if not result:
                msg = "Leider hatte niemand die richtige Antwort.\n{}"
                msg = msg.format(f"** Lösung:** `{answer}`")
                await ctx.send(embed=discord.Embed(description=msg, colour=0x992d22))
                continue

            winner = ""
            for index, obj in enumerate(result):

                if obj in self.data[ctx.guild.id]:
                    self.data[ctx.guild.id][obj] += 1
                else:
                    self.data[ctx.guild.id][obj] = 1

                name = getattr(obj, 'name')
                if index % 2 == 0:
                    extra = " |" if obj != result[-1] else ""
                    winner = f"{winner}**{name}**{extra}"
                else:
                    last = "" if obj == result[-1] else "\n"
                    winner = f"{winner} **{name}**{last}"

            msg = f"Folgende User hatten die richtige Antwort:\n{winner}"
            await ctx.send(embed=discord.Embed(description=msg, color=0x1f8b4c))
            await asyncio.sleep(5)

        if game_count < rounds:
            await ctx.send(embed=error_embed("Quiz vorzeitig beendet"))
        else:

            pool = self.data[ctx.guild.id]
            ranking = sorted(pool.items(), key=lambda k: k[1], reverse=True)
            result_msg = []
            for user, points in ranking:
                msg = f"`{points}` | **{user.display_name}**"
                if points == ranking[0][1]:
                    won = 1500 * points
                    msg = f"{msg} `[{won} Eisen]`"
                    await load.save_user_data(user.id, won)
                result_msg.append(msg)

            if not pool:
                description = "Nicht ein einziger Punkt. Enttäuschend!"
            else:
                description = '\n'.join(result_msg)
            end_embed = self.quiz_embed(description, "Quiz beendet!", True)
            await ctx.send(embed=end_embed)

        self.data.pop(ctx.guild.id)


def setup(bot):
    bot.add_cog(Quiz(bot))
