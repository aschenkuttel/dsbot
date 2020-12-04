from utils import MemberConverter, MissingRequiredKey, seperator
from discord.ext import commands
import discord


class Money(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.type = 3

    async def send_ranking(self, ctx, iterable, dead=False):
        data = []
        for index, record in enumerate(iterable, 1):
            player = self.bot.get_user(record['id'])

            if not dead and player is None:
                continue

            if player is not None:
                name = player.display_name
            else:
                name = "Unknown"

            base = "**Rang {}:** `{} Eisen` [{}]"
            msg = base.format(index, seperator(record['amount']), name)
            data.append(msg)

            if len(data) == 5:
                break

        if data:
            embed = discord.Embed(description="\n".join(data))
            embed.colour = discord.Color.blue()
            await ctx.send(embed=embed)

        else:
            msg = "Aktuell gibt es keine gespeicherten Scores"
            await ctx.send(msg)

    @commands.group(name="iron", invoke_without_command=True)
    async def iron(self, ctx):
        if not ctx.message.content.endswith("iron"):
            raise MissingRequiredKey(("ranking", "send"))

        money, rank = await self.bot.fetch_iron(ctx.author.id, True)
        base = "**Dein Speicher:** `{} Eisen`\n**Globaler Rang:** `{}`"
        await ctx.send(base.format(seperator(money), rank))

    @iron.command(name="send")
    @commands.cooldown(1, 30.0, commands.BucketType.user)
    async def send_(self, ctx, amount: int, *, user: MemberConverter):
        if not 1000 <= amount <= 50000:
            await ctx.send("Du kannst nur `1000-50.000 Eisen` überweisen")
            ctx.command.reset_cooldown(ctx)

        else:
            await self.bot.subtract_iron(ctx.author.id, amount)
            await self.bot.update_iron(user.id, amount)

            base = "Du hast `{}` erfolgreich `{} Eisen` überwiesen (30s Cooldown)"
            await ctx.send(base.format(user.display_name, seperator(amount)))

    @iron.command(name="ranking")
    async def rank_(self, ctx):
        query = 'SELECT * FROM iron_data ORDER BY amount DESC LIMIT 20'
        async with self.bot.ress.acquire() as conn:
            cache = await conn.fetch(query)

        await self.send_ranking(ctx, cache)

    @iron.command(name="local")
    async def local_(self, ctx, member: MemberConverter = None):
        f_query = 'SELECT * FROM iron_data WHERE amount >= ' \
                  '(SELECT amount FROM iron_data WHERE id = $1) ' \
                  'ORDER BY amount ASC LIMIT 3'

        s_query = 'SELECT * FROM iron_data ' \
                  'WHERE amount < $1 ' \
                  'ORDER BY amount DESC LIMIT $2'

        async with self.bot.ress.acquire() as conn:
            member = member or ctx.author
            over = await conn.fetch(f_query, member.id)

            if not over:
                msg = "Der angegebene Member besitzt leider kein Eisen"
                await ctx.send(msg)
                return

            amount = over[0]['amount']
            under = await conn.fetch(s_query, amount, 5 - len(over))

        unordered = list(over) + list(under)
        result = sorted(unordered, key=lambda r: r['amount'], reverse=True)
        await self.send_ranking(ctx, result, dead=True)


def setup(bot):
    bot.add_cog(Money(bot))
