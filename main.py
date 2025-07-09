import discord
import datetime
import asyncio
import csv
import os
import pytz
from dotenv import load_dotenv

load_dotenv()

# ====== CONFIG ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
Bonding_sa_Conste = "Test Channel"  # TEMP for testing
TIMEZONE = pytz.timezone("Europe/London")

# ====== TRACKING DATA ======
tracked_users = {}
log_data = []

intents = discord.Intents.default()
intents.voice_states = True
intents.members = True

class GVGLogger(discord.Client):
    async def setup_hook(self):
        # Runs once when bot starts
        print("🔁 Running force upload...")
        await self.force_upload()

    async def on_ready(self):
        print(f"✅ Logged in as {self.user}")

    async def on_voice_state_update(self, member, before, after):
        now = datetime.datetime.now(TIMEZONE)
        voice_channel = discord.utils.get(member.guild.voice_channels, name=VOICE_CHANNEL_NAME)

        if before.channel != after.channel:
            if after.channel == voice_channel:
                tracked_users[member.id] = now
                print(f"🔵 {member.display_name} joined at {now.time()}")

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

    async def force_upload(self):
        await self.wait_until_ready()
        if not log_data:
            print("⚠️ No data to log.")
            return
        # Save CSV
        with open("voice_log.csv", mode="w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=log_data[0].keys())
            writer.writeheader()
            writer.writerows(log_data)
        print("📄 voice_log.csv saved.")

        # Send file to Discord
        try:
            channel = self.get_channel(LOG_CHANNEL_ID)
            if channel is None:
                print("❌ Log channel not found. Check LOG_CHANNEL_ID.")
                return
            await channel.send(
                content="📄 GVG Voice Log:",
                file=discord.File("voice_log.csv")
            )
            print("✅ Log sent.")
        except Exception as e:
            print(f"❌ Failed to send file: {e}")

# ====== Run Bot ======
client = GVGLogger(intents=intents)
client.run(BOT_TOKEN)
