"""
YouTube Search Telegram Bot
────────────────────────────
Commands:
  /start             – Welcome message & instructions
  /search <query>    – Search YouTube and get 5 video links

Each result has one button:
  📥 Download TXT  – sends the subtitle as a downloadable .txt file

After every search a repeat button appears at the bottom.
"""

import os
import re
import logging
import asyncio
import tempfile

import yt_dlp

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

BOT_TOKEN    = os.environ["BOT_TOKEN"]
RESULT_COUNT = 5

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
logging.getLogger("yt_dlp").setLevel(logging.ERROR)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

ACTIVE_CHAT_MESSAGES_KEY = "active_chat_message_ids"


def remember_message_id(
    context: ContextTypes.DEFAULT_TYPE, message_id: int | None
) -> None:
    if message_id is None:
        return
    ids = context.user_data.setdefault(ACTIVE_CHAT_MESSAGES_KEY, [])
    if message_id not in ids:
        ids.append(message_id)


async def delete_message_by_id(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int | None
) -> None:
    if message_id is None:
        return
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as exc:
        logger.debug("Could not delete message %s: %s", message_id, exc)


async def delete_incoming_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    chat    = update.effective_chat
    message = update.message
    if not chat or not message:
        return
    await delete_message_by_id(context, chat.id, message.message_id)


async def clear_previous_messages(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    chat = update.effective_chat
    if not chat:
        return
    for mid in context.user_data.get(ACTIVE_CHAT_MESSAGES_KEY, []):
        await delete_message_by_id(context, chat.id, mid)
    context.user_data[ACTIVE_CHAT_MESSAGES_KEY] = []


# ──────────────────────────────────────────────
# YouTube search
# ──────────────────────────────────────────────

def search_youtube(query: str) -> list:
    ydl_opts = {
        "quiet":         True,
        "no_warnings":   True,
        "extract_flat":  True,
        "skip_download": True,
    }
    results = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch{RESULT_COUNT}:{query}", download=False)
        for entry in info.get("entries", []):
            if not entry:
                continue
            video_id     = entry.get("id", "")
            duration     = entry.get("duration")
            duration_str = ""
            if duration:
                mins, secs = divmod(int(duration), 60)
                duration_str = f"{mins}:{secs:02d}"
            results.append({
                "title":    entry.get("title", "Unknown title"),
                "url":      f"https://www.youtube.com/watch?v={video_id}",
                "video_id": video_id,
                "channel":  entry.get("channel") or entry.get("uploader", ""),
                "duration": duration_str,
            })
    return results


# ──────────────────────────────────────────────
# Subtitle download & text extraction
# ──────────────────────────────────────────────

def download_subtitle(video_url: str, tmpdir: str) -> str | None:
    """Download subtitle as VTT (no FFmpeg needed). Returns .vtt path or None."""

    def _try(sub_langs: list[str]) -> str | None:
        ydl_opts = {
            "quiet":             True,
            "no_warnings":       True,
            "skip_download":     True,
            "writesubtitles":    True,
            "writeautomaticsub": True,
            "subtitleslangs":    sub_langs,
            "subtitlesformat":   "vtt",
            "outtmpl": os.path.join(tmpdir, "%(title)s.%(ext)s"),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        for fname in os.listdir(tmpdir):
            if fname.endswith(".vtt"):
                return os.path.join(tmpdir, fname)
        return None

    return _try(["en", "en-US", "en-GB"]) or _try(["all"])


def extract_subtitle_text(vtt_path: str) -> str:
    """Parse a VTT file and return clean plain text without timestamps."""
    with open(vtt_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    blocks         = []
    previous_block = None

    for block in re.split(r"\r?\n\r?\n+", content):
        # Skip header/metadata blocks (anything without a timestamp line)
        if "-->" not in block:
            continue
        lines = []
        for raw in block.splitlines():
            line = raw.strip()
            if not line or "-->" in line:
                continue
            clean = re.sub(r"<[^>]+>",  "", line)   # strip inline tags
            clean = re.sub(r"&\w+;",    " ", clean)  # strip HTML entities
            clean = re.sub(r"\s+",      " ", clean).strip()
            if clean:
                lines.append(clean)
        if not lines:
            continue
        merged = " ".join(lines)
        if merged != previous_block:
            blocks.append(merged)
            previous_block = merged

    return "\n".join(blocks).strip()


def build_txt_file(title: str, text: str, tmpdir: str) -> str:
    """Write transcript to a .txt file and return its path."""
    safe_name = re.sub(r'[\\/*?:"<>|]', "_", title)[:80]
    path = os.path.join(tmpdir, f"{safe_name}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"{title}\n")
        f.write("=" * len(title) + "\n\n")
        f.write(text)
    return path


# ──────────────────────────────────────────────
# Message builders
# ──────────────────────────────────────────────

def build_result_message(video: dict, index: int):
    duration = f"⏱ {video['duration']}" if video["duration"] else ""
    channel  = f"📺 {video['channel']}"  if video["channel"]  else ""
    meta     = f"{channel}  {duration}".strip() if (channel or duration) else ""

    text = f"{index}. <b>{video['title']}</b>"
    if meta:
        text += f"\n{meta}"
    text += f"\n{video['url']}"

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "📥 Download TXT",
            callback_data=f"txt|{video['video_id']}",
        ),
    ]])
    return text, keyboard


