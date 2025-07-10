import discord
from discord.ext import commands
from discord import app_commands
import datetime
import pytz
import csv
import os
from dotenv import load_dotenv

load_dotenv()

# === CONFIGURATION ===
VOICE_CHANNEL_NAME = "GVG"
TIMEZONE = pytz.timezone("Europe/London")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))

intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
intents.members = True

client = commands.Bot(command_prefix="!", intents=intents)
tree = app_commands.CommandTree(client)

user_sessions = {}  # {username: join_time}
final_log = {}
tracking_active = False

def now_london():
    return datetime.datetime.now(TIMEZONE)

def fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")

@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {client.user}")

@tree.command(name="start_attendance", description="Start tracking GVG attendance")
async def start_attendance(interaction: discord.Interaction):
    global tracking_active, user_sessions, final_log

    if tracking_active:
        await interaction.response.send_message("⚠️ Tracking is already active.")
        return

    tracking_active = True
    user_sessions.clear()
    final_log.clear()

    await interaction.response.send_message("✅ Started tracking attendance.")

    # Capture users already in the voice channel
    guild = interaction.guild
    voice_channel = discord.utils.get(guild.voice_channels, name=VOICE_CHANNEL_NAME)

    if voice_channel:
        now = now_london()
        for member in voice_channel.members:
            user_sessions[str(member)] = now
            print(f"{member} already in voice channel — marked as joined at {fmt(now)}")

@tree.command(name="end_attendance", description="Stop tracking and send CSV log")
async def end_attendance(interaction: discord.Interaction):
    global tracking_active

    if not tracking_active:
        await interaction.response.send_message("⚠️ Tracking is not active.")
        return

    await finalize_log()
    await send_log_file()
    tracking_active = False
    await interaction.response.send_message("📤 Attendance log finalized and sent.")

@client.event
async def on_voice_state_update(member, before, after):
    if not tracking_active:
        return

    username = str(member)
    now = now_london()

    # Joined GVG
    if (after.channel and after.channel.name == VOICE_CHANNEL_NAME and
        (before.channel is None or before.channel.id != after.channel.id)):

        if username not in user_sessions:
            user_sessions[username] = now
            print(f"{username} joined at {fmt(now)}")

    # Left GVG
    elif (before.channel and before.channel.name == VOICE_CHANNEL_NAME and
          (after.channel is None or after.channel.id != before.channel.id)):

        if username in user_sessions:
            joined_at = user_sessions.pop(username)
            duration = now - joined_at
            final_log[username] = {
                "Joined At": fmt(joined_at),
                "Left At": fmt(now),
                "Duration": str(duration).split(".")[0]
            }
            print(f"{username} left at {fmt(now)} — stayed {duration}")

async def finalize_log():
    # Mark users still in the channel
    end_time = now_london()
    for username, joined_at in user_sessions.items():
        duration = end_time - joined_at
        final_log[username] = {
            "Joined At": fmt(joined_at),
            "Left At": fmt(end_time),
            "Duration": str(duration).split(".")[0]
        }
    user_sessions.clear()

async def send_log_file():
    if not final_log:
        print("No users to log.")
        return

    filename = "voice_summary.csv"
    with open(filename, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["User", "Joined At", "Left At", "Duration"])
        writer.writeheader()
        for user, data in final_log.items():
            row = {"User": user}
            row.update(data)
            writer.writerow(row)

    channel = client.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(
            content="📋 GVG attendance summary:",
            file=discord.File(fp=filename)
        )
        print("✅ Log sent.")
    else:
        print("❌ Log channel not found.")

    os.remove(filename)
    final_log.clear()

client.run(BOT_TOKEN)
