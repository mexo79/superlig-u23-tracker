# Süper Lig U23 Tracker • 2026–27

**[Güncel Google Sheets](https://docs.google.com/spreadsheets/d/1eyhOf-1Vv3LmYCRmodFMBsxAflYIRH7l3iUThRHdVuM/edit)**

## Neler dahil?

- **Kulüp resmî maçları:** Süper Lig, Türkiye Kupası, UEFA Şampiyonlar Ligi, Avrupa Ligi ve Konferans Ligi; eleme maçları dahil (veri sunulduğu ölçüde).
- **Millî takım resmî maçları:** UEFA Uluslar Ligi, Dünya Kupası, Afrika Uluslar Kupası elemeleri, UEFA U21/U19/U17 elemeleri ve API'de doğrulanan turnuvalar.
- **Hariç:** Hazırlık maçları, dostluk maçları, sezon öncesi ve gösteri karşılaşmaları.
- **Dönem:** 1 Temmuz 2026'ten başlayan 2026–27 izleme dönemi. Lig/kupaların 2026/27 sezonuna, millî maçların karşılaşma tarihine göre eşleştirilmesi.
- **TFF genç yabancı kontenjanı:** Bağımsız; yalnızca TFF'nin resmî statüsüyle değerlendirilir ve her yıl Temmuz'da kontrol edilir.

## Google Sheets sekmeleri

- **Tüm U23, U23 Yabancı, U23 Türk:** oyuncu, kulüp, mevki, *erişilebilir tüm resmî maçların toplam dakika, maç, ilk 11, ortalama reyting, gol, asist, kartları* ve en sağda Yerli/Yabancı
- **Süper Lig (Ayrı):** 29 Ekim 2026'daki yalnız Süper Lig ilk aktarımı; eski sayılar korunmuştur
- **Turnuva Bazında:** oyuncu × turnuva × millî/kulüp kırılımı
- **Veri Kapsamı:** turnuva başına tamamlanan maç ve API'nin oyuncu verisi bulunan/eksik maç sayısı
- **TFF Kontenjan, İşlem Günlüğü:** mevcut sekmeler korunur
- **API Canlı Bağlantı:** GitHub'daki günlük CSV'yi içe alma formülü; erişim izni gerektirir.

## Son doğrulanmış ilk aktarım (29 Ekim 2026)

- Süper Lig: **77/81** tamamlanan maçta oyuncu istatistiği
- Şampiyonlar Ligi **12/12**, Avrupa Ligi **3/11**, Konferans Ligi **4/4**
- UEFA Uluslar Ligi **103/104**, Dünya Kupası **26/26** (1 Temmuz'dan sonra), Afrika Uluslar Kupası Elemeleri **44/48**
- Türkiye Kupası **0/4**, UEFA U21 eleme **0/68**, UEFA U17 eleme **0/19** → bunlar *oynanmadı* değil, GOAL API'nin oyuncu istatistiklerini getiremediği maçlardır.
- **27 takip edilen oyuncu**, Süper Lig dışında erişilebilir resmî oyuncu-maç istatistikleriyle eşleşti. **122 adayın** sadece lig alanları zaten boştu; bu boşlukları 0'a çevirmiyoruz.
- Tüm toplamlar **kısmi veridir**, kesin bir sezon toplamı olduğunu garanti etmiyoruz.

## Her gece 23:50 otomatik güncelleme

`.github/workflows/daily-stats.yml` GOAL API'nin resmî Python SDK'sını kullanarak istatistikleri yeniden hesaplar:
1. `src/goal_season_export.py` — Süper Lig maçları
2. `src/goal_all_official_export.py` — UEFA, Türkiye Kupası ve millî takım resmi turnuvaları
3. `src/goal_publish_csv.py` — 224 U23 adayı için **public CSV** çıktısı
4. Github Actions çıktı dosyalarını otomatik commit eder.

Veri dosyaları:
- `data/players.json` — mevcut oyuncu aday listesi
- `data/official_totals.csv` — ana listelerde kullanılacak tüm resmî toplamlar
- `data/competitions.csv` — turnuva bazında istatistik
- `data/coverage.csv` — turnuva bazında eksik maç kapsaması

Bu iş akışı **GOAL_API_KEY** repository secret'ını kullanır. API limitleri veya kaynak erişimi engellenirse eski CSV'yi koruyacak şekilde işlemi hata ile durdurur.

### Google Sheets otomatik senkronizasyonu

**Dikkat:** GitHub'ın CSV yayınlaması ile Sheets'in satırlarının yenilenmesi ayrı iki şeydir.

Seçenek A: Google Sheets'teki `API Canlı Bağlantı` sekmesinde `IMPORTDATA` formülü. Google bir kez **Allow access / Erişime izin ver** onayı ister. Bu onaydan sonra ana listelerin metrik hücreleri formüllerle CSV'ye bağlanabilir; Sheets'in harici veri önbelleği nedeniyle yenileme tam 23:50'ye denk gelmeyebilir.

Seçenek B: `GOOGLE_SERVICE_ACCOUNT_JSON` adlı GitHub Secret ve bu servis hesabına Google Sheets dosyasında Editor yetkisi eklenirse, `src/goal_apply_csv_to_sheet.py` verileri doğrudan üç ana sekmeye yazar.

**Henüz bu bağlantılardan birinin uçtan uca otomatik çalıştığı onaylanmış değil.** İlk içerik Google Drive bağlantısı üzerinden doğrudan yazılmıştır.

### Reytinglerin Google Sheets tarafından tarihe dönüştürülmesi (29 Ekim 2026 düzeltmesi)

Türkçe Google Sheets `IMPORTDATA` bazen `7.12` gibi noktalı ondalık sayıları tarih sanıp **46363** gibi tarih seri numaralarına çevirebilir. Bu yüzden `data/official_totals_safe.csv` içindeki `rating_x100` değerleri **712** olarak yayımlanır; Google Sheets'in üç ana sekmesindeki reyting formülü otomatik olarak **100'e bölüp 7,12** gösterir. Eksik veri `N/A` olarak kalır, yanlışlıkla sıfır sayılmaz.

Her gece 23:50 GitHub Actions, `official_totals_safe.csv` dosyasını da günceller. Canlı Sheets içe aktarımı bu dosyayı kullanır. Yenileme süresi Sheets'in kendi dış veri önbelleğine bağlıdır.

## Kaynak ve sınırlar

GOAL API resmî Python SDK'sı: https://github.com/goal-api/goal-api-python  
GOAL API kapsamı: https://goal-api.com/coverage  
TFF: https://www.tff.org

GOAL API TFF'nin resmi oyuncu lisans servisi değildir. Kulüp/takım bilgileri, oyuncuların TFF statüsü ve genç yabancı kontenjanı ayrıca doğrulanmalıdır. API'nin lig listesinde bulunmak oyuncu maç verilerinin eksiksiz olacağını garanti etmez.