def build_repeat_button(last_query: str) -> InlineKeyboardMarkup:
    label = (last_query[:28] + "…") if len(last_query) > 28 else last_query
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(f"🔁 Repeat: {label}", callback_data="repeat"),
    ]])


# ──────────────────────────────────────────────
# Command handlers
# ──────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await clear_previous_messages(update, context)
    await delete_incoming_message(update, context)
    text = (
        "👋 <b>Welcome to YouTube Search Bot!</b>\n\n"
        "📌 <b>Commands:</b>\n"
        "  /search <i>&lt;query&gt;</i>  – search YouTube\n\n"
        "Or just <b>type anything</b> to search directly."
    )
    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode="HTML",
    )
    remember_message_id(context, msg.message_id)


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args).strip()
    if not query:
        await clear_previous_messages(update, context)
        await delete_incoming_message(update, context)
        msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please provide a search query.\nExample: /search python tutorial",
        )
        remember_message_id(context, msg.message_id)
        return
    await _do_search(update, context, query)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.message.text.strip()
    if query.startswith("/"):
        return
    await _do_search(update, context, query)


async def _do_search(
    update: Update, context: ContextTypes.DEFAULT_TYPE, query: str
) -> None:
    await clear_previous_messages(update, context)
    await delete_incoming_message(update, context)

    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"🔎 Searching for <b>{query}</b> …",
        parse_mode="HTML",
    )
    remember_message_id(context, msg.message_id)

    try:
        loop   = asyncio.get_running_loop()
        videos = await loop.run_in_executor(None, search_youtube, query)
    except Exception as e:
        logger.error("Search error: %s", e)
        await msg.edit_text("❌ Search failed. Please try again.")
        return

    if not videos:
        await msg.edit_text("😕 No results found. Try a different query.")
        return

    context.user_data["last_results"] = {v["video_id"]: v for v in videos}
    context.user_data["last_query"]   = query

    await msg.edit_text(
        f"🔍 <b>Results for:</b> <i>{query}</i>  ({len(videos)} videos)",
        parse_mode="HTML",
    )

    for i, v in enumerate(videos, start=1):
        result_text, keyboard = build_result_message(v, i)
        result_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=result_text,
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_web_page_preview=False,
        )
        remember_message_id(context, result_msg.message_id)

    repeat_msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🔁 <b>Search again?</b>",
        parse_mode="HTML",
        reply_markup=build_repeat_button(query),
    )
    remember_message_id(context, repeat_msg.message_id)


# ──────────────────────────────────────────────
# Button – Download TXT  (prefix: txt|)
# ──────────────────────────────────────────────

async def callback_download_txt(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer("⏳ Preparing TXT file…")

    _, video_id = query.data.split("|", 1)
    chat_id     = query.message.chat_id

    results    = context.user_data.get("last_results", {})
    video_info = results.get(video_id)
    title      = video_info["title"] if video_info else "video"

    status_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"⏳ Downloading subtitle for <b>{title}</b>…",
        parse_mode="HTML",
    )

    loop      = asyncio.get_running_loop()
    video_url = video_info["url"] if video_info else f"https://www.youtube.com/watch?v={video_id}"

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            srt_path = await loop.run_in_executor(
                None, download_subtitle, video_url, tmpdir
            )
        except Exception as e:
            logger.error("Subtitle download error: %s", e)
            await status_msg.edit_text("❌ Failed to download subtitle.")
            return

        if not srt_path:
            await status_msg.edit_text(
                "😕 No subtitle available for this video.\n"
                "(It may not have auto-generated or manual captions.)"
            )
            return

        try:
            transcript = await loop.run_in_executor(None, extract_subtitle_text, srt_path)
        except Exception as e:
            logger.error("SRT extraction error: %s", e)
            await status_msg.edit_text("❌ Failed to read subtitle file.")
            return

        if not transcript:
            await status_msg.edit_text("😕 Subtitle file was empty.")
            return

        try:
            txt_path = await loop.run_in_executor(
                None, build_txt_file, title, transcript, tmpdir
            )
        except Exception as e:
            logger.error("TXT write error: %s", e)
            await status_msg.edit_text("❌ Failed to create TXT file.")
            return

        await status_msg.delete()
        with open(txt_path, "rb") as f:
            await context.bot.send_document(
                chat_id=chat_id,
                document=f,
                filename=os.path.basename(txt_path),
            )


# ──────────────────────────────────────────────
# Button – repeat last search
# ──────────────────────────────────────────────

async def callback_repeat(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query      = update.callback_query
    last_query = context.user_data.get("last_query")

    if not last_query:
        await query.answer("No previous search.")
        return

    await query.answer("🔁 Searching again…")
    await _do_search(update, context, last_query)


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CallbackQueryHandler(callback_download_txt, pattern=r"^txt\|"))
    app.add_handler(CallbackQueryHandler(callback_repeat,       pattern=r"^repeat$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot is running…")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
