from utils import MemberConverter, MissingRequiredKey, seperator
from discord.ext import commands
import discord


class Iron(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.type = 3

    async def send_ranking(self, ctx, iterable, guild=False):
        data = []
        for index, record in iterable:

            if guild is True:
                ids = (ctx.guild.id, record['id'])
                member = self.bot.get_guild_member(*ids)
            else:
                member = self.bot.get_member(record['id'])

            if member is None:
                name = "Unknown"
            elif guild is True:
                name = member.display_name
            else:
                name = member.name

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
            raise MissingRequiredKey(("send", "top", "local"))

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

    @iron.command(name="top")
    async def top_(self, ctx):
        members = self.bot.members.get(ctx.guild.id)
        if members is None:
            return

        query = 'SELECT * FROM iron WHERE id = ANY($1) ' \
                'ORDER BY amount DESC LIMIT 5'
        async with self.bot.ress.acquire() as conn:
            data = await conn.fetch(query, list(members))

            result = []
            for index, record in enumerate(data, 1):
                result.append([index, record])

            await self.send_ranking(ctx, result, guild=True)

    @iron.command(name="global")
    async def global_(self, ctx):
        query = 'SELECT * FROM iron ORDER BY amount DESC LIMIT 5'
        async with self.bot.ress.acquire() as conn:
            cache = await conn.fetch(query)

        result = []
        for index, record in enumerate(cache, 1):
            result.append([index, record])

        await self.send_ranking(ctx, result)

    @iron.command(name="local")
    async def local_(self, ctx, member: MemberConverter = None):
        f_query = 'SELECT * FROM iron WHERE amount >= ' \
                  '(SELECT amount FROM iron WHERE id = $1) ' \
                  'ORDER BY amount ASC LIMIT 3'

        s_query = 'SELECT *, (SELECT COUNT(*) FROM iron ' \
                  'WHERE amount > $1) AS count ' \
                  'FROM iron WHERE amount < $1 ' \
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

            rank = under[0]['count'] + 1

        unordered = list(over) + list(under)
        ordered = sorted(unordered, key=lambda r: r['amount'], reverse=True)
        or_index = ordered.index(over[0])

        result = []
        for index, record in enumerate(ordered):
            new_rank = rank + or_index - index
            result.append([new_rank, record])

        await self.send_ranking(ctx, result)


def setup(bot):
    bot.add_cog(Iron(bot))
