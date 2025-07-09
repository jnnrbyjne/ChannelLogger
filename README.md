# GVG Voice Channel Tracker Bot

This Discord bot tracks who joins the "GVG" voice channel between 2–3 PM UK time on Thursdays and Sundays, logs their time spent, and sends a summary CSV to a specific channel.

## 🛠 Setup

1. **Clone the repo**  
2. **Create a `.env` file** with the following:
```
DISCORD_BOT_TOKEN=your-token-here
LOG_CHANNEL_ID=your-log-channel-id
```
3. **Install dependencies**
```
pip install -r requirements.txt
```
4. **Run the bot**
```
python main.py
```

## 📦 Deployment (Render.com)
- Create a new web service from this repo
- Add the `.env` variables in the Render dashboard
- Use `python main.py` as the start command