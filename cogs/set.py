from utils import WorldConverter, DSConverter,  WrongChannel, complete_embed, error_embed
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

    def get_conquer_data(self, ctx):
        conquer = self.config.get_item(ctx.guild.id, 'conquer', {})
        channel_data = conquer.get(str(ctx.channel.id))

        if channel_data is None:
            raise WrongChannel('conquer')

        else:
            return channel_data

    @commands.group(invoke_without_command=True)
    async def set(self, ctx):
        pre = self.config.get_prefix(ctx.guild.id)
        msg = f"`{pre}set [world|game|conquer|channel|prefix]`"
        await ctx.send(embed=error_embed(msg))

    @set.command(name="world")
    async def set_world(self, ctx, world: WorldConverter):
        old_world = self.config.get_related_world(ctx.guild)
        res = "bereits" if world == old_world else "nun"
        msg = f"Der Server ist {res} mit {world} verbunden"

        if world == old_world:
            await ctx.send(embed=error_embed(msg))
        else:
            self.config.change_item(ctx.guild.id, 'world', world.server)
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
        channels = self.config.get_item(ctx.guild.id, "conquer", default={})
        if str(ctx.channel.id) in channels:
            msg = "Der aktuelle Channel ist bereits eingespeichert"
            await ctx.send(embed=error_embed(msg))

        elif len(channels) >= 2:
            msg = "Du kannst nur 2 Eroberungschannel haben"
            await ctx.send(embed=error_embed(msg))

        else:
            channels[str(ctx.channel.id)] = {'bb': False, 'filter': []}
            self.config.change_item(ctx.guild.id, "conquer", channels)
            msg = f"{ctx.channel.mention} ist nun Eroberungschannel"
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
    async def set_channel(self, ctx, world: WorldConverter):
        config = self.config.get_item(ctx.guild.id, 'channel')
        if config is None:
            cache = {str(ctx.channel.id): world.server}
            self.config.change_item(ctx.guild.id, 'channel', cache)

        else:
            old_world = config.get(str(ctx.channel.id))
            if old_world == world:
                msg = f"Dieser Channel ist bereits zu **{world}** gelinked"
                return await ctx.send(embed=error_embed(msg))
            else:
                config[str(ctx.channel.id)] = world.server
                self.config.save()

        msg = f"Der Channel wurde mit **{world}** gelinked"
        await ctx.send(embed=complete_embed(msg))

    @commands.group(invoke_without_command=True)
    async def remove(self, ctx, entry):
        entries = {'game': "Game Channel",
                   'prefix': "Prefix"}

        if entry.lower() not in entries:
            base = "**Fehlerhafte Eingabe:** {}remove <{}>"
            msg = base.format(ctx.prefix, "/".join(entries))
            return await ctx.send(embed=error_embed(msg))

        done = self.config.remove_item(ctx.guild.id, entry.lower())
        if not done:
            msg = f"Der Server hat keinen zugewiesenen **{entries[entry]}**"
            await ctx.send(embed=error_embed(msg))

        else:
            msg = f"**{entries[entry]}** erfolgreich gelöscht"
            await ctx.send(embed=complete_embed(msg))

    @remove.command(name="conquer")
    async def remove_conquer(self, ctx):
        channels = self.config.get_item(ctx.guild.id, 'conquer')
        if str(ctx.channel.id) in channels:
            channels.pop(str(ctx.channel.id))
            self.config.save()

            msg = f"{ctx.channel.mention} ist kein Eroberungschannel mehr"
            await ctx.send(embed=complete_embed(msg))

        else:
            msg = "Dieser Channel ist nicht eingespeichert"
            await ctx.send(embed=error_embed(msg))

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

    @commands.group(name="conquer", invoke_without_command=True)
    async def conquer(self, ctx):
        cmd = self.bot.get_command("help conquer")
        await ctx.invoke(cmd)

    @conquer.command(name="add")
    async def conquer_add(self, ctx, tribe: DSConverter):
        conquer = self.get_conquer_data(ctx)

        if tribe.alone:
            msg = "Der Filter unterstützt nur Stämme"
            await ctx.send(embed=error_embed(msg))

        elif tribe.id in conquer['filter']:
            msg = "Der Stamm ist bereits eingespeichert"
            await ctx.send(embed=error_embed(msg))

        else:
            conquer['filter'].append(tribe.id)
            self.config.save()

            msg = f"`{tribe.name}` wurde hinzugefügt"
            await ctx.send(embed=complete_embed(msg))

    @conquer.command(name="remove")
    async def conquer_remove(self, ctx, tribe: DSConverter):
        conquer = self.get_conquer_data(ctx)

        if tribe.alone:
            msg = "Der Filter unterstützt nur Stämme"
            await ctx.send(embed=error_embed(msg))

        elif tribe.id not in conquer['filter']:
            msg = "Der Stamm ist nicht eingespeichert"
            await ctx.send(embed=error_embed(msg))

        else:
            conquer['filter'].remove(tribe.id)
            self.config.save()

            msg = f"`{tribe.name}` wurde entfernt"
            await ctx.send(embed=complete_embed(msg))

    @conquer.command(name="grey")
    async def conquer_grey(self, ctx):
        conquer = self.get_conquer_data(ctx)
        conquer['bb'] = True if not conquer['bb'] else False
        self.config.save()

        state_str = "aktiv" if not conquer['bb'] else "inaktiv"
        msg = f"Der Filter für Barbarendörfer ist nun {state_str}"
        await ctx.send(embed=complete_embed(msg))

    @conquer.command(name="list")
    async def conquer_list(self, ctx):
        conquer = self.get_conquer_data(ctx)

        if not conquer['filter']:
            msg = "Es befindet sich kein Stamm im Filter"
            return await ctx.send(embed=error_embed(msg))

        world = self.config.get_related_world(ctx.guild)
        cache = await self.bot.fetch_bulk(world, conquer['filter'], 'tribe')
        data = [obj.name for obj in cache]

        name = "Stamm" if len(data) == 1 else "Stämme"
        title = f"{len(data)} {name} insgesamt:"
        embed = discord.Embed(title=title, description="\n".join(data[:10]))
        await ctx.send(embed=embed)

    @conquer.command(name="clear")
    async def conquer_clear(self, ctx):
        conquer = self.get_conquer_data(ctx)
        conquer['filter'].clear()
        self.config.save()

        msg = "Der Filter wurde zurückgesetzt"
        await ctx.send(embed=complete_embed(msg))


def setup(bot):
    bot.add_cog(Set(bot))
