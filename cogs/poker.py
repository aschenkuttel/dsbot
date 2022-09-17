from discord import app_commands
from discord.ui import View
import asyncio
import discord
import random
import utils
import os


class BlackJack:
    def __init__(self, interaction, iron, deal):
        self.interaction = interaction
        self.player_hand, self.dealer_hand, self.card_cache = deal
        self.player_score = self.calculate_result(self.player_hand)
        self.dealer_score = self.calculate_result(self.dealer_hand[:1])
        self.initial_iron = self.iron = iron
        self.embed = None

    def present_cards(self, content=None, player=False):
        dealer_hand = self.dealer_hand[:1] + ["X"] if player else self.dealer_hand
        hand = f"`{'`**|**`'.join(self.player_hand)}` **[{self.player_score or 'RIP'}]**"
        dealer = f"`{'`**|**`'.join(dealer_hand)}` **[{self.dealer_score or 'RIP'}]**"

        if self.embed is None:
            self.embed = discord.Embed(color=discord.Color.red())
            self.embed.add_field(name="Deine Hand:", value=hand)
            self.embed.add_field(name="Dealer Hand:", value=dealer)
            self.embed.set_footer(text="10s Cooldown nach Abschluss der Runde")

        else:
            self.embed.set_field_at(0, name="Deine Hand:", value=hand)
            self.embed.set_field_at(1, name="Dealer Hand:", value=dealer)

            if content is not None:
                self.embed.description = content

        return self.embed

    def draw_card(self, player):
        new_card = random.choice(self.card_cache)
        self.card_cache.remove(new_card)

        if player is True:
            self.player_hand.append(new_card)
            return self.calculate_entity(player=True)
        else:
            self.dealer_hand.append(new_card)
            return self.calculate_entity(player=False)

    def calculate_entity(self, player):
        if player is True:
            self.player_score = self.calculate_result(self.player_hand)
            return self.player_score
        else:
            self.dealer_score = self.calculate_result(self.dealer_hand)
            return self.dealer_score

    def calculate_result(self, cards):
        card_signs = [c[:-1] for c in cards]
        values = {"J": 10, "Q": 10, "K": 10, "A": 11}
        count = 0

        for card in card_signs:
            spec = values.get(card)
            num = spec or int(card)
            count += num

        last = card_signs.count("A")
        for index in range(last + 1):
            if count <= 21:
                return count
            elif index != last:
                count -= 10

        return False


