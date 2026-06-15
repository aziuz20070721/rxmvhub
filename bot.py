import os
import json
import base64
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp

# ---------- Конфигурация ----------
OWNER_ID = 5980528489
BOT_TOKEN = os.environ["BOT_TOKEN"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = "aziuz20070721/rxmvhub"
DATA_FILE = "data.json"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}"
RAW_DATA_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{DATA_FILE}"

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ---------- FSM ----------
class AddVideoStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_thumbnail = State()
    waiting_for_title = State()
    waiting_for_category = State()
    waiting_for_new_category = State()

# ---------- Работа с данными ----------
async def read_data() -> Optional[Dict[str, Any]]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(RAW_DATA_URL) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    print(f"read_data: HTTP {resp.status}")
                    return None
    except Exception as e:
        print(f"read_data error: {e}")
        return None

async def write_data(data: Dict[str, Any], commit_message: str) -> bool:
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        async with aiohttp.ClientSession() as session:
            # получаем SHA текущего файла
            async with session.get(GITHUB_API_URL, headers=headers) as resp:
                if resp.status == 200:
                    current = await resp.json()
                    sha = current["sha"]
                elif resp.status == 404:
                    sha = None
                else:
                    print(f"write_data GET sha: {resp.status}")
                    return False

            content_str = json.dumps(data, indent=2, ensure_ascii=False)
            content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
            payload = {"message": commit_message, "content": content_b64}
            if sha:
                payload["sha"] = sha

            async with session.put(GITHUB_API_URL, headers=headers, json=payload) as resp:
                success = resp.status in (200, 201)
                if not success:
                    text = await resp.text()
                    print(f"write_data PUT error: {resp.status} - {text}")
                return success
    except Exception as e:
        print(f"write_data exception: {e}")
        return False

# ---------- Вспомогательные ----------
def extract_youtube_id(url: str) -> Optional[str]:
    parsed = urlparse(url)
    if parsed.hostname in ("youtu.be", "www.youtu.be"):
        return parsed.path[1:]
    if parsed.hostname in ("youtube.com", "www.youtube.com"):
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        elif parsed.path.startswith(("/embed/", "/v/")):
            return parsed.path.split("/")[2]
    return None

def is_admin(user_id: int, data: Dict) -> bool:
    return user_id in data.get("admins", [])

# ---------- Команды ----------
@dp.message(Command("start"))
async def cmd_start(message: Message):
    data = await read_data()
    if not data:
        await message.answer("❌ Ошибка загрузки данных. Попробуйте позже.")
        return
    if is_admin(message.from_user.id, data):
        await message.answer(
            "👋 Привет, админ!\n\n"
            "Доступные команды:\n"
            "/add — добавить видео\n"
            "/delete ID — удалить видео\n"
            "/list — показать последние 10 видео\n"
            "/admins — список админов (только владелец)\n"
            "/addadmin — добавить админа (только владелец)\n"
            "/removeadmin — удалить админа (только владелец)\n"
            "/cancel — отменить действие"
        )
    else:
        await message.answer("🔒 Этот бот только для администраторов. Обратитесь к @aziuz20070721.")

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✅ Действие отменено.")

@dp.message(Command("list"))
async def cmd_list(message: Message):
    data = await read_data()
    if not data:
        await message.answer("❌ Ошибка загрузки данных.")
        return
    if not is_admin(message.from_user.id, data):
        await message.answer("⛔ У вас нет прав.")
        return
    videos = data.get("videos", [])[-10:][::-1]
    if not videos:
        await message.answer("📭 Видео пока нет.")
        return
    text = "🎬 Последние 10 видео:\n\n"
    for v in videos:
        text += f"ID: {v['id']} — {v['title']}\n"
    await message.answer(text)

