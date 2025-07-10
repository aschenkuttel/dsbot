from discord.ext import commands, tasks
from discord import app_commands
from collections import Counter
from datetime import datetime
import traceback
import logging
import discord
import aiohttp
import utils
import math
import sys
import re

logger = logging.getLogger('dsbot')


class Listen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.tree.on_error = self.on_app_command_error
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

    @tasks.loop(hours=168)
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
        if message.author.bot or message.guild is None:
            return

        self.active_guilds.add(message.guild.id)
        inactive = self.bot.config.get('inactive', message.guild.id)

        if inactive:
            self.bot.config.update('inactive', False, message.guild.id)

        server = self.bot.config.get_world(message.channel)

        if server is None:
            return

        content = message.clean_content
        convert_cog = self.bot.get_cog('Convert')

        if convert_cog is None:
            raise Exception("convert cog not found")

        # report conversion
        report_urls = re.findall(r'https://.+/public_report/\S*', content)

        if report_urls and self.bot.config.get_switch('report', message.guild.id):
            io_file = await convert_cog.report_to_img(report_urls[0])

            if io_file is None:
                await utils.silencer(message.add_reaction('❌'))
                logger.debug(f"report could not be converted: {report_urls[0]}")
            else:
                file = discord.File(io_file, "report.png")
                await self.send_convert(message, file, file=True, delete=True)
                logger.debug("report converted")

            return

        # coordinate conversion
        coordinates = re.findall(r'\d\d\d\|\d\d\d', content)

        if coordinates and self.bot.config.get_switch('coord', message.guild.id):
            # set imitation workaround to preserve the order of coordinates
            coords = list(dict.fromkeys(c for c in coordinates))
            content = await convert_cog.parse_coords(coords, server)
            embed = discord.Embed(description=content, color=0xcbba99)
            await self.send_convert(message, embed)
            logger.debug("coord converted")
            return

        # ds mention converter
        names = re.findall(r'(?<!\|)\|(\S[^|]*?)\|(?!\|)', content)

        if names and self.bot.config.get_switch('mention', message.guild.id):
            parsed_msg = content.replace("`", "")

            ds_objects = await self.bot.fetch_bulk(server, names[:10], name=True)
            cache = await self.bot.fetch_bulk(server, names[:10], 1, name=True)
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
            embed = discord.Embed(description=parsed_msg, color=0xcbba99)
            embed.set_author(name=title, icon_url=message.author.display_avatar.url)
            await self.send_convert(message, embed, delete=not mentions)
            logger.debug("bbcode converted")


    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        logger.debug(f"command error: {error}")

    async def on_app_command_error(self, interaction, error):
        logger.debug(f"command error [{interaction.full_command_name}]: {error}")
        ephemeral = True
        no_embed = False

        if isinstance(error, app_commands.CommandOnCooldown):
            base = "Cooldown: Versuche es in `{0:.1f}` Sekunden erneut"
            msg = base.format(error.retry_after)
            ephemeral = False

        elif isinstance(error, app_commands.MissingPermissions):
            msg = "Diesen Command kann nur ein Server-Admin ausführen"

        elif isinstance(error, utils.DontPingMe):
            msg = "Schreibe anstatt eines Pings den Usernamen oder Nickname"

        elif isinstance(error, utils.MemberNotFound):
            msg = f"`{error.name}` konnte nicht gefunden werden"

        elif isinstance(error, utils.DSUserNotFound):
            msg = f"`{error.name}` konnte auf {interaction.world} nicht gefunden werden"
            ephemeral = False

        elif isinstance(error, utils.SilentError):
            msg = "Silent Cooldown"

        elif isinstance(error, utils.MissingRequiredKey):
            title = f"Es fehlt einer folgender Keys:"

            result = [title]
            if len(error.keys) < 5:
                batches = ["|".join(error.keys)]
            else:
                index = math.ceil(len(error.keys) / 2)
                batches = utils.show_list(error.keys, "|", index, return_iter=True)

            for batch in batches:
                result.append(f"`<{batch}>`")

            msg = "\n".join(result)

        elif isinstance(error, utils.UnknownWorld):
            msg = "Diese Welt existiert leider nicht"

            if error.possible_world:
                msg += f"\nMeinst du möglicherweise: `{error.possible_world}`"

        elif isinstance(error, utils.InvalidCoordinate):
            msg = "Du musst eine gültige Koordinate angeben"

        elif isinstance(error, utils.WrongChannel):
            if error.type == 'game':
                channel_ids = [self.bot.config.get('game', interaction.guild.id)]

            else:
                raw_ids = self.bot.config.get('conquer', interaction.guild.id)
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
            ephemeral = False
            no_embed = True

        elif isinstance(error, utils.GameChannelMissing):
            msg = "Der Server hat noch keinen Game Channel eingerichtet,\n" \
                  f"dies kann ein Admin mit `/set game` im gewünschten Channel"
            ephemeral = False

        elif isinstance(error, utils.ConquerChannelMissing):
            msg = "Der Server hat noch keinen Conquer Channel eingerichtet,\n" \
                  f"dies kann ein Admin mit `/set conquer` im gewünschten Channel"
            ephemeral = False

        elif isinstance(error, utils.MissingGucci):
            base = "Du hast nur `{} Eisen` auf dem Konto"
            msg = base.format(utils.seperator(error.purse))
            ephemeral = False

        else:
            print(f"Command: {interaction.command.name} Args: {interaction.namespace}")
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
            logger.warning(f"uncommon error ({interaction.server}): {interaction.command.name}")
            return

        if msg is None:
            msg = "Upps, da ist wohl etwas schief gelaufen..."

        if no_embed:
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            embed = utils.error_embed(msg)
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction, command):
        logger.debug(f"command completed [{command.name}]")

        if interaction.user.id != self.bot.owner_id:
            if interaction.command.parent is not None:
                cmd_name = interaction.command.parent.name
            else:
                cmd_name = interaction.command.name

            self.cmd_counter[cmd_name] += 1

        if interaction.guild is None:
            return

        self.active_guilds.add(interaction.guild.id)
        inactive = self.bot.config.get('inactive', interaction.guild.id)

        # TODO remove after some time
        if inactive:
            self.bot.config.update('inactive', False, interaction.guild.id)

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


async def setup(bot):
    await bot.add_cog(Listen(bot))