class Poker(utils.DSGames):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.type = 3
        self.dice = {}
        self.slots = []
        self.blackjack = {}
        self.videopoker = {}
        self.signs = ["h", "d", "c", "s"]
        self.numbers = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        self.full_set = [num + card for num in self.numbers for card in self.signs]
        self.converse = {"J": 11, "Q": 12, "K": 13, "A": 14}
        self.payout = {
            "Paar": 1.5, "Doppel-Paar": 2, "Drilling": 7.5,
            "Straße": 20, "Flush": 40, "Full House": 60,
            "Vierling": 100, "Straight Flush": 250, "Royal Flush": 500
        }
        self.pot = 0
        self.winning_number = None
        self.numbers = list(range(1, 10000))
        self.slot_lock = asyncio.Event()
        self.slot_lock.set()
        self.dices = {
            1: "<:eins:692344708919459880>",
            2: "<:zwei:692344710534135808>",
            3: "<:drei:692344709196283924>",
            4: "<:vier:692344710575947817>",
            5: "<:fuenf:692344710169100319>",
            6: "<:sechs:692344710601113680>"
        }
        self.bot.loop.create_task(self.slot_setup())

    def deal(self, interaction, iron, bj=False):
        card_amount = 2 if bj else 5

        card_pack = []
        packs = 6 if bj else 1
        for _ in range(packs):
            card_pack.extend(self.full_set)

        hands = ['hand']

        if bj:
            hands.append('dealer')

        data = {}
        for key in hands:
            cards = []
            for _ in range(card_amount):
                card = random.choice(card_pack)
                cards.append(card)
                card_pack.remove(card)

            data[key] = cards

        data['cards'] = card_pack

        if bj:
            return data['hand'], data['dealer'], data['cards']

        else:
            stamp = interaction.created_at.timestamp()
            extra = {'author': interaction.user, 'iron': iron, 'time': stamp}
            data.update(extra)
            self.videopoker[interaction.guild.id] = data
            return data['hand'], stamp

    async def player_wins(self, interaction, game, bj=False):
        price = int(game.iron * (2.5 if bj else 1))

        greet = "Blackjack" if bj else "Glückwunsch"
        msg = f"{greet}, du gewinnst {utils.seperator(price)} Eisen!"
        embed = game.present_cards(content=msg)
        embed.colour = discord.Color.green()

        async with self.end_game(game.interaction):
            await self.bot.update_iron(game.interaction.user.id, price)
            await interaction.edit_original_response(embed=embed, view=None)

    async def dealer_wins(self, interaction, game, tie=False, bj=False):
        if tie:
            base = "Unentschieden, du erhältst deinen Einsatz zurück"
            await self.bot.update_iron(interaction.user.id, game.iron)

        else:
            word = "Blackjack" if bj else "RIP"
            base = f"{word}, du hast deinen Einsatz verloren"

        embed = game.present_cards(content=base)
        embed.colour = discord.Color.red()

        async with self.end_game(game.interaction):
            await interaction.edit_original_response(embed=embed, view=None)

    def check_result(self, cards):
        card_numbers = [c[:-1] for c in cards]
        card_signs = [c[-1] for c in cards]

        street = []
        con = self.converse.copy()
        for _ in range(("A" in card_numbers) + 1):
            sequence = []
            for num in card_numbers:
                spec = con.get(num, num)
                sequence.append(int(spec))

            sequence.sort()
            begin, end = min(sequence), max(sequence)
            if sequence == list(range(begin, end + 1)):
                street = sequence
                break
            else:
                con["A"] = 1

        if len(set(card_signs)) == 1:
            if street and sum(street) == 60:
                return "Royal Flush"
            elif street:
                return "Straight Flush"
            else:
                return "Flush"

        elif street:
            return "Straße"

        else:
            hands = {'41': "Vierling", '32': "Full House",
                     '311': "Drilling", '221': "Doppel-Paar",
                     '2111': "Paar"}

            occurs = []
            for num in set(card_numbers):
                amount = card_numbers.count(num)
                occurs.append(str(amount))

            occurs.sort(reverse=True)
            return hands.get("".join(occurs))

    async def blackjack_callback(self, move, interaction):
        await interaction.response.defer()
        possible_moves = ["hit", "stand", "double"]
        game = self.blackjack.get(interaction.guild.id)

        if game is None:
            return

        if move in ("hit", "double"):

            if len(possible_moves) == 3:
                possible_moves.remove("double")

            if move == "double":
                response = await self.bot.subtract_iron(interaction.user.id, game.initial_iron, supress=True)

                if response is None:
                    error = "\nDu hast nicht genügend Eisen..."
                    game.embed.description += error
                    await interaction.response.edit_message(embed=game.embed)
                    return

                game.iron *= 2

            score = game.draw_card(player=True)

            if score is False:
                game.calculate_entity(player=False)
                await self.dealer_wins(interaction, game)
                return

            elif score < 21:
                embed = game.present_cards(player=True)
                await game.interaction.edit_original_response(embed=embed)
                return
            else:
                move = "stand"

        if move == "stand":
            dealer_score = game.calculate_entity(player=False)

            while True:
                if dealer_score == 21 and len(game.dealer_hand) == 2:
                    await self.dealer_wins(interaction, game, bj=True)
                    return

                elif dealer_score is False:
                    await self.player_wins(interaction, game)
                    return

                elif dealer_score >= 17:
                    if game.player_score > dealer_score:
                        await self.player_wins(interaction, game)
                    else:
                        tie = game.player_score == dealer_score
                        await self.dealer_wins(interaction, game, tie=tie)
                    return

                dealer_score = game.draw_card(player=False)
                embed = game.present_cards()
                await game.interaction.edit_original_response(embed=embed)
                await asyncio.sleep(1.5)

    vp = app_commands.Group(name="vp", description="Videopoker Spiel für Eisen")

    @utils.game_channel_only()
    @vp.command(name="start", description="Starte eine Runde Videopoker")
    async def vp_start(self, interaction, iron: app_commands.Range[int, 100, 2000] = 2000):
        data = self.get_game_data(interaction)

        if data:
            name = data['author'].display_name
            await interaction.response.send_message(f"**{name}** spielt gerade...")

        else:
            await self.bot.subtract_iron(interaction.user.id, iron)

            cards, stamp = self.deal(interaction, iron)
            base = "Deine Karten: `{}`{}Ersetze diese mit **/vp draw 1-5**"
            msg = base.format(" ".join(cards), os.linesep)
            await interaction.response.send_message(msg)

            await asyncio.sleep(60)

            current = self.videopoker.get(interaction.guild.id)
            if current and stamp == current.get('time'):
                await interaction.edit_original_response(content="**Spielende:** Zeitüberschreitung(60s)")
                self.videopoker.pop(interaction.guild.id)

    @utils.game_channel_only()
    @vp.command(name="draw", description="Ersetze keine oder bis zu allen Karten deiner Videopoker Runde")
    async def vp_draw(self, interaction, cards: str = None):
        data = self.get_game_data(interaction)

        if data is None:
            msg = "Du musst zuerst eine Runde mit /vp start <100-2000> beginnen"
            await interaction.response.send_message(msg)
            return

        elif data['author'] != interaction.user:
            name = data['author'].display_name
            await interaction.response.send_message(f"**{name}** spielt gerade...")
            return

        if cards:
            try:
                if len(cards) > 5:
                    raise ValueError
                for num in set(cards):
                    num = int(num)
                    if not (0 < num < 6):
                        raise ValueError

                    new_card = random.choice(data['cards'])
                    data['hand'][num - 1] = new_card
                    data['cards'].remove(new_card)

            except ValueError:
                base = "**Fehlerhafte Eingabe**{}Beispiel: /vp draw 134"
                await interaction.response.send_message(base.format(os.linesep))
                return

            card_rep = f"Deine neuen Karten: `{' '.join(data['hand'])}`"
        else:
            card_rep = f"Du behältst deine Karten: `{' '.join(data['hand'])}`"

        result = self.check_result(data['hand'])

        if result:
            pronoun = interaction.lang.vp[result]
            amount = int(data['iron'] * self.payout[result])
            base = "{0}{1}Du hast {2} **{3}**: `{4} Eisen` gewonnen!{1}(10s Cooldown)"
            msg = base.format(card_rep, os.linesep, pronoun, result, amount)
            await self.bot.update_iron(interaction.user.id, amount)

        else:
            base = "{}{}**Du hast nichts und damit deinen Einsatz verloren** (10s Cooldown)"
            msg = base.format(card_rep, os.linesep)

        async with self.end_game(interaction):
            await interaction.response.send_message(msg)

    @utils.game_channel_only()
    @app_commands.command(name="bj", description="Blackjack gegen den Bot")
    async def blackjack(self, interaction, iron: app_commands.Range[int, 100, 50000] = 50000):
        game = self.get_game_data(interaction)

        if game is not None:
            player = game['interaction'].user
            msg = f"**{player.display_name}** spielt gerade..."
            await interaction.response.send_message(msg, ephemeral=True)
            return

        await self.bot.subtract_iron(interaction.user.id, iron)
        response = self.deal(interaction, iron, bj=True)
        game = BlackJack(interaction, iron, response)

        if game.player_score == 21:
            dealer_score = game.calculate_entity(player=False)

            if dealer_score == 21:
                await self.dealer_wins(interaction, game, tie=True)
            else:
                await self.player_wins(interaction, game, bj=True)

        else:
            view = View()

            for move in ("Hit", "Stand", "Double"):
                button = utils.DSButton(
                    custom_id=move.lower(),
                    label=move,
                    row=0,
                    _callback=self.blackjack_callback,
                    style=discord.ButtonStyle.success
                )

                view.add_item(button)

            self.blackjack[interaction.guild.id] = game
            embed = game.present_cards(player=True)
            await interaction.response.send_message(embed=embed, view=view)

    async def slot_setup(self):
        await self.bot.wait_until_unlocked()
        async with self.bot.member_pool.acquire() as conn:
            query = 'SELECT * FROM slot WHERE id < 10000'
            cache = await conn.fetchrow(query)

            if cache is None:
                number = random.randint(1, 9999)
                query = 'INSERT INTO slot(id, amount) VALUES($1, $2)'
                await conn.execute(query, number, 5000)
                self.winning_number = number
                self.pot = 5000

            else:
                self.winning_number = cache['id']
                self.pot = cache['amount']

            amount = (self.pot - 5000) / 1000
            if amount > 9499:
                amount = 9499

            while len(self.numbers) != 9999 - amount:
                number = random.choice(self.numbers)
                if number != self.winning_number:
                    self.numbers.remove(number)

    @utils.game_channel_only()
    @app_commands.command(name="slots", description="Ziehe eine zufällige Zahl und gewinne mit etwas Glück den Pot")
    async def slots(self, interaction):
        await self.bot.subtract_iron(interaction.user.id, 1000)
        await self.slot_lock.wait()

        number = random.choice(self.numbers)
        if number == self.winning_number:
            self.slot_lock.clear()

            await self.bot.update_iron(interaction.user.id, self.pot)

            self.numbers = list(range(1, 10000))
            new_number = random.choice(self.numbers)
            query = 'INSERT INTO slot(id, amount) VALUES($1, $2);'

            async with self.bot.member_pool.acquire() as conn:
                await conn.execute('TRUNCATE TABLE slot')
                await conn.execute(query, new_number, 5000)

            self.pot = 5000
            self.winning_number = new_number
            base = "Glückwunsch, du hast `{} Eisen` gewonnen!\nNeue Gewinnzahl: **{}**"
            msg = base.format(self.pot, self.winning_number)
            self.slot_lock.set()

        else:
            self.pot += 1000
            self.numbers.remove(number)

            query = 'INSERT INTO slot(id, amount) VALUES($1, $2) ' \
                    'ON CONFLICT (id) DO UPDATE SET amount = slot.amount + $2'

            arguments = [(interaction.user.id, 1000), (self.winning_number, 1000)]
            async with self.bot.member_pool.acquire() as conn:
                await conn.executemany(query, arguments)

            msg = f"Leider die falsche Zahl: **{number}**\n" \
                  f"Aktueller Pot: `{utils.seperator(self.pot)}`\n" \
                  f"Gewinnzahl: **{self.winning_number}**"

        async with self.end_game(interaction, time=8):
            await interaction.response.send_message(msg)

    @utils.game_channel_only()
    @app_commands.command(name="slotistics", description="Statistiken des Eisens für den Slots Command")
    async def slotistics(self, interaction):
        query = 'SELECT * FROM slot WHERE id = $1'
        async with self.bot.member_pool.acquire() as conn:
            cache = await conn.fetchrow(query, interaction.user.id)
            if cache is None:
                own_value = 0
            else:
                own_value = cache['amount']

            query = 'SELECT * FROM slot ORDER BY amount DESC LIMIT 6'
            slot_rank = await conn.fetch(query)

        title = f"**Deine Ausgaben:** `{own_value} Eisen`"

        cache = [title]
        for index, row in enumerate(slot_rank[1:]):
            player = self.bot.get_member(row['id'])
            name = player.name if player else "Unknown"
            row = f"**Rang {index + 1}:** `{row['amount']} Eisen` [{name}]"
            cache.append(row)

        embed = discord.Embed(description="\n".join(cache))
        await interaction.response.send_message(embed=embed)

    dice = app_commands.Group(name="dice", description="Würfelspiel um Eisen")

    @utils.game_channel_only()
    @dice.command(name="start", description="Beginne ein Würfelspiel, die höhere Zahl gewinnt!")
    async def dice_start(self, interaction, iron: app_commands.Range[int, 1000, 500000]):
        data = self.get_game_data(interaction)

        if not data:
            await self.bot.subtract_iron(interaction.user.id, iron)

            stamp = interaction.created_at.timestamp()
            data = {'amount': iron, 'challenger': interaction.user, 'time': stamp}
            self.dice[interaction.guild.id] = data

            base = "{} möchte eine Runde um `{} Eisen` spielen, akzeptiere mit `/dice accept`"
            msg = base.format(f"**{interaction.user.display_name}**", utils.seperator(iron))
            await interaction.response.send_message(msg)
            await asyncio.sleep(60)

            current = self.dice.get(interaction.guild.id)
            if current and stamp == current['time']:
                self.dice.pop(interaction.guild.id)
                await self.bot.update_iron(interaction.user.id, iron)
                await interaction.edit_original_response(content="**Spielende:** Zeitüberschreitung(60s)")

        else:
            msg = "Es ist bereits eine Anfrage offen, akzeptiere mit `/dice accept`"
            await interaction.response.send_message(msg)

    @utils.game_channel_only()
    @dice.command(name="accept", description="Akzeptiere ein laufendes Dice Game")
    async def dice_accept(self, interaction):
        data = self.get_game_data(interaction)

        if not data:
            msg = "Aktuell gibt es keine offene Runde, starte mit `/dice <1000-500000>`"
            await interaction.response.send_message(msg)

        else:

            if interaction.user == data['challenger']:
                await interaction.response.send_message("Bro... c'mon")
                return

            await self.bot.subtract_iron(interaction.user.id, data['amount'])

            first_dice = random.randint(1, 6)
            second_dice = random.randint(1, 6)

            dices = self.dices[first_dice], self.dices[second_dice]
            base = "**{.display_name}** {} | {} **{.display_name}**\n"
            arena = base.format(data['challenger'], *dices, interaction.user)

            players = [data['challenger'], interaction.user]
            if first_dice != second_dice:

                if first_dice < second_dice:
                    players.reverse()

                winner, loser = players
                players.remove(loser)

                data['amount'] *= 2
                iron = utils.seperator(data['amount'])
                base = "{}**{}** hat beide Einsätze in Höhe von `{} Eisen` gewonnen."
                msg = base.format(arena, winner.display_name, iron)

            else:
                base = "{}**Unentschieden**, die Einsätze gehen an die Spieler zurück."
                msg = base.format(arena)

            async with self.end_game(interaction):
                await interaction.response.send_message(msg)
                for player in players:
                    await self.bot.update_iron(player.id, data['amount'])


async def setup(bot):
    await bot.add_cog(Poker(bot))
