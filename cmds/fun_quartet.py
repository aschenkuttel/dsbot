from discord.ext import commands
from load import load
from utils import IngameError, error_embed, pcv, game_channel_only, private_message_only
import discord
import asyncio
import operator

prop = {"id": "ID", "rang": "Rang", "punkte": "Punkte", "dörfer": "Dörfer",
        "off": "Off", "def": "Def", "unt": "Unt", "insgesamt": "Insgesamt"}


class Quartet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = {}

    def game_search(self, player_id):
        for guild in self.data:
            if player_id in self.data[guild]["player"]:
                return self.data[guild], guild

    def change_starter(self, game, player_id):
        for player in game["player"]:
            game["first"][player] = 0
        game["first"][player_id] = 1

    def game_end(self, guild_id):
        del self.data[guild_id]

    def ingame_check(self, ctx, in_game=1):
        if in_game:
            for guild in self.data:
                if ctx.author.id in self.data[guild]["player"]:
                    return True
            raise IngameError
        else:
            for guild in self.data:
                if ctx.author.id in self.data[guild]["player"]:
                    raise IngameError
            return True

    def game_basic(self, guild_id, author_id):
        game = {"player": {author_id: {}}, "first": {author_id: 1},
                "running": 0, "played": {}, "stat": "",
                "points": {author_id: 0}, "channel": 0}
        self.data.update({guild_id: game})

    def get_card(self, card_set, card):
        return card_set[card]

    def get_winner(self, card_set, stat):
        win_lis = {}
        for player in card_set:
            win_lis.update({player: self.get_stat(card_set, player, stat)})

        key = (operator.itemgetter(1))
        if stat not in ["dörfer", "punkte", "off", "def", "unt", "insgesamt"]:
            winner = sorted(win_lis.items(), key=key, reverse=False)
        else:
            winner = sorted(win_lis.items(), key=key, reverse=True)

        win = winner[0][1]
        for player, points in winner:
            if not points == win:
                win_lis.pop(player)
        return win_lis

    def get_stat(self, card_set, card, stat):
        if stat == "id":
            return card_set[card].id
        if stat == "rang":
            return card_set[card].rank
        if stat == "punkte":
            return card_set[card].points
        if stat == "dörfer":
            return card_set[card].villages
        if stat == "off":
            return card_set[card].att_bash
        if stat == "def":
            return card_set[card].def_bash
        if stat == "unt":
            return card_set[card].ut_bash
        if stat == "insgesamt":
            return card_set[card].all_bash

    def remove_card(self, game, played_cards):
        for player in list(game["player"]):
            for card in list(game["player"][player]):
                if game["player"][player][card] is played_cards[player]:
                    game["player"][player].pop(card)
        game["played"] = {}

    def compare_embed(self, card_list, win_dict, stat, ctx, game_points):
        data = ctx.bot.get_user(next(iter(win_dict.keys()))).name
        title = f"{data} hat den Trumpf gewonnen!"
        if len(win_dict) > 1:
            title = "Es gab einen Gleichstand!"
            for index, guy in enumerate(win_dict):
                title += f" {ctx.bot.get_user(guy).name}"
                if not index == len(win_dict):
                    title += "und"
            title += "bekommen einen Punkt!"
        em = discord.Embed(title=title)

        for card in card_list:
            obj = card_list[card]
            em.add_field(
                name=f"Karte von {ctx.bot.get_user(card).name}: > {obj.name} <",
                value=f"ID: `{pcv(obj.id)}` | Rang: `{pcv(obj.rank)}` | Punkte:"
                f" `{pcv(obj.points)}` | Dörfer: `{pcv(obj.villages)}` | Off:"
                f" `{pcv(obj.att_bash)}`\nDef: `{pcv(obj.def_bash)}` | Unt:"
                f" `{pcv(obj.ut_bash)}` | Insgesamt: `{pcv(obj.all_bash)}`"
                f"\n".replace(prop[stat], "**" + prop[stat] + "**"), inline=False)

        msg = ""
        for player in game_points:
            msg += f"{ctx.bot.get_user(player).name}: {game_points[player]} | "

        em.set_footer(text=f"{msg[:-3]}")
        return em

    def embed_create(self, game, player_id, beg=0):
        em_bed = discord.Embed(title="Deine Karten:", color=0x0080c0)
        cards = game["player"][player_id]
        if beg:
            c1 = cards[next(iter(cards))]
            em_bed.add_field(
                name=f"{next(iter(cards))}: > {c1.name} <",
                value=f"ID: `{pcv(c1.id)}` | Rang: `{pcv(c1.rank)}` | Punkte: "
                f"`{pcv(c1.points)}` | Dörfer: `{pcv(c1.villages)}` | Off: "
                f"`{pcv(c1.att_bash)}`\nDef: `{pcv(c1.def_bash)}`| Unt: "
                f"`{pcv(c1.ut_bash)}` | Insgesamt: `{pcv(c1.all_bash)}`",
                inline=False)
        for card in cards:
            car = f"{card}: {cards[card].name}"
            em_bed.add_field(name=car, value="Versteckt", inline=False)
        if beg:
            em_bed.remove_field(1)
        return em_bed

    async def start_game(self, world, guild_id):
        user = self.data[guild_id]["player"]
        card_dict = {1: 10, 2: 10, 3: 9, 4: 8}
        num = card_dict[len(user)]
        players = []
        for player in user:
            players.append(player)
        cards = await load.random_id(world, amount=len(user) * num, top=250)
        play_num = 0
        for card in cards:
            if num == 1:
                data = {f"card{card_dict[len(user)] - num + 1}": card}
                user[players[play_num]].update(data)
                play_num += 1
                num = card_dict[len(user)]
                continue
            cache = {f"card{card_dict[len(user)] - num + 1}": card}
            user[players[play_num]].update(cache)
            num -= 1

    @commands.command(aliases=["quartett"])
    @game_channel_only()
    async def quartet(self, ctx):

        self.ingame_check(ctx, 0)
        if ctx.guild.id in self.data:
            msg = "Es läuft bereits eine Runde auf dem Server!"
            return await ctx.send(msg)

        pre = load.pre_fix(ctx.guild.id)
        self.game_basic(ctx.guild.id, ctx.author.id)
        msg = await ctx.send(f"`{ctx.author.name}` möchte eine Partie "
                             f"**dsQuartett** spielen!\nTrete der Runde "
                             f"mit `{pre}join` bei (*2-4 Spieler - "
                             f"Das Spiel startet in einer Minute*)")

        await asyncio.sleep(60)
        # ----- No Solo Action ----- #
        if len(self.data[ctx.guild.id]["player"]) == 1:
            content = "Es wollte leider niemand mitspielen. **Spiel gestoppt**"
            await msg.edit(content=content)
            return self.game_end(ctx.guild.id)

        else:
            self.data[ctx.guild.id]["running"] = 1
            self.data[ctx.guild.id]["channel"] = ctx.message.channel
            await self.start_game(ctx.world, ctx.guild.id)
            for player in self.data[ctx.guild.id]["player"]:
                if player == ctx.author.id:
                    embed = self.embed_create(self.data[ctx.guild.id], player, 1)
                    await ctx.author.send(embed=embed)
                    await self.bot.get_user(player).send(
                        f"Entscheide dich für einen Stat deiner "
                        f"ersten Karte und spiele mit: `{pre}play property`")
                    continue
                embed = self.embed_create(self.data[ctx.guild.id], player)
                await self.bot.get_user(player).send(embed=embed)
                await self.bot.get_user(player).send(
                    f"Das Spiel ist gestartet! "
                    f"`{ctx.author.name}` ist an der Reihe!")
            players = []
            for player in self.data[ctx.guild.id]["player"]:
                players.append(self.bot.get_user(player).name)
            try:
                await msg.delete()
            except discord.Forbidden:
                pass
            await ctx.send(f"Das Spiel ist gestartet. (1h Timeout)\n"
                           f"Teilnehmer: `{'` `'.join(players)}`")
            await asyncio.sleep(3600)
            self.game_end(ctx.guild.id)
            return await ctx.send("**Game Over**: Die Spielzeit von "
                                  "einer Stunde ist abgelaufen.")

    @commands.command()
    @game_channel_only()
    async def join(self, ctx):

        self.ingame_check(ctx, 0)
        if ctx.guild.id not in self.data:
            return await ctx.send("Aktuell läuft kein Spiel - Starte eine "
                                  "neue Runde auf einem Server mit `!quartet`")

        if self.data[ctx.guild.id]["running"] == 1:
            players = []
            for player in self.data[ctx.guild.id]["player"]:
                players.append(self.bot.get_user(player).name)
            await ctx.send(f"Aktuell läuft bereits ein Spiel auf diesem "
                           f"Server!\nTeilnehmer: `{'` `'.join(players)}`")

        player_num = len(self.data[ctx.guild.id]["player"])
        if not player_num >= 4:
            self.data[ctx.guild.id]["player"].update({ctx.author.id: {}})
            self.data[ctx.guild.id]["first"].update({ctx.author.id: 0})
            self.data[ctx.guild.id]["points"].update({ctx.author.id: 0})
            place = 4 - player_num - 1
            if not place == 0:
                pla_msg = f"noch {place} Plätze"
            else:
                pla_msg = "keine Plätze mehr"
            msg = f"`{ctx.author.name}` nimmt am Spiel teil! " \
                f"Es sind {pla_msg} frei."
            await ctx.send(msg)

        else:
            return await ctx.send("Es haben bereits 4 Spieler teilgenommen."
                                  " Das Spiel startet in Kürze!")

    @private_message_only()
    @commands.command(aliases=["spiele"])
    async def play(self, ctx, args):

        self.ingame_check(ctx)
        game, guild_id = self.game_search(ctx.author.id)
        if not game:
            return await ctx.auhor.send("Du bist aktuell kein Teilnehmer"
                                        " einer dsQuartett-Runde.")
        if ctx.author.id in game["played"]:
            return await ctx.author.send(
                "Du hast bereits eine Karte gespielt - "
                "Warte bis sich alle Spieler entschieden haben.")
        if game["first"][ctx.author.id] is 1:
            stat_list = ["id", "rang", "punkte", "dörfer",
                         "off", "def", "unt", "insgesamt"]
            if args.lower() not in stat_list:
                return await ctx.author.send("Die Eigenschaft wurde "
                                             "leider falsch geschrieben!")
            if game["stat"] == args.lower():
                return await ctx.author.send("Diese Eigenschaft wurde bereits "
                                             "letzte Runde verglichen!")
            next_dude = next(iter(game["player"][ctx.author.id]))
            chosen = self.get_card(game["player"][ctx.author.id], next_dude)
            game["played"].update({ctx.author.id: chosen})
            game.update({"stat": args.lower()})
            await ctx.author.send("Deine Karte wurde eingeloggt!")

            # --- MSG to Everyone: Choose Card --- #
            for player in game["player"]:
                if game["first"][player] is 1:
                    continue
                await self.bot.get_user(player).send(
                    f"{ctx.author.name} möchte `{prop[args.lower()]}` "
                    f"vergleichen: Wähle deine Karte mit `!play card`")
        else:
            if not game["played"]:
                return await ctx.send(
                    f"Du musst warten bis der erste Spieler eine"
                    f" Eigenschaft zum Vergleichen ausgewählt hat.")
            if args not in game["player"][ctx.author.id]:
                return await ctx.send("Du besitzt diese Karte nicht.")
            chosen = self.get_card(game["player"][ctx.author.id], args)
            game["played"].update({ctx.author.id: chosen})
            await ctx.send("Deine Karte wurde gespielt!")

            # --- Everybody Played? --- #
            if len(game["player"]) is len(game["played"]):
                stat = game["stat"]
                result = self.get_winner(game["played"], stat)
                for win_pl in result:
                    game["points"][win_pl] += 1
                for player in game["player"]:
                    await self.bot.get_user(player).send(
                        embed=self.compare_embed(game["played"], result, stat,
                                                 ctx, game["points"]))
                await asyncio.sleep(5)
                self.remove_card(game, game["played"])

                # --- No Card Left? --- #
                if not game["player"][ctx.author.id]:
                    end_txt = ""
                    winner = sorted(game["points"].items(),
                                    key=operator.itemgetter(1), reverse=True)
                    for index, (dude, points) in enumerate(winner):
                        if f"`{points}`" in end_txt:
                            end_txt = end_txt.replace(" mit `{points}`", f"und "
                            f"{self.bot.get_user(dude).name} mit `{points}`")
                        else:
                            place = len(end_txt.split("\n"))
                            end_txt += f"**Platz {place}:** " \
                                f"*{self.bot.get_user(dude).name} mit" \
                                f" `{points}` Punkten.*\n"

                    for sentence in end_txt.split("\n"):
                        if sentence:
                            num = sentence.count(" und ") - 1
                            cache = sentence.replace(" und", ",", num)
                            end_txt = end_txt.replace(sentence, cache)
                    await game["channel"].send(end_txt)
                    self.game_end(guild_id)
                    return

                self.change_starter(game, next(iter(result.keys())))
                await asyncio.sleep(5)
                last_winner = None
                for player in game["first"]:
                    if game["first"][player] == 1:
                        last_winner = player
                for player in game["first"]:
                    if game["first"][player] == 1:
                        await self.bot.get_user(player).send(
                            embed=self.embed_create(game, player, 1))
                        await self.bot.get_user(player).send(
                            "Du bist am Zug! Wähle eine "
                            "Eigenschaft mit !play property")
                        continue
                    await self.bot.get_user(player).send(
                        embed=self.embed_create(game, player, 0))
                    await self.bot.get_user(player).send(
                        f"`{self.bot.get_user(last_winner).name}`"
                        f" ist am Zug! Warte bis er sich für eine"
                        f" Vergleichs-Eigenschaft entschieden hat!")

    @quartet.error
    async def quartet_error(self, ctx, error):
        if isinstance(error, IngameError):
            msg = "Du bist bereits Teilnehmer einer aktiven dsQuartett-Runde!"
            return await ctx.send(embed=error_embed(msg))

    @join.error
    async def join_error(self, ctx, error):
        if isinstance(error, IngameError):
            msg = "Du bist bereits Teilnehmer einer aktiven dsQuartett-Runde!"
            return await ctx.send(embed=error_embed(msg))

    @play.error
    async def play_error(self, ctx, error):
        if isinstance(error, IngameError):
            msg = "Du nimmst aktuell an keiner aktiven dsQuartett-Runde teil!"
            return await ctx.send(embed=error_embed(msg))
        if isinstance(error, commands.MissingRequiredArgument):
            msg = "Die gewünschte Karte/Eigenschaft fehlt."
            return await ctx.send(embed=error_embed(msg))


def setup(bot):
    bot.add_cog(Quartet(bot))
