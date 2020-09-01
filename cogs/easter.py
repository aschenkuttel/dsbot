from discord.ext import commands
import asyncio
import random
import discord


class Easter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="votekick")
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def votekick_(self, ctx):
        title = f"{ctx.author.display_name} möchte gekickt werden..."
        description = "Stimme jetzt im Chat mit **Ja** oder **Nein**\n" \
                      "**Grund:** Es wurde keiner angegeben."
        embed = discord.Embed(title=title, description=description)
        embed.set_footer(text="Voting wird nach 60 Sekunden geschlossen")
        embed.set_thumbnail(url=ctx.author.avatar_url)
        message = await ctx.send(embed=embed)

        counter = []

        def check(msg):
            if ctx.channel != msg.channel or ctx.author.id in counter:
                return

            if any(word in msg.content.lower() for word in ["ja", "nein"]):
                counter.append(ctx.author.id)

        try:
            await self.bot.wait_for('message', check=check, timeout=60)

        except asyncio.TimeoutError:
            embed = message.embeds[0]
            german = "hat" if len(counter) == 1 else "haben"
            embed.set_footer(text="Voting wurde geschlossen")
            answer = f"und {len(counter)} User {german} das geglaubt, yikes."
            embed.description = answer
            await message.edit(embed=embed)

    @commands.command(name="fake")
    async def fake_(self, ctx, username=None):
        if not username:
            return await ctx.send("Es muss ein Ziel angegeben werden...")

        msg = await ctx.send("Sending...")
        await asyncio.sleep(5)
        res = f"**{random.randint(101, 1999)}** Fakes wurden auf {username} versendet."
        await msg.edit(content=res)

    @commands.command(name="suicide")
    async def suicide_(self, ctx):
        await ctx.send("`0800/111 0 111`")


def setup(bot):
    bot.add_cog(Easter(bot))
