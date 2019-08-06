from bs4 import BeautifulSoup
from discord.ext import commands
from load import load
from utils import pcv, error_embed


class Recap(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="recap", aliases=["tagebuch"])
    async def recap(self, ctx, *, args):

        player, time = await load.re_handler(ctx.world, args)

        if not 30 > time > 0:
            msg = "Das Maximum für den Recap Command sind 29 Tage."
            return await ctx.send(embed=error_embed(msg))

        me = 'player' if player.alone else 'tribe'
        page_link = "http://de.twstats.com/de{}/index.php?page={}&id={}&mode=history"
        page_link = page_link.format(ctx.url, me, player.id)

        async with self.bot.session.get(page_link) as r:
            soup = BeautifulSoup(await r.read(), "html.parser")

        data = soup.find(id='export').text.split("\n")
        try:
            point1, villages1, bash1 = data[0].split(",")[4:7]
            point8, villages8, bash8 = data[time].split(",")[4:7]
            if not player.alone:
                member1, member8 = data[0].split(",")[3], data[time].split(",")[3]
            else:
                member1, member8 = 0, 0

        except (IndexError, ValueError):
            c = "Spieler" if player.alone else "Stamm"
            msg = f"Der {c}: `{player.name}` ist noch keine {time} Tage auf der Welt!"
            return await ctx.send(msg)

        p_done = pcv(int(point1) - int(point8))
        v_done = str(int(villages1) - int(villages8))
        b_done = pcv(int(bash1) - int(bash8))
        m_done = int(member1) - int(member8)

        a = "Punkte verloren," if p_done.startswith("-") else "Punkte gemacht,"
        p_done = p_done[1:] if p_done.startswith("-") else p_done

        b = "verschenkt" if v_done.startswith("-") else "geholt"
        v_done = v_done[1:] if v_done.startswith("-") else v_done
        v_done = int(v_done) if player.alone else int(v_done) - m_done
        x = "Dorf" if v_done == 1 or v_done == -1 else "Dörfer"

        if b_done.startswith("-"):
            c = f"`{b_done[1:]}` Bashpoints verloren"
        else:
            c = f"sich `{b_done}` Bashpoints erkämpft"

        y = "hat" if player.alone else "haben"

        msg = "seit gestern" if time == 1 else f"in den letzten {time} Tagen:"
        tri = ""
        if not player.alone:
            if m_done >= 0:
                tri = f" `{m_done}` Spieler aufgenommen,"
            else:
                tri = f" `{str(m_done)[1:]}` Spieler gekickt, "
        name = f"`{player.name}` {y} {msg}"
        answer = f"{name}{tri} `{p_done}` {a} `{v_done}` {x} {b} und {c}."
        await ctx.send(answer)

    @recap.error
    async def recap_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=error_embed("Der gewünschte Spieler/Stamm fehlt"))


def setup(bot):
    bot.add_cog(Recap(bot))
