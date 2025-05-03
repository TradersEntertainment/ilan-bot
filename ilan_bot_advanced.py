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
GECMIS_DOSYA = "gonderilen_ilanlar.txt"
SUBSCRIBERS_FILE = "users.txt"

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

    # Diğer mesajlar
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

def ilanlari_kontrol_et():
    if not bot:
        logger.error("Bot henüz başlatılmadı, ilanlar kontrol edilemiyor")
        return

    logger.info("🔍 İlanlar kontrol ediliyor...")
    try:
        r = requests.get(URL, verify=False, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Log the HTML to understand site structure
        logger.info(f"Sayfa içeriği: {soup.title.text if soup.title else 'Title yok'}")
        
        # Try different CSS selectors to find ilanlar
        
        # 1. Angular bazlı yeni yapı
        ilanlar = soup.find_all("div", class_=lambda x: x and "col-border" in x and "ng-star-inserted" in x)
        logger.info(f"Angular div ile bulunan ilan sayısı: {len(ilanlar)}")
        
        # 2. Eski yapı - card-list-item
        if not ilanlar:
            ilanlar = soup.find_all("a", class_="card-list-item")
            logger.info(f"card-list-item ile bulunan ilan sayısı: {len(ilanlar)}")
        
        # 3. Farklı class ile arama
        if not ilanlar:
            ilanlar = soup.find_all("a", class_="announcement-list-item")
            logger.info(f"announcement-list-item ile bulunan ilan sayısı: {len(ilanlar)}")
        
        # 4. İçeriğinde "/ilan/" olan bağlantılar
        if not ilanlar:
            ilanlar = soup.find_all("a", href=lambda href: href and "/ilan/" in href)
            logger.info(f"Href içinde /ilan/ olan bağlantılar: {len(ilanlar)}")
        
        # 5. İçeriğinde "Üniversite" veya "öğretim" kelimesi geçen bağlantılar
        if not ilanlar:
            ilanlar = []
            for div in soup.find_all("div"):
                text = div.get_text(strip=True).lower()
                if "üniversite" in text or "öğretim" in text:
                    ilanlar.append(div)
            logger.info(f"Üniversite/öğretim geçen div'ler: {len(ilanlar)}")
            
        logger.info(f"📦 Toplam bulunan ilan sayısı: {len(ilanlar)}")
        
        # Bulunan ilk 3 ilanı logla
        for i, ilan in enumerate(ilanlar[:3]):
            logger.info(f"İlan {i+1} içeriği: {ilan.get_text(strip=True)[:100]}")

        onceki_linkler = okunan_linkler()
        yeni_linkler = []

        # Aboneleri oku
        subscribers = read_subscribers()
        if not subscribers:
            logger.warning("⚠️ Hiç abone bulunamadı!")
            return
            
        # İlanları işle
        for ilan in ilanlar:
            try:
                # İlan başlığını bul
                baslik = ilan.get_text(strip=True)
                
                # Angular yapısında bağlantıyı bul
                # Parent veya yakın elemanlardan link bulmaya çalış
                link = None
                
                # Eğer ilan bir bağlantı ise
                if ilan.name == 'a' and ilan.get('href'):
                    href = ilan.get('href')
                    # Link düzelt
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            link = "https://www.ilan.gov.tr" + href
                        else:
                            link = "https://www.ilan.gov.tr/" + href
                    else:
                        link = href
                else:
                    # Parent veya child'lardan link bulmaya çalış
                    # Parent'larda ara
                    parent = ilan.parent
                    for i in range(3):  # 3 seviye yukarı bak
                        if parent and parent.name == 'a' and parent.get('href'):
                            href = parent.get('href')
                            if not href.startswith('http'):
                                if href.startswith('/'):
                                    link = "https://www.ilan.gov.tr" + href
                                else:
                                    link = "https://www.ilan.gov.tr/" + href
                            else:
                                link = href
                            break
                        if parent:
                            parent = parent.parent
                    
                    # Child'larda ara
                    if not link:
                        a_tags = ilan.find_all('a')
                        if a_tags and a_tags[0].get('href'):
                            href = a_tags[0].get('href')
                            if not href.startswith('http'):
                                if href.startswith('/'):
                                    link = "https://www.ilan.gov.tr" + href
                                else:
                                    link = "https://www.ilan.gov.tr/" + href
                            else:
                                link = href
                
                # Link bulunamadıysa özel bir link oluştur
                if not link:
                    # İlan başlığından URL-safe bir string oluştur
                    import re
                    from urllib.parse import quote
                    safe_title = re.sub(r'[^\w\s-]', '', baslik).strip().lower()
                    safe_title = re.sub(r'[-\s]+', '-', safe_title)
                    link = f"https://www.ilan.gov.tr/ilan/search?q={quote(baslik[:30])}"
                
                # Tarih bilgisi - eğer bulunamazsa geçerli tarihi kullan
                tarih = "İlan tarihi belirtilmemiş"
                
                # Debug log
                logger.info(f"[İlan] {baslik[:50]}... | {tarih} → {link}")

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
                        logger.info(f"✅ İlan {basarili_gonderim} aboneye gönderildi: {baslik[:50]}...")
                else:
                    logger.info(f"⏭️ Zaten gönderilmiş, atlanıyor: {link}")
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

# Zamanlanmış görev
def scheduled_job():
    logger.info("Zamanlanmış görev başlatıldı")
    counter = 0
    while True:
        try:
            counter += 1
            ilanlari_kontrol_et()
            
            # Her 6 saatte bir bilgi mesajı (36 * 10 dakika = 6 saat)
            if counter % 36 == 0:
                logger.info(f"ℹ️ Bot çalışmaya devam ediyor, son {counter} kontrol sorunsuz.")
        except Exception as e:
            logger.error(f"⚠️ Zamanlanmış iş hatası: {e}")
        
        # 10 dakika bekle
        logger.info("10 dakika bekleniyor...")
        time.sleep(600)

# Ana fonksiyon
def main():
    global bot
    
    # Webhook temizle ve bot başlat
    logger.info("Bot başlatılıyor...")
    bot = setup_bot()
    
    # Gerekli dosyaları kontrol et
    if not os.path.exists(GECMIS_DOSYA):
        with open(GECMIS_DOSYA, "w", encoding="utf-8") as f:
            pass
        logger.info(f"📄 {GECMIS_DOSYA} dosyası oluşturuldu.")
    
    if not os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            pass
        logger.info(f"📄 {SUBSCRIBERS_FILE} dosyası oluşturuldu.")
    
    # Komut işleyicilerini ayarla
    setup_handlers(bot)
    
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
