from load import load, DSObject
from utils import *


class Set(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def __local_check(self, ctx):
        if ctx.guild is None:
            raise commands.NoPrivateMessage
        return ctx.author.guild_permissions.administrator

    @commands.group(invoke_without_command=True, case_insensitive=True)
    async def set(self, ctx):
        pre = load.pre_fix(ctx.guild.id)
        msg = f"`{pre}set <world> / <game> / <conquer> /" \
              f" <tribe> / <prefix> / <channelworld>`"
        await ctx.send(embed=error_embed(msg))

    @set.command(name="world")
    async def world_(self, ctx, world: int):

        # --- Valid World Check --- #
        if not await load.is_valid(world):
            msg = "Die Welt wurde bereits geschlossen / existiert noch nicht!"
            return await ctx.send(embed=error_embed(msg))

        old = load.get_world(ctx.channel)

        # --- Check if World already linked --- #

        if world == old:
            msg = f"Der Server ist bereits zu Welt `{world}` gelinked!"
            return await ctx.send(embed=error_embed(msg))

        load.change_config(ctx.guild.id, "world", world)
        name = "Welt" if world > 50 else "Casual"
        msg = f"Der Server wurde mit {name} `{world}` gelinked!"
        await ctx.send(embed=complete_embed(msg))

    @set.command(name="game")
    async def game_(self, ctx):
        cur = load.get_config(ctx.guild.id, "game")
        if cur == ctx.channel.id:
            return await ctx.send("Der aktuelle Channel ist bereits eingespeichert.")
        load.change_config(ctx.guild.id, "game", ctx.channel.id)
        msg = f"<#{ctx.channel.id}> ist nun der aktive Game-Channel."
        await ctx.send(embed=complete_embed(msg))

    @set.command(name="conquer")
    async def conquer_(self, ctx):
        cur = load.get_config(ctx.guild.id, "conquer")
        if cur and cur == ctx.channel.id:
            return await ctx.send("Der aktuelle Channel ist bereits eingespeichert.")
        load.change_config(ctx.guild.id, "conquer", ctx.channel.id)
        msg = f"<#{ctx.channel.id}> ist nun der aktive Eroberungschannel."
        await ctx.send(embed=complete_embed(msg))

    @set.command(name="prefix")
    async def prefix_(self, ctx, pre):
        cur = load.pre_fix(ctx.guild.id)
        if cur == pre:
            msg = f"`{cur}` ist bereits der aktuelle Prefix dieses Servers."
            return await ctx.send(embed=error_embed(msg))
        load.change_config(ctx.guild.id, "prefix", pre)
        msg = f"Der Prefix `{pre}` ist nun aktiv."
        await ctx.send(embed=complete_embed(msg))

    @set.command(name="tribe")
    async def tribe_(self, ctx, *, tribe: DSObject):
        cur = load.get_config(ctx.guild.id, "conquer")
        if cur is None:
            msg = "Der Server hat noch keinen Conquer Channel."
            return await ctx.send(embed=error_embed(msg))
        load.change_config(ctx.guild.id, "tribe", tribe.id)
        msg = f"`{tribe.name}` ist nun der registrierte Stamm."
        await ctx.send(embed=complete_embed(msg))

    @set.command(name="channelworld")
    async def channel_world(self, ctx, world: int):

        if not await load.is_valid(world):
            msg = "Die Welt wurde bereits geschlossen / existiert noch nicht!"
            return await ctx.send(embed=error_embed(msg))

        config = load.get_config(ctx.guild.id, "channel")
        if config is None:
            cache = {str(ctx.channel.id): world}
            load.change_config(ctx.guild.id, "channel", cache)

        else:
            old_world = config.get(str(ctx.channel.id))
            if old_world == world:
                msg = f"Der Server ist bereits zu Welt `{world}` gelinked!"
                return await ctx.send(embed=error_embed(msg))
            config[str(ctx.channel.id)] = world

        load.save_config()
        name = "Welt" if world > 50 else "Casual"
        msg = f"Der Channel wurde mit {name} `{world}` gelinked!"
        await ctx.send(embed=complete_embed(msg))

    @commands.group(invoke_without_command=True)
    async def remove(self, ctx, entry):
        entries = ("game", "conquer", "prefix", "tribe")
        if entry.lower() not in entries:
            pre = load.pre_fix(ctx.guild.id)
            msg = f"**Fehlerhafte Eingabe:** {pre}remove <{'/'.join(entries)}>"
            return await ctx.send(embed=error_embed(msg))
        res = {"game": "Game Channel", "conquer": "Eroberungschannel",
               "prefix": "Prefix", "tribe": "Conquer Stamm"}
        done = load.remove_config(ctx.guild.id, entry.lower())
        if not done:
            msg = f"Der Server hat keinen zugewiesenen `{res[entry]}`."
            return await ctx.send(embed=error_embed(msg))
        msg = f"`{res[entry]}` erfolgreich gelöscht."
        await ctx.send(embed=complete_embed(msg))

    @remove.command(name="channelworld")
    async def remove_channelworld(self, ctx):
        config = load.get_config(ctx.guild.id, "channel")
        if config:
            world = config.get(str(ctx.channel.id))
            state = True if world else False

        else:
            state = False

        if not state:
            msg = "Dieser Channel hat keine eigene Welt"
            return await ctx.send(embed=error_embed(msg))

        del config[str(ctx.channel.id)]
        msg = "Die Channel-Welt wurde gelöscht"
        await ctx.send(embed=complete_embed(msg))

    @commands.command(name="world")
    async def world_get(self, ctx):
        world = load.get_world(ctx.channel)
        cas = "Welt " if world > 50 else "Casual "
        msg = f"{cas}{world}"
        await ctx.send(embed=complete_embed(msg))


def setup(bot):
    bot.add_cog(Set(bot))
