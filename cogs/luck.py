from discord.ext import commands
import asyncio
import typing
import random
import utils


class Casino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dice = {}
        self.slots = []
        self.cache = bot.cache
        self.number = self.cache.get('slotnumber')
        self.pot = self.cache.get('slotpot', 0)
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
        if ctx.guild.id in self.slots:
            return

        await self.bot.subtract_iron(ctx.author.id, 1000)

        number = 46860
        # number = random.randrange(10000, 50001)
        if number == self.number:
            self.number = random.randrange(10000, 50001)
            base = "Glückwunsch, du hast `{} Eisen` gewonnen!\nNeue Gewinnzahl: **{}**"
            msg = base.format(self.pot, self.number)
            await self.bot.update_iron(ctx.author.id, self.pot)
            self.cache.set('slotnumber', self.number)
            self.cache.set('slotpot', 0)
            self.pot = 0
            await ctx.send(msg)

        else:
            self.pot += 1000
            base = "Leider die falsche Zahl: **{}**\nAktueller Pot: `{}`\nGewinnzahl: **{}**"
            msg = base.format(number, utils.seperator(self.pot), self.number)
            self.cache.set('slotpot', self.pot)
            await ctx.send(msg)

        self.slots.append(ctx.guild.id)
        await asyncio.sleep(10)
        self.slots.remove(ctx.guild.id)

    @utils.game_channel_only()
    @commands.command(name="dice")
    async def dice_(self, ctx, argument: typing.Union[int, str]):
        data = self.dice.get(ctx.guild.id)
        if data is False:
            return

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
                try:
                    current = self.dice.get(ctx.guild.id)
                    if stamp == current['time']:
                        self.dice.pop(ctx.guild.id)
                        await self.bot.update_iron(ctx.author.id, argument)
                        await begin.edit(content="**Spielende:** Zeitüberschreitung(60s)")

                except TypeError:
                    return

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
                base = "**{.display_name}** {} | {} **{.display_name}**"
                arena = base.format(data['challenger'], *dices, ctx.author)

                players = [data['challenger'], ctx.author]
                if first_dice != second_dice:
                    if first_dice > second_dice:
                        winner, loser = players
                    else:
                        loser, winner = players

                    price = data['amount'] * 2
                    base = "{}\n**{}** hat beide Einsätze in Höhe von `{} Eisen` gewonnen."
                    msg = base.format(arena, winner.display_name, price)
                    await self.bot.update_iron(winner.id, price)

                else:

                    for player in players:
                        await self.bot.update_iron(player.id, data['amount'])
                        
                    base = "{}\n**Unentschieden**, die Einsätze gehen an die Spieler zurück."
                    msg = base.format(arena)

                await ctx.send(msg)
                self.dice[ctx.guild.id] = False
                await asyncio.sleep(15)
                self.dice.pop(ctx.guild.id)

        else:
            base = "Starte entweder ein Spiel `{0}dice <iron>` oder akzeptiere `{0}dice accept`"
            await ctx.send(base.format(ctx.prefix))


def setup(bot):
    bot.add_cog(Casino(bot))
