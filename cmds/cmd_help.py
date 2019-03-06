import asyncio
from discord.ext import commands
import discord


async def embed_message(data, ctx):
    pref = await ctx.bot.get_prefix(ctx.message)
    desc = f"**Beschreibung:** {data[1].replace('~', pref)}\n" \
        f"**Command Typ:** {data[2].replace('~', pref)}\n" \
        f"**Command Input:**\n{data[3].replace('~', pref)}" \
        f"\n**Beispiel:**\n{data[4].replace('~', pref)}"
    emb = discord.Embed(title=f"Command: {data[0].replace('~', pref)}",
                        description=desc, color=discord.Color.blue())
    return emb


async def help_message(ctx):
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.message.add_reaction("📨")
    await asyncio.sleep(5)
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True, case_insensitive=True)
    async def help(self, ctx):
        prefix = await self.bot.get_prefix(ctx.message)
        desc = "Erhalte eine ausführliche Erklärung zu einzelnen Commands mit "
        emb_help = discord.Embed(description=f"{desc}`{prefix}help command`")
        emb_help.add_field(
            name="DS Commands:",
            value="`akte` | *TwStats URL von Spieler/Stamm*\n"
                  "`avatar` | *Bildbearbeitung auf DS Profilbildmaße (+Gif)*\n"
                  "`bash` | *Bashpoints von Spieler/Stamm*\n"
                  "`daily` | *Top 5 der Daily Ranglisten*\n"
                  "`emoji` | *DS Emojis für den Server*\n"
                  # "`map` | *Aktuelle Top 10 Karte einer Welt*\n"
                  "`nude` | *Avatar von Spieler/Stamm/Random*\n"
                  "`player` | *Ingame URL von Spieler/Stamm*\n"
                  "`recap` | *Statistik der letzten Tage von Spieler/Stamm*\n"
                  "`rm` | *Rundmail Generator für mehrere Stämme*\n"
                  "`rz` | *Perfekte Verteilung der Truppen für den Raubzug*\n"
                  "`set` | *Admin Commands für gewisse Settings*\n"
                  "`sl` | *Useless Af*\n"
                  "`time` | *Erinnerung in gewünschter Uhrzeit*\n"
                  "`villages` | *Koord-Liste eines Spieler/Stammes für WB*\n"
                  "`visit` | *Gastlogin-Url einer Welt*\n")
        emb_help.add_field(
            name="Fun Commands:",
            value="`ag` | *Anagram Spiel (DS Worte)*\n"
                  "`duali` | *Dualikompatibilät mit Discord User*\n"
                  "`hangman` | *Hangman Spiel (DS Worte)*\n"
                  "`mirror` | *Avatar eines Discord Users*\n"
                  "`orakel` | *Antwort auf eine Ja/Nein Frage*\n"
                  "`quiz` | *Minigame mit ds-bezogenen Fragen.*\n"
                  "`quartet` | *DS-Quartett mit Spielern der Server-Welt*\n"
                  "`res` | *Statistik der Bot-Währung*\n"
                  "`vp` | *Videopoker mit Bot-Währung*")
        await ctx.author.send(embed=emb_help)
        return await help_message(ctx)

    @help.command(name="akte")
    async def akte_(self, ctx):
        title = "`~akte` - `~twstats`"
        desc = "Erhalte die TwStats Akte eines Spielers oder Stammes."
        cmd_type = "Server Command"
        cmd_inp = "`~akte <playername/tribename>`"
        example = "`~akte madberg`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    @help.command(name="avatar")
    async def avatar_(self, ctx):
        title = "`~avatar` - `~profilbild`"
        desc = "Gebe eine Image-Url an und erhalte das Bild auf DS Maße " \
               "(280x170) geschnitten. Bewegte Bilder werden unterstützt."
        cmd_type = "Private Message Command"
        cmd_inp = "`~avatar <url with (png, jpg, gif ending)>`"
        example = "`~avatar https://pbs.twimg.com/media/DEkxiRCXsAALRoF.jpg `"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    @help.command(name="bash")
    async def bash_(self, ctx):
        title = "`~bash` - `~allbash` - `~attbash` - `~defbash` - `~utbash`"
        desc = "Erhalte entweder eine Zusammenfassung eines Accounts, St" \
               "ammes oder vergleiche 2 Spieler, Stämme und deren Bashpoints."
        cmd_type = "Server Command"
        cmd_inp = "`~bash <playername/tribename>`\n" \
                  "`~allbash <playername> / <playername>`"
        example = "`~bash lemme smash`\n`~allbash gods rage / Knueppel-Kutte`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    @help.command(name="daily")
    async def daily_(self, ctx):
        title = "`~daily` - `~top`"
        desc = "Erhalte die aktuelle Top 5 der jeweiligen Daily Rangliste."
        cmd_type = "Server Command"
        cmd_inp = "`~daily <bash/def/ut/farm/villages/conquer>`"
        example = "`~daily bash`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    @help.command(name="emoji")
    async def emoji_(self, ctx):
        title = "`~emoji` - `~cancer`"
        desc = "Füge deinem Server eine Reihe von DS Emojis hinzu."
        cmd_type = "Server Command"
        cmd_inp = "`~emoji`"
        example = "`~emoji`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    # @help.command(name="map")
    # async def map_(self, ctx):
    #     title = "`~map` - `~karte`"
    #     desc = "Erhalte die aktuelle Top 10 Karte der gewünschten / Serverwelt."
    #     cmd_type = "Server Command"
    #     cmd_inp = "`~map <world#optional>`"
    #     example = "`~map`\n`~map 160`"
    #     data = title, desc, cmd_type, cmd_inp, example
    #     await ctx.author.send(embed=await embed_message(data, ctx))
    #     return await help_message(ctx)

    @help.command(name="nude")
    async def nude_(self, ctx):
        title = "`~nude` - `~nacktbild`"
        desc = "Erhalte das Profilbild eines Spielers, Stammes. Falls " \
               "kein Name angegeben wird, wird ein Bild zufällig " \
               "von allen Spielern der Welt ausgesucht."
        cmd_type = "Server Command"
        cmd_inp = "`~nude`\n`~nude <playername/tribename>`"
        example = "`~nude`\n`~nude Leedsi`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    @help.command(name="player")
    async def player_(self, ctx):
        title = "`~player` - `~spieler` - `~tribe` - `~stamm`"
        desc = "Erhalte den Gastlogin-Link eines Spieler oder Stammes."
        cmd_type = "Server/PM Command"
        cmd_inp = "`~player <playername>`\n`~tribe <tribename>`"
        example = "`~player Philson Cardoso`\n`~tribe Milf!`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

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
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

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
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    @help.command(name="rz")
    async def rz_(self, ctx):
        title = "`~rz3` - `~rz4`"
        desc = "Erhalte die beste Aufteilung für den Raubzug. " \
               "Verschiedene Truppentypen per Leerzeichen trennen."
        cmd_type = "Server Command [Creator: Madberg]"
        cmd_inp = "`~rz4 <unit-amount>`"
        example = "`~rz4 200 100`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    @help.command(name="set")
    async def set_(self, ctx):
        title = "`~set`"
        desc = "Legt die servergebundene Welt fest, einen \"Game Channel\" welchen" \
               "die meisten Game Commands benötigen, einen neuen servergebundenen Prefix," \
               "einen Conquer Channel für stündliche Eroberungen. Zusätzlich lässt sich mit" \
               "`set tribe` nur der Eroberungsfeed eines bestimmten Stammes anzeigen."
        cmd_type = "Admin Server Command"
        cmd_inp = "`~set game`\n`~set world <world>`\n`~set prefix <prefix>`\n" \
                  "`~set conquer`\n`~set tribe <tribename>`"
        example = "`~set game`\n`~set world 117`\n`~set prefix -`" \
                  "`~set conquer`\n`~set tribe BumBum`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    @help.command(name="remove")
    async def remove_(self, ctx):
        title = "`~remove`"
        desc = "Entfernt eingstellte Serverconfigs / Gegensatz zu ~set"
        cmd_type = "Admin Server Command"
        cmd_inp = "`~remove <prefix/game/conquer/tribe>"
        example = "`~sl 1 5 344|555 677|455 344|567"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    # @help.command(name="sl")
    # async def sl_(self, ctx):
    #     title = "`~sl`"
    #     desc = "Erhalte die fertigen Links für das \"Truppen Einfügen" \
    #            " Script\". Alles nach den Truppen Argumenten wird" \
    #            " dann auf Coordinaten gefiltert."
    #     cmd_type = "Private Message Command"
    #     cmd_inp = "`~sl <spy> <lkav> <coord list>"
    #     example = "`~sl 1 5 344|555 677|455 344|567"
    #     data = title, desc, cmd_type, cmd_inp, example
    #     await ctx.author.send(embed=await embed_message(data, ctx))
    #     return await help_message(ctx)

    @help.command(name="time")
    async def time_(self, ctx):
        title = "`~time`"
        desc = "Lasst euch zu einem gewünschten Zeitpunkt erinnern. Der " \
               "Bot schreibt euch nach Ablauf der Zeit per privater " \
               "Nachricht an. Ein Grund kann, muss aber nicht angegeben " \
               "werden. Folgende Zeitformate sind möglich: " \
               "<5h2m10s> h=hour, m=minute, s=seconds | <12:30:27>"
        cmd_type = "Private Message Command"
        cmd_inp = "`~time <time> <reason>`"
        example = "`~time 50s`\n`~time 18:22 Pizza aus dem Ofen holen`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    @help.command(name="villages")
    async def villages_(self, ctx):
        title = "`~villages` - `~dörfer`"
        desc = "Erhalte eine Coord-Liste eines Accounts oder Stammes. " \
               "Wenn gewünscht kann man auch einen Kontinent mit angeben werden. " \
               "Ideal für das Faken mit Workbench."
        cmd_type = "Server Command"
        cmd_inp = "`~villages <amount> <playername/tribename> <continent>`"
        example = "`~villages 20 madberg`\n`~villages all madberg k55`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    @help.command(name="visit")
    async def visit_(self, ctx):
        title = "`~visit` - `~besuch`"
        desc = "Erhalte den Gastlogin-Link einer Welt."
        cmd_type = "Server Command"
        cmd_inp = "`~visit <world>`"
        example = "`~visit 143`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    @help.command(name="ag")
    async def ag_(self, ctx):
        title = "`~ag` - `~anagram` - `~guess`"
        desc = "Spiele eine Runde Anagram mit Worten aus DS."
        cmd_type = "Server Command"
        cmd_inp = "`~ag`\n`<your guess>`"
        example = "`~ag`\n`Späher`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    @help.command(name="duali")
    async def duali_(self, ctx):
        title = "`~duali` - `~mitspieler`"
        desc = "Der Bot sieht vorraus wie gut du und der angegebene " \
               "User in einem Account zusammenspielen würdet."
        cmd_type = "Server Command"
        cmd_inp = "`~duali <discord username>`"
        example = "`~duali Neel x Kutte`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    @help.command(name="hangman")
    async def hangman_(self, ctx):
        title = "`~hangman` - `~galgenmännchen`"
        desc = "Spiele doch eine Runde Galgenmännchen. Alle Worte " \
               "kommen bis auf ein paar Ausnahmen in DS vor."
        cmd_type = "Server Command"
        cmd_inp = "`~hangman`\n`~guess <character or solution>`"
        example = "`~hangman`\n`~guess a`\n`~guess Späher`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    @help.command(name="mirror")
    async def mirror_(self, ctx):
        title = "`~mirror` - `~spiegel`"
        desc = "Der Bot zeigt dir den aktuellen Discord Avatar eines Users." \
               "Falls keiner angegeben ist siehst du selber in den Spiegel."
        cmd_type = "Server Command"
        cmd_inp = "`~mirror`\n`~mirror <discord username>`"
        example = "`~mirror`\n`~mirror mettberg`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    @help.command(name="orakel")
    async def orakel_(self, ctx):
        title = "`~orakel`"
        desc = "Frag den Bot eine Ja/Nein Frage und er beantwortet sie dir. " \
               "Schrei ihn aber bitte nicht an."
        cmd_type = "Server Command"
        cmd_inp = "`~orakel <question>`"
        example = "`~orakel Werde ich bald geadelt?`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

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
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    @help.command(name="quiz")
    async def quiz_(self, ctx):
        title = "`~quiz`"
        desc = "Ein ds-bezogenes Quiz mit 4 unterschiedlichen Modulen."
        cmd_type = "Server Command"
        cmd_inp = "`~quiz <game_rounds>`"
        example = "`~quiz 10`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    @help.command(name="res")
    async def res_(self, ctx):
        title = "`~res`"
        desc = "Beim Gewinnen von Spielen (ag, hangman und vp) gewinnt man " \
               "Eisen. Man kann sich seinen Speicher anzeigen lassen, die " \
               "aktuelle Top 5 des Servers oder die globale Top 5 aller " \
               "User auf allen Servern auf dem der Bot ist. " \
               "Man kann auch anderen Spielern Res übertragen."
        cmd_type = "Server Command"
        cmd_inp = "`~res`\n`~res top`\n`~res global`\n" \
                  "`~res send <amount> <discord username>`"
        example = "`~res`\n`~res top`\n`~res global`\n`~res send 8000 Luke`"
        data = title, desc, cmd_type, cmd_inp, example
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

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
        await ctx.author.send(embed=await embed_message(data, ctx))
        return await help_message(ctx)

    @help.command(name="bot")
    async def self_(self, ctx):
        pref = await ctx.bot.get_prefix(ctx.message)
        desc = "Der Bot ist ein Hobbyprojekt meinerseits welches seit " \
               "kurzem allen DS Spielern offen zur Nutzung steht." \
               " Dies sollte anfangs lediglich eine kleine Hilfe für das " \
               "Umwandeln von Koordinaten werden. Inzwischen " \
               "gibt es einige nützliche Commands und auch einige " \
               "Spielereien. Ich freue mich über jegliche Art von " \
               "Vorschlag / Kritik. Man kann mich hierbei entweder Ingame " \
               "oder per Discord PN erreichen."
        page3 = discord.Embed(title=f"Alle Commands unter: {pref}help",
                              color=0x0d90e2, description=desc)
        page3.set_author(name="Knueppel-Kutte(DS) / Neel x Kutte#1515")
        page3.set_thumbnail(
            url=ctx.bot.get_user(211836670666997762).avatar_url)
        await ctx.author.send(embed=page3)
        return await help_message(ctx)


def setup(bot):
    bot.add_cog(Help(bot))
