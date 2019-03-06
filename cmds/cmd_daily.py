import discord
from bs4 import BeautifulSoup
from discord.ext import commands
from load import load
from utils import error_embed


class Daily(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.base = ["https://de",
                     ".die-staemme.de/guest.php?"
                     "village=null&screen=ranking&"
                     "mode=in_a_day&type="]

    async def top5(self, session, res_link):
        async with session.get(res_link) as r:
            soup = BeautifulSoup(await r.read(), "html.parser")

            xo = soup.find("table", id="in_a_day_ranking_table")
            x1 = xo.find_all("tr")
            res = []
            try:
                for table in x1[1:6]:
                    name = table.find("a").text.strip()
                    points = table.findAll("td")[3].text
                    res.append(f"`{points}` **|** {name}")
                em = discord.Embed(description='\n'.join(res))
            except AttributeError:
                msg = "Aktuell liegen noch keine Daten vor."
                return discord.Embed(title=msg, color=discord.Color.red())
            return em

    @commands.group(name="daily", aliases=["top"], invoke_without_command=True)
    async def daily_(self, ctx):
        if ctx.subcommand_passed or ctx.invoked_with.lower() == "daily":
            pre = await self.bot.get_prefix(ctx.message)
            msg = f"{pre}daily <bash/def/ut/farm/villages/conquer>"
            return await ctx.send(embed=error_embed(msg))

    @daily_.command(name="bash")
    async def bash_(self, ctx):
        world = load.get_world(ctx.channel, True)
        res_link = f"{self.base[0]}{world}{self.base[1]}kill_att"
        emb = await self.top5(self.bot.session, res_link)
        return await ctx.send(embed=emb)

    @daily_.command(name="def")
    async def def_(self, ctx):
        world = load.get_world(ctx.channel, True)
        res_link = f"{self.base[0]}{world}{self.base[1]}kill_def"
        emb = await self.top5(self.bot.session, res_link)
        return await ctx.send(embed=emb)

    @daily_.command(name="ut")
    async def ut_(self, ctx):
        world = load.get_world(ctx.channel, True)
        res_link = f"{self.base[0]}{world}{self.base[1]}kill_sup"
        emb = await self.top5(self.bot.session, res_link)
        return await ctx.send(embed=emb)

    @daily_.command(name="farm")
    async def farm_(self, ctx):
        world = load.get_world(ctx.channel, True)
        res_link = f"{self.base[0]}{world}{self.base[1]}loot_res"
        emb = await self.top5(self.bot.session, res_link)
        return await ctx.send(embed=emb)

    @daily_.command(name="villages")
    async def villages_(self, ctx):
        world = load.get_world(ctx.channel, True)
        res_link = f"{self.base[0]}{world}{self.base[1]}loot_vil"
        emb = await self.top5(self.bot.session, res_link)
        return await ctx.send(embed=emb)

    @daily_.command(name="conquer")
    async def conquer_(self, ctx):
        world = load.get_world(ctx.channel, True)
        res_link = f"{self.base[0]}{world}{self.base[1]}conquer"
        emb = await self.top5(self.bot.session, res_link)
        return await ctx.send(embed=emb)


def setup(bot):
    bot.add_cog(Daily(bot))
