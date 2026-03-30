

import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
import os

# -------------------- KONFIGURACJA --------------------
# Token bota - zalecane użycie zmiennej środowiskowej DISCORD_TOKEN
TOKEN = os.environ.get("DISCORD_TOKEN") or "DISCORD_TOKEN"
CHANNEL_ID = 1488141879668113492  # Wstaw ID kanału, w którym mają być przypomnienia

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler = AsyncIOScheduler()

# -------------------- DOMYŚLNE USTAWIENIA --------------------
reminder_message = "Cześć! To jest Twoje przypomnienie."
reminder_hour = 13
reminder_minute = 0
reminder_day = "fri"
reminder_frequency = "weekly"  # "daily" lub "weekly"

# -------------------- FUNKCJE --------------------
async def send_reminder():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(reminder_message)

def schedule_reminder():
    scheduler.remove_all_jobs()
    if reminder_frequency == "daily":
        trigger = CronTrigger(hour=reminder_hour, minute=reminder_minute)
    elif reminder_frequency == "weekly":
        trigger = CronTrigger(day_of_week=reminder_day, hour=reminder_hour, minute=reminder_minute)
    
    # Ważna poprawka: użycie bot.loop.create_task dla coroutine
    scheduler.add_job(lambda: bot.loop.create_task(send_reminder()), trigger)

# -------------------- PANEL INTERAKTYWNY --------------------
class ReminderModal(discord.ui.Modal, title="Edytuj treść przypomnienia"):
    message_input = discord.ui.TextInput(label="Treść", style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction):
        global reminder_message
        reminder_message = self.message_input.value
        await interaction.response.send_message(
            f"Treść przypomnienia zmieniona na:\n{reminder_message}", ephemeral=True
        )

class ReminderSettingsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # brak limitu czasu

    @discord.ui.button(label="Edytuj treść", style=discord.ButtonStyle.primary)
    async def edit_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReminderModal())

    @discord.ui.select(
        placeholder="Wybierz częstotliwość",
        options=[
            discord.SelectOption(label="Codziennie", value="daily"),
            discord.SelectOption(label="Co tydzień", value="weekly")
        ]
    )
    async def select_frequency(self, interaction: discord.Interaction, select: discord.ui.Select):
        global reminder_frequency
        reminder_frequency = select.values[0]
        schedule_reminder()
        await interaction.response.send_message(f"Częstotliwość ustawiona na: {reminder_frequency}", ephemeral=True)

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
        global reminder_day
        reminder_day = select.values[0]
        schedule_reminder()
        await interaction.response.send_message(f"Dzień przypomnienia ustawiony na: {reminder_day}", ephemeral=True)

    @discord.ui.select(
        placeholder="Wybierz godzinę",
        options=[discord.SelectOption(label=f"{i:02d}:00", value=str(i)) for i in range(0,24)]
    )
    async def select_hour(self, interaction: discord.Interaction, select: discord.ui.Select):
        global reminder_hour
        reminder_hour = int(select.values[0])
        schedule_reminder()
        await interaction.response.send_message(f"Godzina przypomnienia ustawiona na: {reminder_hour:02d}:{reminder_minute:02d}", ephemeral=True)

    @discord.ui.select(
        placeholder="Wybierz minutę",
        options=[discord.SelectOption(label=f"{i:02d}", value=str(i)) for i in range(0,60,5)]
    )
    async def select_minute(self, interaction: discord.Interaction, select: discord.ui.Select):
        global reminder_minute
        reminder_minute = int(select.values[0])
        schedule_reminder()
        await interaction.response.send_message(f"Minuta przypomnienia ustawiona na: {reminder_hour:02d}:{reminder_minute:02d}", ephemeral=True)

# -------------------- SLASH COMMAND --------------------
@bot.tree.command(name="reminder_panel", description="Otwórz panel do ustawień przypomnienia")
async def reminder_panel(interaction: discord.Interaction):
    view = ReminderSettingsView()
    await interaction.response.send_message("Panel ustawień przypomnienia:", view=view, ephemeral=True)

# -------------------- EVENT READY --------------------
@bot.event
async def on_ready():
    scheduler.start()
    await bot.tree.sync()
    schedule_reminder()
    print(f"Bot zalogowany jako {bot.user}")

# -------------------- URUCHOMIENIE --------------------
bot.run(TOKEN)