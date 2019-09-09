from discord.ext import commands
from load import load
import traceback
import discord
import aiohttp
import random
import utils
import sys
import re

listener = commands.Cog.listener
error_embed = utils.error_embed


class Listen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cap = 10

    @listener()
    async def on_message(self, message):

        if not message.guild or message.author.bot:
            return

        world = load.get_world(message.channel)
        if not world:
            return

        # --- Report Converter --- #
        if message.content.__contains__("public_report"):

            file = await load.fetch_report(self.bot.loop, message.content)
            if file is None:
                return await load.silencer(message.add_reaction('❌'))
            await message.channel.send(file=discord.File(file, "report.png"))
            await utils.silencer(message.delete())
            return

        # ----- Coord Converter -----#
        result = re.findall(r'\d\d\d\|\d\d\d', message.content)
        if result:
            pre = load.get_prefix(message.guild.id)
            if message.content.lower().startswith(pre.lower()):
                return

            cache, bad, good = [], [], []
            for coord in result[:self.cap]:
                if coord in cache:
                    continue
                res = await load.fetch_village(world, coord, True)
                if not res:
                    bad.append(coord)
                    cache.append(coord)
                else:
                    if res.player_id:
                        player = await load.fetch_player(world, res.player_id)
                        owner = f"[{player.name}]"
                    else:
                        owner = "[Barbarendorf]"
                    good.append(f"[{coord}]({res.ingame_url}) {owner}")
                    cache.append(coord)

            found = '\n'.join(good) or ""
            lost = ','.join(bad) or ""
            if found:
                found = f"**Gefundene Koordinaten:**\n{found}"
            if lost:
                lost = f"**Nicht gefunden:**\n{lost}"
            em = discord.Embed(description=f"{found}\n{lost}")
            await message.channel.send(embed=em)

    @listener()
    async def on_message_edit(self, before, after):
        if self.bot.user == before.author:
            return
        ctx = await self.bot.get_context(after)
        if ctx.valid:
            await self.bot.invoke(ctx)

    @listener()
    async def on_command_completion(self, ctx):
        await load.save_usage_cmd(ctx.invoked_with)

    @listener()
    async def on_command_error(self, ctx, error):

        error = getattr(error, 'original', error)

        if isinstance(error, commands.CommandNotFound):
            if len(ctx.invoked_with) == ctx.invoked_with.count(ctx.prefix):
                return
            else:
                data = random.choice(load.msg["noCommand"])
                await ctx.send(data.format(f"{ctx.prefix}{ctx.invoked_with}"))

        elif isinstance(error, commands.NoPrivateMessage):
            msg = "Der Command ist leider nur auf einem Server verfügbar"
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, utils.DontPingMe):
            msg = "Schreibe anstatt eines Pings den Usernamen oder Nickname"
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, utils.PrivateOnly):
            msg = "Der Command ist leider nur per private Message verfügbar"
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, utils.WorldMissing):
            msg = "Der Server hat noch keine zugeordnete Welt\n" \
                  f"Dies kann nur der Admin mit `{ctx.prefix}set world`"
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, utils.GameChannelMissing):
            msg = "Der Server hat keinen Game-Channel\n" \
                  f"Nutze `{ctx.prefix}set game` um einen festzulegen"
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, utils.WrongChannel):
            channel = load.get_item(ctx.guild.id, "game")
            await ctx.send(f"<#{channel}>")

        elif isinstance(error, commands.NotOwner):
            msg = "Diesen Command kann nur der Bot-Owner ausführen"
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, commands.MissingPermissions):
            msg = "Diesen Command kann nur ein Server-Admin ausführen"
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, commands.CommandOnCooldown):
            msg = "Command Cooldown: Versuche es in {} Sekunden erneut"
            await ctx.send(embed=error_embed(msg.format(int(error.retry_after))))

        elif isinstance(error, utils.DSUserNotFound):
            name = f"Casual {error.world}" if error.world < 50 else f"der `{error.world}`"
            msg = f"`{error.name}` konnte auf {name} nicht gefunden werden"
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, utils.GuildUserNotFound):
            msg = f"`{error.name}` konnte nicht gefunden werden"
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, commands.BotMissingPermissions):
            msg = f"Dem Bot fehlen folgende Rechte auf diesem Server:\n" \
                  f"`{', '.join(error.missing_perms)}`"
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, discord.Forbidden):
            msg = f"Dem Bot fehlen benötigte Rechte:\n`{error.text}`"
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, aiohttp.InvalidURL):
            return

        else:
            cog = self.bot.get_cog(ctx.command.cog_name)
            data = getattr(cog, 'data', None)
            if data:
                try:
                    data.pop(ctx.guild.id)
                except KeyError:
                    pass

            print(f"Command Message: {ctx.message.content}")
            print("Command Error:")
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


def setup(bot):
    bot.add_cog(Listen(bot))
