cat > /mnt/user-data/outputs/rxmvhub/bot.py << 'PYEOF'
import asyncio
import json
import os
import base64
import httpx
import io
from datetime import datetime
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT

BOT_TOKEN = os.environ["BOT_TOKEN"]
GITHUB_TOKEN = os.environ["REPO_TOKEN"]
OWNER_ID = 5980528489
GITHUB_REPO = "aziuz20070721/rxmvhub"
DATA_FILE = "data.json"
LOG_CHANNEL = -1004479533617

KNOWN_SOURCES = ["sex-studentki.live", "rusoska.com", "xhamster.com"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ── GitHub ────────────────────────────────────────────────────────

async def github_get():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content), data["sha"]

async def github_save(db: dict, sha: str):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    content = base64.b64encode(json.dumps(db, ensure_ascii=False, indent=2).encode()).decode()
    payload = {"message": "update data", "content": content, "sha": sha}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.put(url, headers=headers, json=payload)
        r.raise_for_status()

# ── Logging ───────────────────────────────────────────────────────

def get_hashtag(user: types.User) -> str:
    if user.username:
        return f"#_{user.username}"
    return f"#id{user.id}"

def now_str() -> str:
    return datetime.utcnow().strftime("%d.%m.%Y %H:%M:%S UTC")

async def log_new_user(user: types.User):
    tag = get_hashtag(user)
    lang = user.language_code or "неизвестен"
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    text = (
        f"🆕 <b>НОВЫЙ ПОЛЬЗОВАТЕЛЬ</b> {tag}\n\n"
        f"👤 Имя: <b>{name}</b>\n"
        f"🔖 Username: @{user.username or '—'}\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"🌐 Язык: {lang}\n"
        f"🤖 Бот: {'да' if user.is_bot else 'нет'}\n"
        f"⭐️ Premium: {'да' if getattr(user, 'is_premium', False) else 'нет'}\n"
        f"🕐 Первый вход: {now_str()}"
    )
    try:
        await bot.send_message(LOG_CHANNEL, text, parse_mode="HTML")
    except Exception as e:
        print(f"Log error: {e}")

async def log_visit(user: types.User):
    tag = get_hashtag(user)
    text = (
        f"👁 <b>ВИЗИТ</b> {tag}\n"
        f"🕐 {now_str()}\n"
        f"👤 @{user.username or user.id}"
    )
    try:
        await bot.send_message(LOG_CHANNEL, text, parse_mode="HTML")
    except:
        pass

async def log_video_click(user: types.User, video_title: str, video_url: str, source: str):
    tag = get_hashtag(user)
    text = (
        f"▶️ <b>КЛИК ПО ВИДЕО</b> {tag}\n"
        f"🎬 {video_title}\n"
        f"🌐 {source}\n"
        f"🔗 {video_url}\n"
        f"🕐 {now_str()}"
    )
    try:
        await bot.send_message(LOG_CHANNEL, text, parse_mode="HTML")
    except:
        pass

# ── PDF досье ─────────────────────────────────────────────────────

