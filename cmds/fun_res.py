from discord.ext import commands
from utils import pcv, error_embed, GuildUser
from load import load
import discord

find = discord.utils.find


class Money(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="res")
    async def res_(self, ctx):
        cmd_list = ("top", "global", "send")
        if ctx.subcommand_passed and ctx.subcommand_passed not in cmd_list:
            pref = await self.bot.get_prefix(ctx.message)
            return await ctx.send(embed=error_embed(
                f"Falscher Command: `{pref}res` | "
                f"`{pref}res top` | `{pref}res global` - `{pref}res send`"))
        if ctx.invoked_subcommand:
            return

        money, rank = await load.get_user_data(ctx.author.id, True)
        return await ctx.send(f"**Dein Speicher:** `{pcv(money)} "
                              f"Eisen`\n**Globaler Rang:** `{rank}`")

    @res_.command()
    @commands.cooldown(1, 30.0, commands.BucketType.user)
    async def send(self, ctx, amount: int, *, user: GuildUser):
        cur = await load.get_user_data(ctx.author.id)
        if cur < amount:
            await ctx.send(f"Du hast nur `{cur} Eisen` auf dem Konto.")
            return ctx.command.reset_cooldown(ctx)
        if not 20001 > amount > 99:
            await ctx.send("Du kannst nur `100-20.000 Eisen` überweisen.")
            return ctx.command.reset_cooldown(ctx)

        await load.save_user_data(ctx.author.id, -amount)
        await load.save_user_data(user.id, amount)

        return await ctx.send(
            f"Du hast `{user.display_name}` erfolgreich "
            f"`{pcv(amount)} Eisen` überwiesen (30s Cooldown)")

    @res_.command(name="top")
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
                                  "noch keine gespeicherten Scores.")

    @res_.command(name="global")
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

    @send.error
    async def send_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            embed = error_embed("Fehlerhafte Eingabe - Beispiel\n"
                                "!ress send <username> <100-20000>:")
            ctx.command.reset_cooldown(ctx)
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Money(bot))
