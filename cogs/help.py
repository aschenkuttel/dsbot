import asyncio
from discord.ext import commands
import discord

cmds = [
    "`akte` | Twstats-URL von Spieler/Stamm",
    "`avatar` | Konvertiert Bild auf vorgeschriebene DS-Maße",
    "`bash` | Zusammenfassung der Bashpoints von Spieler/Stamm",
    "`conquer` | Administrator-Commands für den Conquer Channel",
    "`daily` | Top 5 der \"An einem Tag\"-Ranglisten",
    "`emoji` | Fügt dem Server eine Reihe von DS-Emojis hinzu",
    "`nude` | Profilbild von Spieler/Stamm oder zufällig",
    "`pin` | Help Embed für den Server"
    "`player` | Ingame-URL von Spieler/Stamm",
    "`recap` | Kurze Zusammenfassung der letzten Tage eines Spielers/Stammes",
    "`rm` | Rundmail Generator für mehrere Stämme",
    "`rz` | Ungefähre Verteilung der Truppen auf die Raubzugoptionen",
    "`set` | Administrator-Commands für Einstellungen",
    "`sl` | Generiert Truppen-Einfügen SL Script für angegebene Dörfer",
    "`time` | Erinnerung zu gewünschter Uhrzeit per PN",
    "`villages` | Liste von Koordinaten von Spieler/Stamm",
    "`visit` | Gastlogin-Url von gewünschter/Server-Welt",
]

