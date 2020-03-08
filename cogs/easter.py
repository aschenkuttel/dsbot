from discord.ext import commands
from utils import GuildUser
import discord
import asyncio
import random


class Enjoy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="orakel")
    async def orakel_(self, ctx, *, args):
        if args == args.upper() and not args == args.lower():
            return await ctx.send(random.choice(self.bot.msg["fearOrakel"]))

        else:

            num = random.randint(1, 500)
            if num not in [300, 400, 500]:
                await ctx.send(random.choice(self.bot.msg["cleanOrakel"]))

            elif num == 300:

                data = "Hilfe, ich bin in Kuttes Keller gefangen" \
                       " und werde gezwungen diese Antw"
                msg = await ctx.send(data)
                await asyncio.sleep(4)
                await msg.edit(content="Bot wird neugestartet")
                txt = "Bot wird neugestartet"
                time = 0
                while time < 9:
                    time += 1
                    txt = txt
                    if time in [1, 4, 7]:
                        txt = txt + "."
                    elif time in [2, 5, 8]:
                        txt = txt + ".."
                    elif time in [3, 6, 9]:
                        txt = txt + "..."
                    await msg.edit(content=txt)
                    await asyncio.sleep(1.25)
                await msg.edit(content="dsBot wurde erfolgreich neugestartet.")

            elif num == 400:

                async with ctx.typing():
                    await asyncio.sleep(10)
                    data = "Ach weißt du, ich wollte dir eigentlich was " \
                           "schönes schreiben, aber was du letztens zu " \
                           "mir gesagt hast war echt fies. Selber Schuld."
                    return await ctx.send(data)

            elif num == 500:

                await ctx.send("Schon wieder eine Frage...")
                await asyncio.sleep(2)
                await ctx.send("Weißt du, ich bin deinen Scheiß langsam satt!")
                await asyncio.sleep(3)
                await ctx.send("Als ob du die Frage nicht "
                               "selber beantworten kannst.....")
                await asyncio.sleep(10)
                await ctx.send("NEIN DU HÄLTST JETZT MAL DIE SCHNAUZE!!!")
                await asyncio.sleep(3)
                await ctx.send("Ich bin Done mit dir, DONE!")

            else:
                await ctx.send("Irgendetwas ist wohl schief gelaufen :/")

    @commands.command(name="duali", aliases=["mitspieler"])
    async def duali_(self, ctx, *, user: GuildUser):
        if user == self.bot.user:
            em = discord.Embed()
            url = "http://media1.tenor.com/images/561e3f9a9c6c" \
                  "1912e2edc4c1055ff13e/tenor.gif?itemid=9601551"
            em.set_image(url=url)
            msg = "Das ist echt cute... aber ich regel solo."
            await ctx.send(msg, embed=em)
        elif user == ctx.author:
            yt = "https://www.youtube.com/watch?v=fZcZvlcNyOk"
            em = discord.Embed(title="0% - Sorry", url=yt)
            await ctx.send(embed=em)
        else:
            me = int(str(ctx.author.id)[-3:][:-1]) + sum(int(num) for num in str(ctx.author.id))
            you = int(str(user.id)[-3:][:-1]) + sum(int(num) for num in str(user.id))
            result = (me + you) % 101

            if result >= 90:
                answer = "`{}` und `{}` hiermit erkläre ich euch zu Duali und Dualin :heart:"
                answer = answer.format(ctx.author.display_name, user.display_name)
            elif result >= 80:
                answer = "Fast das perfekte Dreamteam :heart_eyes:"
            elif result >= 70:
                answer = f"Uff nicht schlecht. Ihr regelt auf jeden Fall :heart:"
            elif result >= 60:
                answer = f"Nice, euch zwei seh ich in einem Account :blush: "
            elif result >= 50:
                answer = f"Ihr könnt es versuchen aber es gibt bessere Dualis für euch beide..."
            elif result >= 40:
                answer = "Ihr beide in einem Account? Bitte überlegt es euch."
            elif result >= 30:
                answer = "Bitte spielt niemals in einem Account."
            elif result >= 20:
                answer = "Bitte spielt niemals in einem Stamm."
            elif result >= 10:
                answer = "Ihr beide solltet euch nicht einmal im selben Land aufhalten..."
            else:
                answer = "Bitte schlagt eure Köpfe solange an die Wand, " \
                         "bis ihr Erinnerungen aneinander verliert."

            await ctx.send(f"Ihr passt zu `{result}%` zusammen.\n{answer}")

    @commands.command(name="mirror", aliases=["spiegel"])
    async def mirror_(self, ctx, *, user: GuildUser = None):
        em = discord.Embed()
        em.set_image(url=user.avatar_url if user else ctx.author.avatar_url)
        await ctx.send(embed=em)

    @commands.command(name="fake")
    async def fake_(self, ctx, username=None):
        if not username:
            return await ctx.send("Es muss ein Ziel angegeben werden")
        msg = await ctx.send("Sending...")
        await asyncio.sleep(5)
        res = f"**{random.randint(101, 1999)}** Fakes wurden auf {username} versendet."
        await msg.edit(content=res)

    @commands.command(name="ddos")
    async def ddos_(self, ctx, *, user: GuildUser):
        msg = await ctx.send("DDOS starting..")
        await asyncio.sleep(2)
        await msg.edit(content=f"scanning for `{user.display_name}`...")
        await asyncio.sleep(2)
        await msg.edit(content="sending packages.")
        await asyncio.sleep(4)
        await msg.edit(content="deactivating WLAN..")
        await asyncio.sleep(2)
        await msg.edit(content="deactivating LAN...")
        await asyncio.sleep(2)
        await msg.edit(content="shutdown.")
        await asyncio.sleep(1)
        await msg.edit(content=f"DDOS Attack succeeded: `{user}` is offline.")

    @commands.command(name="suicide")
    async def suicide_(self, ctx):
        await ctx.send("`0800/111 0 111`")


def setup(bot):
    bot.add_cog(Enjoy(bot))
