# -*- coding: utf-8 -*-
import telebot, random
from telebot import types

# === CONFIG ===
BOT_TOKEN = "8164680356:AAF0XQwdtArAKURSs1dwJ3kVOH9klDjw3fc"
ADMIN_ID  = 8171444846
UPI_ID    = "mohd.kaifu@sbi"

bot = telebot.TeleBot(BOT_TOKEN)

# === STORAGE (in-memory) ===
user_credits = {}         # {user_id: credits}
username_numbers = {}     # {"@uname": "+91 ..."}
claimed_referral = set()  # users who already claimed +5 once
admin_state = {}          # {admin_id: {"mode": "..."}}

# === HELPERS ===
def ensure_user(uid):
    if uid not in user_credits:
        user_credits[uid] = 3

def rand_mobile():
    return "+91 " + str(random.randint(6345678901, 9876543210))

def calc_price(n):
    if n <= 100:
        r = 2.0
    elif n <= 1000:
        r = 1.5
    else:
        r = 1.0
    return n * r, r

def out_of_credits(chat_id):
    msg = (
        "❌ *Credits Khatam!*\n\n"
        "💳 *Rate Chart*\n"
        "• 1–100 = ₹2/credit\n"
        "• 101–1000 = ₹1.5/credit\n"
        "• 1001+ = ₹1/credit\n\n"
        f"📲 Pay via UPI: `{UPI_ID}`\n"
        "👉 `/buy` ya `/buy 150` likhkar price dekho."
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💳 Buy Credits", callback_data="rates"))
    kb.add(types.InlineKeyboardButton("📩 Contact Admin", url=f"tg://user?id={ADMIN_ID}"))
    bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=kb)

# === START + REFERRAL ===
@bot.message_handler(commands=['start'])
def start_cmd(m):
    uid = m.from_user.id
    ensure_user(uid)

    # referral: /start <ref_id> ; both sides get +5 once
    parts = m.text.split(maxsplit=1)
    if len(parts) == 2:
        try:
            ref_id = int(parts[1])
            if ref_id != uid and uid not in claimed_referral:
                claimed_referral.add(uid)
                ensure_user(ref_id)
                user_credits[uid] += 5
                user_credits[ref_id] += 5
                bot.send_message(uid,     f"🎉 Referral se +5 credits mil gaye! Total: {user_credits[uid]}")
                bot.send_message(ref_id,  f"🎉 Aapko ek referral mila! +5 credits. Total: {user_credits[ref_id]}")
        except:
            pass

    txt = (
        f"👋 Welcome {m.from_user.first_name or ''}!\n\n"
        "🎁 Pehli baar 3 Free Credits mil gaye.\n\n"
        "Commands:\n"
        "• /username \n"
        "• /credits – apne credits\n"
        "• /refer – referral link (+5)\n"
        "• /buy  or  /buycredits – rate & price\n"
        "• /myid – apna Telegram ID\n"
        "• /admin – admin/help"
    )
    bot.send_message(m.chat.id, txt)

# === BASICS ===
@bot.message_handler(commands=['myid'])
def myid(m):
    bot.send_message(m.chat.id, f"🆔 `{m.from_user.id}`", parse_mode="Markdown")

@bot.message_handler(commands=['credits'])
def credits(m):
    ensure_user(m.from_user.id)
    bot.send_message(m.chat.id, f"💳 Aapke paas {user_credits[m.from_user.id]} credits hain.")

@bot.message_handler(commands=['refer'])
def refer(m):
    ensure_user(m.from_user.id)
    link = f"https://t.me/{bot.get_me().username}?start={m.from_user.id}"
    bot.send_message(m.chat.id, f"📢 Referral link (dono ko +5):\n{link}")

