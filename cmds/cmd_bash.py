from utils import pcv, error_embed
from discord.ext import commands
from load import load, DSObject
import discord
import asyncio


def compare(bash_data1, bash_data2):
    if bash_data1 == bash_data2:
        msg = f"{pcv(bash_data1)} :left_right_arrow: {pcv(bash_data2)}"
    elif bash_data1 > bash_data2:
        msg = f"{pcv(bash_data1)} :arrow_left: {pcv(bash_data2)}"
    else:
        msg = f"{pcv(bash_data1)} :arrow_right: {pcv(bash_data2)}"
    return discord.Embed(description=msg)


class Bash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="bash")
    async def bash(self, ctx, *, user: DSObject):

        msg = await ctx.send(f"Besiegte Gegner von: `{user.name}`")
        await asyncio.sleep(3)
        await msg.edit(content=f"Als Angreifer: `{pcv(user.att_bash)} Bashpoints`")
        await asyncio.sleep(3)
        await msg.edit(content=f"Als Verteidiger: `{pcv(user.def_bash)} Bashpoints`")
        await asyncio.sleep(3)
        if user.alone:
            await msg.edit(content=f"Als Unterstützer: `{pcv(user.ut_bash)} Bashpoints`")
            await asyncio.sleep(3)
        return await msg.edit(content=f"Insgesamt: `{pcv(user.all_bash)} Bashpoints`")

    @commands.command(name="allbash", aliases=["offbash", "defbash", "utbash"])
    async def allbash(self, ctx, *, args):

        if not args.__contains__("/"):
            msg = "Du musst die beiden Spielernamen mit `/` trennen."
            return await ctx.send(msg)

        player1 = args.partition("/")[0].strip()
        player2 = args.partition("/")[2].strip()

        if player1.lower() == player2.lower():
            await ctx.send("Dein Witz :arrow_right: Unlustig")

        else:

            world = load.get_world(ctx.channel)
            s1 = await load.find_both_data(player1, world)
            s2 = await load.find_both_data(player2, world)

            if not s1 and not s2:
                msg = f"Auf der `{world}` gibt es weder einen Stamm noch " \
                    f"einen Spieler, der `{player1}` oder `{player2}` heißt."
                await ctx.send(msg)

            if not s1 or not s2:
                player = player1 if not s1 else player2
                msg = f"Auf der `{world}` gibt es einen Stamm oder Spieler " \
                    f"namens `{player}` nicht!"
                await ctx.send(msg)

            # ----- Defensive Bashpoints -----#
            elif ctx.invoked_with == "defbash":
                await ctx.send(embed=compare(s1.def_bash, s2.def_bash))

            # ----- Offensive Bashpoints -----#
            elif ctx.invoked_with == "offbash":
                await ctx.send(embed=compare(s1.att_bash, s2.att_bash))

            # ----- Support Bashpoints -----#
            elif ctx.invoked_with == "utbash":
                await ctx.send(embed=compare(s1.ut_bash, s2.ut_bash))

            # ----- All Bashpoints -----#
            else:
                await ctx.send(embed=compare(s1.all_bash, s2.all_bash))

    @bash.error
    async def bash_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=error_embed(f"Der gewünschte Spieler/Stamm fehlt."))

    @allbash.error
    async def allbash_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=error_embed(f"Die gewünschten Spieler/Stämme fehlen."))


def setup(bot):
    bot.add_cog(Bash(bot))
