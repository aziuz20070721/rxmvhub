import asyncio
import json
import os
import base64
import httpx
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GITHUB_TOKEN = os.environ.get("REPO_TOKEN")
OWNER_ID = 5980528489
GITHUB_REPO = "aziuz20070721/rxmvhub"
DATA_FILE = "data.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

KNOWN_SOURCES = [
    "sex-studentki.live"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}

# ─── GitHub Helpers ──────────────────────────────────────────────

async def github_get():
    """Получить data.json из GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content), data["sha"]

async def github_save(db: dict, sha: str):
    """Сохранить data.json в GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    content = base64.b64encode(json.dumps(db, ensure_ascii=False, indent=2).encode()).decode()
    payload = {"message": "update data", "content": content, "sha": sha}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.put(url, headers=headers, json=payload)
        r.raise_for_status()

# ─── Parsers ─────────────────────────────────────────────────────

async def parse_sex_studentki(limit: int) -> list:
    """Парсер sex-studentki.live"""
    videos = []
    page = 1
    async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        while len(videos) < limit and page <= 10:
            try:
                url = f"https://sex-studentki.live/hq-porn/{page}/"
                r = await client.get(url)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")
                
                # Ищем видео карточки
                items = soup.select(".thumb, .thumbs a[href*='video'], a[href*='/video/']")
                if not items:
                    items = soup.select("article, .item, .video-item")
                
                if not items:
                    break
                
                for item in items:
                    if len(videos) >= limit:
                        break
                    
                    try:
                        # Ищем ссылку на видео
                        link = None
                        if item.name == 'a':
                            link = item
                        else:
                            link = item.find('a', href=True)
                        
                        if not link:
                            continue
                        
                        href = link.get('href', '')
                        if not href or 'video' not in href.lower():
                            continue
                        
                        # Ищем изображение
                        img = item.find('img') if item.name != 'a' else link.find('img')
                        if not img:
                            continue
                        
                        title = img.get('alt', '') or img.get('title', '')
                        if not title:
                            title = item.get_text(strip=True)[:100]
                        
                        thumbnail = img.get('data-src') or img.get('src', '')
                        
                        if not title or not thumbnail:
                            continue
                        
                        # Абсолютный URL
                        if not href.startswith('http'):
                            href = 'https://sex-studentki.live' + (href if href.startswith('/') else '/' + href)
                        if thumbnail and not thumbnail.startswith('http'):
                            thumbnail = 'https://sex-studentki.live' + (thumbnail if thumbnail.startswith('/') else '/' + thumbnail)
                        
                        videos.append({
                            "title": title.strip()[:150],
                            "url": href,
                            "thumbnail": thumbnail,
                            "source": "sex-studentki.live"
                        })
                    except Exception as e:
                        continue
                
                page += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                break
    
    return videos[:limit]

async def parse_rusoska(limit: int) -> list:
    """Парсер rusoska.com"""
    videos = []
    page = 1
    async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        while len(videos) < limit and page <= 10:
            try:
                url = f"https://rusoska.com/porno-cats/{page}/"
                r = await client.get(url)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")
                
                # Ищем видео карточки
                items = soup.select(".thumb, .thumbs a[href*='video'], a[href*='/video/']")
                if not items:
                    items = soup.select("article, .item, .video-item, .video_item")
                
                if not items:
                    break
                
                for item in items:
                    if len(videos) >= limit:
                        break
                    
                    try:
                        # Ищем ссылку на видео
                        link = None
                        if item.name == 'a':
                            link = item
                        else:
                            link = item.find('a', href=True)
                        
                        if not link:
                            continue
                        
                        href = link.get('href', '')
                        if not href or 'video' not in href.lower():
                            continue
                        
                        # Ищем изображение
                        img = item.find('img') if item.name != 'a' else link.find('img')
                        if not img:
                            continue
                        
                        title = img.get('alt', '') or img.get('title', '')
                        if not title:
                            title = item.get_text(strip=True)[:100]
                        
                        thumbnail = img.get('data-src') or img.get('src', '')
                        
                        if not title or not thumbnail:
                            continue
                        
                        # Абсолютный URL
                        if not href.startswith('http'):
                            href = 'https://rusoska.com' + (href if href.startswith('/') else '/' + href)
                        if thumbnail and not thumbnail.startswith('http'):
                            thumbnail = 'https://rusoska.com' + (thumbnail if thumbnail.startswith('/') else '/' + thumbnail)
                        
                        videos.append({
                            "title": title.strip()[:150],
                            "url": href,
                            "thumbnail": thumbnail,
                            "source": "rusoska.com"
                        })
                    except Exception as e:
                        continue
                
                page += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                break
    
    return videos[:limit]

