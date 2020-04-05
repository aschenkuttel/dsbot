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

    def get_item(self, guild_id, item):
        config = self._config.get(guild_id)
        if config is None:
            return
        else:
            return config.get(item)

    def change_item(self, guild_id, item, value):
        if guild_id not in self._config:
            self._config[guild_id] = {}

        self._config[guild_id][item] = value
        self.save()

    def remove_item(self, guild_id, item):
        config = self._config.get(guild_id)
        if not config:
            return

        job = config.pop(item, None)
        if job is not None:
            self.save()

        return job

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

    def get_guild_world(self, guild):
        con = self._config.get(guild.id)
        if con is None:
            return
        else:
            return con.get('world')

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
        default = "?"
        if config is None:
            return default
        else:
            return config.get('prefix', default)

    def save(self):
        json.dump(self._config, open(self.path, 'w'))

    def reset_guild(self, guild_id):
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
