import requests
from bs4 import BeautifulSoup
import telebot
import time
import os
import threading
import logging
import flask

# Logging ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask uygulaması (webhook için)
app = flask.Flask(__name__)

# Telegram bilgileri
TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Render.com spesifik ayarlar
PORT = int(os.environ.get('PORT', 5000))
WEBHOOK_URL = os.environ.get('RENDER_EXTERNAL_URL')
if WEBHOOK_URL:
    logger.info(f"Webhook URL: {WEBHOOK_URL}")
else:
    logger.warning("RENDER_EXTERNAL_URL bulunamadı, webhook kullanılmayacak")

# URL ve geçmiş dosyası
URL = "https://www.ilan.gov.tr/ilan/kategori/693/arastirma-gorevlisi-ogretim-gorevlisi-uzman"
GECMIS_DOSYA = "gonderilen_ilanlar.txt"
SUBSCRIBERS_FILE = "users.txt"

# Abone listesini oku
def read_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        return set()
    with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
        return set(int(line.strip()) for line in f if line.strip().isdigit())

# Yeni abone ekle
def write_subscriber(chat_id):
    with open(SUBSCRIBERS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{chat_id}\n")

# /start komutu: abone kaydı
@bot.message_handler(commands=['start'])
def subscribe(message):
    chat_id = message.chat.id
    subs = read_subscribers()
    if chat_id not in subs:
        write_subscriber(chat_id)
        bot.send_message(chat_id, "✅ Bot aboneliğine kaydoldunuz! Yeni ilanları alacaksınız.")
    else:
        bot.send_message(chat_id, "ℹ️ Zaten abonesiniz, yeni ilanlar geldikçe bilgilendirileceksiniz.")

# Diğer mesajlar için yardımcı komut
@bot.message_handler(func=lambda message: True)
def default_reply(message):
    bot.send_message(message.chat.id, "Lütfen /start yazarak abone olun.")

# Önceki ilanları oku
def okunan_linkler():
    if not os.path.exists(GECMIS_DOSYA):
        with open(GECMIS_DOSYA, "w", encoding="utf-8") as f:
            pass
        return set()
    with open(GECMIS_DOSYA, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

def yeni_ilanlari_bul():
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
                    for chat_id in subscribers:
                        try:
                            bot.send_message(chat_id, mesaj, parse_mode="Markdown")
                            logger.info(f"✅ İlan gönderildi: chat_id={chat_id}")
                        except Exception as e:
                            logger.error(f"⚠️ Mesaj gönderme hatası (chat_id={chat_id}): {e}")
                    
                    yeni_linkler.append(link)
                else:
                    logger.debug(f"⏭️ Zaten gönderilmiş, atlanıyor: {link}")
            except Exception as e:
                logger.error(f"⚠️ İlan işleme hatası: {e}")
                continue

        # Sonuçları kaydet
        if yeni_linkler:
            with open(GECMIS_DOSYA, "a", encoding="utf-8") as f:
                for l in yeni_linkler:
                    f.write(l + "\n")
            logger.info(f"✅ {len(yeni_linkler)} yeni ilan kaydedildi.")
        else:
            logger.info("🔍 Yeni ilan bulunamadı.")
    except Exception as e:
        logger.error(f"⚠️ Ana hata: {e}")

# Flask webhook route
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = flask.request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    if WEBHOOK_URL:
        bot.set_webhook(url=WEBHOOK_URL + '/' + TOKEN)
        return f"Webhook ayarlandı: {WEBHOOK_URL}", 200
    return "Webhook URL bulunamadı", 400

# Düzenli kontrol işlevi
def scheduled_job():
    while True:
        try:
            yeni_ilanlari_bul()
        except Exception as e:
            logger.error(f"⚠️ Zamanlanmış iş hatası: {e}")
        time.sleep(600)  # 10 dakika

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
    
    # Render.com'da webhook kullan, yoksa normal polling
    if WEBHOOK_URL:
        # Scraper thread başlat
        threading.Thread(target=scheduled_job, daemon=True).start()
        logger.info("📣 Webhook modu ile bot başlatıldı")
        # Flask uygulamasını çalıştır
        app.run(host="0.0.0.0", port=PORT)
    else:
        # Webhook temizle ve polling moduna geç
        bot.remove_webhook()
        # Scraper thread başlat
        threading.Thread(target=scheduled_job, daemon=True).start()
        logger.info("📣 Polling modu ile bot başlatıldı")
        # Long polling başlat
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
