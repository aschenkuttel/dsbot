from discord import app_commands
from discord.ext import commands
import discord
import asyncio
import utils


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.categories = [
            "Administratives",
            "Stämme Features",
            "Utilities",
            "Minigames"
        ]

    def packing(self, storage, package):
        pkg = [f"`{c}`" for c in package]
        storage.append(" ".join(pkg))
        package.clear()

    def help_embed(self):
        emb_help = discord.Embed(color=discord.Color.blue())
        emb_help.set_footer(text="Supportserver: https://discord.gg/s7YDfFW")

        groups = {name: [] for name in self.categories}
        for name, cog in self.bot.cogs.items():
            cog_type = getattr(cog, 'type', None)

            if cog_type is None:
                continue

            category = self.categories[cog_type]
            for cmd in cog.walk_app_commands():
                if isinstance(cmd, app_commands.Command):
                    if cmd.parent is not None:
                        cmd_name = f"{cmd.parent.name} {cmd.name}"
                    else:
                        cmd_name = cmd.name

                    groups[category].append(cmd_name)

        for name, cmd_list in groups.items():
            cache = []
            datapack = []
            sorted_list = utils.sort_list(cmd_list)

            for cmd in sorted_list:

                if len("".join(cache) + cmd) > 30 and len(cache) > 1:
                    self.packing(datapack, cache)

                cache.append(cmd)

                num = 4 if len(cmd) > 4 else 5
                if len(cache) >= num or len(cache) > 1 and "[" in cache[-2]:
                    self.packing(datapack, cache)

                if cmd == sorted_list[-1] and cache:
                    self.packing(datapack, cache)

                elif "[" in cmd and len(cache) == 2:
                    self.packing(datapack, cache)

            emb_help.add_field(name=f"{name}:", value="\n".join(datapack), inline=False)

        return emb_help

    def tip_embed(self, title, description):
        color = discord.Color.blue()
        embed = discord.Embed(title=title, description=description, color=color)
        return embed

    @app_commands.command(name="commands", description="Eine Lister aller Commands")
    async def commands(self, interaction):
        embed = self.help_embed()
        await interaction.response.send_message(embed=embed)

    help = app_commands.Group(name="help", description="xd")

    @help.command(name="points", description="Erklärung des points Arguments")
    async def points(self, interaction):
        msg = "Punkte können in folgendem Format angegeben werden:\n" \
              "<100 (die gewünschten Punkte müssen unter 100 sein)\n" \
              "=100 (die gewünschten Punkte müssen exakt 100 sein)\n" \
              "<100 (die gewünschten Punkte müssen über 100 sein)\n"
        embed = self.tip_embed("Erklärung des Argument: points", msg)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @help.command(name="state", description="All die unterstützten State Typen")
    async def state(self, interaction):
        msg = "Es gibt folgende States:\n" \
              "**bash** (Offensive Bahspoints)\n" \
              "**def** (Defensive Bahspoints)\n" \
              "**sup** (Unterstützungs Bashpoints)\n" \
              "**farm** (Erbeutete Rohstoffe)\n" \
              "**villages** (Geplünderte Dörfer)\n" \
              "**scavenge** (Raubzüge)\n" \
              "**conquer** (Eroberte Dörfer)"

        embed = self.tip_embed("Erklärung des Argument: state", msg)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @help.command(name="awards", description="All die unterstützten Awardtypen")
    async def awards(self, interaction):
        msg = "Es gibt folgende Awards:\n" \
              "**bash** (Offensive Bahspoints)\n" \
              "**def** (Defensive Bahspoints)\n" \
              "**sup** (Unterstützungs Bashpoints)\n" \
              "**farm** (Erbeutete Rohstoffe)\n" \
              "**villages** (Geplünderte Dörfer)\n" \
              "**scavenge** (Raubzüge)\n" \
              "**conquer** (Eroberte Dörfer)"

        embed = self.tip_embed("Erklärung des Argument: state", msg)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Help(bot))
