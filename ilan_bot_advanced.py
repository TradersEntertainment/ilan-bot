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
        return set(int(line.strip()) for line in f)

# Yeni abone ekle
def write_subscriber(chat_id):
    with open(SUBSCRIBERS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{chat_id}\n")

# /start komutu: abone kaydı\@
@bot.message_handler(commands=['start'])
def subscribe(message):
    chat_id = message.chat.id
    subs = read_subscribers()
    if chat_id not in subs:
        write_subscriber(chat_id)
        bot.send_message(chat_id, "✅ Bot aboneliğine kaydoldunuz! Yeni ilanları alacaksınız.")
    else:
        bot.send_message(chat_id, "ℹ️ Zaten abonesiniz, yeni ilanlar geldikçe bilgilendirileceksiniz.")

# Diğer mesajlar için yardımcı komut\@
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
    r = requests.get(URL, verify=False)
    soup = BeautifulSoup(r.text, 'html.parser')

    # En başta kaç tane eleman bulduğumuzu logla:
    ilanlar = soup.find_all("div", class_="card-body")
    print(f"📦 Bulunan card-body sayısı: {len(ilanlar)}")

    onceki_linkler = okunan_linkler()
    yeni_linkler = []

    for ilan in ilanlar:
        try:
            a_tag = ilan.find("a")
            baslik = a_tag.text.strip()
            link = "https://www.ilan.gov.tr" + a_tag["href"]

            # İşte burası: her bulduğumuz linki logluyoruz
            print(f"[DEBUG] Bulunan ilan: “{baslik}” → {link}")

            if link not in onceki_linkler:
                mesaj = f"📢 Yeni ilan:\n{baslik}\n{link}"
                bot.send_message(CHAT_ID, mesaj)
                yeni_linkler.append(link)
        except Exception as e:
            print(f"⚠️ Döngü hatası: {e}")
            continue

    # Sonuçları kaydet
    if yeni_linkler:
        with open(GECMIS_DOSYA, "a", encoding="utf-8") as f:
            for l in yeni_linkler:
                f.write(l + "\n")
    else:
        print("⏭️ Yeni ilan bulunamadı ya da zaten gönderilmiş.")


# Arka planda ilan kontrol döngüsü
def scrap_loop():
    while True:
        yeni_ilanlari_bul()
        time.sleep(600)  # 1 dakika

if __name__ == "__main__":
    # Scraper thread başlat
    threading.Thread(target=scrap_loop, daemon=True).start()
    print("📣 Bot başlatıldı, abonelik bekleniyor...")
    bot.polling(non_stop=True)
