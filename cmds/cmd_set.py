from utils import error_embed, complete_embed, DSObject, ConquerChannelMissing
from discord.ext import commands
from load import load
import discord


class Set(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        if ctx.guild is None:
            raise commands.NoPrivateMessage
        if ctx.author.guild_permissions.administrator:
            return True
        raise commands.MissingPermissions(['administrator'])

    @commands.group(invoke_without_command=True, case_insensitive=True)
    async def set(self, ctx):
        pre = load.pre_fix(ctx.guild.id)
        msg = f"`{pre}set [world|game|conquer|channel|prefix]`"
        await ctx.send(embed=error_embed(msg))

    @set.command(name="world")
    async def set_world(self, ctx, world: int):

        # --- Valid World Check --- #
        if not load.is_valid(world):
            msg = "Die Welt wurde bereits geschlossen / existiert noch nicht!"
            return await ctx.send(embed=error_embed(msg))

        article = "Welt" if world > 50 else "Casual"

        # --- Check if World already linked --- #
        if world == ctx.world:
            msg = f"Der Server ist bereits mit {article} `{world}` verbunden!"
            return await ctx.send(embed=error_embed(msg))

        load.change_config(ctx.guild.id, "world", world)
        msg = f"Der Server ist nun mit {article} `{world}` verbunden!"
        await ctx.send(embed=complete_embed(msg))

    @set.command(name="game")
    async def set_game(self, ctx):
        cur = load.get_config(ctx.guild.id, "game")
        if cur == ctx.channel.id:
            return await ctx.send("Der aktuelle Channel ist bereits eingespeichert.")
        load.change_config(ctx.guild.id, "game", ctx.channel.id)
        msg = f"<#{ctx.channel.id}> ist nun der aktive Game-Channel."
        await ctx.send(embed=complete_embed(msg))

    @set.command(name="conquer")
    async def set_conquer(self, ctx):
        cur = load.get_config(ctx.guild.id, "conquer")
        if cur and cur == ctx.channel.id:
            return await ctx.send("Der aktuelle Channel ist bereits eingespeichert.")
        load.change_config(ctx.guild.id, "conquer", ctx.channel.id)
        msg = f"<#{ctx.channel.id}> ist nun der aktive Eroberungschannel."
        await ctx.send(embed=complete_embed(msg))

    @set.command(name="prefix")
    async def set_prefix(self, ctx, pre):
        cur = load.pre_fix(ctx.guild.id)
        if cur == pre:
            msg = f"`{cur}` ist bereits der aktuelle Prefix dieses Servers."
            return await ctx.send(embed=error_embed(msg))
        load.change_config(ctx.guild.id, "prefix", pre)
        msg = f"Der Prefix `{pre}` ist nun aktiv."
        await ctx.send(embed=complete_embed(msg))

    @set.command(name="channel")
    async def set_channel(self, ctx, world: int):

        if not load.is_valid(world):
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
        entries = ("game", "conquer", "prefix")
        if entry.lower() not in entries:
            pre = load.pre_fix(ctx.guild.id)
            msg = f"**Fehlerhafte Eingabe:** {pre}remove <{'/'.join(entries)}>"
            return await ctx.send(embed=error_embed(msg))
        res = {"game": "Game Channel", "conquer": "Eroberungschannel",
               "prefix": "Prefix"}
        done = load.remove_config(ctx.guild.id, entry.lower())
        if not done:
            msg = f"Der Server hat keinen zugewiesenen `{res[entry]}`"
            return await ctx.send(embed=error_embed(msg))
        msg = f"`{res[entry]}` erfolgreich gelöscht"
        await ctx.send(embed=complete_embed(msg))

    @remove.command(name="channel")
    async def remove_channel(self, ctx):
        config = load.get_config(ctx.guild.id, "channel")
        if config:
            world = config.get(str(ctx.channel.id))
            state = bool(world)
        else:
            state = False

        if not state:
            msg = "Dieser Channel hat keine eigene Welt"
            return await ctx.send(embed=error_embed(msg))

        config.pop(str(ctx.channel.id))
        load.change_config(ctx.guild.id, "channel", config)
        msg = "Die Channel-Welt wurde gelöscht"
        await ctx.send(embed=complete_embed(msg))

    @commands.command(name="world")
    async def get_world(self, ctx):
        cas = "Welt " if ctx.world > 50 else "Casual "
        msg = f"{cas}{ctx.world}"
        await ctx.send(embed=complete_embed(msg))

    @commands.group(case_insensitive=True)
    async def conquer(self, ctx):
        channel = load.get_config(ctx.guild.id, "conquer")
        if not channel:
            raise ConquerChannelMissing

    @conquer.command(name="add")
    async def conquer_add(self, ctx, tribe: DSObject):
        cache = load.get_config(ctx.guild.id, "filter")
        if cache is None:
            cache = []
        if tribe.alone:
            msg = "Der Filter unterstützt nur Stämme"
            return await ctx.send(embed=error_embed(msg))
        if tribe.id in cache:
            msg = "Der Stamm ist bereits eingespeichert"
            return await ctx.send(embed=error_embed(msg))
        cache.append(tribe.id)
        load.change_config(ctx.guild.id, "filter", cache)
        msg = "done"
        await ctx.send(embed=complete_embed(msg))

    @conquer.command(name="remove")
    async def conquer_remove(self, ctx, tribe: DSObject):
        cache = load.get_config(ctx.guild.id, "filter")
        if cache is None:
            cache = []
        if tribe.alone:
            msg = "Der Filter unterstützt nur Stämme"
            return await ctx.send(embed=error_embed(msg))
        if tribe.id not in cache:
            msg = "Der Stamm ist nicht eingespeichert"
            return await ctx.send(embed=error_embed(msg))
        cache.remove(tribe.id)
        load.change_config(ctx.guild.id, "filter", cache)
        msg = "done"
        await ctx.send(embed=complete_embed(msg))

    @conquer.command(name="grey")
    async def conquer_grey(self, ctx):
        cache = load.get_config(ctx.guild.id, "bb")
        state = True if not cache else False
        load.change_config(ctx.guild.id, "bb", state)
        state_str = "aktiv" if state else "inaktiv"
        msg = f"Der Filter für Barbarendörfer ist nun {state_str}"
        await ctx.send(embed=complete_embed(msg))

    @conquer.command(name="list")
    async def conquer_list(self, ctx):
        filter_list = load.get_config(ctx.guild.id, "filter")
        if not filter_list:
            msg = "Aktuell ist kein Stamm im Filter gespeichert"
            return await ctx.send(embed=error_embed(msg))

        cache = await load.find_allys(ctx.world, filter_list)
        data = [obj.name for obj in cache]
        title = f"{len(data)} Stämme insgesamt"
        embed = discord.Embed(title=title, description='\n'.join(data[:10]))
        await ctx.send(embed=embed)

    @conquer.command(name="clear")
    async def conquer_clear(self, ctx):
        load.change_config(ctx.guild.id, "filter", [])
        msg = "Der Filter wurde zurückgesetzt"
        await ctx.send(embed=complete_embed(msg))


def setup(bot):
    bot.add_cog(Set(bot))
