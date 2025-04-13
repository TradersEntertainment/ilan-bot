import requests
from bs4 import BeautifulSoup
import telebot
import time
import os

# Telegram bilgileri
TOKEN = "7797092615:AAETVqEPlYhiQRoS7T_rY1oOfEQz02pDQCg"
CHAT_ID = "515442086"
bot = telebot.TeleBot(TOKEN)

# İlan adresi
URL = "https://www.ilan.gov.tr/ilan/kategori/693/arastirma-gorevlisi-ogretim-gorevlisi-uzman?ats=5&currentPage=0&field=publish_time&order=desc"
GECMIS_DOSYA = "gonderilen_ilanlar.txt"

# Daha önce gönderilen ilanları oku
def okunan_linkler():
    if not os.path.exists(GECMIS_DOSYA):
        return set()
    with open(GECMIS_DOSYA, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

# Yeni ilanları çek
def yeni_ilanlari_bul():
    print(f"🔎 {time.ctime()}: Yeni ilanlar kontrol ediliyor...")
    r = requests.get(URL, verify=False)
    soup = BeautifulSoup(r.text, 'html.parser')
    ilanlar = soup.find_all("div", class_="card-body")

    onceki_linkler = okunan_linkler()
    yeni_linkler = []

    for ilan in ilanlar:
        try:
            baslik = ilan.find("a").text.strip()
            link = "https://www.ilan.gov.tr" + ilan.find("a")["href"]
            if link not in onceki_linkler:
                mesaj = f"📢 Yeni İlan:\n{baslik}\n{link}"
                bot.send_message(CHAT_ID, mesaj)
                yeni_linkler.append(link)
        except:
            continue

    if yeni_linkler:
        with open(GECMIS_DOSYA, "a", encoding="utf-8") as f:
            for link in yeni_linkler:
                f.write(link + "\n")

# Başlangıç mesajı
bot.send_message(CHAT_ID, "🔔 ilan.gov.tr takip botu başlatıldı!")

# Döngü
while True:
    yeni_ilanlari_bul()
    time.sleep(300)
