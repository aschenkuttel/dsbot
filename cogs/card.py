import discord
from discord.ext import commands
import asyncio
import utils

prop = {"name": "Spieler", "id": "ID", "rank": "Rang", "points": "Punkte",
        "villages": "Dörfer", "att_bash": "OFF", "def_bash": "DEF",
        "ut_bash": "UT", "all_bash": "Insgesamt"}


class Card(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = {}
        self.cache = []
        self.format = ('points', 'att_bash', 'def_bash',
                       'ut_bash', 'all_bash')

    def show_hand(self, hand, instruction, beginner=False):
        description = f"**Tribalcards | Deine Hand:**\n\n"
        for index, player in enumerate(hand):

            if beginner and index == 0:
                card = f"Oberster Karte:\n"
                values = []
                for key, value in prop.items():
                    pval = getattr(player, key)

                    if key in self.format:
                        pval = utils.pcv(pval)

                    pstat = f"**{value}:** `{pval}`"
                    values.append(pstat)

                result = utils.show_list(values, sep=" | ", line_break=3)
                card += f"{result}\n\n"

                base = "Du bist am Zug, wähle eine Eigenschaft mit {}play <property>"
                instruction = base.format(instruction)

            else:
                card = f"**{index + 1}**: {player.name}\n"

            description += card

        embed = discord.Embed(description=description)
        embed.set_footer(text=instruction)
        return embed

    @utils.game_channel_only()
    @commands.command(name="tribalcards", aliases=["tc"])
    async def tribalcards_(self, ctx, response=None):
        data = self.data.get(ctx.guild.id)
        if data is False:
            return

        if ctx.author.id in self.cache and response is None:
            msg = f"Du bist bereits Spieler einer aktiven Tribalcard-Runde"
            return await ctx.send(embed=utils.error_embed(msg))

        if response and response.lower() == "join":
            if not data:
                base = "Aktuell ist keine Spielanfrage offen, starte mit `{}`"
                msg = f"{base.format(ctx.prefix)}tribalcards"

            elif len(data['players']) == 4:
                msg = "Es sind bereits 4 Spieler registriert"

            elif data.get('active'):
                names = [f"`{m.display_name}`" for m in data['players']]
                base = "Aktuell läuft bereits eine Runde auf dem Server, Teilnehmer:\n`{}`"
                msg = base.format(utils.show_list(names, line_break=4))

            else:
                data['players'][ctx.author] = {}
                amount = 4 - len(data['players'])

                if not amount:
                    free_spots = "`keine Plätze` mehr"
                else:
                    free_spots = f"noch `{amount} Plätze`"

                base = "**{}** nimmt am Spiel teil\n(Noch {} frei)"
                msg = base.format(ctx.author.display_name, free_spots)

            await ctx.send(msg)

        elif response is None:
            self.cache.append(ctx.author.id)

            data = {'players': {ctx.author: {}}, 'id': ctx.message.id,
                    'played': {}, 'beginner': ctx.author, 'ctx': ctx}
            self.data[ctx.guild.id] = data

            base = "**{}** möchte eine Runde **Tribalcards** spielen,\ntritt der Runde mit " \
                   "`{}tc join` bei:\n(2-4 Spieler, Spiel beginnt in 60s)"
            msg = base.format(ctx.author.display_name, ctx.prefix)
            begin = await ctx.send(msg)

            await asyncio.sleep(20)
            data['active'] = True

            player_num = len(data['players'])
            if player_num == 0:
                content = "Es wollte leider niemand mitspielen :/\n**Spiel beendet**"
                await begin.edit(content=content)
                return self.data.pop(ctx.guild.id)

            amount = (3 - player_num) * player_num
            cards = await self.bot.fetch_random(ctx.server, amount=amount, top=100)
            for player, userdata in data['players'].items():
                hand = userdata['cards'] = []
                userdata['points'] = 0
                while len(hand) < amount / player_num:
                    card = cards.pop(0)
                    hand.append(card)

            hand = data['players'][ctx.author]['cards']
            embed = self.show_hand(hand, ctx.prefix, True)
            resp = await utils.silencer(ctx.author.send(embed=embed))

            if resp is False:
                base = "**{}** konnte keine private Nachricht geschickt werden,\n" \
                       "**Spiel beendet**"
                msg = base.format(ctx.author.display_name)
                await begin.edit(content=msg)
                self.data.pop(ctx.guild.id)

            else:
                data['players'][ctx.author]['msg'] = resp
                await asyncio.sleep(3600)
                current = self.data.get(ctx.guild.id)
                if current and current['id'] == data['id']:
                    self.data.pop(ctx.guild.id)

    @commands.dm_only()
    @commands.command(name="play")
    async def play_(self, ctx, card_or_property):
        for guild_id, data in self.data.items():
            if data is False:
                continue
            if ctx.author in data['players']:
                break
        else:
            msg = "Du befindest dich in keiner Tribalcards-Runde"
            return await ctx.send(msg)

        userdata = data['players'][ctx.author]
        if ctx.author in data['played']:
            msg = "Du hast bereits eine Karte gespielt, warte auf die anderen Spieler"
            await ctx.send(msg)

        elif data['beginner'] == ctx.author:
            for attribute, name in prop.items():
                if attribute == "name":
                    continue
                if name.lower() == card_or_property.lower():
                    break
            else:
                msg = "Die angegebene Eigenschaft gibt es leider nicht"
                return await ctx.send(msg, delete_after=10)

            if data.get('last') == attribute:
                msg = "Die angegebene Eigeschaft wurde bereits in der letzten Runde verglichen"
                return await ctx.send(msg, delete_after=10)

            card = userdata['cards'].pop(0)
            data['played'][ctx.author] = card
            data['attribute'] = attribute
            data['last'] = attribute

            for player, playerdata in data['players'].items():
                if ctx.author == player:
                    msg = "Deine Eigenschaft wurde registriert, warte auf die anderen Spieler"
                    embed = playerdata['msg'].embeds[0]
                    embed.set_footer(text=msg)
                    await playerdata['msg'].edit(embed=embed)

                else:
                    base = "{} möchte {} vergleichen, wähle deine Karte mit {}play <number>"
                    msg = base.format(ctx.author.display_name, name, data['ctx'].bot.prefix)
                    embed = self.show_hand(playerdata['cards'], msg)
                    await player.send(embed=embed)

        else:
            if not data['played']:
                base = "Du musst warten bis sich {} für eine Eigenschaft entschieden hat"
                msg = base.format(data['beginner'].display_name)
                return await ctx.send(msg, delete_after=10)

            try:
                index = int(card_or_property) - 1
                card = userdata['cards'].pop(index)
            except (ValueError, IndexError):
                msg = "Bitte gebe eine gültige Kartennummer an"
                return await ctx.send(msg, delete_after=10)

            played = data['played']
            players = data['players']
            played[ctx.author] = card
            if len(players) != len(played):
                msg = "Deine Karte wurde registriert, warte auf die anderen Spieler"
                embed = userdata['msg'].embeds[0]
                embed.set_footer(text=msg)
                await userdata['msg'].edit(embed=embed)

            else:
                # compare and possible end
                ranking = []
                for user, dsobj in played.items():
                    value = getattr(dsobj, data['attribute'])
                    ranking.append([user, value])

                reverse = data['attribute'] not in ("rank", "id")
                ranking.sort(key=lambda dc: dc[1], reverse=reverse)

                winner = []
                embed = discord.Embed()
                for user, value in ranking:
                    if not winner:
                        winner.append([user, value])
                        players[user]['points'] += 1
                    elif winner[0][1] == value:
                        winner.append([user, value])

                    points = players[user]['points']
                    dsobj = utils.escape(played[user].name)
                    name = f"Karte von {user.display_name} ({points}):"
                    value = f"**{prop[data['attribute']]} von {dsobj}:** `{utils.pcv(value)}`"
                    embed.add_field(name=name, value=value, inline=False)

                base = "Warte bis {} sich für eine Eigenschaft entschieden hat"

                player = "**, **".join([tup[0].display_name for tup in winner])
                plural = "hat" if len(winner) == 1 else "haben"
                title = f"**{player}** {plural} die Runde gewonnen"
                embed.title = title

                beginner = winner[0][0]
                for member, _ in ranking:
                    if member in [m[0] for m in winner]:
                        embed.colour = discord.Color.green()
                    else:
                        embed.colour = discord.Color.red()
                        if userdata['cards']:
                            embed.set_footer(text=base.format(beginner.display_name))

                    await member.send(embed=embed)

                if userdata['cards']:
                    played.clear()
                    data['beginner'] = beginner
                    beginner_data = players[beginner]

                    prefix = data['ctx'].bot.prefix
                    embed = self.show_hand(beginner_data['cards'], prefix, True)
                    msg = await beginner.send(embed=embed)
                    beginner_data['msg'] = msg

                else:
                    ranking = []
                    for member, playerdata in players.items():
                        ranking.append([member, playerdata['points']])

                    ranking.sort(key=lambda dc: dc[1], reverse=True)

                    winners = []
                    represent = ""
                    winner, highest = ranking[0]
                    for member, points in ranking:
                        base = "\n`{}` | **{}**"
                        represent += base.format(points, member.display_name)

                        if points == highest:
                            price = highest * 4000
                            await self.bot.update_iron(member.id, price)
                            represent += f" `[{price} Eisen]`"
                            winners.append(member.display_name)

                    player = "**, **".join(winners)
                    plural = "hat" if len(winners) == 1 else "haben"
                    base = "**{}** {} das Tribalcards Spiel gewonnen!\n{}"
                    description = base.format(player, plural, represent)
                    embed = discord.Embed(description=description)
                    await data['ctx'].send(embed=embed)
                    self.data.pop(data['ctx'].guild.id)


def setup(bot):
    bot.add_cog(Card(bot))
