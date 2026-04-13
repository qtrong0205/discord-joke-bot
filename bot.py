import discord
from discord.ext import commands
import requests
import os
from dotenv import load_dotenv
from flask import Flask
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, date
import pytz
from threading import Thread

# ================= Load Environment Variables =================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# ================= Flask Web Server =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Discord Joke Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ================= Discord Bot Setup =================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= Joke API =================
def get_joke():
    url = "https://official-joke-api.appspot.com/random_joke"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Lấy ngày hiện tại theo múi giờ Việt Nam
            tz = pytz.timezone("Asia/Ho_Chi_Minh")
            current_date = datetime.now(tz).strftime("%A, %d/%m/%Y")
            return f"🤡 **Chào mấy thằng nhóc, tao là Vua Hề Bảo hôm nay là {current_date}**\nTa có một câu joke có mấy nhóc đây\n{data['setup']}\n{data['punchline']}🤣🤣"
    except Exception:
        pass
    return "😂 Hôm nay không lấy được joke, nhưng chúc bạn một ngày vui vẻ!"

# ================= Ensure One Joke Per Day =================
LAST_SENT_FILE = "last_sent.txt"

def has_sent_today():
    today = date.today().isoformat()
    if not os.path.exists(LAST_SENT_FILE):
        return False
    with open(LAST_SENT_FILE, "r") as f:
        return f.read().strip() == today

def mark_sent_today():
    with open(LAST_SENT_FILE, "w") as f:
        f.write(date.today().isoformat())

# ================= Send Joke =================
async def send_joke():
    if has_sent_today():
        print("Joke already sent today.")
        return
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(get_joke())
        mark_sent_today()
        print("Joke sent successfully!")
    else:
        print("Channel not found. Check CHANNEL_ID.")

# ================= Scheduler =================
scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Ho_Chi_Minh"))

# ================= Bot Ready Event =================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    # Cơ chế "bù": gửi nếu hôm nay chưa gửi
    await send_joke()

    # Chỉ khởi tạo scheduler một lần
    if not scheduler.running:
        scheduler.add_job(send_joke, "cron", hour=7, minute=0)
        scheduler.start()
        print("Scheduler started.")

# ================= Command for Manual Testing =================
@bot.command()
async def joke(ctx):
    await ctx.send(get_joke())

# ================= Run Both Flask and Discord =================
if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run(TOKEN)