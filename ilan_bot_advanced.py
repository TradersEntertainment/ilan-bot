import requests
from bs4 import BeautifulSoup
import telebot
import time
import os
import threading
import logging
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# SSL uyarılarını kapat
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Logging ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Telegram bilgileri
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    logger.error("BOT_TOKEN bulunamadı! Lütfen çevre değişkenlerini kontrol edin.")
    exit(1)

# URL ve geçmiş dosyası
URL = "https://www.ilan.gov.tr/ilan/kategori/693/arastirma-gorevlisi-ogretim-gorevlisi-uzman"
GECMIS_DOSYA = "gonderilen_ilanlar.txt"
SUBSCRIBERS_FILE = "users.txt"

# İlk başlatma sırasında herhangi bir önceki webhook'u temizle
bot = None

def setup_bot():
    global bot
    try:
        bot = telebot.TeleBot(TOKEN)
        # Herhangi bir webhook yapılandırmasını temizle
        bot.remove_webhook()
        time.sleep(1)  # API'nin temizlemeyi işlemesi için bekle
        logger.info("Bot başlatıldı ve webhook temizlendi")
        return bot
    except Exception as e:
        logger.error(f"Bot kurulum hatası: {e}")
        raise

# Abone listesini oku
def read_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
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
    except Exception as e:
        logger.error(f"Abone ekleme hatası: {e}")

# /start komutu: abone kaydı
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

    # Diğer mesajlar için yardımcı komut
    @bot.message_handler(func=lambda message: True)
    def default_reply(message):
        try:
            bot.send_message(message.chat.id, "Lütfen /start yazarak abone olun.")
        except Exception as e:
            logger.error(f"Default handler hatası: {e}")

# Önceki ilanları oku
def okunan_linkler():
    if not os.path.exists(GECMIS_DOSYA):
        with open(GECMIS_DOSYA, "w", encoding="utf-8") as f:
            pass
        return set()
    
    try:
        with open(GECMIS_DOSYA, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    except Exception as e:
        logger.error(f"Okunan linkler hatası: {e}")
        return set()

def yeni_ilanlari_bul():
    if not bot:
        logger.error("Bot henüz başlatılmadı, ilanlar kontrol edilemiyor")
        return

    logger.info("🔍 İlanlar kontrol ediliyor...")
    try:
        r = requests.get(URL, verify=False, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')

        # İlanları bul
        ilanlar = soup.find_all("a", class_="card-list-item")
        logger.info(f"📦 Bulunan ilan sayısı: {len(ilanlar)}")

        onceki_linkler = okunan_linkler()
        yeni_linkler = []

        # Aboneleri oku
        subscribers = read_subscribers()
        if not subscribers:
            logger.warning("⚠️ Hiç abone bulunamadı!")
            return

        for ilan in ilanlar:
            try:
                href = ilan["href"]
                link = "https://www.ilan.gov.tr" + href
                baslik = ilan.find("h3", class_="card-header").get_text(strip=True)
                tarih = ilan.find("div", class_="card-footer").get_text(strip=True)

                # Debug log
                logger.debug(f"[DEBUG] {baslik} | {tarih} → {link}")

                if link not in onceki_linkler:
                    mesaj = (
                        f"📢 *Yeni İlan*\n"
                        f"*{baslik}*\n"
                        f"_{tarih}_\n"
                        f"{link}"
                    )
                    
                    # Tüm abonelere gönder
                    basarili_gonderim = 0
                    for chat_id in subscribers:
                        try:
                            bot.send_message(chat_id, mesaj, parse_mode="Markdown")
                            basarili_gonderim += 1
                            logger.info(f"✅ İlan gönderildi: chat_id={chat_id}")
                        except Exception as e:
                            logger.error(f"⚠️ Mesaj gönderme hatası (chat_id={chat_id}): {e}")
                    
                    if basarili_gonderim > 0:
                        yeni_linkler.append(link)
                        logger.info(f"✅ İlan {basarili_gonderim} aboneye gönderildi: {baslik}")
                else:
                    logger.debug(f"⏭️ Zaten gönderilmiş, atlanıyor: {link}")
            except Exception as e:
                logger.error(f"⚠️ İlan işleme hatası: {e}")
                continue

        # Sonuçları kaydet
        if yeni_linkler:
            try:
                with open(GECMIS_DOSYA, "a", encoding="utf-8") as f:
                    for l in yeni_linkler:
                        f.write(l + "\n")
                logger.info(f"✅ {len(yeni_linkler)} yeni ilan kaydedildi.")
            except Exception as e:
                logger.error(f"⚠️ İlan kaydetme hatası: {e}")
        else:
            logger.info("🔍 Yeni ilan bulunamadı.")
    except Exception as e:
        logger.error(f"⚠️ Ana hata: {e}")

# Arka planda ilan kontrol döngüsü
def scheduled_job():
    counter = 0
    while True:
        try:
            counter += 1
            yeni_ilanlari_bul()
            
            # Her 6 saat'te bir mesaj yaz (36 kez 10 dakika = 6 saat)
            if counter % 36 == 0:
                logger.info(f"ℹ️ Bot hala çalışıyor, son {counter} kontrolde sorunsuz.")
        except Exception as e:
            logger.error(f"⚠️ Zamanlanmış iş hatası: {e}")
        
        # Her döngü sonrası 10 dakika bekle
        time.sleep(600)

def start_bot_with_retry():
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            global bot
            bot = setup_bot()
            setup_handlers(bot)
            
            # Scraper thread başlat
            threading.Thread(target=scheduled_job, daemon=True).start()
            logger.info("📣 Bot başlatıldı, polling başlıyor...")
            
            # Long polling başlat (hata toleranslı)
            bot.infinity_polling(timeout=30, long_polling_timeout=15, allowed_updates=["message"])
            
            # Eğer infinity_polling'den normal şekilde çıkarsa, başarılı
            logger.info("Bot normale döndü, çıkılıyor.")
            break
        
        except Exception as e:
            retry_count += 1
            logger.error(f"⚠️ Bot başlatma hatası (deneme {retry_count}/{max_retries}): {e}")
            
            if retry_count >= max_retries:
                logger.critical("⛔ Maksimum yeniden deneme sayısına ulaşıldı, çıkılıyor.")
                break
                
            # Her başarısız denemeden sonra 30 saniye bekle
            time.sleep(30)

if __name__ == "__main__":
    # İlk çalıştırmada dosyaların varlığını kontrol et
    if not os.path.exists(GECMIS_DOSYA):
        with open(GECMIS_DOSYA, "w", encoding="utf-8") as f:
            pass
        logger.info(f"📄 {GECMIS_DOSYA} dosyası oluşturuldu.")
    
    if not os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            pass
        logger.info(f"📄 {SUBSCRIBERS_FILE} dosyası oluşturuldu.")
    
    # Botun webhook'larını temizle
    bot = telebot.TeleBot(TOKEN)
    try:
        bot.remove_webhook()
        logger.info("Önceki webhook temizlendi")
    except Exception as e:
        logger.warning(f"Webhook temizlenirken hata: {e}")
    
    # Biraz bekle
    time.sleep(3)
    
    # Bot başlatma, yeniden deneme mekanizması ile
    start_bot_with_retry()
