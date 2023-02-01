from discord.ext import commands, tasks
from discord import app_commands
from collections import Counter
import traceback
import logging
import discord
import aiohttp
import utils
import math
import sys

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

    async def on_app_command_error(self, interaction, error):
        print(type(error))
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