# === BUY / RATES ===
@bot.message_handler(commands=['buy','buycredit','buycredits'])
def buy(m):
    msg = (
        "💳 *Credit Rate Chart*\n\n"
        "• 1–100 = ₹2/credit\n"
        "• 101–1000 = ₹1.5/credit\n"
        "• 1001+ = ₹1/credit\n\n"
        "🧮 Example:\n"
        "/buy 50  → ₹100\n"
        "/buy 150 → ₹225\n"
        "/buy 1200 → ₹1200\n\n"
        f"📲 Pay via UPI: `{UPI_ID}`\n"
        "Payment ke baad `/myid` bhejein."
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📩 Contact Admin", url=f"tg://user?id={ADMIN_ID}"))
    bot.send_message(m.chat.id, msg, parse_mode="Markdown", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text.lower().startswith("/buy ") and len(m.text.split())==2 and m.text.split()[1].isdigit())
def buy_calc(m):
    n = int(m.text.split()[1])
    if n <= 0:
        bot.send_message(m.chat.id, "⚠️ Credits 1 se zyada honi chahiye.")
        return
    price, rate = calc_price(n)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📩 Contact Admin", url=f"tg://user?id={ADMIN_ID}"))
    bot.send_message(
        m.chat.id,
        f"🛒 *Purchase Summary*\n\nCredits: {n}\nRate: ₹{rate}/credit\nPrice: ₹{int(price) if price.is_integer() else price:.2f}\n\n"
        f"📲 UPI: `{UPI_ID}`\nPayment ke baad `/myid` bhejein.",
        parse_mode="Markdown",
        reply_markup=kb
    )

# === USERNAME LOOKUP ===
@bot.message_handler(commands=['username'])
def username_cmd(m):
    ensure_user(m.from_user.id)
    if user_credits[m.from_user.id] <= 0:
        out_of_credits(m.chat.id); return
    parts = m.text.split(maxsplit=1)
    if len(parts) == 1:
        bot.send_message(m.chat.id, "👉 Konsa username? `@username` bhejo.", parse_mode="Markdown"); return
    _handle_username(m, parts[1].strip())

@bot.message_handler(func=lambda m: m.text.strip().startswith("@"))
def any_at(m):
    ensure_user(m.from_user.id)
    if user_credits[m.from_user.id] <= 0:
        out_of_credits(m.chat.id); return
    _handle_username(m, m.text.strip())

def _handle_username(m, uname):
    u = uname.lower()
    if u in username_numbers:
        num = username_numbers[u]
    else:
        num = rand_mobile()
        username_numbers[u] = num

    user_credits[m.from_user.id] -= 1
    bot.send_message(
        m.chat.id,
        f"✅ Username Search Result\n\n"
        f"🔗 Username: {u}\n"
        f"📱 Mobile: {num}\n\n"
        f" 👉 FIND BY @I_M_KAIFU\n\n"
        f"💳 Remaining Credits: {user_credits[m.from_user.id]}"
    )

    if user_credits[m.from_user.id] == 0:
        out_of_credits(m.chat.id)

# === ADMIN PANEL ===
@bot.message_handler(commands=['admin'])
def admin(m):
    if m.from_user.id != ADMIN_ID:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("👨‍💻 Contact Admin", url=f"tg://user?id={ADMIN_ID}"))
        bot.send_message(m.chat.id, "📩 Help/recharge ke liye admin se contact karein.", reply_markup=kb)
        return

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("👥 Users List", callback_data="users_list"))
    kb.add(types.InlineKeyboardButton("📂 Users Count", callback_data="users_count"))
    kb.add(types.InlineKeyboardButton("📈 Rate Chart",  callback_data="rates"))
    kb.add(types.InlineKeyboardButton("➕ Add Credits", callback_data="adm_add"))
    kb.add(types.InlineKeyboardButton("➖ Remove Credits", callback_data="adm_remove"))
    kb.add(types.InlineKeyboardButton("🧰 Set Credits", callback_data="adm_set"))
    kb.add(types.InlineKeyboardButton("🔎 Check Credits", callback_data="adm_check"))
    bot.send_message(m.chat.id, "⚙️ *Admin Panel*", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    # non-admin shouldn't trigger admin callbacks
    if c.data.startswith("adm") or c.data in {"users_list","users_count","rates"}:
        if c.from_user.id != ADMIN_ID:
            return

    if c.data == "users_list":
        if not user_credits:
            bot.send_message(c.message.chat.id, "📂 Koi user nahi.")
        else:
            lines = ["👥 *Users List*\n"]
            for uid, cr in user_credits.items():
                lines.append(f"• {uid} → {cr} credits")
            bot.send_message(c.message.chat.id, "\n".join(lines), parse_mode="Markdown")

    elif c.data == "users_count":
        bot.send_message(c.message.chat.id, f"📂 *Total Users:* {len(user_credits)}", parse_mode="Markdown")

    elif c.data == "rates":
        msg = (
            "💳 *Credit Rate Chart*\n"
            "• 1–100 = ₹2/credit\n"
            "• 101–1000 = ₹1.5/credit\n"
            "• 1001+ = ₹1/credit\n\n"
            f"📲 UPI: `{UPI_ID}`\nExample: `/buy 350`"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📩 Contact Admin", url=f"tg://user?id={ADMIN_ID}"))
        bot.send_message(c.message.chat.id, msg, parse_mode="Markdown", reply_markup=kb)

    # interactive admin modes
    elif c.data == "adm_add":
        admin_state[c.from_user.id] = {"mode": "add"}
        bot.send_message(c.message.chat.id, "➕ Send: `user_id amount`", parse_mode="Markdown")
    elif c.data == "adm_remove":
        admin_state[c.from_user.id] = {"mode": "remove"}
        bot.send_message(c.message.chat.id, "➖ Send: `user_id amount`", parse_mode="Markdown")
    elif c.data == "adm_set":
        admin_state[c.from_user.id] = {"mode": "set"}
        bot.send_message(c.message.chat.id, "🧰 Send: `user_id amount`", parse_mode="Markdown")
    elif c.data == "adm_check":
        admin_state[c.from_user.id] = {"mode": "check"}
        bot.send_message(c.message.chat.id, "🔎 Send: `user_id`", parse_mode="Markdown")

# capture admin text after choosing a mode
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.from_user.id in admin_state)
def admin_input(m):
    mode = admin_state[m.from_user.id]["mode"]

    try:
        if mode in {"add","remove","set"}:
            parts = m.text.split()
            uid, amt = int(parts[0]), int(parts[1])
            ensure_user(uid)
            if mode == "add":
                user_credits[uid] += amt
                bot.send_message(m.chat.id, f"✅ {uid} +{amt} → {user_credits[uid]}")
                bot.send_message(uid, f"🎁 Admin ne +{amt} credits diye! Total: {user_credits[uid]}")
            elif mode == "remove":
                user_credits[uid] = max(0, user_credits[uid] - amt)
                bot.send_message(m.chat.id, f"🗑 {uid} -{amt} → {user_credits[uid]}")
                bot.send_message(uid, f"⚠️ Admin ne {amt} credits remove kiye. Bache: {user_credits[uid]}")
            else:  # set
                user_credits[uid] = max(0, amt)
                bot.send_message(m.chat.id, f"🧰 {uid} set → {user_credits[uid]}")
                bot.send_message(uid, f"ℹ️ Admin ne aapke credits set kiye: {user_credits[uid]}")
        elif mode == "check":
            uid = int(m.text.strip())
            bot.send_message(m.chat.id, f"🆔 {uid} → {user_credits.get(uid,0)} credits")
    except Exception as e:
        bot.send_message(m.chat.id, "❌ Galat format. Example: `8171444846 100`", parse_mode="Markdown")
    finally:
        admin_state.pop(m.from_user.id, None)

# === RUN ===
print("🤖 Bot is running…")
bot.infinity_polling()