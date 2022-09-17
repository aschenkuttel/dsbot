from utils import MemberConverter, MissingRequiredKey, seperator
from discord import app_commands
from discord.ext import commands
import tabulate
import discord


class Iron(commands.GroupCog, name="iron"):
    def __init__(self, bot):
        self.bot = bot
        self.type = 3

    async def send_ranking(self, interaction, iterable, guild_data=None):
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
            await interaction.response.send_message(embed=embed)

        else:
            msg = "Aktuell gibt es keine gespeicherten Scores"
            await interaction.response.send_message(msg)

    @app_commands.command(name="balance", description="Erhalte deinen aktuellen Eisenspeicher und deinen globalen Rang")
    async def balance_(self, interaction):
        money, rank = await self.bot.fetch_iron(interaction.user.id, True)
        base = "**Dein Speicher:** `{} Eisen`\n**Globaler Rang:** `{}`"
        await interaction.response.send_message(base.format(seperator(money), rank))

    @app_commands.command(name="send", description="Sende einem User Eisen")
    @app_commands.describe(amount="Eine Anzahl an Eisen zwischen 1000 und 50000")
    async def send_(self, interaction, member: MemberConverter, amount: int):
        if not 1000 <= amount <= 50000:
            await interaction.response.send_message("Du kannst nur `1000-50.000 Eisen` überweisen")
        else:
            await self.bot.subtract_iron(interaction.user.id, amount)
            await self.bot.update_iron(member.id, amount)

            base = "Du hast `{}` erfolgreich `{} Eisen` überwiesen (30s Cooldown)"
            await interaction.response.send_message(base.format(member.display_name, seperator(amount)))

    @app_commands.command(name="top", description="Die Top 5 des Servers")
    async def top_(self, ctx):
        member_list = self.bot.member.get(ctx.guild.id)
        if member_list is None:
            return

        query = 'SELECT * FROM iron WHERE id = ANY($1) ' \
                'ORDER BY amount DESC LIMIT 5'
        async with self.bot.member_pool.acquire() as conn:
            data = await conn.fetch(query, list(member_list))

            result = []
            for index, record in enumerate(data, 1):
                result.append([index, record])

            await self.send_ranking(ctx, result, guild_data=member_list)

    @app_commands.command(name="global", description="Die globalen Top 5")
    async def global_(self, ctx):
        query = 'SELECT * FROM iron ORDER BY amount DESC LIMIT 5'
        async with self.bot.member_pool.acquire() as conn:
            cache = await conn.fetch(query)

        result = []
        for index, record in enumerate(cache, 1):
            result.append([index, record])

        await self.send_ranking(ctx, result)

    @app_commands.command(name="local", description="Die globalen Top 5 Spieler um den angegebenen Member")
    @app_commands.describe(member="Der Name des gewünschten Members, bei Default der Author des Commands")
    async def local_(self, interaction, member: MemberConverter = None):
        f_query = 'SELECT *, (SELECT COUNT(*) FROM iron ' \
                  'WHERE amount > (SELECT amount FROM iron WHERE id = $1)) AS count ' \
                  'FROM iron WHERE amount >= (SELECT amount FROM iron WHERE id = $1) ' \
                  'ORDER BY amount ASC LIMIT 3'

        s_query = 'SELECT * FROM iron WHERE amount < $1 ' \
                  'ORDER BY amount DESC LIMIT $2'

        async with self.bot.member_pool.acquire() as conn:
            member = member or interaction.user
            over = await conn.fetch(f_query, member.id)

            if not over:
                msg = "Der angegebene Member besitzt leider kein Eisen"
                await interaction.response.send_message(msg)
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

        await self.send_ranking(interaction, result)


async def setup(bot):
    await bot.add_cog(Iron(bot))
