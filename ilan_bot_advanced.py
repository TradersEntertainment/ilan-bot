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

# Yeni ilanları kontrol et
def yeni_ilanlari_bul():
    print("🔍 İlanlar kontrol ediliyor...")
    try:
        r = requests.get(URL, verify=False, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        alintilar = soup.find_all("div", class_="quote")

        onceki = okunan_linkler()
        yeniler = []
        subs = read_subscribers()

        for alinti in alintilar:
            metin = alinti.find("span", class_="text").text.strip()
            if metin not in onceki:
                yeniler.append(metin)
                for uid in subs:
                    bot.send_message(uid, f"💬 Yeni alıntı:\n{metin}")
                print(f"✅ Yeni alıntı gönderildi: {metin}")
            else:
                print("⏭️ Zaten gönderilmiş: atlanıyor.")

        if yeniler:
            with open(GECMIS_DOSYA, "a", encoding="utf-8") as f:
                for m in yeniler:
                    f.write(m + "\n")
        else:
            print("🔍 Yeni alıntı bulunamadı.")
    except Exception as e:
        print(f"🚫 Hata: {e}")

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
