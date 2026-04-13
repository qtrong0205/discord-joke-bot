import discord
from discord.ext import commands
import requests
import os
from dotenv import load_dotenv
from flask import Flask, Response
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import pytz
from threading import Thread
import google.generativeai as genai

# ================= Load Environment Variables =================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TOKEN or not CHANNEL_ID or not GEMINI_API_KEY:
    raise ValueError("Missing environment variables. Please check your .env file.")

# ================= Configure Gemini API =================
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# ================= Flask Web Server =================
app = Flask(__name__)

@app.route("/")
def home():
    return Response("Discord Joke Bot is running!", status=200, mimetype="text/plain")

@app.route("/ping")
def ping():
    return Response("pong", status=200, mimetype="text/plain")

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ================= Discord Bot Setup =================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= Joke Translation with Gemini =================
def translate_joke_to_vietnamese(joke_en: str) -> str:
    prompt = (
    "Bạn là một dịch giả hài hước và thông minh.\n"
    "Hãy dịch câu joke tiếng Anh sau sang tiếng Việt một cách tự nhiên, "
    "giữ được sự hài hước và đúng ngữ cảnh.\n\n"
    "Yêu cầu:\n"
    "1. Nếu câu joke là chơi chữ (pun/wordplay), hãy giữ ý nghĩa hài hước "
    "tốt nhất có thể khi dịch.\n"
    "2. Nếu việc chơi chữ khó hiểu đối với người Việt, hãy thêm một phần "
    "giải thích ngắn gọn.\n"
    "3. Nếu không phải là joke chơi chữ, chỉ cần dịch mà không cần giải thích.\n"
    "4. Không thêm bất kỳ nội dung nào ngoài các phần được yêu cầu.\n\n"
    "Định dạng kết quả:\n"
    "- Nếu KHÔNG phải chơi chữ:\n"
    "  <joke>\n"
    "- Nếu LÀ chơi chữ:\n"
    "  <joke>\n"
    "  📝 Giải thích: <explanation>\n\n"
    f"Câu joke: {joke_en}"
    )
    try:
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        print(f"Gemini translation error: {e}")

    # Fallback nếu có lỗi
    return joke_en

# ================= Fetch Joke from API =================
def get_joke() -> str:
    url = "https://official-joke-api.appspot.com/random_joke"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            joke_en = f"{data['setup']} {data['punchline']}"

            # Dịch sang tiếng Việt bằng Gemini
            joke_vi = translate_joke_to_vietnamese(joke_en)

            # Lấy ngày hiện tại theo múi giờ Việt Nam
            tz = pytz.timezone("Asia/Ho_Chi_Minh")
            current_date = datetime.now(tz).strftime("%A, %d/%m/%Y")

            return (
                f"🤡 **Chào mấy thằng nhóc, tao là Vua Hề Bảo!**\n"
                f"📅 Hôm nay là {current_date}\n"
                f"🎭 Ta có một câu joke cho mấy nhóc đây:\n\n"
                f"{joke_vi} 🤣"
            )
    except Exception as e:
        print(f"Joke API error: {e}")

    return "😂 Hôm nay không lấy được joke, nhưng chúc bạn một ngày vui vẻ!"

# ================= Ensure One Joke Per Day =================
LAST_SENT_FILE = "last_sent.txt"

def has_sent_today() -> bool:
    tz = pytz.timezone("Asia/Ho_Chi_Minh")
    today = datetime.now(tz).date().isoformat()

    if not os.path.exists(LAST_SENT_FILE):
        return False

    with open(LAST_SENT_FILE, "r") as f:
        return f.read().strip() == today

def mark_sent_today():
    tz = pytz.timezone("Asia/Ho_Chi_Minh")
    today = datetime.now(tz).date().isoformat()

    with open(LAST_SENT_FILE, "w") as f:
        f.write(today)

# ================= Send Joke =================
async def send_joke():
    if has_sent_today():
        print("Joke already sent today.")
        return

    channel = bot.get_channel(CHANNEL_ID)

    # Nếu channel chưa có trong cache, thử fetch
    if channel is None:
        try:
            channel = await bot.fetch_channel(CHANNEL_ID)
        except Exception as e:
            print(f"Cannot fetch channel: {e}")
            return

    try:
        await channel.send(get_joke())
        mark_sent_today()
        print("Joke sent successfully!")
    except Exception as e:
        print(f"Error sending joke: {e}")

# ================= Scheduler =================
scheduler = AsyncIOScheduler(
    timezone=pytz.timezone("Asia/Ho_Chi_Minh")
)

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
        print("Scheduler started. Waiting for 7:00 AM...")

# ================= Command for Manual Testing =================
@bot.command(name="joke")
async def joke_command(ctx):
    await ctx.send(get_joke())

# ================= Run Both Flask and Discord =================
if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run(TOKEN)