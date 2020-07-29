import discord
import json


class Config:
    def __init__(self, bot):
        self._config = {}
        self.bot = bot
        self.path = f"{bot.data_path}/config.json"
        self.load_config()

    def load_config(self):
        cache = json.load(open(self.path))
        data = {int(key): value for key, value in cache.items()}
        self._config.update(data)

    def get_config(self, guild_id, setup=False):
        config = self._config.get(guild_id)
        if config is None and setup:
            config = self._config[guild_id] = {}

        return config

    def get_item(self, guild_id, item, default=None):
        config = self.get_config(guild_id)
        if config is None:
            return default
        else:
            return config.get(item, default)

    def change_item(self, guild_id, item, value):
        config = self.get_config(guild_id, setup=True)
        config[item] = value
        self.save()

    def remove_item(self, guild_id, item, bulk=False):
        config = self.get_config(guild_id)
        if config is None:
            return

        job = config.pop(item, None)
        if job is not None and not bulk:
            self.save()

        return job

    def update_switch(self, guild_id, key):
        config = self.get_config(guild_id, setup=True)
        switches = config.get('switches')
        if switches is None:
            switches = config['switches'] = {}

        old = switches.get(key, True)
        switches[key] = not old
        self.save()

        return not old

    def get_switch(self, guild_id, key):
        config = self._config.get(guild_id)
        if not config:
            return True

        switches = config.get('switches', {})
        return switches.get(key, True)

    def get_world(self, channel):
        con = self._config.get(channel.guild.id)
        if con is None:
            return

        main = con.get('world')
        if not main:
            return

        chan = con.get('channel')
        idc = str(channel.id)
        world = chan.get(idc, main) if chan else main
        return world

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

            chan = config.get('channel')
            if chan:
                return chan.get(str(obj.id))

    def remove_world(self, world):
        for guild in self._config:
            config = self._config[guild]
            if config.get('world') == world:
                config.pop('world')

            channel = config.get('channel', {})
            for ch in channel.copy():
                if channel[ch] == world:
                    channel.pop(ch)

        self.save()

    def get_prefix(self, guild_id):
        config = self._config.get(guild_id)
        default = self.bot.prefix
        if config is None:
            return default
        else:
            return config.get('prefix', default)

    def save(self):
        json.dump(self._config, open(self.path, 'w'))

    def remove_guild(self, guild_id):
        if guild_id in self._config:
            self._config.pop(guild_id)
            self.save()
            return True


class Cache:
    def __init__(self, bot):
        self._cache = {}
        self.bot = bot
        self.path = f"{bot.data_path}/cache.json"
        self.load_cache()

    def load_cache(self):
        self._cache = json.load(open(self.path))

    def save(self):
        json.dump(self._cache, open(self.path, 'w'))

    def get(self, key, default=None):
        return self._cache.get(key, default)

    def set(self, key, value):
        self._cache[key] = value
        self.save()
