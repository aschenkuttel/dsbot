import discord
from bs4 import BeautifulSoup
from discord.ext import commands
from utils import error_embed
from load import load


class Daily(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.never = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.base = "https://de{}.die-staemme.de/guest.php?village" \
                    "=null&screen=ranking&mode=in_a_day&type={}"
        self.keys = {"bash": "kill_att", "def": "kill_def", "ut": "kill_supp",
                     "farm": "loot_res", "villages": "loot_vil", "conquer": "conquer"}

    async def top5(self, session, ctx):
        key = self.keys[ctx.invoked_with.lower()]
        res_link = self.base.format(ctx.url, key)

        async with session.get(res_link) as r:
            soup = BeautifulSoup(await r.read(), "html.parser")

        table = soup.find('table', id='in_a_day_ranking_table')
        rows = table.find_all('tr')
        result = []

        try:
            for row in rows[1:6]:
                vanity = row.find('a')['href']
                player_id = int(vanity.split("=")[-1])
                player = await load.fetch_player(ctx.world, player_id)
                name = player.name if player else "Unknown"
                url = player.guest_url if player else self.never
                points = row.findAll("td")[3].text
                result.append(f"`{points}` **|** [{name}]({url})")
            return discord.Embed(description='\n'.join(result))

        except AttributeError:
            msg = "Aktuell liegen noch keine Daten vor."
            return discord.Embed(title=msg, color=discord.Color.red())

    @commands.group(name="daily", aliases=["top"], invoke_without_command=True)
    async def daily_(self, ctx):
        pre = await self.bot.get_prefix(ctx.message)
        msg = f"{pre}daily <bash/def/ut/farm/villages/conquer>"
        return await ctx.send(embed=error_embed(msg))

    @daily_.command(name="bash", aliases=["def", "ut", "farm", "villages", "conquer"])
    async def types_(self, ctx):
        embed = await self.top5(self.bot.session, ctx)
        return await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Daily(bot))
