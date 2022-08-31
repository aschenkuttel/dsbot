from discord import app_commands
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
            "Utilities",
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
        desc = "Erhalte eine ausführliche Erklärung zu\n" \
               f"einzelnen Commands mit `{prefix}help <command>`"

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

        cmd_name = ctx.command.name
        cmd_description = ctx.lang.help[cmd_name]

        cmd_kwargs = ctx.lang.help.get(f"{cmd_name}_kwargs")
        if cmd_kwargs:
            cmd_description += f"\n\n{cmd_kwargs}\n"

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
        emb.set_footer(text="<> = benötigtes Argument\n[] = optionales Argument")
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

    @app_commands.command(name="commands")
    async def commands(self, ctx):
        pin = "pin" in ctx.message.content.lower()
        if pin and not ctx.author.guild_permissions.administrator:
            raise commands.MissingPermissions(['administrator'])

        if ctx.invoked_subcommand is not None:
            return

        embed = self.help_embed(ctx.prefix)
        await self.send_embed(ctx, embed)

    # help = app_commands.Group(name="help", description="xd")


async def setup(bot):
    await bot.add_cog(Help(bot))
