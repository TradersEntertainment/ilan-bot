import requests
from bs4 import BeautifulSoup
import telebot
import time
import os

TOKEN = "7797092615:AAETVqEPlYhiQRoS7T_rY1oOfEQz02pDQCg"
bot = telebot.TeleBot(TOKEN)

URL = "https://www.ilan.gov.tr/ilan/kategori/693/arastirma-gorevlisi-ogretim-gorevlisi-uzman?ats=5&currentPage=0&field=publish_time&order=desc"
GECMIS_DOSYA = "gonderilen_ilanlar.txt"
KULLANICI_DOSYA = "users.txt"

def kullanicilari_oku():
    if not os.path.exists(KULLANICI_DOSYA):
        return set()
    with open(KULLANICI_DOSYA, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

@bot.message_handler(func=lambda message: True)
def kullanici_ekle(message):
    user_id = str(message.chat.id)
    mevcutlar = kullanicilari_oku()
    if user_id not in mevcutlar:
        with open(KULLANICI_DOSYA, "a", encoding="utf-8") as f:
            f.write(user_id + "\n")
        bot.send_message(user_id, "✅ Bot'a başarıyla abone oldun! Yeni ilanları sana göndereceğim.")
    else:
        bot.send_message(user_id, "🔄 Zaten kayıtlısın. Yeni ilanlar geldikçe sana yollayacağım.")

def okunan_linkler():
    if not os.path.exists(GECMIS_DOSYA):
        return set()
    with open(GECMIS_DOSYA, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

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
                for uid in kullanicilari_oku():
                    bot.send_message(uid, mesaj)
                yeni_linkler.append(link)
        except:
            continue

    if yeni_linkler:
        with open(GECMIS_DOSYA, "a", encoding="utf-8") as f:
            for link in yeni_linkler:
                f.write(link + "\n")

for uid in kullanicilari_oku():
    bot.send_message(uid, "🔔 ilan.gov.tr takip botu başlatıldı!")

def donguyu_baslat():
    while True:
        yeni_ilanlari_bul()
        time.sleep(300)

import threading
threading.Thread(target=donguyu_baslat).start()
bot.polling()
