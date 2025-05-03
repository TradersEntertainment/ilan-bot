# URL ve geçmiş dosyası bölümünü güncelleyin:
URL = "https://www.ilan.gov.tr/akademik-personel-alimlari/arastirma-gorevlisi-ogretim-gorevlisi-uzman"
GECMIS_DOSYA = "gonderilen_ilanlar.txt"
SUBSCRIBERS_FILE = "users.txt"

# Tarama fonksiyonunu güncelleyin:
def ilanlari_kontrol_et():
    if not bot:
        logger.error("Bot henüz başlatılmadı, ilanlar kontrol edilemiyor")
        return

    logger.info("🔍 İlanlar kontrol ediliyor...")
    try:
        r = requests.get(URL, verify=False, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Site başlığını kontrol et
        logger.info(f"Sayfa içeriği: {soup.title.text if soup.title else 'Title yok'}")
        
        # Ekran görüntüsünde görülen tabloyu bulmaya çalış
        # 1. Tablo satırlarını ara
        table_rows = soup.find_all("tr")
        if table_rows:
            logger.info(f"Tablo satırı bulundu: {len(table_rows)}")
        
        # 2. Kurum ve başlık içeren div'leri ara
        kurum_divs = soup.find_all("div", string=lambda s: s and "ÜNİVERSİTESİ" in s.upper())
        logger.info(f"Üniversite içeren div sayısı: {len(kurum_divs)}")
        
        # 3. İlan numaraları ara
        ilan_nums = soup.find_all(string=lambda s: s and s.strip().startswith("YOK") and s.strip()[3:].isdigit())
        logger.info(f"İlan numarası olabilecek metin sayısı: {len(ilan_nums)}")
        
        # 4. Tüm linkleri ara
        all_links = soup.find_all("a", href=True)
        ilan_links = [a for a in all_links if "/ilan/" in a.get("href")]
        logger.info(f"İlan içeren link sayısı: {len(ilan_links)}")
        
        # İlan listesini oluştur
        ilanlar = []
        
        # Öncelikle ilan linklerini dene
        if ilan_links:
            for link in ilan_links:
                try:
                    baslik = link.get_text(strip=True)
                    if not baslik:
                        # Link içinde başlık yoksa, parent elementte ara
                        parent = link.parent
                        baslik_elem = parent.find(string=lambda s: s and len(s.strip()) > 10)
                        if baslik_elem:
                            baslik = baslik_elem.strip()
                        else:
                            # Hala bulunamadıysa, yakın kardeş elementlerde ara
                            next_sibling = link.next_sibling
                            if next_sibling and next_sibling.string and len(next_sibling.string.strip()) > 10:
                                baslik = next_sibling.string.strip()
                            else:
                                # Son çare olarak link metnini kullan
                                baslik = "İlan Detayı"
                    
                    href = link.get("href")
                    # URL düzeltmesi
                    if not href.startswith("http"):
                        if href.startswith("/"):
                            full_link = "https://www.ilan.gov.tr" + href
                        else:
                            full_link = "https://www.ilan.gov.tr/" + href
                    else:
                        full_link = href
                        
                    # Debug için görüntüle
                    logger.info(f"İlan bulundu: {baslik[:50]} - {full_link}")
                    
                    ilanlar.append({
                        "baslik": baslik,
                        "link": full_link,
                        "tarih": "İlan tarihi belirtilmemiş"
                    })
                except Exception as e:
                    logger.error(f"Link işleme hatası: {e}")
        
        # Tablo yapısına göre dene
        if not ilanlar and len(table_rows) > 1:  # Header + en az bir satır
            for row in table_rows[1:]:  # Header'ı atla
                try:
                    cells = row.find_all("td")
                    if len(cells) >= 2:  # En az kurum ve başlık
                        kurum = cells[0].get_text(strip=True)
                        baslik = cells[1].get_text(strip=True)
                        ilan_no = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                        
                        # Link bulmaya çalış
                        link_elem = row.find("a", href=True)
                        if link_elem:
                            href = link_elem.get("href")
                            if not href.startswith("http"):
                                if href.startswith("/"):
                                    link = "https://www.ilan.gov.tr" + href
                                else:
                                    link = "https://www.ilan.gov.tr/" + href
                            else:
                                link = href
                        else:
                            # Link yoksa ilanın ID'sine göre URL oluştur
                            link = f"https://www.ilan.gov.tr/ilan/{ilan_no}" if ilan_no else f"https://www.ilan.gov.tr/search?q={baslik[:30]}"
                        
                        logger.info(f"Tablo ilanı: {kurum} - {baslik} - {ilan_no}")
                        
                        ilanlar.append({
                            "baslik": f"{kurum} - {baslik}",
                            "link": link,
                            "tarih": "İlan tarihi belirtilmemiş"
                        })
                except Exception as e:
                    logger.error(f"Tablo satırı işleme hatası: {e}")
        
        # 3. Alternatif: Üniversite içeren div'leri kullan
        if not ilanlar and kurum_divs:
            for div in kurum_divs:
                try:
                    kurum = div.get_text(strip=True)
                    # Parent elementte link ara
                    parent = div.parent
                    link_elem = None
                    if parent:
                        link_elem = parent.find("a", href=True)
                    
                    # Eğer link bulunamazsa, kardeş elementlerde ara 
                    if not link_elem:
                        siblings = list(div.next_siblings)
                        for sibling in siblings:
                            if sibling.name == "a" and sibling.get("href"):
                                link_elem = sibling
                                break
                    
                    # En yakın tr elementinde başlık ara
                    tr_elem = div.find_parent("tr")
                    baslik = kurum
                    if tr_elem:
                        baslik_elem = tr_elem.find_all("td")
                        if len(baslik_elem) > 1:
                            baslik = baslik_elem[1].get_text(strip=True)
                    
                    # Link URL'si
                    if link_elem:
                        href = link_elem.get("href")
                        if not href.startswith("http"):
                            if href.startswith("/"):
                                link = "https://www.ilan.gov.tr" + href
                            else:
                                link = "https://www.ilan.gov.tr/" + href
                        else:
                            link = href
                    else:
                        # Link yoksa arama URL'si oluştur
                        link = f"https://www.ilan.gov.tr/search?q={kurum.replace(' ', '+')}"
                    
                    logger.info(f"Div ilanı: {kurum} - {baslik}")
                    
                    ilanlar.append({
                        "baslik": f"{kurum} - {baslik}",
                        "link": link,
                        "tarih": "İlan tarihi belirtilmemiş"
                    })
                except Exception as e:
                    logger.error(f"Div işleme hatası: {e}")
        
        # Toplam bulduğumuz ilan
        logger.info(f"📦 Toplam bulunan ilan sayısı: {len(ilanlar)}")
        
        # Bulunan ilk 3 ilanı logla
        for i, ilan in enumerate(ilanlar[:3]):
            logger.info(f"İlan {i+1}: {ilan['baslik']} -> {ilan['link']}")

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
                baslik = ilan['baslik']
                link = ilan['link']
                tarih = ilan['tarih']
                
                # Debug log
                logger.info(f"[İlan işleniyor] {baslik[:50]}... | {tarih} → {link}")

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