def build_dossier_pdf(user_data: dict, events: list) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    BLACK = colors.HexColor("#1a1a1a")
    ORANGE = colors.HexColor("#ff9000")
    GRAY = colors.HexColor("#555555")
    LIGHTGRAY = colors.HexColor("#f0f0f0")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", fontSize=22, fontName="Helvetica-Bold",
                                  textColor=BLACK, alignment=TA_CENTER, spaceAfter=6)
    subtitle_style = ParagraphStyle("subtitle", fontSize=11, fontName="Helvetica",
                                     textColor=GRAY, alignment=TA_CENTER, spaceAfter=20)
    section_style = ParagraphStyle("section", fontSize=13, fontName="Helvetica-Bold",
                                    textColor=ORANGE, spaceBefore=16, spaceAfter=8)
    body_style = ParagraphStyle("body", fontSize=10, fontName="Helvetica",
                                 textColor=BLACK, spaceAfter=4, leading=16)
    mono_style = ParagraphStyle("mono", fontSize=9, fontName="Courier",
                                 textColor=GRAY, spaceAfter=3, leading=14)

    story = []

    # Заголовок
    story.append(Paragraph("rxmv<font color='#ff9000'>hub</font>", title_style))
    story.append(Paragraph("ДОСЬЕ ПОЛЬЗОВАТЕЛЯ", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=ORANGE))
    story.append(Spacer(1, 0.4*cm))

    # Основные данные
    story.append(Paragraph("ЛИЧНЫЕ ДАННЫЕ", section_style))

    uid = user_data.get("id", "—")
    uname = user_data.get("username", "—")
    name = user_data.get("name", "—")
    lang = user_data.get("language_code", "—")
    premium = "Да" if user_data.get("is_premium") else "Нет"
    first_seen = user_data.get("first_seen", "—")
    last_seen = user_data.get("last_seen", "—")
    visit_count = user_data.get("visit_count", 0)
    click_count = user_data.get("click_count", 0)

    info_data = [
        ["Поле", "Значение"],
        ["Имя", name],
        ["Username", f"@{uname}" if uname != "—" else "—"],
        ["Telegram ID", str(uid)],
        ["Язык", lang],
        ["Premium", premium],
        ["Первый вход", first_seen],
        ["Последний вход", last_seen],
        ["Всего визитов", str(visit_count)],
        ["Кликов по видео", str(click_count)],
    ]

    info_table = Table(info_data, colWidths=[5*cm, 11*cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ORANGE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 1), (-1, -1), LIGHTGRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHTGRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
    ]))
    story.append(info_table)

    # История активности
    if events:
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("ИСТОРИЯ АКТИВНОСТИ", section_style))
        story.append(HRFlowable(width="100%", thickness=1, color=LIGHTGRAY))
        story.append(Spacer(1, 0.2*cm))
        for ev in events[-50:]:
            story.append(Paragraph(ev, mono_style))

    # Футер
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=ORANGE))
    story.append(Paragraph(f"Сгенерировано: {now_str()} | rxmvhub", subtitle_style))

    doc.build(story)
    return buf.getvalue()

# ── Парсеры ───────────────────────────────────────────────────────

async def parse_sex_studentki(limit: int) -> list:
    videos = []
    page = 1
    async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        while len(videos) < limit:
            try:
                r = await client.get(f"https://sex-studentki.live/hq-porn/{page}/")
                soup = BeautifulSoup(r.text, "html.parser")
                items = soup.select(".video-item, .thumb, article, .item") or soup.select("a[href*='/video']")
                if not items:
                    break
                for item in items:
                    if len(videos) >= limit:
                        break
                    try:
                        a = item if item.name == "a" else item.find("a")
                        img = item.find("img")
                        title = (img.get("alt") or img.get("title") or "") if img else ""
                        href = a["href"] if a else ""
                        thumb = (img.get("data-src") or img.get("src", "")) if img else ""
                        if not title:
                            title = item.get_text(strip=True)[:80]
                        if href and title:
                            if not href.startswith("http"):
                                href = "https://sex-studentki.live" + href
                            if thumb and not thumb.startswith("http"):
                                thumb = "https://sex-studentki.live" + thumb
                            videos.append({"title": title.strip(), "url": href, "thumbnail": thumb, "source": "sex-studentki.live"})
                    except:
                        continue
                page += 1
                await asyncio.sleep(1)
            except:
                break
    return videos[:limit]

