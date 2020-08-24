from discord.ext import commands
from utils import MemberConverter
import discord
import asyncio
import random


class Enjoy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.url = "http://media1.tenor.com/images/561e3f9a9c6c" \
                   "1912e2edc4c1055ff13e/tenor.gif?itemid=9601551"

    @commands.command(name="orakel")
    async def orakel_(self, ctx, *, args):
        if args == args.upper() and not args == args.lower():
            answer = random.choice(self.bot.msg['fearOrakel'])
            return await ctx.send(answer)

        percentage = random.random()
        if percentage > 0.005:
            answer = random.choice(self.bot.msg['cleanOrakel'])
            return await ctx.send(answer)

        easter = random.choice([True, False])
        if easter is True:
            data = "Hilfe ich bin in Kuttes Keller gefangen " \
                   "und werde gezwungen diese Antw"
            msg = await ctx.send(data)
            await asyncio.sleep(4)
            await msg.edit(content="Bot wird neugestartet...")
            await asyncio.sleep(5)
            await msg.edit(content="dsBot wurde erfolgreich neugestartet.")

        elif easter is False:
            async with ctx.typing():
                await asyncio.sleep(10)
                data = "Ach weißt du, ich wollte dir eigentlich was " \
                       "schönes schreiben, aber was du letztens zu " \
                       "mir gesagt hast war echt fies. Selber Schuld!"
                return await ctx.send(data)

        else:
            await ctx.send("Schon wieder eine Frage...")
            await asyncio.sleep(3)
            await ctx.send("Weißt du, ich bin deinen Scheiß langsam satt!")
            await asyncio.sleep(4)
            await ctx.send("Als ob du die Frage nicht selber beantworten kannst.....")
            await asyncio.sleep(10)
            await ctx.send("NEIN DU HÄLTST JETZT MAL DIE SCHNAUZE!!!")
            await asyncio.sleep(3)
            await ctx.send("Ich bin Done mit dir, DONE!")

    @commands.command(name="duali")
    async def duali_(self, ctx, *, user: MemberConverter):
        if user == self.bot.user:
            embed = discord.Embed()
            embed.set_image(url=self.url)
            msg = "Das ist echt cute... aber ich regel solo."
            await ctx.send(msg, embed=embed)

        elif user == ctx.author:
            yt = "https://www.youtube.com/watch?v=fZcZvlcNyOk"
            em = discord.Embed(title="0% - Sorry", url=yt)
            await ctx.send(embed=em)

        else:
            me = int(str(ctx.author.id)[-3:][:-1]) + sum(int(num) for num in str(ctx.author.id))
            you = int(str(user.id)[-3:][:-1]) + sum(int(num) for num in str(user.id))
            result = (me + you) % 101

            index = 9 if result >= 90 else int(result / 10)
            answer = self.bot.msg['dualAnswer'][index]

            await ctx.send(f"Ihr passt zu `{result}%` zusammen.\n{answer}")

    @commands.command(name="mirror")
    async def mirror_(self, ctx, *, user: MemberConverter = None):
        em = discord.Embed()
        target = user or ctx.author
        em.set_image(url=target.avatar_url)
        await ctx.send(embed=em)

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
    bot.add_cog(Enjoy(bot))