async def parse_xhamster(limit: int) -> list:
    """Парсер xhamster.com"""
    videos = []
    page = 0
    async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        while len(videos) < limit and page < 10:
            try:
                url = f"https://ru.xhamster.com/videos/newest/?page={page}"
                r = await client.get(url)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")
                
                # Ищем видео карточки
                items = soup.select(".thumb-list__item, a.video-thumb, .video-item, article")
                if not items:
                    items = soup.select("a[href*='/videos/']")
                
                if not items:
                    break
                
                for item in items:
                    if len(videos) >= limit:
                        break
                    
                    try:
                        # Ищем ссылку на видео
                        link = None
                        if item.name == 'a':
                            link = item
                        else:
                            link = item.find('a', href=True)
                        
                        if not link:
                            continue
                        
                        href = link.get('href', '')
                        if not href or 'video' not in href.lower():
                            continue
                        
                        # Ищем изображение
                        img = item.find('img') if item.name != 'a' else link.find('img')
                        if not img:
                            continue
                        
                        title = img.get('alt', '') or img.get('title', '')
                        if not title:
                            title_elem = item.select_one('[class*="title"], .video-title')
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                        
                        if not title:
                            title = item.get_text(strip=True)[:100]
                        
                        thumbnail = img.get('data-src') or img.get('src', '')
                        
                        if not title or not thumbnail:
                            continue
                        
                        # Абсолютный URL
                        if not href.startswith('http'):
                            href = 'https://ru.xhamster.com' + (href if href.startswith('/') else '/' + href)
                        if thumbnail and not thumbnail.startswith('http'):
                            thumbnail = 'https://ru.xhamster.com' + (thumbnail if thumbnail.startswith('/') else '/' + thumbnail)
                        
                        videos.append({
                            "title": title.strip()[:150],
                            "url": href,
                            "thumbnail": thumbnail,
                            "source": "xhamster.com"
                        })
                    except Exception as e:
                        continue
                
                page += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                break
    
    return videos[:limit]

async def parse_source(source: str, limit: int) -> list:
    """Выбрать парсер по названию сайта"""
    if "sex-studentki" in source:
        return await parse_sex_studentki(limit)
    elif "rusoska" in source:
        return await parse_rusoska(limit)
    elif "xhamster" in source:
        return await parse_xhamster(limit)
    return []

# ─── FSM ─────────────────────────────────────────────────────────

class ParseState(StatesGroup):
    choose_source = State()
    choose_count = State()

# ─── Helpers ─────────────────────────────────────────────────────

def is_admin(user_id: int, db: dict) -> bool:
    """Проверить, админ ли пользователь"""
    return user_id == OWNER_ID or user_id in db.get("admins", [])

