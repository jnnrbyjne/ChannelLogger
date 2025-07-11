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
ADMIN_ROLE_ID = 1349496161936867359  # <-- Replace with your actual ADMIN role ID

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

user_sessions = {}  # display_name: join_time
final_log = {}
tracking_active = False


def fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def now_london():
    return datetime.datetime.now(TIMEZONE)


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
    global tracking_active, user_sessions, final_log
    tracking_active = True
    user_sessions = {}
    final_log = {}

    # Capture users already in the GVG channel
    guild = interaction.guild
    voice_channel = discord.utils.get(guild.voice_channels, name=VOICE_CHANNEL_NAME)
    if voice_channel:
        now = now_london()
        for member in voice_channel.members:
            user_sessions[member.display_name] = now
            print(f"{member.display_name} was already in channel at {fmt(now)}")

    await interaction.response.send_message("📢 GVG tracking has started.", ephemeral=True)
    print("✅ GVG tracking started.")


@tree.command(name="endgvg", description="End tracking and send attendance log")
@app_commands.check(has_admin_role)
async def endgvg(interaction: discord.Interaction):
    global tracking_active
    tracking_active = False
    await finalize_log()
    await send_log_file()
    await interaction.response.send_message("📋 GVG log has been generated and sent.", ephemeral=True)
    print("✅ GVG tracking ended and log sent.")


@bot.event
async def on_voice_state_update(member, before, after):
    if not tracking_active:
        return

    display_name = member.display_name
    now = now_london()

    # Joined GVG
    if (after.channel and after.channel.name == VOICE_CHANNEL_NAME and
        (before.channel is None or before.channel.id != after.channel.id)):

        if display_name not in user_sessions:
            user_sessions[display_name] = now
            print(f"{display_name} joined at {fmt(now)}")

    # Left GVG
    elif (before.channel and before.channel.name == VOICE_CHANNEL_NAME and
          (after.channel is None or after.channel.id != before.channel.id)):

        if display_name in user_sessions:
            joined_at = user_sessions.pop(display_name)
            duration = now - joined_at
            final_log[display_name] = {
                "Joined At": fmt(joined_at),
                "Left At": fmt(now),
                "Duration": str(duration).split(".")[0]
            }
            print(f"{display_name} left at {fmt(now)} — stayed {duration}")


async def finalize_log():
    end_time = now_london()
    for display_name, joined_at in user_sessions.items():
        duration = end_time - joined_at
        final_log[display_name] = {
            "Joined At": fmt(joined_at),
            "Left At": fmt(end_time),
            "Duration": str(duration).split(".")[0]
        }
    user_sessions.clear()


async def send_log_file():
    if not final_log:
        print("No users joined the GVG channel.")
        return

    filename = "gvg_manual_log.csv"
    with open(filename, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["User", "Joined At", "Left At", "Duration"])
        writer.writeheader()
        for user, data in final_log.items():
            row = {"User": user}
            row.update(data)
            writer.writerow(row)

    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(
            content="📋 Manual GVG attendance log:",
            file=discord.File(fp=filename)
        )
        print("✅ Summary log sent.")
    else:
        print("❌ Log channel not found.")

    os.remove(filename)
    final_log.clear()


@tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.CheckFailure):
        await interaction.response.send_message(
            "❌ You don't have permission to use this command.",
            ephemeral=True
        )

bot.run(TOKEN)
