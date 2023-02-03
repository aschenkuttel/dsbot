from discord.ext import commands
from discord import app_commands
from datetime import datetime
from discord.ui import TextInput, Modal
import dateparser
import asyncio
import discord
import logging
import utils

logger = logging.getLogger('dsbot')


class Timer:
    def __init__(self, bot, data):
        self.bot = bot
        self.id = data['id']
        self.author_id = data['author_id']
        self.channel_id = data['channel_id']
        self.creation = data['creation']
        self.expiration = data['expiration']
        self.reason = data['reason']

    @classmethod
    def from_arguments(cls, bot, arguments):
        self = cls.__new__(cls)
        self.bot = bot
        self.id = 0
        self.author_id, self.channel_id = arguments[:2]
        self.creation, self.expiration = arguments[2:4]
        self.reason = arguments[4]
        return self

    async def send(self):
        embed = discord.Embed(colour=discord.Color.dark_gold())
        embed.description = self.reason

        channel = self.bot.get_channel(self.channel_id)
        author = await self.bot.fetch_user(self.author_id)

        if author is None:
            return

        if channel is None:
            channel = author

        try:
            msg = f"**Erinnerung:** {author.mention}"
            await channel.send(msg, embed=embed)
            logger.debug(f"reminder {self.id}: successfull")

        except (discord.Forbidden, discord.HTTPException):
            logger.debug(f"reminder {self.id}: not allowed")
            return


class ReminderModal(Modal):
    def __init__(self, callback):
        super().__init__(title="Reminder")
        self.callback = callback

    time_input = TextInput(label="Erinner mich an/in")
    reason_input = TextInput(label="Grund", style=discord.TextStyle.long, required=False)

    async def on_submit(self, interaction):
        await self.callback(interaction, self.time_input.value, self.reason_input.value)

    async def on_error(self, interaction, error):
        pass


class Reminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.type = 2
        self.char_limit = 200
        self.set = {'PREFER_DATES_FROM': "future"}
        self.preset = "%d.%m.%Y | %H:%M:%S Uhr"
        self._task = self.bot.loop.create_task(self.remind_loop())
        self._lock = asyncio.Event(loop=bot.loop)
        self.current_reminder = None

    def cog_unload(self):
        self._task.cancel()

    def restart(self, reminder=None):
        self._task.cancel()

        if reminder is None:
            self._lock.clear()

        self.current_reminder = reminder
        self._task = self.bot.loop.create_task(self.remind_loop())

    async def remind_loop(self):
        await self.bot.wait_until_unlocked()
        while not self.bot.is_closed():

            if not self.current_reminder:
                query = 'SELECT * FROM reminder ORDER BY expiration'
                async with self.bot.member_pool.acquire() as conn:
                    data = await conn.fetchrow(query)

                    if data is not None:
                        self.current_reminder = Timer(self.bot, data)

            if self.current_reminder:
                logger.debug(f"reminder {self.current_reminder.id}: sleeping")

                difference = (self.current_reminder.expiration - datetime.now())
                seconds = difference.total_seconds()
                await asyncio.sleep(seconds)

                query = "DELETE FROM reminder WHERE id = $1"
                async with self.bot.member_pool.acquire() as conn:
                    await conn.execute(query, self.current_reminder.id)

                if seconds > -60:
                    logger.debug(f"reminder {self.current_reminder.id}: send message")
                    await self.current_reminder.send()

                self.current_reminder = None
                self._lock.clear()

            else:
                await self._lock.wait()

    async def save_reminder(self, interaction: discord.Interaction, raw_time, raw_reason):
        if raw_reason:
            reason = raw_reason.strip()[:self.char_limit]
        else:
            reason = "Kein Grund angegeben"

        kwargs = {'locales': ["de-BE"], 'settings': self.set}
        expected_date = dateparser.parse(raw_time, **kwargs)

        if expected_date is None:
            msg = "Es konnte kein gültiges Zeitformat erkannt werden"
            await interaction.response.send_message(embed=utils.error_embed(msg))
            return

        current_date = datetime.now()
        difference = (expected_date - current_date).total_seconds()

        embed = discord.Embed(colour=discord.Color.green())
        embed.description = "**Erinnerung registriert:**"
        represent = expected_date.strftime(self.preset)
        embed.set_footer(text=represent)

        if difference < 0:
            msg = "Der Zeitpunkt ist bereits vergangen"
            await interaction.response.send_message(embed=utils.error_embed(msg))
            return

        arguments = [interaction.user.id, interaction.channel.id, current_date, expected_date, reason]
        reminder = Timer.from_arguments(self.bot, arguments)

        if difference < 60:
            await interaction.response.send_message(embed=embed)
            await asyncio.sleep(difference)
            await reminder.send()

        else:
            query = 'INSERT INTO reminder ' \
                    '(author_id, channel_id, creation, expiration, reason)' \
                    ' VALUES ($1, $2, $3, $4, $5) RETURNING id'
            async with self.bot.member_pool.acquire() as conn:
                resp = await conn.fetchrow(query, *arguments)
                reminder.id = resp['id']

            if not self.current_reminder:
                self.current_reminder = reminder
                self._lock.set()

            else:
                if reminder.expiration < self.current_reminder.expiration:
                    self.restart(reminder)

            logger.debug(f"reminder {resp['id']}: registered")
            embed.description = f"{embed.description[:-3]} (ID {resp['id']}):**"
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="remind", description="Lass dich vom Bot zu einer gewünschten Zeit erinnern")
    @utils.bot_has_permissions(send_messages=True, embed_links=True)
    async def remind(self, interaction):
        modal = ReminderModal(self.save_reminder)
        await interaction.response.send_modal(modal)

    reminder = app_commands.Group(name="reminder", description="xd")

    @reminder.command(name="list", description="All deine aktiven Reminder")
    async def list(self, interaction):
        query = 'SELECT * FROM reminder WHERE author_id = $1 ORDER BY expiration'
        async with self.bot.member_pool.acquire() as conn:
            data = await conn.fetch(query, interaction.user.id)

        if not data:
            msg = "Du hast keine aktiven Reminder"
            await interaction.response.send_message(embed=utils.error_embed(msg))

        else:
            reminders = []
            for row in data[:10]:
                timer = Timer(self.bot, row)
                date = timer.expiration.strftime(self.preset)
                reminders.append(f"`ID {timer.id}` | **{date}**")

            title = f"Deine Reminder ({len(data)} Insgesamt):"
            embed = discord.Embed(description="\n".join(reminders), title=title)
            await interaction.response.send_message(embed=embed)

    @reminder.command(name="remove", description="Lösche einen bestimmten Reminder mit der ID")
    async def remove(self, interaction, reminder_id: int):
        query = 'DELETE FROM reminder WHERE author_id = $1 AND id = $2'
        async with self.bot.member_pool.acquire() as conn:
            response = await conn.execute(query, interaction.user.id, reminder_id)

        if response == "DELETE 0":
            msg = "Du hast keinen Reminder mit der angegebenen ID"
            await interaction.response.send_message(embed=utils.error_embed(msg))
            return

        if self.current_reminder and self.current_reminder.id == reminder_id:
            self.restart()

        embed = utils.complete_embed("Der Reminder wurde gelöscht")
        await interaction.response.send_message(embed=embed)

    @reminder.command(name="clear", description="Lösche all deine aktiven Reminder")
    async def clear(self, interaction):
        query = 'DELETE FROM reminder WHERE author_id = $1 RETURNING id'
        async with self.bot.member_pool.acquire() as conn:
            deleted_rows = await conn.fetch(query, interaction.user.id)

        if not deleted_rows:
            msg = "Du hast keine aktiven Reminder"
            await interaction.response.send_message(embed=utils.error_embed(msg))
            return

        if self.current_reminder:
            old_ids = [rec['id'] for rec in deleted_rows]
            if self.current_reminder.id in old_ids:
                self.restart()

        msg = f"Alle deine Reminder wurden gelöscht ({len(deleted_rows)})"
        await interaction.response.send_message(embed=utils.complete_embed(msg))


async def setup(bot):
    await bot.add_cog(Reminder(bot))
