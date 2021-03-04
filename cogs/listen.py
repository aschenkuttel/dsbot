from discord.ext import commands, tasks
from PIL import Image, ImageChops
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
                         aiohttp.InvalidURL,
                         discord.Forbidden,
                         utils.SilentError)
        self.active_guilds = set()
        self.guild_timeout.start()

    async def called_per_hour(self):
        async with self.bot.member_pool.acquire() as conn:
            await self.update_usage(conn)
            await self.update_members(conn)

    @tasks.loop(hours=120)
    async def guild_timeout(self):
        if self.bot.is_locked():
            return

        counter = 0
        for guild in self.bot.guilds:
            if guild.id not in self.active_guilds:
                self.bot.config.update('inactive', True, guild.id, bulk=True)
                counter += 1

        self.bot.config.save()
        self.active_guilds.clear()
        logger.debug(f"{counter} inactive guilds")

    async def update_usage(self, conn):
        if not self.cmd_counter:
            return

        query = 'INSERT INTO usage(name, amount) ' \
                'VALUES($1, $2) ' \
                'ON CONFLICT (name) DO UPDATE SET ' \
                'amount = usage.amount + $2'
        await conn.executemany(query, self.cmd_counter.items())
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
    def html_to_image(self, raw_data):
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

        file = await self.bot.execute(self.html_to_image, data)
        return file

    async def send_convert(self, message, pkg, file=False, delete=False):
        try:
            if file is True:
                await message.channel.send(file=pkg)
            else:
                await message.channel.send(embed=pkg)

            if delete is True:
                await message.delete()

        except (discord.Forbidden, discord.NotFound):
            pass

        finally:
            self.bot.update_member(message.author)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.guild is None:
            return

        if message.author.id in self.blacklist:
            return

        guild_id = message.guild.id
        self.active_guilds.add(guild_id)

        world = self.bot.config.get_world(message.channel)
        if world is None:
            return

        pre = self.bot.command_prefix(self.bot, message)
        if message.content.startswith(pre):
            return

        content = message.clean_content

        # report conversion
        report_urls = re.findall(r'https://.+/public_report/\S*', content)
        if report_urls and self.bot.config.get_switch('report', guild_id):
            file = await self.fetch_report(report_urls[0])

            if file is None:
                await utils.silencer(message.add_reaction('❌'))
                return

            await self.send_convert(message, file, file=True, delete=True)
            logger.debug("report converted")

        # coordinate conversion
        coordinates = re.findall(r'\d\d\d\|\d\d\d', content)
        if coordinates and self.bot.config.get_switch('coord', guild_id):
            # set imitation workaround to preserve order of coordinates
            coords = list(dict.fromkeys(c for c in coordinates))
            villages = await self.bot.fetch_bulk(world, coords, 2, name=True)
            village_dict = {str(vil): vil for vil in villages}

            player_ids = [obj.player_id for obj in villages]
            players = await self.bot.fetch_bulk(world, player_ids, dictionary=True)

            found_villages = []

            for coord in coords.copy():
                village = village_dict.get(coord)
                if village is None:
                    continue

                player = players.get(village.player_id)

                if player:
                    owner = f"[{player.name}]"
                else:
                    owner = "[Barbarendorf]"

                found_villages.append(f"{village.mention} {owner}")
                coords.remove(village.coords)

            if existing := '\n'.join(found_villages):
                existing = f"**Gefundene Koordinaten:**\n{existing}"
            if remaining := ', '.join(coords):
                remaining = f"**Nicht gefunden:**\n{remaining}"

            embed = discord.Embed(description=f"{existing}\n{remaining}")
            await self.send_convert(message, embed)
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

            time = datetime.now().strftime("%H:%M Uhr")
            title = f"{message.author.display_name} um {time}"
            embed = discord.Embed(description=parsed_msg)
            embed.set_author(name=title, icon_url=message.author.avatar_url)

            await self.send_convert(message, embed, delete=not mentions)
            logger.debug("bbcode converted")

    @commands.Cog.listener()
    async def on_command(self, ctx):
        cid, cmd = (ctx.message.id, ctx.message.content)
        logger.debug(f"command invoked [{cid}]: {cmd}")

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        logger.debug(f"command completed [{ctx.message.id}]")

        if ctx.author.id == self.bot.owner_id:
            if ctx.command.parent is not None:
                cmd = str(ctx.command.parent)
            else:
                cmd = str(ctx.command)

            self.cmd_counter[cmd] += 1

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        self.active_guilds.add(guild.id)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self.bot.config.remove_config(guild.id)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        for config in ('conquer', 'channel'):
            subconfig = self.bot.config.get(config, channel.guild.id)
            if subconfig and str(channel.id) in subconfig:
                subconfig.pop(str(channel.id))

        game_channel_id = self.bot.config.get('game', channel.guild.id)
        if game_channel_id == channel.id:
            self.bot.config.remove('game', channel.guild.id, bulk=True)

        self.bot.config.save()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, 'original', error)
        if isinstance(error, self.silenced):
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            error = utils.MissingRequiredArgument()
        elif isinstance(error, commands.BadArgument):
            error = utils.BadArgument()

        logger.debug(f"command error [{ctx.message.id}]: {error}")
        cmd = ctx.invoked_with

        if isinstance(error, commands.CommandNotFound):
            if len(cmd) == cmd.count(ctx.prefix):
                return
            else:
                data = random.choice(ctx.lang.unknown_command)
                msg = data.format(f"{ctx.prefix}{cmd}")

        elif isinstance(error, utils.MissingRequiredArgument):
            msg = f"Dem Command fehlt ein benötigtes Argument"

        elif isinstance(error, utils.BadArgument):
            msg = "Ein Argument war nicht vom erwarteten Typ"

        elif isinstance(error, utils.MissingRequiredKey):
            cmd = f"{ctx.prefix}{cmd.lower()}"

            if error.pos_arg:
                cmd += f" <{error.pos_arg}>"

            title = f"**{cmd}** fehlt ein benötigter Key:"

            result = [title]
            if len(error.keys) < 5:
                batches = ["|".join(error.keys)]
            else:
                index = math.ceil(len(error.keys) / 2)
                batches = utils.show_list(error.keys, "|", index, return_iter=True)

            for batch in batches:
                result.append(f"`<{batch}>`")

            msg = "\n".join(result)

        elif isinstance(error, commands.NoPrivateMessage):
            msg = "Der Command ist leider nur auf einem Server möglich"

        elif isinstance(error, commands.PrivateMessageOnly):
            msg = "Der Command ist leider nur per private Message möglich"

        elif isinstance(error, utils.DontPingMe):
            msg = "Schreibe anstatt eines Pings den Usernamen oder Nickname"

        elif isinstance(error, utils.WorldMissing):
            msg = "Der Server hat keine zugeordnete Welt\n" \
                  f"Dies kann ein Admin mit `{ctx.prefix}set world <world>`"

        elif isinstance(error, utils.UnknownWorld):
            msg = "Diese Welt existiert leider nicht"

            if error.possible_world:
                msg += f"\nMeinst du möglicherweise: `{error.possible_world}`"

        elif isinstance(error, utils.InvalidCoordinate):
            msg = "Du musst eine gültige Koordinate angeben"

        elif isinstance(error, utils.WrongChannel):
            if error.type == 'game':
                channel_ids = [self.bot.config.get('game', ctx.guild.id)]

            else:
                raw_ids = self.bot.config.get('conquer', ctx.guild.id)
                channel_ids = [int(channel_id) for channel_id in raw_ids]

            if not channel_ids:
                raise utils.ConquerChannelMissing()

            base = []
            for channel_id in channel_ids:
                channel = self.bot.get_channel(channel_id)

                if channel is None:
                    base.append(f"Deleted Channel ({channel_id})")
                else:
                    base.append(channel.mention)

            msg = "\n".join(base)

        elif isinstance(error, utils.GameChannelMissing):
            msg = "Der Server hat noch keinen Game Channel eingerichtet,\n" \
                  f"dies kann ein Admin mit `{ctx.prefix}set game` im gewünschten Channel"

        elif isinstance(error, utils.ConquerChannelMissing):
            msg = "Der Server hat noch keinen Conquer Channel eingerichtet,\n" \
                  f"dies kann ein Admin mit `{ctx.prefix}set conquer` im gewünschten Channel"

        elif isinstance(error, utils.MissingGucci):
            base = "Du hast nur `{} Eisen` auf dem Konto"
            msg = base.format(utils.seperator(error.purse))

        elif isinstance(error, utils.ArgumentOutOfRange):
            item = ctx.lang.error['out_of_range'][error.item]
            base = "{} darf nur einen Wert zwischen `{}` und `{}` haben"
            msg = base.format(item, error.min, error.max)

        elif isinstance(error, commands.NotOwner):
            msg = "Diesen Command kann nur der Bot-Owner ausführen"

        elif isinstance(error, commands.MissingPermissions):
            msg = "Diesen Command kann nur ein Server-Admin ausführen"

        elif isinstance(error, commands.CommandOnCooldown):
            base = "Command Cooldown: Versuche es in {0:.1f} Sekunden erneut"
            msg = base.format(error.retry_after)

        elif isinstance(error, utils.DSUserNotFound):
            msg = f"`{error.name}` konnte auf {ctx.world} nicht gefunden werden"

        elif isinstance(error, utils.MemberNotFound):
            msg = f"`{error.name}` konnte nicht gefunden werden"

        elif isinstance(error, commands.BotMissingPermissions):
            base = "Dem Bot fehlen folgende Rechte auf diesem Server:\n`{}`"
            msg = base.format(', '.join(error.missing_perms))

        elif isinstance(error, commands.ExpectedClosingQuoteError):
            msg = "Ein Argument wurde mit einem Anführungszeichen begonnen und nicht geschlossen"

        else:
            print(f"Command Message: {ctx.message.content}")
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
            logger.warning(f"uncommon error ({ctx.server}): {ctx.message.content}")
            return

        try:
            if isinstance(error, utils.HelpFailure):
                embed = utils.error_embed(msg, ctx=ctx)
                await ctx.send(embed=embed)
            elif isinstance(error, utils.EmbedFailure):
                embed = utils.error_embed(msg)
                await ctx.send(embed=embed)
            else:
                await ctx.send(msg)

        except discord.Forbidden:
            msg = "Dem Bot fehlen benötigte Rechte: `Embed Links`"
            await ctx.safe_send(msg)


def setup(bot):
    bot.add_cog(Listen(bot))
