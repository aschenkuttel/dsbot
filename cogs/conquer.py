from utils import Conquer, silencer, get_seconds, get_local_now
from discord.ext import commands
import collections
import datetime
import logging
import discord
import asyncio

logger = logging.getLogger('dsbot')


class ConquerLoop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._conquer = {}

    @commands.is_owner()
    @commands.command(name="manual")
    async def manual_(self, ctx):
        await self.called_per_hour()
        await ctx.send("manual feed done")

    # main loop called from main
    async def called_per_hour(self):
        unix = get_seconds(added_hours=-1, starting_timestamp=True)
        date = datetime.datetime.fromtimestamp(unix)
        date_string = date.strftime('%d.%m.%Y')

        conquer_channels = []

        for guild in self.bot.guilds:
            if self.bot.config.get('inactive', guild.id) is True:
                continue

            conquer = self.bot.config.get('conquer', guild.id, {})

            for channel_id, config in conquer.items():
                channel = guild.get_channel(int(channel_id))

                if channel is None:
                    logger.debug(f"skipped unkown channel: {channel_id}")
                    continue

                permissions = channel.permissions_for(guild.me)
                if not permissions.send_messages and not permissions.embed_links:
                    logger.debug(f"skipped forbidden channel {channel_id}")
                    continue

                server = self.bot.config.get_world(channel)
                world = self.bot.worlds.get(server)
                if world is None:
                    logger.debug(f"skipped {server}")
                    continue

                conquer_channels.append((channel, config, world))

        worlds = []
        for *_, world in conquer_channels:
            if world not in worlds:
                worlds.append(world)

        await self.update_conquer(worlds, unix)
        logger.debug(f"loaded {len(worlds)}")

        counter = collections.Counter()
        for channel, config, world in conquer_channels:
            resp = await self.conquer_feed(channel, config, world, date_string)
            if resp is True:
                counter[channel.guild.id] += 1

            await asyncio.sleep(0.5)

        self._conquer.clear()
        logger.debug(f"conquer feed complete ({len(counter)} guilds / {sum(counter.values())} channels)")

    async def conquer_feed(self, channel, config, world, date_string):
        data = await self.conquer_parse(world.server, config)
        if not data:
            return False

        conquer_pkg = []
        data.append("")
        title = f"Eroberungen am {date_string}"
        embed = discord.Embed(title=title)

        for line in data:

            if len(embed.fields) == 4 or not line:

                if not conquer_pkg or len(embed.fields) == 4:
                    await silencer(channel.send(embed=embed))
                    embed = discord.Embed()

                else:
                    data.append("")

            cache = "\n".join(conquer_pkg)
            length = len(embed.description) if embed.description else 0

            if len(conquer_pkg) == 3 and length + len(cache) < 2048:
                if length + len(cache) + len(line) < 2048:
                    cache = "\n".join(conquer_pkg + [line])
                    conquer_pkg.clear()

                else:
                    conquer_pkg = [line]

                if length:
                    embed.description += f"{cache}\n"
                else:
                    embed.description = f"{cache}\n\n"

            elif len(conquer_pkg) == 3 and len(embed.fields) < 4:
                if len(cache) + len(line) < 1024:
                    cache = "\n".join(conquer_pkg + [line])
                    conquer_pkg.clear()
                else:
                    conquer_pkg = [line]

                embed.add_field(name='\u200b', value=cache, inline=False)

            else:
                conquer_pkg.append(line)

        return True

    async def update_conquer(self, worlds, unix):
        old_unix = get_seconds(added_hours=0, starting_timestamp=True)

        for world in worlds:
            if world.type == "s":
                continue

            try:
                data = await self.fetch_conquer(world, unix)
            except Exception as error:
                logger.warning(f"{world.server} skipped: {error}")
                continue

            if not data[0]:
                continue
            if data[0].startswith('<'):
                continue

            cache = []
            for line in data:
                int_list = [int(num) for num in line.split(',')]
                cache.append(int_list)

            player_ids = []
            village_ids = []
            conquer_cache = []

            for entry in cache:
                vil_id, unix_time, new_owner, old_owner = entry

                # skips conquers after conquer timeframe which
                # would count for the next iteration
                if unix_time >= old_unix:
                    continue

                village_ids.append(vil_id)
                player_ids.extend([new_owner, old_owner])
                conquer = Conquer(world, entry)
                conquer_cache.append(conquer)

            # Make all the API Calls
            players = await self.bot.fetch_bulk(world.server, player_ids, dictionary=True)
            tribe_ids = list(set([obj.tribe_id for obj in players.values() if obj.tribe_id]))
            tribes = await self.bot.fetch_bulk(world.server, tribe_ids, 'tribe', dictionary=True)
            villages = await self.bot.fetch_bulk(world.server, village_ids, 'village', dictionary=True)

            conquer_cache.reverse()
            for index, conquer in enumerate(conquer_cache):
                if conquer.self_conquer:
                    continue

                if index and not conquer.grey_conquer:
                    prior_conquer = conquer_cache[index - 1]
                    if prior_conquer.village_id == conquer.village_id:

                        stamp = int(prior_conquer.time.timestamp())
                        window = list(range(stamp - 5, stamp + 6))

                        if int(conquer.time.timestamp()) in window:
                            continue

                conquer.village = villages.get(conquer.village_id)
                conquer.old_player = players.get(conquer.old_player_id)
                conquer.new_player = players.get(conquer.new_player_id)

                if conquer.old_player:
                    conquer.old_tribe = tribes.get(conquer.old_player.tribe_id)
                if conquer.new_player:
                    conquer.new_tribe = tribes.get(conquer.new_player.tribe_id)

            conquer_cache.reverse()
            self._conquer[world.server] = conquer_cache

    async def fetch_conquer(self, world, unix):
        base = "https://{}/interface.php?func=get_conquer&since={}"
        url = base.format(world.url, unix)

        async with self.bot.session.get(url) as resp:
            data = await resp.text('utf-8')
            return data.split('\n')

    async def conquer_parse(self, server, config):
        data = self._conquer.get(server)
        if not data:
            return

        bb_conquer = config.get('bb')
        tribe_filter = config.get('tribe', [])
        filter_ids = []

        if tribe_filter:
            members = await self.bot.fetch_tribe_member(server, tribe_filter)
            filter_ids.extend([player.id for player in members])

        player_filter = config.get('player', [])
        filter_ids.extend(player_filter)

        result = []
        for conquer in data:
            if filter_ids and not bool(set(filter_ids) & set(conquer.player_ids)):
                continue

            if not bb_conquer and conquer.grey_conquer:
                continue

            if not conquer.village:
                continue

            if conquer.new_player:
                tribe = f" **{conquer.new_tribe}**" if conquer.new_tribe else ""
                new = f"{conquer.new_player.mention}{tribe}"
            else:
                new = "Barbarendorf"

            if conquer.old_player:
                tribe = f" **{conquer.old_tribe}**" if conquer.old_tribe else ""
                old = f"{conquer.old_player.mention}{tribe}"
            else:
                old = "Barbarendorf"

            now = conquer.time.strftime('%H:%M')
            village_hyperlink = f"[{conquer.coords}]({conquer.village.ingame_url})"
            result.append(f"``{now}`` | {new} adelt {village_hyperlink} von {old}")

        return result


async def setup(bot):
    await bot.add_cog(ConquerLoop(bot))
