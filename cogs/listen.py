from PIL import Image, ImageChops
from discord.ext import commands
from collections import Counter
from datetime import datetime
from bs4 import BeautifulSoup
import traceback
import logging
import discord
import aiohttp
import imgkit
import random
import utils
import math
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
                         utils.IngameError,
                         utils.SilentError)

    async def called_per_hour(self):
        async with self.bot.ress.acquire() as conn:
            await self.update_usage(conn)
            await self.update_members(conn)

    async def update_usage(self, conn):
        query = 'INSERT INTO usage(name, amount) VALUES($1, $2) ' \
                'ON CONFLICT (name) DO UPDATE SET amount = usage.amount + $2'

        data = [(k, v) for k, v in self.cmd_counter.items()]
        if not data:
            return

        await conn.executemany(query, data)
        self.cmd_counter.clear()

    async def update_members(self, conn):
        args = []
        for members in self.bot.members.values():
            for member in members.values():
                args.append(member.arguments)

        query = 'INSERT INTO member (id, guild_id, name, nick, last_update) ' \
                'VALUES ($1, $2, $3, $4, $5) ' \
                'ON CONFLICT (id, guild_id) DO UPDATE SET ' \
                'name = $3, nick = $4, last_update = $5'

        await conn.executemany(query, args)

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

        guild_id = message.guild.id
        self.bot.active_guilds.add(guild_id)

        world = self.bot.config.get_world(message.channel)
        if world is None:
            return

        pre = self.bot.config.get_prefix(guild_id)
        if message.content.lower().startswith(pre.lower()):
            return

        content = message.clean_content

        # report conversion
        report_urls = re.findall(r'https://.+/public_report/\S*', content)
        if report_urls and self.bot.config.get_switch('report', guild_id):
            file = await self.fetch_report(report_urls[0])

            if file is None:
                await utils.silencer(message.add_reaction('❌'))
                return

            try:
                await message.channel.send(file=discord.File(file, "report.png"))
                await message.delete()
            except discord.Forbidden:
                pass
            finally:
                self.bot.update_member(message.author)
                logger.debug("report converted")
                return

        # coordinate conversion
        coordinates = re.findall(r'\d\d\d\|\d\d\d', content)
        if coordinates and self.bot.config.get_switch('coord', guild_id):
            coords = set(coordinates)
            villages = await self.bot.fetch_bulk(world, coords, 2, name=True)
            player_ids = [obj.player_id for obj in villages]
            players = await self.bot.fetch_bulk(world, player_ids, dictionary=True)
            good = []

            for village in villages:
                player = players.get(village.player_id)

                if player:
                    owner = f"[{player.name}]"
                else:
                    owner = "[Barbarendorf]"

                good.append(f"{village.mention} {owner}")
                coords.remove(village.coords)

            found = '\n'.join(good)
            lost = ', '.join(coords)
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
                self.bot.update_member(message.author)
                logger.debug("coord converted")
                return

        # ds mention converter
        names = re.findall(r'(?<!\|)\|([\S][^|]*?)\|(?!\|)', content)
        if names and self.bot.config.get_switch('mention', guild_id):
            parsed_msg = message.clean_content.replace("`", "")
            ds_objects = await self.bot.fetch_bulk(world, names[:10], name=True)
            cache = await self.bot.fetch_bulk(world, names[:10], 1, name=True)
            ds_objects.extend(cache)

            mentions = message.mentions.copy()
            mentions.extend(message.role_mentions)
            mentions.extend(message.channel_mentions)

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

            current = datetime.now()
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
                self.bot.update_member(message.author)
                logger.debug("bbcode converted")

    @commands.Cog.listener()
    async def on_command(self, ctx):
        cid, cmd = (ctx.message.id, ctx.message.content)
        logger.debug(f"command invoked [{cid}]: {cmd}")

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        logger.debug(f"command completed [{ctx.message.id}]")

        if ctx.author.id != self.bot.owner_id:
            if ctx.command.parent is not None:
                cmd = str(ctx.command.parent)
            else:
                cmd = str(ctx.command)

            self.cmd_counter[cmd] += 1

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self.bot.config.remove_config(guild.id)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        cmd = ctx.invoked_with
        msg, tip = None, None

        error = getattr(error, 'original', error)
        if isinstance(error, self.silenced):
            return

        logger.debug(f"command error [{ctx.message.id}]: {error}")

        if isinstance(error, commands.CommandNotFound):
            if len(cmd) == cmd.count(ctx.prefix):
                return
            else:
                data = random.choice(ctx.lang.unknown_command)
                await ctx.send(data.format(f"{ctx.prefix}{cmd}"))
                return

        elif isinstance(error, commands.MissingRequiredArgument):
            msg = "Dem Command fehlt ein benötigtes Argument"
            tip = True

        elif isinstance(error, utils.MissingRequiredKey):
            clean_cmd = f"{ctx.prefix}{cmd.lower()}"
            result = []

            index = math.ceil(len(error.keys) / 2)
            batches = utils.show_list(error.keys, "|", index, return_iter=True)
            for batch in batches:
                result.append(f"`{clean_cmd} <{batch}>`")

            msg = "\n".join(result)
            tip = True

        elif isinstance(error, commands.NoPrivateMessage):
            msg = "Der Command ist leider nur auf einem Server möglich"

        elif isinstance(error, commands.PrivateMessageOnly):
            msg = "Der Command ist leider nur per private Message möglich"

        elif isinstance(error, utils.DontPingMe):
            msg = "Schreibe anstatt eines Pings den Usernamen oder Nickname"
            tip = True

        elif isinstance(error, utils.WorldMissing):
            msg = "Der Server hat noch keine zugeordnete Welt\n" \
                  f"Dies kann nur der Admin mit `{ctx.prefix}set world`"

        elif isinstance(error, utils.UnknownWorld):
            msg = "Diese Welt existiert leider nicht."
            tip = True

            if error.possible_world:
                msg += f"\nMeinst du möglicherweise: `{error.possible_world}`"

        elif isinstance(error, utils.InvalidCoordinate):
            msg = "Du musst eine gültige Koordinate angeben"

        elif isinstance(error, utils.WrongChannel):
            if error.type == 'game':
                channel_id = self.bot.config.get('game', ctx.guild.id)
                await ctx.send(f"<#{channel_id}>")
                return

            elif error.type == 'conquer':
                msg = "Du befindest dich nicht in einem Eroberungschannel"

        elif isinstance(error, utils.GameChannelMissing):
            msg = "Der Server hat keinen Game-Channel\n" \
                  f"Nutze `{ctx.prefix}set game` um einen festzulegen"

        elif isinstance(error, utils.MissingGucci):
            base = "Du hast nur `{} Eisen` auf dem Konto"
            msg = base.format(utils.seperator(error.purse))

        elif isinstance(error, utils.InvalidBet):
            base = "Der Einsatz muss zwischen {} und {} Eisen liegen"
            msg = base.format(error.min, error.max)

        elif isinstance(error, commands.NotOwner):
            msg = "Diesen Command kann nur der Bot-Owner ausführen"

        elif isinstance(error, commands.MissingPermissions):
            msg = "Diesen Command kann nur ein Server-Admin ausführen"

        elif isinstance(error, commands.CommandOnCooldown):
            raw = "Command Cooldown: Versuche es in {0:.1f} Sekunden erneut"
            msg = raw.format(error.retry_after)

        elif isinstance(error, utils.DSUserNotFound):
            msg = f"`{error.name}` konnte auf {ctx.world} nicht gefunden werden"

        elif isinstance(error, utils.MemberNotFound):
            msg = f"`{error.name}` konnte nicht gefunden werden"

        elif isinstance(error, commands.BotMissingPermissions):
            base = "Dem Bot fehlen folgende Rechte auf diesem Server:\n`{}`"
            msg = base.format(', '.join(error.missing_perms))

        elif isinstance(error, commands.ExpectedClosingQuoteError):
            msg = "Ein Argument wurde mit einem Anführungszeichen begonnen und nicht geschlossen"

        if msg:
            try:
                context = ctx if tip is True else None
                embed = utils.error_embed(msg, ctx=context)
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
