import logging
import random
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

BOT_TOKEN = "7989564394:AAF7WfIynM3x8IGRtITdYyv21HmKRNf7x-c"
ADMIN_ID = 0 

user_data_store = {}
STOCKS = {"random": [], "coin30k": [], "vip": []}

# PROMO SİSTEMİ (Varsayılan Stok: 960)
PROMO_SYSTEM = {
    "stock": 960,
    "claimed_users": [],  # Kod alan kullanıcı ID'leri
    "generated_codes": {}  # Kodlar: {"KOD_ADI": {"ap": 40, "used": False}}
}

PRODUCTS = {
    "random": {"name": "🎲 Random CPM1 Hesap", "stars": 15, "ap": 45},
    "coin30k": {"name": "💰 30k Coin Garanti Hesap", "stars": 30, "ap": 90},
    "vip": {"name": "👑 250k-500k Coin VIP Hesap", "stars": 200, "ap": 600},
}

AP_PACKAGES = {
    "ap100": {"ap": 100, "stars": 80},
    "ap200": {"ap": 200, "stars": 160},
    "ap500": {"ap": 500, "stars": 400},
    "ap1000": {"ap": 1000, "stars": 800},
    "ap2500": {"ap": 2500, "stars": 2000},
    "ap5000": {"ap": 5000, "stars": 4000},
    "ap10000": {"ap": 10000, "stars": 8000},
}

