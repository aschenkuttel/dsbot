from discord.ext import commands
import discord
import asyncio
import utils


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = {}
        self.categories = [
            "Administratives",
            "Stämme Features",
            "Utilities and Fun",
            "Minigames"
        ]

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

    def packing(self, storage, package):
        pkg = [f"`{c}`" for c in package]
        storage.append(" ".join(pkg))
        package.clear()

    def help_embed(self, prefix):
        desc = "Erhalte eine ausführliche Erklärung zu\neinzelnen " \
               "Commands mit `{0}help <command>`".format(prefix)
        emb_help = discord.Embed(description=desc, color=discord.Color.blue())
        emb_help.set_footer(text="Supportserver: https://discord.gg/s7YDfFW")

        groups = {name: [] for name in self.categories}
        for name, cog in self.bot.cogs.items():
            cog_type = getattr(cog, 'type', None)

            if cog_type is None:
                continue

            category = self.categories[cog_type]
            for cmd in cog.get_commands():

                if cmd.hidden is True:
                    continue

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

        cmd_description = ctx.lang.help[ctx.command.name]

        raw_inp = [f"`{ctx.prefix}{cmd}`" for cmd in data[2]]
        cmd_inp = "\n".join(raw_inp)

        raw_example = [f"`{ctx.prefix}{cmd}`" for cmd in data[3]]
        example = "\n".join(raw_example)

        color = discord.Color.blue()
        description = f"**Beschreibung:**\n{cmd_description}\n" \
                      f"**Command Typ:** {data[1]}\n" \
                      f"**Command Input:**\n {cmd_inp}\n" \
                      f"**Beispiel:**\n {example}"
        emb = discord.Embed(title=title, description=description, color=color)
        return emb

    async def send_embed(self, ctx, embed):
        if "pin" in ctx.message.content:
            await ctx.send(embed=embed)

        else:
            await ctx.author.send(embed=embed)
            response = await ctx.private_hint()
            if response:
                data = {'embed': embed, 'cache': [ctx.author.id]}
                self.cache[ctx.message.id] = data
                await asyncio.sleep(600)
                self.cache.pop(ctx.message.id)

    @commands.group(aliases=["pin"])
    async def help(self, ctx):
        pin = "pin" in ctx.message.content.lower()
        if pin and not ctx.author.guild_permissions.administrator:
            raise commands.MissingPermissions(['administrator'])

        if ctx.invoked_subcommand is not None:
            return

        if ctx.subcommand_passed:
            msg = "Der angegebene Command existiert nicht"
            embed = discord.Embed(color=discord.Color.red(), description=msg)
            embed.set_footer(text=f"Alle Commands unter {ctx.prefix}help")
            await ctx.send(embed=embed)
        else:
            embed = self.help_embed(ctx.prefix)
            await self.send_embed(ctx, embed)

    # Administratives
    @help.command(name="set")
    async def set_(self, ctx):
        title = ["set"]
        cmd_type = "Admin Command"
        cmd_inp = ["set world <world>",
                   "set channelworld <world>",
                   "set game",
                   "set conquer",
                   "set prefix <prefix>"]
        example = ["set world de172",
                   "set channelworld de164",
                   "set game",
                   "set conquer",
                   "set prefix -"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="reset")
    async def reset_(self, ctx):
        title = ["reset"]
        cmd_type = "Admin Command"
        cmd_inp = ["reset <game|conquer|config>"]
        example = ["reset game",
                   "reset conquer",
                   "reset config"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="world")
    async def world_(self, ctx):
        title = ["world"]
        cmd_type = "Admin Command"
        cmd_inp = ["world"]
        example = ["world"]

        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="enable")
    async def enable_(self, ctx):
        title = ["enable"]
        cmd_type = "Admin Command"
        cmd_inp = ["enable"]
        example = ["enable"]

        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="remove")
    async def remove_(self, ctx):
        title = ["remove"]
        cmd_type = "Admin Command"
        cmd_inp = ["remove channelworld",
                   "remove game",
                   "remove conquer",
                   "remove conquer <channel_id>",
                   "remove prefix"]
        example = ["remove channelworld",
                   "remove game",
                   "remove conquer",
                   "remove conquer 123456789",
                   "remove prefix"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="worlds")
    async def worlds_(self, ctx):
        title = ["worlds"]
        cmd_type = "Admin Command"
        cmd_inp = ["worlds"]
        example = ["worlds"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="conquer")
    async def conquer_(self, ctx):
        title = ["conquer"]
        cmd_type = "Admin Command"
        cmd_inp = ["conquer add <tribe>",
                   "conquer remove <tribe>",
                   "conquer grey",
                   "conquer list",
                   "conquer clear"]
        example = ["conquer add 300",
                   "conquer remove 300",
                   "conquer grey",
                   "conquer list",
                   "conquer clear"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="convert")
    async def convert_(self, ctx):
        title = ["convert"]
        cmd_type = "Admin Command"
        cmd_inp = ["convert",
                   "convert <coord|report|mention>"]
        example = ["convert",
                   "convert coord",
                   "convert report",
                   "convert mention"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    # Stämme Features
    @help.command(name="map")
    async def map_(self, ctx):
        title = ["map"]
        cmd_type = "Server Command"
        cmd_inp = ["map",
                   "map <tribe> <tribe> <tribe>",
                   "map <tribe> <tribe> & <tribe> <tribe>",
                   "map <top=5-20> <player=true/false>",
                   "map <label=0-3> <center=coord> <zoom=0-5>",
                   "map <tribe> & <tribe> <tribe> <label=0-3>"]
        example = ["map",
                   "map 300 W-Inc",
                   "map 300 W-Inc & SPARTA",
                   "map top=5 player=true",
                   "map center=450|450 zoom=3 label=0",
                   "map 300 & W-Inc SPARTA label=3"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="top")
    async def top_(self, ctx):
        title = ["top"]
        cmd_type = "Server Command"
        cmd_inp = ["top <bash/def/ut/farm/villages/scavenge/conquer>"]
        example = ["top bash"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="bash")
    async def bash_(self, ctx):
        title = ["bash"]
        cmd_type = "Server Command"
        cmd_inp = ["bash <playername/tribename>",
                   "bash <playername> / <playername>"]
        example = ["bash lemme smash",
                   "bash gods rage / Knueppel-Kutte"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="nude")
    async def nude_(self, ctx):
        title = ["nude"]
        cmd_type = "Server Command"
        cmd_inp = ["nude",
                   "nude <playername/tribename>"]
        example = ["nude",
                   "nude Leedsi"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="daily", aliases=["dailytribe"])
    async def daily_(self, ctx):
        title = ["daily", "aktueller"]
        cmd_type = "Server Command"
        cmd_inp = ["daily <points|minus|basher|defender>",
                   "dailytribe <supporter|fighter|loser|conquerer>"]
        example = ["daily supporter",
                   "dailytribe minus"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="recap")
    async def recap_(self, ctx):
        title = ["recap"]
        cmd_type = "Server Command"
        cmd_inp = ["recap <playername> <time>"]
        example = ["recap madberg",
                   "recap madberg 20"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="visit")
    async def visit_(self, ctx):
        title = ["visit"]
        cmd_type = "Server Command"
        cmd_inp = ["visit <world>"]
        example = ["visit de143"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="custom")
    async def custom_(self, ctx):
        title = ["custom"]
        cmd_type = "Server Command"
        cmd_inp = ["custom <world>"]
        example = ["custom de172"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="player", aliases=["tribe"])
    async def player_(self, ctx):
        title = ["player", "tribe"]
        cmd_type = "Server Command"
        cmd_inp = ["player <playername>",
                   "tribe <tribename>"]
        example = ["player Philson Cardoso",
                   "tribe Milf!"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="members")
    async def members_(self, ctx):
        title = ["members"]
        cmd_type = "Server Command"
        cmd_inp = ["members <tribetag>",
                   "members <tribetag> <url_type=ingame>"]
        example = ["members W-Inc",
                   "members W-Inc twstats"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="bashrank")
    async def bashrank_(self, ctx):
        title = ["bashrank"]
        cmd_type = "Server Command"
        cmd_inp = ["bashrank <tribetag>",
                   "bashrank <tribetag> <bashtype>"]
        example = ["bashrank W-Inc",
                   "bashrank W-Inc support"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="inactive", aliases=["graveyard"])
    async def inactive_(self, ctx):
        title = ["inactive", "graveyard"]
        cmd_type = "Server Command"
        cmd_inp = ["inactive <coord>",
                   "inactive <coord> <radius=1-25> <since=1-14>",
                   "inactive <coord> <radius=1-25> <points<=>yourvalue>",
                   "inactive <coord> <tribe=true/false>"]
        example = ["inactive 500|500",
                   "inactive 500|500 radius=20 since=7",
                   "inactive 500|500 radius=5 points<500",
                   "inactive 500|500 tribe=true"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="settings")
    async def settings_(self, ctx):
        title = ["settings"]
        cmd_type = "Server Command"
        cmd_inp = ["settings",
                   "settings <world>"]
        example = ["settings",
                   "settings de186"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="villages")
    async def villages_(self, ctx):
        title = ["villages"]
        cmd_type = "Server Command"
        cmd_inp = ["villages <amount> <playername/tribename>"]
        example = ["villages 20 madberg",
                   "villages all madberg k55"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="timelapse")
    async def timelapse_(self, ctx):
        title = ["timelapse"]
        cmd_type = "Server Command"
        cmd_inp = ["timelapse <world>"]
        example = ["timelapse",
                   "timelapse de186",
                   "timelapse de186 days=20"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="bb")
    async def bb_(self, ctx):
        title = ["bb"]
        cmd_type = "Server Command"
        cmd_inp = ["bb <coord>",
                   "bb <coord> <radius=1-25>",
                   "bb <coord> <radius=1-25> <points<=>yourvalue>"]
        example = ["bb 555|555",
                   "bb 555|555 radius=25",
                   "bb 555|555 radius=20 points<100",
                   "bb 555|555 radius=10 points>200"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="rm")
    async def rm_(self, ctx):
        title = ["rm"]
        cmd_type = "Server Command"
        cmd_inp = ["rm <tribename> <tribename>"]
        example = ["rm Skype! down \"Mum, I like to farm!\""]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="rz", aliases=["rz2", "rz3", "rz4"])
    async def rz_(self, ctx):
        title = ["rz", "rz2", "rz3", "rz4"]
        cmd_type = "Server Command [Creator: Madberg]"
        cmd_inp = ["rz4 <unit-amount>"]
        example = ["rz4 200 100"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="sl")
    async def sl_(self, ctx):
        title = ["sl"]
        cmd_type = "Server/PM Command"
        cmd_inp = ["sl <troop=amount> <*coords>"]
        example = ["sl speer=20 lkav=5 späher=2 550|490 489|361",
                   "sl axt=80ramme=20ag=1 [coord]452|454[/coord]"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    # Utilities
    @help.command(name="info")
    async def info_(self, ctx):
        title = ["info"]
        cmd_type = "Server Command"
        cmd_inp = ["info"]
        example = ["info"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="poll")
    async def poll_(self, ctx):
        title = ["poll"]
        cmd_type = "Server Command"
        cmd_inp = ["poll \"<question>\" <option> <option> ..."]
        example = ["poll \"Sollen wir das BND beenden?\" Ja Nein Vielleicht"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="duali")
    async def duali_(self, ctx):
        title = ["duali"]
        cmd_type = "Server Command"
        cmd_inp = ["duali <discord username>"]
        example = ["duali Neel x Kutte"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="emoji")
    async def emoji_(self, ctx):
        title = ["emoji"]
        cmd_type = "Admin Command"
        cmd_inp = ["emoji"]
        example = ["emoji"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="avatar")
    async def avatar_(self, ctx):
        title = ["avatar"]
        cmd_type = "PM Command"
        cmd_inp = ["avatar <url with (png, jpg, gif ending)>"]
        example = ["avatar https://homepage/beispielbild.png"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="orakel")
    async def orakel_(self, ctx):
        title = ["orakel"]
        cmd_type = "Server Command"
        cmd_inp = ["orakel <question>"]
        example = ["orakel Werde ich bald geadelt?"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="remind")
    async def remind_(self, ctx):
        title = ["remind"]
        cmd_type = "PM Command"
        cmd_inp = ["remind <time> <newline> <reason>",
                   "remind list",
                   "remind remove <reminder id>",
                   "remind clear",
                   "now"]
        example = ["remind 50s",
                   "remind 18:22\nPizza aus dem Ofen holen",
                   "remind list",
                   "remind remove 120",
                   "remind clear",
                   "now`"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="pin")
    async def pin_(self, ctx):
        title = ["pin"]
        cmd_type = "Admin Command"
        cmd_inp = ["pin",
                   "pin <command>"]
        example = ["pin",
                   "pin player"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    # Minigames
    @help.command(name="dice")
    async def dice_(self, ctx):
        title = ["dice"]
        cmd_type = "Server Command"
        cmd_inp = ["dice <amount (1000-500000) or accept>"]
        example = ["dice 50000",
                   "dice accept"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="iron")
    async def iron_(self, ctx):
        title = ["iron"]
        cmd_type = "Server Command"
        cmd_inp = ["iron",
                   "iron top",
                   "iron local",
                   "iron global",
                   "iron send <amount> <discord username>"]
        example = ["iron",
                   "iron top",
                   "iron local",
                   "iron global",
                   "iron send 8000 Sheldon"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="quiz")
    async def quiz_(self, ctx):
        title = ["quiz"]
        cmd_type = "Server Command"
        cmd_inp = ["quiz <rounds>"]
        example = ["quiz 10"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="slots", aliases=["slotistics"])
    async def slots_(self, ctx):
        title = ["slots", "slotistics"]
        cmd_type = "Server Command"
        cmd_inp = ["slots",
                   "slotistics"]
        example = ["slots",
                   "slotistics"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="anagram", aliases=["ag"])
    async def anagram_(self, ctx):
        title = ["anagram", "ag"]
        cmd_type = "Server Command"
        cmd_inp = ["ag",
                   "<guess>"]
        example = ["ag",
                   "Späher"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="blackjack", aliases=["bj"])
    async def blackjack_(self, ctx):
        title = ["blackjack", "bj"]
        cmd_type = "Server Command"
        cmd_inp = ["bj <optional=amount(100-50000)>"]
        example = ["bj",
                   "bj 5000"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="hangman", aliases=["hg"])
    async def hangman_(self, ctx):
        title = ["hangman", "hg"]
        cmd_type = "Server Command"
        cmd_inp = ["hangman",
                   "guess <character or solution>"]
        example = ["hangman",
                   "guess h",
                   "guess Späher"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="tribalcards", aliases=["tc"])
    async def tribalcards_(self, ctx):
        title = ["tribalcards", "tc", "play"]
        cmd_type = "Server Command / PM Command"
        cmd_inp = ["quartet",
                   "play <card or stat>"]
        example = ["quartet",
                   "play 5",
                   "play off"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)

    @help.command(name="videopoker", aliases=["vp", "draw"])
    async def videpoker_(self, ctx):
        title = ["videopoker", "vp", "draw"]
        cmd_type = "Server Command"
        cmd_inp = ["vp <2000, optional=amount(100-2000)>",
                   "draw <cardnumbers>"]
        example = ["vp",
                   "vp 500",
                   "draw 13"]
        data = title, cmd_type, cmd_inp, example
        embed = self.cmd_embed(data, ctx)
        await self.send_embed(ctx, embed)


def setup(bot):
    bot.add_cog(Help(bot))