async def parse_rusoska(limit: int) -> list:
    videos = []
    page = 1
    async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        while len(videos) < limit:
            try:
                r = await client.get(f"https://rusoska.com/porno-cats/{page}/")
                soup = BeautifulSoup(r.text, "html.parser")
                items = soup.select(".video-item, .thumb, article, .item, .video_item") or soup.select("a[href*='/video'], a[href*='/porno']")
                if not items:
                    break
                for item in items:
                    if len(videos) >= limit:
                        break
                    try:
                        a = item if item.name == "a" else item.find("a")
                        img = item.find("img")
                        title = (img.get("alt") or img.get("title") or "") if img else ""
                        href = a["href"] if a else ""
                        thumb = (img.get("data-src") or img.get("src", "")) if img else ""
                        if not title:
                            title = item.get_text(strip=True)[:80]
                        if href and title:
                            if not href.startswith("http"):
                                href = "https://rusoska.com" + href
                            if thumb and not thumb.startswith("http"):
                                thumb = "https://rusoska.com" + thumb
                            videos.append({"title": title.strip(), "url": href, "thumbnail": thumb, "source": "rusoska.com"})
                    except:
                        continue
                page += 1
                await asyncio.sleep(1)
            except:
                break
    return videos[:limit]

async def parse_xhamster(limit: int) -> list:
    videos = []
    page = 1
    async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        while len(videos) < limit:
            try:
                r = await client.get(f"https://ru.xhamster.com/?page={page}")
                soup = BeautifulSoup(r.text, "html.parser")
                items = soup.select(".video-thumb, .thumb-list__item, article")
                if not items:
                    break
                for item in items:
                    if len(videos) >= limit:
                        break
                    try:
                        a = item.find("a")
                        img = item.find("img")
                        title_el = item.select_one(".video-thumb-info__name, .thumb-image-container__title")
                        title = title_el.get_text(strip=True) if title_el else (img.get("alt", "") if img else "")
                        href = a["href"] if a else ""
                        thumb = (img.get("data-src") or img.get("src", "")) if img else ""
                        if href and title:
                            if not href.startswith("http"):
                                href = "https://ru.xhamster.com" + href
                            videos.append({"title": title.strip(), "url": href, "thumbnail": thumb, "source": "xhamster.com"})
                    except:
                        continue
                page += 1
                await asyncio.sleep(1)
            except:
                break
    return videos[:limit]

async def parse_source(source: str, limit: int) -> list:
    if "sex-studentki" in source:
        return await parse_sex_studentki(limit)
    elif "rusoska" in source:
        return await parse_rusoska(limit)
    elif "xhamster" in source:
        return await parse_xhamster(limit)
    return []

# ── FSM ───────────────────────────────────────────────────────────

class ParseState(StatesGroup):
    choose_source = State()
    choose_count = State()

class DossierState(StatesGroup):
    choose_user = State()

# ── Helpers ───────────────────────────────────────────────────────

def is_admin(user_id: int, db: dict) -> bool:
    return user_id == OWNER_ID or user_id in db.get("admins", [])

