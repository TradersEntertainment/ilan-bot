import requests
from bs4 import BeautifulSoup
import telebot
import time
import os

# Telegram bilgileri
TOKEN = "7797092615:AAFBNobmedc04sE9OBUI-UeB9vxMJJfGjPE"
CHAT_ID = "515442086"
bot = telebot.TeleBot(TOKEN)

# İlan adresi
URL = "https://quotes.toscrape.com"
GECMIS_DOSYA = "gonderilen_ilanlar.txt"

# Daha önce gönderilen ilanları oku
def okunan_linkler():
    if not os.path.exists(GECMIS_DOSYA):
        return set()
    with open(GECMIS_DOSYA, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

# Yeni ilanları çek
def yeni_ilanlari_bul():
    print("🌐 Siteye istek atılıyor...")
    try:
        r = requests.get(URL, verify=False)
        soup = BeautifulSoup(r.text, 'html.parser')
        alintilar = soup.find_all("div", class_="quote")

        onceki_linkler = okunan_linkler()
        yeni_linkler = []

        for alinti in alintilar:
            try:
                metin = alinti.find("span", class_="text").text.strip()
                print(f"🎯 Alıntı bulundu: {metin}")
                if metin not in onceki_linkler:
                    mesaj = f"💬 Yeni alıntı:\n{metin}"
                    bot.send_message(CHAT_ID, mesaj)
                    print("✅ Yeni alıntı gönderildi!")
                    yeni_linkler.append(metin)
                else:
                    print("⏭️ Zaten gönderilmiş, atlanıyor.")
            except Exception as e:
                print(f"⚠️ Alıntı hatası: {e}")
                continue

        if yeni_linkler:
            with open(GECMIS_DOSYA, "a", encoding="utf-8") as f:
                for link in yeni_linkler:
                    f.write(link + "\n")
        else:
            print("🔍 Yeni alıntı bulunamadı.")
    except Exception as e:
        print(f"🚫 Siteye erişimde hata: {e}")

# Sürekli kontrol et (her 1 dakikada bir)
while True:
    print("\n🕒 Kontrol başlıyor...")
    yeni_ilanlari_bul()
    print("⏸️ Bekleniyor...")
    time.sleep(60)  # 1 dakika
