import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8962445060:AAEatnjtKUW66d--dFVdjgGnRqLMN_P7o44"
DOSYASI = "stok.txt"

def stok_oku():
    if not os.path.exists(DOSYASI):
        return []
    with open(DOSYASI, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def stok_guncelle(kalanlar):
    with open(DOSYASI, "w", encoding="utf-8") as f:
        for hesap in kalanlar:
            f.write(hesap + "\n")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stok = stok_oku()
    stok_sayisi = len(stok)
    
    keyboard = [
        [InlineKeyboardButton("🛒 Hesap Satın Al", callback_data="buy_menu")],
        [InlineKeyboardButton("📦 Stok Durumu", callback_data="stock_status")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🚀 **CPM1 | Hesap Mağazası'na Hoş Geldiniz!**\n\n"
        f"En güvenilir Car Parking Multiplayer 1 hesapları burada.\n"
        f"📦 Güncel Stok: **{stok_sayisi} adet**\n\n"
        f"İşlem yapmak için aşağıdaki butonları kullanabilirsiniz:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "stock_status":
        stok = stok_oku()
        await query.message.edit_text(
            f"📦 **Güncel Stok Durumu:**\nMağazamızda şu an toplam **{len(stok)}** adet hesap bulunmaktadır.",
            parse_mode="Markdown"
        )
    elif query.data == "buy_menu":
        keyboard = [
            [InlineKeyboardButton("1 Adet (15 Yıldız)", callback_data="buy_1")],
            [InlineKeyboardButton("2 Adet (30 Yıldız)", callback_data="buy_2")],
            [InlineKeyboardButton("3 Adet (45 Yıldız)", callback_data="buy_3")],
            [InlineKeyboardButton("4 Adet (60 Yıldız)", callback_data="buy_4")],
            [InlineKeyboardButton("5 Adet (50 Yıldız - İndirimli!)", callback_data="buy_5")],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("Lütfen almak istediğiniz miktarı seçin:", reply_markup=reply_markup)
        
    elif query.data == "main_menu":
        stok = stok_oku()
        keyboard = [
            [InlineKeyboardButton("🛒 Hesap Satın Al", callback_data="buy_menu")],
            [InlineKeyboardButton("📦 Stok Durumu", callback_data="stock_status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            f"🚀 **CPM1 | Hesap Mağazası'na Hoş Geldiniz!**\n\n"
            f"📦 Güncel Stok: **{len(stok)} adet**",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    elif query.data.startswith("buy_"):
        adet = int(query.data.split("_")[1])
        stok = stok_oku()
        
        if len(stok) < adet:
            await query.message.edit_text(f"❌ Maalesef yeterli stok yok! Mevcut stok: {len(stok)}")
            return
            
        if adet < 5:
            fiyat = adet * 15
        else:
            fiyat = adet * 10
            
        prices = [{"label": f"{adet} Adet CPM1 Hesabı", "amount": fiyat}]
        
        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title=f"CPM1 Hesap Satışı ({adet} adet)",
            description=f"Car Parking Multiplayer 1 - {adet} adet hesap teslimatı.",
            payload=f"cpm_hesap_{adet}",
            currency="XTR",
            prices=prices
        )

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    payload = payment.invoice_payload
    
    if payload.startswith("cpm_hesap_"):
        adet = int(payload.split("_")[2])
        stok = stok_oku()
        
        if len(stok) < adet:
            await update.message.reply_text("❌ Ödeme alındı ancak stok tükendi! Lütfen yöneticiyle iletişime geçin.")
            return
            
        verilecekler = stok[:adet]
        kalanlar = stok[adet:]
        stok_guncelle(kalanlar)
        
        dosya_adi = "verilen_hesaplar.txt"
        with open(dosya_adi, "w", encoding="utf-8") as f:
            for hesap in verilecekler:
                f.write(hesap + "\n")
                
        with open(dosya_adi, "rb") as f:
            await update.message.reply_document(
                document=f,
                caption=f"✅ Ödemeniz başarıyla alındı!\n🎁 Satın aldığınız {adet} adet hesap ekteki `.txt` dosyasındadır. Hayırlı olsun!"
            )
        
        if os.path.exists(dosya_adi):
            os.remove(dosya_adi)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    
    print("Mağaza Botu GitHub üzerinde aktif!")
    app.run_polling()

if __name__ == "__main__":
    main()
  
