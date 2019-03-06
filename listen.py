from load import load
from utils import *
import discord
import random
import re

listener = commands.Cog.listener


class Listen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @listener()
    async def on_message(self, message):

        if not message.guild or message.author.bot:
            return

        if not load.get_world(message.channel):
            return

        # --- Report Converter --- #
        if message.content.__contains__("public_report"):
            file = await load.report_func(message.content)
            if not file:
                return await load.silencer(message.add_reaction('❌'))
            await message.channel.send(file=discord.File(file, "report.png"))
            return await load.silencer(message.delete())

        # ----- Coord Converter -----#
        result = re.findall(r'\d\d\d\|\d\d\d', message.content)
        if result:
            pre = load.pre_fix(message.guild.id)
            if message.content.lower().startswith(pre.lower()):
                return
            found, lost = await load.coordverter(result, message.guild.id)
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
        print(f"MAIN LISTENER: {error}")
        print(type(error))
        if isinstance(error, commands.CommandNotFound):
            if ctx.guild:
                pre = load.pre_fix(ctx.guild.id)
            else:
                pre = "!"
            if len(ctx.invoked_with) == ctx.invoked_with.count(pre):
                return
            else:
                data = random.choice(load.msg["noCommand"])
                return await ctx.send(data.format(f"{pre}{ctx.invoked_with}"))

        if isinstance(error, commands.NoPrivateMessage):
            msg = "Der Command ist leider nur auf einem Server verfügbar."
            return await ctx.send(embed=error_embed(msg))

        if isinstance(error, DontPingMe):
            msg = "Schreibe anstatt eines Pings den Usernamen oder Nickname."
            return await ctx.send(embed=error_embed(msg))

        if isinstance(error, PrivateOnly):
            msg = "Der Command ist leider nur private Message verfügbar!"
            return await ctx.send(embed=error_embed(msg))

        if isinstance(error, WorldMissing):
            pre = load.pre_fix(ctx.guild.id)
            msg = "Der Server hat noch keine zugeordnete Welt.\n" \
                f"Dies kann nur der Admin mit `{pre}set world`"
            return await ctx.send(embed=error_embed(msg))

        if isinstance(error, GameChannelMissing):
            pre = load.pre_fix(ctx.guild.id)
            msg = "Der Server hat noch keinen Game-Channel.\n" \
                f"Dies kann nur der Admin mit `{pre}set game`"
            return await ctx.send(embed=error_embed(msg))

        if isinstance(error, WrongChannel):
            channel = load.get_config(ctx.guild.id, "game")
            return await ctx.send(f"<#{channel}>")

        if isinstance(error, commands.NotOwner):
            msg = "Diesen Command kann nur der Bot-Owner ausführen!"
            return await ctx.send(embed=error_embed(msg))

        if isinstance(error, commands.MissingPermissions):
            msg = "Diesen Command kann nur ein Server-Admin ausführen!"
            return await ctx.send(embed=error_embed(msg))

        if isinstance(error, commands.CommandOnCooldown):
            msg = "Command Cooldown: Versuche es in {} Sekunden erneut."
            await ctx.send(embed=error_embed(msg.format(int(error.retry_after))))

        if isinstance(error, DSUserNotFound):
            name = f"Casual {error.world}" if error.world < 50 else f"der `{error.world}`"
            msg = f"`{error.name}` konnte auf {name} nicht gefunden werden."
            return await ctx.send(embed=error_embed(msg))

        if isinstance(error, GuildUserNotFound):
            msg = f"`{error.name}` konnte nicht gefunden werden."
            return await ctx.send(embed=error_embed(msg))

        if isinstance(error, commands.BotMissingPermissions):
            msg = "Dem Bot fehlen benötigte Rechte auf diesem Server."
            return await ctx.send(embed=error_embed(msg))


def setup(bot):
    bot.add_cog(Listen(bot))
