from abc import ABC
from discord import app_commands
import typing
import utils
from utils import DSInteraction
import utils.error as error
import re


class MemberConverter(app_commands.Transformer, ABC):
    __slots__ = ('id', 'name', 'display_name', 'avatar_url')

    async def transform(self, interaction, value):
        if re.match(r'<@!?([0-9]+)>$', value):
            raise error.DontPingMe

        member = interaction.client.get_member_by_name(interaction.guild.id, value)
        if member is not None:
            return member

        member = await interaction.guild.query_members(value)
        if member:
            return member[0]
        else:
            raise error.MemberNotFound(value)


class DSConverter(app_commands.Transformer):

    def __init__(self, ds_type=None):
        self.ds_type = ds_type

    __slots__ = ('id', 'x', 'y', 'world', 'url', 'alone',
                 'name', 'tag', 'tribe_id', 'villages',
                 'points', 'rank', 'player', 'att_bash',
                 'att_rank', 'def_bash', 'def_rank',
                 'all_bash', 'all_rank', 'sup_bash',
                 'member', 'all_points', 'mention',
                 'guest_url', 'ingame_url', 'twstats_url')

    async def autocomplete(self, interaction: DSInteraction, current):
        if interaction.server is None:
            return []

        cached_objects = await interaction.client.get_tribal_cache(interaction, self.ds_type)

        if self.ds_type is not None:
            attribute = 'name' if self.ds_type == 'player' else 'tag'

            return [app_commands.Choice(name=getattr(k, attribute), value=f"{k.id}_autocomplete")
                    for k in cached_objects.values() if current.lower() in getattr(k, attribute).lower()][:25]

        else:
            players, tribes = cached_objects
            cached_objects = list(players.values())
            cached_objects.extend(tribes.values())

            return [app_commands.Choice(name=getattr(k, 'tag', getattr(k, 'name')), value=f"{k.id}_autocomplete")
                    for k in cached_objects
                    if current.lower() in getattr(k, 'tag', getattr(k, 'name')).lower()][:25]

    async def transform(self, interaction: DSInteraction, value):
        if "_autocomplete" in value:
            obj_id = int(value.replace("_autocomplete", ""))

            if self.ds_type is not None:
                cache = getattr(interaction.client, f"{self.ds_type}s")
                obj_cache = cache.get(interaction.server, {})
                obj = obj_cache.get(obj_id)

            else:
                player_cache = interaction.client.players
                tribe_cache = interaction.client.tribes

                player_obj_cache = player_cache.get(interaction.server, {})
                tribe_obj_cache = tribe_cache.get(interaction.server, {})
                obj = player_obj_cache.get(obj_id, tribe_obj_cache.get(obj_id))

        elif self.ds_type is not None:
            func = getattr(interaction.client, f"fetch_{self.ds_type}")
            obj = await func(interaction.server, value, name=True)
        else:
            obj = await interaction.client.fetch_both(interaction.server, value)

        if not obj:
            raise error.DSUserNotFound(value)
        return obj


class WorldConverter(app_commands.Transformer):
    __slots__ = ('server', 'speed', 'unit_speed', 'moral',
                 'config', 'lang', 'number', 'title',
                 'domain', 'icon', 'show', 'guest_url')

    async def autocomplete(self, interaction: DSInteraction, current):
        worlds = list(interaction.client.worlds.keys())
        worlds.sort()

        return [app_commands.Choice(name=k, value=k)
                for k in worlds
                if current.lower() in k.lower()][:25]

    async def transform(self, interaction: DSInteraction, value):
        argument = value.lower()
        world = interaction.client.worlds.get(argument)

        if world is None:
            numbers = re.findall(r'\d+', argument)
            if numbers:
                for world in interaction.client.worlds:
                    if numbers[0] in world:
                        break

            raise error.UnknownWorld(world)

        else:
            return world


class CoordinateConverter(app_commands.Transformer, ABC):
    __slots__ = ('x', 'y')

    async def transform(self, interaction, value):
        return utils.Coordinate.from_str(value)


class CoordinatesConverter(app_commands.Transformer, ABC):
    async def transform(self, interaction, value) -> typing.Iterable[str]:
        raw_coords = re.findall(r'\d\d\d\|\d\d\d', value)
        return [utils.Coordinate.from_known_str(coord) for coord in raw_coords]


class ConversionKeyConverter(app_commands.Transformer, ABC):
    __slots__ = ('lower',)

    async def autocomplete(self, interaction: DSInteraction, current):
        keys = interaction.lang.converter_title.keys()

        return [app_commands.Choice(name=k, value=k)
                for k in keys
                if current.lower() in k.lower()]

    async def transform(self, interaction: DSInteraction, value):
        name = interaction.lang.converter_title.get(value.lower())

        if name is None:
            raise utils.MissingRequiredKey(interaction.lang.converter_title.keys())
        else:
            return name, value