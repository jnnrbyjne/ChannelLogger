import discord
import datetime
import asyncio
import csv
import os
import pytz
from dotenv import load_dotenv

load_dotenv()

# ====== CONFIG ======
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Set this in Render environment variables
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))  # Set this in Render environment variables
VOICE_CHANNEL_NAME = "Test Channel"  # TEMP for testing
TIMEZONE = pytz.timezone("Europe/London")

# ====== TRACKING DATA ======
tracked_users = {}  # {user_id: join_time}
log_data = []  # list of dicts: [{'name': ..., 'duration_minutes': ...}]

intents = discord.Intents.default()
intents.message_content = False
intents.voice_states = True
intents.members = True  # Required for voice tracking

client = discord.Client(intents=intents)

# ====== Voice Tracking ======
@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

@client.event
async def on_voice_state_update(member, before, after):
    now = datetime.datetime.now(TIMEZONE)

    # Only care about our test channel
    if before.channel != after.channel:
        voice_channel = discord.utils.get(member.guild.voice_channels, name=VOICE_CHANNEL_NAME)

        # Joined the target channel
        if after.channel == voice_channel:
            tracked_users[member.id] = now
            print(f"🔵 {member.display_name} joined at {now.time()}")

        # Left the target channel
        if before.channel == voice_channel and member.id in tracked_users:
            join_time = tracked_users.pop(member.id)
            duration = (now - join_time).total_seconds() / 60
            log_data.append({
                "Name": member.display_name,
                "Joined at": join_time.strftime("%H:%M:%S"),
                "Left at": now.strftime("%H:%M:%S"),
                "Duration (minutes)": round(duration, 2)
            })
            print(f"🔴 {member.display_name} left at {now.time()}, stayed {round(duration,2)} min")

# ====== Log File Management ======
async def finalize_log():
    if not log_data:
        print("⚠️ No data to log.")
        return

    with open("voice_log.csv", mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=log_data[0].keys())
        writer.writeheader()
        writer.writerows(log_data)
    print("📄 voice_log.csv saved.")

async def send_log_file():
    try:
        channel = client.get_channel(LOG_CHANNEL_ID)
        if channel is None:
            print("❌ Log channel not found. Check LOG_CHANNEL_ID.")
            return
        if not os.path.exists("voice_log.csv"):
            print("❌ voice_log.csv not found.")
            return
        await channel.send(
            content="📄 GVG Voice Log:",
            file=discord.File("voice_log.csv")
        )
        print("✅ Sent voice_log.csv to channel.")
    except Exception as e:
        print(f"❌ Failed to send log file: {e}")

# ====== Force Upload On Startup (for testing) ======
async def force_upload():
    await client.wait_until_ready()
    print("🔁 Forcing log upload...")
    await finalize_log()
    await send_log_file()
    print("✅ Log upload triggered.")

client.loop.create_task(force_upload())

# ====== Start Bot ======
client.run(BOT_TOKEN)
