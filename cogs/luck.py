from discord.ext import commands
import collections
import asyncio
import discord
import typing
import random
import utils


class Casino(utils.TribalGames):
    def __init__(self, bot):
        self.bot = bot
        self.dice = {}
        self.slots = []
        self.cache = bot.cache
        self.number = self.cache.get('slotnumber')
        self.pot = self.cache.get('slotpot', 0)
        slotistics = self.cache.get('slotistics')
        self.slotistics = collections.Counter(slotistics)
        self.dices = {
            1: "<:eins:692344708919459880>",
            2: "<:zwei:692344710534135808>",
            3: "<:drei:692344709196283924>",
            4: "<:vier:692344710575947817>",
            5: "<:fuenf:692344710169100319>",
            6: "<:sechs:692344710601113680>"
        }

    @utils.game_channel_only()
    @commands.command(name="slots")
    async def slots_(self, ctx):
        await self.bot.subtract_iron(ctx.author.id, 1000)

        number = random.randint(1, 9999)
        if number == self.number:
            self.number = random.randint(1, 9999)
            base = "Glückwunsch, du hast `{} Eisen` gewonnen!\nNeue Gewinnzahl: **{}**"
            self.cache.set('slotnumber', self.number, bulk=True)
            self.cache.set('slotistics', {}, bulk=True)
            msg = base.format(self.pot, self.number)
            self.slotistics = collections.Counter()
            self.pot = 0

            await self.bot.update_iron(ctx.author.id, self.pot)

        else:
            self.pot += 1000
            self.slotistics[str(ctx.author.id)] += 1000
            base = "Leider die falsche Zahl: **{}**\nAktueller Pot: `{}`\nGewinnzahl: **{}**"
            msg = base.format(number, utils.seperator(self.pot), self.number)

        self.cache.set('slotpot', self.pot, bulk=True)
        self.cache.set('slotistics', self.slotistics)

        async with self.cooldown(ctx, time=10):
            await ctx.send(msg)

    @commands.command(name="slotistics")
    async def slotistics_(self, ctx):
        statistics = self.cache.get('slotistics')
        value = statistics.get(str(ctx.author.id), 0)
        title = f"**Deine Ausgaben:** `{value} Eisen`"

        cache = [title]
        ranked = sorted(statistics.items(), key=lambda e: e[1], reverse=True)
        for index, (player_id, value) in enumerate(ranked[:5]):
            player = self.bot.get_user(int(player_id))
            name = player.name if player else "Unknown"
            row = f"**Rang {index + 1}:** `{value} Eisen` [{name}]"
            cache.append(row)

        await ctx.send(embed=discord.Embed(description="\n".join(cache)))

    @utils.game_channel_only()
    @commands.command(name="dice")
    async def dice_(self, ctx, argument: typing.Union[int, str]):
        data = self.get_game_data(ctx)

        if isinstance(argument, int):

            if not data:
                if not 1000 <= argument <= 500000:
                    raise utils.InvalidBet(1000, 500000)

                await self.bot.subtract_iron(ctx.author.id, argument)

                stamp = ctx.message.created_at.timestamp()
                data = {'amount': argument, 'challenger': ctx.author, 'time': stamp}
                self.dice[ctx.guild.id] = data

                base = "{} möchte eine Runde um `{} Eisen` spielen, akzeptiere mit `{}dice accept`"
                msg = base.format(f"**{ctx.author.display_name}**", argument, ctx.prefix)
                begin = await ctx.send(msg)

                await asyncio.sleep(60)

                current = self.dice.get(ctx.guild.id)
                if current and stamp == current['time']:
                    self.dice.pop(ctx.guild.id)
                    await self.bot.update_iron(ctx.author.id, argument)
                    await begin.edit(content="**Spielende:** Zeitüberschreitung(60s)")

            else:
                base = "Es ist bereits eine Anfrage offen, akzeptiere mit `{}dice accept`"
                await ctx.send(base.format(ctx.prefix))

        elif argument.lower() == "accept":

            if not data:
                base = "Aktuell gibt es keine offene Runde, starte mit `{}dice <1000-500000>`"
                await ctx.send(base.format(ctx.prefix))

            else:

                if ctx.author == data['challenger']:
                    return await ctx.send("Bro... c'mon")

                await self.bot.subtract_iron(ctx.author.id, data['amount'])

                first_dice = random.randint(1, 6)
                second_dice = random.randint(1, 6)

                dices = self.dices[first_dice], self.dices[second_dice]
                base = "**{.display_name}** {} | {} **{.display_name}**\n"
                arena = base.format(data['challenger'], *dices, ctx.author)

                players = [data['challenger'], ctx.author]
                if first_dice != second_dice:

                    if first_dice < second_dice:
                        players.reverse()

                    winner, loser = players
                    players.remove(loser)

                    price = data['amount'] * 2
                    base = "{}**{}** hat beide Einsätze in Höhe von `{} Eisen` gewonnen."
                    msg = base.format(arena, winner.display_name, price)

                else:
                    base = "{}**Unentschieden**, die Einsätze gehen an die Spieler zurück."
                    msg = base.format(arena)

                async with self.cooldown(ctx):
                    await ctx.send(msg)
                    for player in players:
                        await self.bot.update_iron(player.id, data['amount'])

        else:
            base = "Starte entweder ein Spiel `{0}dice <iron>` oder akzeptiere `{0}dice accept`"
            await ctx.send(base.format(ctx.prefix))


def setup(bot):
    bot.add_cog(Casino(bot))
