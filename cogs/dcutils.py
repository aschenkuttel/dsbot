from discord.ext import commands
from discord import app_commands
from utils import MemberConverter
import discord
import random
import os


class DCUtils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.type = 2
        self.poll_time = 10
        self.url = "http://media1.tenor.com/images/561e3f9a9c6c" \
                   "1912e2edc4c1055ff13e/tenor.gif?itemid=9601551"
        self.emojis = {}
        self.setup_emojis()

    def setup_emojis(self):
        path = f"{self.bot.data_path}/emojis"
        for folder in os.listdir(path):
            new_path = f"{path}/{folder}"
            for file in os.listdir(new_path):
                with open(f"{new_path}/{file}", 'rb') as pic:
                    img = bytearray(pic.read())
                    name = file.split(".")[0]
                    self.emojis[name] = img

    @app_commands.command(name="oracle", description="Erhalte eine Antwort vom Bot auf eine Frage")
    @app_commands.describe(question="Eine Frage die mit Ja oder Nein beantwortet werden kann")
    async def orakel(self, interaction, question: str):
        await interaction.response.defer()

        # checks for both since numbers would
        # count as auppercase as well
        if question == question.upper() and not question == question.lower():
            answer = random.choice(interaction.lang.oracle['scared'])
        else:
            answer = random.choice(interaction.lang.oracle['normal'])

        msg = f"{interaction.user.display_name} fragt: {question}\n\n{answer}"
        await interaction.followup.send(msg)

    @app_commands.command(name="duali", description="Schau wie kompatibel du mit einem anderen Discord Member bist")
    async def duali(self, interaction, member: MemberConverter):
        if member == self.bot.user:
            embed = discord.Embed()
            embed.set_image(url=self.url)
            msg = "Das ist echt cute... aber ich regel solo."
            await interaction.response.send_message(msg, embed=embed)

        elif member == interaction.user:
            yt = "https://www.youtube.com/watch?v=fZcZvlcNyOk"
            embed = discord.Embed(title="0% - Sorry", url=yt)
            await interaction.response.send_message(embed=embed)

        else:
            points = 0
            for idc in (interaction.user.id, member.id):
                num = int(str(idc)[-3:-1])
                number = num + sum(int(n) for n in str(idc))
                points += number

            result = points % 101
            index = 9 if result >= 90 else int(result / 10)
            answer = interaction.lang.duali[index]
            msg = f"Ihr passt zu `{result}%` zusammen.\n{answer}"
            await interaction.response.send_message(msg)

    @app_commands.command(name="info", description="Diverse Informationen über den Bot")
    async def info(self, interaction):
        result = [f"Aktuell in `{len(self.bot.guilds)}` Servern!"]

        data = await self.bot.fetch_usage(amount=10)

        if data:
            result.append("**Die 10 meist benutzen Commands:**")

        for cmd, usage in data:
            result.append(f"`{usage}` **|** {cmd}")

        embed = discord.Embed()
        embed.description = "\n".join(result)
        embed.set_footer(text="Supportserver: https://discord.gg/s7YDfFW")
        name = "dsBot | Einladungslink"
        url = "https://discord.com/api/oauth2/authorize?client_id=344191195981021185&scope=applications.commands"
        embed.set_author(icon_url=self.bot.user.display_avatar.url, name=name, url=url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="emoji", description="Fügt dem Server eine Reihe an DS Emojis hinzu")
    @app_commands.checks.bot_has_permissions(manage_emojis=True)
    async def emoji(self, interaction):
        await interaction.response.defer()

        counter = 0
        for name, emoji in self.emojis.items():
            if name in [e.name for e in interaction.guild.emojis]:
                continue

            await interaction.guild.create_custom_emoji(name=name, image=emoji)
            counter += 1

        msg = f"`{counter}/{len(self.emojis)}` Emojis wurden hinzugefügt"
        await interaction.followup.send(msg)


async def setup(bot):
    await bot.add_cog(DCUtils(bot))
