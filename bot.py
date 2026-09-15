import os
import random
import time
import logging
import uuid
import json
from flask import Flask
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, PreCheckoutQueryHandler, MessageHandler, filters

# --- RENDER İÇİN WEB SUNUCUSU (KAPANMAYI ÖNLER) ---
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Bot aktif ve calisiyor!"

def run():
    app_flask.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

# Logging ayarları
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8962445060:AAEatnjtKUW66d--dFVdjgGnRqLMN_P7o44"
PROVIDER_TOKEN = ""  # Telegram Stars (XTR) için boş bırakılır

USER_DATA_FILE = "users.txt"
STOCK_FILE = "stok.txt"
KAMPANYA_SAYAC_FILE = "kampanya_sayac.txt"
KODLAR_FILE = "aktif_kodlar.txt"
CUSTOM_CODES_FILE = "custom_codes.json"

# --- KOD SİSTEMİ FONKSİYONLARI ---
def load_custom_codes():
    if not os.path.exists(CUSTOM_CODES_FILE):
        return {}
    try:
        with open(CUSTOM_CODES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_custom_codes(codes_dict):
    with open(CUSTOM_CODES_FILE, "w", encoding="utf-8") as f:
        json.dump(codes_dict, f, ensure_ascii=False, indent=4)

def generate_unique_code(product_name):
    unique_suffix = uuid.uuid4().hex[:6].upper()
    code = f"CPM-{product_name}-{unique_suffix}"
    codes = load_custom_codes()
    while code in codes:
        unique_suffix = uuid.uuid4().hex[:6].upper()
        code = f"CPM-{product_name}-{unique_suffix}"
    
    codes[code] = {"used": False, "product": product_name}
    save_custom_codes(codes)
    return code

# --- KAMPANYA SAYAÇ ---
def get_campaign_count():
    if not os.path.exists(KAMPANYA_SAYAC_FILE):
        return 0
    with open(KAMPANYA_SAYAC_FILE, "r", encoding="utf-8") as f:
        val = f.read().strip()
        return int(val) if val.isdigit() else 0

def save_campaign_count(count):
    with open(KAMPANYA_SAYAC_FILE, "w", encoding="utf-8") as f:
        f.write(str(count))

# --- YARDIMCI FONKSİYONLAR ---
def load_stock():
    if not os.path.exists(STOCK_FILE):
        return []
    with open(STOCK_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def save_stock(stock):
    with open(STOCK_FILE, "w", encoding="utf-8") as f:
        for item in stock:
            f.write(f"{item}\n")

def get_user_balance(user_id):
    if not os.path.exists(USER_DATA_FILE):
        return 0.0, set(), 0.0, 0.0, 0.0
    with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if int(parts[0]) == user_id:
                points = float(parts[1])
                refs = set(int(r) for r in parts[2].split(";") if r)
                last_kod_time = float(parts[3]) if len(parts) > 3 else 0.0
                last_bonus_yildiz = float(parts[4]) if len(parts) > 4 else 0.0
                kayit_zamani = float(parts[5]) if len(parts) > 5 else time.time()
                return points, refs, last_kod_time, last_bonus_yildiz, kayit_zamani
    return 0.0, set(), 0.0, 0.0, time.time()

def update_user_balance_extended(user_id, points, refs, last_kod_time, last_bonus_yildiz, kayit_zamani):
    users = []
    found = False
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")
                uid = int(parts[0])
                kz = float(parts[5]) if len(parts) > 5 else kayit_zamani
                if uid == user_id:
                    users.append(f"{user_id},{points},{';'.join(map(str, refs))},{last_kod_time},{last_bonus_yildiz},{kz}\n")
                    found = True
                else:
                    users.append(line)
    if not found:
        users.append(f"{user_id},{points},{';'.join(map(str, refs))},{last_kod_time},{last_bonus_yildiz},{kayit_zamani}\n")
    with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
        f.writelines(users)

# --- KOMUTLAR ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    simdiki_zaman = time.time()
    points, refs, last_kod_time, last_bonus_yildiz, kayit_zamani = get_user_balance(user.id)

    if not os.path.exists(USER_DATA_FILE) or kayit_zamani == 0.0:
        kayit_zamani = simdiki_zaman

    if args and args[0].isdigit():
        ref_id = int(args[0])
        if ref_id != user.id and ref_id not in refs:
            refs.add(ref_id)
            update_user_balance_extended(user.id, points, refs, last_kod_time, last_bonus_yildiz, kayit_zamani)
            ref_points, ref_refs, ref_lk, ref_lb, ref_kz = get_user_balance(ref_id)
            update_user_balance_extended(ref_id, ref_points + 5.0, ref_refs, ref_lk, ref_lb, ref_kz)
            try:
                await context.bot.send_message(chat_id=ref_id, text="🎉 Davetin kabul edildi! Hesabına +5 CarpiPuan eklendi.")
            except:
                pass

    update_user_balance_extended(user.id, points, refs, last_kod_time, last_bonus_yildiz, kayit_zamani)

    stock = load_stock()
    keyboard = [
        [InlineKeyboardButton("📦 Hesap Satın Al (15 CarpiPuan)", callback_data="buy_point")],
        [InlineKeyboardButton("⭐ Yıldız ile Doğrudan Hesap Satın Al", callback_data="buy_star_menu")],
        [InlineKeyboardButton("⭐ Yıldız ile CarpiPuan Satın Al", callback_data="buy_star_points_menu")],
        [InlineKeyboardButton("🎁 Şanslı Kod Al (/kodal)", callback_data="cmd_kodal")],
        [InlineKeyboardButton("⭐ Günlük / 12 Saatlik Bonuslar", callback_data="cmd_bonuslar")],
        [InlineKeyboardButton("👥 Arkadaşını Davet Et (+5 CarpiPuan)", callback_data="invite")],
        [InlineKeyboardButton("👤 Profilim & Puan Durumum", callback_data="profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"🚀 CPM1 Hesap Mağazasına Hoş Geldin!\n\n"
        f"📦 Güncel Stok: {len(stock)} adet hesap\n"
        f"🏆 CarpiPuanın: {points:.1f} CarpiPuan\n"
        f"(15 CarpiPuan = 1 Ücretsiz Hesap)\n\n"
        f"Aşağıdaki menüden işlem seçebilirsin:"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup)

# --- ŞANSLI KOD SİSTEMİ ---
async def kod_talep_et(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    simdiki_zaman = time.time()
    points, refs, last_kod_time, last_bonus_yildiz, kayit_zamani = get_user_balance(user.id)
    
    kullanilan_sayi = get_campaign_count()
    TOPLAM_LIMIT = 98230
    
    if kullanilan_sayi >= TOPLAM_LIMIT:
        msg = "Üzgünüm reis, 98.230 kişilik toplam kampanya limiti dolmuştur."
        if update.message: await update.message.reply_text(msg)
        elif update.callback_query: await update.callback_query.message.reply_text(msg)
        return
        
    otuz_gun = 30 * 24 * 60 * 60
    if last_kod_time > 0:
        gecen_sure = simdiki_zaman - last_kod_time
        if gecen_sure < otuz_gun:
            kalan_gun = int((otuz_gun - gecen_sure) / (24 * 60 * 60))
            msg = f"Bu kampanyadan tekrar yararlanabilmek için {kalan_gun} gün beklemelisin."
            if update.message: await update.message.reply_text(msg)
            elif update.callback_query: await update.callback_query.message.reply_text(msg)
            return

    gecen_gun_sayisi = int((simdiki_zaman - kayit_zamani) / (24 * 60 * 60))
    harfler = random.choice(["CPM", "CRP", "BOT", "CAR"])
    sayilar = random.randint(1000, 9999)
    uretilen_kod = f"{harfler}{sayilar}"
    odul_turu = random.choice(["Yıldız", "Carpipuan"])
    
    ozel_gunler = [20, 30, 40, 60, 365, 10000]
    if any(abs(gecen_gun_sayisi - og) <= 1 for og in ozel_gunler):
        secenekler = [round(random.randint(5, 15) / 10.0, 1), random.randint(10, 80)]
        odul_miktari = random.choice(secenekler)
    else:
        secenekler_normal = [round(random.randint(5, 9) / 10.0, 1), random.randint(2, 10)]
        odul_miktari = random.choice(secenekler_normal)
    
    with open(KODLAR_FILE, "a", encoding="utf-8") as f:
        f.write(f"{uretilen_kod},{user.id},{odul_turu},{odul_miktari}\n")
        
    update_user_balance_extended(user.id, points, refs, simdiki_zaman, last_bonus_yildiz, kayit_zamani)
    save_campaign_count(kullanilan_sayi + 1)
    
    kalan_kot = TOPLAM_LIMIT - (kullanilan_sayi + 1)
    
    mesaj = (
        f"🎯 **Şanslı Kodun Üretildi!**\n\n"
        f"🔑 Kodun: `{uretilen_kod}`\n"
        f"🎁 Ödül: **{odul_miktari} {odul_turu}**\n"
        f"Kullanmak için: `/kullan {uretilen_kod}`"
    )
    if update.message:
        await update.message.reply_text(mesaj, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.reply_text(mesaj, parse_mode="Markdown")

async def kodu_aktif_et(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if not args:
        await update.message.reply_text("Lütfen bir kod giriniz.\nÖrnek: `/kullan CPM9000` veya `/kod CPM-50Puan-A3F`", parse_mode="Markdown")
        return
        
    girilen_kod = args[0].strip().upper()
    
    # 1. Önce özel ürün kodlarına bak (Yıldız ile satın alım kodları)
    custom_codes = load_custom_codes()
    if girilen_kod in custom_codes:
        if custom_codes[girilen_kod]["used"]:
            await update.message.reply_text("❌ Bu kod daha önce **kullanılmış**!")
            return
        custom_codes[girilen_kod]["used"] = True
        save_custom_codes(custom_codes)
        await update.message.reply_text(f"✅ Ürün kodunuz başarıyla onaylandı ve aktifleşti! ({custom_codes[girilen_kod]['product']})")
        return

    # 2. Şanslı kodlara bak
    if not os.path.exists(KODLAR_FILE):
        await update.message.reply_text("❌ Geçersiz kod.")
        return
        
    satirlar = []
    bulundu = False
    odul_bilgisi = None
    
    with open(KODLAR_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) == 4:
                kod, kid, tur, miktar = parts
                if kod == girilen_kod:
                    bulundu = True
                    if int(kid) != user.id:
                        await update.message.reply_text("❌ Bu kod başka bir kullanıcıya aittir.")
                        satirlar.append(line)
                        continue
                    odul_bilgisi = (tur, float(miktar) if "." in miktar or float(miktar).is_integer() == False else int(miktar))
                    continue
            satirlar.append(line)
            
    if not bulundu:
        await update.message.reply_text("❌ Girdiğiniz kod geçersiz veya daha önce kullanılmış.")
        return
        
    with open(KODLAR_FILE, "w", encoding="utf-8") as f:
        f.writelines(satirlar)
        
    tur, miktar = odul_bilgisi
    points, refs, lk, lb, kz = get_user_balance(user.id)
    update_user_balance_extended(user.id, points + miktar, refs, lk, lb, kz)
    await update.message.reply_text(f"🎉 Kod başarıyla onaylandı!\nHesabına **{miktar} {tur}** eklendi.", parse_mode="Markdown")

async def gunluk_bonus_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    simdiki_zaman = time.time()
    points, refs, lk, last_bonus_yildiz, kz = get_user_balance(user.id)
    
    bir_gun = 24 * 60 * 60
    if simdiki_zaman - last_bonus_yildiz < bir_gun:
        kalan = int((bir_gun - (simdiki_zaman - last_bonus_yildiz)) / 3600)
        msg = f"⏳ Günlük yıldız bonusu için {kalan} saat beklemelisin."
        if update.message: await update.message.reply_text(msg)
        elif update.callback_query: await update.callback_query.message.reply_text(msg)
        return
        
    kazanilan_yildiz = round(random.randint(9, 13) / 10.0, 1)
    update_user_balance_extended(user.id, points, refs, lk, simdiki_zaman, kz)
    
    msg = f"⭐ Günlük Yıldız Bonusun Yüklendi: **{kazanilan_yildiz} Yıldız**"
    if update.message: await update.message.reply_text(msg, parse_mode="Markdown")
    elif update.callback_query: await update.callback_query.message.reply_text(msg, parse_mode="Markdown")

async def carpipuan_bonus_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    kazanilan_puan = round(random.randint(3, 9) / 10.0, 1)
    points, refs, lk, lb, kz = get_user_balance(user.id)
    update_user_balance_extended(user.id, points + kazanilan_puan, refs, lk, lb, kz)
    
    msg = f"🎁 12 Saatlik Bonus Yüklendi: **{kazanilan_puan} CarpiPuan**"
    if update.message: await update.message.reply_text(msg, parse_mode="Markdown")
    elif update.callback_query: await update.callback_query.message.reply_text(msg, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    points, refs, _, _, _ = get_user_balance(user.id)

    if query.data == "profile":
        stock = load_stock()
        text = (
            f"👤 **Profil Bilgilerin:**\n\n"
            f"🆔 ID: `{user.id}`\n"
            f"🏆 CarpiPuan: {points:.1f}\n"
            f"📦 Mağaza Stok: {len(stock)} adet\n\n"
            f"🔗 Davet Linkin:\n`https://t.me/{context.bot.username}?start={user.id}`"
        )
        keyboard = [[InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="main_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "invite":
        invite_link = f"https://t.me/{context.bot.username}?start={user.id}"
        text = f"👥 **Davet Et Kazan!**\n\nHer arkadaşın için +5 Puan:\n`{invite_link}`"
        keyboard = [[InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="main_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "cmd_kodal":
        await kod_talep_et(update, context)

    elif query.data == "cmd_bonuslar":
        keyboard = [
            [InlineKeyboardButton("⭐ Günlük Yıldız Al", callback_data="claim_star_bonus")],
            [InlineKeyboardButton("📦 12 Saatlik CarpiPuan Al", callback_data="claim_point_bonus")],
            [InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="main_menu")]
        ]
        await query.message.edit_text("🎁 **Bonus Merkezi**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "claim_star_bonus":
        await gunluk_bonus_al(update, context)

    elif query.data == "claim_point_bonus":
        await carpipuan_bonus_al(update, context)

    elif query.data == "main_menu":
        await start(update, context)

    elif query.data == "buy_point":
        if points < 15:
            await query.message.reply_text("❌ Yetersiz CarpiPuan! (15 Puan gerekli)")
            return
        stock = load_stock()
        if not stock:
            await query.message.reply_text("❌ Stok kalmadı!")
            return
        
        account = stock.pop(0)
        save_stock(stock)
        p_curr, r_curr, lk_curr, lb_curr, kz_curr = get_user_balance(user.id)
        update_user_balance_extended(user.id, p_curr - 15, r_curr, lk_curr, lb_curr, kz_curr)
        
        secret_code = generate_unique_code("1x_Hesap")
        await query.message.reply_text(f"✅ Hesap satın alındı!\n\n🔑 **Hesap Bilgisi:** `{account}`\n🎁 **Size Özel Tek Kullanımlık Kodunuz:** `{secret_code}`", parse_mode="Markdown")

    elif query.data == "buy_star_menu":
        keyboard = [
            [InlineKeyboardButton("⚡ 1 Adet Hesap (15 Yıldız)", callback_data="star_acc_1")],
            [InlineKeyboardButton("⚡ 2 Adet Hesap (30 Yıldız)", callback_data="star_acc_2")],
            [InlineKeyboardButton("⚡ 5 Adet Hesap (50 Yıldız - İndirimli)", callback_data="star_acc_5")],
            [InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="main_menu")]
        ]
        await query.message.edit_text("⭐ **Yıldız ile Hesap Alımı**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("star_acc_"):
        count = int(query.data.split("_")[2])
        unit_price = 15 if count < 5 else 10
        total_stars = count * unit_price
        prices = [LabeledPrice(f"{count} Adet Hesap", total_stars)]
        
        await context.bot.send_invoice(
            chat_id=user.id, title=f"{count} Adet Hesap", description=f"{count} adet hesap teslimi",
            payload=f"star_acc_{count}", provider_token=PROVIDER_TOKEN, currency="XTR", prices=prices
        )

    elif query.data == "buy_star_points_menu":
        keyboard = [
            [InlineKeyboardButton("📦 50 CarpiPuan (50 Yıldız)", callback_data="star_p_50")],
            [InlineKeyboardButton("📦 100 CarpiPuan (90 Yıldız)", callback_data="star_p_100")],
            [InlineKeyboardButton("📦 500 CarpiPuan (400 Yıldız)", callback_data="star_p_500")],
            [InlineKeyboardButton("📦 1.000 CarpiPuan (750 Yıldız)", callback_data="star_p_1000")],
            [InlineKeyboardButton("📦 5.000 CarpiPuan (3.500 Yıldız)", callback_data="star_p_5000")],
            [InlineKeyboardButton("📦 10.000 CarpiPuan (6.500 Yıldız)", callback_data="star_p_10000")],
            [InlineKeyboardButton("📦 40.000 CarpiPuan (22.000 Yıldız)", callback_data="star_p_40000")],
            [InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="main_menu")]
        ]
        await query.message.edit_text("⭐ **Yıldız ile CarpiPuan Al**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("star_p_"):
        amount = query.data.split("_")[2]
        package_map = {
            "50": (50, 50), 
            "100": (90, 100), 
            "500": (400, 500), 
            "1000": (750, 1000), 
            "5000": (3500, 5000), 
            "10000": (6500, 10000), 
            "20000": (12000, 20000), 
            "40000": (22000, 40000)
        }
        stars, points_to_add = package_map[amount]
        prices = [LabeledPrice(f"{points_to_add} CarpiPuan", stars)]
        
        await context.bot.send_invoice(
            chat_id=user.id, title=f"{points_to_add} CarpiPuan", description=f"{points_to_add} CarpiPuan yükleme",
            payload=f"star_p_{amount}", provider_token=PROVIDER_TOKEN, currency="XTR", prices=prices
        )

# --- ÖDEME DOĞRULAMA ---
async def pre_checkout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    payment = update.message.successful_payment
    payload = payment.invoice_payload
    points, refs, lk, lb, kz = get_user_balance(user.id)

    if payload.startswith("star_acc_"):
        count = int(payload.split("_")[2])
        status_stock = load_stock()
        accounts = []
        for _ in range(count):
            if status_stock:
                accounts.append(status_stock.pop(0))
            else:
                accounts.append("Stok eklenecek")
        save_stock(status_stock)
        
        acc_text = "\n".join([f"`{a}`" for a in accounts])
        secret_code = generate_unique_code(f"{count}x_Hesap")
        await update.message.reply_text(f"🎉 Ödeme başarılı!\n\n🔑 **Hesaplar:**\n{acc_text}\n\n🎁 **Size Özel Tek Kullanımlık Kodunuz:** `{secret_code}`", parse_mode="Markdown")

    elif payload.startswith("star_p_"):
        amount_str = payload.sp
