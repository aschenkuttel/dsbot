from discord.ext import commands
from utils import error_embed
from PIL import Image, ImageSequence
from io import BytesIO
from load import load, DSObject
from bs4 import BeautifulSoup
import discord


class Graphic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emo_list = ["ag", "axt", "dorfi",
                         "inc", "katta", "lkav",
                         "ramme", "schwert", "skav",
                         "speer", "spy", "ut"]

    # ----- Crop ----- #
    def crop(self, img, x, y):
        img = img.crop((
            img.size[0] / 2 - x / 2,
            img.size[1] / 2 - y / 2,
            img.size[0] / 2 + x / 2,
            img.size[1] / 2 + y / 2))
        return img

    # --- Resize --- #
    def img_resize(self, img):
        x = img.size[0]
        y = x / 1.5
        if img.size[0] / img.size[1] > 1.5:
            y = img.size[1]
            x = y * 1.5

        fac = min(270 / x, 180 / y)
        img = self.crop(img, x, y)
        img = img.resize((int(x * fac), int(y * fac)), Image.ANTIALIAS)
        return img

    # --- Gif Resize --- #
    def gif_resize(self, frames):
        img = next(frames)
        x = img.size[0]
        y = x / 1.5
        if img.size[0] / img.size[1] > 1.5:
            y = img.size[1]
            x = y * 1.5

        fac = min(270 / x, 180 / y)
        for frame in frames:
            pic = frame.copy()
            pic = self.crop(pic, x, y)
            pic = pic.resize((int(x * fac), int(y * fac)), Image.ANTIALIAS)
            yield pic

    @commands.command(name="avatar", aliases=["profilbild"])
    async def avatar_(self, ctx, url):

        async with self.bot.session.get(url) as r:
            avatar_bytes = await r.read()

        with Image.open(BytesIO(avatar_bytes)) as img:

            if img.size[0] <= 270 and img.size[1] <= 180:
                msg = "Das angegebene Bild ist bereits klein genug."
                return await ctx.send(embed=error_embed(msg))

            output_buffer = BytesIO()

            if img.format == "GIF":
                frames = ImageSequence.Iterator(img)
                frames = self.gif_resize(frames)
                om = next(frames)
                om.save(output_buffer, "gif", save_all=True, append_images=list(frames), quality=90)
                filename = "avatar.gif"

            else:
                img = self.img_resize(img)
                img.save(output_buffer, "png", quality=90)
                filename = "avatar.png"

            output_buffer.seek(0)
            file = discord.File(fp=output_buffer, filename=filename)
            await ctx.author.send(file=file)

    # @commands.command(name="map", aliases=["karte"])
    # @commands.cooldown(1, 60.0, commands.BucketType.guild)
    # async def map_(self, ctx, world=None):
    #
    #     if not world:
    #         world = load.get_world(ctx.channel, True)
    #
    #     base_url = "https://www.dsreal.de/index.php?screen=map_history&world=de{}"
    #     img_url = "https://www.dsreal.de/history.php?world=de{}&id={}"
    #     result = base_url.format(world)
    #     res = await self.bot.session.get(result)
    #     html = await res.text()
    #     soup = BeautifulSoup(html, 'html.parser')
    #     form = soup.find_all('form')
    #     inputs = form[1].find_all('option')
    #     value = inputs[0]["value"]
    #     url = img_url.format(world, value)
    #     resp2 = await self.bot.session.get(url)
    #     cache = await resp2.read()
    #     with Image.open(BytesIO(cache)) as img:
    #         dis = 310
    #         h, w = img.height, img.width
    #         img = img.crop((0 + dis, 0 + dis, w - dis, h - dis))
    #         file = BytesIO()
    #         img.save(file, "png")
    #         file.seek(0)
    #
    #     await ctx.send(file=discord.File(file, f"{world}_map.png"))

    @commands.command(name="nude", aliases=["nacktfoto"])
    @commands.cooldown(1, 10.0, commands.BucketType.member)
    async def nude_(self, ctx, *, user: DSObject = None):

        world = load.get_world(ctx.channel, True)
        base_player = f"https://de{world}.die-staemme.de/guest.php?screen=info_"

        # ----- Random Player Picture -----#
        if user:

            # ----- Picture of the Given Player -----#
            insert = 'player' if user.alone else 'ally'
            result_link = f"{base_player}{insert}&id={user.id}"
            resp = await self.bot.session.get(result_link)
            data = await resp.read()
            soup = BeautifulSoup(data, "html.parser")
            result = soup.find(alt="Profilbild") if user.alone else soup.find("img")
            if not result:
                msg = "Glaub mir, die Nudes von `{}` willst du nicht!"
                return await ctx.send(msg.format(user.name))

        else:
            await ctx.trigger_typing()
            while True:
                idr = await load.random_id(world)
                result_link = f"{base_player}player&id={idr.id}"
                resp = await self.bot.session.get(result_link)
                data = await resp.read()
                soup = BeautifulSoup(data, "html.parser")
                result = soup.find(alt="Profilbild")
                if not result:
                    continue
                elif str(result).__contains__("/avatar/"):
                    continue
                else:
                    break

        resp2 = await self.bot.session.get(result['src'])
        img = await resp2.read()
        file = BytesIO()
        file.write(img)
        file.seek(0)
        await ctx.send(file=discord.File(file, "userpic.gif"))

    @commands.command(name="emoji", aliases=["cancer"])
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji_(self, ctx):
        guild = self.bot.get_guild(213992901263228928)
        cache = 0
        for emo in self.emo_list:
            if emo in [e.name for e in ctx.guild.emojis]:
                continue
            emoji = discord.utils.get(guild.emojis, name=emo)
            async with self.bot.session.get(emoji.url) as resp2:
                img = await resp2.read()
                img = bytearray(img)
            await ctx.guild.create_custom_emoji(name=emo, image=img)
            cache += 1

        await ctx.send(f"`{cache}/12` Emojis wurden hinzugefügt.")

    # @map_.error
    # async def map_error(self, ctx, error):
    #     await ctx.send(f"Huch, das sieht gar nicht gut aus!\n{error}")

    @avatar_.error
    async def avatar_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=error_embed(f"Die URL fehlt."))
        if hasattr(error, "original"):
            print(type(error))
            if isinstance(error.original, (ValueError, OSError)):
                msg = "Du musst eine gültige URL angeben"
                return await ctx.send(embed=error_embed(msg))


def setup(bot):
    bot.add_cog(Graphic(bot))
