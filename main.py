import discord
from discord import app_commands
from discord.ext import commands
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

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
VOICE_CHANNEL_NAME = "GVG"
TIMEZONE = pytz.timezone("Europe/London")
ADMIN_ROLE_ID = 1349496161936867359  # Replace with your actual role ID

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

user_sessions = {}  # display_name: list of (join, leave) tuples
tracking_active = False


def fmt(dt):
return dt.strftime("%Y-%m-%d %H:%M:%S")


def now_london():
return datetime.datetime.now(TIMEZONE)


def tracking_window_for_today():
now = now_london()
weekday = now.weekday()  # Monday = 0, Sunday = 6
if weekday in [3, 6]:  # Thursday or Sunday
start = now.replace(hour=14, minute=0, second=0, microsecond=0)
end = now.replace(hour=15, minute=0, second=0, microsecond=0)
return start, end
return None, None


def is_tracking_day():
weekday = now_london().weekday()
return weekday in [3, 6]  # Thursday or Sunday


def has_admin_role(interaction: discord.Interaction):
return any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles)


@bot.event
async def on_ready():
print(f"✅ Logged in as {bot.user}")
try:
synced = await tree.sync()
print(f"✅ Synced {len(synced)} command(s).")
except Exception as e:
print(f"❌ Error syncing commands: {e}")


@tree.command(name="startgvg", description="Start tracking GVG attendance")
@app_commands.check(has_admin_role)
async def startgvg(interaction: discord.Interaction):
global tracking_active, user_sessions
tracking_active = True
user_sessions = {}

    await interaction.response.send_message("📢 GVG tracking has started.", ephemeral=True)  # RESPOND FIRST

    # Then continue the logic
guild = interaction.guild
voice_channel = discord.utils.get(guild.voice_channels, name=VOICE_CHANNEL_NAME)
now = now_london()
if voice_channel:
for member in voice_channel.members:
user_sessions[member.display_name] = [(now, None)]
print(f"{member.display_name} was already in channel at {fmt(now)}")

    await interaction.response.send_message("📢 GVG tracking has started.", ephemeral=True)
print("✅ GVG tracking started.")


@tree.command(name="endgvg", description="End tracking and send attendance log")
@app_commands.check(has_admin_role)
async def endgvg(interaction: discord.Interaction):
global tracking_active
tracking_active = False
await finalize_log()
await interaction.response.send_message("📋 GVG log has been generated and sent.", ephemeral=True)
print("✅ GVG tracking ended and log sent.")


@bot.event
async def on_voice_state_update(member, before, after):
if not tracking_active:
return

now = now_london()
name = member.display_name

if after.channel and after.channel.name == VOICE_CHANNEL_NAME and (
before.channel is None or before.channel.id != after.channel.id
):
if name not in user_sessions:
user_sessions[name] = []
user_sessions[name].append((now, None))
print(f"{name} joined at {fmt(now)}")

elif before.channel and before.channel.name == VOICE_CHANNEL_NAME and (
after.channel is None or after.channel.id != before.channel.id
):
if name in user_sessions and user_sessions[name][-1][1] is None:
user_sessions[name][-1] = (user_sessions[name][-1][0], now)
print(f"{name} left at {fmt(now)}")


async def finalize_log():
now = now_london()
start, end = tracking_window_for_today()
final_log = {}

for name, sessions in user_sessions.items():
total_time = datetime.timedelta()
for join, leave in sessions:
if leave is None:
leave = now

if start and end:
# Only count time within 2–3 PM on Thursday or Sunday
join_clamped = max(join, start)
leave_clamped = min(leave, end)
if join_clamped < leave_clamped:
total_time += (leave_clamped - join_clamped)
else:
# Count full session on other days
total_time += (leave - join)

if total_time.total_seconds() > 0:
final_log[name] = {
"Joined At": fmt(start if start else sessions[0][0]),
"Left At": fmt(end if end else sessions[-1][1] or now),
"Duration": str(total_time).split(".")[0]
}

if final_log:
await send_log_file(final_log)
else:
print("ℹ️ No valid attendance to log.")


async def send_log_file(log_data):
filename = "gvg_manual_log.csv"
with open(filename, "w", newline='', encoding="utf-8") as f:
writer = csv.DictWriter(f, fieldnames=["User", "Joined At", "Left At", "Duration"])
writer.writeheader()
for user, data in log_data.items():
row = {"User": user}
row.update(data)
writer.writerow(row)

channel = bot.get_channel(LOG_CHANNEL_ID)
if channel:
await channel.send(
content="📋 GVG attendance log:",
file=discord.File(fp=filename)
)
print("✅ Log sent.")
else:
print("❌ Log channel not found.")

os.remove(filename)


@tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
if isinstance(error, app_commands.errors.CheckFailure):
await interaction.response.send_message(
"❌ You don't have permission to use this command (ADMIN role required).",
ephemeral=True
)

bot.run(TOKEN)

from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

bot.run(TOKEN)
