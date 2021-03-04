from discord.ext import commands
import asyncio
import discord
import typing
import random
import utils


class Casino(utils.DSGames):
    def __init__(self, bot):
        self.bot = bot
        self.type = 3
        self.dice = {}
        self.slots = []
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
    @commands.command(name="slots")
    async def slots_(self, ctx):
        await self.bot.subtract_iron(ctx.author.id, 1000)
        await self.slot_lock.wait()

        number = random.choice(self.numbers)
        if number == self.winning_number:
            self.slot_lock.clear()

            await self.bot.update_iron(ctx.author.id, self.pot)

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

            arguments = [(ctx.author.id, 1000), (self.winning_number, 1000)]
            async with self.bot.member_pool.acquire() as conn:
                await conn.executemany(query, arguments)

            base = "Leider die falsche Zahl: **{}**\n" \
                   "Aktueller Pot: `{}`\nGewinnzahl: **{}**"
            msg = base.format(number, utils.seperator(self.pot), self.winning_number)

        async with self.end_game(ctx, time=8):
            await ctx.send(msg)

    @utils.game_channel_only()
    @commands.command(name="slotistics")
    async def slotistics_(self, ctx):
        query = 'SELECT * FROM slot WHERE id = $1'
        async with self.bot.member_pool.acquire() as conn:
            cache = await conn.fetchrow(query, ctx.author.id)
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
        await ctx.send(embed=embed)

    @utils.game_channel_only()
    @commands.command(name="dice")
    async def dice_(self, ctx, argument: typing.Union[int, str]):
        data = self.get_game_data(ctx)

        if isinstance(argument, int):
            if not data:
                utils.valid_range(argument, 1000, 500000, "bet")
                await self.bot.subtract_iron(ctx.author.id, argument)

                stamp = ctx.message.created_at.timestamp()
                data = {'amount': argument, 'challenger': ctx.author, 'time': stamp}
                self.dice[ctx.guild.id] = data

                iron = utils.seperator(argument)
                base = "{} möchte eine Runde um `{} Eisen` spielen, akzeptiere mit `{}dice accept`"
                msg = base.format(f"**{ctx.author.display_name}**", iron, ctx.prefix)
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
                    await ctx.send("Bro... c'mon")
                    return

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

                    data['amount'] *= 2
                    iron = utils.seperator(data['amount'])
                    base = "{}**{}** hat beide Einsätze in Höhe von `{} Eisen` gewonnen."
                    msg = base.format(arena, winner.display_name, iron)

                else:
                    base = "{}**Unentschieden**, die Einsätze gehen an die Spieler zurück."
                    msg = base.format(arena)

                async with self.end_game(ctx):
                    await ctx.send(msg)
                    for player in players:
                        await self.bot.update_iron(player.id, data['amount'])

        else:
            base = "Starte entweder ein Spiel `{0}dice <iron>` oder akzeptiere `{0}dice accept`"
            await ctx.send(base.format(ctx.prefix))


def setup(bot):
    bot.add_cog(Casino(bot))
