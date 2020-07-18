from utils import MemberConverter, seperator, error_embed
from discord.ext import commands
import discord


class Money(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="iron")
    async def iron(self, ctx):
        cmd_list = ("top", "global", "send")
        if ctx.subcommand_passed and ctx.subcommand_passed not in cmd_list:
            msg = f"Falsche Eingabe | `{ctx.prefix}iron <top/global/send>"
            return await ctx.send(embed=error_embed(msg))

        if ctx.invoked_subcommand:
            return

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

    @iron.command(name="global", aliases=["top"])
    async def rank_(self, ctx):
        top = ctx.invoked_with.lower() == "top"
        guild = ctx.guild if top else None

        data = []
        cache = await self.bot.fetch_iron_list(100, guild)
        for index, record in enumerate(cache):
            if top:
                player = guild.get_member(record['id'])
            else:
                player = self.bot.get_user(record['id'])

            if player is None:
                continue

            base = "**Rang {}:** `{} Eisen` [{.display_name}]"
            msg = base.format(len(data) + 1, seperator(record['amount']), player)
            data.append(msg)

            if len(data) == 5:
                break

        if data:
            embed = discord.Embed(description="\n".join(data), color=discord.Color.blue())
            await ctx.send(embed=embed)

        else:
            msg = "Aktuell gibt es keine gespeicherten Scores"
            await ctx.send(embed=error_embed(msg))


def setup(bot):
    bot.add_cog(Money(bot))
