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

    def receive(self, data, choice):
        result = []
        for entry in data:
            value = getattr(entry, choice)
            result.append((value, entry))
        return result

    def resolve(self, data, key, reverse=False):
        low = False if key in ("rank", "id") else True
        if reverse:
            low = not low
        res = sorted(data, key=lambda x: x[0], reverse=low)
        return res[0]

    def quiz_embed(self, desc, rounds, ingame=False):
        title = "Frage " + rounds if not ingame else rounds
        color = discord.Colour.dark_blue()
        embed = discord.Embed(color=color, title=title, description=desc)
        return embed

    def index_me_senpai(self, iterable):
        cache = []
        for index, name in enumerate(iterable):
            cache.append(f"`{index + 1}` | **{name}**")
        return '\n'.join(cache)

    def get_index(self, iterable, compareable):
        for index, obj in enumerate(iterable):
            if obj == compareable:
                return str(index + 1)

    def two_per(self, iterable, attr):
        result = ""
        for index, obj in enumerate(iterable):
            name = getattr(obj, attr)
            if index % 2 == 0:
                extra = " |" if obj != iterable[-1] else ""
                result = f"{result}**{name}**{extra}"

            else:
                last = "" if obj == iterable[-1] else "\n"
                result = f"{result} **{name}**{last}"
        return result

    def save_points(self, guild_id, user):
        if user in self.data[guild_id]:
            self.data[guild_id][user] += 1
        else:
            self.data[guild_id][user] = 1

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

    async def winner(self, guild_id):
        pool = self.data[guild_id]
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
        title = "Quiz beendet!"
        result = self.quiz_embed(description, title, True)
        return result

    async def get_player(self, world, tribes, positive):
        fake_list = []
        target, rest = tribes[0].id, [obj.id for obj in tribes[1:]]
        foo, bar = (rest, [target]) if positive else ([target], rest)
        data = await load.find_ally_player(world, foo)
        while len(fake_list) < 4:
            player = random.choice(data)
            if player not in fake_list:
                fake_list.append(player)
        data = await load.find_ally_player(world, bar)
        target_player = random.choice(data)
        result = fake_list + [target_player]
        random.shuffle(result)
        return target_player.name, [obj.name for obj in result]

    # Module One
    async def top_entity(self, ctx, cur):
        switch = random.choice([True, False])
        direction = random.choice([True, False])
        entity = "Stämme" if switch else "Spieler"
        top = 15 if switch else 100
        data = await load.random_id(ctx.world, top=top, amount=5, tribe=switch)
        base = f"Welcher dieser 5 {entity} hat"
        witcher = tr_options if switch else pl_options
        key = random.choice(list(witcher))
        listed = self.receive(data, key)
        value, obj = self.resolve(listed, key, reverse=direction)
        options = self.index_me_senpai([u.name for u in data])
        which = way[key][1] if direction else way[key][0]
        question = f"{base} {witcher[key].format(which)}\n\n{options}"
        answer = self.get_index(data, obj)
        lever = False if key in ("id", "rank") else True
        sweet = f"{pcv(value)} {stat[key]}" if lever else f"{stat[key]} {value}"
        answer_str = f"{obj.name} | {sweet}"

        await ctx.send(embed=self.quiz_embed(question, cur))
        result = await self.wait_for_answers(ctx, answer)
        return result, answer_str

    # Module Two
    async def general_ask(self, ctx, cur):
        question, answer = random.choice(load.msg["generalQuestion"])
        splitted = question.split(" ")
        mid = int((len(splitted) + 1) / 2)
        first, second = ' '.join(splitted[:mid]), ' '.join(splitted[mid:])
        question = f"{first}\n{second}"
        await ctx.send(embed=self.quiz_embed(question, f"{cur} (15s)"))
        result = await self.wait_for_answers(ctx, answer, 5)
        return result, answer

    # Module Three
    async def tribe_quiz(self, ctx, cur):
        tribes = await load.random_id(ctx.world, amount=5, top=15, tribe=True)
        positive = random.choice([True, False])
        target, rest = tribes[0], tribes[1:]
        no = " " if positive else " nicht "
        msg = f"Welcher dieser Spieler ist{no}bei `{target.name}`?"
        data = await self.get_player(ctx.world, tribes, positive)
        options = self.index_me_senpai(data[1])
        question = "{}\n{}".format(msg, options)
        answer = self.get_index(data[1], data[0])
        await ctx.send(embed=self.quiz_embed(question, cur))
        result = await self.wait_for_answers(ctx, answer)
        return result, data[0]

    # Module Four
    async def image_guess(self, ctx, rounds):
        state = random.choice([True, False])
        base_player = f"https://de{ctx.url}.die-staemme.de/guest.php?screen=info_"
        top = 15 if state else 100
        obj_list = await load.random_id(ctx.world, amount=top, top=top, tribe=state)
        insert = 'ally' if state else 'player'
        random.shuffle(obj_list)
        for obj in obj_list:
            result_link = f"{base_player}{insert}&id={obj.id}"
            resp = await self.bot.session.get(result_link)
            data = await resp.read()
            soup = BeautifulSoup(data, "html.parser")
            if state:
                result = soup.find("img")
            else:
                result = soup.find(alt="Profilbild")
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
                answer = self.get_index(options, obj)
                msg = "Welchem {} gehört dieses Bild?\n{}"
                formatted = self.index_me_senpai([u.name for u in options])
                embed = self.quiz_embed(msg.format(title, formatted), rounds)
                embed.set_image(url=result['src'])
                await ctx.send(embed=embed)
                break
        else:
            return None, None

        result = await self.wait_for_answers(ctx, answer)
        return result, obj.name

    async def game_engine(self, ctx, rounds):
        self.data[ctx.guild.id] = {}
        game_count = 0
        while game_count < rounds:
            game = random.choice(self.game_pool)
            cur = f"{game_count + 1} / {rounds}"
            result, answer = await game(ctx, cur)

            if result is None:
                break

            game_count += 1
            if not result:
                msg = "Leider hatte niemand die richtige Antwort.\n{}"
                msg = msg.format(f"** Lösung:** `{answer}`")
                await ctx.send(embed=discord.Embed(description=msg))
                continue

            for user in result:
                self.save_points(ctx.guild.id, user)

            won = self.two_per(result, "name")
            msg = f"Folgende User hatten die richtige Antwort:\n{won}"
            await ctx.send(embed=discord.Embed(description=msg))

            await asyncio.sleep(5)

        if game_count < rounds:
            await ctx.send(embed=error_embed("Game vorzeitig beendet!"))
        else:
            end_embed = await self.winner(ctx.guild.id)
            await ctx.send(embed=end_embed)

    @commands.command(name="quiz")
    @game_channel_only()
    async def quiz(self, ctx, rounds: int = 5):

        if ctx.guild.id in self.data:
            msg = "Auf diesem Server läuft bereits eine Runde."
            return await ctx.send(embed=error_embed(msg))

        if rounds < 5:
            msg = "Die Runden-Mindestanzahl beträgt 5!"
            return await ctx.send(embed=error_embed(msg))

        title = "**Das Spiel startet in Kürze!** (15s)"
        msg = "Pro Runde ein Zeitfenster von 10s,\n" \
              "nur die erste Antwort wird gewertet!"

        await ctx.send(embed=discord.Embed(title=title, description=msg))
        await asyncio.sleep(15)
        await self.game_engine(ctx, rounds)
        self.data.pop(ctx.guild.id)


def setup(bot):
    bot.add_cog(Quiz(bot))
