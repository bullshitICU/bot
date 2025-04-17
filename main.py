import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackContext, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters, ContextTypes
)

BOT_TOKEN = "7835423403:AAFXzA4ieCone_309bA6HD1sDsNkbSfY7jg"
ADMIN_ID = 1489701727
CHANNEL_USERNAME = "@ReamyEarn"

DATA_FILE = "users.json"
(
    SET_WALLET_TYPE,
    SET_WALLET_INPUT
) = range(2)

user_data = {}

def load_data():
    global user_data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            user_data = json.load(f)
    else:
        user_data["tasks"] = []

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(user_data, f)

def get_user(user_id):
    uid = str(user_id)
    if uid not in user_data:
        user_data[uid] = {
            "balance": 0.0,
            "wallet": None,
            "referrer": None,
            "tasks_done": [],
            "referral_earnings": 0.0,
            "referrals": [],
            "language": None
        }
    return user_data[uid]

def get_next_tasks(user_id, limit=5):
    all_tasks = user_data.get("tasks", [])
    done = get_user(user_id)["tasks_done"]
    return [t for t in all_tasks if t not in done][:limit]

async def is_member(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    try:
        chat_member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args = context.args

    if user_id not in user_data:
        user_data[user_id] = {
            "balance": 0.0,
            "wallet": None,
            "referrer": None,
            "tasks_done": [],
            "referral_earnings": 0.0,
            "referrals": [],
            "language": None
        }
        if args:
            ref = args[0]
            if ref != user_id and ref in user_data:
                user_data[user_id]["referrer"] = ref
                user_data[ref]["referrals"].append(user_id)

    save_data()

    if not await is_member(update, context):
        join_btn = [[InlineKeyboardButton("Join @ReamyEarn", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]]
        await update.message.reply_text("Please join our channel to use the bot.", reply_markup=InlineKeyboardMarkup(join_btn))
        return

    keyboard = [
        [InlineKeyboardButton("English", callback_data="lang_en")],
        [InlineKeyboardButton("Arabic", callback_data="lang_ar")]
    ]
    await update.message.reply_text("Choose your language / اختر لغتك:", reply_markup=InlineKeyboardMarkup(keyboard))

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = get_user(query.from_user.id)

    lang = "English" if query.data == "lang_en" else "Arabic"
    user["language"] = lang
    save_data()
    await show_main_menu(query, context)

async def show_main_menu(update_or_query, context):
    keyboard = [
        [InlineKeyboardButton("Tasks", callback_data="tasks")],
        [InlineKeyboardButton("Check Balance", callback_data="balance")],
        [InlineKeyboardButton("Referral", callback_data="referral")],
        [InlineKeyboardButton("Set Wallet", callback_data="set_wallet")],
        [InlineKeyboardButton("Withdraw", callback_data="withdraw")]
    ]
    if isinstance(update_or_query, Update):
        await update_or_query.message.reply_text("Main Menu:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update_or_query.edit_message_text("Main Menu:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user = get_user(user_id)

    if query.data == "tasks":
        tasks = get_next_tasks(user_id)
        if not tasks:
            await query.edit_message_text("No tasks available. Come back later.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main")]]))
            return

        btns = [[InlineKeyboardButton(f"Task {i+1}", url=task, callback_data=f"task_{i}")] for i, task in enumerate(tasks)]
        btns.append([InlineKeyboardButton("Refresh Tasks", callback_data="tasks")])
        btns.append([InlineKeyboardButton("Go Back", callback_data="main")])
        await query.edit_message_text("Available Tasks:", reply_markup=InlineKeyboardMarkup(btns))

    elif query.data.startswith("task_"):
        task_index = int(query.data.split("_")[1])
        tasks = get_next_tasks(user_id)
        if task_index < len(tasks):
            task_url = tasks[task_index]
            user["tasks_done"].append(task_url)
            user["balance"] += 0.1

            ref = user.get("referrer")
            if ref and ref in user_data:
                user_data[ref]["balance"] += 0.01
                user_data[ref]["referral_earnings"] += 0.01

            save_data()
            await query.edit_message_text(f"Task Completed!\nYou earned $0.10", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main")]]))
        else:
            await query.edit_message_text("Invalid task.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main")]]))

    elif query.data == "balance":
        await query.edit_message_text(f"Your balance: ${user['balance']:.2f}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main")]]))

    elif query.data == "referral":
        link = f"https://t.me/{context.bot.username}?start={user_id}"
        count = len(user.get("referrals", []))
        earned = user.get("referral_earnings", 0)
        text = f"Your referral link:\n{link}\n\nReferrals: {count}\nReferral earnings: ${earned:.2f}"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main")]]))

    elif query.data == "set_wallet":
        keyboard = [
            [InlineKeyboardButton("USDT (TRC20)", callback_data="wallet_trc20")],
            [InlineKeyboardButton("USDC (ERC20)", callback_data="wallet_usdc")],
            [InlineKeyboardButton("PayPal Email", callback_data="wallet_paypal")],
            [InlineKeyboardButton("Go Back", callback_data="main")]
        ]
        await query.edit_message_text("Select wallet type:", reply_markup=InlineKeyboardMarkup(keyboard))
        return SET_WALLET_TYPE

    elif query.data == "withdraw":
        if not user["wallet"]:
            await query.edit_message_text("Please set your wallet first.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main")]]))
        elif user["balance"] < 50:
            await query.edit_message_text(f"Minimum to withdraw is $50. You have ${user['balance']:.2f}.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main")]]))
        else:
            await context.bot.send_message(ADMIN_ID, f"Withdraw request from {user_id}\nBalance: ${user['balance']:.2f}\nWallet: {user['wallet']['type']} - {user['wallet']['address']}")
            await query.edit_message_text("Withdrawal request sent to admin.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Go Back", callback_data="main")]]))

    elif query.data == "main":
        await show_main_menu(query, context)

    return ConversationHandler.END

async def wallet_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    wallet_type = query.data.replace("wallet_", "")
    context.user_data["wallet_type"] = wallet_type.upper()
    await query.edit_message_text(f"Send your {context.user_data['wallet_type']} address/email now:")
    return SET_WALLET_INPUT

async def wallet_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    wallet_type = context.user_data.get("wallet_type", "UNKNOWN")
    address = update.message.text

    user["wallet"] = {
        "type": wallet_type,
        "address": address
    }
    save_data()

    await update.message.reply_text(
        f"Wallet saved:\nType: {wallet_type}\nAddress: {address}"
    )
    await show_main_menu(update, context)
    return ConversationHandler.END

async def addtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("You are not allowed.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /addtask <url>")
        return
    link = context.args[0]
    user_data.setdefault("tasks", []).append(link)
    save_data()
    await update.message.reply_text("Task added.")

def main():
    load_data()
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button)],
        states={
            SET_WALLET_TYPE: [CallbackQueryHandler(wallet_type_handler, pattern="^wallet_")],
            SET_WALLET_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_input_handler)],
        },
        fallbacks=[],
        per_message=True
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addtask", addtask))
    app.add_handler(CallbackQueryHandler(set_language, pattern="^lang_"))
    app.add_handler(conv)

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
