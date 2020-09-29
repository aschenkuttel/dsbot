from discord.ext import commands
import discord
import asyncio
import utils


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = {}
        self.categories = ["Administratives", "Stämme Features",
                           "Utilities and Fun", "Minigames"]

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user == self.bot.user:
            return

        data = self.cache.get(reaction.message.id)
        if data is None:
            return

        if user.id in data['cache']:
            return

        if reaction.emoji == "📨":
            try:
                embed = data['embed']
                data['cache'].append(user.id)
                await user.send(embed=embed)
            except discord.Forbidden:
                pass

    async def mailbox(self, ctx, embed):
        response = await ctx.private_hint()
        if response:
            data = {'embed': embed, 'cache': [ctx.author.id]}
            self.cache[ctx.message.id] = data
            await asyncio.sleep(600)
            self.cache.pop(ctx.message.id)

    def packing(self, storage, package):
        pkg = [f"`{c}`" for c in package]
        storage.append(" ".join(pkg))
        package.clear()

    def help_embed(self, prefix):
        desc = "Erhalte eine ausführliche Erklärung zu\neinzelnen " \
               "Commands mit `{0}help <commandname>`".format(prefix)
        emb_help = discord.Embed(description=desc, color=discord.Color.blue())
        emb_help.set_footer(text="Supportserver: https://discord.gg/s7YDfFW")

        groups = {name: [] for name in self.categories}
        for name, cog in self.bot.cogs.items():
            cog_type = getattr(cog, 'type', None)

            if cog_type is None:
                continue

            category = self.categories[cog_type]
            for cmd in cog.get_commands():

                for alias in cmd.aliases:
                    if len(alias) < 3:
                        cmd_name = f"{alias} [{cmd}]"
                        break
                else:
                    cmd_name = str(cmd)

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

    def cmd_embed(self, data, ctx):
        titles = [f"`{ctx.prefix}{cmd}`" for cmd in data[0]]
        title = f"Command: {' - '.join(titles)}"

        raw_inp = [f"`{ctx.prefix}{cmd}`" for cmd in data[3]]
        cmd_inp = "\n".join(raw_inp)

        raw_example = [f"`{ctx.prefix}{cmd}`" for cmd in data[4]]
        example = "\n".join(raw_example)

        color = discord.Color.blue()
        parseable = f"**Beschreibung:**\n{data[1]}\n" \
                    f"**Command Typ:** {data[2]}\n" \
                    f"**Command Input:**\n {cmd_inp}\n" \
                    f"**Beispiel:**\n {example}"
        description = parseable.replace("~", ctx.prefix)
        emb = discord.Embed(title=title, description=description, color=color)
        return emb

    @commands.command(name="pin")
    @commands.has_permissions(administrator=True)
    async def pin_help_(self, ctx):
        embed = self.help_embed(ctx.prefix)
        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    async def help(self, ctx):
        if ctx.subcommand_passed:
            msg = "Der angegebene Command existiert nicht"
            embed = discord.Embed(color=discord.Color.red(), description=msg)
            embed.set_footer(text=f"Alle Commands unter {ctx.prefix}help")
            await ctx.send(embed=embed)
        else:
            embed = self.help_embed(ctx.prefix)
            await ctx.author.send(embed=embed)
            await self.mailbox(ctx, embed)

    # Administratives
    @help.command(name="set")
    async def set_(self, ctx):
        title = "`~set`"
        desc = "Legt die servergebundene oder channelgebundene Welt fest, " \
               "einen \"Game Channel\" welchen die meisten Game Commands benötigen, " \
               "einen Conquer Channel für stündliche Eroberungen oder einen neuen Prefix.\n" \
               "Mögliche Switches: `report, request, coord, mention`"
        cmd_type = "Admin Command"
        cmd_inp = ["~set world <world>",
                   "~set channel <world>",
                   "~set game",
                   "~set conquer",
                   "~set prefix <prefix>",
                   "~set switch <converter>"]
        example = ["~set world de172",
                   "~set channel de164",
                   "~set game",
                   "~set conquer",
                   "~set prefix -",
                   "~set switch mention"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="reset")
    async def reset_(self, ctx):
        title = "`~reset`"
        desc = "Setzt einen gewünschten Teil oder die gesamten Serverconfigs zurück"
        cmd_type = "Admin Command"
        cmd_inp = ["~reset <game|conquer|config>`"]
        example = ["~reset game",
                   "~reset conquer",
                   "~reset config"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="world")
    async def world_(self, ctx):
        title = "`~world`"
        desc = "Erhalte die Welt des Textchannels oder des Servers"
        cmd_type = "Admin Command"
        cmd_inp = ["~world"]
        example = ["~world"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="remove")
    async def remove_(self, ctx):
        title = "`~remove`"
        desc = "Entfernt eingstellte Serverconfigs / Gegensatz zu ~set"
        cmd_type = "Admin Command"
        cmd_inp = ["~remove channel",
                   "~remove game",
                   "~remove conquer",
                   "~remove prefix"]
        example = ["~remove channel",
                   "~remove game",
                   "~remove conquer",
                   "~remove prefix"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="switch")
    async def switch_(self, ctx):
        title = "`~switch`"
        desc = "Aktiviert oder Deaktiviert einen der 4 Konverter:\n" \
               "Koordinaten, Berichte, BB-Codes oder Unterstützungsanfrage"
        cmd_type = "Admin Command"
        cmd_inp = ["~switch <coord|request|mention|record>`",
                   "~switch list"]
        example = ["~switch coord",
                   "~switch request",
                   "~switch mention",
                   "~switch record",
                   "~switch list"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="worlds")
    async def worlds_(self, ctx):
        title = "`~worlds`"
        desc = "Erhalte alle momentan aktive Welten"
        cmd_type = "Admin Command"
        cmd_inp = ["~worlds"]
        example = ["~worlds"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="conquer")
    async def conquer_(self, ctx):
        title = "`~conquer`"
        desc = "Fügt dem Conquer-Filter einen Stamm hinzu oder entfernt ihn, " \
               "blendet zukünftig alle Barbarendörfer aus/ein, zeigt alle" \
               "Stämme im Filter an oder löscht diesen komplett"
        cmd_type = "Admin Command"
        cmd_inp = ["~conquer add <tribe>",
                   "~conquer remove <tribe>",
                   "~conquer grey",
                   "~conquer list",
                   "~conquer clear"]
        example = ["~conquer add 300",
                   "~conquer remove 300",
                   "~conquer grey",
                   "~conquer list",
                   "~conquer clear"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    # Stämme Features
    @help.command(name="map")
    async def map_(self, ctx):
        title = "`~map`"
        desc = "Erstellt eine Karte der Welt und markiert angegebene Stämme. " \
               "Falls keine angegeben werden erhält man eine Darstellung der Top 10. " \
               "Des weiteren können mit einem & Zeichen zwischen mehreren Stämmen diese " \
               "gruppiert und einheitlich angezeigt werden"
        cmd_type = "Server Command"
        cmd_inp = ["~map",
                   "~map <tribe> <tribe> <tribe>",
                   "~map <tribe> <tribe> & <tribe> <tribe>"]
        example = ["~map",
                   "~map <300> <W-Inc>",
                   "~map 300 W-Inc & SPARTA"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="top")
    async def top_(self, ctx):
        title = "`~top`"
        desc = "Erhalte die ewige Top 5 der jeweiligen \"An einem Tag\"-Rangliste."
        cmd_type = "Server Command"
        cmd_inp = ["~top <bash/def/ut/farm/villages/scavenge/conquer>"]
        example = ["~top bash"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="bash", aliases=["allbash", "attbash", "defbash", "supbash"])
    async def bash_(self, ctx):
        title = "`~bash` - `~allbash` - `~attbash` - `~defbash` - `~supbash`"
        desc = "Erhalte entweder eine Zusammenfassung eines Accounts, " \
               "Stammes oder vergleiche 2 Spieler/Stämme und deren Bashpoints"
        cmd_type = "Server Command"
        cmd_inp = ["~bash <playername/tribename>",
                   "~allbash <playername> / <playername>"]
        example = ["~bash lemme smash",
                   "~allbash gods rage / Knueppel-Kutte"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="nude")
    async def nude_(self, ctx):
        title = "`~nude`"
        desc = "Erhalte das Profilbild eines Spielers, Stammes. Falls " \
               "kein Name angegeben wird, wird ein Bild zufällig " \
               "von allen Spielern der Server-Welt ausgesucht."
        cmd_type = "Server Command"
        cmd_inp = ["~nude",
                   "~nude <playername/tribename>"]
        example = ["~nude",
                   "~nude Leedsi"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="daily", aliases=["aktueller"])
    async def daily_(self, ctx):
        title = "`~daily` - `~aktueller`"
        desc = "Erhalte die aktuelle Top 5 einiger \"des Tages\"-Ranglisten. " \
               "Bei Benutzung der deutschen Commandvariante `aktueller` erhält man " \
               "die gleichen Rangliste nur für Stämme. Die Daten sind aufgrund der " \
               "Limitierung von Inno nur stündlich aktualisiert und Ranglisten mit " \
               "Bashpoints zeigen nur den Unterschied und nicht die berrechneten " \
               "Punkte. Deshalb können letztendliche Ergebnisse auch abweichen und " \
               "sollen lediglich als Anhaltspunkt dienen."
        cmd_type = "Server Command"
        cmd_inp = ["~daily <angreifer/verteidiger/unterstützer>",
                   "~aktueller <kämpfer/eroberer/verlierer/>"]
        example = ["~daily eroberer",
                   "~aktueller angreifer"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="recap")
    async def recap_(self, ctx):
        title = "`~recap`"
        desc = "Der Bot fasst die Entwicklung des Spieler, Stammes der " \
               "vergangenen 7 oder gewünschten Tage zusammen. Falls keine " \
               "Tage angegeben werden, wählt der Bot automatisch eine Woche."
        cmd_type = "Server Command"
        cmd_inp = ["~recap <playername> <time>"]
        example = ["~recap madberg",
                   "~recap madberg 20"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="visit")
    async def visit_(self, ctx):
        title = "`~visit`"
        desc = "Erhalte den Gastlogin-Link einer Welt"
        cmd_type = "Server Command"
        cmd_inp = ["~visit <world>"]
        example = ["~visit de143"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="custom")
    async def custom_(self, ctx):
        title = "`~custom`"
        desc = "Erstellt eine Karte der channelverbundenen oder angegebenen Welt. " \
               "Die Emotes sind hierbei als \"Knöpfe\" zu betrachten, Optionen wie " \
               "Zoom und Markierung haben mehrere Stufen (5 Minuten Zeitlimit)"
        cmd_type = "Server Command"
        cmd_inp = ["~custom <world>"]
        example = ["~custom de172"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="player", aliases=["tribe"])
    async def player_(self, ctx):
        title = "`~player` - `~tribe`"
        desc = "Erhalte eine kleine Übersicht eines Accounts/Stamm mit 30-Tage-Graph"
        cmd_type = "Server Command"
        cmd_inp = ["~player <playername>",
                   "~tribe <tribename>"]
        example = ["~player Philson Cardoso",
                   "~tribe Milf!"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="retime")
    async def retime_(self, ctx):
        title = "`~retime`"
        desc = "Erhalte die Retime Zeit eines ankommenden Angriffs. " \
               "Hierbei kopiert man einfach die Zeile des Angriffs " \
               "und fügt sie dahinter ein. Die Laufzeit ist per default " \
               "Ramme, nimmt sonst den umbenannten Befehl, kann aber auch " \
               "manuell an erster Stelle eingetragen werden"
        cmd_type = "Server Command"
        cmd_inp = ["~retime <commandline>",
                   "~retime <runtime> <commandline>"]
        example = ["~retime <commandline>",
                   "~retime Ramme <commandline>"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)
    
    @help.command(name="members")
    async def members_(self, ctx):
        title = ["members"]
        desc = "Erhalte alle Member eines Stammes,\n" \
               "mögliche Optionen: `ingame, guest, twstats`"
        cmd_type = "Server Command"
        cmd_inp = ["members <tribetag>",
                   "members <tribetag> <url_type=ingame>"]
        example = ["members W-Inc",
                   "members W-Inc twstats"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="inactive", aliases=["graveyard"])
    async def inactive_(self, ctx):
        title = ["inactive", "graveyard"]
        desc = "Erhalte eine Coord-Liste aller inaktiven Accounts in einem gewissen Radius." \
               "Arguments werden hierbei als \"keywords\" angegeben. Der Radius kann zwischen " \
               "`1` und `25` Dörfern groß sein, die Punktegrenze kann über oder unter einem Wert " \
               "sein, hierbei verwendet man statt `=` entweder `>` oder `<`. Falls nach " \
               "inaktiven Spielern mit Stamm gesucht wird, kann man dies so angeben: tribe=true"
        cmd_type = "Server Command"
        cmd_inp = ["inactive <coord> <radius=10, points=none, since=3, tribe=none>"]
        example = ["inactive 500|500 radius=20 since=7",
                   "inactive 500|500 radius=5 points<500",
                   "inactive 500|500 tribe=true"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="villages")
    async def villages_(self, ctx):
        title = "`~villages`"
        desc = "Erhalte eine Coord-Liste eines Accounts oder Stammes. " \
               "Wenn gewünscht kann man auch einen Kontinent mit angegeben werden. " \
               "Ideal für das Faken mit Workbench."
        cmd_type = "Server Command"
        cmd_inp = ["~villages <amount> <playername/tribename> <continent>"]
        example = ["~villages 20 madberg",
                   "~villages all madberg k55"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="bb")
    async def bb_(self, ctx):
        title = "`~bb`"
        desc = "Erhalte alle Koordinaten in einem Radius um ein gewünschtes Dorf. Optionen " \
               "sind Radius(Default = 20, Maximum 100 in jede Richtung) " \
               "und Points(Punktezahl der Dörfer bis zur gewünschten Grenze)"
        cmd_type = "Server Command"
        cmd_inp = ["~bb <coord> <options>"]
        example = ["~bb 555|555",
                   "~bb 555|555 radius=50 points=100"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="rm")
    async def rm_(self, ctx):
        title = "`~rm`"
        desc = "Der Bot generiert automatisch eine Liste aller Member der " \
               "angegebenen Stämme damit man diese kopieren und einfügen " \
               "kann. Namen mit Leerzeichen müssen mit \"\" umrandet sein."
        cmd_type = "Server Command"
        cmd_inp = ["~rm <tribename> <tribename>"]
        example = ["~rm Skype! down \"Mum, I like to farm!\""]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="raubzug", aliases=["rz3", "rz4"])
    async def rz_(self, ctx):
        title = "`~rz3` - `~rz4`"
        desc = "Erhalte die beste Aufteilung für den Raubzug. " \
               "Verschiedene Truppentypen per Leerzeichen trennen."
        cmd_type = "Server Command [Creator: Madberg]"
        cmd_inp = ["~rz4 <unit-amount>"]
        example = ["~rz4 200 100"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="sl")
    async def sl_(self, ctx):
        title = "`~sl`"
        desc = "Erstellt beliebig viele \"Truppen einfügen\" SL-Scripte.\n" \
               "Truppen werden hierbei per Keyword angegeben(Truppe=Anzahl):\n" \
               "`Speer, Schwert, Axt, Bogen, Späher, Lkav, Berittene`\n" \
               "`Skav, Ramme, Katapult, Paladin, Ag`"
        cmd_type = "Server/PM Command"
        cmd_inp = ["~sl <troop>=<amount> <*coords>"]
        example = ["~sl speer=20 lkav=5 späher=2 550|490 489|361",
                   "~sl axt=80ramme=20ag=1 [coord]452|454[/coord]"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    # Utilities
    @help.command(name="avatar")
    async def avatar_(self, ctx):
        title = "`~avatar`"
        desc = "Gebe eine Image-Url an und erhalte das Bild auf DS Maße " \
               "(280x170) geschnitten. Bewegte Bilder werden unterstützt."
        cmd_type = "PM Command"
        cmd_inp = ["~avatar <url with (png, jpg, gif ending)>"]
        example = ["~avatar https://homepage/beispielbild.png"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="emoji")
    async def emoji_(self, ctx):
        title = "`~emoji`"
        desc = "Füge deinem Server eine Reihe von DS-Emojis hinzu."
        cmd_type = "Admin Command"
        cmd_inp = ["~emoji"]
        example = ["~emoji"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="poll")
    async def poll_(self, ctx):
        title = "`~poll`"
        desc = "Erstelle eine Abstimmung mit bis zu 9 Auswahlmöglichkeiten"
        cmd_type = "Server Command"
        cmd_inp = ["~poll \"<question>\" <option> <option> ..."]
        example = ["~poll \"Sollen wir das BND beenden?\" Ja Nein Vielleicht"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="pin")
    async def pin_(self, ctx):
        title = "`~pin`"
        desc = "Erhalte den Help Command im Server zum Anpinnen"
        cmd_type = "Admin Command"
        cmd_inp = ["~pin"]
        example = ["~pin"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="remind")
    async def remind_(self, ctx):
        title = "`~remind`"
        desc = "Der Bot erinnert dich nach Ablauf der Zeit per Nachricht, " \
               "ein Grund is Optional. Der Bot richtet sich bei Zeiteingaben an " \
               "MEZ/MESZ (Deutschland), mit \"now\" könnt ihr die aktuelle Zeit abfragen " \
               "falls ihr im Ausland seid. Lass dir all deine aktiven Reminder anzeigen, " \
               "lösche einen einzelnen oder alle."
        cmd_type = "PM Command"
        cmd_inp = ["~remind <time> <neuer Absatz> <reason>",
                   "~remind list",
                   "~remind remove <reminder id>",
                   "~remind clear",
                   "~now"]
        example = ["~remind 50s",
                   "~remind 18:22\nPizza aus dem Ofen holen",
                   "~remind list",
                   "~remind remove 120",
                   "~remind clear",
                   "~now`"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="duali")
    async def duali_(self, ctx):
        title = "`~duali`"
        desc = "Der Bot sieht vorraus wie gut du und der angegebene " \
               "User in einem Account zusammenspielen würdet."
        cmd_type = "Server Command"
        cmd_inp = ["~duali <discord username>"]
        example = ["~duali Neel x Kutte"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="mirror")
    async def mirror_(self, ctx):
        title = "`~mirror`"
        desc = "Der Bot zeigt dir den aktuellen Discord Avatar eines Users." \
               "Falls keiner angegeben ist, wird dir dein Eigener gezeigt"
        cmd_type = "Server Command"
        cmd_inp = ["~mirror",
                   "~mirror <discord username>"]
        example = ["~mirror",
                   "~mirror mettberg"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="orakel")
    async def orakel_(self, ctx):
        title = "`~orakel`"
        desc = "Frag den Bot eine Ja/Nein Frage und er beantwortet sie dir. " \
               "Schrei ihn aber bitte nicht an."
        cmd_type = "Server Command"
        cmd_inp = ["~orakel <question>"]
        example = ["~orakel Werde ich bald geadelt?"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    # Minigames
    @help.command(name="anagram", aliases=["ag"])
    async def anagram_(self, ctx):
        title = "`~ag` - `~anagram`"
        desc = "Spiele eine Runde Anagram mit Worten aus DS."
        cmd_type = "Server Command"
        cmd_inp = ["~ag",
                   "<your guess>"]
        example = ["~ag",
                   "Späher"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="tribalcards", aliases=["tc"])
    async def tribalcards_(self, ctx):
        title = "`~tribalcards` - `~tc` - `~play`"
        desc = "Spiel eine Runde Tribalcards. Gespielt wird mit zufälligen " \
               "Accounts der Serverwelt. Der Spielgründer darf anfangen und " \
               "muss nun eine Eigenschaft auswählen gegen welche die anderen " \
               "Spieler vergleichen müssen. Der Gewinner beginnt von da an. " \
               "Das Spiel geht solange bis keine Karten mehr übrig sind."
        cmd_type = "Server Command / PM Command"
        cmd_inp = ["~quartet",
                   "~play <card or stat>"]
        example = ["~quartet",
                   "~play 5",
                   "~play off"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="hangman")
    async def hangman_(self, ctx):
        title = "`~hangman`"
        desc = "Spiele eine Runde Galgenmännchen. Alle Worte " \
               "kommen bis auf ein paar Ausnahmen in DS vor."
        cmd_type = "Server Command"
        cmd_inp = ["~hangman",
                   "~guess <character or solution>"]
        example = ["~hangman",
                   "~guess a",
                   "~guess Späher"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="slots")
    async def slots_(self, ctx):
        title = "`~slots`"
        desc = "Ziehe eine zufällige Zahl zwischen 10000-99999, bei gleicher Gewinnzahl " \
               "erhältst du den globalen Pot, Einsatz automatisch 1000 Eisen"
        cmd_type = "Server Command"
        cmd_inp = ["~slots"]
        example = ["~slots"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="quiz")
    async def quiz_(self, ctx):
        title = "`~quiz`"
        desc = "Ein ds-bezogenes Quiz mit 4 unterschiedlichen Modulen."
        cmd_type = "Server Command"
        cmd_inp = ["~quiz <game_rounds>"]
        example = ["~quiz 10"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="blackjack", aliases=["bj"])
    async def blackjack_(self, ctx):
        title = "`~blackjack` - `~bj`"
        desc = "Spiele eine Runde Blackjack und wähle eine der drei Möglichkeiten:\n" \
               "h[hit = noch eine Karte], s[stand = keine Karte mehr] oder\n" \
               "d[double = noch eine Karte, verdoppelter Einsatz und der Dealer ist am Zug]\n" \
               "Diese kannst du ohne Command in den Chat schreiben"
        cmd_type = "Server Command"
        cmd_inp = ["~bj <optional=amount(100-50000)>"]
        example = ["~bj 50000"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="videopoker", aliases=["vp", "draw"])
    async def vp_(self, ctx):
        title = "`~videopoker` - `~vp` - `~draw`"
        desc = "Du erhältst 5 Karten aus einem typischen 52er Set. Nun hast " \
               "du die Möglichkeit einmal Karten auszutauschen. " \
               "Man spielt um einen gewünschten Einsatz, " \
               "je nach Hand erhält man immer größeren Gewinn."
        cmd_type = "Server Command"
        cmd_inp = ["~vp <optional=amount(100-2000)>",
                   "~draw <cardnumbers>"]
        example = ["~vp 2000",
                   "~draw 13"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="dice")
    async def dice_(self, ctx):
        title = "`~dice` - `~würfelspiel`"
        desc = "Starte ein 1vs1 Würfelspiel, das größere Auge gewinnt beide Einsätze"
        cmd_type = "Server Command"
        cmd_inp = ["~dice <amount (1000-500000) or accept>"]
        example = ["~dice 50000",
                   "~dice accept"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)

    @help.command(name="iron")
    async def iron_(self, ctx):
        title = "`~iron` - `~eisen`"
        desc = "Beim Gewinnen von Spielen (ag, hangman und vp) gewinnt man " \
               "Eisen. Man kann sich seinen Speicher anzeigen lassen, die " \
               "aktuelle Top 5 des Servers oder die globale Top 5 aller " \
               "User auf allen Servern auf dem der Bot ist. " \
               "Man kann auch anderen Spielern Eisen übertragen."
        cmd_type = "Server Command"
        cmd_inp = ["~iron",
                   "~iron top",
                   "~iron global",
                   "~iron send <amount> <discord username>"]
        example = ["~iron",
                   "~iron top",
                   "~iron global",
                   "~iron send 8000 Sheldon"]
        data = title, desc, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await ctx.author.send(embed=embed)
        await self.mailbox(ctx, embed)


def setup(bot):
    bot.add_cog(Help(bot))
