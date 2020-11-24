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
import sys
import io
import re

logger = logging.getLogger('dsbot')


class UTParser:
    def __init__(self, bot, server, package):
        self.bot = bot
        self.server = server
        self.package = package
        self.village_cache = {}
        self.world = bot.worlds[server]
        self.players = {}
        self.target_player = None
        self.target = None

    async def parse(self):
        resp = await self.fetch_objects()
        if resp is False or not self.village_cache:
            return False

        try:
            embed = await self.embed_builder()
            return embed
        except Exception as error:
            logger.error(f"request error: {error}")

    async def fetch_objects(self):
        raw = " ".join(self.package)
        coordinates = re.findall(r'\d\d\d\|\d\d\d', raw)
        villages = await self.bot.fetch_bulk(self.server, set(coordinates),
                                             table="village", name=True)
        self.village_cache = {vil.coords: vil for vil in villages}

        if len(villages) != len(set(coordinates)):
            return False

        for coord, vil in self.village_cache.items():
            if vil.player_id in self.players:
                self.players[vil.player_id].append(vil)
            else:
                self.players[vil.player_id] = [vil]

        player_ids = list(self.players.keys())
        player_objs = await self.bot.fetch_bulk(self.server, player_ids)

        for player in player_objs:
            vil_list = self.players.pop(player.id)
            for vil in vil_list:
                self.players[vil.coords] = player

        self.target = self.village_cache[coordinates[0]]
        self.target_player = self.players[self.target.coords]

    async def embed_builder(self):
        embed = discord.Embed(colour=discord.Color.blue())
        embed.title = f"{self.target_player.name} wird angegriffen!"
        cache = [f"**Dorf:** {self.target.mention}"]
        unit_icon_dict = self.bot.msg['unitIcon']

        field_cache = []
        for line in self.package[1:]:
            nums = re.findall(r'\d+', line)
            if "Wallstufe" in line or "Zustimmung" in line:
                addition = line.replace("[b]", "**")
                addition = addition.replace("[/b]", "**")
                addition = addition.replace(nums[0], f"`{nums[0]}`")
                cache.append(addition)
            elif "Verteidiger" in line:
                knight = self.world.config['game']['knight'] == "1"
                bow = self.world.config['game']['archer'] == "1"

                units = list(unit_icon_dict.values())
                for unit, icon in unit_icon_dict.items():
                    if not knight and unit == "knight":
                        units.remove(icon)
                    elif not bow and unit == "archer":
                        units.remove(icon)

                if len(nums) != len(units):
                    units.remove("<:tw_militia:737220482994274366>")

                stationed = []
                for index, num in enumerate(nums):
                    if int(num):
                        stationed.append(f"{units[index]} {num}")

                cache.extend(["**Verteidiger**:", " ".join(stationed), ""])

            elif line.startswith("[command]"):
                attacker_coord = re.findall(r'\[coord](.*)\[/coord]', line)
                village = self.village_cache[attacker_coord[0]]
                attacker = self.players[attacker_coord[0]]

                possible_info = re.findall(r'\[command](\S*)\[/command]', line)
                renamed = re.findall(r'\[/command]([^].]*)\[coord]', line)
                lz_icon = "<:tw_who:737244837149016064>"

                name = renamed[0].strip()
                if name:
                    renames = self.bot.msg['unitRename']
                    lz_unit = renames.get(name)
                    icon = unit_icon_dict.get(lz_unit)
                    if icon:
                        lz_icon = icon

                raw_time = re.findall(r'-->.*?:(.*)\[player]', line)
                time = raw_time[0].strip()

                inc_icon = self.bot.msg['attackIcon'].get(possible_info[0])
                attack = f"{inc_icon} {lz_icon} `{time}` [{village.mention}] **{attacker.name}**"

                if len("\n".join(cache + [attack])) > 2048:
                    field_cache.append(attack)
                    if len(field_cache) == 4 or line == self.package[-1]:
                        embed.add_field(name='\u200b', value="\n".join(field_cache), inline=False)
                        field_cache.clear()

                else:
                    cache.append(attack)

        embed.description = "\n".join(cache)
        footer = "Ausgegraute Rammen = unbekannte Laufzeiten"
        embed.set_footer(text=footer)

        return embed


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
                logger.debug("report converted")
                return

        # ut request conversion
        ut_requests = re.findall(r'(\[b].*)|(\[command].*)', content)
        if ut_requests and self.bot.config.get_switch('request', guild_id):
            request_packages = [[]]

            for title, command in ut_requests:
                current = request_packages[-1]
                header = title.startswith("[b]Dorf:[/b]")
                if header and len(current) == 0:
                    current.append(title)
                elif header and len(current) > 0:
                    request_packages.append([title])
                elif not header and current:
                    current.append(title or command)

            for pkg in request_packages:
                parser = UTParser(self.bot, world, pkg)
                embed = await parser.parse()

                if embed is False:
                    await utils.silencer(message.add_reaction('❌'))
                    return

                try:
                    await message.channel.send(embed=embed)
                    await message.delete()
                except (discord.Forbidden, discord.HTTPException):
                    continue

            return

        # coord conversion
        coordinates = re.findall(r'\d\d\d\|\d\d\d', content)
        if coordinates and self.bot.config.get_switch('coord', guild_id):
            coords = set(coordinates)
            villages = await self.bot.fetch_bulk(world, coords, 2, name=True)
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
                coordinates.remove(f"{vil.x}|{vil.y}")

            found = '\n'.join(good)
            lost = ', '.join(coordinates)
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
                data = random.choice(self.bot.msg["noCommand"])
                await ctx.send(data.format(f"{ctx.prefix}{cmd}"))
                return

        elif isinstance(error, commands.MissingRequiredArgument):
            msg = "Dem Command fehlt ein benötigtes Argument"
            tip = ctx

        elif isinstance(error, utils.MissingRequiredKey):
            msg = f"`{ctx.prefix}{cmd.lower()} <{'|'.join(error.keys)}>`"
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

        elif isinstance(error, utils.InvalidCoordinate):
            msg = "Du musst eine gültige Koordinate angeben"

        elif isinstance(error, utils.WrongChannel):
            if error.type == "game":
                channel = self.bot.config.get('game', ctx.guild.id)
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
            base = "Dem Bot fehlen folgende Rechte auf diesem Server:\n`{}`"
            msg = base.format(', '.join(error.missing_perms))

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
