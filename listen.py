from discord.ext import commands
from load import load
import discord
import random
import utils
import re


listener = commands.Cog.listener
error_embed = utils.error_embed


class Listen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @listener()
    async def on_message(self, message):

        if not message.guild or message.author.bot:
            return

        world = load.get_world(message.channel)
        if not world:
            return

        # --- Report Converter --- #
        if message.content.__contains__("public_report"):

            file = await load.report_func(message.content)
            if file is None:
                return await load.silencer(message.add_reaction('❌'))
            await message.channel.send(file=discord.File(file, "report.png"))
            await load.silencer(message.delete())
            return

        # ----- Coord Converter -----#
        result = re.findall(r'\d\d\d\|\d\d\d', message.content)
        if result:
            pre = load.pre_fix(message.guild.id)
            if message.content.lower().startswith(pre.lower()):
                return
            found, lost = await load.coordverter(result, world)
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
        print(f"{ctx.invoked_with}: {error}")

        pre = "!"
        if ctx.guild:
            pre = load.pre_fix(ctx.guild.id)

        if isinstance(error, commands.CommandNotFound):

            if len(ctx.invoked_with) == ctx.invoked_with.count(pre):
                return
            else:
                data = random.choice(load.msg["noCommand"])
                await ctx.send(data.format(f"{pre}{ctx.invoked_with}"))

        elif isinstance(error, commands.NoPrivateMessage):
            msg = "Der Command ist leider nur auf einem Server verfügbar."
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, utils.DontPingMe):
            msg = "Schreibe anstatt eines Pings den Usernamen oder Nickname."
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, utils.PrivateOnly):
            msg = "Der Command ist leider nur private Message verfügbar!"
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, utils.WorldMissing):
            msg = "Der Server hat noch keine zugeordnete Welt.\n" \
                f"Dies kann nur der Admin mit `{pre}set world`"
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, utils.GameChannelMissing):
            msg = "Der Server hat keinen Game-Channel.\n" \
                f"Nutze `{pre}set game` um einen festzulegen."
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, utils.ConquerChannelMissing):
            msg = "Der Server hat keinen Conquer-Channel.\n" \
                f"Nutze `{pre}set conquer` um einen festzulegen."
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, utils.WrongChannel):
            channel = load.get_config(ctx.guild.id, "game")
            await ctx.send(f"<#{channel}>")

        elif isinstance(error, commands.NotOwner):
            msg = "Diesen Command kann nur der Bot-Owner ausführen!"
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, commands.MissingPermissions):
            msg = "Diesen Command kann nur ein Server-Admin ausführen!"
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, commands.CommandOnCooldown):
            msg = "Command Cooldown: Versuche es in {} Sekunden erneut."
            await ctx.send(embed=error_embed(msg.format(int(error.retry_after))))

        elif isinstance(error, utils.DSUserNotFound):
            name = f"Casual {error.world}" if error.world < 50 else f"der `{error.world}`"
            msg = f"`{error.name}` konnte auf {name} nicht gefunden werden."
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, utils.GuildUserNotFound):
            msg = f"`{error.name}` konnte nicht gefunden werden."
            await ctx.send(embed=error_embed(msg))

        elif isinstance(error, commands.BotMissingPermissions):
            msg = "Dem Bot fehlen benötigte Rechte auf diesem Server."
            await ctx.send(embed=error_embed(msg))

        else:
            cog = self.bot.get_cog(ctx.command.cog_name)
            data = getattr(cog, 'data', None)
            if data:
                data.pop(ctx.guild.id)


def setup(bot):
    bot.add_cog(Listen(bot))
