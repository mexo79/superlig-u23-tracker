# Süper Lig U23 Tracker • 2026–27

[Google Sheets veritabanı](https://docs.google.com/spreadsheets/d/1eyhOf-1Vv3LmYCRmodFMBsxAflYIRH7l3iUThRHdVuM/edit)

## Durum
- Beş sekmeli, sütun filtreleriyle artan/azalan sıralanabilir Google Sheets dosyası oluşturuldu.
- GitHub Actions günlük kontrolü 23:50 Europe/Istanbul saatine ayarlandı.
- **Otomatik istatistik yazma henüz aktif değil:** Google Sheets service-account anahtarı, TFF oyuncu ana listesi ve SofaScore oyuncu kimlikleri gerekiyor.
- Sistem eksik ayarda veri yazmaz; kaynak hatasında eski değerler korunur.

## Kurulum
1. GitHub Actions repository variable `GOOGLE_SHEET_ID`: `1eyhOf-1Vv3LmYCRmodFMBsxAflYIRH7l3iUThRHdVuM`
2. Google Cloud'da Sheets API etkin bir hizmet hesabı aç, Sheets dosyasını bu hesabın e-postasına **Editor** olarak paylaş.
3. Hizmet hesabı JSON'unu GitHub Actions secret `GOOGLE_SERVICE_ACCOUNT_JSON` olarak ekle. Credential'ı repoya commit etme.
4. `TFF Kontenjan` sekmesine TFF doğrulanmış oyuncu listesi, ayrım, uygunluk ve SofaScore IDs ekle.
5. Manuel workflow çalıştır; gerçek istatistiklerin doğru ve eksiksiz geldiğini doğrula.

SofaScore resmî ve herkese açık desteklenen API sunmuyor; burada kullanılan URL gayriresmî ve erişimi/izinleri garanti değil. SofaScore istatistiklerini başka veri sağlayıcısının verileriyle karıştırma.

TFF uygunluk kuralı yılda bir Temmuz'da kontrol edilir. Avrupa, kupa ve millî takım istatistikleri ayrı kaynak ve alan gerektirir; mevcut kod yalnızca Süper Lig içindir.
