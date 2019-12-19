from utils import pcv, error_embed, GuildUser
from discord.ext import commands
from load import load
import discord


class Money(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="iron")
    async def iron_(self, ctx):
        cmd_list = ("top", "global", "send")
        if ctx.subcommand_passed and ctx.subcommand_passed not in cmd_list:
            return await ctx.send(embed=error_embed(
                f"Falsche Eingabe | `{ctx.prefix}iron <top/global/send>"))
        if ctx.invoked_subcommand:
            return

        money, rank = await load.get_user_data(ctx.author.id, True)
        return await ctx.send(f"**Dein Speicher:** `{pcv(money)} "
                              f"Eisen`\n**Globaler Rang:** `{rank}`")

    @iron_.command()
    @commands.cooldown(1, 30.0, commands.BucketType.user)
    async def send(self, ctx, amount: int, *, user: GuildUser):
        cur = await load.get_user_data(ctx.author.id)
        if cur < amount:
            await ctx.send(f"Du hast nur `{cur} Eisen` auf dem Konto")
            return ctx.command.reset_cooldown(ctx)
        if not 20001 > amount > 99:
            await ctx.send("Du kannst nur `100-20.000 Eisen` überweisen")
            return ctx.command.reset_cooldown(ctx)

        await load.save_user_data(ctx.author.id, -amount)
        await load.save_user_data(user.id, amount)

        return await ctx.send(
            f"Du hast `{user.display_name}` erfolgreich "
            f"`{pcv(amount)} Eisen` überwiesen (30s Cooldown)")

    @iron_.command(name="top")
    async def top_(self, ctx):
        data = await load.get_user_top(5, ctx.guild)
        msg = f""
        for index, record in enumerate(data):
            player = self.bot.get_user(int(record['id']))
            use = "Unknown" if not player else player.display_name
            msg += f"**Rang {index + 1}:** `{pcv(record['amount'])} Eisen` [{use}]\n"
        if msg:
            embed = discord.Embed(description=msg, color=discord.Color.blue())
            return await ctx.send(embed=embed)
        else:
            return await ctx.send("Auf diesem Server gibt es "
                                  "noch keine gespeicherten Scores")

    @iron_.command(name="global")
    async def global_(self, ctx):
        data = await load.get_user_top(5)
        msg = f""
        for index, record in enumerate(data):
            player = self.bot.get_user(int(record['id']))
            use = "Unknown" if not player else player.display_name
            msg += f"**Rang {index + 1}:** `{pcv(record['amount'])} Eisen` [{use}]\n"
        if msg:
            embed = discord.Embed(description=msg, color=discord.Color.blue())
            return await ctx.send(embed=embed)
        else:
            msg = "Aktuell gibt es keine gespeicherten Scores!"
            return await ctx.send(msg)


def setup(bot):
    bot.add_cog(Money(bot))
