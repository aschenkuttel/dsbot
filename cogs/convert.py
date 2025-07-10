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
            return None

        # bugfix since inno serves webp files now which wkhtml doesn't support
        # since inno serves still pngs aswell we just replace the suffix
        content = str(tiles[1]).replace(".webp", ".png")
        main = f"{utils.whymtl}<head></head>{content}"
        css = f"{self.bot.data_path}/report.css"

        try:
            img_bytes = imgkit.from_string(main, False, options=utils.imgkit, css=css)
        except UnicodeDecodeError as err:
            img_bytes = err.args[1]

        # crops empty background
        im = Image.open(io.BytesIO(img_bytes)).convert('RGB')

        im.save(f"{self.bot.data_path}/report.png")

        bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
        diff = ImageChops.difference(im, bg)
        diff = ImageChops.add(diff, diff, 2.0, -10)
        im = im.crop(diff.getbbox())

        # crops border and saves to FileIO
        result = im.crop((2, 2, im.width - 2, im.height - 2))
        file = io.BytesIO()
        result.save(file, 'png')
        file.seek(0)
        return file

    async def report_to_img(self, content):
        try:
            async with self.bot.session.get(content) as res:
                data = await res.text()
        except (aiohttp.InvalidURL, ValueError):
            return None

        return await self.bot.execute(self.html_to_image, data)

    async def parse_coords(self, coords, server):
        found_villages = []

        villages = await self.bot.fetch_bulk(server, coords, 2, name=True)
        village_dict = {str(vil): vil for vil in villages}
        player_ids = [obj.player_id for obj in villages]
        players = await self.bot.fetch_bulk(server, player_ids, dictionary=True)

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

        return f"{existing}\n{remaining}"

    @app_commands.command(name="coords", description="Konvertiert eine oder mehrere Koordinaten in Hyperlinks")
    @app_commands.describe(coordinates="Eine oder mehrere Koordinaten die konvertiert werden sollen")
    async def coords(self, interaction, coordinates: utils.CoordinatesConverter):
        await interaction.response.defer()
        # set imitation workaround to preserve the order of coordinates
        coords = list(dict.fromkeys(str(c) for c in coordinates))  # noqa (due transformer)

        if not coords:
            embed = utils.error_embed(text="Keine gültige Koordinate gefunden")
            await interaction.response.send_message(embed=embed)
            return

        content = await self.parse_coords(coords, interaction.server)
        embed = discord.Embed(description=content)
        await interaction.followup.send(embed=embed)
        logger.debug("coord converted")

    @app_commands.command(name="report", description="Konvertiert einen Bericht Link in ein Bild")
    @app_commands.describe(report="Ein Link eines veröffentlichten Berichts")
    async def report(self, interaction, report: str):
        await interaction.response.defer()

        report_url = re.match(r'https://.+/public_report/[^\s\\]*', report)

        if report_url:
            io_file = await self.report_to_img(report_url.string)

            if io_file is not None:
                file = discord.File(io_file, "report.png")
                await interaction.followup.send(file=file)
                logger.debug("report converted")
                return

        else:
            embed = utils.error_embed("Invalid Report")
            await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Convert(bot))
