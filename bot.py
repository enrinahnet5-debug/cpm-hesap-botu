import json
import os
import random
import string
import threading
import time
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

# Flask Keep-Alive Sunucusu (Railway / Render uyumlu)
app = Flask(__name__)

@app.route("/")
def home():
    return "CPM1 VIP Mağaza Aktif ve Çalışıyor!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

ADMIN_IDS = [8520025523]
BOT_USERNAME = "Cpm1Hesap_Satis_bot"
TOKEN = "8962445060:AAFypELLnBZ-1NDdU_4gUeIjNBZL-gWORTE"

DB_FILE = "veritabani.json"

def veri_yukle():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"users": {}, "email_passwords": {}, "promo_codes": {}, "banned": []}

def veri_kaydet():
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(DB_DATA, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

DB_DATA = veri_yukle()
if not isinstance(DB_DATA, dict) or "users" not in DB_DATA:
    DB_DATA = {"users": {}, "email_passwords": {}, "promo_codes": {}, "banned": []}

if "promo_codes" not in DB_DATA:
    DB_DATA["promo_codes"] = {}

KULLANICILAR = DB_DATA["users"]
PROMO_CODES = DB_DATA["promo_codes"]

def stok_oku():
    if not os.path.exists("stok.txt"):
        with open("stok.txt", "w", encoding="utf-8") as f:
            f.write("")
        return []
    with open("stok.txt", "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines() if line.strip() and ":" in line]

def stok_dusur_ve_ver(adet=1):
    stoklar = stok_oku()
    if len(stoklar) < adet:
        return None
    verilecek_hesaplar = stoklar[:adet]
    with open("stok.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(stoklar[adet:]) + "\n")
    return verilecek_hesaplar

def get_ana_menu_keyboard(stok_adet, user_data=None):
    h_adet = user_data.get("hesap_adet", 1) if user_data else 1
    h_yildiz = h_adet * 15
    h_puan = h_adet * 300.0

    c_adet = user_data.get("coin_hesap_adet", 1) if user_data else 1
    c_yildiz = c_adet * 50
    c_puan = c_adet * 1000.0

    f_adet = user_data.get("full_hesap_adet", 1) if user_data else 1
    f_yildiz = f_adet * 100
    f_puan = f_adet * 2000.0

    karaborsa_uyari = " (🔥 Karaborsa!)" if stok_adet < 5 and stok_adet > 0 else ""

    keyboard = [
        [
            InlineKeyboardButton("➖", callback_data="h_az"),
            InlineKeyboardButton(f"🎲 {h_adet} Adet Random ({h_yildiz} ⭐️ / +{h_puan} Puan){karaborsa_uyari}", callback_data="bos_bilgi"),
            InlineKeyboardButton("➕", callback_data="h_art"),
        ],
        [
            InlineKeyboardButton(f"💳 Random Al (Puan ile: +{h_puan})", callback_data="hp_al"),
            InlineKeyboardButton(f"⭐ Random Al (Yıldız ile: {h_yildiz})", callback_data="hy_al"),
        ],
        [
            InlineKeyboardButton("➖", callback_data="c_az"),
            InlineKeyboardButton(f"💰 {c_adet} Adet 250-500k Coin ({c_yildiz} ⭐️ / +{c_puan} Puan)", callback_data="bos_bilgi"),
            InlineKeyboardButton("➕", callback_data="c_art"),
        ],
        [
            InlineKeyboardButton(f"💳 Coinli Al (Puan ile: +{c_puan})", callback_data="cp_al"),
            InlineKeyboardButton(f"⭐ Coinli Al (Yıldız ile: {c_yildiz})", callback_data="cy_al"),
        ],
        [
            InlineKeyboardButton("➖", callback_data="f_az"),
            InlineKeyboardButton(f"👑 {f_adet} Adet Full+Full ({f_yildiz} ⭐️ / +{f_puan} Puan)", callback_data="bos_bilgi"),
            InlineKeyboardButton("➕", callback_data="f_art"),
        ],
        [
            InlineKeyboardButton(f"💳 Full Al (Puan ile: +{f_puan})", callback_data="fp_al"),
            InlineKeyboardButton(f"⭐ Full Al (Yıldız ile: {f_yildiz})", callback_data="fy_al"),
        ],
        [
            InlineKeyboardButton("👑 VIP Abonelik Al (300 Yıldız / Ay)", callback_data="vip_satin_al")
        ],
        [
            InlineKeyboardButton("⭐ Yıldız ile ApexPuan Yükle", callback_data="puan_menu")
        ],
        [
            InlineKeyboardButton("🛠️ .es3 Şifre Yapıcı", callback_data="es3_yapici")
        ],
        [
            InlineKeyboardButton("🔐 Şifreyi Çöz & Ödülü Kap (3 Yıldız)", callback_data="sifre_baslat")
        ],
        [
            InlineKeyboardButton("🎁 Bana Özel Promo Kodu Üret", callback_data="promo_kullan")
        ],
        [
            InlineKeyboardButton("🎁 Günlük Ödül Al", callback_data="gunluk")
        ],
        [
            InlineKeyboardButton("🏆 Liderlik Tablosu", callback_data="liderlik")
        ],
        [
            InlineKeyboardButton("👥 Arkadaşını Davet Et (+50 ApexPuan)", callback_data="davet")
        ],
        [
            InlineKeyboardButton("👤 Profilim & Bilgilerim", callback_data="profil")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_str = str(update.effective_user.id)
    if user_id_str in DB_DATA.get("banned", []):
        await update.message.reply_text("❌ Bu botu kullanmanız yasaklanmıştır.")
        return

    args = context.args
    if user_id_str not in KULLANICILAR:
        KULLANICILAR[user_id_str] = {
            "carpipuan": 0.0,
            "son_gunluk": 0,
            "davet_edildi": False,
            "davet_sayisi": 0,
            "hesap_adet": 1,
            "coin_hesap_adet": 1,
            "full_hesap_adet": 1,
            "sifre_oyunu_kullanildi": False,
            "beklenen_sifre": None,
            "used_promos": [],
            "vip_bitis": 0,
        }
        if args and args[0].startswith("ref_"):
            try:
                ref_id_str = args[0].split("_")[1]
                if ref_id_str != user_id_str and ref_id_str in KULLANICILAR:
                    if not KULLANICILAR[user_id_str].get("davet_edildi", False):
                        KULLANICILAR[user_id_str]["davet_edildi"] = True
                        KULLANICILAR[ref_id_str]["carpipuan"] = round(
                            KULLANICILAR[ref_id_str]["carpipuan"] + 50.0, 1
                        )
                        KULLANICILAR[ref_id_str]["davet_sayisi"] = (
                            KULLANICILAR[ref_id_str].get("davet_sayisi", 0) + 1
                        )
                        veri_kaydet()
                        try:
                            await context.bot.send_message(
                                chat_id=int(ref_id_str),
                                text="🎉 Tebrikler reis! Davet ettiğin kullanıcı botu başlattı ve hesabına +50 ApexPuan eklendi!",
                            )
                        except Exception:
                            pass
            except Exception:
                pass
        veri_kaydet()

    stok_adet = len(stok_oku())
    user_data = KULLANICILAR[user_id_str]
    mesaj = f"🚀 CPM1 VIP Mağazasına Hoş Geldin!\n\n📦 Güncel Stok: {stok_adet} adet hesap\n⭐ ApexPuanın: +{user_data['carpipuan']} ApexPuan\n\nAşağıdaki menüden işlem seçebilirsin:"
    await update.message.reply_text(
        mesaj,
        reply_markup=get_ana_menu_keyboard(stok_adet, user_data),
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id_str = str(query.from_user.id)
    user_id = query.from_user.id

    if user_id_str in DB_DATA.get("banned", []):
        await query.answer("❌ Engellendiğin için işlem yapamazsın.", show_alert=True)
        return

    if user_id_str not in KULLANICILAR:
        KULLANICILAR[user_id_str] = {
            "carpipuan": 0.0,
            "son_gunluk": 0,
            "hesap_adet": 1,
            "coin_hesap_adet": 1,
            "full_hesap_adet": 1,
            "sifre_oyunu_kullanildi": False,
            "beklenen_sifre": None,
            "used_promos": [],
            "vip_bitis": 0,
        }
        veri_kaydet()

    user_data = KULLANICILAR[user_id_str]
    stok_adet = len(stok_oku())

    if query.data == "bos_bilgi":
        await query.answer()
        return

    elif query.data == "ana_menu":
        await query.answer()
        mesaj = f"🚀 CPM1 VIP Mağazasına Hoş Geldin!\n\n📦 Güncel Stok: {stok_adet} adet hesap\n⭐ ApexPuanın: +{user_data['carpipuan']} ApexPuan\n\nAşağıdaki menüden işlem seçebilirsin:"
        await query.edit_message_text(mesaj, reply_markup=get_ana_menu_keyboard(stok_adet, user_data))

    elif query.data == "es3_yapici":
        await query.answer()
        keyboard = [[InlineKeyboardButton("🔙 Menü", callback_data="ana_menu")]]
        mesaj = (
            "🛠️ **.es3 Şifre Yapıcı Aracı**\n\n"
            "Car Parking Multiplayer .es3 dosyalarındaki şifreleme ve düzenleme "
            "işlemleri için bu aracı kullanabilirsin."
        )
        await query.edit_message_text(mesaj, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "vip_satin_al":
        await query.answer()
        await context.bot.send_invoice(
            chat_id=user_id,
            title="👑 1 Aylık VIP Abonelik",
            description="Her gün rastgele 5 - 30 ApexPuan kazanma hakkı!",
            payload="vip_uyelik_300",
            currency="XTR",
            prices=[LabeledPrice("VIP Abonelik", 300)],
        )

    elif query.data == "promo_kullan":
        await query.answer()
        context.user_data["beklenen_islem"] = "promo_gir"
        keyboard = [[InlineKeyboardButton("🔙 İptal / Ana Menü", callback_data="ana_menu")]]
        await query.edit_message_text(
            "🎟️ Lütfen kullanmak istediğin Promo Kodu sohbete mesaj olarak yaz:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "h_art":
        await query.answer()
        if user_data["hesap_adet"] < max(1, stok_adet if stok_adet > 0 else 1):
            user_data["hesap_adet"] += 1
            veri_kaydet()
        try:
            await query.edit_message_reply_markup(reply_markup=get_ana_menu_keyboard(stok_adet, user_data))
        except Exception:
            pass

    elif query.data == "h_az":
        await query.answer()
        if user_data["hesap_adet"] > 1:
            user_data["hesap_adet"] -= 1
            veri_kaydet()
        try:
            await query.edit_message_reply_markup(reply_markup=get_ana_menu_keyboard(stok_adet, user_data))
        except Exception:
            pass

    elif query.data == "c_art":
        await query.answer()
        if user_data["coin_hesap_adet"] < max(1, stok_adet if stok_adet > 0 else 1):
            user_data["coin_hesap_adet"] += 1
            veri_kaydet()
        try:
            await query.edit_message_reply_markup(reply_markup=get_ana_menu_keyboard(stok_adet, user_data))
        except Exception:
            pass

    elif query.data == "c_az":
        await query.answer()
        if user_data["coin_hesap_adet"] > 1:
            user_data["coin_hesap_adet"] -= 1
            veri_kaydet()
        try:
            await query.edit_message_reply_markup(reply_markup=get_ana_menu_keyboard(stok_adet, user_data))
        except Exception:
            pass

    elif query.data == "f_art":
        await query.answer()
        if user_data["full_hesap_adet"] < max(1, stok_adet if stok_adet > 0 else 1):
            user_data["full_hesap_adet"] += 1
            veri_kaydet()
        try:
            await query.edit_message_reply_markup(reply_markup=get_ana_menu_keyboard(stok_adet, user_data))
        except Exception:
            pass

    elif query.data == "f_az":
        await query.answer()
        if user_data["full_hesap_adet"] > 1:
            user_data["full_hesap_adet"] -= 1
            veri_kaydet()
        try:
            await query.edit_message_reply_markup(reply_markup=get_ana_menu_keyboard(stok_adet, user_data))
        except Exception:
            pass

    elif query.data == "hp_al":
        adet = user_data.get("hesap_adet", 1)
        gerekli_puan = float(adet * 300)
        if user_data["carpipuan"] < gerekli_puan:
            await query.answer(f"❌ Yetersiz ApexPuan! Lazım: +{gerekli_puan}", show_alert=True)
            return
        if stok_adet < adet:
            await query.answer("❌ Stok kalmadı!", show_alert=True)
            return
        verilenler = stok_dusur_ve_ver(adet)
        if verilenler:
            await query.answer()
            user_data["carpipuan"] = round(user_data["carpipuan"] - gerekli_puan, 1)
            veri_kaydet()
            hesaplar_metni = "\n".join(verilenler)
            keyboard = [[InlineKeyboardButton("🔙 Menü", callback_data="ana_menu")]]
            try:
                mesaj = f"✅ Random VIP Hesaplar Verildi!\n\n🔑 Bilgiler:\n{hesaplar_metni}\n\n⭐ Kalan ApexPuan: +{user_data['carpipuan']}"
                await query.edit_message_text(mesaj, reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception:
                await context.bot.send_message(chat_id=user_id, text=f"✅ Random VIP Hesaplar:\n\n{hesaplar_metni}")

    elif query.data == "hy_al":
        await query.answer()
        adet = user_data.get("hesap_adet", 1)
        toplam_fiyat = adet * 15
        if stok_adet < adet:
            await query.answer("❌ Stok yetersiz!", show_alert=True)
            return
        await context.bot.send_invoice(
            chat_id=user_id,
            title=f"{adet} Adet Random Hesap",
            description=f"{adet} Adet Random Hesap ({toplam_fiyat} Yıldız)",
            payload=f"hesap_random_{adet}",
            currency="XTR",
            prices=[LabeledPrice("Random Hesap", toplam_fiyat)],
        )

    elif query.data == "cp_al":
        adet = user_data.get("coin_hesap_adet", 1)
        gerekli_puan = float(adet * 1000)
        if user_data["carpipuan"] < gerekli_puan:
            await query.answer(f"❌ Yetersiz ApexPuan! Lazım: +{gerekli_puan}", show_alert=True)
            return
        if stok_adet < adet:
            await query.answer("❌ Stok kalmadı!", show_alert=True)
            return
        verilenler = stok_dusur_ve_ver(adet)
        if verilenler:
            await query.answer()
            user_data["carpipuan"] = round(user_data["carpipuan"] - gerekli_puan, 1)
            veri_kaydet()
            hesaplar_metni = "\n".join(verilenler)
            keyboard = [[InlineKeyboardButton("🔙 Menü", callback_data="ana_menu")]]
            try:
                mesaj = f"✅ 250-500k Coinli Hesaplar Verildi!\n\n🔑 Bilgiler:\n{hesaplar_metni}\n\n⭐ Kalan ApexPuan: +{user_data['carpipuan']}"
                await query.edit_message_text(mesaj, reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception:
                await context.bot.send_message(chat_id=user_id, text=f"✅ Coinli Hesaplar:\n\n{hesaplar_metni}")

    elif query.data == "cy_al":
        await query.answer()
        adet = user_data.get("coin_hesap_adet", 1)
        toplam_fiyat = adet * 50
        if stok_adet < adet:
            await query.answer("❌ Stok yetersiz!", show_alert=True)
            return
        await context.bot.send_invoice(
            chat_id=user_id,
            title=f"{adet} Adet Coinli Hesap",
            description=f"{adet} Adet 250-500k Coinli Hesap ({toplam_fiyat} Yıldız)",
            payload=f"hesap_coin_{adet}",
            currency="XTR",
            prices=[LabeledPrice("Coinli Hesap", toplam_fiyat)],
        )

    elif query.data == "fp_al":
        adet = user_data.get("full_hesap_adet", 1)
        gerekli_puan = float(adet * 2000)
        if user_data["carpipuan"] < gerekli_puan:
            await query.answer(f"❌ Yetersiz ApexPuan! Lazım: +{gerekli_puan}", show_alert=True)
            return
        if stok_adet < adet:
            await query.answer("❌ Stok kalmadı!", show_alert=True)
            return
        verilenler = stok_dusur_ve_ver(adet)
        if verilenler:
            await query.answer()
            user_data["carpipuan"] = round(user_data["carpipuan"] - gerekli_puan, 1)
            veri_kaydet()
            hesaplar_metni = "\n".join(verilenler)
            keyboard = [[InlineKeyboardButton("🔙 Menü", callback_data="ana_menu")]]
            try:
                mesaj = f"✅ Full+Full Her Şeyi Açık Hesaplar Verildi!\n\n🔑 Bilgiler:\n{hesaplar_metni}\n\n⭐ Kalan ApexPuan: +{user_data['carpipuan']}"
                await query.edit_message_text(mesaj, reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception:
                await context.bot.send_message(chat_id=user_id, text=f"✅ Full Hesaplar:\n\n{hesaplar_metni}")

    elif query.data == "fy_al":
        await query.answer()
        adet = user_data.get("full_hesap_adet", 1)
        toplam_fiyat = adet * 100
        if stok_adet < adet:
            await query.answer("❌ Stok yetersiz!", show_alert=True)
            return
        await context.bot.send_invoice(
            chat_id=user_id,
            title=f"{adet} Adet Full+Full Hesap",
            description=f"{adet} Adet Full+Full Her Şeyi Açık Hesap ({toplam_fiyat} Yıldız)",
            payload=f"hesap_full_{adet}",
            currency="XTR",
            prices=[LabeledPrice("Full Hesap", toplam_fiyat)],
        )

    elif query.data == "sifre_baslat":
        await query.answer()
        if user_data.get("sifre_oyunu_kullanildi", False):
            await query.answer("❌ Hakkını zaten kullandın!", show_alert=True)
            return
        user_data["sifre_oyunu_kullanildi"] = True
        veri_kaydet()
        await context.bot.send_invoice(
            chat_id=user_id,
            title="🔐 Şifre Çözme Oyunu",
            description="3 Yıldız öde, şifreyi al ve sohbete yaz!",
            payload="sifre_oyunu_3_yildiz",
            currency="XTR",
            prices=[LabeledPrice("Sifre Hakki", 3)],
        )

    elif query.data == "puan_menu":
        await query.answer()
        keyboard = [
            [InlineKeyboardButton("⭐ 100 ApexPuan ➔ 50 Yıldız", callback_data="apex_100")],
            [InlineKeyboardButton("⭐ 250 ApexPuan ➔ 120 Yıldız", callback_data="apex_250")],
            [InlineKeyboardButton("⭐ 500 ApexPuan ➔ 250 Yıldız", callback_data="apex_500")],
            [InlineKeyboardButton("⭐ 1,000 ApexPuan ➔ 500 Yıldız", callback_data="apex_1000")],
            [InlineKeyboardButton("⭐ 2,000 ApexPuan ➔ 1,050 Yıldız", callback_data="apex_2000")],
            [InlineKeyboardButton("⭐ 5,000 ApexPuan ➔ 2,700 Yıldız", callback_data="apex_5000")],
            [InlineKeyboardButton("⭐ 10,000 ApexPuan ➔ 5,500 Yıldız", callback_data="apex_10000")],
            [InlineKeyboardButton("⭐ 50,000 ApexPuan ➔ 28,000 Yıldız", callback_data="apex_50000")],
            [InlineKeyboardButton("⭐ 100,000 ApexPuan ➔ 58,000 Yıldız", callback_data="apex_100000")],
            [InlineKeyboardButton("🔙 Menü", callback_data="ana_menu")],
        ]
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("apex_"):
        await query.answer()
        puan_miktari = int(query.data.split("_")[1])
        fiyat_tablosu = {
            100: 50, 250: 120, 500: 250, 1000: 500, 2000: 1050,
            5000: 2700, 10000: 5500, 50000: 28000, 100000: 58000
        }
        yildiz_fiyati = fiyat_tablosu.get(puan_miktari, 50)
        await context.bot.send_invoice(
            chat_id=user_id,
            title="⭐ ApexPuan Elit Paket",
            description=f"{puan_miktari:,} ApexPuan Yüklemesi",
            payload=f"apex_yukle_{puan_miktari}",
            currency="XTR",
            prices=[LabeledPrice("ApexPuan", yildiz_fiyati)],
        )

    elif query.data == "gunluk":
        await query.answer()
