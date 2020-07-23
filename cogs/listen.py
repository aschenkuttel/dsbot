from PIL import Image, ImageChops
from discord.ext import commands
from collections import Counter
from datetime import timedelta
from bs4 import BeautifulSoup
import traceback
import logging
import discord
import aiohttp
import imgkit
import random
import utils
import sys
import io
import re

logger = logging.getLogger('dsbot')


class Listen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cap = 10
        self.blacklist = []
        self.cmd_counter = Counter()
        self.silenced = (commands.UnexpectedQuoteError,
                         commands.BadArgument,
                         aiohttp.InvalidURL,
                         discord.Forbidden,
                         utils.IngameError)

    async def called_by_hour(self):
        query = 'INSERT INTO usage_data(name, usage) VALUES($1, $2) ' \
                'ON CONFLICT (name) DO UPDATE SET usage = usage_data.usage + $2'

        data = [(k, v) for k, v in self.cmd_counter.items()]
        if not data:
            return

        async with self.bot.ress.acquire() as conn:
            await conn.executemany(query, data)

        self.cmd_counter.clear()

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

        if message.author.id in self.blacklist:
            return

        self.bot.active_guilds.add(message.guild.id)

        world = self.bot.config.get_world(message.channel)
        if not world:
            return

        pre = self.bot.config.get_prefix(message.guild.id)
        if message.content.lower().startswith(pre.lower()):
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
                logger.debug("report converted")
                return

        # Coord Converter
        result = re.findall(r'\d\d\d\|\d\d\d', message.content)
        if result:

            result = set(result)
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

                good.append(f"{vil.mention} {owner}")
                result.remove(f"{vil.x}|{vil.y}")

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
                logger.debug("coord converted")
                return

        # DS Player/Tribe Converter
        if "|" not in message.content:
            return

        content = message.clean_content
        mentions = message.mentions.copy()
        mentions.extend(message.role_mentions)
        mentions.extend(message.channel_mentions)

        for mention in mentions:
            if isinstance(mention, discord.Member):
                raw = f"@{mention.display_name}"
            else:
                raw = f"@{mention.name}"
            content = content.replace(raw, "")

        names = re.findall(r'(?<!\|)\|([\w][^|]*?)\|(?!\|)', message.clean_content)
        if names:
            parsed_msg = message.clean_content.replace("`", "")
            ds_objects = await self.bot.fetch_bulk(world, names[:10], name=True)
            cache = await self.bot.fetch_bulk(world, names[:10], 1, name=True)
            ds_objects.extend(cache)

            found_names = {}
            for dsobj in ds_objects:
                found_names[dsobj.name.lower()] = dsobj
                if not dsobj.alone:
                    found_names[dsobj.tag.lower()] = dsobj

            for name in names:
                dsobj = found_names.get(name.lower())
                if not dsobj:
                    failed = f"**{name}**<:failed:708982292630077450>"
                    parsed_msg = parsed_msg.replace(f"|{name}|", failed)

                else:
                    parsed_msg = parsed_msg.replace(f"|{name}|", dsobj.mention)

            current = message.created_at + timedelta(hours=1)
            time = current.strftime("%H:%M Uhr")
            title = f"{message.author.display_name} um {time}"
            embed = discord.Embed(description=parsed_msg)
            embed.set_author(name=title, icon_url=message.author.avatar_url)

            try:
                await message.channel.send(embed=embed)
                if not mentions:
                    await message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
            finally:
                logger.debug("bbcode converted")

    @commands.Cog.listener()
    async def on_command(self, ctx):
        cid, cmd = (ctx.message.id, ctx.message.content)
        logger.debug(f"command invoked [{cid}]: {cmd}")

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        cid, cmd = (ctx.message.id, ctx.invoked_with)
        logger.debug(f"command completed [{cid}]")

        if ctx.author.id != self.bot.owner_id:
            self.cmd_counter[str(ctx.command)] += 1

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self.bot.config.remove_guild(guild.id)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        cmd = ctx.invoked_with
        msg, tip = None, None

        logger.debug(f"command error [{ctx.message.id}]: {error}")

        error = getattr(error, 'original', error)
        if isinstance(error, self.silenced):
            return

        elif isinstance(error, commands.CommandNotFound):
            if len(cmd) == cmd.count(ctx.prefix):
                return
            else:
                data = random.choice(self.bot.msg["noCommand"])
                return await ctx.send(data.format(f"{ctx.prefix}{cmd}"))

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
            msg = base.format(utils.seperator(error.purse))

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

        elif isinstance(error, utils.MemberConverterNotFound):
            msg = f"`{error.name}` konnte nicht gefunden werden"

        elif isinstance(error, commands.BotMissingPermissions):
            msg = f"Dem Bot fehlen folgende Rechte auf diesem Server:\n" \
                  f"`{', '.join(error.missing_perms)}`"
        elif isinstance(error, commands.ExpectedClosingQuoteError):
            msg = "Ein Argument wurde mit einem Anführungszeichen begonnen und nicht geschlossen"

        if msg:
            try:
                embed = utils.error_embed(msg, ctx=tip)
                await ctx.send(embed=embed)
            except discord.Forbidden:
                msg = "Dem Bot fehlen benötigte Rechte: `Embed Links`"
                await ctx.safe_send(msg)

        else:
            print(f"Command Message: {ctx.message.content}")
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
            logger.warning(f"uncommon error ({ctx.server}): {ctx.message.content}")


def setup(bot):
    bot.add_cog(Listen(bot))
