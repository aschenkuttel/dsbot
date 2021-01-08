from discord.ext import commands
from utils import MemberConverter
import discord
import asyncio
import random


class DCUtils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.type = 2
        self.duration = 300
        self.url = "http://media1.tenor.com/images/561e3f9a9c6c" \
                   "1912e2edc4c1055ff13e/tenor.gif?itemid=9601551"

    @commands.command(name="orakel")
    async def orakel_(self, ctx, *, args):
        await ctx.trigger_typing()

        # checks for both since numbers would
        # count as auppercase as well
        if args == args.upper() and not args == args.lower():
            answer = random.choice(ctx.lang.scared_oracle)
            await ctx.send(answer)
            return

        percentage = random.random()
        if percentage > 0.005:
            answer = random.choice(ctx.lang.oracle)
            await ctx.send(answer)
            return

        easter = random.choice([1, 2, 3])
        if easter == 1:
            data = "Hilfe ich bin in Kuttes Keller gefangen " \
                   "und werde gezwungen diese Antw"
            msg = await ctx.send(data)
            await asyncio.sleep(4)
            await msg.edit(content="Bot wird neugestartet...")
            await asyncio.sleep(5)
            await msg.edit(content="dsBot wurde erfolgreich neugestartet.")

        elif easter == 2:
            await asyncio.sleep(10)
            msg = "Ach weißt du, ich wollte dir eigentlich was " \
                  "schönes schreiben, aber was du letztens zu " \
                  "mir gesagt hast war echt fies. Selber Schuld!"
            await ctx.send(msg)

        else:
            responses = ["Schon wieder eine Frage...",
                         "Weißt du, ich bin deinen Scheiß langsam satt!",
                         "Als ob du die Frage nicht selber beantworten kannst.....",
                         "NEIN DU HÄLTST JETZT MAL DIE SCHNAUZE!!!",
                         "Ich bin Done mit dir, DONE!"]
            for response in responses:
                sec = random.randint(3, 6)
                await asyncio.sleep(sec)
                await ctx.send(response)

    @commands.command(name="duali")
    async def duali_(self, ctx, *, member: MemberConverter):
        if member == self.bot.user:
            embed = discord.Embed()
            embed.set_image(url=self.url)
            msg = "Das ist echt cute... aber ich regel solo."
            await ctx.send(msg, embed=embed)

        elif member == ctx.author:
            yt = "https://www.youtube.com/watch?v=fZcZvlcNyOk"
            embed = discord.Embed(title="0% - Sorry", url=yt)
            await ctx.send(embed=embed)

        else:
            points = 0
            for idc in (ctx.author.id, member.id):
                num = int(str(idc)[-3:-1])
                number = num + (sum(int(n) for n in str(idc)))
                points += number

            result = points % 101
            index = 9 if result >= 90 else int(result / 10)
            answer = ctx.lang.duali_message[index]

            await ctx.send(f"Ihr passt zu `{result}%` zusammen.\n{answer}")

    @commands.command(name="poll")
    async def poll_(self, ctx, question, *options):
        if len(options) > 9:
            msg = "Die maximale Anzahl der Auswahlmöglichkeiten beträgt 9"
            await ctx.send(msg)
            return

        parsed_options = ""
        for index, opt in enumerate(options):
            choice = f"\n`{index + 1}.` {opt}"
            parsed_options += choice

        title = f"**Abstimmung von {ctx.author.display_name}:**"
        description = f"{title}\n{question}{parsed_options}"
        embed = discord.Embed(description=description, color=discord.Color.purple())
        embed.set_footer(text="Abstimmung endet in 15 Minuten")
        poll = await ctx.send(embed=embed)

        for num in range(len(options)):
            emoji = f"{num + 1}\N{COMBINING ENCLOSING KEYCAP}"
            await poll.add_reaction(emoji)

        await ctx.safe_delete()
        await asyncio.sleep(self.duration)

        for dur in [2, 1]:
            cur = int(self.duration / 60) * dur
            embed.set_footer(text=f"Abstimmung endet in {cur} Minuten")
            await poll.edit(embed=embed)
            await asyncio.sleep(self.duration)

        refetched = await ctx.channel.fetch_message(poll.id)
        votes = sorted(refetched.reactions, key=lambda r: r.count, reverse=True)
        color = discord.Color.red()

        if [r.count for r in votes].count(1) == len(votes):
            msg = "`Niemand hat an der Abstimmung teilgenommen`"

        elif votes[0].count > votes[1].count:
            color = discord.Color.green()
            winner = refetched.reactions.index(votes[0])
            msg = f"`{options[winner]} hat gewonnen`"

        else:
            msg = "`Es konnte kein klares Ergebnis erzielt werden`"

        result = f"{title}\n{question}\n{msg}"
        wimbed = discord.Embed(description=result, color=color)
        wimbed.set_footer(text="Abstimmung beendet")
        await poll.edit(embed=wimbed)

    @commands.command(name="mirror")
    async def mirror_(self, ctx, *, member: MemberConverter = None):
        embed = discord.Embed()
        member = member or ctx.author
        embed.set_image(url=member.avatar_url)
        await ctx.send(embed=embed)

    @commands.command(name="info")
    async def info_(self, ctx):
        result = [f"Aktuell in `{len(self.bot.guilds)}` Servern",
                  "**Die 5 meist benutzen Commands:**"]

        data = await self.bot.fetch_usage(amount=5)

        for cmd, usage in data:
            result.append(f"`{usage}` **|** {cmd}")

        embed = discord.Embed()
        embed.description = "\n".join(result)
        embed.set_footer(text="Supportserver: https://discord.gg/s7YDfFW")
        name = "dsBot | Die Stämme x Discord"
        embed.set_author(icon_url=self.bot.user.avatar_url, name=name)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(DCUtils(bot))
