from discord.ext import commands
from discord import app_commands
from discord.ui import View
from datetime import datetime
import discord
import utils
import re
import io


class MemberMenue:
    def __init__(self, interaction, tribe, pages):
        self.interaction = interaction
        self.tribe = tribe
        self.pages = pages
        self.view = View()

        placeholder = "{}"
        self.base = f"Member von {self.tribe.tag} ({placeholder}/{len(self.pages)})"
        self.embed = discord.Embed(title=self.base.format(1), url=self.tribe.expected_url)
        self.embed.description = "\n".join(self.pages[0])

        self.emojis = []
        self.current_index = 0

    async def setup(self):
        self.add_buttons()
        await self.interaction.response.send_message(embed=self.embed, view=self.view)

    def add_buttons(self):
        numbers = []
        for num in range(1, len(self.pages) + 1):
            button = f"{num}\N{COMBINING ENCLOSING KEYCAP}"
            numbers.append(button)

        self.emojis = ["⏪", *numbers, "⏩"]

        for index, emoji in enumerate(self.emojis):
            button = utils.DSButton(
                custom_id=str(index),
                emoji=emoji,
                row=0 if index < 4 else 1,
                _callback=self.update,
                disabled=True if index == 1 else False
            )

            self.view.add_item(button)

    async def update(self, raw_index, interaction):
        index = int(raw_index)

        if index - 1 == self.current_index:
            return

        last_index = len(self.pages) - 1

        if index in [0, len(self.emojis) - 1]:
            direction = -1 if index == 0 else 1
            self.current_index += direction

            if self.current_index < 0:
                self.current_index = last_index

            elif self.current_index > last_index:
                self.current_index = 0

        else:
            # ignoring the first emoji
            self.current_index = index - 1

        self.embed.title = self.base.format(self.current_index + 1)
        page = self.pages[self.current_index]
        self.embed.description = "\n".join(page)

        for child in self.view.children:
            # custom_id due linter error xd
            if int(getattr(child, 'custom_id')) == self.current_index + 1:
                child.disabled = True
            else:
                child.disabled = False

        await interaction.response.edit_message(embed=self.embed, view=self.view)