@dp.message(Command("delete"))
async def cmd_delete(message: Message):
    data = await read_data()
    if not data:
        await message.answer("❌ Ошибка загрузки данных.")
        return
    if not is_admin(message.from_user.id, data):
        await message.answer("⛔ Только админы могут удалять видео.")
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("❌ Использование: /delete ID")
        return
    try:
        vid = int(parts[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом.")
        return
    old_len = len(data["videos"])
    data["videos"] = [v for v in data["videos"] if v["id"] != vid]
    if len(data["videos"]) == old_len:
        await message.answer(f"❌ Видео с ID {vid} не найдено.")
        return
    success = await write_data(data, f"Удалено видео {vid} админом {message.from_user.id}")
    if success:
        await message.answer(f"✅ Видео с ID {vid} удалено.")
    else:
        await message.answer("❌ Ошибка сохранения в GitHub. Проверьте токены.")

async def modify_admin(message: Message, add: bool):
    if message.from_user.id != OWNER_ID:
        await message.answer("⛔ Только создатель может управлять админами.")
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("❌ Использование: /addadmin @username или /addadmin 123456789")
        return
    arg = parts[1].strip()
    if arg.startswith("@"):
        try:
            chat = await bot.get_chat(arg)
            user_id = chat.id
        except Exception:
            await message.answer("❌ Не удалось найти пользователя. Используйте числовой ID.")
            return
    else:
        try:
            user_id = int(arg)
        except ValueError:
            await message.answer("❌ ID должен быть числом или @username.")
            return
    data = await read_data()
    if not data:
        await message.answer("❌ Ошибка загрузки данных.")
        return
    admins = data.get("admins", [])
    if add:
        if user_id in admins:
            await message.answer("⚠️ Этот пользователь уже админ.")
            return
        admins.append(user_id)
    else:
        if user_id not in admins:
            await message.answer("⚠️ Этот пользователь не админ.")
            return
        if user_id == OWNER_ID:
            await message.answer("❌ Нельзя удалить создателя из админов.")
            return
        admins.remove(user_id)
    data["admins"] = admins
    success = await write_data(data, f"{'Добавлен' if add else 'Удалён'} админ {user_id}")
    if success:
        await message.answer(f"✅ Админ {user_id} {'добавлен' if add else 'удалён'}.")
    else:
        await message.answer("❌ Ошибка сохранения.")

@dp.message(Command("addadmin"))
async def add_admin(message: Message):
    await modify_admin(message, add=True)

@dp.message(Command("removeadmin"))
async def remove_admin(message: Message):
    await modify_admin(message, add=False)

@dp.message(Command("admins"))
async def list_admins(message: Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("⛔ Только создатель может просматривать список админов.")
        return
    data = await read_data()
    if not data:
        await message.answer("❌ Ошибка загрузки.")
        return
    admins = data.get("admins", [])
    if not admins:
        await message.answer("📭 Список админов пуст.")
        return
    text = "👥 Список админов:\n"
    for uid in admins:
        try:
            user = await bot.get_chat(uid)
            name = user.full_name or str(uid)
        except:
            name = str(uid)
        text += f"- {name} (ID: {uid})\n"
    await message.answer(text)

# ---------- ADD FSM ----------
@dp.message(Command("add"))
async def cmd_add_start(message: Message, state: FSMContext):
    data = await read_data()
    if not data:
        await message.answer("❌ Ошибка загрузки данных.")
        return
    if not is_admin(message.from_user.id, data):
        await message.answer("⛔ Только админы могут добавлять видео.")
        return
    await state.set_state(AddVideoStates.waiting_for_url)
    await message.answer("📎 Отправь ссылку на видео (YouTube).\nОтмена: /cancel")

@dp.message(AddVideoStates.waiting_for_url, F.text)
async def process_url(message: Message, state: FSMContext):
    url = message.text.strip()
    vid_id = extract_youtube_id(url)
    if not vid_id:
        await message.answer("❌ Это не похоже на ссылку YouTube. Попробуй снова или /cancel.")
        return
    await state.update_data(url=url, youtube_id=vid_id)
    await state.set_state(AddVideoStates.waiting_for_thumbnail)
    await message.answer(
        "🖼 Теперь отправь ссылку на превью (картинку).\n"
        "Если это YouTube и хочешь авто-превью, напиши: авто\n"
        "Можно также прислать фото напрямую."
    )

@dp.message(AddVideoStates.waiting_for_thumbnail, F.text)
async def process_thumbnail_text(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    youtube_id = data.get("youtube_id")
    if text.lower() == "авто" and youtube_id:
        thumbnail = f"https://img.youtube.com/vi/{youtube_id}/hqdefault.jpg"
    else:
        if not text.startswith(("http://", "https://")):
            await message.answer("❌ Пожалуйста, отправь ссылку, начинающуюся с http:// или https://, или напиши 'авто'.")
            return
        thumbnail = text
    await state.update_data(thumbnail=thumbnail)
    await state.set_state(AddVideoStates.waiting_for_title)
    await message.answer("📝 Напиши название видео.")

@dp.message(AddVideoStates.waiting_for_thumbnail, F.photo)
async def process_thumbnail_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    await state.update_data(thumbnail=file_url)
    await state.set_state(AddVideoStates.waiting_for_title)
    await message.answer("📝 Напиши название видео.")

@dp.message(AddVideoStates.waiting_for_title, F.text)
async def process_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if len(title) < 3:
        await message.answer("❌ Название слишком короткое. Попробуй ещё раз.")
        return
    await state.update_data(title=title)
    full_data = await read_data()
    if not full_data:
        await message.answer("❌ Ошибка загрузки категорий. Попробуй позже.")
        await state.clear()
        return
    categories = full_data.get("categories", [])
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for cat in categories:
        kb.inline_keyboard.append([InlineKeyboardButton(text=cat, callback_data=f"cat_{cat}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="✨ Новая категория", callback_data="cat_new")])
    await state.set_state(AddVideoStates.waiting_for_category)
    await message.answer("🏷 Выбери категорию:", reply_markup=kb)

@dp.callback_query(AddVideoStates.waiting_for_category)
async def process_category_callback(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    if data == "cat_new":
        await state.set_state(AddVideoStates.waiting_for_new_category)
        await callback.message.edit_text("✏️ Напиши название новой категории:")
        await callback.answer()
        return
    if data.startswith("cat_"):
        category = data[4:]
        await state.update_data(category=category)
        await save_video(callback.message, state)
        await callback.answer()

@dp.message(AddVideoStates.waiting_for_new_category, F.text)
async def process_new_category(message: Message, state: FSMContext):
    new_cat = message.text.strip()
    if not new_cat:
        await message.answer("❌ Категория не может быть пустой. Напиши название.")
        return
    await state.update_data(category=new_cat)
    await save_video(message, state)

async def save_video(msg: Message, state: FSMContext):
    data = await state.get_data()
    title = data.get("title")
    url = data.get("url")
    thumbnail = data.get("thumbnail")
    category = data.get("category")
    added_by = msg.from_user.id
    date = datetime.now().strftime("%Y-%m-%d")

    full_data = await read_data()
    if not full_data:
        await msg.answer("❌ Ошибка загрузки базы. Видео не сохранено.")
        await state.clear()
        return

    if category not in full_data["categories"]:
        full_data["categories"].append(category)

    next_id = full_data.get("next_id", 1)
    new_video = {
        "id": next_id,
        "title": title,
        "url": url,
        "thumbnail": thumbnail,
        "category": category,
        "added_by": added_by,
        "date": date
    }
    full_data["videos"].append(new_video)
    full_data["next_id"] = next_id + 1

    success = await write_data(full_data, f"Добавлено видео {next_id}: {title}")
    if success:
        await msg.answer(f"✅ Видео «{title}» добавлено! ID: {next_id}")
    else:
        await msg.answer("❌ Ошибка сохранения в GitHub. Попробуй ещё раз.")
    await state.clear()

# ---------- Запуск бота ----------
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот запущен и готов к работе")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
