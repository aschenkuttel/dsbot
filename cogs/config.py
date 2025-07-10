from utils import complete_embed, error_embed
from discord.ext import commands
from discord import app_commands
import discord
import logging
import utils

logger = logging.getLogger('dsbot')


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.type = 0
        self.config = bot.config

    def get_conquer_data(self, interaction):
        conquer = self.config.get_conquer(interaction.guild.id)
        if not conquer:
            raise utils.ConquerChannelMissing()

        channel_config = conquer.get(str(interaction.channel.id))
        if channel_config is None:
            raise utils.WrongChannel('conquer')
        else:
            return channel_config

    set = app_commands.Group(name="set", description="Einstellungen hinzufügen")

    @set.command(name="world", description="Hinterlegt dem Server eine Welt")
    @app_commands.describe(world="Die gewünschte neue Server-Welt")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_world(self, interaction, world: utils.WorldConverter):
        old_server = self.config.get_related_world(interaction.guild)

        if world.server == old_server:
            msg = f"Der Server ist bereits mit {world} verbunden"
            await interaction.response.send_message(embed=error_embed(msg))
        else:
            self.config.update('world', world.server, interaction.guild.id)
            msg = f"Der Server ist nun mit {world} verbunden"
            await interaction.response.send_message(embed=complete_embed(msg))

    @set.command(name="channelworld", description="Hinterlegt dem Channel eine Welt")
    @app_commands.describe(world="Die gewünschte neue Channel-Welt")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_channelworld(self, interaction, world: utils.WorldConverter):
        config = self.config.get('channel', interaction.guild.id)
        str_channel_id = str(interaction.channel.id)

        if config is None:
            config = {str_channel_id: world.server}
            self.config.update('channel', config, interaction.guild.id)

        else:
            old_server = config.get(str_channel_id)

            if world.server == old_server:
                msg = f"Dieser Channel ist bereits mit {world} verbunden"
                await interaction.response.send_message(embed=error_embed(msg))
                return

            else:
                config[str_channel_id] = world.server
                self.config.save()

        msg = f"Der Channel ist nun mit {world} verbunden"
        await interaction.response.send_message(embed=complete_embed(msg))

    @set.command(name="game", description="Aktiviert den Game Channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_game(self, interaction):
        game_channel_id = self.config.get('game', interaction.guild.id)

        if game_channel_id == interaction.channel.id:
            msg = "Der aktuelle Channel ist bereits eingespeichert"
            await interaction.response.send_message(embed=error_embed(msg))
        else:
            self.config.update('game', interaction.channel.id, interaction.guild.id)
            msg = f"{interaction.channel.mention} ist nun der aktive Game Channel"
            await interaction.response.send_message(embed=complete_embed(msg))

    @set.command(name="conquer", description="Aktiviert den Conquer Channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_conquer(self, interaction):
        channels = self.config.get('conquer', interaction.guild.id, default={})

        if str(interaction.channel.id) in channels:
            msg = "Der aktuelle Channel ist bereits eingespeichert"
            await interaction.response.send_message(embed=error_embed(msg))

        elif len(channels) >= 2:
            msg = "Momentan sind nur 2 Conquer Channel möglich"
            await interaction.response.send_message(embed=error_embed(msg))

        else:
            channels[str(interaction.channel.id)] = {'bb': False, 'tribe': [], 'player': []}
            self.config.update('conquer', channels, interaction.guild.id)
            msg = f"{interaction.channel.mention} ist nun ein Conquer Channel"
            await interaction.response.send_message(embed=complete_embed(msg))

    remove = app_commands.Group(name="remove", description="Einstellungen entfernen")

    @remove.command(name="channelworld", description="Entfernt die Channel Welt")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_channelworld(self, interaction):
        config = self.config.get('channel', interaction.guild.id)
        channel_id = str(interaction.channel.id)

        if config and channel_id in config:
            config.pop(channel_id)
            self.config.save()
            msg = "Die Welt des Channels wurde gelöscht"
            await interaction.response.send_message(embed=complete_embed(msg))

        else:
            msg = "Der Channel hat keine eigene Welt"
            await interaction.response.send_message(embed=error_embed(msg))

    @remove.command(name="game", description="Entfernt den Game Channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_game(self, interaction, channel_id: int = None):
        game_channel_id = self.config.get('game', interaction.guild.id)
        channel_id = channel_id or interaction.channel.id

        if game_channel_id and channel_id == game_channel_id:
            self.config.remove('game', interaction.guild.id)
            self.config.save()

            channel = interaction.guild.get_channel(channel_id)
            mention = channel.mention if channel else f"{channel_id}"
            msg = f"{mention} ist nun nicht mehr der Game-Channel"
            await interaction.response.send_message(embed=complete_embed(msg))

        else:
            msg = "Dies ist nicht der Game-Channel"
            await interaction.response.send_message(embed=error_embed(msg))

    @remove.command(name="conquer", description="Entfernt den Conquer Channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_conquer(self, interaction, channel_id: int = None):
        # conquer channel ids are stored as strings, hence the parsing
        config = self.config.get('conquer', interaction.guild.id)
        channel_id = str(channel_id or interaction.channel.id)

        if config and channel_id in config:
            config.pop(channel_id)
            self.config.save()

            channel = interaction.guild.get_channel(int(channel_id))
            mention = channel.mention if channel else f"{channel_id}"
            msg = f"{mention} ist nun kein Eroberungs-Channel mehr"
            await interaction.response.send_message(embed=complete_embed(msg))

        else:
            msg = "Dies ist kein Eroberungs-Channel"
            await interaction.response.send_message(embed=error_embed(msg))

    conquer = app_commands.Group(name="conquer", description="Einstellungen für Conquer Channel")

    @conquer.command(name="add", description="Fügt einen Stamm oder Spieler dem Conquer Filter hinzu")
    @app_commands.checks.has_permissions(administrator=True)
    async def conquer_add(self, interaction, dsobj: utils.DSConverter):
        conquer = self.get_conquer_data(interaction)

        if dsobj.id in conquer[dsobj.type]:
            msg = "Der Stamm ist bereits eingespeichert"
            await interaction.response.send_message(embed=error_embed(msg))

        else:
            conquer[dsobj.type].append(dsobj.id)
            self.config.save()

            msg = f"`{dsobj}` wurde hinzugefügt"
            await interaction.response.send_message(embed=complete_embed(msg))

    @conquer.command(name="remove", description="Entfernt einen Stamm oder Spieler aus dem Conquer Filter")
    @app_commands.checks.has_permissions(administrator=True)
    async def conquer_remove(self, interaction, dsobj: utils.DSConverter):
        conquer = self.get_conquer_data(interaction)

        if dsobj.id not in conquer[dsobj.type]:
            msg = "Der Stamm ist nicht eingespeichert"
            await interaction.response.send_message(embed=error_embed(msg))

        else:
            conquer[dsobj.type].remove(dsobj.id)
            self.config.save()

            msg = f"`{dsobj}` wurde entfernt"
            await interaction.response.send_message(embed=complete_embed(msg))

    @conquer.command(name="grey", description="Toggled die Eroberungen von Barbarendörfern")
    @app_commands.checks.has_permissions(administrator=True)
    async def conquer_grey(self, interaction):
        conquer = self.get_conquer_data(interaction)
        conquer['bb'] = not conquer.get('bb')
        self.config.save()

        state_str = "ausgeblendet" if not conquer['bb'] else "angezeigt"
        msg = f"Die Eroberungen von Barbarendörfern werden nun {state_str}"
        await interaction.response.send_message(embed=complete_embed(msg))

    @conquer.command(name="list", description="Zeigt den Conquer Filter des Channels")
    @app_commands.checks.has_permissions(administrator=True)
    async def conquer_list(self, interaction):
        await interaction.response.defer()
        conquer = self.get_conquer_data(interaction)

        if not conquer['tribe'] and not conquer['player']:
            msg = "Du hast noch keinen Stamm oder Spieler in den Filter eingetragen"
            await interaction.followup.send(embed=error_embed(msg))

        else:
            world = self.config.get_world(interaction.channel)

            counter = 0
            embed = discord.Embed()
            for dstype in ('tribe', 'player'):
                cache = await interaction.client.fetch_bulk(world, conquer[dstype], dstype)

                if not cache:
                    continue

                data = [str(obj) for obj in cache[:20]]
                name = "Stämme:" if dstype == "tribe" else "Spieler:"
                embed.add_field(name=name, value="\n".join(data), inline=False)
                counter += len(data)

            name = "Element" if counter == 1 else "Elemente"
            embed.title = f"{counter} {name} insgesamt:"
            await interaction.followup.send(embed=embed)

    @conquer.command(name="clear", description="Setzt den Conquer Filter zurück")
    @app_commands.checks.has_permissions(administrator=True)
    async def conquer_clear(self, interaction):
        conquer = self.get_conquer_data(interaction)
        conquer['tribe'].clear()
        conquer['player'].clear()
        self.config.save()

        msg = "Der Filter wurde zurückgesetzt"
        await interaction.response.send_message(embed=complete_embed(msg))

    convert = app_commands.Group(name="convert", description="Einstellungen der Message Converter")

    @convert.command(name="list", description="Zeigt die aktuellen Converter Einstellungen")
    @app_commands.checks.has_permissions(administrator=True)
    async def convert_list(self, interaction):
        listed = []

        switches = self.bot.config.get_switches(interaction.guild.id)

        for key, value in interaction.lang.converter_title.items():
            state = switches.get(key, True)
            represent = "aktiv" if state else "inaktiv"
            listed.append(f"**{value} ({key}):** `{represent}`")

        msg = "\n".join(listed)
        await interaction.response.send_message(embed=complete_embed(msg))

    @convert.command(name="toggle", description="Toggled den gewünschten Konverter AN/AUS")
    @app_commands.describe(key="Der gewünschte Konverter")
    @app_commands.checks.has_permissions(administrator=True)
    async def convert_toggle(self, interaction, key: utils.ConversionKeyConverter):
        name, value = key
        new_value = self.bot.config.update_switch(value, interaction.guild.id)
        state = "aktiv" if new_value else "inaktiv"
        msg = f"Die Konvertierung der {name} ist nun {state}"
        await interaction.response.send_message(embed=complete_embed(msg))


async def setup(bot):
    await bot.add_cog(Config(bot))
