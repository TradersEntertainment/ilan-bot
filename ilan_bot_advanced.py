import requests
from bs4 import BeautifulSoup
import telebot
import time
import os
import threading

# Telegram bilgileri
TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

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
        return set()
    with open(GECMIS_DOSYA, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

def yeni_ilanlari_bul():
    print("🔍 İlanlar kontrol ediliyor...")
    try:
        r = requests.get(URL, verify=False, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')

        # İlanları bul
        ilanlar = soup.find_all("a", class_="card-list-item")
        print(f"📦 Bulunan ilan sayısı: {len(ilanlar)}")

        onceki_linkler = okunan_linkler()
        yeni_linkler = []

        # Aboneleri oku
        subscribers = read_subscribers()
        if not subscribers:
            print("⚠️ Hiç abone bulunamadı!")

        for ilan in ilanlar:
            try:
                href = ilan["href"]
                link = "https://www.ilan.gov.tr" + href
                baslik = ilan.find("h3", class_="card-header").get_text(strip=True)
                tarih = ilan.find("div", class_="card-footer").get_text(strip=True)

                # Debug log
                print(f"[DEBUG] {baslik} | {tarih} → {link}")

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
                            print(f"✅ İlan gönderildi: chat_id={chat_id}")
                        except Exception as e:
                            print(f"⚠️ Mesaj gönderme hatası (chat_id={chat_id}): {e}")
                    
                    yeni_linkler.append(link)
                else:
                    print(f"⏭️ Zaten gönderilmiş, atlanıyor: {link}")
            except Exception as e:
                print(f"⚠️ İlan işleme hatası: {e}")
                continue

        # Sonuçları kaydet
        if yeni_linkler:
            with open(GECMIS_DOSYA, "a", encoding="utf-8") as f:
                for l in yeni_linkler:
                    f.write(l + "\n")
            print(f"✅ {len(yeni_linkler)} yeni ilan kaydedildi.")
        else:
            print("🔍 Yeni ilan bulunamadı.")
    except Exception as e:
        print(f"⚠️ Ana hata: {e}")

# Arka planda ilan kontrol döngüsü
def scrap_loop():
    while True:
        try:
            yeni_ilanlari_bul()
        except Exception as e:
            print(f"⚠️ Scraper döngü hatası: {e}")
        
        time.sleep(600)  # 10 dakika (saniye olarak)

if __name__ == "__main__":
    # İlk çalıştırmada dosyaların varlığını kontrol et
    if not os.path.exists(GECMIS_DOSYA):
        with open(GECMIS_DOSYA, "w", encoding="utf-8") as f:
            pass
        print(f"📄 {GECMIS_DOSYA} dosyası oluşturuldu.")
    
    if not os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            pass
        print(f"📄 {SUBSCRIBERS_FILE} dosyası oluşturuldu.")
    
    # Scraper thread başlat
    threading.Thread(target=scrap_loop, daemon=True).start()
    print("📣 Bot başlatıldı, abonelik bekleniyor...")
    
    try:
        bot.polling(non_stop=True)
    except Exception as e:
        print(f"⚠️ Bot çalışma hatası: {e}")
