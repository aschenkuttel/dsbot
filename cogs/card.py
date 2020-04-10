from discord.ext import commands
from bs4 import BeautifulSoup
import asyncio
import discord
import random
import utils


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

prop = {"name": "Spieler", "id": "ID", "rank": "Rang", "points": "Punkte",
        "villages": "Dörfer", "att_bash": "OFF", "def_bash": "DEF",
        "ut_bash": "UT", "all_bash": "Insgesamt"}


class Card(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = []
        self.quiz = {}
        self.tc = {}
        self.game_pool = [
            self.top_entity,
            self.general_ask,
            self.tribe_quiz,
            self.image_guess
        ]
        self.format = ('points', 'att_bash', 'def_bash',
                       'ut_bash', 'all_bash')

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
        data = await self.bot.fetch_random(ctx.server, top=top, amount=5, tribe=switch)
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
        sweet = f"{stat[key]} {value}" if lowest else f"{utils.pcv(value)} {stat[key]}"
        answer_str = f"{obj.name} | {sweet}"

        await ctx.send(embed=self.quiz_embed(question, cur))
        result = await self.wait_for_answers(ctx, index)
        return result, answer_str

    # Module Two
    async def general_ask(self, ctx, rounds):
        raw_question, answer = random.choice(self.bot.msg["generalQuestion"])
        splitted = raw_question.split(" ")
        mid = int((len(splitted) + 1) / 2)
        first_half, second_half = ' '.join(splitted[:mid]), ' '.join(splitted[mid:])
        question = f"{first_half}\n{second_half}"
        await ctx.send(embed=self.quiz_embed(question, f"{rounds} (15s)"))
        result = await self.wait_for_answers(ctx, answer, 5)
        return result, answer

    # Module Three
    async def tribe_quiz(self, ctx, rounds):
        tribes = await self.bot.fetch_random(ctx.server, amount=5, top=15, tribe=True)
        positive = random.choice([True, False])
        target, rest = tribes[0].id, [obj.id for obj in tribes[1:]]
        foo, bar = (rest, target) if positive else (target, rest)
        data = await self.bot.fetch_tribe_member(ctx.server, foo)

        fake_list = []
        while len(fake_list) < 4:
            player = random.choice(data)
            if player not in fake_list:
                fake_list.append(player)

        data = await self.bot.fetch_tribe_member(ctx.server, bar)
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
        obj_list = await self.bot.fetch_random(ctx.server, amount=top, top=top, tribe=state)
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

    def show_hand(self, hand, instruction, beginner=False):
        description = f"**Tribalcards | Deine Hand:**\n\n"
        for index, player in enumerate(hand):

            if beginner and index == 0:
                card = f"Oberster Karte:\n"
                values = []
                for key, value in prop.items():
                    pval = getattr(player, key)

                    if key in self.format:
                        pval = utils.pcv(pval)

                    pstat = f"**{value}:** `{pval}`"
                    values.append(pstat)

                result = utils.show_list(values, sep=" | ", line_break=3)
                card += f"{result}\n\n"

                base = "Du bist am Zug, wähle eine Eigenschaft mit {}play <property>"
                instruction = base.format(instruction)

            else:
                card = f"**{index + 1}**: {player.name}\n"

            description += card

        embed = discord.Embed(description=description)
        embed.set_footer(text=instruction)
        return embed

    @commands.command(name="quiz")
    @utils.game_channel_only()
    async def quiz(self, ctx, rounds: int = 5):
        if ctx.guild.id in self.quiz:
            msg = "Auf diesem Server läuft bereits eine Runde"
            return await ctx.send(embed=utils.error_embed(msg))

        if 5 <= rounds <= 20:
            msg = "Es müssen zwischen 5-20 Runden sein"
            return await ctx.send(embed=utils.error_embed(msg))

        title = "**Das Spiel startet in Kürze** (15s)"
        msg = "Pro Runde ein Zeitfenster von 10s,\n" \
              "nur die erste Antwort wird gewertet!"

        await ctx.send(embed=discord.Embed(title=title, description=msg))
        await asyncio.sleep(15)

        self.quiz[ctx.guild.id] = {}
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
                await ctx.send(embed=discord.Embed(description=msg, colour=0x992d22))
                continue

            winner = ""
            for index, obj in enumerate(result):

                if obj in self.quiz[ctx.guild.id]:
                    self.quiz[ctx.guild.id][obj] += 1
                else:
                    self.quiz[ctx.guild.id][obj] = 1

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
            msg = "Keine Antwort, Quiz vorzeitig beendet"
            await ctx.send(embed=utils.error_embed(msg))
        else:

            pool = self.quiz[ctx.guild.id]
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
            end_embed = self.quiz_embed(description, "Quiz beendet!", True)
            await ctx.send(embed=end_embed)

        self.quiz.pop(ctx.guild.id)

    @utils.game_channel_only()
    @commands.command(name="tribalcards", aliases=["tc"])
    async def tribalcards_(self, ctx, response=None):
        data = self.tc.get(ctx.guild.id)
        if data is False:
            return

        if ctx.author.id in self.cache and response is None:
            msg = f"Du bist bereits Spieler einer aktiven Tribalcard-Runde"
            return await ctx.send(embed=utils.error_embed(msg))

        if response and response.lower() == "join":
            if not data:
                base = "Aktuell ist keine Spielanfrage offen, starte mit `{}`"
                msg = f"{base.format(ctx.prefix)}tribalcards"

            elif len(data['players']) == 4:
                msg = "Es sind bereits 4 Spieler registriert"

            elif data.get('active'):
                names = [f"`{m.display_name}`" for m in data['players']]
                base = "Aktuell läuft bereits eine Runde auf dem Server, Teilnehmer:\n`{}`"
                msg = base.format(utils.show_list(names, line_break=4))

            else:
                data['players'][ctx.author] = {}
                amount = 4 - len(data['players'])

                if not amount:
                    free_spots = "`keine Plätze` mehr"
                else:
                    free_spots = f"noch `{amount} Plätze`"

                base = "**{}** nimmt am Spiel teil\n(Noch {} frei)"
                msg = base.format(ctx.author.display_name, free_spots)
                self.cache.append(ctx.author.id)

            await ctx.send(msg)

        elif response is None:
            self.cache.append(ctx.author.id)

            data = {'players': {ctx.author: {}}, 'id': ctx.message.id,
                    'played': {}, 'beginner': ctx.author, 'ctx': ctx}
            self.tc[ctx.guild.id] = data

            base = "**{}** möchte eine Runde **Tribalcards** spielen,\ntritt der Runde mit " \
                   "`{}tc join` bei:\n(2-4 Spieler, Spiel beginnt in 60s)"
            msg = base.format(ctx.author.display_name, ctx.prefix)
            begin = await ctx.send(msg)

            await asyncio.sleep(20)
            data['active'] = True

            player_num = len(data['players'])
            if player_num == 0:
                content = "Es wollte leider niemand mitspielen :/\n**Spiel beendet**"
                await begin.edit(content=content)
                return self.tc.pop(ctx.guild.id)

            amount = (3 - player_num) * player_num
            cards = await self.bot.fetch_random(ctx.server, amount=amount, top=100)
            for player, userdata in data['players'].items():
                hand = userdata['cards'] = []
                userdata['points'] = 0
                while len(hand) < amount / player_num:
                    card = cards.pop(0)
                    hand.append(card)

            hand = data['players'][ctx.author]['cards']
            embed = self.show_hand(hand, ctx.prefix, True)
            resp = await utils.silencer(ctx.author.send(embed=embed))

            if resp is False:
                base = "**{}** konnte keine private Nachricht geschickt werden,\n" \
                       "**Spiel beendet**"
                msg = base.format(ctx.author.display_name)
                await begin.edit(content=msg)
                self.tc.pop(ctx.guild.id)

            else:
                data['players'][ctx.author]['msg'] = resp
                await asyncio.sleep(3600)
                current = self.tc.get(ctx.guild.id)
                if current and current['id'] == data['id']:
                    self.tc.pop(ctx.guild.id)

    @commands.dm_only()
    @commands.command(name="play")
    async def play_(self, ctx, card_or_property):
        for guild_id, data in self.tc.items():
            if data is False:
                continue
            if ctx.author in data['players']:
                break
        else:
            msg = "Du befindest dich in keiner Tribalcards-Runde"
            return await ctx.send(msg)

        userdata = data['players'][ctx.author]
        if ctx.author in data['played']:
            msg = "Du hast bereits eine Karte gespielt, warte auf die anderen Spieler"
            await ctx.send(msg)

        elif data['beginner'] == ctx.author:
            for attribute, name in prop.items():
                if attribute == "name":
                    continue
                if name.lower() == card_or_property.lower():
                    break
            else:
                msg = "Die angegebene Eigenschaft gibt es leider nicht"
                return await ctx.send(msg, delete_after=10)

            if data.get('last') == attribute:
                msg = "Die angegebene Eigeschaft wurde bereits in der letzten Runde verglichen"
                return await ctx.send(msg, delete_after=10)

            card = userdata['cards'].pop(0)
            data['played'][ctx.author] = card
            data['attribute'] = attribute
            data['last'] = attribute

            for player, playerdata in data['players'].items():
                if ctx.author == player:
                    msg = "Deine Eigenschaft wurde registriert, warte auf die anderen Spieler"
                    embed = playerdata['msg'].embeds[0]
                    embed.set_footer(text=msg)
                    await playerdata['msg'].edit(embed=embed)

                else:
                    base = "{} möchte {} vergleichen, wähle deine Karte mit {}play <number>"
                    msg = base.format(ctx.author.display_name, name, data['ctx'].bot.prefix)
                    embed = self.show_hand(playerdata['cards'], msg)
                    await player.send(embed=embed)

        else:
            if not data['played']:
                base = "Du musst warten bis sich {} für eine Eigenschaft entschieden hat"
                msg = base.format(data['beginner'].display_name)
                return await ctx.send(msg, delete_after=10)

            try:
                index = int(card_or_property) - 1
                card = userdata['cards'].pop(index)
            except (ValueError, IndexError):
                msg = "Bitte gebe eine gültige Kartennummer an"
                return await ctx.send(msg, delete_after=10)

            played = data['played']
            players = data['players']
            played[ctx.author] = card
            if len(players) != len(played):
                msg = "Deine Karte wurde registriert, warte auf die anderen Spieler"
                embed = userdata['msg'].embeds[0]
                embed.set_footer(text=msg)
                await userdata['msg'].edit(embed=embed)

            else:
                # compare and possible end
                ranking = []
                for user, dsobj in played.items():
                    value = getattr(dsobj, data['attribute'])
                    ranking.append([user, value])

                reverse = data['attribute'] not in ("rank", "id")
                ranking.sort(key=lambda dc: dc[1], reverse=reverse)

                winner = []
                embed = discord.Embed()
                for user, value in ranking:
                    if not winner:
                        winner.append([user, value])
                        players[user]['points'] += 1
                    elif winner[0][1] == value:
                        winner.append([user, value])

                    points = players[user]['points']
                    dsobj = utils.escape(played[user].name)
                    name = f"Karte von {user.display_name} ({points}):"
                    value = f"**{prop[data['attribute']]} von {dsobj}:** `{utils.pcv(value)}`"
                    embed.add_field(name=name, value=value, inline=False)

                base = "Warte bis {} sich für eine Eigenschaft entschieden hat"

                player = "**, **".join([tup[0].display_name for tup in winner])
                plural = "hat" if len(winner) == 1 else "haben"
                title = f"**{player}** {plural} die Runde gewonnen"
                embed.title = title

                beginner = winner[0][0]
                for member, _ in ranking:
                    if member in [m[0] for m in winner]:
                        embed.colour = discord.Color.green()
                    else:
                        embed.colour = discord.Color.red()
                        if userdata['cards']:
                            embed.set_footer(text=base.format(beginner.display_name))

                    await member.send(embed=embed)

                if userdata['cards']:
                    played.clear()
                    data['beginner'] = beginner
                    beginner_data = players[beginner]

                    prefix = data['ctx'].bot.prefix
                    embed = self.show_hand(beginner_data['cards'], prefix, True)
                    msg = await beginner.send(embed=embed)
                    beginner_data['msg'] = msg

                else:
                    ranking = []
                    for member, playerdata in players.items():
                        ranking.append([member, playerdata['points']])

                    ranking.sort(key=lambda dc: dc[1], reverse=True)

                    winners = []
                    represent = ""
                    winner, highest = ranking[0]
                    for member, points in ranking:
                        base = "\n`{}` | **{}**"
                        represent += base.format(points, member.display_name)

                        if points == highest:
                            price = highest * 4000
                            await self.bot.update_iron(member.id, price)
                            represent += f" `[{price} Eisen]`"
                            winners.append(member.display_name)

                        self.cache.remove(member.id)

                    player = "**, **".join(winners)
                    plural = "hat" if len(winners) == 1 else "haben"
                    base = "**{}** {} das Tribalcards Spiel gewonnen!\n{}"
                    description = base.format(player, plural, represent)
                    embed = discord.Embed(description=description)
                    await data['ctx'].send(embed=embed)

                    self.tc[data['ctx'].guild.id] = False
                    await asyncio.sleep(15)
                    self.tc.pop(data['ctx'].guild.id)


def setup(bot):
    bot.add_cog(Card(bot))