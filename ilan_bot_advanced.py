import requests
from bs4 import BeautifulSoup
import telebot
import time
import os
import threading
import logging
import re
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from datetime import datetime

# SSL uyarılarını kapat
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Logging ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Telegram bilgileri
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    logger.error("BOT_TOKEN bulunamadı! Lütfen çevre değişkenlerini kontrol edin.")
    exit(1)

logger.info("Bot başlatılıyor...")

# Bot oluştur ve webhook temizle
bot = None

# Güncel ilan sayısı (global değişken)
current_ilan_count = 0

def setup_bot():
    global bot
    try:
        bot = telebot.TeleBot(TOKEN)
        # Webhook temizleme
        bot.remove_webhook()
        time.sleep(2)  # API'nin işlemesi için bekle
        logger.info("Webhook temizlendi")
        return bot
    except Exception as e:
        logger.error(f"Bot kurulum hatası: {e}")
        raise

# URL ve geçmiş dosyası
URL = "https://www.ilan.gov.tr/ilan/kategori/693/arastirma-gorevlisi-ogretim-gorevlisi-uzman"
ILAN_SAYISI_DOSYA = "son_ilan_sayisi.txt"
SUBSCRIBERS_FILE = "users.txt"
SON_BILDIRIM_TARIHI = "son_bildirim.txt"

# Abone listesini oku
def read_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            pass
        return set()
    
    try:
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            return set(int(line.strip()) for line in f if line.strip().isdigit())
    except Exception as e:
        logger.error(f"Abone listesi okuma hatası: {e}")
        return set()

