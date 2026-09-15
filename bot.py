import os
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, PreCheckoutQueryHandler, filters, ContextTypes

# Loglama ayarları
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Token (Koda gömülü versiyon)
TOKEN = "8962445060:AAEatnjtKUW66d--dFVdjgGnRqLMN_P7o44"

# Bellek tabanlı veritabanı (user_id: {"points": 0, "referred_by": None})
user_data_db = {}

# Stok dosyasından hesap okuma/yazma
def get_stock_accounts():
    if not os.path.exists("stock.txt"):
        return []
    with open("stock.txt", "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines

def save_stock_accounts(accounts):
    with open("stock.txt", "w", encoding="utf-8") as f:
        for acc in accounts:
            f.write(acc + "\n")

# Ana menü klavyesi
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📦 Hesap Satın Al (15 CarpiPuan)", callback_data="buy_account_points")],
        [InlineKeyboardButton("⭐ Yıldız ile Hesap Satın Al (Örn: 500 Yıldız)", callback_data="buy_account_stars")],
        [InlineKeyboardButton("⭐ Yıldız ile CarpiPuan Satın Al", callback_data="buy_points_menu")],
        [InlineKeyboardButton("👥 Arkadaşını Davet Et (+5 CarpiPuan)", callback_data="ref_link")],
        [InlineKeyboardButton("👤 Profilim & Puan Durumum", callback_data="profile")]
    ]
    return InlineKeyboardMarkup(keyboard)

# /start komutu ve referans sistemi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    args = context.args

    if user_id not in user_data_db:
        user_data_db[user_id] = {"points": 0, "referred_by": None}
        # Referans kontrolü
        if args and args[0].isdigit():
            ref_id = int(args[0])
            if ref_id != user_id and ref_id in user_data_db:
                user_data_db[user_id]["referred_by"] = ref_id
                user_data_db[ref_id]["points"] += 5
                try:
                    await context.bot.send_message(
                        chat_id=ref_id,
                        text=f"🎉 Tebrikler! Davet ettiğin biri botu başlattı ve hesabına **+5 CarpiPuan** eklendi!"
                    )
                except Exception:
                    pass

    stock_count = len(get_stock_accounts())
    points = user_data_db[user_id]["points"]

    text = (
        f"🚀 CPM1 Hesap Mağazasına Hoş Geldin!\n\n"
        f"📦 Güncel Stok: {stock_count} adet hesap\n"
        f"🏆 CarpiPuanın: {points} CarpiPuan\n"
        f"(15 CarpiPuan = 1 Ücretsiz Hesap)\n\n"
        f"Aşağıdaki menüden işlem seçebilirsin:"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=get_main_menu())
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=get_main_menu())

# Buton yönlendiricileri
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in user_data_db:
        user_data_db[user_id] = {"points": 0, "referred_by": None}

    data = query.data

    if data == "main_menu":
        stock_count = len(get_stock_accounts())
        points = user_data_db[user_id]["points"]
        text = (
            f"🚀 CPM1 Hesap Mağazasına Hoş Geldin!\n\n"
            f"📦 Güncel Stok: {stock_count} adet hesap\n"
            f"🏆 CarpiPuanın: {points} CarpiPuan\n\n"
            f"Aşağıdaki menüden işlem seçebilirsin:"
        )
        await query.message.edit_text(text, reply_markup=get_main_menu())

    elif data == "profile":
        points = user_data_db[user_id]["points"]
        text = (
            f"👤 **Profil Bilgilerin:**\n\n"
            f"🆔 Telegram ID: `{user_id}`\n"
            f"🏆 CarpiPuan: {points}\n"
            f"📦 Harcanabilir Puan Durumu: {'Yeterli ✅' if points >= 15 else 'Yetersiz ❌ (15 CarpiPuan lazım)'}"
        )
        keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "ref_link":
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        text = (
            f"👥 **Arkadaşını Davet Et Kazan!**\n\n"
            f"Bağlantını arkadaşlarınla paylaş, her katılan kişi başına **+5 CarpiPuan** kazan!\n\n"
            f"🔗 Senin Davet Linkin:\n`{ref_link}`"
        )
        keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "buy_account_points":
        points = user_data_db[user_id]["points"]
        if points < 15:
            await query.message.reply_text("❌ Yetersiz CarpiPuan! Hesap almak için en az 15 puana ihtiyacın var. Arkadaşını davet ederek puan kazanabilirsin.")
            return

        stock = get_stock_accounts()
        if not stock:
            await query.message.reply_text("❌ Maalesef şu an stokta hiç hesap kalmadı. Lütfen daha sonra tekrar dene.")
            return

        # Puan düş ve stoktan hesap ver (FIFO)
        user_data_db[user_id]["points"] -= 15
        given_account = stock.pop(0)
        save_stock_accounts(stock)

        await query.message.reply_text(
            f"🎉 Başarıyla hesap satın aldın!\n\n"
            f"🔑 **Hesap Bilgisi:**\n`{given_account}`\n\n"
            f"Kalan CarpiPuanın: {user_data_db[user_id]['points']}",
            parse_mode="Markdown"
        )

    elif data == "buy_points_menu":
        keyboard = [
            [InlineKeyboardButton("⭐ 500 Yıldız - 40000 CarpiPuan", callback_data="star_pack_1")],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]
        ]
        await query.message.edit_text("⭐ Yıldız ile yüklemek istediğin CarpiPuan paketini seç:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "buy_account_stars":
        # Doğrudan Yıldız ile hesap satın alma (Telegram Stars Faturası)
        title = "CPM1 Hesabı"
        description = "1 Adet Hazır CPM Hesabı (Telegram Yıldızı ile)"
        payload = "account_star_payload"
        currency = "XTR"
        prices = [LabeledPrice("CPM Hesabı", 100)] # Örn: 100 Yıldız

        await context.bot.send_invoice(
            chat_id=user_id,
            title=title,
            description=description,
            payload=payload,
            provider_token="",
            currency=currency,
            prices=prices
        )

    elif data == "star_pack_1":
        title = "40000 CarpiPuan Paketi"
        description = "Mağazamızda harcamak üzere hesabınıza 40000 CarpiPuan eklenecektir."
        payload = "points_pack_1"
        currency = "XTR"
        prices = [LabeledPrice("40000 CarpiPuan", 14000)]

        await context.bot.send_invoice(
            chat_id=user_id,
            title=title,
            description=description,
            payload=payload,
            provider_token="",
            currency=currency,
            prices=prices
        )

# Ödeme Onay Öncesi
async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

# Başarılı Ödeme Sonrası
async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    payload = payment.invoice_payload

    if user_id not in user_data_db:
        user_data_db[user_id] = {"points": 0, "referred_by": None}

    if payload == "points_pack_1":
        user_data_db[user_id]["points"] += 40000
        await update.message.reply_text("✅ Ödeme başarılı! 40000 CarpiPuan hesabına eklendi. /start yazarak menüye dönebilirsin.")
    elif payload == "account_star_payload":
        stock = get_stock_accounts()
        if not stock:
            await update.message.reply_text("✅ Ödeme başarılı ancak şu an stokta hesap kalmadı! Lütfen yöneticiye bildir, hesabın en kısa sürede verilecektir.")
            return
        given_account = stock.pop(0)
        save_stock_accounts(stock)
        await update.message.reply_text(
            f"🎉 Ödeme başarılı! Yıldız ile aldığın hesap:\n\n`{given_account}`",
            parse_mode="Markdown"
        )

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    application.run_polling()

if __name__ == "__main__":
    main()
