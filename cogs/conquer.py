from utils import Conquer, silencer, escape
from discord.ext import commands
import datetime
import discord
import asyncio


class ConquerLoop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._conquer = {}
        self.bot.loop.create_task(self.conquer_loop())

    @commands.command(name="manual")
    @commands.is_owner()
    async def manual_(self, ctx):
        await self.conquer_feed()

    # main loop
    async def conquer_loop(self):
        seconds = self.get_seconds()
        await asyncio.sleep(seconds)
        while not self.bot.is_closed():
            try:
                await self.bot.refresh_worlds()
                await self.conquer_feed()
                wait_pls = self.get_seconds()
                await asyncio.sleep(wait_pls)

            except Exception as error:
                print(f"Conguer Error: {error}")
                user = self.bot.get_user(self.bot.owner_id)
                await user.send("conquer task crashed")
                return

    async def conquer_feed(self):
        await self.update_conquer()
        for guild in self.bot.guilds:
            world = self.bot.config.get_guild_world(guild)
            if not world:
                continue

            channel_id = self.bot.config.get_item(guild.id, 'conquer')
            channel = guild.get_channel(channel_id)
            if not channel:
                continue

            tribes = self.bot.config.get_item(guild.id, 'filter')
            grey = self.bot.config.get_item(guild.id, 'bb', False)
            data = await self.conquer_parse(world, tribes, grey)
            if not data:
                continue

            date, conquer_feed = data
            if not conquer_feed:
                continue
            
            conquer_pkg = []
            embed = discord.Embed(title=date)
            conquer_feed.append("")
            for line in conquer_feed:

                if len(embed.fields) == 4 or not line:

                    if conquer_pkg:
                        conquer_feed.append("")
                    else:
                        await silencer(channel.send(embed=embed))
                        embed = discord.Embed()

                conquer_pkg.append(line)

                cache = "\n".join(conquer_pkg)
                length = len(embed.description)

                if len(conquer_pkg) == 4 and len(cache) + length < 2048:
                    if not length:
                        embed.description = f"{cache}\n\n"
                    else:
                        embed.description += f"{cache}\n"
                    conquer_pkg.clear()

                elif len(conquer_pkg) == 4:
                    embed.add_field(name='\u200b', value=cache, inline=False)
                    conquer_pkg.clear()

    async def update_conquer(self):
        for world in self.bot.worlds:

            if "s" in world:
                continue

            sec = self.get_seconds(True)
            data = await self.fetch_conquer(world, sec)

            self._conquer[world] = []
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
            old_unix = self.get_seconds(True, 1)
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
        base = "http://{}.die-staemme.de/interface.php?func=get_conquer&since={}"
        async with self.bot.session.get(base.format(world, cur)) as resp:
            data = await resp.text('utf-8')
            return data.split('\n')

    def get_seconds(self, reverse=False, only=0):
        now = datetime.datetime.now()
        hours = -1 if reverse else 1
        clean = now + datetime.timedelta(hours=hours + only)
        goal_time = clean.replace(minute=0, second=0, microsecond=0)
        start_time = now.replace(microsecond=0)
        if reverse:
            goal_time, start_time = start_time, goal_time
        goal = (goal_time - start_time).seconds
        return goal if not only else start_time.timestamp()

    async def conquer_parse(self, world, only_tribes, bb):
        data = self._conquer.get(world)
        if not data:
            return

        tribe_players = {}
        if only_tribes:
            members = await self.bot.fetch_tribe_member(world, only_tribes)
            tribe_players = {obj.id: obj for obj in members}

        date = None
        result = []
        for conquer in data:
            if only_tribes and not any(idc in tribe_players for idc in conquer.player_ids):
                continue
            if not bb and conquer.grey:
                continue
            if not conquer.village:
                continue

            old = conquer.old_player or "[Barbarendorf]"
            new = conquer.new_player or "[Barbarendorf]"
            village_hyperlink = f"[{conquer.coords}]({conquer.village.ingame_url})"

            if conquer.new_player:
                new = f"[{escape(new.name)}]({new.ingame_url})"
                if conquer.new_tribe:
                    new += f" **{escape(conquer.new_tribe.tag)}**"

            if conquer.old_player:
                old = f"[{escape(old.name)}]({old.ingame_url})"
                if conquer.old_tribe:
                    old += f" **{escape(conquer.old_tribe.tag)}**"

            date, now = conquer.time.strftime('%d-%m-%Y'), conquer.time.strftime('%H:%M')
            result.append(f"``{now}`` | {new} adelt {village_hyperlink} von {old}")

        return date, result


def setup(bot):
    bot.add_cog(ConquerLoop(bot))
