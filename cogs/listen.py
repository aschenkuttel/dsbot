from PIL import Image, ImageChops
from discord.ext import commands
from datetime import timedelta
from bs4 import BeautifulSoup
import traceback
import discord
import aiohttp
import imgkit
import random
import utils
import sys
import io
import re


class Listen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cap = 10
        self.blacklist = []
        self.last_message = {}
        self.silenced = (commands.BadArgument,
                         aiohttp.InvalidURL,
                         discord.Forbidden,
                         utils.IngameError)

    # Report HTML to Image Converter
    def html_lover(self, raw_data):
        soup = BeautifulSoup(raw_data, 'html.parser')
        tiles = soup.body.find_all(class_='vis')
        if len(tiles) < 2:
            return
        main = f"{utils.whymtl}<head></head>{tiles[1]}"
        css = f"{self.bot.data_path}/report.css"
        img_bytes = imgkit.from_string(main, False, options=utils.imgkit, css=css)

        # crops empty background
        im = Image.open(io.BytesIO(img_bytes))
        bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
        diff = ImageChops.difference(im, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        im = im.crop(diff.getbbox())

        # crops border and saves to FileIO
        result = im.crop((2, 2, im.width - 2, im.height - 2))
        file = io.BytesIO()
        result.save(file, 'png')
        file.seek(0)
        return file

    async def fetch_report(self, content):
        try:
            async with self.bot.session.get(content) as res:
                data = await res.text()
        except (aiohttp.InvalidURL, ValueError):
            return

        file = await self.bot.execute(self.html_lover, data)
        return file

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if not message.guild:
            return

        self.bot.last_message.add(message.guild.id)

        if message.author.id in self.blacklist:
            return

        world = self.bot.config.get_world(message.channel)
        if not world:
            return

        # Report Converter
        if message.content.__contains__("public_report"):
            file = await self.fetch_report(message.content)
            if file is None:
                return await utils.silencer(message.add_reaction('❌'))
            try:
                await message.channel.send(file=discord.File(file, "report.png"))
                await message.delete()
            except discord.Forbidden:
                pass
            finally:
                return

        # Coord Converter
        result = re.findall(r'\d\d\d\|\d\d\d', message.content)
        if result:

            result = set(result)
            pre = self.bot.config.get_prefix(message.guild.id)
            if message.content.lower().startswith(pre.lower()):
                return

            coords = [obj.replace('|', '') for obj in result]
            villages = await self.bot.fetch_bulk(world, coords, "village", name=True)
            player_ids = [obj.player_id for obj in villages]
            players = await self.bot.fetch_bulk(world, player_ids, dic=True)
            good = []
            for vil in villages:

                player = players.get(vil.player_id)
                if player:
                    owner = f"[{player.name}]"
                else:
                    owner = "[Barbarendorf]"

                coord = f"{vil.x}|{vil.y}"
                good.append(f"[{coord}]({vil.ingame_url}) {owner}")
                result.remove(coord)

            found = '\n'.join(good)
            lost = ','.join(result)
            if found:
                found = f"**Gefundene Koordinaten:**\n{found}"
            if lost:
                lost = f"**Nicht gefunden:**\n{lost}"
            em = discord.Embed(description=f"{found}\n{lost}")
            try:
                await message.channel.send(embed=em)
            except discord.Forbidden:
                pass
            finally:
                return

        # DS Player/Tribe Converter
        names = re.findall(r'<(.*?)>', message.clean_content)
        emojis = re.findall(r'<a?:[a-zA-Z0-9_]+:([0-9]+)>', message.content)

        for idc in emojis:
            for name in names.copy():
                if idc in name:
                    names.remove(name)

        if names:
            names = names[:10]
            parsed_msg = message.clean_content.replace("`", "")
            ds_objects = await self.bot.fetch_bulk(world, names, name=True)
            cache = await self.bot.fetch_bulk(world, names, 1, name=True)
            ds_objects.extend(cache)

            found_names = {}
            for dsobj in ds_objects:
                found_names[dsobj.name.lower()] = dsobj
                if not dsobj.alone:
                    found_names[dsobj.tag.lower()] = dsobj

            for name in names:
                dsobj = found_names.get(name.lower())
                if not dsobj:
                    parsed_msg = parsed_msg.replace(f"<{name}>", "[Unknown]")
                    continue

                correct_name = dsobj.name if dsobj.alone else dsobj.tag
                hyperlink = f"[{correct_name}]({dsobj.ingame_url})"
                parsed_msg = parsed_msg.replace(f"<{name}>", hyperlink)

            current = message.created_at + timedelta(hours=1)
            time = current.strftime("%H:%M Uhr")
            title = f"{message.author.display_name} um {time}"
            embed = discord.Embed(description=parsed_msg)
            embed.set_author(name=title, icon_url=message.author.avatar_url)
            try:
                await message.channel.send(embed=embed)
                await message.delete()
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        if ctx.author.id == self.bot.owner_id:
            return
        else:
            await self.bot.save_usage(ctx.invoked_with)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self.bot.config.remove_guild(guild.id)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        msg, tip = None, None
        error = getattr(error, 'original', error)
        if isinstance(error, self.silenced):
            return

        elif isinstance(error, commands.CommandNotFound):
            if len(ctx.invoked_with) == ctx.invoked_with.count(ctx.prefix):
                return
            else:
                data = random.choice(self.bot.msg["noCommand"])
                return await ctx.send(data.format(f"{ctx.prefix}{ctx.invoked_with}"))

        elif isinstance(error, commands.MissingRequiredArgument):
            msg = "Dem Command fehlt ein benötigtes Argument"
            tip = ctx

        elif isinstance(error, commands.NoPrivateMessage):
            msg = "Der Command ist leider nur auf einem Server verfügbar"

        elif isinstance(error, commands.PrivateMessageOnly):
            msg = "Der Command ist leider nur per private Message verfügbar"

        elif isinstance(error, utils.DontPingMe):
            msg = "Schreibe anstatt eines Pings den Usernamen oder Nickname"
            tip = ctx

        elif isinstance(error, utils.WorldMissing):
            msg = "Der Server hat noch keine zugeordnete Welt\n" \
                  f"Dies kann nur der Admin mit `{ctx.prefix}set world`"

        elif isinstance(error, utils.UnknownWorld):
            msg = "Diese Welt existiert leider nicht."
            if error.possible:
                msg += f"\nMeinst du möglicherweise: `{error.possible}`"
            tip = ctx

        elif isinstance(error, utils.WrongChannel):
            if error.type == "game":
                channel = self.bot.config.get_item(ctx.guild.id, "game")
                return await ctx.send(f"<#{channel}>")

            else:
                msg = "Du befindest dich nicht in einem Eroberungschannel"

        elif isinstance(error, utils.GameChannelMissing):
            msg = "Der Server hat keinen Game-Channel\n" \
                  f"Nutze `{ctx.prefix}set game` um einen festzulegen"

        elif isinstance(error, utils.MissingGucci):
            base = "Du hast nur `{} Eisen` auf dem Konto"
            msg = base.format(utils.pcv(error.purse))

        elif isinstance(error, utils.InvalidBet):
            base = "Der Einsatz muss zwischen {} und {} Eisen liegen"
            msg = base.format(error.low, error.high)

        elif isinstance(error, commands.NotOwner):
            msg = "Diesen Command kann nur der Bot-Owner ausführen"

        elif isinstance(error, commands.MissingPermissions):
            msg = "Diesen Command kann nur ein Server-Admin ausführen"

        elif isinstance(error, commands.CommandOnCooldown):
            raw = "Command Cooldown: Versuche es in {0:.1f} Sekunden erneut"
            msg = raw.format(error.retry_after)

        elif isinstance(error, utils.DSUserNotFound):
            msg = f"`{error.name}` konnte auf {ctx.world} nicht gefunden werden"

        elif isinstance(error, utils.GuildUserNotFound):
            msg = f"`{error.name}` konnte nicht gefunden werden"

        elif isinstance(error, commands.BotMissingPermissions):
            msg = f"Dem Bot fehlen folgende Rechte auf diesem Server:\n" \
                  f"`{', '.join(error.missing_perms)}`"

        if msg:
            try:
                embed = utils.error_embed(msg, ctx=tip)
                await ctx.send(embed=embed)
            except discord.Forbidden:
                msg = "Dem Bot fehlen benötigte Rechte: `Embed Links`"
                await ctx.safe_send(msg)

        else:
            print(f"Command Message: {ctx.message.content}")
            print("Command Error:")
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


def setup(bot):
    bot.add_cog(Listen(bot))