# Yeni abone ekle
def write_subscriber(chat_id):
    try:
        with open(SUBSCRIBERS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{chat_id}\n")
        logger.info(f"Yeni abone eklendi: {chat_id}")
    except Exception as e:
        logger.error(f"Abone ekleme hatası: {e}")

# Son ilan sayısını oku
def son_ilan_sayisini_oku():
    if not os.path.exists(ILAN_SAYISI_DOSYA):
        return 0
    
    try:
        with open(ILAN_SAYISI_DOSYA, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return int(content) if content.isdigit() else 0
    except Exception as e:
        logger.error(f"Son ilan sayısı okuma hatası: {e}")
        return 0

# Son ilan sayısını kaydet
def son_ilan_sayisini_kaydet(sayi):
    try:
        with open(ILAN_SAYISI_DOSYA, "w", encoding="utf-8") as f:
            f.write(str(sayi))
        logger.info(f"Son ilan sayısı kaydedildi: {sayi}")
    except Exception as e:
        logger.error(f"İlan sayısı kaydetme hatası: {e}")

# Son bildirim tarihini kaydet
def son_bildirim_tarihini_kaydet():
    try:
        with open(SON_BILDIRIM_TARIHI, "w", encoding="utf-8") as f:
            f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    except Exception as e:
        logger.error(f"Son bildirim tarihi kaydetme hatası: {e}")

# Son bildirim tarihini oku
def son_bildirim_tarihini_oku():
    if not os.path.exists(SON_BILDIRIM_TARIHI):
        return "Henüz bildirim gönderilmedi"
    
    try:
        with open(SON_BILDIRIM_TARIHI, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"Son bildirim tarihi okuma hatası: {e}")
        return "Bilinmiyor"

# Bot komut işleyicileri
def setup_handlers(bot):
    @bot.message_handler(commands=['start'])
    def subscribe(message):
        chat_id = message.chat.id
        try:
            subs = read_subscribers()
            if chat_id not in subs:
                write_subscriber(chat_id)
                bot.send_message(chat_id, "✅ Bot aboneliğine kaydoldunuz! Yeni ilanları alacaksınız.")
                logger.info(f"Yeni abone: {chat_id}")
            else:
                bot.send_message(chat_id, "ℹ️ Zaten abonesiniz, yeni ilanlar geldikçe bilgilendirileceksiniz.")
                logger.info(f"Mevcut abone tekrar kaydolmaya çalıştı: {chat_id}")
        except Exception as e:
            logger.error(f"Subscribe handler hatası: {e}")
            bot.send_message(chat_id, "⚠️ Bir hata oluştu, lütfen tekrar deneyin.")

    # Son durumu göster
    @bot.message_handler(commands=['durum'])
    def show_status(message):
        try:
            son_ilan_sayisi = son_ilan_sayisini_oku()
            son_bildirim = son_bildirim_tarihini_oku()
            abone_sayisi = len(read_subscribers())
            
            mesaj = (
                f"📊 *Bot Durumu*\n"
                f"📌 Güncel ilan sayısı: {current_ilan_count}\n"
                f"📋 Son kaydedilen ilan sayısı: {son_ilan_sayisi}\n"
                f"👥 Toplam abone: {abone_sayisi}\n"
                f"⏱️ Son bildirim zamanı: {son_bildirim}\n"
                f"🔄 Kontrol sıklığı: Her saat\n"
                f"🌐 İzlenen URL: {URL}"
            )
            
            bot.send_message(message.chat.id, mesaj, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Durum gösterme hatası: {e}")
            bot.send_message(message.chat.id, "⚠️ Durum bilgisi alınamadı.")

    # Diğer mesajlar
    @bot.message_handler(func=lambda message: True)
    def default_reply(message):
        try:
            # Şu anki ilan sayısını söyle
            if current_ilan_count > 0:
                bot.send_message(
                    message.chat.id, 
                    f"📢 Şu anda sistemde toplam {current_ilan_count} ilan bulunuyor.\n\nAbone olmak için /start yazabilirsiniz. Durum bilgisi için /durum yazabilirsiniz."
                )
            else:
                bot.send_message(
                    message.chat.id, 
                    "Lütfen /start yazarak abone olun. Durum bilgisi için /durum yazabilirsiniz."
                )
        except Exception as e:
            logger.error(f"Default handler hatası: {e}")

def ilanlari_kontrol_et():
    global current_ilan_count
    
    if not bot:
        logger.error("Bot henüz başlatılmadı, ilanlar kontrol edilemiyor")
        return

    logger.info("🔍 İlanlar kontrol ediliyor...")
    try:
        r = requests.get(URL, verify=False, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # 1. Doğrudan verdiğiniz link formatını ara
        pattern1 = r'Araştırma Görevlisi.+?Uzman\s*\((\d+)\)'
        
        # Tüm metinde ara
        page_text = soup.get_text()
        
        # Pattern 1 ile ara
        found_ilan_sayisi = 0
        match1 = re.search(pattern1, page_text)
        if match1:
            found_ilan_sayisi = int(match1.group(1))
            logger.info(f"İlan sayısı bulundu (Pattern 1): {found_ilan_sayisi}")
        
        # Bulunamadıysa, alternatif yöntem
        if found_ilan_sayisi == 0:
            # 2. Tüm linklerde parantez içi sayıları tara
            for link in soup.find_all("a"):
                link_text = link.get_text().strip()
                if "Araştırma Görevlisi" in link_text and "Uzman" in link_text:
                    # Parantez içi sayıyı ara
                    match2 = re.search(r'\((\d+)\)', link_text)
                    if match2:
                        found_ilan_sayisi = int(match2.group(1))
                        logger.info(f"İlan sayısı bulundu (Link içinde): {found_ilan_sayisi}")
                        break
        
        # Hala bulunamadıysa
        if found_ilan_sayisi == 0:
            # 3. Kaba arama - tüm parantez içi sayıları bul
            all_parenthesis_numbers = re.findall(r'\((\d+)\)', page_text)
            if all_parenthesis_numbers:
                logger.info(f"Bulunan tüm parantez içi sayılar: {all_parenthesis_numbers}")
                # İlk bulunan sayıyı kullan
                found_ilan_sayisi = int(all_parenthesis_numbers[0])
                logger.info(f"İlan sayısı bulundu (Parantez içi ilk sayı): {found_ilan_sayisi}")
        
        if found_ilan_sayisi == 0:
            logger.warning("❗ İlan sayısı bulunamadı! Sayfa yapısı değişmiş olabilir.")
            return
        
        # Global değişkeni güncelle
        current_ilan_count = found_ilan_sayisi
        
        # Son ilan sayısını oku
        son_ilan_sayisi = son_ilan_sayisini_oku()
        logger.info(f"Mevcut ilan sayısı: {found_ilan_sayisi}, Son kaydedilen: {son_ilan_sayisi}")
        
        # İlan sayısı değişmişse
        if found_ilan_sayisi != son_ilan_sayisi:
            # Farklılık miktarı
            if found_ilan_sayisi > son_ilan_sayisi:
                # Yeni ilan sayısı
                yeni_ilan_sayisi = found_ilan_sayisi - son_ilan_sayisi
                logger.info(f"✨ {yeni_ilan_sayisi} yeni ilan tespit edildi!")
                
                # Aboneleri al
                subscribers = read_subscribers()
                if not subscribers:
                    logger.warning("⚠️ Hiç abone bulunamadı!")
                    # İlan sayısını yine de güncelle
                    son_ilan_sayisini_kaydet(found_ilan_sayisi)
                    return
                
                # Tüm abonelere bildirim gönder
                mesaj = (
                    f"📢 *Yeni İlanlar Eklendi*\n"
                    f"Toplam {yeni_ilan_sayisi} yeni ilan sisteme eklendi.\n"
                    f"Şu anda toplam {found_ilan_sayisi} ilan var.\n\n"
                    f"İlanları görmek için: {URL}"
                )
                
                # Abonelere gönder
                basarili_gonderim = 0
                for chat_id in subscribers:
                    try:
                        bot.send_message(chat_id, mesaj, parse_mode="Markdown")
                        basarili_gonderim += 1
                        logger.info(f"✅ Bildirim gönderildi: chat_id={chat_id}")
                    except Exception as e:
                        logger.error(f"⚠️ Mesaj gönderme hatası (chat_id={chat_id}): {e}")
                
                logger.info(f"✅ {basarili_gonderim} aboneye bildirim gönderildi.")
                
                # Son bildirim tarihini güncelle
                son_bildirim_tarihini_kaydet()
            else:
                # İlan sayısı azalmış
                azalan_ilan_sayisi = son_ilan_sayisi - found_ilan_sayisi
                logger.warning(f"⚠️ İlan sayısı azalmış: {son_ilan_sayisi} -> {found_ilan_sayisi} ({azalan_ilan_sayisi} ilan azaldı)")
                
                # Abonelere ilan sayısının azaldığını bildirelim
                subscribers = read_subscribers()
                if subscribers:
                    mesaj = (
                        f"ℹ️ *İlan Güncellemesi*\n"
                        f"{azalan_ilan_sayisi} ilan sistemden kaldırılmış.\n"
                        f"Şu anda toplam {found_ilan_sayisi} ilan var.\n\n"
                        f"İlanları görmek için: {URL}"
                    )
                    
                    # Abonelere gönder
                    for chat_id in subscribers:
                        try:
                            bot.send_message(chat_id, mesaj, parse_mode="Markdown")
                            logger.info(f"✅ Bildirim gönderildi: chat_id={chat_id}")
                        except Exception as e:
                            logger.error(f"⚠️ Mesaj gönderme hatası (chat_id={chat_id}): {e}")
                    
                    # Son bildirim tarihini güncelle
                    son_bildirim_tarihini_kaydet()
            
            # Son ilan sayısını güncelle
            son_ilan_sayisini_kaydet(found_ilan_sayisi)
        else:
            logger.info("🔍 İlan sayısında değişiklik yok.")
            
    except Exception as e:
        logger.error(f"⚠️ Ana hata: {e}")

# Zamanlanmış görev
def scheduled_job():
    logger.info("Zamanlanmış görev başlatıldı")
    counter = 0
    while True:
        try:
            counter += 1
            ilanlari_kontrol_et()
            
            # Her 24 saatte bir bilgi mesajı (24 * 1 saat = 24 saat)
            if counter % 24 == 0:
                logger.info(f"ℹ️ Bot çalışmaya devam ediyor, son {counter} kontrol sorunsuz.")
        except Exception as e:
            logger.error(f"⚠️ Zamanlanmış iş hatası: {e}")
        
        # 1 saat bekle (3600 saniye)
        logger.info("1 saat bekleniyor...")
        time.sleep(3600)

# Ana fonksiyon
def main():
    global bot
    
    # Webhook temizle ve bot başlat
    logger.info("Bot başlatılıyor...")
    bot = setup_bot()
    
    # Gerekli dosyaları kontrol et
    if not os.path.exists(ILAN_SAYISI_DOSYA):
        with open(ILAN_SAYISI_DOSYA, "w", encoding="utf-8") as f:
            f.write("0")
        logger.info(f"📄 {ILAN_SAYISI_DOSYA} dosyası oluşturuldu.")
    
    if not os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            pass
        logger.info(f"📄 {SUBSCRIBERS_FILE} dosyası oluşturuldu.")
    
    # Komut işleyicilerini ayarla
    setup_handlers(bot)
    
    # İlk kontrol
    ilanlari_kontrol_et()
    
    # Zamanlanmış görevi ayrı bir thread'de başlat
    worker_thread = threading.Thread(target=scheduled_job, daemon=True)
    worker_thread.start()
    logger.info("✅ İlan kontrol thread'i başlatıldı")
    
    # Polling başlat (bu thread'i bloke eder)
    logger.info("✅ Bot polling başlatılıyor...")
    try:
        # apihelper.API_URL değerini değiştirerek API çakışmalarının önüne geçebiliriz
        bot.infinity_polling(timeout=20, long_polling_timeout=10, allowed_updates=["message"])
    except Exception as e:
        logger.error(f"❌ Polling hatası: {e}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"❌❌❌ Kritik hata: {e}")
