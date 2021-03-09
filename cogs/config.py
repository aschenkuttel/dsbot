from utils import complete_embed, error_embed
from discord.ext import commands
import discord
import logging
import utils

logger = logging.getLogger('dsbot')


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.type = 0
        self.config = self.bot.config

    async def cog_check(self, ctx):
        if ctx.guild is None:
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        else:
            raise commands.MissingPermissions(['administrator'])

    def get_conquer_data(self, ctx):
        conquer = self.config.get_conquer(ctx)
        if not conquer:
            raise utils.ConquerChannelMissing()

        channel_config = conquer.get(str(ctx.channel.id))
        if channel_config is None:
            raise utils.WrongChannel('conquer')
        else:
            return channel_config

    @commands.group(invoke_without_command=True)
    async def set(self, _):
        keys = ("world", "channel_world", "game", "conquer", "prefix")
        raise utils.MissingRequiredKey(keys)

    @set.command(name="world")
    async def set_world(self, ctx, world: utils.WorldConverter):
        old_world = self.config.get_related_world(ctx.guild)

        if world == old_world:
            msg = f"Der Server ist bereits mit {world} verbunden"
            await ctx.send(embed=error_embed(msg))
        else:
            self.config.update('world', world.server, ctx.guild.id)
            msg = f"Der Server ist nun mit {world} verbunden"
            await ctx.send(embed=complete_embed(msg))

    @set.command(name="channelworld")
    async def set_channelworld(self, ctx, world: utils.WorldConverter):
        config = self.config.get('channel', ctx.guild.id)

        if config is None:
            config = {str(ctx.channel.id): world.server}
            self.config.update('channel', config, ctx.guild.id)

        else:
            old_world = config.get(str(ctx.channel.id))

            if old_world == world:
                msg = f"Dieser Channel ist bereits mit {world} verbunden"
                await ctx.send(embed=error_embed(msg))
                return

            else:
                config[str(ctx.channel.id)] = world.server
                self.config.save()

        msg = f"Der Channel ist nun mit {world} verbunden"
        await ctx.send(embed=complete_embed(msg))

    @set.command(name="game")
    async def set_game(self, ctx):
        cur = self.config.get('game', ctx.guild.id)

        if cur == ctx.channel.id:
            msg = "Der aktuelle Channel ist bereits eingespeichert"
            await ctx.send(embed=error_embed(msg))
        else:
            self.config.update('game', ctx.channel.id, ctx.guild.id)
            msg = f"{ctx.channel.mention} ist nun der aktive Game Channel"
            await ctx.send(embed=complete_embed(msg))

    @set.command(name="conquer")
    async def set_conquer(self, ctx):
        channels = self.config.get('conquer', ctx.guild.id, default={})

        if str(ctx.channel.id) in channels:
            msg = "Der aktuelle Channel ist bereits eingespeichert"
            await ctx.send(embed=error_embed(msg))

        elif len(channels) >= 2:
            msg = "Momentan sind nur 2 Eroberungschannel möglich"
            await ctx.send(embed=error_embed(msg))

        else:
            channels[str(ctx.channel.id)] = {'bb': False, 'tribe': [], 'player': []}
            self.config.update('conquer', channels, ctx.guild.id)
            msg = f"{ctx.channel.mention} ist nun ein Eroberungschannel"
            await ctx.send(embed=complete_embed(msg))

    @set.command(name="prefix")
    async def set_prefix(self, ctx, new_prefix):
        prefix = self.config.get_prefix(ctx.guild.id)

        if new_prefix == prefix:
            msg = "`{}` ist bereits der aktuelle Prefix dieses Servers"
            await ctx.send(embed=error_embed(msg.format(prefix)))

        else:
            self.config.update('prefix', new_prefix, ctx.guild.id)
            msg = f"Der Prefix `{new_prefix}` ist nun aktiv"
            await ctx.send(embed=complete_embed(msg))

    @commands.command(name="convert")
    async def convert_(self, ctx, key=None):
        if key is None:
            listed = []

            for key, value in ctx.lang.converter_title.items():
                state = self.bot.config.get_switch(key, ctx.guild.id)
                represent = "aktiv" if state else "inaktiv"
                listed.append(f"**{value} ({key}):** `{represent}`")

            msg = "\n".join(listed)

        else:
            key = key.lower()
            name = ctx.lang.converter_title.get(key)

            if name is None:
                raise utils.MissingRequiredKey(ctx.lang.converter_title)

            new_value = self.bot.config.update_switch(key, ctx.guild.id)
            state = "aktiv" if new_value else "inaktiv"
            msg = f"Die Konvertierung der {name} ist nun {state}"

        await ctx.send(embed=complete_embed(msg))

    @commands.group(invoke_without_command=True)
    async def remove(self, ctx, entry):
        entry = entry.lower()
        config_entry = ctx.lang.config_title.get(entry)

        if config_entry is None:
            keys = list(ctx.lang.config_title.keys())
            keys.extend(["channelworld", "conquer"])
            raise utils.MissingRequiredKey(keys)

        done = self.config.remove(entry, ctx.guild.id)
        if not done:
            msg = f"Der Server hat keinen zugewiesenen {config_entry}"
            await ctx.send(embed=error_embed(msg))

        else:
            msg = f"{config_entry} erfolgreich gelöscht"
            await ctx.send(embed=complete_embed(msg))

    @remove.command(name="conquer")
    async def remove_conquer(self, ctx, channel_id=None):
        config = self.config.get('conquer', ctx.guild.id)
        channel_id = channel_id or str(ctx.channel.id)

        if config and channel_id in config:
            config.pop(channel_id)
            self.config.save()

            channel = ctx.guild.get_channel(int(channel_id))
            mention = channel.mention if channel else f"{channel_id}"
            msg = f"{mention} ist nun kein Eroberungschannel mehr"
            await ctx.send(embed=complete_embed(msg))

        else:
            msg = "Dies ist kein Conquer Channel"
            await ctx.send(embed=error_embed(msg))

    @remove.command(name="channelworld")
    async def remove_channelworld(self, ctx):
        config = self.config.get('channel', ctx.guild.id)
        channel_id = str(ctx.channel.id)

        if config and channel_id in config:
            config.pop(channel_id)
            self.config.save()
            msg = "Die Welt des Channels wurde gelöscht"
            await ctx.send(embed=complete_embed(msg))

        else:
            msg = "Der Channel hat keine eigene Welt"
            await ctx.send(embed=error_embed(msg))

    @commands.group(name="conquer", invoke_without_command=True)
    async def conquer(self, ctx):
        self.get_conquer_data(ctx)
        cmd = self.bot.get_command('help conquer')
        await ctx.invoke(cmd)

    @conquer.command(name="add")
    async def conquer_add(self, ctx, *, dsobj: utils.DSConverter):
        conquer = self.get_conquer_data(ctx)

        if dsobj.id in conquer[dsobj.type]:
            msg = "Der Stamm ist bereits eingespeichert"
            await ctx.send(embed=error_embed(msg))

        else:
            conquer[dsobj.type].append(dsobj.id)
            self.config.save()

            msg = f"`{dsobj}` wurde hinzugefügt"
            await ctx.send(embed=complete_embed(msg))

    @conquer.command(name="remove")
    async def conquer_remove(self, ctx, *, dsobj: utils.DSConverter):
        conquer = self.get_conquer_data(ctx)

        if dsobj.id not in conquer[dsobj.type]:
            msg = "Der Stamm ist nicht eingespeichert"
            await ctx.send(embed=error_embed(msg))

        else:
            conquer[dsobj.type].remove(dsobj.id)
            self.config.save()

            msg = f"`{dsobj}` wurde entfernt"
            await ctx.send(embed=complete_embed(msg))

    @conquer.command(name="grey")
    async def conquer_grey(self, ctx):
        conquer = self.get_conquer_data(ctx)
        conquer['bb'] = not conquer.get('bb')
        self.config.save()

        state_str = "ausgeblendet" if not conquer['bb'] else "angezeigt"
        msg = f"Die Eroberungen von Barbarendörfern werden nun {state_str}"
        await ctx.send(embed=complete_embed(msg))

    @conquer.command(name="list")
    async def conquer_list(self, ctx):
        conquer = self.get_conquer_data(ctx)

        if not conquer['tribe'] and not conquer['player']:
            msg = "Du hast noch keinen Stamm oder Spieler in den Filter eingetragen"
            await ctx.send(embed=error_embed(msg))

        else:
            world = self.config.get_world(ctx.channel)

            counter = 0
            embed = discord.Embed()
            for dstype in ('tribe', 'player'):
                cache = await self.bot.fetch_bulk(world, conquer[dstype], dstype)

                if not cache:
                    continue

                data = [str(obj) for obj in cache[:20]]
                name = "Stämme:" if dstype == "tribe" else "Spieler:"
                embed.add_field(name=name, value="\n".join(data), inline=False)
                counter += len(data)

            name = "Element" if counter == 1 else "Elemente"
            embed.title = f"{counter} {name} insgesamt:"
            await ctx.send(embed=embed)

    @conquer.command(name="clear")
    async def conquer_clear(self, ctx):
        conquer = self.get_conquer_data(ctx)
        conquer['tribe'].clear()
        conquer['player'].clear()
        self.config.save()

        msg = "Der Filter wurde zurückgesetzt"
        await ctx.send(embed=complete_embed(msg))


def setup(bot):
    bot.add_cog(Config(bot))
