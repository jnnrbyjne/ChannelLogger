import discord
import asyncio
import datetime
import pytz
import csv
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

client = discord.Client(intents=intents)

# === CONFIGURATION ===
VOICE_CHANNEL_NAME = "GVG"
TIMEZONE = pytz.timezone("Europe/London")

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))

user_sessions = {}  # {username: join_time}
final_log = {}
has_logged_today = False

def is_tracking_time():
    now = datetime.datetime.now(TIMEZONE)
    return (
        now.hour == 14 and
        now.weekday() in [3, 6]  # Thursday (3), Sunday (6)
    )

def is_upload_time():
    now = datetime.datetime.now(TIMEZONE)
    return (
        now.hour == 15 and now.minute == 0 and
        now.weekday() in [3, 6]
    )

def now_london():
    return datetime.datetime.now(TIMEZONE)

def fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    client.loop.create_task(schedule_log_delivery())

@client.event
async def on_voice_state_update(member, before, after):
    if not is_tracking_time():
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

async def schedule_log_delivery():
    global has_logged_today
    await client.wait_until_ready()

    while not client.is_closed():
        now = now_london()

        if is_upload_time() and not has_logged_today:
            await finalize_log()
            await send_log_file()
            has_logged_today = True

        if now.hour == 0 and now.minute == 0:
            has_logged_today = False

        await asyncio.sleep(60)

async def finalize_log():
    end_time = datetime.datetime.combine(now_london().date(), datetime.time(15, 0)).replace(tzinfo=TIMEZONE)

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
        print("No users joined the GVG channel today.")
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
            content="📋 GVG attendance summary (2–3 PM UK time):",
            file=discord.File(fp=filename)
        )
        print("✅ Summary log sent.")
    else:
        print("❌ Log channel not found.")

    os.remove(filename)
    final_log.clear()

client.run(BOT_TOKEN)
