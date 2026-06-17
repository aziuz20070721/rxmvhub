import asyncio
import json
import os
import base64
import httpx
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

BOT_TOKEN = os.environ["BOT_TOKEN"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
OWNER_ID = 5980528489
GITHUB_REPO = "aziuz20070721/rxmvhub"
DATA_FILE = "data.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ─── GitHub helpers ───────────────────────────────────────────────

async def github_get_file():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content), data["sha"]

async def github_save_file(db: dict, sha: str):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    content = base64.b64encode(json.dumps(db, ensure_ascii=False, indent=2).encode()).decode()
    payload = {"message": "update data", "content": content, "sha": sha}
    async with httpx.AsyncClient() as client:
        r = await client.put(url, headers=headers, json=payload)
        r.raise_for_status()

# ─── FSM ──────────────────────────────────────────────────────────

class AddVideo(StatesGroup):
    url = State()
    thumbnail = State()
    title = State()
    category = State()
    new_category = State()

# ─── Helpers ──────────────────────────────────────────────────────

def is_admin(user_id: int, db: dict) -> bool:
    return user_id == OWNER_ID or user_id in db.get("admins", [])

def category_keyboard(categories: list) -> ReplyKeyboardMarkup:
    buttons = [[KeyboardButton(text=c)] for c in categories]
    buttons.append([KeyboardButton(text="➕ Новая категория")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

# ─── Commands ─────────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(msg: types.Message):
    db, _ = await github_get_file()
    role = "👑 Создатель" if msg.from_user.id == OWNER_ID else ("🛡 Админ" if is_admin(msg.from_user.id, db) else "👤 Пользователь")
    await msg.answer(
        f"👋 Добро пожаловать в <b>rxmvhub</b>!\n\n"
        f"Твоя роль: {role}\n\n"
        f"Команды:\n"
        f"/add — добавить видео\n"
        f"/delete ID — удалить видео\n"
        f"/addadmin ID — добавить админа (только создатель)\n"
        f"/removeadmin ID — удалить админа (только создатель)\n"
        f"/list — список видео\n"
        f"/admins — список админов",
        parse_mode="HTML"
    )

@dp.message(Command("addadmin"))
async def cmd_addadmin(msg: types.Message):
    if msg.from_user.id != OWNER_ID:
        return await msg.answer("❌ Только создатель может назначать админов.")
    parts = msg.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await msg.answer("Использование: /addadmin 123456789")
    new_id = int(parts[1])
    db, sha = await github_get_file()
    if new_id in db["admins"]:
        return await msg.answer("Этот пользователь уже админ.")
    db["admins"].append(new_id)
    await github_save_file(db, sha)
    await msg.answer(f"✅ Пользователь {new_id} назначен админом!")

@dp.message(Command("removeadmin"))
async def cmd_removeadmin(msg: types.Message):
    if msg.from_user.id != OWNER_ID:
        return await msg.answer("❌ Только создатель может удалять админов.")
    parts = msg.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await msg.answer("Использование: /removeadmin 123456789")
    rem_id = int(parts[1])
    db, sha = await github_get_file()
    if rem_id not in db["admins"]:
        return await msg.answer("Этот пользователь не является админом.")
    db["admins"].remove(rem_id)
    await github_save_file(db, sha)
    await msg.answer(f"✅ Пользователь {rem_id} удалён из админов.")

@dp.message(Command("admins"))
async def cmd_admins(msg: types.Message):
    db, _ = await github_get_file()
    admins = db.get("admins", [])
    if not admins:
        return await msg.answer("Админов пока нет.")
    text = "🛡 <b>Список админов:</b>\n" + "\n".join(f"• {a}" for a in admins)
    await msg.answer(text, parse_mode="HTML")

@dp.message(Command("list"))
async def cmd_list(msg: types.Message):
    db, _ = await github_get_file()
    videos = db.get("videos", [])
    if not videos:
        return await msg.answer("Видео пока нет.")
    text = "🎬 <b>Видео:</b>\n"
    for v in videos[-20:]:
        text += f"\n<b>ID {v['id']}</b> — {v['title']} [{v['category']}]\n{v['url']}\n"
    await msg.answer(text, parse_mode="HTML")

@dp.message(Command("delete"))
async def cmd_delete(msg: types.Message):
    db, _ = await github_get_file()
    if not is_admin(msg.from_user.id, db):
        return await msg.answer("❌ Нет доступа.")
    parts = msg.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await msg.answer("Использование: /delete 5")
    vid_id = int(parts[1])
    db2, sha = await github_get_file()
    before = len(db2["videos"])
    db2["videos"] = [v for v in db2["videos"] if v["id"] != vid_id]
    if len(db2["videos"]) == before:
        return await msg.answer("Видео с таким ID не найдено.")
    await github_save_file(db2, sha)
    await msg.answer(f"✅ Видео {vid_id} удалено!")

# ─── Add video FSM ────────────────────────────────────────────────

@dp.message(Command("add"))
async def cmd_add(msg: types.Message, state: FSMContext):
    db, _ = await github_get_file()
    if not is_admin(msg.from_user.id, db):
        return await msg.answer("❌ Нет доступа.")
    await state.set_state(AddVideo.url)
    await msg.answer("🔗 Шаг 1/4: Отправь ссылку на видео:", reply_markup=ReplyKeyboardRemove())

@dp.message(AddVideo.url)
async def add_url(msg: types.Message, state: FSMContext):
    await state.update_data(url=msg.text.strip())
    await state.set_state(AddVideo.thumbnail)
    await msg.answer("🖼 Шаг 2/4: Отправь ссылку на превью (картинка .jpg/.png):")

@dp.message(AddVideo.thumbnail)
async def add_thumbnail(msg: types.Message, state: FSMContext):
    await state.update_data(thumbnail=msg.text.strip())
    await state.set_state(AddVideo.title)
    await msg.answer("📝 Шаг 3/4: Напиши название видео:")

@dp.message(AddVideo.title)
async def add_title(msg: types.Message, state: FSMContext):
    await state.update_data(title=msg.text.strip())
    db, _ = await github_get_file()
    categories = db.get("categories", [])
    await state.set_state(AddVideo.category)
    if categories:
        await msg.answer("🏷 Шаг 4/4: Выбери категорию или создай новую:", reply_markup=category_keyboard(categories))
    else:
        await msg.answer("🏷 Шаг 4/4: Категорий пока нет. Напиши название новой категории:")

@dp.message(AddVideo.category)
async def add_category(msg: types.Message, state: FSMContext):
    text = msg.text.strip()
    if text == "➕ Новая категория":
        await state.set_state(AddVideo.new_category)
        return await msg.answer("Напиши название новой категории:", reply_markup=ReplyKeyboardRemove())
    await finish_add(msg, state, text)

@dp.message(AddVideo.new_category)
async def add_new_category(msg: types.Message, state: FSMContext):
    await finish_add(msg, state, msg.text.strip())

async def finish_add(msg: types.Message, state: FSMContext, category: str):
    data = await state.get_data()
    db, sha = await github_get_file()
    next_id = max((v["id"] for v in db["videos"]), default=0) + 1
    if category not in db["categories"]:
        db["categories"].append(category)
    db["videos"].append({
        "id": next_id,
        "title": data["title"],
        "url": data["url"],
        "thumbnail": data["thumbnail"],
        "category": category
    })
    await github_save_file(db, sha)
    await state.clear()
    await msg.answer(
        f"✅ Видео добавлено!\n\n"
        f"🆔 ID: {next_id}\n"
        f"📝 {data['title']}\n"
        f"🏷 {category}",
        reply_markup=ReplyKeyboardRemove()
    )

# ─── Run ──────────────────────────────────────────────────────────

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
