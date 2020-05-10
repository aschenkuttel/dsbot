from utils import error_embed, DSConverter
from PIL import Image, ImageSequence
from discord.ext import commands
from bs4 import BeautifulSoup
from io import BytesIO
import discord
import aiohttp
import os


class Graphic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emojis = {}
        self.setup_emojis()

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

    def setup_emojis(self):
        path = f"{self.bot.data_path}/emojis/"
        for file in os.listdir(path):
            with open(f"{path}/{file}", 'rb') as pic:
                img = bytearray(pic.read())
                name = file.split(".")[0]
            self.emojis[name] = img

    @commands.command(name="avatar")
    async def avatar_(self, ctx, url):

        async with self.bot.session.get(url) as r:
            avatar_bytes = await r.read()

        img = Image.open(BytesIO(avatar_bytes))
        if img.size[0] <= 270 and img.size[1] <= 180:
            msg = "Das angegebene Bild ist bereits klein genug"
            return await ctx.send(embed=error_embed(msg))

        output_buffer = BytesIO()
        if img.format == "GIF":
            frames = ImageSequence.Iterator(img)
            frames = await self.bot.execute(self.gif_resize, frames)
            om = next(frames)
            om.save(output_buffer, "gif", save_all=True, append_images=list(frames), quality=90)
            filename = "avatar.gif"

        else:
            img = await self.bot.execute(self.img_resize, img)
            img.save(output_buffer, "png", quality=90)
            filename = "avatar.png"

        output_buffer.seek(0)
        file = discord.File(fp=output_buffer, filename=filename)
        await ctx.author.send(file=file)
        await ctx.private_hint()

    @commands.command(name="nude", aliases=["profilbild"])
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def nude_(self, ctx, *, user: DSConverter = None):
        if user:
            async with self.bot.session.get(user.guest_url) as res:
                data = await res.read()
            soup = BeautifulSoup(data, "html.parser")
            result = soup.find(alt="Profilbild") if user.alone else soup.find("img")
            if not result:
                msg = "Glaub mir, die Nudes von `{}` willst du nicht!"
                return await ctx.send(msg.format(user.name))

        else:
            await ctx.trigger_typing()
            for _ in range(0, 30):
                user = await self.bot.fetch_random(ctx.server)
                async with self.bot.session.get(user.guest_url) as res:
                    data = await res.read()
                soup = BeautifulSoup(data, "html.parser")
                result = soup.find(alt="Profilbild")
                if not result:
                    continue
                elif str(result).__contains__("/avatar/"):
                    continue
                break
            else:
                msg = "Die maximale Anzahl von Versuchen wurden erreicht"
                return await ctx.send(embed=error_embed(msg))

        async with self.bot.session.get(result['src']) as res2:
            img = await res2.read()

        file = BytesIO(img)
        await ctx.send(file=discord.File(file, "userpic.gif"))

    @commands.command(name="emoji", aliases=["cancer"])
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji_(self, ctx):
        counter = 0
        for name, emoji in self.emojis.items():
            if name in [e.name for e in ctx.guild.emojis]:
                continue
            await ctx.guild.create_custom_emoji(name=name, image=emoji)
            counter += 1
        await ctx.send(f"`{counter}/{len(self.emojis)}` Emojis wurden hinzugefügt")

    @avatar_.error
    async def avatar_error(self, ctx, error):
        if hasattr(error, "original"):
            badboys = ValueError, OSError, aiohttp.InvalidURL
            if isinstance(error.original, badboys):
                msg = "Du musst eine gültige URL angeben"
                await ctx.send(embed=error_embed(msg))


def setup(bot):
    bot.add_cog(Graphic(bot))
