import requests
from bs4 import BeautifulSoup
import telebot
import os
import time

# Telegram bilgileri
TOKEN = "8098227772:AAFVn8Zno7oIt38KLwfFdlCQbAakTL6OpqY"
CHAT_ID = "515442086"
bot = telebot.TeleBot(TOKEN)

# Hedef URL
URL = "https://www.ilan.gov.tr/ilan/kategori/693/arastirma-gorevlisi-ogretim-gorevlisi-uzman"
GECMIS_DOSYA = "gonderilen_ilanlar.txt"

# Önceden gönderilen ilanları oku
def okunan_linkler():
    if not os.path.exists(GECMIS_DOSYA):
        return set()
    with open(GECMIS_DOSYA, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

# Yeni ilanları bul
def yeni_ilanlari_bul():
    print("🔍 İlanlar çekiliyor...")

    r = requests.get(URL, verify=False)
    soup = BeautifulSoup(r.text, 'html.parser')
    ilanlar = soup.find_all("div", class_="card-body")
    
    print(f"📦 Toplam ilan sayısı: {len(ilanlar)}")

    onceki_linkler = okunan_linkler()
    yeni_linkler = []

    for ilan in ilanlar:
        try:
            baslik = ilan.find("a").text.strip()
            link = "https://www.ilan.gov.tr" + ilan.find("a")["href"]
            print(f"🎯 Denetlenen ilan: {baslik}")
            if link not in onceki_linkler:
                mesaj = f"📢 {baslik}\n🔗 {link}"
                bot.send_message(CHAT_ID, mesaj)
                yeni_linkler.append(link)
        except Exception as e:
            print(f"Hata oluştu: {e}")
            continue

    if yeni_linkler:
        with open(GECMIS_DOSYA, "a", encoding="utf-8") as f:
            for link in yeni_linkler:
                f.write(link + "\n")

bot.send_message(CHAT_ID, "🔔 Takip botu başlatıldı!")
while True:
    yeni_ilanlari_bul()
    time.sleep(10800)
