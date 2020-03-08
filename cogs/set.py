from utils import DSObject, World, complete_embed, error_embed
from discord.ext import commands
import discord


class Set(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config

    async def cog_check(self, ctx):
        if ctx.guild is None:
            raise commands.NoPrivateMessage
        if ctx.author.guild_permissions.administrator:
            return True
        raise commands.MissingPermissions(['administrator'])

    @commands.group(invoke_without_command=True)
    async def set(self, ctx):
        pre = self.config.get_prefix(ctx.guild.id)
        msg = f"`{pre}set [world|game|conquer|channel|prefix]`"
        await ctx.send(embed=error_embed(msg))

    @set.command(name="world")
    async def set_world(self, ctx, world: World):
        res = "bereits" if world == ctx.world else "nun"
        msg = f"Der Server ist {res} mit `{world}` verbunden"

        # --- Check if World already linked --- #
        if world == ctx.world:
            await ctx.send(embed=error_embed(msg))
        else:
            self.config.change_item(ctx.guild.id, 'world', world.number)
            await ctx.send(embed=complete_embed(msg))

    @set.command(name="game")
    async def set_game(self, ctx):
        cur = self.config.get_item(ctx.guild.id, "game")
        if cur == ctx.channel.id:
            msg = "Der aktuelle Channel ist bereits eingespeichert"
            await ctx.send(embed=error_embed(msg))
        else:
            self.config.change_item(ctx.guild.id, "game", ctx.channel.id)
            msg = f"<#{ctx.channel.id}> ist nun der aktive Game-Channel"
            await ctx.send(embed=complete_embed(msg))

    @set.command(name="conquer")
    async def set_conquer(self, ctx):
        cur = self.config.get_item(ctx.guild.id, "conquer")
        if cur == ctx.channel.id:
            msg = "Der aktuelle Channel ist bereits eingespeichert"
            await ctx.send(embed=error_embed(msg))
        else:
            self.config.change_item(ctx.guild.id, "conquer", ctx.channel.id)
            msg = f"<#{ctx.channel.id}> ist nun der aktive Eroberungschannel"
            await ctx.send(embed=complete_embed(msg))

    @set.command(name="prefix")
    async def set_prefix(self, ctx, pre):
        cur = self.config.get_prefix(ctx.guild.id)
        if cur == pre:
            msg = f"`{cur}` ist bereits der aktuelle Prefix dieses Servers"
            await ctx.send(embed=error_embed(msg))

        else:
            self.config.change_item(ctx.guild.id, 'prefix', pre)
            msg = f"Der Prefix `{pre}` ist nun aktiv"
            await ctx.send(embed=complete_embed(msg))

    @set.command(name="channel")
    async def set_channel(self, ctx, world: World):
        config = self.config.get_item(ctx.guild.id, 'channel')
        if config is None:
            cache = {str(ctx.channel.id): world.number}
            self.config.change_item(ctx.guild.id, 'channel', cache)

        else:
            old_world = config.get(str(ctx.channel.id))
            if old_world == world:
                msg = f"Dieser Channel ist bereits zu **{world}** gelinked"
                return await ctx.send(embed=error_embed(msg))
            else:
                config[str(ctx.channel.id)] = world.number
                self.config.save()

        msg = f"Der Channel wurde mit **{world}** gelinked"
        await ctx.send(embed=complete_embed(msg))

    @commands.group(invoke_without_command=True)
    async def remove(self, ctx, entry):
        entries = {'game': "Game Channel",
                   'conquer': "Eroberungschannel",
                   'prefix': "Prefix"}

        if entry.lower() not in entries:
            example = f"{ctx.prefix}remove <{'/'.join(entries)}>"
            msg = f"**Fehlerhafte Eingabe:** {example}"
            return await ctx.send(embed=error_embed(msg))

        done = self.config.remove_item(ctx.guild.id, entry.lower())
        if not done:
            msg = f"Der Server hat keinen zugewiesenen **{entries[entry]}**"
            await ctx.send(embed=error_embed(msg))
        else:
            msg = f"**{entries[entry]}** erfolgreich gelöscht"
            await ctx.send(embed=complete_embed(msg))

    @remove.command(name="channel")
    async def remove_channel(self, ctx):
        config = self.config.get_item(ctx.guild.id, 'channel')
        if config:
            world = config.get(str(ctx.channel.id))
            state = bool(world)
        else:
            state = False

        if not state:
            msg = "Dieser Channel hat keine eigene Welt"
            await ctx.send(embed=error_embed(msg))
        else:
            config.pop(str(ctx.channel.id))
            self.config.save()
            msg = "Die Channel-Welt wurde gelöscht"
            await ctx.send(embed=complete_embed(msg))

    @commands.command(name="world")
    async def get_world(self, ctx):
        world_name = f"{World(ctx.world)}"
        await ctx.send(embed=complete_embed(world_name))

    @commands.command(name="worlds")
    async def worlds_(self, ctx):
        worlds = sorted(self.bot.worlds)
        normal, casual = [], []
        for world in worlds:
            iterable = normal if world > 50 else casual
            iterable.append(str(world))

        result = []
        for wlist in normal, casual:
            cache = ""
            counter = 0
            for index, world in enumerate(wlist):
                if counter == 3:
                    cache += f"{world}\n"
                    counter = 0
                else:
                    if world == wlist[-1]:
                        cache += f"{world}"
                    else:
                        cache += f"{world}, "
                    counter += 1
            result.append(cache)

        base = "**Normale Welten:**\n{0}\n**Casual:**\n{1}"
        embed = discord.Embed(description=base.format(*result))
        await ctx.send(embed=embed)

    @commands.group(name="conquer")
    async def conquer(self, ctx):
        cmd = self.bot.get_command("help conquer")
        await ctx.invoke(cmd)

    @conquer.command(name="add")
    async def conquer_add(self, ctx, tribe: DSObject):
        cache = self.config.get_item(ctx.guild.id, 'filter')
        if cache is None:
            cache = []

        if tribe.alone:
            msg = "Der Filter unterstützt nur Stämme"
            await ctx.send(embed=error_embed(msg))

        elif tribe.id in cache:
            msg = "Der Stamm ist bereits eingespeichert"
            await ctx.send(embed=error_embed(msg))

        else:
            cache.append(tribe.id)
            self.config.change_item(ctx.guild.id, 'filter', cache)
            msg = f"`{tribe.name}` wurde hinzugefügt"
            await ctx.send(embed=complete_embed(msg))

    @conquer.command(name="remove")
    async def conquer_remove(self, ctx, tribe: DSObject):
        cache = self.config.get_item(ctx.guild.id, 'filter')
        if cache is None:
            cache = []

        if tribe.alone:
            msg = "Der Filter unterstützt nur Stämme"
            await ctx.send(embed=error_embed(msg))

        elif tribe.id not in cache:
            msg = "Der Stamm ist nicht eingespeichert"
            await ctx.send(embed=error_embed(msg))

        else:
            cache.remove(tribe.id)
            self.config.change_item(ctx.guild.id, 'filter', cache)
            msg = f"`{tribe.name}` wurde entfernt"
            await ctx.send(embed=complete_embed(msg))

    @conquer.command(name="grey")
    async def conquer_grey(self, ctx):
        cache = self.config.get_item(ctx.guild.id, 'bb')
        state = False if cache is not False else True
        self.config.change_item(ctx.guild.id, 'bb', state)
        state_str = "aktiv" if not state else "inaktiv"
        msg = f"Der Filter für Barbarendörfer ist nun {state_str}"
        await ctx.send(embed=complete_embed(msg))

    @conquer.command(name="list")
    async def conquer_list(self, ctx):
        filter_list = self.config.get_item(ctx.guild.id, 'filter')
        if not filter_list:
            msg = "Es befindet sich kein Stamm im Filter"
            return await ctx.send(embed=error_embed(msg))

        world = self.config.get_guild_world(ctx.guild)
        cache = await self.bot.fetch_bulk(world, filter_list, 'tribe')
        data = [obj.name for obj in cache]

        name = "Stamm" if len(data) == 1 else "Stämme"
        title = f"{len(data)} {name} insgesamt"
        embed = discord.Embed(title=title, description="\n".join(data[:10]))
        await ctx.send(embed=embed)

    @conquer.command(name="clear")
    async def conquer_clear(self, ctx):
        self.config.remove_item(ctx.guild.id, 'filter')
        msg = "Der Filter wurde zurückgesetzt"
        await ctx.send(embed=complete_embed(msg))


def setup(bot):
    bot.add_cog(Set(bot))
