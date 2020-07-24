from utils.error import DontPingMe, MemberConverterNotFound, DSUserNotFound, UnknownWorld
from utils.classes import DSWorld
from discord.ext import commands
import re


class MemberConverter(commands.Converter):
    __slots__ = ('id', 'name', 'display_name', 'avatar_url')

    async def convert(self, ctx, arg):
        if re.match(r'<@!?([0-9]+)>$', arg):
            raise DontPingMe
        name = arg.lower()
        for m in ctx.guild.members:
            if name == m.display_name.lower():
                return m
            if name == m.name.lower():
                return m
        else:
            raise MemberConverterNotFound(arg)


class DSConverter(commands.Converter):

    def __init__(self, ds_type=None):
        self.type = ds_type

    __slots__ = ('id', 'x', 'y', 'world', 'url', 'alone',
                 'name', 'tag', 'tribe_id', 'villages',
                 'points', 'rank', 'player', 'att_bash',
                 'att_rank', 'def_bash', 'def_rank',
                 'all_bash', 'all_rank', 'sup_bash',
                 'member', 'all_points', 'mention',
                 'guest_url', 'ingame_url', 'twstats_url')

    async def convert(self, ctx, argument):
        if self.type:
            func = getattr(ctx.bot, f"fetch_{self.type}")
            obj = await func(ctx.server, argument, name=True)
        else:
            obj = await ctx.bot.fetch_both(ctx.server, argument)

        if not obj:
            raise DSUserNotFound(argument)
        return obj


class WorldConverter(commands.Converter):
    __slots__ = ('server', 'speed', 'unit_speed', 'moral',
                 'config', 'lang', 'number', 'title',
                 'domain', 'icon', 'show', 'guest_url')

    async def convert(self, ctx, argument):
        argument = argument.lower()
        world = ctx.bot.worlds.get(argument)

        if world is None:
            numbers = re.findall(r'\d+', argument)
            if numbers:
                for world in ctx.bot.worlds:
                    if numbers[0] in world:
                        break

            raise UnknownWorld(world)

        else:
            return world


class TimeConverter(commands.Converter):
    def __init__(self):
        pass

    async def convert(self, ctx, arguments):
        pass
