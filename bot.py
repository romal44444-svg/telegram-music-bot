# bot.py
import asyncio
import requests
from io import BytesIO
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from yt_dlp import YoutubeDL

TOKEN = "8761560039:AAEqkHka_6tSN8GYf5g1JaedQSr6HC26E7o"

bot = Bot(token=TOKEN)
dp = Dispatcher()

search_cache = {}

USERS_FILE = "users.txt"

# ---------- сохранение пользователей ----------
def save_user(user_id):
    try:
        with open(USERS_FILE, "r") as f:
            users = f.read().splitlines()
    except FileNotFoundError:
        users = []

    if str(user_id) not in users:
        with open(USERS_FILE, "a") as f:
            f.write(str(user_id) + "\n")

# ---------- настройки yt-dlp ----------
YDL_SEARCH = {
    "quiet": True,
    "skip_download": True,
    "extract_flat": True
}

YDL_AUDIO = {
    "format": "bestaudio/best",
    "quiet": True
}

# ---------- /start ----------
@dp.message(Command("start"))
async def start(message: types.Message):
    save_user(message.from_user.id)
    await message.answer(
        "🎵 Отправь название песни\n\n"
        "Пример:\n"
        "Alan Walker Faded"
    )

# ---------- статистика ----------
@dp.message(Command("stats"))
async def stats(message: types.Message):
    try:
        with open(USERS_FILE) as f:
            users = f.readlines()
            count = len(users)
    except:
        count = 0
    await message.answer(f"👥 Пользователей бота: {count}")

# ---------- поиск трека ----------
@dp.message()
async def search_music(message: types.Message):
    save_user(message.from_user.id)
    query = message.text.strip()
    await message.answer("🔎 Ищу треки...")

    try:
        with YoutubeDL(YDL_SEARCH) as ydl:
            info = ydl.extract_info(f"ytsearch10:{query}", download=False)
    except Exception:
        await message.answer("❌ Ошибка поиска")
        return

    tracks = info.get("entries", [])
    if not tracks:
        await message.answer("❌ Ничего не найдено")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    search_cache[message.from_user.id] = {}

    for i, track in enumerate(tracks):
        title = track.get("title", "Track")
        video_id = track.get("id")
        search_cache[message.from_user.id][str(i)] = video_id

        btn = InlineKeyboardButton(
            text=f"{i+1}. {title}",
            callback_data=f"music_{i}"
        )
        keyboard.inline_keyboard.append([btn])

    thumb = tracks[0].get("thumbnails", [{}])[-1].get("url")
    if thumb:
        try:
            img = requests.get(thumb, timeout=10).content
            photo = BufferedInputFile(img, filename="cover.jpg")
            await message.answer_photo(
                photo=photo,
                caption="🎵 Выберите трек:",
                reply_markup=keyboard
            )
            return
        except:
            pass

    await message.answer("🎵 Выберите трек:", reply_markup=keyboard)

# ---------- скачивание трека ----------
@dp.callback_query(lambda c: c.data.startswith("music_"))
async def send_music(callback: types.CallbackQuery):
    await callback.answer()
    index = callback.data.split("_")[1]
    user_tracks = search_cache.get(callback.from_user.id)

    if not user_tracks:
        await callback.message.answer("Поиск устарел. Напишите название снова.")
        return

    video_id = user_tracks[index]
    url = f"https://youtube.com/watch?v={video_id}"
    await callback.message.answer("⬇️ Загружаю аудио...")

    try:
        with YoutubeDL(YDL_AUDIO) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception:
        await callback.message.answer("❌ Ошибка загрузки трека")
        return

    audio_url = info.get("url")
    title = info.get("title", "Track")
    artist = info.get("uploader", "Unknown")

    try:
        response = requests.get(audio_url, stream=True, timeout=20)
        audio_bytes = BytesIO()
        for chunk in response.iter_content(1024 * 64):
            if chunk:
                audio_bytes.write(chunk)
                if audio_bytes.tell() > 20 * 1024 * 1024:
                    await callback.message.answer("❌ Трек слишком большой для отправки.")
                    return
        audio_bytes.seek(0)

        audio = BufferedInputFile(audio_bytes.read(), filename="music.mp3")
        await bot.send_audio(
            chat_id=callback.message.chat.id,
            audio=audio,
            title=title,
            performer=artist
        )
    except Exception:
        await callback.message.answer("❌ Ошибка скачивания аудио")

# ---------- запуск ----------
if __name__ == "__main__":
    print("Бот запущен...")
    asyncio.run(dp.start_polling(bot))
