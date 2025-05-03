import requests
from bs4 import BeautifulSoup
import telebot
import time
import os
import logging
import flask

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask app (for webhook)
app = flask.Flask(__name__)

# Bot configuration
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    logger.error("BOT_TOKEN not found!")
    exit(1)

bot = telebot.TeleBot(TOKEN)
logger.info("Bot initialized")

# Render.com specific settings
PORT = int(os.environ.get('PORT', 8080))
app_url = os.environ.get('RENDER_EXTERNAL_URL')
if not app_url:
    logger.warning("RENDER_EXTERNAL_URL not found, using default webhook")
    app_url = f"https://{os.environ.get('RENDER_SERVICE_NAME')}.onrender.com"

# URL ve geçmiş dosyası
URL = "https://www.ilan.gov.tr/ilan/kategori/693/arastirma-gorevlisi-ogretim-gorevlisi-uzman"
GECMIS_DOSYA = "gonderilen_ilanlar.txt"
SUBSCRIBERS_FILE = "users.txt"

# Abone listesini oku
def read_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            pass
        return set()
        
    with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
        return set(int(line.strip()) for line in f if line.strip().isdigit())

# Yeni abone ekle
def write_subscriber(chat_id):
    with open(SUBSCRIBERS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{chat_id}\n")

# /start komutu
@bot.message_handler(commands=['start'])
def on_start(message):
    chat_id = message.chat.id
    subs = read_subscribers()
    
    if chat_id not in subs:
        write_subscriber(chat_id)
        bot.send_message(chat_id, "✅ Bot aboneliğine kaydoldunuz! Yeni ilanları alacaksınız.")
        logger.info(f"New subscriber: {chat_id}")
    else:
        bot.send_message(chat_id, "ℹ️ Zaten abonesiniz, yeni ilanlar geldikçe bilgilendirileceksiniz.")
        logger.info(f"Existing subscriber: {chat_id}")

# Diğer mesajlar
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "Lütfen /start yazarak abone olun.")

# Webhook route
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_str = flask.request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return ''

# Webhook kontrol sayfası
@app.route('/')
def index():
    return 'Bot is running'

# Önceki ilanları oku
def okunan_linkler():
    if not os.path.exists(GECMIS_DOSYA):
        with open(GECMIS_DOSYA, "w", encoding="utf-8") as f:
            pass
        return set()
        
    with open(GECMIS_DOSYA, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

# İlanları kontrol et
def check_jobs():
    logger.info("Checking for new jobs...")
    try:
        r = requests.get(URL, verify=False, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')

        # İlanları bul
        ilanlar = soup.find_all("a", class_="card-list-item")
        logger.info(f"Found {len(ilanlar)} jobs")

        onceki_linkler = okunan_linkler()
        yeni_linkler = []
        
        # Aboneleri oku
        subscribers = read_subscribers()
        if not subscribers:
            logger.warning("No subscribers found!")
            return

        for ilan in ilanlar:
            try:
                href = ilan["href"]
                link = "https://www.ilan.gov.tr" + href
                baslik = ilan.find("h3", class_="card-header").get_text(strip=True)
                tarih = ilan.find("div", class_="card-footer").get_text(strip=True)

                if link not in onceki_linkler:
                    mesaj = (
                        f"📢 *Yeni İlan*\n"
                        f"*{baslik}*\n"
                        f"_{tarih}_\n"
                        f"{link}"
                    )
                    
                    # Send to all subscribers
                    for chat_id in subscribers:
                        try:
                            bot.send_message(chat_id, mesaj, parse_mode="Markdown")
                            logger.info(f"Sent notification to {chat_id}")
                        except Exception as e:
                            logger.error(f"Failed to send message to {chat_id}: {e}")
                    
                    yeni_linkler.append(link)
                    logger.info(f"New job: {baslik}")
                else:
                    logger.debug(f"Already seen: {baslik}")
            except Exception as e:
                logger.error(f"Error processing job: {e}")

        # Save new links
        if yeni_linkler:
            with open(GECMIS_DOSYA, "a", encoding="utf-8") as f:
                for l in yeni_linkler:
                    f.write(l + "\n")
            logger.info(f"Saved {len(yeni_linkler)} new jobs")
        else:
            logger.info("No new jobs found")
    except Exception as e:
        logger.error(f"Error checking jobs: {e}")

# Scheduled task to check jobs
def scheduled_task():
    while True:
        try:
            check_jobs()
        except Exception as e:
            logger.error(f"Scheduled task error: {e}")
        
        logger.info("Sleeping for 10 minutes...")
        time.sleep(600)  # 10 dakika

if __name__ == "__main__":
    # Remove existing webhook
    bot.remove_webhook()
    time.sleep(1)
    
    # Set webhook
    webhook_url = f"{app_url}/{TOKEN}"
    bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook set: {webhook_url}")
    
    # Start the job checking thread in a separate thread
    import threading
    threading.Thread(target=scheduled_task, daemon=True).start()
    
    # Start Flask server
    logger.info(f"Starting Flask server on port {PORT}")
    app.run(host='0.0.0.0', port=PORT)