def sources_keyboard(sources: list) -> ReplyKeyboardMarkup:
    """Клавиатура со списком сайтов"""
    buttons = [[KeyboardButton(text=s)] for s in sources]
    buttons.append([KeyboardButton(text="❌ Отмена")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

# ─── Commands ────────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(msg: types.Message):
    """Команда /start"""
    try:
        db, sha = await github_get()
        
        # Добавить пользователя в список
        if msg.from_user.id not in db.get("users", []) and msg.from_user.id != OWNER_ID:
            db.setdefault("users", []).append(msg.from_user.id)
            await github_save(db, sha)
        
        role = "👑 Создатель" if msg.from_user.id == OWNER_ID else ("🛡 Админ" if is_admin(msg.from_user.id, db) else "👤 Пользователь")
        
        await msg.answer(
            f"👋 Добро пожаловать в <b>rxmvhub</b>!\n\n"
            f"Твоя роль: {role}\n\n"
            f"<b>📋 Команды:</b>\n"
            f"/parse — парсить видео с сайта\n"
            f"/sources — список сайтов\n"
            f"/stats — статистика\n\n"
            f"<b>🛡 Админ команды:</b>\n"
            f"/addsource [сайт] — добавить сайт\n"
            f"/removesource [сайт] — удалить сайт\n"
            f"/users — список пользователей\n\n"
            f"<b>👑 Создатель команды:</b>\n"
            f"/addadmin [ID] — добавить админа\n"
            f"/removeadmin [ID] — удалить админа",
            parse_mode="HTML"
        )
    except Exception as e:
        await msg.answer(f"❌ Ошибка: {e}")

@dp.message(Command("sources"))
async def cmd_sources(msg: types.Message):
    """Показать список сайтов"""
    try:
        db, _ = await github_get()
        sources = db.get("sources", KNOWN_SOURCES)
        if not sources:
            return await msg.answer("Сайтов пока нет. Добавь через /addsource")
        text = "🌐 <b>Доступные сайты для парсинга:</b>\n" + "\n".join(f"• {s}" for s in sources)
        await msg.answer(text, parse_mode="HTML")
    except Exception as e:
        await msg.answer(f"❌ Ошибка: {e}")

@dp.message(Command("addsource"))
async def cmd_addsource(msg: types.Message):
    """Добавить новый сайт"""
    try:
        db, _ = await github_get()
        if not is_admin(msg.from_user.id, db):
            return await msg.answer("❌ Нет доступа. Только админы могут добавлять сайты.")
        
        parts = msg.text.split(maxsplit=1)
        if len(parts) < 2:
            return await msg.answer("Использование: /addsource rusoska.com")
        
        source = parts[1].strip().lower()
        db, sha = await github_get()
        db.setdefault("sources", KNOWN_SOURCES[:])
        
        if source in db["sources"]:
            return await msg.answer(f"❌ Сайт <b>{source}</b> уже есть в базе.", parse_mode="HTML")
        
        db["sources"].append(source)
        await github_save(db, sha)
        await msg.answer(f"✅ Сайт <b>{source}</b> добавлен!", parse_mode="HTML")
    except Exception as e:
        await msg.answer(f"❌ Ошибка: {e}")

@dp.message(Command("removesource"))
async def cmd_removesource(msg: types.Message):
    """Удалить сайт"""
    try:
        db, _ = await github_get()
        if not is_admin(msg.from_user.id, db):
            return await msg.answer("❌ Нет доступа. Только админы могут удалять сайты.")
        
        parts = msg.text.split(maxsplit=1)
        if len(parts) < 2:
            return await msg.answer("Использование: /removesource rusoska.com")
        
        source = parts[1].strip().lower()
        db, sha = await github_get()
        sources = db.get("sources", KNOWN_SOURCES[:])
        
        if source not in sources:
            return await msg.answer(f"❌ Сайт <b>{source}</b> не найден в базе.", parse_mode="HTML")
        
        sources.remove(source)
        db["sources"] = sources
        await github_save(db, sha)
        await msg.answer(f"✅ Сайт <b>{source}</b> удалён.", parse_mode="HTML")
    except Exception as e:
        await msg.answer(f"❌ Ошибка: {e}")

@dp.message(Command("parse"))
async def cmd_parse(msg: types.Message, state: FSMContext):
    """Начать парсинг"""
    try:
        db, _ = await github_get()
        if not is_admin(msg.from_user.id, db):
            return await msg.answer("❌ Нет доступа. Только админы могут парсить видео.")
        
        sources = db.get("sources", KNOWN_SOURCES)
        if not sources:
            return await msg.answer("❌ Сначала добавь сайты через /addsource")
        
        await state.set_state(ParseState.choose_source)
        await msg.answer("🌐 Выбери сайт для парсинга:", reply_markup=sources_keyboard(sources))
    except Exception as e:
        await msg.answer(f"❌ Ошибка: {e}")

@dp.message(ParseState.choose_source)
async def parse_choose_source(msg: types.Message, state: FSMContext):
    """Выбор сайта для парсинга"""
    if msg.text == "❌ Отмена":
        await state.clear()
        return await msg.answer("Отменено.", reply_markup=ReplyKeyboardRemove())
    
    db, _ = await github_get()
    sources = db.get("sources", KNOWN_SOURCES)
    
    if msg.text not in sources:
        return await msg.answer("❌ Выбери сайт из списка!")
    
    await state.update_data(source=msg.text)
    await state.set_state(ParseState.choose_count)
    await msg.answer(
        f"📊 Сколько видео собрать с <b>{msg.text}</b>? (1-500)",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(ParseState.choose_count)
async def parse_choose_count(msg: types.Message, state: FSMContext):
    """Выбор количества видео"""
    if not msg.text.isdigit() or not (1 <= int(msg.text) <= 500):
        return await msg.answer("❌ Введи число от 1 до 500!")
    
    count = int(msg.text)
    data = await state.get_data()
    source = data["source"]
    await state.clear()
    
    status_msg = await msg.answer(
        f"⏳ Парсю <b>{count}</b> видео с <b>{source}</b>...\n\n"
        f"Это может занять несколько минут, не отправляй команды.",
        parse_mode="HTML"
    )
    
    try:
        videos = await parse_source(source, count)
        
        if not videos:
            return await status_msg.edit_text(
                f"😔 Ничего не нашёл на <b>{source}</b>.\n\n"
                f"Возможные причины:\n"
                f"• Сайт заблокировал парсер\n"
                f"• Изменилась структура сайта\n"
                f"• Проблема с сетью",
                parse_mode="HTML"
            )
        
        db, sha = await github_get()
        existing_urls = {v["url"] for v in db.get("videos", [])}
        new_videos = [v for v in videos if v["url"] not in existing_urls]
        
        if not new_videos:
            return await status_msg.edit_text(
                f"✅ Найдено {len(videos)} видео, но все они уже в базе."
            )
        
        next_id = max((v["id"] for v in db.get("videos", [])), default=0) + 1
        for v in new_videos:
            v["id"] = next_id
            next_id += 1
        
        db.setdefault("videos", []).extend(new_videos)
        await github_save(db, sha)
        
        await status_msg.edit_text(
            f"✅ <b>Готово!</b>\n\n"
            f"📥 Найдено: {len(videos)}\n"
            f"🆕 Добавлено новых: {len(new_videos)}\n"
            f"♻️ Дубликатов пропущено: {len(videos) - len(new_videos)}\n\n"
            f"Всего видео в базе: {len(db.get('videos', []))}",
            parse_mode="HTML"
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка парсинга: {str(e)[:100]}")

@dp.message(Command("stats"))
async def cmd_stats(msg: types.Message):
    """Показать статистику"""
    try:
        db, _ = await github_get()
        videos = db.get("videos", [])
        sources = {}
        
        for v in videos:
            s = v.get("source", "unknown")
            sources[s] = sources.get(s, 0) + 1
        
        text = f"📊 <b>Статистика rxmvhub:</b>\n\n🎬 Всего видео: <b>{len(videos)}</b>\n"
        
        if sources:
            text += "\n<b>По источникам:</b>\n"
            for s, c in sorted(sources.items(), key=lambda x: -x[1]):
                text += f"• {s}: {c}\n"
        
        text += f"\n👥 Пользователей: <b>{len(db.get('users', []))}</b>\n"
        text += f"🛡 Админов: <b>{len(db.get('admins', []))}</b>"
        
        await msg.answer(text, parse_mode="HTML")
    except Exception as e:
        await msg.answer(f"❌ Ошибка: {e}")

@dp.message(Command("users"))
async def cmd_users(msg: types.Message):
    """Показать список пользователей"""
    try:
        db, _ = await github_get()
        if not is_admin(msg.from_user.id, db):
            return await msg.answer("❌ Нет доступа. Только админы могут видеть список пользователей.")
        
        users = db.get("users", [])
        if not users:
            return await msg.answer("👥 Пользователей пока нет.")
        
        text = f"👥 <b>Пользователи ({len(users)}):</b>\n" + "\n".join(f"• {u}" for u in users[:50])
        if len(users) > 50:
            text += f"\n... и еще {len(users) - 50}"
        
        await msg.answer(text, parse_mode="HTML")
    except Exception as e:
        await msg.answer(f"❌ Ошибка: {e}")

@dp.message(Command("addadmin"))
async def cmd_addadmin(msg: types.Message):
    """Добавить админа (только создатель)"""
    try:
        if msg.from_user.id != OWNER_ID:
            return await msg.answer("❌ Только создатель может управлять админами.")
        
        parts = msg.text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            return await msg.answer("Использование: /addadmin 123456789")
        
        new_id = int(parts[1])
        db, sha = await github_get()
        db.setdefault("admins", [])
        
        if new_id in db["admins"]:
            return await msg.answer(f"❌ Пользователь {new_id} уже админ.")
        
        db["admins"].append(new_id)
        await github_save(db, sha)
        await msg.answer(f"✅ Пользователь {new_id} назначен админом!")
    except Exception as e:
        await msg.answer(f"❌ Ошибка: {e}")

@dp.message(Command("removeadmin"))
async def cmd_removeadmin(msg: types.Message):
    """Удалить админа (только создатель)"""
    try:
        if msg.from_user.id != OWNER_ID:
            return await msg.answer("❌ Только создатель может управлять админами.")
        
        parts = msg.text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            return await msg.answer("Использование: /removeadmin 123456789")
        
        rem_id = int(parts[1])
        db, sha = await github_get()
        
        if rem_id not in db.get("admins", []):
            return await msg.answer(f"❌ Пользователь {rem_id} не является админом.")
        
        db["admins"].remove(rem_id)
        await github_save(db, sha)
        await msg.answer(f"✅ Пользователь {rem_id} удалён из админов.")
    except Exception as e:
        await msg.answer(f"❌ Ошибка: {e}")

# ─── Auto-parse on startup ────────────────────────────────────────

async def auto_parse_on_start():
    """Автоматический парсинг при первом запуске"""
    await asyncio.sleep(5)  # Дождемся инициализации
    
    try:
        db, sha = await github_get()
        
        # Проверить флаг первого запуска
        if db.get("initial_parse_done"):
            await bot.send_message(OWNER_ID, "🤖 Бот запущен. Начальный парсинг уже был выполнен.")
            return
        
        await bot.send_message(OWNER_ID, "🚀 <b>Начинаю первоначальный сбор видео...</b>\n\nЭто может занять 10-20 минут.", parse_mode="HTML")
        
        sources = db.get("sources", KNOWN_SOURCES)
        all_videos = []
        
        for source in sources:
            try:
                await bot.send_message(OWNER_ID, f"⏳ Парсю {source}...")
                videos = await parse_source(source, 100)
                all_videos.extend(videos)
                await bot.send_message(OWNER_ID, f"✅ {source}: найдено {len(videos)} видео")
            except Exception as e:
                await bot.send_message(OWNER_ID, f"⚠️ {source}: ошибка — {str(e)[:100]}")
            
            await asyncio.sleep(2)  # Задержка между парсерами
        
        # Сохранить видео
        db, sha = await github_get()
        existing_urls = {v["url"] for v in db.get("videos", [])}
        new_videos = [v for v in all_videos if v["url"] not in existing_urls]
        
        next_id = max((v["id"] for v in db.get("videos", [])), default=0) + 1
        for v in new_videos:
            v["id"] = next_id
            next_id += 1
        
        db.setdefault("videos", []).extend(new_videos)
        db["initial_parse_done"] = True
        db.setdefault("sources", KNOWN_SOURCES)
        
        await github_save(db, sha)
        
        total_found = sum(1 for _ in all_videos)
        await bot.send_message(
            OWNER_ID,
            f"🎉 <b>Первоначальный парсинг завершен!</b>\n\n"
            f"📥 Всего найдено: {total_found}\n"
            f"🆕 Добавлено новых: {len(new_videos)}\n"
            f"📦 Всего видео в базе: {len(db.get('videos', []))}",
            parse_mode="HTML"
        )
    except Exception as e:
        try:
            await bot.send_message(OWNER_ID, f"❌ Ошибка при первоначальном парсинге: {str(e)[:100]}")
        except:
            pass

# ─── Main ────────────────────────────────────────────────────────

async def main():
    asyncio.create_task(auto_parse_on_start())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