class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.type = 1
        self.base = "javascript: var settings = Array" \
                    "({0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}, {9}," \
                    " {10}, {11}, {12}, {13}, 'attack'); $.getScript" \
                    "('https://media.innogamescdn.com/com_DS_DE/" \
                    "scripts/qb_main/scriptgenerator.js'); void(0);"
        self.units = {'speer': "spear",
                      'schwert': "sword",
                      'axt': "axe",
                      'bogen': "archer",
                      'späher': "spy",
                      'lkav': "light",
                      'berittene': "marcher",
                      'skav': "heavy",
                      'ramme': "ram",
                      'katapult': "catapult",
                      'paladin': "knight",
                      'ag': "snob"}

        self.same_scavenge_2 = (0.714285, 0.285714)
        self.same_scavenge_3 = (0.625, 0.25, 0.125)
        self.same_scavenge_4 = (0.5765, 0.231, 0.1155, 0.077)
        self.best_scavenge_4 = (0.223, 0.244, 0.261, 0.272)
        # (((factor * loot) ** 2 * 100) ** 0.45 + 1800) * 0.8845033719

    # temporary fix
    async def fetch_oldest_tableday(self, conn):
        query = 'SELECT table_name FROM information_schema.tables ' \
                'WHERE table_schema=\'public\' AND table_type=\'BASE TABLE\' ' \
                'AND table_name LIKE \'player%\''

        cache = await conn.fetch(query)
        tables = " ".join([rec['table_name'] for rec in cache])
        numbers = [int(n) for n in re.findall(r'\d+', tables)]
        return sorted(numbers)[-1]

    @app_commands.command(name="members", description="Alle Mitglieder eines Stammes")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.guild.id)
    async def members(self, interaction, tribe: utils.DSConverter('tribe'), url_type: str = "ingame"):
        if url_type not in ("ingame", "guest", "twstats"):
            msg = "Der angegebene Url Typ ist nicht vorhanden:\n" \
                  "`(ingame[default], guest, twstats)`"
            await interaction.response.send_message(msg)
            return

        members = await self.bot.fetch_tribe_member(interaction.server, tribe.id)
        sorted_members = sorted(members, key=lambda obj: obj.rank)

        if not sorted_members:
            msg = "Der angegebene Stamm hat keine Mitglieder"
            await interaction.response.send_message(msg)
            return

        tribe.expected_url = getattr(tribe, f"{url_type}_url")

        if url_type == "ingame":
            url_type = "mention"
        else:
            url_type += "_mention"

        pages = [[]]
        for index, member in enumerate(sorted_members, 1):
            number = f"0{index}" if index < 10 else index
            line = f"`{number}` | {getattr(member, url_type)}"

            if len(pages[-1]) == 15:
                pages.append([line])
            else:
                pages[-1].append(line)

        pager = MemberMenue(interaction, tribe, pages)
        await pager.setup()

    @app_commands.command(name="rm", description="Alle Mitglieder mehrerer Stämme für das Schreiben einer Rundmail")
    async def rundmail_(self, interaction, tribes: str):
        await interaction.response.defer()
        tribes = tribes.split(" ")

        if len(tribes) > 10:
            msg = "Nur bis zu `10 Stämme` aufgrund der maximalen Zeichenlänge"
            await interaction.followup.send(msg)
            return

        data = await self.bot.fetch_tribe_member(interaction.server, tribes, name=True)
        if not data:
            await interaction.followup.send("Die angegebenen Stämme haben keine Mitglieder")

        else:
            result = [obj.name for obj in data]
            msg = f"```{';'.join(result)}```"
            await interaction.followup.send(msg, ephemeral=True)

    @app_commands.command(name="nude", description="Ein zufälliges Profilbild oder das eines Spielers/Stammes")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.guild_id)
    async def nude_(self, interaction, dsobj: utils.DSConverter = None):
        if dsobj is None:
            players = await self.bot.fetch_random(interaction.server, amount=30, max=True)
        else:
            players = [dsobj]

        for player in players:
            result = await self.bot.fetch_profile_picture(player, bool(dsobj))

            if result is not None:
                break

        else:
            if dsobj:
                msg = f"Glaub mir, die Nudes von `{dsobj.name}` willst du nicht!"
            else:
                msg = "Die maximale Anzahl von Versuchen wurden erreicht"

            await interaction.response.send_message(msg)
            return

        async with self.bot.session.get(result) as res2:
            image = io.BytesIO(await res2.read())
            file = discord.File(image, "userpic.gif")
            await interaction.response.send_message(file=file)

    @app_commands.command(name="visit", description="Gastzugang Url für eine gewünschte Welt oder die des Channels")
    async def visit(self, interaction, world: utils.WorldConverter = None):
        if world is None:
            world = interaction.world

        description = f"[{world.represent(True)}]({world.guest_url})"
        await interaction.response.send_message(embed=discord.Embed(description=description))

    @app_commands.command(name="sl", description="Konvertiert Truppen in eine SL Truppen Einfüge Vorlage")
    @app_commands.describe(troops="Mehrere Einheiten in Form von Einheit=Anzahl",
                           coordinates="Mehrere Koordinaten für Dörfer")
    async def sl(self, interaction, troops: str, coordinates: str):
        troops = re.findall(r'[A-z]*=\d*', troops)
        coordinates = re.findall(r'\d\d\d\|\d\d\d', coordinates)

        if not troops or not coordinates:
            msg = f"Du musst mindestens eine Truppe und ein Dorf angeben"
            await interaction.response.send_message(msg, ephemeral=True)
            return

        wiki = list(self.units)
        data = [0 for _ in range(12)]
        for kwarg in troops:
            name, amount = kwarg.split("=")
            try:
                index = wiki.index(name.lower())
                data[index] = int(amount)
            except ValueError:
                continue

        if not sum(data):
            troops = ", ".join([o.capitalize() for o in wiki])
            msg = f"Du musst einen gültigen Truppennamen angeben:\n`{troops}`"
            await interaction.response.send_message(msg)
            return

        result = []
        counter = 0
        package = []
        iteratable = set(coordinates)
        for index, coord in enumerate(iteratable):
            x, y = coord.split("|")
            script = self.base.format(*data, x, y)

            if counter + len(script) > 2000 or index == len(iteratable) - 1:
                result.append(package)
            else:
                package.append(script)
                counter += len(script)

        for package in result:
            msg = "\n".join(package)
            await interaction.response.send_message(f"```js\n{msg}\n```", ephemeral=True)

    @app_commands.command(name="rz", description="Beste Raubzug Aufteilung für Stufe 4")
    async def rz(self, interaction, units: str):
        await self.scavenge(interaction, units, best=True)

    @app_commands.command(name="rz2", description="Gleiche Raubzug Aufteilung für Stufe 2")
    async def rz2(self, interaction, units: str):
        await self.scavenge(interaction, units, 2)

    @app_commands.command(name="rz3", description="Gleiche Raubzug Aufteilung für Stufe 3")
    async def rz3(self, interaction, units: str):
        await self.scavenge(interaction, units, 3)

    @app_commands.command(name="rz4", description="Gleiche Raubzug Aufteilung für Stufe 4")
    async def rz4(self, interaction, units: str):
        await self.scavenge(interaction, units)

    async def scavenge(self, interaction, raw_units, factor=4, best=False):
        if best is True:
            factors = getattr(self, "best_scavenge_4")
        else:
            factors = getattr(self, f"same_scavenge_{factor}")

        scavenge_batches = ([], [], [], [])

        try:
            raw_unit_list = raw_units.split(" ")
            units = [int(unit) for unit in raw_unit_list]
        except ValueError:
            raise commands.ArgumentParsingError()

        for troop_amount in units[:10]:
            for index, appendix in enumerate(factors):
                troops = str(round(appendix * troop_amount))
                scavenge_batches[index].append(troops)

        result = []
        for index, troops in enumerate(scavenge_batches, start=1):
            if troops:
                troop_str = ", ".join(troops)
                result.append(f"`Raubzug {index}:` **[{troop_str}]**")

        embed = discord.Embed(description="\n".join(result))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="settings", description="Einstellungen einer gewünschten Welt oder der des Channels")
    async def settings_(self, interaction, world: utils.WorldConverter = None):
        world = world or interaction.world
        title = f"Settings der {world.represent(clean=True)} {world.icon}"
        embed = discord.Embed(title=title, url=world.settings_url)

        cache = []
        for key, data in interaction.lang.settings.items():
            parent, title, description = data.values()
            value = None
            if "|" in key:
                keys = key.split("|")[::-1]
                raw_value = [f"{world.config[parent][k]}:00" for k in keys]
                value = description.format(*raw_value)
            elif parent:
                raw_value = world.config[parent][key]
                if key == "fake_limit":
                    index = 1 if int(raw_value) else 0
                    value = description[index].format(raw_value)
                elif description:
                    try:
                        value = description[int(raw_value)]
                    except IndexError:
                        pass

            else:
                raw_value = getattr(world, key, None)
                if str(raw_value)[-1] == "0":
                    value = int(raw_value)
                elif key == "moral":
                    value = description[int(raw_value)]
                else:
                    value = round(float(raw_value), 3)

            cache.append(f"**{title}:** {value or raw_value}")

        embed.description = "\n".join(cache)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Utils(bot))
