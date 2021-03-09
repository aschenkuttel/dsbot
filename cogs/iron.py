from utils import MemberConverter, MissingRequiredKey, seperator
from discord.ext import commands
import tabulate
import discord


class Iron(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.type = 3

    async def send_ranking(self, ctx, iterable, guild_data=None):
        data = []
        for index, record in iterable:

            if guild_data:
                member = guild_data[record['id']]
            else:
                member = self.bot.get_member(record['id'])

            if member is None:
                name = "Unknown"
            elif guild_data:
                name = member.display_name
            else:
                name = member.name

            data.append([f"{index})", name, "»", seperator(record['amount'])])

            if len(data) == 5:
                break

        if data:
            obj = "Server" if guild_data else "Bot"
            title = f"Top 5 Eisen des {obj}s"
            parts = tabulate.tabulate(data, tablefmt='plain', disable_numparse=True)
            desc = f"```py\n{parts}\n```"
            embed = discord.Embed(title=title, description=desc)
            embed.colour = discord.Color.blue()
            await ctx.send(embed=embed)

        else:
            msg = "Aktuell gibt es keine gespeicherten Scores"
            await ctx.send(msg)

    @commands.group(name="iron", invoke_without_command=True)
    async def iron(self, ctx):
        if not ctx.message.content.endswith("iron"):
            raise MissingRequiredKey(("send", "global", "top", "local"))

        money, rank = await self.bot.fetch_iron(ctx.author.id, True)
        base = "**Dein Speicher:** `{} Eisen`\n**Globaler Rang:** `{}`"
        await ctx.send(base.format(seperator(money), rank))

    @iron.command(name="send")
    @commands.cooldown(1, 10.0, commands.BucketType.user)
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
        async with self.bot.member_pool.acquire() as conn:
            data = await conn.fetch(query, list(members))

            result = []
            for index, record in enumerate(data, 1):
                result.append([index, record])

            await self.send_ranking(ctx, result, guild_data=members)

    @iron.command(name="global")
    async def global_(self, ctx):
        query = 'SELECT * FROM iron ORDER BY amount DESC LIMIT 5'
        async with self.bot.member_pool.acquire() as conn:
            cache = await conn.fetch(query)

        result = []
        for index, record in enumerate(cache, 1):
            result.append([index, record])

        await self.send_ranking(ctx, result)

    @iron.command(name="local")
    async def local_(self, ctx, member: MemberConverter = None):
        f_query = 'SELECT *, (SELECT COUNT(*) FROM iron ' \
                  'WHERE amount > (SELECT amount FROM iron WHERE id = $1)) AS count ' \
                  'FROM iron WHERE amount >= (SELECT amount FROM iron WHERE id = $1) ' \
                  'ORDER BY amount ASC LIMIT 3'

        s_query = 'SELECT * FROM iron WHERE amount < $1 ' \
                  'ORDER BY amount DESC LIMIT $2'

        async with self.bot.member_pool.acquire() as conn:
            member = member or ctx.author
            over = await conn.fetch(f_query, member.id)

            if not over:
                msg = "Der angegebene Member besitzt leider kein Eisen"
                await ctx.send(msg)
                return

            amount = over[0]['amount']
            global_index = over[0]['count']
            under = await conn.fetch(s_query, amount, 5 - len(over))

        unordered = list(over) + list(under)
        ordered = sorted(unordered, key=lambda r: r['amount'], reverse=True)
        author_index = ordered.index(over[0])

        result = []
        for index, record in enumerate(ordered, start=1):
            user_rank = global_index + index - author_index
            result.append([user_rank, record])

        await self.send_ranking(ctx, result)


def setup(bot):
    bot.add_cog(Iron(bot))
