
import requests
from bs4 import BeautifulSoup
import telebot
import time
import os

TOKEN = "7797092615:AAFBNobmedc04sE9OBUI-UeB9vxMJJfGjPE"
CHAT_ID = "515442086"
bot = telebot.TeleBot(TOKEN)

URL = "https://quotes.toscrape.com"
GECMIS_DOSYA = "gonderilen_ilanlar.txt"

def okunan_linkler():
    if not os.path.exists(GECMIS_DOSYA):
        return set()
    with open(GECMIS_DOSYA, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

def yeni_ilanlari_bul():
    print("🔄 İlanlar çekiliyor...")
    r = requests.get(URL, verify=False)
    soup = BeautifulSoup(r.text, 'html.parser')
    ilanlar = soup.find_all("div", class_="card-body")

    onceki_linkler = okunan_linkler()
    yeni_linkler = []

    for ilan in ilanlar:
        try:
            a_tag = ilan.find("a")
            baslik = a_tag.text.strip()
            link = "https://www.ilan.gov.tr" + a_tag["href"]

            if link not in onceki_linkler:
                mesaj = f"📢 Yeni ilan: {baslik}\n🔗 {link}"
                bot.send_message(CHAT_ID, mesaj)
                yeni_linkler.append(link)
        except Exception as e:
            print(f"Hata: {e}")
            continue

    if yeni_linkler:
        with open(GECMIS_DOSYA, "a", encoding="utf-8") as f:
            for link in yeni_linkler:
                f.write(link + "\n")

print("📣 Takip başlatıldı.")
while True:
    yeni_ilanlari_bul()
    time.sleep(60)  # 3 saat = 10800 saniye
