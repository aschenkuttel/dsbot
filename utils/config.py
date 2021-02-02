import discord
import json


class Config:
    def __init__(self, bot):
        self._config = {}
        self.path = f"{bot.data_path}/config.json"
        self.setup()

    def setup(self):
        cache = json.load(open(self.path))
        self._config = {int(k): v for k, v in cache.items()}

    def save(self):
        json.dump(self._config, open(self.path, 'w'))

    def get(self, item, guild_id, default=None):
        config = self.get_config(guild_id)
        if config is None:
            return
        else:
            return config.get(item, default)

    def update(self, item, value, guild_id, bulk=False):
        config = self.get_config(guild_id, setup=True)
        config[item] = value

        if bulk is False:
            self.save()

    def remove(self, item, guild_id, bulk=False):
        config = self.get_config(guild_id)
        if config is None:
            return

        job = config.pop(item, None)
        if job is not None and bulk is False:
            self.save()

        return job

    def get_config(self, guild_id, setup=False):
        config = self._config.get(guild_id)

        if config is None and setup is True:
            config = self._config[guild_id] = {}

        return config

    def remove_config(self, guild_id):
        response = self._config.pop(guild_id, None)
        if response is not None:
            self.save()
            return True

    def get_world(self, channel):
        config = self._config.get(channel.guild.id)
        if config is None:
            return

        main_world = config.get('world')
        if main_world is None:
            return

        channel_config = config.get('channel', {})
        channel_world = channel_config.get(str(channel.id))
        return channel_world or main_world

    def get_related_world(self, obj):
        if isinstance(obj, discord.Guild):
            config = self._config.get(obj.id)
            if config is None:
                return

            return config.get('world')

        if isinstance(obj, discord.TextChannel):
            config = self._config.get(obj.guild.id)
            if config is None:
                return

            chan = config.get('channel', {})
            return chan.get(str(obj.id))

    def remove_world(self, world):
        for config in self._config.values():
            if config.get('world') == world:
                config.pop('world')

            channel = config.get('channel', {})
            for ch in channel.copy():
                if channel[ch] == world:
                    channel.pop(ch)

        self.save()

    def get_switch(self, key, guild_id):
        config = self._config.get(guild_id)
        if not config:
            return True

        switches = config.get('switches', {})
        return switches.get(key, True)

    def update_switch(self, key, guild_id, bulk=False):
        config = self.get_config(guild_id, setup=True)
        switches = config.get('switches')
        if switches is None:
            switches = config['switches'] = {}

        old = switches.get(key, True)
        switches[key] = not old

        if not bulk:
            self.save()

        return not old

    def get_prefix(self, guild_id):
        config = self._config.get(guild_id)

        if config is None:
            return
        else:
            return config.get('prefix')

    def get_conquer(self, ctx):
        conquer = self.get('conquer', ctx.guild.id)

        if conquer is None:
            return
        else:
            return conquer.get(str(ctx.channel.id))
