from utils import game_channel_only
from discord.ext import commands
import asyncio
import random


l1 = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
l2 = ["h", "d", "c", "s"]
full_set = [card + num for num in l2 for card in l1]
spec = {"J": 11, "Q": 12, "K": 13, "A": 14, "a": 1}
wins = {"Paar": 1.5, "Doppel-Paar": 2, "Drilling": 7.5, "Straße": 20,
        "Flush": 40, "Full House": 60, "Vierling": 100,
        "Straight Flush": 250, "Royal Flush": 500}
win_msg = {"Paar": "ein", "Doppel-Paar": "ein", "Drilling": "einen",
           "Straße": "eine", "Flush": "einen", "Full House": "ein",
           "Vierling": "einen", "Straight Flush": "'nen fucking",
           "Royal Flush": "legit einen..."}


class VP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = {}

    def cuteverter(self, card_list):
        cute = [card for card in card_list.values()]
        return cute

    async def game_end(self, guild_id):
        self.data[guild_id] = False
        await asyncio.sleep(15)
        self.data.pop(guild_id)

    def starter(self, guild_id, player_id, cash):
        cards = {}
        card_cache = full_set.copy()
        while len(cards) < 5:
            card = random.choice(full_set)
            if card not in cards.values():
                cards["{}".format(len(cards) + 1)] = card
                card_cache.remove(card)
        data = {"cards": cards, "player": player_id, "bet": cash,
                "game_id": random.getrandbits(128), "cache": card_cache}
        self.data.update({guild_id: data})

    def card_replace(self, guild_id, card_numbers):
        if card_numbers == 0:
            return
        card_list = self.data[guild_id]["cards"]
        cache = self.data[guild_id]["cache"]
        for num in set(card_numbers):
            new = random.choice(cache)
            if new not in card_list.values():
                card_list[num] = new
                cache.remove(new)

    def street_checker(self, nums):
        street_check = []
        for index, nm in enumerate(nums):

            if index == 0:
                continue
            street_check.append(abs(nums[index - 1] - nm))

        if street_check.count(1) == 4:
            return True
        else:
            return False

    def num_lis(self, checker):
        num = []
        for card in checker:
            try:
                num.append(int(card[0]))
            except ValueError:
                num.append(spec[card[0]])
        num.sort()
        return num

    def check_result(self, card_list):
        checker = [(card[:-1], card[-1]) for card in card_list.values()]
        if len(set([card[1] for card in checker])) == 1:
            num = self.num_lis(checker)
            street = self.street_checker(num)
            if street and set(num) == {10, 11, 12, 13, 14}:
                return "Royal Flush"
            if street:
                return "Straight Flush"
            else:
                try:
                    num_x = num
                    num_x.remove(14)
                    num_x.append(1)
                    num_x.sort()
                    street = self.street_checker(num_x)
                    if street:
                        return "Straight Flush"
                    else:
                        return "Flush"
                except ValueError:
                    return "Flush"

        num = self.num_lis(checker)
        street = self.street_checker(num)
        if street:
            return "Straße"
        else:
            try:
                num_x = num
                num_x.remove(14)
                num_x.append(1)
                num_x.sort()
                street = self.street_checker(num_x)
                if street:
                    return "Straße"
            except ValueError:
                pass

        p_check = []
        check = [card[0] for card in checker]
        for num in check:
            if check.count(num) == 4:
                p_check.append(4)
            if check.count(num) == 3:
                p_check.append(3)
            if check.count(num) == 2:
                p_check.append(2)

        if p_check.count(4) == 4:
            return "Vierling"
        if p_check.count(3) == 3 and p_check.count(2) == 2:
            return "Full House"
        if p_check.count(3) == 3:
            return "Drilling"
        if p_check.count(2) == 4:
            return "Doppel-Paar"
        if p_check.count(2) == 2:
            return "Paar"

        return False

    @commands.command(aliases=["videopoker"])
    @game_channel_only()
    async def vp(self, ctx, money: int):

        if money > 2000 or money < 100:
            await ctx.send("Fehlerhafte Eingabe: `!vp <100-2000>`")
            return

        credit = await self.bot.fetch_user_data(ctx.author.id)
        if credit - money < 0:
            await ctx.send("Du kannst nicht um Geld spielen welches du nicht besitzt...")
            return

        if ctx.guild.id in self.data:
            if self.data[ctx.guild.id] is False:
                return
            player = ctx.bot.get_user(self.data[ctx.guild.id]['player']).name
            await ctx.send(f"`{player}` spielt bereits auf dem Server eine Runde `!vp`")
            return

        self.starter(ctx.guild.id, ctx.author.id, money)
        cards = ' '.join(self.cuteverter(self.data[ctx.guild.id]['cards']))
        start_msg = await ctx.send(f"Deine Karten: `{cards}` - "
                                   f"Ersetze Karten mit `!draw 1-5`")
        game_id = self.data[ctx.guild.id]["game_id"]
        await asyncio.sleep(60)
        if ctx.guild.id in self.data:
            if self.data[ctx.guild.id] is not False:
                if self.data[ctx.guild.id]["game_id"] == game_id:
                    await start_msg.edit(
                        content="Die maximale Wartezeit von einer Minute"
                                " des `!vp` Commands ist abgelaufen.")
                    bet = self.data[ctx.guild.id]['bet']
                    await self.bot.save_user_data(ctx.author.id, - bet)
                    await self.game_end(ctx.guild.id)

    @commands.command(aliases=["ziehen"])
    @game_channel_only()
    async def draw(self, ctx, cards=""):

        # --- Various Checks --- #
        if ctx.guild.id not in self.data:
            await ctx.send("Du musst erst eine Runde mit `!vp <100-2000>` starten!")
            return
        if self.data[ctx.guild.id] == 0:
            return
        if ctx.author.id != self.data[ctx.guild.id]['player']:
            player = self.bot.get_user(self.data[ctx.guild.id]['player'])
            await ctx.send(f"`{player.display_name}` spielt bereits "
                           f"auf dem Server eine Runde `!vp`")
            return

            # --- Card Replace Handler --- #
        if cards:
            if len(cards) > 5 or len(cards) - len(set(cards)) != 0:
                await ctx.send("Fehlerhafte Eingabe - Bsp: `!draw 135`")
                return
            for num in cards:
                try:
                    if int(num) > 5 or int(num) < 1:
                        await ctx.send("Fehlerhafte Eingabe - Bsp: `!draw 125`")
                        return
                    else:
                        continue
                except ValueError:
                    await ctx.send("Fehlerhafte Eingabe - Bsp: `!draw 14`")
                    return
            self.card_replace(ctx.guild.id, [num for num in cards])

        n_cards = ' '.join(self.cuteverter(self.data[ctx.guild.id]['cards']))
        if cards:
            end_msg = f"Deine neuen Karten: `{n_cards}`"
        else:
            end_msg = f"Du behältst deine Karten: `{n_cards}`"

        # --- Result Check --- #
        result = self.check_result(self.data[ctx.guild.id]['cards'])
        if not result:
            await ctx.send(f"{end_msg}\n**Du hast nichts und damit"
                           f" deinen Einsatz verloren** *(15s Cooldown)*")
            # --- Money Lose --- #
            await self.bot.save_user_data(ctx.author.id, -self.data[ctx.guild.id]['bet'])
            return await self.game_end(ctx.guild.id)

        # --- Result if WON --- #
        result_msg = f"{win_msg[result]} **{result}**"
        amount_won = int(self.data[ctx.guild.id]['bet'] * wins[f"{result}"])
        await ctx.send(f"{end_msg}\nDu hast {result_msg} - `{amount_won}"
                       f" Eisen` gewonnen *(15s Cooldown)*")
        bet = self.data[ctx.guild.id]['bet']
        await self.bot.save_user_data(ctx.author.id, amount_won - bet)
        await self.game_end(ctx.guild.id)


def setup(bot):
    bot.add_cog(VP(bot))
