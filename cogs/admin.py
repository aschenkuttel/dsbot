from discord.ext import commands
from discord import app_commands
import utils


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.type = 0
        self.games = {'Word': ["hangman", "anagram"],
                      'Card': ["quiz", "tribalcard"],
                      'Poker': ["blackjack", "videopoker"]}
        self.config_types = ["game", "conquer", "config"]

    @app_commands.command(name="enable",
                          description="Aktiviert den Server wieder falls dieser als inaktiv markiert wurde")
    @app_commands.checks.has_permissions(administrator=True)
    async def enable_(self, interaction):
        inactive = self.bot.config.get('inactive', interaction.guild.id)
        if inactive is True:
            self.bot.config.remove('inactive', interaction.guild.id)
            msg = "Der Server ist nun wieder als aktiv marktiert"
            embed = utils.complete_embed(msg)
        else:
            msg = "Der Server ist bereits aktiv"
            embed = utils.error_embed(msg)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="reset", description="Setzt eine oder die gesamte Config des Servers zurück")
    @app_commands.rename(config_type="type")
    @app_commands.describe(config_type="<game|conquer|config>")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset(self, interaction, config_type: str):
        if config_type == "game":
            for name, caches in self.games.items():
                cog = self.bot.get_cog(name)

                for cache_name in caches:
                    cache = getattr(cog, cache_name)
                    cache.pop(interaction.guild.id, None)

            msg = "Alle Spiele wurden zurückgesetzt"
            await interaction.response.send_message(embed=utils.complete_embed(msg))

        elif config_type == "conquer":
            self.bot.config.update('conquer', {}, interaction.guild.id)
            msg = "Die Conquereinstellungen wurden zurückgesetzt"
            await interaction.response.send_message(embed=utils.complete_embed(msg))

        elif config_type == "config":
            self.bot.config.remove_config(interaction.guild.id)
            msg = "Die Servereinstellungen wurden zurückgesetzt"
            await interaction.response.send_message(embed=utils.complete_embed(msg))

        else:
            msg = f"`/reset <{'|'.join(self.config_types)}>`"
            await interaction.response.send_message(embed=utils.error_embed(msg))

    @app_commands.command(name="world", description="Die aktuelle Welt des Channels")
    async def world(self, interaction):
        world = self.bot.config.get_related_world(interaction.channel)
        relation = "Channel" if world == interaction.server else "Server"
        embed = utils.complete_embed(f"{interaction.world} [{relation}]")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Admin(bot))