def sources_keyboard(sources: list) -> ReplyKeyboardMarkup:
    buttons = [[KeyboardButton(text=s)] for s in sources]
    buttons.append([KeyboardButton(text="❌ Отмена")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

async def update_user_in_db(user: types.User, is_new: bool):
    try:
        db, sha = await github_get()
        users = db.setdefault("users_data", {})
        uid = str(user.id)
        now = now_str()
        name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        if uid not in users or is_new:
            users[uid] = {
                "id": user.id,
                "username": user.username or "",
                "name": name,
                "language_code": user.language_code or "",
                "is_premium": getattr(user, "is_premium", False),
                "first_seen": now,
                "last_seen": now,
                "visit_count": 1,
                "click_count": 0,
                "events": [f"[{now}] 🆕 Первый вход"]
            }
        else:
            users[uid]["last_seen"] = now
            users[uid]["visit_count"] = users[uid].get("visit_count", 0) + 1
            users[uid]["username"] = user.username or users[uid].get("username", "")
            users[uid]["name"] = name or users[uid].get("name", "")
            users[uid].setdefault("events", []).append(f"[{now}] 👁 Визит")
        # Обновляем список users (IDs)
        if user.id not in db.get("users", []):
            db.setdefault("users", []).append(user.id)
        db["users_data"] = users
        await github_save(db, sha)
    except Exception as e:
        print(f"update_user error: {e}")

async def log_click_in_db(user_id: int, video_title: str, video_url: str, source: str):
    try:
        db, sha = await github_get()
        uid = str(user_id)
        users = db.setdefault("users_data", {})
        if uid in users:
            now = now_str()
            users[uid]["click_count"] = users[uid].get("click_count", 0) + 1
            users[uid].setdefault("events", []).append(
                f"[{now}] ▶️ Клик: {video_title[:40]} ({source})"
            )
            db["users_data"] = users
            await github_save(db, sha)
    except Exception as e:
        print(f"log_click error: {e}")

# ── Commands ──────────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(msg: types.Message):
    user = msg.from_user
    db, _ = await github_get()
    is_new = str(user.id) not in db.get("users_data", {})
    await update_user_in_db(user, is_new)
    if is_new:
        await log_new_user(user)
    else:
        await log_visit(user)
    role = "👑 Создатель" if user.id == OWNER_ID else ("🛡 Админ" if is_admin(user.id, db) else "👤 Пользователь")
    await msg.answer(
        f"👋 Добро пожаловать в <b>rxmvhub</b>!\n\n"
        f"Твоя роль: {role}\n\n"
        f"<b>Команды:</b>\n"
        f"/parse — парсить видео\n"
        f"/sources — список сайтов\n"
        f"/addsource — добавить сайт\n"
        f"/removesource — удалить сайт\n"
        f"/users — список пользователей\n"
        f"/dossier — досье на пользователя\n"
        f"/addadmin ID — добавить админа\n"
        f"/removeadmin ID — удалить админа\n"
        f"/stats — статистика",
        parse_mode="HTML"
    )

@dp.message(Command("dossier"))
async def cmd_dossier(msg: types.Message):
    if msg.from_user.id != OWNER_ID:
        return await msg.answer("❌ Только создатель.")
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        return await msg.answer(
            "Использование:\n"
            "/dossier @username\n"
            "/dossier 123456789"
        )
    query = parts[1].strip().lstrip("@")
    db, _ = await github_get()
    users_data = db.get("users_data", {})
    found = None
    for uid, udata in users_data.items():
        if query.isdigit() and str(udata["id"]) == query:
            found = udata
            break
        elif not query.isdigit() and udata.get("username", "").lower() == query.lower():
            found = udata
            break
    if not found:
        return await msg.answer("❌ Пользователь не найден в базе.")
    await msg.answer("⏳ Генерирую досье...")
    try:
        events = found.get("events", [])
        pdf_bytes = build_dossier_pdf(found, events)
        name = found.get("username") or str(found.get("id"))
        await msg.answer_document(
            types.BufferedInputFile(pdf_bytes, filename=f"dossier_{name}.pdf"),
            caption=f"📋 Досье: @{found.get('username') or found.get('id')}\n{get_hashtag(types.User(id=found['id'], is_bot=False, first_name=found.get('name',''), username=found.get('username')))}"
        )
    except Exception as e:
        await msg.answer(f"❌ Ошибка генерации PDF: {e}")

@dp.message(Command("users"))
async def cmd_users(msg: types.Message):
    db, _ = await github_get()
    if not is_admin(msg.from_user.id, db):
        return await msg.answer("❌ Нет доступа.")
    users_data = db.get("users_data", {})
    if not users_data:
        return await msg.answer("Пользователей пока нет.")
    text = f"👥 <b>Пользователи ({len(users_data)}):</b>\n\n"
    for uid, u in users_data.items():
        uname = f"@{u['username']}" if u.get('username') else f"ID {u['id']}"
        text += f"• {uname} — визитов: {u.get('visit_count',0)}, кликов: {u.get('click_count',0)}\n"
    await msg.answer(text, parse_mode="HTML")

@dp.message(Command("stats"))
async def cmd_stats(msg: types.Message):
    db, _ = await github_get()
    videos = db.get("videos", [])
    sources = {}
    for v in videos:
        s = v.get("source", "unknown")
        sources[s] = sources.get(s, 0) + 1
    text = f"📊 <b>Статистика rxmvhub:</b>\n\n🎬 Всего видео: <b>{len(videos)}</b>\n\n"
    for s, c in sources.items():
        text += f"• {s}: {c}\n"
    text += f"\n👥 Пользователей: <b>{len(db.get('users_data', {}))}</b>"
    await msg.answer(text, parse_mode="HTML")

@dp.message(Command("sources"))
async def cmd_sources(msg: types.Message):
    db, _ = await github_get()
    sources = db.get("sources", KNOWN_SOURCES)
    text = "🌐 <b>Сайты:</b>\n" + "\n".join(f"• {s}" for s in sources)
    await msg.answer(text, parse_mode="HTML")

@dp.message(Command("addsource"))
async def cmd_addsource(msg: types.Message):
    db, _ = await github_get()
    if not is_admin(msg.from_user.id, db):
        return await msg.answer("❌ Нет доступа.")
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        return await msg.answer("Использование: /addsource rusoska.com")
    source = parts[1].strip().lower()
    db2, sha = await github_get()
    db2.setdefault("sources", KNOWN_SOURCES[:])
    if source in db2["sources"]:
        return await msg.answer("Уже есть.")
    db2["sources"].append(source)
    await github_save(db2, sha)
    await msg.answer(f"✅ {source} добавлен!")

@dp.message(Command("removesource"))
async def cmd_removesource(msg: types.Message):
    db, _ = await github_get()
    if not is_admin(msg.from_user.id, db):
        return await msg.answer("❌ Нет доступа.")
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        return await msg.answer("Использование: /removesource rusoska.com")
    source = parts[1].strip().lower()
    db2, sha = await github_get()
    sources = db2.get("sources", KNOWN_SOURCES[:])
    if source not in sources:
        return await msg.answer("Не найден.")
    sources.remove(source)
    db2["sources"] = sources
    await github_save(db2, sha)
    await msg.answer(f"✅ {source} удалён.")

@dp.message(Command("parse"))
async def cmd_parse(msg: types.Message, state: FSMContext):
    db, _ = await github_get()
    if not is_admin(msg.from_user.id, db):
        return await msg.answer("❌ Нет доступа.")
    sources = db.get("sources", KNOWN_SOURCES)
    await state.set_state(ParseState.choose_source)
    await msg.answer("🌐 Выбери сайт:", reply_markup=sources_keyboard(sources))

@dp.message(ParseState.choose_source)
async def parse_choose_source(msg: types.Message, state: FSMContext):
    if msg.text == "❌ Отмена":
        await state.clear()
        return await msg.answer("Отменено.", reply_markup=ReplyKeyboardRemove())
    db, _ = await github_get()
    sources = db.get("sources", KNOWN_SOURCES)
    if msg.text not in sources:
        return await msg.answer("Выбери из списка!")
    await state.update_data(source=msg.text)
    await state.set_state(ParseState.choose_count)
    await msg.answer(f"📊 Сколько видео? (1-500)", reply_markup=ReplyKeyboardRemove())

@dp.message(ParseState.choose_count)
async def parse_choose_count(msg: types.Message, state: FSMContext):
    if not msg.text.isdigit() or not (1 <= int(msg.text) <= 500):
        return await msg.answer("Введи число от 1 до 500!")
    count = int(msg.text)
    data = await state.get_data()
    source = data["source"]
    await state.clear()
    status = await msg.answer(f"⏳ Парсю {count} видео с {source}...")
    try:
        videos = await parse_source(source, count)
        if not videos:
            return await status.edit_text("😔 Ничего не нашёл.")
        db, sha = await github_get()
        existing = {v["url"] for v in db.get("videos", [])}
        new = [v for v in videos if v["url"] not in existing]
        next_id = max((v["id"] for v in db.get("videos", [])), default=0) + 1
        for v in new:
            v["id"] = next_id
            next_id += 1
        db.setdefault("videos", []).extend(new)
        await github_save(db, sha)
        await status.edit_text(f"✅ Готово!\n📥 Найдено: {len(videos)}\n🆕 Добавлено: {len(new)}\n♻️ Дубликатов: {len(videos)-len(new)}")
    except Exception as e:
        await status.edit_text(f"❌ Ошибка: {e}")

@dp.message(Command("addadmin"))
async def cmd_addadmin(msg: types.Message):
    if msg.from_user.id != OWNER_ID:
        return await msg.answer("❌ Только создатель.")
    parts = msg.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await msg.answer("Использование: /addadmin 123456789")
    new_id = int(parts[1])
    db, sha = await github_get()
    db.setdefault("admins", [])
    if new_id in db["admins"]:
        return await msg.answer("Уже админ.")
    db["admins"].append(new_id)
    await github_save(db, sha)
    await msg.answer(f"✅ {new_id} назначен админом!")

@dp.message(Command("removeadmin"))
async def cmd_removeadmin(msg: types.Message):
    if msg.from_user.id != OWNER_ID:
        return await msg.answer("❌ Только создатель.")
    parts = msg.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await msg.answer("Использование: /removeadmin 123456789")
    rem_id = int(parts[1])
    db, sha = await github_get()
    if rem_id not in db.get("admins", []):
        return await msg.answer("Не является админом.")
    db["admins"].remove(rem_id)
    await github_save(db, sha)
    await msg.answer(f"✅ {rem_id} удалён.")

# ── Webhook для кликов с сайта ────────────────────────────────────

@dp.message(F.text.startswith("/click"))
async def handle_click(msg: types.Message):
    # Формат: /click VIDEO_ID USER_ID
    parts = msg.text.split()
    if len(parts) < 3:
        return
    try:
        vid_id = int(parts[1])
        uid = int(parts[2])
        db, _ = await github_get()
        video = next((v for v in db.get("videos", []) if v["id"] == vid_id), None)
        if not video:
            return
        user_data = db.get("users_data", {}).get(str(uid))
        if user_data:
            fake_user = types.User(id=uid, is_bot=False, first_name=user_data.get("name",""), username=user_data.get("username"))
            await log_video_click(fake_user, video["title"], video["url"], video.get("source",""))
        await log_click_in_db(uid, video["title"], video["url"], video.get("source",""))
    except:
        pass

# ── Автопарсинг ───────────────────────────────────────────────────

async def auto_parse_on_start():
    try:
        db, sha = await github_get()
        if db.get("initial_parse_done"):
            return
        await bot.send_message(OWNER_ID, "🚀 Начинаю первоначальный сбор 100 видео с каждого сайта...")
        sources = db.get("sources", KNOWN_SOURCES)
        all_new = []
        for source in sources:
            try:
                await bot.send_message(OWNER_ID, f"⏳ Парсю {source}...")
                videos = await parse_source(source, 100)
                all_new.extend(videos)
                await bot.send_message(OWNER_ID, f"✅ {source}: {len(videos)} видео")
            except Exception as e:
                await bot.send_message(OWNER_ID, f"❌ {source}: {e}")
        db2, sha2 = await github_get()
        existing = {v["url"] for v in db2.get("videos", [])}
        new = [v for v in all_new if v["url"] not in existing]
        next_id = max((v["id"] for v in db2.get("videos", [])), default=0) + 1
        for v in new:
            v["id"] = next_id
            next_id += 1
        db2.setdefault("videos", []).extend(new)
        db2["initial_parse_done"] = True
        db2.setdefault("sources", KNOWN_SOURCES)
        await github_save(db2, sha2)
        await bot.send_message(OWNER_ID, f"🎉 Готово! Добавлено {len(new)} видео.")
    except Exception as e:
        try:
            await bot.send_message(OWNER_ID, f"❌ Ошибка автопарсинга: {e}")
        except:
            pass

async def main():
    asyncio.create_task(auto_parse_on_start())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
PYEOF
echo "Done"
