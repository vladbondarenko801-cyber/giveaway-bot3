"""
🎉 Telegram Giveaway Bot
- Кнопка "Участвовать" со счётчиком
- Проверка подписки на канал
- Результаты отправляются только админу
- Многоразовый: можно запускать сколько угодно розыгрышей
"""

import logging
import random
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from telegram.error import TelegramError

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)

BOT_TOKEN  = "8636624423:AAFYuUCCTFLOGDwKQMySWks_0C8ej5UxRgk"
CHANNEL_ID = "@givewaytestWNM"
ADMIN_ID   = 7814917590

giveaways: dict = {}
giveaway_counter: int = 0


def build_keyboard(giveaway_id: int, count: int, active: bool) -> InlineKeyboardMarkup:
    if active:
        label = f"🎟 Участвовать  |  👥 {count}"
        btn = InlineKeyboardButton(label, callback_data=f"join:{giveaway_id}")
    else:
        label = f"🔒 Розыгрыш завершён  |  👥 {count}"
        btn = InlineKeyboardButton(label, callback_data="closed")
    return InlineKeyboardMarkup([[btn]])


async def is_subscribed(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except TelegramError:
        return False


def user_display(user) -> tuple:
    name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Без имени"
    username = f"@{user.username}" if user.username else "нет username"
    return name, username


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот для розыгрышей.\n\n"
        "📋 <b>Команды:</b>\n"
        "/new_giveaway &lt;приз&gt; — создать новый розыгрыш\n"
        "/end_giveaway &lt;ID&gt; — завершить розыгрыш и выбрать победителя\n"
        "/list — список всех розыгрышей\n"
        "/participants &lt;ID&gt; — список участников\n\n"
        "Пример: /new_giveaway iPhone 15 Pro",
        parse_mode="HTML",
    )


async def cmd_new_giveaway(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Только администратор может создавать розыгрыши.")
        return

    prize = " ".join(ctx.args).strip() if ctx.args else ""
    if not prize:
        await update.message.reply_text("⚠️ Укажите приз.\nПример: /new_giveaway AirPods Pro")
        return

    global giveaway_counter
    giveaway_counter += 1
    gid = giveaway_counter

    keyboard = build_keyboard(gid, 0, active=True)
    text = (
        f"🎉 <b>РОЗЫГРЫШ #{gid}</b>\n\n"
        f"🏆 Приз: <b>{prize}</b>\n\n"
        f"📌 Условия участия:\n"
        f"• Подпишитесь на канал\n"
        f"• Нажмите кнопку <b>«Участвовать»</b>\n\n"
        f"Победитель будет выбран случайно 🎲"
    )

    try:
        msg = await ctx.bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ Не удалось отправить в канал:\n{e}")
        return

    giveaways[gid] = {
        "message_id": msg.message_id,
        "chat_id": msg.chat.id,
        "prize": prize,
        "participants": {},
        "active": True,
    }

    await update.message.reply_text(
        f"✅ Розыгрыш <b>#{gid}</b> создан и опубликован!\n"
        f"🏆 Приз: {prize}\n\n"
        f"Завершить: /end_giveaway {gid}",
        parse_mode="HTML",
    )


async def cmd_end_giveaway(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Только администратор может завершать розыгрыши.")
        return

    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text("⚠️ Укажите ID розыгрыша.\nПример: /end_giveaway 1")
        return

    gid = int(ctx.args[0])
    gw = giveaways.get(gid)

    if not gw:
        await update.message.reply_text(f"❌ Розыгрыш #{gid} не найден.")
        return
    if not gw["active"]:
        await update.message.reply_text(f"⚠️ Розыгрыш #{gid} уже завершён.")
        return

    gw["active"] = False
    participants = gw["participants"]
    count = len(participants)

    keyboard = build_keyboard(gid, count, active=False)
    try:
        await ctx.bot.edit_message_reply_markup(
            chat_id=gw["chat_id"],
            message_id=gw["message_id"],
            reply_markup=keyboard,
        )
    except TelegramError:
        pass

    if not participants:
        await ctx.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"😔 <b>Розыгрыш #{gid} завершён</b>\n\n"
                f"🏆 Приз: {gw['prize']}\n"
                f"Участников не было — победитель не определён."
            ),
            parse_mode="HTML",
        )
        return

    winner_id = random.choice(list(participants.keys()))
    winner = participants[winner_id]

    parts_list = "\n".join(
        f"{i+1}. {p['name']} ({p['username']})"
        for i, p in enumerate(participants.values())
    )

    result_text = (
        f"🏆 <b>РЕЗУЛЬТАТЫ РОЗЫГРЫША #{gid}</b>\n\n"
        f"🎁 Приз: {gw['prize']}\n"
        f"👥 Всего участников: {count}\n\n"
        f"🥇 <b>ПОБЕДИТЕЛЬ:</b>\n"
        f"   {winner['name']} ({winner['username']})\n"
        f"   ID: <code>{winner_id}</code>\n\n"
        f"📋 <b>Все участники:</b>\n{parts_list}"
    )

    await ctx.bot.send_message(
        chat_id=ADMIN_ID,
        text=result_text,
        parse_mode="HTML",
    )

    await update.message.reply_text(
        f"✅ Розыгрыш <b>#{gid}</b> завершён!\n"
        f"Результаты отправлены вам выше 👆",
        parse_mode="HTML",
    )


