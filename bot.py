import os
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, PreCheckoutQueryHandler, ContextTypes

# Loglama ayarları
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

# Bellek tabanlı veritabanı (user_id: {"points": 0, "invited_count": 0})
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

# /start komutu ve referans sistemi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if user_id not in user_data_db:
        user_data_db[user_id] = {"points": 0, "invited_count": 0}
        
        # Referans kontrolü (Örn: /start ref_123456)
        if context.args:
            arg = context.args[0]
            if arg.startswith("ref_"):
                try:
                    referrer_id = int(arg.replace("ref_", ""))
                    if referrer_id != user_id and referrer_id in user_data_db:
                        if user_data_db[referrer_id]["invited_count"] < 20: # Max 20 kişi sınırı
                            user_data_db[referrer_id]["invited_count"] += 1
                            user_data_db[referrer_id]["points"] += 5 # Her davete 5 CpmPuan
                            
                            try:
                                await context.bot.send_message(
                                    chat_id=referrer_id,
                                    text=f"🎉 Tebrikler! Davet ettiğin biri botu başlattı ve **+5 CpmPuan** kazandın!\nToplam CpmPuanın: {user_data_db[referrer_id]['points']}"
                                )
                            except:
                                pass
                except ValueError:
                    pass

    stocks = get_stock_accounts()
    stock_count = len(stocks)
    user_info = user_data_db[user_id]

    keyboard = [
        [InlineKeyboardButton("📦 Hesap Satın Al (15 CpmPuan)", callback_data="buy_with_points")],
        [InlineKeyboardButton("⭐ Yıldız ile CpmPuan Satın Al", callback_data="buy_points_menu")],
        [InlineKeyboardButton("👥 Arkadaşını Davet Et (+5 Puan)", callback_data="invite_link")],
        [InlineKeyboardButton("👤 Profilim & Puan Durumum", callback_data="my_profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"🚀 **CPM1 Hesap Mağazasına Hoş Geldin!**\n\n"
        f"📦 Güncel Stok: **{stock_count} adet** hesap\n"
        f"🏆 CpmPuanın: **{user_info['points']} CpmPuan**\n"
        f"*(15 CpmPuan = 1 Ücretsiz Hesap)*\n\n"
        f"Aşağıdaki menüden işlem seçebilirsin:"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# Buton yönlendirmeleri
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in user_data_db:
        user_data_db[user_id] = {"points": 0, "invited_count": 0}

    user_info = user_data_db[user_id]

    if query.data == "my_profile":
        ref_link = f"https://t.me/{context.bot.username}?start=ref_{user_id}"
        text = (
            f"👤 **Profil Bilgilerin:**\n\n"
            f"🏆 CpmPuanın: {user_info['points']}\n"
            f"👥 Davet Ettiğin Kişi: {user_info['invited_count']} / 20\n\n"
            f"🔗 **Özel Davet Linkin:**\n`{ref_link}`\n\n"
            f"Bu linki arkadaşlarınla paylaşarak her davet için **5 CpmPuan** kazanabilirsin!"
        )
        keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "invite_link":
        ref_link = f"https://t.me/{context.bot.username}?start=ref_{user_id}"
        text = (
            f"🎁 **Arkadaşını Davet Et, CpmPuan Kazan!**\n\n"
            f"Aşağıdaki linkini arkadaşlarına gönder. Botu başlattıkları an hesabına **5 CpmPuan** eklensin!\n"
            f"Toplamda en fazla 20 kişi davet edebilirsin ({user_info['invited_count']}/20).\n\n"
            f"🔗 Linkin:\n`{ref_link}`"
        )
        keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "main_menu":
        await start(update, context)

    elif query.data == "buy_with_points":
        if user_info["points"] < 15:
            keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]]
            await query.message.edit_text(
                f"❌ Yeterli CpmPuanın yok!\n\nMevcut CpmPuanın: {user_info['points']}\nGerekli CpmPuan: 15\n\nArkadaşlarını davet ederek veya yıldız ile puan satın alarak puan kazanabilirsin!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            stocks = get_stock_accounts()
            if not stocks:
                keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]]
                await query.message.edit_text("❌ Maalesef şu an stokta hiç hesap kalmadı!", reply_markup=InlineKeyboardMarkup(keyboard))
                return

            account = stocks.pop(0)
            save_stock_accounts(stocks)
            user_info["points"] -= 15

            text = (
                f"🎉 **Tebrikler! CpmPuan ile Başarıyla Hesap Aldın!**\n\n"
                f"🔑 **Hesap Bilgilerin:**\n`{account}`\n\n"
                f"Kalan CpmPuanın: {user_info['points']}"
            )
            keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]]
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "buy_points_menu":
        # 50 puandan 40.000 puana kadar seçenekler
        keyboard = [
            [InlineKeyboardButton("50 CpmPuan (30 Yıldız)", callback_data="buy_p_50")],
            [InlineKeyboardButton("250 CpmPuan (140 Yıldız)", callback_data="buy_p_250")],
            [InlineKeyboardButton("1,000 CpmPuan (500 Yıldız)", callback_data="buy_p_1000")],
            [InlineKeyboardButton("5,000 CpmPuan (2,200 Yıldız)", callback_data="buy_p_5000")],
            [InlineKeyboardButton("10,000 CpmPuan (4,000 Yıldız)", callback_data="buy_p_10000")],
            [InlineKeyboardButton("20,000 CpmPuan (7,500 Yıldız)", callback_data="buy_p_20000")],
            [InlineKeyboardButton("40,000 CpmPuan (14,000 Yıldız)", callback_data="buy_p_40000")],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]
        ]
        await query.message.edit_text(
            "⭐ **CpmPuan Satın Alma Menüsü**\n\nİstediğin CpmPuan paketini seçerek Telegram Yıldızı ile anında satın alabilirsin:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    # Puan Paketleri için Yıldız Fatura Tetikleyicileri
    elif query.data.startswith("buy_p_"):
        points_amount = int(query.data.replace("buy_p_", ""))
        
        # 50'den 40.000'e kadar fiyat haritası
        price_map = {
            50: 30,
            250: 140,
            1000: 500,
            5000: 2200,
            10000: 4000,
            20000: 7500,
            40000: 14000
        }
        stars = price_map.get(points_amount, 30)

        title = f"{points_amount} CpmPuan"
        description = f"Mağazamızda harcamak üzere hesabınıza {points_amount} CpmPuan eklenecektir."
        payload = f"points_pack_{points_amount}"
        prices = [LabeledPrice("CpmPuan", stars)]

        await context.bot.send_invoice(
            chat_id=user_id,
            title=title,
            description=description,
            payload=payload,
            currency="XTR",
            prices=prices
        )

# Ödeme Onay Aşaması (Pre-checkout)
async def pre_checkout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

# Ödeme Başarılı Olduğunda Puanı Kullanıcıya Yükleme
async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    payload = payment.invoice_payload
    user_id = update.effective_user.id

    if user_id not in user_data_db:
        user_data_db[user_id] = {"points": 0, "invited_count": 0}

    if payload.startswith("points_pack_"):
        earned_points = int(payload.replace("points_pack_", ""))
        user_data_db[user_id]["points"] += earned_points

        await update.message.reply_text(
            f"🎉 **Ödeme Başarılı!**\n\n"
            f"Hesabına başarıyla **{earned_points} CpmPuan** eklendi! 🚀\n"
            f"Toplam CpmPuanın: {user_data_db[user_id]['points']}\n\n"
            f"Ana menüye dönmek için /start yazabilirsin."
        )

def main():
    if not TOKEN:
        logger.error("BOT_TOKEN bulunamadı!")
        return

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_callback))
    
    from telegram.ext import MessageHandler, filters
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    logger.info("Bot başlatılıyor...")
    application.run_polling()

if __name__ == "__main__":
    main()  