fun = [
    "`ag` | Anagram Rätsel im DS-Format",
    "`duali` | Dualikompatibilät mit User",
    "`hangman` | Galgenmännchen im DS-Format",
    "`mirror` | Avatar eines Users/den Eigenen",
    "`orakel` | Zufällige Antwort auf eine Ja/Nein Frage",
    "`quiz` | Quiz mit weltenbezogenen und allgemeinen Fragen",
    "`quartet` | Quartet mit Accounts der Server-Welt",
    "`iron` | Commands für Statistiken und Senden von Eisen",
    "`vp` | Videopoker im IRC-Stil"
]


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def help_embed(self, prefix):
        desc = "Erhalte eine ausführliche Erklärung zu einzelnen Commands\nmit " \
               "`{0}help <command>` | Beispiel: `{0}help villages`".format(prefix)
        emb_help = discord.Embed(description=desc, color=discord.Color.blue())
        emb_help.add_field(name="DS-Commands:", value="\n".join(cmds))
        emb_help.add_field(name="Fun-Commands:", value="\n".join(fun))
        return emb_help

    async def cmd_embed(self, data, ctx):
        data = [obj.replace("~", ctx.prefix) for obj in data]
        title = f"Command: {data[0]}"
        desc = f"**Beschreibung:** {data[1]}\n**Command Typ:** {data[2]}\n" \
               f"**Command Input:**\n{data[3]}\n**Beispiel:**\n{data[4]}"
        emb = discord.Embed(title=title, description=desc, color=discord.Color.blue())
        return emb

    async def send_help(self, ctx):
        try:
            if ctx.guild:
                await ctx.message.add_reaction("📨")
            await asyncio.sleep(5)
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound):
            return

    @commands.command(name="pin")
    @commands.has_permissions(administrator=True)
    async def pin_(self, ctx):
        embed = self.help_embed(ctx.prefix)
        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    async def help(self, ctx):
        if ctx.subcommand_passed:
            msg = "Der angegebene Command existiert nicht"
            embed = discord.Embed(color=discord.Color.red(), description=msg)
            await ctx.send(embed=embed)
        else:
            embed = self.help_embed(ctx.prefix)
            await ctx.author.send(embed=embed)
            await self.send_help(ctx)

    # DS Commands

    @help.command(name="akte")
    async def akte_(self, ctx):
        title = "`~akte` - `~twstats`"
        desc = "Erhalte die Twstats Akte eines Spielers oder Stammes."
        cmd_type = "Server Command"
        cmd_inp = "`~akte <playername/tribename>`"
        example = "`~akte madberg`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="avatar")
    async def avatar_(self, ctx):
        title = "`~avatar` - `~profilbild`"
        desc = "Gebe eine Image-Url an und erhalte das Bild auf DS Maße " \
               "(280x170) geschnitten. Bewegte Bilder werden unterstützt."
        cmd_type = "Private Message Command"
        cmd_inp = "`~avatar <url with (png, jpg, gif ending)>`"
        example = "`~avatar https://homepage/beispielbild.png`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="bash")
    async def bash_(self, ctx):
        title = "`~bash` - `~allbash` - `~attbash` - `~defbash` - `~utbash`"
        desc = "Erhalte entweder eine Zusammenfassung eines Accounts, St" \
               "ammes oder vergleiche 2 Spieler/Stämme und deren Bashpoints."
        cmd_type = "Server Command"
        cmd_inp = "`~bash <playername/tribename>`\n" \
                  "`~allbash <playername> / <playername>`"
        example = "`~bash lemme smash`\n`~allbash gods rage / Knueppel-Kutte`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="conquer")
    async def conquer_(self, ctx):
        title = "`~conquer`"
        desc = "Fügt dem Conquer-Filter einen Stamm hinzu oder entfernt ihn, " \
               "blendet zukünftig alle Barbarendörfer aus/ein, zeigt alle" \
               "Stämme im Filter an oder löscht diesen komplett"
        cmd_type = "Admin Server Command"
        cmd_inp = "`~conquer add <tribe>`\n`~conquer remove <tribe>`\n" \
                  "`~conquer grey`\n`~conquer list`\n`~conquer clear`"
        example = "`~conquer add 300`\n`~conquer remove 300`\n" \
                  "`~conquer grey`\n`~conquer list`\n`~conquer clear`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="daily")
    async def daily_(self, ctx):
        title = "`~daily` - `~top`"
        desc = "Erhalte die aktuelle Top 5 der jeweiligen \"An einem Tag\"-Rangliste."
        cmd_type = "Server Command"
        cmd_inp = "`~daily <bash/def/ut/farm/villages/scavenge/conquer>`"
        example = "`~daily bash`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="emoji")
    async def emoji_(self, ctx):
        title = "`~emoji` - `~cancer`"
        desc = "Füge deinem Server eine Reihe von DS-Emojis hinzu."
        cmd_type = "Server Command"
        cmd_inp = "`~emoji`"
        example = "`~emoji`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="nude")
    async def nude_(self, ctx):
        title = "`~nude` - `~nacktbild`"
        desc = "Erhalte das Profilbild eines Spielers, Stammes. Falls " \
               "kein Name angegeben wird, wird ein Bild zufällig " \
               "von allen Spielern der Server-Welt ausgesucht."
        cmd_type = "Server Command"
        cmd_inp = "`~nude`\n`~nude <playername/tribename>`"
        example = "`~nude`\n`~nude Leedsi`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="pin")
    async def pin_(self, ctx):
        title = "`~pin`"
        desc = "Erhalte den Help Command im Server zum Anpinnen"
        cmd_type = "Server Admin Command"
        cmd_inp = "`~pin`"
        example = "`~pin`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="player")
    async def player_(self, ctx):
        title = "`~player` - `~spieler` - `~tribe` - `~stamm`"
        desc = "Erhalte den Gastlogin-Link eines Spieler oder Stammes."
        cmd_type = "Server/PM Command"
        cmd_inp = "`~player <playername>`\n`~tribe <tribename>`"
        example = "`~player Philson Cardoso`\n`~tribe Milf!`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="recap")
    async def recap_(self, ctx):
        title = "`~recap` - `~tagebuch`"
        desc = "Der Bot fasst die Entwicklung des Spieler, Stammes der " \
               "vergangenen 7 oder gewünschten Tage zusammen. Falls keine " \
               "Tage angegeben werden, wählt der Bot automatisch eine Woche."
        cmd_type = "Server/PM Command"
        cmd_inp = "`~recap <playername> <time>`"
        example = "`~recap madberg`\n`~recap madberg 20`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="rm")
    async def rm_(self, ctx):
        title = "`~rm` - `~rundmail`"
        desc = "Der Bot generiert automatisch eine Liste aller Member der " \
               "angegebenen Stämme damit man diese kopieren und einfügen " \
               "kann. Namen mit Leerzeichen müssen mit \"\" umrandet sein."
        cmd_type = "Server Command"
        cmd_inp = "`~rm <tribename> <tribename>`"
        example = "`~rm Skype! down \"Mum, I like to farm!\"`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="rz")
    async def rz_(self, ctx):
        title = "`~rz3` - `~rz4`"
        desc = "Erhalte die beste Aufteilung für den Raubzug. " \
               "Verschiedene Truppentypen per Leerzeichen trennen."
        cmd_type = "Server Command [Creator: Madberg]"
        cmd_inp = "`~rz4 <unit-amount>`"
        example = "`~rz4 200 100`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="set")
    async def set_(self, ctx):
        title = "`~set`"
        desc = "Legt die servergebundene oder channelgebundene Welt fest, " \
               "einen \"Game Channel\" welchen die meisten Game Commands benötigen, " \
               "einen Conquer Channel für stündliche Eroberungen oder einen neuen Prefix"
        cmd_type = "Admin Server Command"
        cmd_inp = "`~set <world>`\n`~set channel <world>`\n`~set game`\n" \
                  "`~set conquer`\n`~set prefix <prefix>`"
        example = "`~set world 117`\n`~set channel 164`\n`~set game`\n" \
                  "`~set conquer`\n`~set prefix -`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="sl")
    async def sl_(self, ctx):
        title = "`~sl`"
        desc = "Erstellt beliebig viele \"Truppen einfügen\" SL-Scripte.\nTruppen werden " \
               "hierbei per Keyword angegeben(Truppe=Anzahl):\n`Speer, Schwert, Axt, Bogen, " \
               "Späher, Lkav, Berittene`\n`Skav, Ramme, Katapult, Paladin, Ag`"
        cmd_type = "Server/PM Command"
        cmd_inp = "`~sl <troop>=<amount> <*coords>`"
        example = "`~sl speer=20 lkav=5 späher=2 550|490 489|361`\n" \
                  "`~sl axt=80ramme=20ag=1 [coord]452|454[/coord]`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="remove")
    async def remove_(self, ctx):
        title = "`~remove`"
        desc = "Entfernt eingstellte Serverconfigs / Gegensatz zu ~set"
        cmd_type = "Admin Server Command"
        cmd_inp = "`~remove channel`\n`~remove game`\n" \
                  "`~remove conquer`\n`~remove prefix`"
        example = "`~remove channel`\n`~remove game`\n" \
                  "`~remove conquer`\n`~remove prefix`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="time")
    async def time_(self, ctx):
        title = "`~time`"
        desc = "Der Bot erinnert dich nach Ablauf der Zeit per privater " \
               "Nachricht. Ein Grund kann, muss aber nicht angegeben " \
               "werden. Folgende Zeitformate sind möglich: " \
               "<5h2m10s> h=hour, m=minute, s=seconds | <12:30:27>"
        cmd_type = "Private Message Command"
        cmd_inp = "`~time <time> <reason>`"
        example = "`~time 50s`\n`~time 18:22 Pizza aus dem Ofen holen`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="villages")
    async def villages_(self, ctx):
        title = "`~villages` - `~dörfer`"
        desc = "Erhalte eine Coord-Liste eines Accounts oder Stammes. " \
               "Wenn gewünscht kann man auch einen Kontinent mit angegeben werden. " \
               "Ideal für das Faken mit Workbench."
        cmd_type = "Server Command"
        cmd_inp = "`~villages <amount> <playername/tribename> <continent>`"
        example = "`~villages 20 madberg`\n`~villages all madberg k55`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="visit")
    async def visit_(self, ctx):
        title = "`~visit` - `~besuch`"
        desc = "Erhalte den Gastlogin-Link einer Welt."
        cmd_type = "Server Command"
        cmd_inp = "`~visit <world>`"
        example = "`~visit 143`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    # Fun Commands

    @help.command(name="ag")
    async def ag_(self, ctx):
        title = "`~ag` - `~anagram` - `~guess`"
        desc = "Spiele eine Runde Anagram mit Worten aus DS."
        cmd_type = "Server Command"
        cmd_inp = "`~ag`\n`<your guess>`"
        example = "`~ag`\n`Späher`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="duali")
    async def duali_(self, ctx):
        title = "`~duali` - `~mitspieler`"
        desc = "Der Bot sieht vorraus wie gut du und der angegebene " \
               "User in einem Account zusammenspielen würdet."
        cmd_type = "Server Command"
        cmd_inp = "`~duali <discord username>`"
        example = "`~duali Neel x Kutte`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="hangman")
    async def hangman_(self, ctx):
        title = "`~hangman` - `~galgenmännchen`"
        desc = "Spiele eine Runde Galgenmännchen. Alle Worte " \
               "kommen bis auf ein paar Ausnahmen in DS vor."
        cmd_type = "Server Command"
        cmd_inp = "`~hangman`\n`~guess <character or solution>`"
        example = "`~hangman`\n`~guess a`\n`~guess Späher`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="iron")
    async def iron_(self, ctx):
        title = "`~iron`"
        desc = "Beim Gewinnen von Spielen (ag, hangman und vp) gewinnt man " \
               "Eisen. Man kann sich seinen Speicher anzeigen lassen, die " \
               "aktuelle Top 5 des Servers oder die globale Top 5 aller " \
               "User auf allen Servern auf dem der Bot ist. " \
               "Man kann auch anderen Spielern Eisen übertragen."
        cmd_type = "Server Command"
        cmd_inp = "`~iron`\n`~iron top`\n`~iron global`\n" \
                  "`~iron send <amount> <discord username>`"
        example = "`~iron`\n`~iron top`\n`~iron global`\n`~iron send 8000 Sheldon`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="mirror")
    async def mirror_(self, ctx):
        title = "`~mirror` - `~spiegel`"
        desc = "Der Bot zeigt dir den aktuellen Discord Avatar eines Users." \
               "Falls keiner angegeben ist, wird dir dein Eigener gezeigt"
        cmd_type = "Server Command"
        cmd_inp = "`~mirror`\n`~mirror <discord username>`"
        example = "`~mirror`\n`~mirror mettberg`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="orakel")
    async def orakel_(self, ctx):
        title = "`~orakel`"
        desc = "Frag den Bot eine Ja/Nein Frage und er beantwortet sie dir. " \
               "Schrei ihn aber bitte nicht an."
        cmd_type = "Server Command"
        cmd_inp = "`~orakel <question>`"
        example = "`~orakel Werde ich bald geadelt?`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="quartet")
    async def quartet_(self, ctx):
        title = "`~quartet` - `~quartett` - `~play`"
        desc = "Spiel eine Runde DsQuartett. Gespielt wird mit zufälligen " \
               "Accounts der Serverwelt. Der Spielgründer darf anfangen und " \
               "muss nun eine Eigenschaft auswählen gegen welche die anderen" \
               " Spieler vergleichen müssen. Der Gewinner darf nun beginnen." \
               " Das Spiel geht solange bis keine Karten mehr übrig sind."
        cmd_type = "Server Command / PM Command"
        cmd_inp = "`~quartet`\n`~play <card or stat>`"
        example = "`~quartet`\n`~play card 5`\n`~play card ut`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="quiz")
    async def quiz_(self, ctx):
        title = "`~quiz`"
        desc = "Ein ds-bezogenes Quiz mit 4 unterschiedlichen Modulen."
        cmd_type = "Server Command"
        cmd_inp = "`~quiz <game_rounds>`"
        example = "`~quiz 10`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="vp")
    async def vp_(self, ctx):
        title = "`~vp` - `~videopoker` - `~draw`"
        desc = "Du erhältst 5 Karten aus einem typischen 52er Set. Nun hast " \
               "die die Möglichkeit einmal Karten auszutauschen. " \
               "Man spielt um einen gewünschten Einsatz. " \
               "Je nach Hand erhält man immer größeren Gewinn."
        cmd_type = "Server Command"
        cmd_inp = "`~vp <amount>`\n`~draw <cardnumbers>`"
        example = "`~vp 2000`\n`~draw 13`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await self.cmd_embed(data, ctx))
        await self.send_help(ctx)

    @help.command(name="bot")
    async def self_(self, ctx):
        desc = "Der Bot ist ein Hobbyprojekt meinerseits welches seit " \
               "kurzem allen DS Spielern offen zur Nutzung steht." \
               " Dies sollte anfangs lediglich eine kleine Hilfe für das " \
               "Umwandeln von Koordinaten werden. Inzwischen " \
               "gibt es einige nützliche Commands und auch einige " \
               "Spielereien. Ich freue mich über jegliche Art von " \
               "Vorschlag / Kritik. Man kann mich hierbei entweder Ingame " \
               "oder per Discord PN erreichen."
        page3 = discord.Embed(title=f"Alle Commands unter: {ctx.prefix}help",
                              color=0x0d90e2, description=desc)
        page3.set_author(name="Knueppel-Kutte(DS) / Neel x Kutte#1515")
        page3.set_thumbnail(
            url=ctx.bot.get_user(211836670666997762).avatar_url)
        await ctx.author.send(embed=page3)
        await self.send_help(ctx)


def setup(bot):
    bot.add_cog(Help(bot))
