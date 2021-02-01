from utils import Conquer, silencer
from discord.ext import commands
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
    async def manual(self, ctx):
        await self.called_per_hour()
        await ctx.send("manual feed done")

    # main loop called from main
    async def called_per_hour(self):
        await self.update_conquer()
        unix = self.bot.get_seconds(added_hours=-1, timestamp=True)
        date = datetime.datetime.fromtimestamp(unix)
        date_string = date.strftime('%d.%m.%Y')

        counter = 0
        for guild in self.bot.guilds:
            inactive = self.bot.config.get('inactive', guild.id)
            if inactive is True:
                continue

            resp = await self.conquer_feed(guild, date_string)
            if resp is True:
                counter += 1

            await asyncio.sleep(0.5)

        logger.debug(f"conquer feed complete ({counter} guilds)")

    async def conquer_feed(self, guild, date_string):
        conquer = self.bot.config.get('conquer', guild.id)
        if not conquer:
            return

        response = False
        for channel_id, conquer_config in conquer.items():
            channel = guild.get_channel(int(channel_id))
            if channel is None:
                continue

            world = self.bot.config.get_world(channel)
            if world is None:
                continue

            data = await self.conquer_parse(world, conquer_config)
            if not data:
                continue

            response = True
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
                length = len(embed.description)

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

        return response

    async def update_conquer(self):
        old_unix = self.bot.get_seconds(added_hours=0, timestamp=True)
        sec = self.bot.get_seconds(added_hours=-1)

        for world, world_obj in self.bot.worlds.items():

            if world_obj.type == "s":
                continue

            try:
                data = await self.fetch_conquer(world_obj, sec)
            except Exception as error:
                logger.warning(f"{world} skipped: {error}")
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
            players = await self.bot.fetch_bulk(world, player_ids, dictionary=True)
            tribe_ids = [obj.tribe_id for obj in players.values() if obj.tribe_id]
            tribes = await self.bot.fetch_bulk(world, tribe_ids, 'tribe', dictionary=True)
            villages = await self.bot.fetch_bulk(world, village_ids, 'village', dictionary=True)

            conquer_cache.reverse()
            for index, conquer in enumerate(conquer_cache):
                if conquer.self_conquer:
                    continue

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
            self._conquer[world] = conquer_cache

    async def fetch_conquer(self, world, sec=3600):
        now = datetime.datetime.now()
        base = "https://{}/interface.php?func=get_conquer&since={}"
        url = base.format(world.url, now.timestamp() - sec)

        async with self.bot.session.get(url) as resp:
            data = await resp.text('utf-8')
            return data.split('\n')

    async def conquer_parse(self, world, config):
        data = self._conquer.get(world)
        if not data:
            return

        bb_conquer = config.get('bb')
        filter_ids = {}

        tribe_filter = config.get('tribe')
        if tribe_filter:
            members = await self.bot.fetch_tribe_member(world, tribe_filter)
            filter_ids.update({obj.id: obj for obj in members})

        player_filter = config.get('player')
        if player_filter:
            players = await self.bot.fetch_bulk(world, player_filter)
            filter_ids.update({obj.id: obj for obj in players})

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
                new = "[Barbarendorf]"

            if conquer.old_player:
                tribe = f" **{conquer.old_tribe}**" if conquer.old_tribe else ""
                old = f"{conquer.old_player.mention}{tribe}"
            else:
                old = "[Barbarendorf]"

            now = conquer.time.strftime('%H:%M')
            village_hyperlink = f"[{conquer.coords}]({conquer.village.ingame_url})"
            result.append(f"``{now}`` | {new} adelt {village_hyperlink} von {old}")

        return result


def setup(bot):
    bot.add_cog(ConquerLoop(bot))
