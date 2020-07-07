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
        self.start = True
        self._conquer = {}
        self.guild_timeout.start()

    @tasks.loop(hours=72)
    async def guild_timeout(self):
        if self.start is True:
            self.start = False
            return

        counter = 0
        for guild in self.bot.guilds:
            if guild.id in self.bot.last_message:
                continue
            else:
                self.bot.config.remove_item(guild.id, 'conquer', bulk=True)
                counter += 1

        self.bot.config.save()
        self.bot.last_message.clear()
        logger.debug(f"{counter} inactive guilds")

    # main loop called from main
    async def called_by_hour(self):
        await self.update_conquer()

        counter = 0
        for guild in self.bot.guilds:
            resp = await self.conquer_feed(guild)
            if resp is True:
                counter += 1

        logger.debug(f"conquer feed complete ({counter} guilds)")

    async def conquer_feed(self, guild):
        conquer = self.bot.config.get_item(guild.id, 'conquer')
        if not conquer:
            return

        response = False
        for channel_id, conquer_data in conquer.items():
            channel = guild.get_channel(int(channel_id))
            if not channel:
                continue

            world = self.bot.config.get_world(channel)
            if not world:
                continue

            data = await self.conquer_parse(world, conquer_data)
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
                sec = self.bot.get_seconds(True)
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
            old_unix = self.bot.get_seconds(True, 1)
            for entry in cache:
                vil_id, unix_time, new_owner, old_owner = entry

                if unix_time > old_unix:
                    continue

                village_ids.append(vil_id)
                player_ids.extend([new_owner, old_owner])
                conquer = Conquer(world, entry)
                conquer_cache.append(conquer)

            # Make all the API Calls
            players = await self.bot.fetch_bulk(world, player_ids, dic=True)
            tribe_ids = [obj.tribe_id for obj in players.values() if obj.tribe_id]
            tribes = await self.bot.fetch_bulk(world, tribe_ids, 'tribe', dic=True)
            villages = await self.bot.fetch_bulk(world, village_ids, 'village', dic=True)

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
                conquer.old_player = players.get(conquer.old_id)
                conquer.new_player = players.get(conquer.new_id)
                if conquer.old_player:
                    conquer.old_tribe = tribes.get(conquer.old_player.tribe_id)
                if conquer.new_player:
                    conquer.new_tribe = tribes.get(conquer.new_player.tribe_id)

            conquer_cache.reverse()
            self._conquer[world] = conquer_cache

    async def fetch_conquer(self, world, sec=3600):
        now = datetime.datetime.now()
        cur = now.timestamp() - sec
        base = "https://{}/interface.php?func=get_conquer&since={}"
        async with self.bot.session.get(base.format(world.url, cur)) as resp:
            data = await resp.text('utf-8')
            return data.split('\n')

    async def conquer_parse(self, world, config):
        data = self._conquer.get(world)
        if not data:
            return

        only_tribes = config['filter']

        tribe_players = {}
        if only_tribes:
            members = await self.bot.fetch_tribe_member(world, only_tribes)
            tribe_players = {obj.id: obj for obj in members}

        date = None
        result = []
        for conquer in data:
            if only_tribes and not any(idc in tribe_players for idc in conquer.player_ids):
                continue

            if not config['bb'] and conquer.grey:
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
