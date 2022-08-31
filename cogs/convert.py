from discord.ext import commands
from discord import app_commands
from bs4 import BeautifulSoup
from PIL import Image, ImageChops
import aiohttp
import discord
import logging
import imgkit
import utils
import io
import re

logger = logging.getLogger('dsbot')


class Convert(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Report HTML to Image Converter
    def html_to_image(self, raw_data):
        soup = BeautifulSoup(raw_data, 'html.parser')
        tiles = soup.body.find_all(class_='vis')

        if len(tiles) < 2:
            return

        main = f"{utils.whymtl}<head></head>{tiles[1]}"
        css = f"{self.bot.data_path}/report.css"
        img_bytes = imgkit.from_string(main, False, options=utils.imgkit, css=css)

        # crops empty background
        im = Image.open(io.BytesIO(img_bytes))
        bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
        diff = ImageChops.difference(im, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        im = im.crop(diff.getbbox())

        # crops border and saves to FileIO
        result = im.crop((2, 2, im.width - 2, im.height - 2))
        file = io.BytesIO()
        result.save(file, 'png')
        file.seek(0)
        return file

    async def fetch_report(self, content):
        try:
            async with self.bot.session.get(content) as res:
                data = await res.text()
        except (aiohttp.InvalidURL, ValueError):
            return

        file = await self.bot.execute(self.html_to_image, data)
        return file

    @app_commands.command(name="coords", description="Konvertiert eine oder mehrere Koordinaten in Hyperlinks")
    async def coords(self, interaction, coordinates: utils.CoordinatesConverter):
        # set imitation workaround to preserve order of coordinates
        coords = list(dict.fromkeys(str(c) for c in coordinates))  # noqa (due transformer)
        villages = await self.bot.fetch_bulk(interaction.server, coords, 2, name=True)
        village_dict = {str(vil): vil for vil in villages}

        player_ids = [obj.player_id for obj in villages]
        players = await self.bot.fetch_bulk(interaction.server, player_ids, dictionary=True)

        found_villages = []

        for coord in coords.copy():
            village = village_dict.get(coord)
            if village is None:
                continue

            player = players.get(village.player_id)

            if player:
                owner = f"[{player.name}]"
            else:
                owner = "[Barbarendorf]"

            found_villages.append(f"{village.mention} {owner}")
            coords.remove(village.coords)

        if existing := '\n'.join(found_villages):
            existing = f"**Gefundene Koordinaten:**\n{existing}"
        if remaining := ', '.join(coords):
            remaining = f"**Nicht gefunden:**\n{remaining}"

        embed = discord.Embed(description=f"{existing}\n{remaining}")
        await interaction.response.send_message(embed=embed)
        logger.debug("coord converted")

    @app_commands.command(name="report", description="Konvertiert einen Bericht Link in ein Bild")
    async def report(self, interaction, report: str):
        report_url = re.match(r'https://.+/public_report/\S*', report)
        if report_url:
            file = await self.fetch_report(report_url.string)

            if file is not None:
                await interaction.response.send_message(file=file)
                logger.debug("report converted")
                return

        embed = utils.error_embed("Invalid Report")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Convert(bot))
