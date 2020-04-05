from discord.ext import commands
import discord
import utils


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config

    async def cog_check(self, ctx):
        if await self.bot.is_owner(ctx.author):
            return True
        raise commands.NotOwner

    @commands.command(name="presence")
    async def presence_(self, ctx, *, args):
        await self.bot.change_presence(status=discord.Status.online,
                                       activity=discord.Game(name=args))
        await ctx.send("Presence verändert")

    @commands.command(name="reload")
    async def reload_(self, ctx, cog):
        try:
            self.bot.reload_extension(f"cogs.{cog}")
            await ctx.send("Extension erfolgreich neu geladen")
            print("-- Extension reloaded --")
        except Exception as error:
            await ctx.send(error)

    @commands.command(name="guild_reset")
    async def guild_reset_(self, ctx, guild_id: int):
        response = self.bot.config.reset_guild(guild_id)
        if response:
            msg = "Serverdaten zurückgesetzt"
        else:
            msg = "Keine zugehörige Config gefunden"
        await ctx.send(msg)

    @commands.command(name="ursula")
    async def ursula_(self, ctx):
        await ctx.send(f"{len(ctx.bot.guilds)}")

    @commands.command(name="stats")
    async def stats_(self, ctx):
        data = await self.bot.get_usage()
        if not data:
            return
        result = [f"`{usage}` [{cmd}]" for cmd, usage in data]
        return await ctx.send(
            embed=discord.Embed(description='\n'.join(result)))

    @commands.command(name="change")
    async def change_(self, ctx, guild_id: int, item, value):
        if item.lower() not in ["prefix", "world", "game", "conquer"]:
            await ctx.send(embed=utils.error_embed("Fehlerhafte Eingabe"))
            return
        value = value if item == "prefix" else int(value)
        self.bot.config.change_item(guild_id, item, value)
        await ctx.send(f"`{item}` registriert")

    @commands.command(name="change_res")
    async def res_(self, ctx, idc: int, iron: int):
        await self.bot.update_iron(idc, iron)
        await ctx.send(f"Dem User wurden `{iron} Eisen` hinzugefügt")


def setup(bot):
    bot.add_cog(Admin(bot))
