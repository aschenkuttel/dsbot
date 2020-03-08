from utils import game_channel_only
from discord.ext import commands
import asyncio
import time


class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = {}

    @commands.command(name="blackjack", aliases=["bj"])
    @game_channel_only()
    async def blackjack_(self, ctx, amount: int):

        if amount > 100000 or amount < 100:
            await ctx.send("Fehlerhafte Eingabe: `!bj <100-100000>`")
            return

        credit = await self.bot.fetch_user_data(ctx.author.id)
        if credit - amount < 0:
            await ctx.send("Du kannst nicht um Geld spielen welches du nicht besitzt.")
            return

        current = self.data.get(ctx.guild.id)
        if current is False:
            return
        if current:
            # game is ongoing
            return

        data = {'time': ctx.message.created_at, 'master': ctx.author.id, 'amount': amount}
        self.data[ctx.guild.id] = data

        msg = f"{ctx.author.display_name} möchte eine Runde Blackjack spielen:\n" \
              f"Einsatz: {amount} Eisen | Das Spiel startet in einer Minute"
        await ctx.send(msg)
        await asyncio.sleep(60)


def setup(bot):
    bot.add_cog(Blackjack(bot))
