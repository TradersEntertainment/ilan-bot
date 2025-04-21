import requests
from bs4 import BeautifulSoup
import telebot
import time
import os

# Telegram bilgileri
TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = 515442086  # Sadece senin chat ID'n
bot = telebot.TeleBot(TOKEN)

# URL ve geçmiş dosyası
URL = "https://www.ilan.gov.tr/ilan/kategori/693/arastirma-gorevlisi-ogretim-gorevlisi-uzman"
GECMIS_DOSYA = "gonderilen_ilanlar.txt"

# Önceden gönderilen ilanları oku
def okunan_linkler():
    if not os.path.exists(GECMIS_DOSYA):
        return set()
    with open(GECMIS_DOSYA, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

# Yeni ilanları çek ve kontrol et
def yeni_ilanlari_bul():
    try:
        r = requests.get(URL, verify=False, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        ilanlar = soup.find_all("a", class_="card-list-item")
        
        onceki_linkler = okunan_linkler()
        yeni_linkler = []

        for ilan in ilanlar:
            link = "https://www.ilan.gov.tr" + ilan.get("href")
            baslik = ilan.get_text(strip=True)
            if link not in onceki_linkler:
                mesaj = f"📌 Yeni ilan:\n{baslik}\n{link}"
                bot.send_message(CHAT_ID, mesaj)
                yeni_linkler.append(link)
        
        if yeni_linkler:
            with open(GECMIS_DOSYA, "a", encoding="utf-8") as f:
                for link in yeni_linkler:
                    f.write(link + "\n")
    except Exception as e:
        bot.send_message(CHAT_ID, f"⚠️ Hata oluştu: {e}")

# Mesaj kontrolü sadece belirli kullanıcı için
@bot.message_handler(func=lambda message: message.chat.id == CHAT_ID)
def handle_message(message):
    bot.send_message(CHAT_ID, "🔔 ilan.gov.tr takip botu çalışıyor!")

# Başlangıç mesajı
def baslat():
    bot.send_message(CHAT_ID, "🔔 ilan.gov.tr takip botu başlatıldı!")

# Döngü başlat
if __name__ == "__main__":
    baslat()
    while True:
        yeni_ilanlari_bul()
        time.sleep(10800)  # 3 saat