async def cmd_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not giveaways:
        await update.message.reply_text("📭 Розыгрышей пока нет.")
        return

    lines = []
    for gid, gw in giveaways.items():
        status = "✅ Активен" if gw["active"] else "🔒 Завершён"
        lines.append(f"#{gid} | {status} | 🏆 {gw['prize']} | 👥 {len(gw['participants'])}")

    await update.message.reply_text(
        "📋 <b>Все розыгрыши:</b>\n\n" + "\n".join(lines),
        parse_mode="HTML",
    )


async def cmd_participants(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text("Пример: /participants 1")
        return

    gid = int(ctx.args[0])
    gw = giveaways.get(gid)

    if not gw:
        await update.message.reply_text(f"❌ Розыгрыш #{gid} не найден.")
        return

    participants = gw["participants"]
    if not participants:
        await update.message.reply_text(f"👥 В розыгрыше #{gid} пока нет участников.")
        return

    lines = [
        f"{i+1}. {p['name']} ({p['username']})"
        for i, p in enumerate(participants.values())
    ]
    await update.message.reply_text(
        f"👥 <b>Участники розыгрыша #{gid}</b> ({len(lines)} чел.):\n\n" + "\n".join(lines),
        parse_mode="HTML",
    )


async def handle_join(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "closed":
        await query.answer("🔒 Розыгрыш уже завершён.", show_alert=True)
        return

    gid = int(data.split(":")[1])
    gw = giveaways.get(gid)

    if not gw or not gw["active"]:
        await query.answer("🔒 Розыгрыш уже завершён.", show_alert=True)
        return

    user = query.from_user
    user_id = user.id

    if user_id in gw["participants"]:
        await query.answer("✅ Вы уже участвуете в этом розыгрыше!", show_alert=True)
        return

    subscribed = await is_subscribed(ctx.bot, user_id)
    if not subscribed:
        await query.answer(
            f"❌ Вы не подписаны на канал!\n"
            f"Подпишитесь на {CHANNEL_ID} и нажмите кнопку снова.",
            show_alert=True,
        )
        return

    name, username = user_display(user)
    gw["participants"][user_id] = {"name": name, "username": username}
    count = len(gw["participants"])

    keyboard = build_keyboard(gid, count, active=True)
    try:
        await ctx.bot.edit_message_reply_markup(
            chat_id=gw["chat_id"],
            message_id=gw["message_id"],
            reply_markup=keyboard,
        )
    except TelegramError:
        pass

    await query.answer(
        f"🎉 Вы зарегистрированы!\nВсего участников: {count}",
        show_alert=True,
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",         cmd_start))
    app.add_handler(CommandHandler("new_giveaway",  cmd_new_giveaway))
    app.add_handler(CommandHandler("end_giveaway",  cmd_end_giveaway))
    app.add_handler(CommandHandler("list",          cmd_list))
    app.add_handler(CommandHandler("participants",  cmd_participants))
    app.add_handler(CallbackQueryHandler(handle_join))

    logging.info("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
