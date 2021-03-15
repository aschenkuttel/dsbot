from discord.ext import commands
from utils import MemberConverter
import datetime
import discord
import asyncio
import random
import utils


class DCUtils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.type = 2
        self.poll_time = 10
        self.url = "http://media1.tenor.com/images/561e3f9a9c6c" \
                   "1912e2edc4c1055ff13e/tenor.gif?itemid=9601551"

    @commands.command(name="speedrun", hidden=True)
    async def speedrun(self, ctx):
        date = datetime.datetime(2021, 1, 6, 8)
        now = datetime.datetime.now()

        difference = (now - date).total_seconds()
        m, s = divmod(difference, 60)
        h, m = divmod(m, 60)

        rep = f'{int(h)} : {int(m)} : {int(s)}'
        await ctx.send(rep)

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
    async def poll_(self, ctx, time: int, *, arguments):
        lines = arguments.split("\n")

        if not 3 <= len(lines) <= 9:
            msg = "You should have between two and nine choices"
            await ctx.send(msg)
            return

        question = lines.pop(0)

        parsed_options = ""
        for index, option in enumerate(lines):
            parsed_options += f"\n`{index + 1}.` {option}"

        title = f"**Poll from {ctx.author.display_name}**"
        description = f"{title}\n{question}{parsed_options}"
        embed = discord.Embed(description=description, color=discord.Color.purple())
        embed.set_footer(text=f"Voting ends in {time} minutes")
        embed.set_thumbnail(url=ctx.author.avatar_url)
        poll = await ctx.send(embed=embed)

        for num in range(len(lines)):
            emoji = f"{num + 1}\N{COMBINING ENCLOSING KEYCAP}"
            await poll.add_reaction(emoji)

        await utils.silencer(ctx.message.delete())
        whole, remainder = divmod(time, self.poll_time)

        first_duration = self.poll_time if whole else remainder
        await asyncio.sleep(first_duration * 60)

        for n in range(1, whole):
            if n + 1 != whole:
                minutes = self.poll_time
                cur = (whole - n) * self.poll_time + remainder
            else:
                minutes = remainder
                cur = minutes

            embed.set_footer(text=f"Voting ends in {cur} minutes")
            await poll.edit(embed=embed)
            await asyncio.sleep(minutes * 60)

        re_fetched = await ctx.channel.fetch_message(poll.id)
        votes = sorted(re_fetched.reactions, key=lambda r: r.count, reverse=True)
        color = discord.Color.red()

        if [r.count for r in votes].count(1) == len(votes):
            msg = "`Nobody voted!`"

        elif votes[0].count > votes[1].count:
            color = discord.Color.green()
            winner = re_fetched.reactions.index(votes[0])
            msg = f"`{lines[winner]} won with {votes[0].count - 1} votes!`"

        else:
            msg = "`The poll resulted in a draw...`"

        result = f"{title}\n{question}\n{msg}"
        result_embed = discord.Embed(description=result, color=color)
        result_embed.set_footer(text="Finished.")
        await poll.edit(embed=result_embed)
        await utils.silencer(poll.clear_reactions())

    @commands.command(name="info")
    async def info_(self, ctx):
        result = [f"Aktuell in `{len(self.bot.guilds)}` Servern!"]

        data = await self.bot.fetch_usage(amount=10)

        if data:
            result.append("**Die 10 meist benutzen Commands:**")

        for cmd, usage in data:
            result.append(f"`{usage}` **|** {cmd}")

        embed = discord.Embed()
        embed.description = "\n".join(result)
        embed.set_footer(text="Supportserver: https://discord.gg/s7YDfFW")
        name = "dsBot | Einladungslink"
        url = "http://discordapp.com/oauth2/authorize?&client_id=344191195981021185&scope=bot"
        embed.set_author(icon_url=self.bot.user.avatar_url, name=name, url=url)
        await ctx.send(embed=embed)

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

            if any(word in msg.content.lower() for word in ("ja", "nein")):
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


def setup(bot):
    bot.add_cog(DCUtils(bot))
