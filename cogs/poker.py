from utils import game_channel_only
from discord.ext import commands
import asyncio
import random
import os


signs = ["h", "d", "c", "s"]
numbers = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
full_set = [num + card for num in numbers for card in signs]
converse = {"J": 11, "Q": 12, "K": 13, "A": 14}
payout = {"Paar": 1.5, "Doppel-Paar": 2, "Drilling": 7.5, "Straße": 20, "Flush": 40,
          "Full House": 60, "Vierling": 100, "Straight Flush": 250, "Royal Flush": 500}


class VP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = {}

    def dealer(self, ctx, cash, timestamp):
        card_pack = full_set.copy()
        cards = []

        for _ in range(5):
            card = random.choice(card_pack)
            cards.append(card)
            card_pack.remove(card)

        data = {'cards': cards, 'player': ctx.author, 'bet': cash,
                'time': timestamp, 'cache': card_pack}
        self.data[ctx.guild.id] = data
        return " ".join(cards)

    def check_result(self, cards):
        card_numbers = [c[:-1] for c in cards]
        card_signs = [c[-1] for c in cards]

        street = []
        con = converse.copy()
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

        # Flush Cases
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

    @game_channel_only()
    @commands.command(name="vp", aliases=["videopoker"])
    async def vp_(self, ctx, money: int):
        if not 100 < money <= 2000:
            msg = "Der Einsatz muss zwischen 100-2000 Eisen betragen."
            return await ctx.send(msg)

        credit = await self.bot.fetch_user_data(ctx.author.id)
        if credit - money < 0:
            msg = "Du verfügst nicht über ausreichend Eisen, Bro..."
            return await ctx.send(msg)

        data = self.data.get(ctx.guild.id)
        if data is False:
            return

        elif data:
            name = data['player'].display_name
            msg = f"`{name}` ist noch in einer aktiven Runde."
            await ctx.send(msg)

        else:
            timestamp = ctx.message.created_at.timestamp()
            cards = self.dealer(ctx, money, timestamp)
            msg = "Deine Karten: `{}`\n" \
                  "Ersetze diese mit **{}draw 1-5**"
            begin = await ctx.send(msg.format(cards, ctx.prefix))

            await asyncio.sleep(60)
            current = self.data.get(ctx.guild.id)
            if not current:
                return

            elif current['player'] != ctx.author:
                return

            elif timestamp != current['time']:
                return

            else:
                await begin.edit(content="Spielende: Zeitüberschreitung(60s)")
                await self.bot.save_user_data(ctx.author.id, - current['bet'])

    @commands.command(name="draw", aliases=["ziehen"])
    async def draw_(self, ctx, cards=None):
        data = self.data.get(ctx.guild.id)
        if data is False:
            return

        elif not data:
            msg = "Du musst zuerst eine Runde mit {}vp <100-2000> beginnen."
            await ctx.send(msg.format(ctx.prefix))

        elif data['player'] != ctx.author:
            name = data['player'].display_name
            await ctx.send(f"{name} ist bereits in einer Runde.")

        else:
            if cards:
                try:
                    if len(cards) > 5:
                        raise ValueError
                    for num in set(cards):
                        num = int(num)
                        if not (0 < num < 6):
                            raise ValueError

                        new_card = random.choice(data['cache'])
                        data['cards'][num - 1] = new_card
                        data['cache'].remove(new_card)

                except ValueError:
                    base = "**Fehlerhafte Eingabe**{}Beispiel: {}draw 134"
                    msg = base.format(os.linesep, ctx.prefix)
                    return await ctx.send(msg)

                card_rep = f"Deine neuen Karten: `{' '.join(data['cards'])}`"
            else:
                card_rep = f"Du behältst deine Karten: `{' '.join(data['cards'])}`"

            result = self.check_result(data['cards'])
            if result:
                pronoun = self.bot.msg['vpMessage'][result]
                amount = int(data['bet'] * payout[result])
                base = "{0}{1}Du hast {2} **{3}**: `{4} Eisen` gewonnen{1}(15s Cooldown)"
                msg = base.format(card_rep, os.linesep, pronoun, result, amount)

            else:
                amount = 0
                base = "{}{}**Du hast nichts und damit deinen Einsatz verloren** (15s Cooldown)"
                msg = base.format(card_rep, os.linesep)

            await self.bot.save_user_data(ctx.author.id, amount - data['bet'])
            await ctx.send(msg)

            self.data[ctx.guild.id] = False
            await asyncio.sleep(15)
            self.data.pop(ctx.guild.id)


def setup(bot):
    bot.add_cog(VP(bot))
