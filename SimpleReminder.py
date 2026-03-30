import discord
from discord.ext import commands, tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
import os
import json

# -------------------- KONFIGURACJA --------------------
TOKEN = os.environ.get("DISCORD_TOKEN") or "DISCORD_TOKEN"
SETTINGS_FILE = "settings.json"

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler()

# -------------------- USTAWIENIA --------------------
# Wczytaj ustawienia z pliku lub stwórz pusty słownik
try:
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        guild_settings = json.load(f)
except FileNotFoundError:
    guild_settings = {}

# -------------------- FUNKCJE --------------------
def save_settings():
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(guild_settings, f, indent=4, ensure_ascii=False)

async def send_reminder(guild_id):
    settings = guild_settings.get(str(guild_id))
    if not settings:
        return
    channel_id = settings.get("channel_id")
    message = settings.get("message", "Cześć! To jest Twoje przypomnienie.")
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(message)

def schedule_reminders():
    scheduler.remove_all_jobs()
    for guild_id, settings in guild_settings.items():
        freq = settings.get("frequency", "weekly")
        hour = settings.get("hour", 13)
        minute = settings.get("minute", 0)
        day = settings.get("day", "fri")
        
        if freq == "daily":
            trigger = CronTrigger(hour=hour, minute=minute)
        else:  # weekly
            trigger = CronTrigger(day_of_week=day, hour=hour, minute=minute)
        
        scheduler.add_job(lambda gid=guild_id: bot.loop.create_task(send_reminder(gid)), trigger)

# -------------------- PANEL INTERAKTYWNY --------------------
class ReminderModal(discord.ui.Modal, title="Edytuj treść przypomnienia"):
    message_input = discord.ui.TextInput(label="Treść wiadomości", style=discord.TextStyle.long)
    
    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = str(self.guild_id)
        guild_settings.setdefault(guild_id, {})
        guild_settings[guild_id]["message"] = self.message_input.value
        save_settings()
        await interaction.response.send_message(f"Treść przypomnienia ustawiona na:\n{self.message_input.value}", ephemeral=True)

class ReminderSettingsView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @discord.ui.select(
        placeholder="Wybierz kanał do przypomnień",
        options=[]
    )
    async def select_channel(self, interaction: discord.Interaction, select: discord.ui.Select):
        guild_id = str(self.guild_id)
        channel_id = int(select.values[0])
        guild_settings.setdefault(guild_id, {})
        guild_settings[guild_id]["channel_id"] = channel_id
        save_settings()
        schedule_reminders()
        await interaction.response.send_message(f"Kanał przypomnienia ustawiony na: <#{channel_id}>", ephemeral=True)

    @discord.ui.button(label="Edytuj treść", style=discord.ButtonStyle.primary)
    async def edit_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReminderModal(self.guild_id))

    @discord.ui.select(
        placeholder="Wybierz częstotliwość",
        options=[
            discord.SelectOption(label="Codziennie", value="daily"),
            discord.SelectOption(label="Co tydzień", value="weekly")
        ]
    )
    async def select_frequency(self, interaction: discord.Interaction, select: discord.ui.Select):
        guild_id = str(self.guild_id)
        guild_settings.setdefault(guild_id, {})
        guild_settings[guild_id]["frequency"] = select.values[0]
        save_settings()
        schedule_reminders()
        await interaction.response.send_message(f"Częstotliwość ustawiona na: {select.values[0]}", ephemeral=True)

    @discord.ui.select(
        placeholder="Wybierz dzień tygodnia",
        options=[
            discord.SelectOption(label="Poniedziałek", value="mon"),
            discord.SelectOption(label="Wtorek", value="tue"),
            discord.SelectOption(label="Środa", value="wed"),
            discord.SelectOption(label="Czwartek", value="thu"),
            discord.SelectOption(label="Piątek", value="fri"),
            discord.SelectOption(label="Sobota", value="sat"),
            discord.SelectOption(label="Niedziela", value="sun")
        ]
    )
    async def select_day(self, interaction: discord.Interaction, select: discord.ui.Select):
        guild_id = str(self.guild_id)
        guild_settings.setdefault(guild_id, {})
        guild_settings[guild_id]["day"] = select.values[0]
        save_settings()
        schedule_reminders()
        await interaction.response.send_message(f"Dzień przypomnienia ustawiony na: {select.values[0]}", ephemeral=True)

    @discord.ui.select(
        placeholder="Wybierz godzinę",
        options=[discord.SelectOption(label=f"{i:02d}:00", value=str(i)) for i in range(24)]
    )
    async def select_hour(self, interaction: discord.Interaction, select: discord.ui.Select):
        guild_id = str(self.guild_id)
        guild_settings.setdefault(guild_id, {})
        guild_settings[guild_id]["hour"] = int(select.values[0])
        save_settings()
        schedule_reminders()
        hour = guild_settings[guild_id]["hour"]
        minute = guild_settings[guild_id].get("minute", 0)
        await interaction.response.send_message(f"Godzina przypomnienia ustawiona na: {hour:02d}:{minute:02d}", ephemeral=True)

    @discord.ui.select(
        placeholder="Wybierz minutę",
        options=[discord.SelectOption(label=f"{i:02d}", value=str(i)) for i in range(0,60,5)]
    )
    async def select_minute(self, interaction: discord.Interaction, select: discord.ui.Select):
        guild_id = str(self.guild_id)
        guild_settings.setdefault(guild_id, {})
        guild_settings[guild_id]["minute"] = int(select.values[0])
        save_settings()
        schedule_reminders()
        hour = guild_settings[guild_id].get("hour", 13)
        minute = guild_settings[guild_id]["minute"]
        await interaction.response.send_message(f"Minuta przypomnienia ustawiona na: {hour:02d}:{minute:02d}", ephemeral=True)

# -------------------- SLASH COMMAND --------------------
@bot.tree.command(name="reminder_panel", description="Otwórz panel do ustawień przypomnienia")
async def reminder_panel(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    view = ReminderSettingsView(guild_id)

    # Ustaw opcje kanałów dynamicznie
    channel_options = []
    for ch in interaction.guild.text_channels:
        channel_options.append(discord.SelectOption(label=ch.name, value=str(ch.id)))
    view.select_channel.options = channel_options

    await interaction.response.send_message("Panel ustawień przypomnienia:", view=view, ephemeral=True)

# -------------------- EVENT READY --------------------
@bot.event
async def on_ready():
    scheduler.start()
    schedule_reminders()
    await bot.tree.sync()
    print(f"Bot zalogowany jako {bot.user}")

# -------------------- URUCHOMIENIE --------------------
bot.run(TOKEN)