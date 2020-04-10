from utils import GuildUser, pcv, error_embed
from discord.ext import commands
import discord


class Money(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="iron")
    async def iron_(self, ctx):
        cmd_list = ("top", "global", "send")
        if ctx.subcommand_passed and ctx.subcommand_passed not in cmd_list:
            msg = f"Falsche Eingabe | `{ctx.prefix}iron <top/global/send>"
            return await ctx.send(embed=error_embed(msg))

        if ctx.invoked_subcommand:
            return

        money, rank = await self.bot.fetch_iron(ctx.author.id, True)
        base = "**Dein Speicher:** `{} Eisen`\n**Globaler Rang:** `{}`"
        await ctx.send(base.format(pcv(money), rank))

    @iron_.command()
    @commands.cooldown(1, 30.0, commands.BucketType.user)
    async def send(self, ctx, amount: int, *, user: GuildUser):
        if not 1000 <= amount <= 500000:
            await ctx.send("Du kannst nur `1000-50.000 Eisen` überweisen")
            ctx.command.reset_cooldown(ctx)

        else:
            await self.bot.subtract_iron(ctx.author.id, amount)
            await self.bot.update_iron(user.id, amount)

            base = "Du hast `{}` erfolgreich `{} Eisen` überwiesen (30s Cooldown)"
            await ctx.send(base.format(user.display_name, pcv(amount)))

    @iron_.command(name="global", aliases=["top"])
    async def rank_(self, ctx):
        top = ctx.invoked_with.lower() == "top"
        guild = ctx.guild if top else None

        msg = ""
        data = await self.bot.fetch_iron_list(5, guild)
        for index, record in enumerate(data):
            if top:
                player = guild.get_member(record['id'])
            else:
                player = self.bot.get_user(record['id'])

            name = "Unknown" if not player else player.display_name
            msg += f"**Rang {index + 1}:** `{pcv(record['amount'])} Eisen` [{name}]\n"

        if msg:
            embed = discord.Embed(description=msg, color=discord.Color.blue())
            await ctx.send(embed=embed)

        else:
            msg = "Aktuell gibt es keine gespeicherten Scores"
            await ctx.send(embed=error_embed(msg))


def setup(bot):
    bot.add_cog(Money(bot))