def get_user(user_id):
    if user_id not in user_data_store:
        user_data_store[user_id] = {
            "ap": 0, 
            "orders": [], 
            "vip_expire": None, 
            "last_vip_wheel": None,
            "awaiting_code": False
        }
    return user_data_store[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = get_user(user.id)
    u["awaiting_code"] = False
    
    if PROMO_SYSTEM["stock"] > 0:
        promo_btn_text = f"🎁 Promo Kod Al (Stok: {PROMO_SYSTEM['stock']})"
    else:
        promo_btn_text = "❌ Promo Kod (Stok Bitti)"

    keyboard = [
        [InlineKeyboardButton("🛒 CPM2 Hesap Mağazası", callback_data="shop")],
        [InlineKeyboardButton("🎰 Apexpuan Şans Çarkı (7 ⭐️)", callback_data="wheel_ap_info")],
        [InlineKeyboardButton("👑 VIP Üyelik Satın Al (800 ⭐️)", callback_data="vip_buy_info")],
        [InlineKeyboardButton("👑 VIP Günlük Çark (Ücretsiz)", callback_data="wheel_vip_daily")],
        [InlineKeyboardButton(promo_btn_text, callback_data="get_promo_code")],
        [InlineKeyboardButton("🎟️ Promo Kod Kullan", callback_data="use_code")],
        [InlineKeyboardButton("💎 Apexpuan Satın Al", callback_data="ap_shop")],
        [InlineKeyboardButton("👤 Profilim & Siparişlerim", callback_data="profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    vip_status = "👑 VIP Üye" if (u["vip_expire"] and u["vip_expire"] > datetime.now()) else "Standart Üye"
    text = f"👋 Merhaba {user.first_name}!\nÜyelik Tipi: **{vip_status}**\n\nCPM2 Mağazasına hoş geldin. Aşağıdaki menüden seçim yapabilirsin."
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if data == "main_menu":
        await query.answer()
        await start(update, context)

    # --- 1. PROMO KOD OLUŞTURUP VERME ---
    elif data == "get_promo_code":
        if user_id in PROMO_SYSTEM["claimed_users"]:
            await query.answer("❌ Zaten bir promo kod aldın!", show_alert=True)
            return

        if PROMO_SYSTEM["stock"] <= 0:
            await query.answer("❌ Üzgünüm, stok tükendi!", show_alert=True)
            return

        # Stok düş ve benzersiz kod üret
        PROMO_SYSTEM["stock"] -= 1
        PROMO_SYSTEM["claimed_users"].append(user_id)
        
        rand_code = f"APEX-{''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=6))}"
        won_ap = random.choice([30, 40, 50])
        
        PROMO_SYSTEM["generated_codes"][rand_code] = {"ap": won_ap, "used": False}

        await query.answer("✅ Promo kodun oluşturuldu!", show_alert=False)
        keyboard = [[InlineKeyboardButton("🎟️ Kodu Şimdi Kullan", callback_data="use_code")]]
        
        await query.message.reply_text(
            f"🎉 **PROMO KODUNU ALDIN!**\n\n"
            f"🔑 Kodun: `{rand_code}`\n"
            f"💎 Değeri: **{won_ap} Apexpuan**\n\n"
            f"Kodu kopyala ve menüdeki **🎟️ Promo Kod Kullan** seçeneğinden hesabına tanımla!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        await start(update, context)

    # --- 2. PROMO KOD KULLANMA BUTONU ---
    elif data == "use_code":
        await query.answer()
        u = get_user(user_id)
        u["awaiting_code"] = True
        keyboard = [[InlineKeyboardButton("⬅️ İptal / Ana Menü", callback_data="main_menu")]]
        await query.message.edit_text(
            "🎟️ **Promo Kod Kullan**\n\nElindeki promo kodu sohbet alanına mesaj olarak yazıp gönder:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    # --- DİĞER BUTONLAR ---
    elif data == "wheel_ap_info":
        await query.answer()
        keyboard = [
            [InlineKeyboardButton("⭐ 7 Yıldız İle Çevir", callback_data="spin_ap_7star")],
            [InlineKeyboardButton("⬅️ Ana Menü", callback_data="main_menu")]
        ]
        await query.message.edit_text(
            "🎰 **Apexpuan Şans Çarkı**\n\n7 Yıldız karşılığında çarkı çevirerek şansına **1 ile 10 AP** arası Apexpuan kazanabilirsin!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data == "spin_ap_7star":
        await query.answer()
        prices = [LabeledPrice(label="AP Şans Çarkı", amount=7)]
        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title="🎰 AP Şans Çarkı",
            description="1-10 AP arası kazanmak için 7 Yıldız ödeyin.",
            payload="spin_ap_7stars_paid",
            provider_token="",
            currency="XTR",
            prices=prices
        )

    elif data == "vip_buy_info":
        await query.answer()
        keyboard = [
            [InlineKeyboardButton("👑 800 Yıldız İle VIP Al", callback_data="buy_vip_800star")],
            [InlineKeyboardButton("⬅️ Ana Menü", callback_data="main_menu")]
        ]
        await query.message.edit_text(
            "👑 **Aylık VIP Üyelik (30 Gün)**\n\n**VIP Üyelik Ayrıcalıkları:**\n"
            "• Her gün **1 Defa Ücretsiz VIP Çarkı** çevirme hakkı.\n"
            "• VIP Çarktan her gün **30 AP - 500 AP** arası bakiye veya **Rastgele Hesap** kazanma şansı!\n\n"
            "Fiyat: **800 ⭐️ / 30 Gün**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data == "buy_vip_800star":
        await query.answer()
        prices = [LabeledPrice(label="Aylık VIP Üyelik", amount=800)]
        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title="👑 30 Günlük VIP Üyelik",
            description="Aylık VIP ayrıcalıklarına sahip olun.",
            payload="buy_vip_monthly_paid",
            provider_token="",
            currency="XTR",
            prices=prices
        )

    elif data == "wheel_vip_daily":
        await query.answer()
        u = get_user(user_id)
        now = datetime.now()

        if not u["vip_expire"] or u["vip_expire"] < now:
            keyboard = [[InlineKeyboardButton("👑 VIP Ol (800 ⭐️)", callback_data="vip_buy_info")]]
            await query.message.edit_text("❌ **Bu çark sadece VIP üyelere özeldir!**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return

        if u["last_vip_wheel"] and now - u["last_vip_wheel"] < timedelta(days=1):
            kalan = timedelta(days=1) - (now - u["last_vip_wheel"])
            saat = kalan.seconds // 3600
            dakika = (kalan.seconds % 3600) // 60
            await query.message.reply_text(f"⏳ Bugüne ait VIP çark hakkını kullandın! Tekrar çevirmek için **{saat} saat {dakika} dakika** beklemelisin.", parse_mode="Markdown")
            return

        u["last_vip_wheel"] = now
        reward_type = random.choices(["ap", "account"], weights=[70, 30])[0]

        if reward_type == "ap":
            won_ap = random.randint(30, 500)
            u["ap"] += won_ap
            await query.message.reply_text(f"🎉 **VIP Günlük Çark Çevrildi!**\n\n💎 Kazandığın: **+{won_ap} Apexpuan**\nGüncel Bakiyen: **{u['ap']} AP**", parse_mode="Markdown")
        else:
            available_cats = [c for c, accs in STOCKS.items() if len(accs) > 0]
            if available_cats:
                chosen_cat = random.choice(available_cats)
                won_acc = STOCKS[chosen_cat].pop(0)
                u["orders"].append(won_acc)
                cat_name = PRODUCTS[chosen_cat]["name"]
                await query.message.reply_text(f"🎉 **EFSANEVİ ÖDÜL!**\n\n🎁 VIP Çarktan Hesap Kazandın!\n🏷️ Tür: **{cat_name}**\n🔑 Hesap: `{won_acc}`", parse_mode="Markdown")
            else:
                won_ap = random.randint(100, 500)
                u["ap"] += won_ap
                await query.message.reply_text(f"🎉 **VIP Günlük Çark Çevrildi!**\n💎 Kazandığın: **+{won_ap} AP**", parse_mode="Markdown")

    elif data == "shop":
        await query.answer()
        keyboard = []
        for key, item in PRODUCTS.items():
            stock_count = len(STOCKS[key])
            keyboard.append([InlineKeyboardButton(f"{item['name']} - {item['stars']} ⭐️ / {item['ap']} AP (Stok: {stock_count})", callback_data=f"item_{key}_1")])
        keyboard.append([InlineKeyboardButton("⬅️ Ana Menü", callback_data="main_menu")])
        await query.message.edit_text("🛒 **Satın almak istediğin hesabı seç:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("item_"):
        await query.answer()
        _, key, count = data.split("_")
        count = int(count)
        item = PRODUCTS[key]
        stock_count = len(STOCKS[key])
        total_stars = item["stars"] * count
        total_ap = item["ap"] * count

        keyboard = [
            [
                InlineKeyboardButton("➖", callback_data=f"item_{key}_{max(1, count-1)}"),
                InlineKeyboardButton(f"Adet: {count}", callback_data="ignore"),
                InlineKeyboardButton("➕", callback_data=f"item_{key}_{count+1}")
            ],
            [InlineKeyboardButton(f"💳 {total_stars} Yıldız ile Öde", callback_data=f"pay_stars_{key}_{count}")],
            [InlineKeyboardButton(f"💎 {total_ap} AP ile Öde", callback_data=f"pay_ap_{key}_{count}")],
            [InlineKeyboardButton("⬅️ Mağazaya Dön", callback_data="shop")]
        ]
        text = f"📦 **Ürün:** {item['name']}\n📊 **Mevcut Stok:** {stock_count} Adet\n💰 **Birim Fiyat:** {item['stars']} ⭐️ / {item['ap']} AP\n🔢 **Seçilen Adet:** {count}\n💳 **Toplam Tutar:** {total_stars} ⭐️ VEYA {total_ap} AP"
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("pay_stars_"):
        await query.answer()
        _, _, key, count = data.split("_")
        count = int(count)
        if len(STOCKS[key]) < count:
            await query.message.reply_text(f"❌ **Yetersiz Stok!** Stokta sadece **{len(STOCKS[key])}** adet var.", parse_mode="Markdown")
            return
        item = PRODUCTS[key]
        total_stars = item["stars"] * count
        prices = [LabeledPrice(label=f"{count}x {item['name']}", amount=total_stars)]
        await context.bot.send_invoice(chat_id=query.message.chat_id, title=item['name'], description=f"{count} adet {item['name']} teslimatı.", payload=f"buyacc_{key}_{count}", provider_token="", currency="XTR", prices=prices)

    elif data.startswith("pay_ap_"):
        await query.answer()
        _, _, key, count = data.split("_")
        count = int(count)
        u = get_user(user_id)
        item = PRODUCTS[key]
        total_ap = item["ap"] * count
        if len(STOCKS[key]) < count:
            await query.message.reply_text(f"❌ **Yetersiz Stok!** Stokta sadece **{len(STOCKS[key])}** adet var.", parse_mode="Markdown")
            return
        if u["ap"] < total_ap:
            await query.message.reply_text(f"❌ **Yetersiz Apexpuan!**\n\nGerekli: {total_ap} AP\nSende Olan: {u['ap']} AP", parse_mode="Markdown")
            return
        u["ap"] -= total_ap
        delivered_accs = [STOCKS[key].pop(0) for _ in range(count)]
        u["orders"].extend(delivered_accs)
        acc_text = "\n".join([f"`{acc}`" for acc in delivered_accs])
        await query.message.reply_text(f"✅ **Ödeme Apexpuan ile Yapıldı!**\n\n🎉 Teslim Edilen Hesaplar:\n{acc_text}\n\n💎 Kalan Bakiye: **{u['ap']} AP**", parse_mode="Markdown")

    elif data == "ap_shop":
        await query.answer()
        keyboard = [[InlineKeyboardButton(f"🔹 {pkg['ap']} AP — {pkg['stars']} ⭐️", callback_data=f"getap_{key}")] for key, pkg in AP_PACKAGES.items()]
        keyboard.append([InlineKeyboardButton("⬅️ Ana Menü", callback_data="main_menu")])
        await query.message.edit_text("💎 **Apexpuan Paketleri (Yıldız İle Al):**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("getap_"):
        await query.answer()
        pkg_key = data.replace("getap_", "")
        pkg = AP_PACKAGES[pkg_key]
        prices = [LabeledPrice(label=f"{pkg['ap']} Apexpuan", amount=pkg["stars"])]
        await context.bot.send_invoice(chat_id=query.message.chat_id, title=f"{pkg['ap']} Apexpuan Paketi", description=f"Hesabınıza {pkg['ap']} Apexpuan tanımlanacaktır.", payload=f"addap_{pkg_key}", provider_token="", currency="XTR", prices=prices)

    elif data == "profile":
        await query.answer()
        u = get_user(user_id)
        orders_text = "\n".join([f"- `{o}`" for o in u["orders"]]) if u["orders"] else "Henüz sipariş yok."
        vip_info = "❌ Aktif Değil"
        if u["vip_expire"] and u["vip_expire"] > datetime.now():
            kalan_gun = (u["vip_expire"] - datetime.now()).days + 1
            vip_info = f"👑 Aktif ({kalan_gun} Gün Kaldı)"
        text = f"👤 **Profilim**\n\n💎 **Apexpuan Bakiye:** {u['ap']} AP\n👑 **VIP Üyelik:** {vip_info}\n\n📜 **Sipariş Geçmişim:**\n{orders_text}"
        keyboard = [[InlineKeyboardButton("⬅️ Ana Menü", callback_data="main_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- PROMO KOD METİN DİNLENMESİ (KULLANMA SÜRECİ) ---
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    u = get_user(user_id)
    text = update.message.text.strip().upper()

    if u.get("awaiting_code"):
        u["awaiting_code"] = False
        
        if text in PROMO_SYSTEM["generated_codes"]:
            code_info = PROMO_SYSTEM["generated_codes"][text]
            if code_info["used"]:
                await update.message.reply_text("❌ **Bu promo kod daha önce kullanılmış!**", parse_mode="Markdown")
            else:
                code_info["used"] = True
                reward_ap = code_info["ap"]
                u["ap"] += reward_ap
                await update.message.reply_text(
                    f"🎉 **PROMO KOD BAŞARIYLA KULLANILDI!**\n\n"
                    f"💎 Hesabına **+{reward_ap} Apexpuan** eklendi.\n"
                    f"📊 Güncel Bakiyen: **{u['ap']} AP**",
                    parse_mode="Markdown"
                )
        else:
            await update.message.reply_text("❌ **Geçersiz promo kod!**", parse_mode="Markdown")

# --- ADMIN KOD STOĞU GÜNCELLEME KOMUTU (/promo_stok 960) ---
async def reset_promo_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID != 0 and update.effective_user.id != ADMIN_ID:
        return

    try:
        new_stock = int(context.args[0])
        PROMO_SYSTEM["stock"] = new_stock
        PROMO_SYSTEM["claimed_users"] = []
        await update.message.reply_text(f"✅ **Promo Kod Stoğu Güncellendi!**\n\n📦 Yeni Stok: **{new_stock}**")
    except Exception:
        await update.message.reply_text("⚠️ **Kullanım:** `/promo_stok 960`")

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    payload = payment.invoice_payload
    u = get_user(user_id)
    
    if payload == "spin_ap_7stars_paid":
        won_ap = random.randint(1, 10)
        u["ap"] += won_ap
        await update.message.reply_text(f"🎉 **Çark Çevrildi!**\n\n🎰 Kazandığın: **+{won_ap} Apexpuan**\n💎 Yeni Bakiyen: **{u['ap']} AP**", parse_mode="Markdown")

    elif payload == "buy_vip_monthly_paid":
        now = datetime.now()
        start_date = u["vip_expire"] if (u["vip_expire"] and u["vip_expire"] > now) else now
        u["vip_expire"] = start_date + timedelta(days=30)
        await update.message.reply_text("👑 **TEBRİKLER! VIP Üyeliğiniz 30 Gün Süreyle Aktif Edildi!**", parse_mode="Markdown")

    elif payload.startswith("addap_"):
        pkg_key = payload.replace("addap_", "")
        pkg = AP_PACKAGES[pkg_key]
        u["ap"] += pkg["ap"]
        await update.message.reply_text(f"✅ **Ödeme Başarılı!**\n\nHesabınıza **+{pkg['ap']} Apexpuan** eklendi.", parse_mode="Markdown")

    elif payload.startswith("buyacc_"):
        _, key, count = payload.split("_")
        count = int(count)
        delivered_accs = [STOCKS[key].pop(0) for _ in range(count) if STOCKS[key]]
        u["orders"].extend(delivered_accs)
        acc_text = "\n".join([f"`{acc}`" for acc in delivered_accs])
        await update.message.reply_text(f"✅ **Ödeme Başarılı!**\n\n🎉 Satın aldığınız hesaplar:\n{acc_text}", parse_mode="Markdown")

async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID != 0 and update.effective_user.id != ADMIN_ID:
        return
    try:
        args = context.args
        category = args[0]
        accounts = args[1:]
        if category in STOCKS:
            STOCKS[category].extend(accounts)
            await update.message.reply_text(f"✅ **{category}** kategorisine **{len(accounts)}** adet stok eklendi!")
        else:
            await update.message.reply_text("❌ Geçersiz kategori!")
    except Exception:
        await update.message.reply_text("⚠️ **Kullanım:** `/stok_ekle <kategori> <mail:pass1>`")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stok_ekle", add_stock))
    app.add_handler(CommandHandler("promo_stok", reset_promo_stock))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    app.add_handler(MessageHandler(filters.DOCUMENT, handle_document))
    
    app.run_polling()

if __name__ == "__main__":
    
    main()
    async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID != 0 and update.effective_user.id != ADMIN_ID:
        return
    
    document = update.message.document
    caption = update.message.caption
    
    if not caption or caption not in STOCKS:
        await update.message.reply_text("❌ Dosya gönderirken açıklama (caption) kısmına kategori adını yazmalısın:\nÖrnek kategoriler: `random`, `coin30k`, `vip`", parse_mode="Markdown")
        return
        
    try:
        file = await context.bot.get_file(document.file_id)
        file_bytes = await file.download_as_bytearray()
        content = file_bytes.decode('utf-8')
        
        accounts = [line.strip() for line in content.splitlines() if line.strip()]
        
        if accounts:
            STOCKS[caption].extend(accounts)
            await update.message.reply_text(f"✅ Dosyadan **{caption}** kategorisine **{len(accounts)}** adet stok eklendi!")
        else:
            await update.message.reply_text("❌ Dosya boş veya okunamadı!")
    except Exception as e:
        await update.message.reply_text(f"❌ Bir hata oluştu: {e}")
        
    
