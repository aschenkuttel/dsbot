from discord.ext import commands, tasks
from utils import Conquer, silencer
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

        counter = 0
        for guild in self.bot.guilds:
            inactive = self.bot.config.get('inactive', guild.id)
            if inactive is True:
                continue

            resp = await self.conquer_feed(guild)
            if resp is True:
                counter += 1

        logger.debug(f"conquer feed complete ({counter} guilds)")

    async def conquer_feed(self, guild):
        conquer = self.bot.config.get('conquer', guild.id)
        if not conquer:
            return

        response = False
        for channel_id, conquer_config in conquer.items():
            channel = guild.get_channel(int(channel_id))
            if not channel:
                continue

            world = self.bot.config.get_world(channel)
            if not world:
                continue

            data = await self.conquer_parse(world, conquer_config)
            if not data:
                continue

            date, conquer_feed = data
            if not conquer_feed:
                continue

            response = True
            conquer_pkg = []
            embed = discord.Embed(title=date)
            conquer_feed.append("")

            for line in conquer_feed:

                if len(embed.fields) == 4 or not line:

                    if not conquer_pkg or len(embed.fields) == 4:
                        await silencer(channel.send(embed=embed))
                        embed = discord.Embed()
                        await asyncio.sleep(1)

                    else:
                        conquer_feed.append("")

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
        for world, world_obj in self.bot.worlds.items():

            if "s" in world:
                continue

            self._conquer[world] = []

            try:
                sec = self.bot.get_seconds(added_hours=-1)
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
            old_unix = self.bot.get_seconds(added_hours=0, timestamp=True)

            for entry in cache:
                vil_id, unix_time, new_owner, old_owner = entry

                # skips conquers after conquer timeframe which
                # would count for the next iteration
                if unix_time > old_unix:
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
                if conquer.self_conquer():
                    continue

                last = conquer_cache[index - 1]
                if last.id == conquer.id and not last.self_conquer():

                    stamp = int(last.time.timestamp())
                    window = list(range(stamp - 5, stamp + 6))

                    if int(conquer.time.timestamp()) in window:
                        continue

                conquer.village = villages.get(conquer.id)
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

        filter_ids = {}
        bbs = config.get('bb')

        tribe_filter = config.get('tribe')
        if tribe_filter:
            members = await self.bot.fetch_tribe_member(world, tribe_filter)
            filter_ids.update({obj.id: obj for obj in members})

        player_filter = config.get('player')
        if player_filter:
            players = await self.bot.fetch_bulk(world, player_filter)
            filter_ids.update({obj.id: obj for obj in players})

        date = None
        result = []
        for conquer in data:

            if filter_ids and not bool(set(filter_ids) & set(conquer.player_ids)):
                continue

            if not bbs and conquer.grey_conquer():
                continue

            if not conquer.village:
                continue

            old = conquer.old_player or "[Barbarendorf]"
            new = conquer.new_player or "[Barbarendorf]"
            village_hyperlink = f"[{conquer.coords}]({conquer.village.ingame_url})"

            if conquer.new_player:
                if conquer.new_tribe:
                    tribe = f"**{conquer.new_tribe}**"
                else:
                    tribe = "**N/A**"

                new = f"{new.mention} {tribe}"

            if conquer.old_player:
                if conquer.old_tribe:
                    tribe = f" **{conquer.old_tribe}**"
                else:
                    tribe = "**N/A**"

                old = f"{old.mention} {tribe}"

            date, now = conquer.time.strftime('%d-%m-%Y'), conquer.time.strftime('%H:%M')
            result.append(f"``{now}`` | {new} adelt {village_hyperlink} von {old}")

        return date, result


def setup(bot):
    bot.add_cog(ConquerLoop(bot))
