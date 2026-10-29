# 2026-27 Süper Lig U23 veritabanı

**Google Sheets:** https://docs.google.com/spreadsheets/d/1eyhOf-1Vv3LmYCRmodFMBsxAflYIRH7l3iUThRHdVuM/edit

**Durum (29 Ekim 2026):** Üç aday oyuncu listesi hazır, API adaptörü GitHub'a eklendi. **API anahtarı ve Google yetkilendirmesi henüz yapılandırılmadığından oyuncu performansları canlı doldurulmadı.** Kaynağı doğrulanmamış istatistikler sıfır yapılmaz.

## Sistem nasıl çalışır?

- **Performans:** [RapidAPI Süper Lig sağlayıcısı](https://rapidapi.com/yuvr99-WHTEITBQbOc/api/super-lig/pricing). 2026-27 fikstürünü sorgular, yalnızca bitmiş ve arşivde henüz bulunmayan maçların oyuncu detaylarını indirir.
- Maç başına oyuncu verilerini iki gizli Google Sheets sekmesinde saklar, dakika/maç/ilk 11/reyting/gol/asist/sarı/kırmızı toplamlarını hesaplar.
- **TFF:** Türk/Yabancı ve 2026-27, 2027-28 kontenjan bilgileri yalnızca TFF kontenjan sekmesinden gelir; günlük işlem bunları değiştirmez.
- **Üç görünüm:** Tüm U23, U23 Yabancı, U23 Türk. Her görünümde artan/azalan başlık filtreleri korunur.
- **Saat:** Her gün 23:50 (Europe/Istanbul). Kaynağın maç istatistiklerini eksik göndermesi durumunda eski değerleri korur ve sorun günlüğe/Actions'a yansır.

## Kullanıcının bir kez yapacağı iki yetkilendirme

1. [RapidAPI Süper Lig fiyatlandırması](https://rapidapi.com/yuvr99-WHTEITBQbOc/api/super-lig/pricing) üzerinden **Basic ($0, ayda 500 istek)** planını seç. API anahtarını GitHub deposunun **Settings → Secrets and variables → Actions → New repository secret** menüsünde `RAPIDAPI_KEY` adıyla ekle. Anahtarı bu sohbetin içine veya depoya dosya olarak yapıştırma.
2. [Google Cloud Console](https://console.cloud.google.com/) üzerinden Sheets API etkin bir *service account* oluştur ve bu servisin e-posta adresini yukarıdaki Google Sheet'e **Editor** olarak ekle. Service account JSON anahtarını aynı GitHub Secrets alanına `GOOGLE_SERVICE_ACCOUNT_JSON` adıyla ekle. GitHub depoya asla JSON anahtarını commit etme.

Sonra [GitHub Actions](https://github.com/mexo79/superlig-u23-tracker/actions/workflows/daily-stats.yml) sayfasında **Run workflow** ile manuel deneme yap. İlk tam çekim birden çok API isteği kullanır. İlk gece oyuncu sayısı, eşleşme oranı, stat alanlarının eksiksizliği ve kaynağın gerçek kadrolarla uyumu mutlaka doğrulanmalıdır.

## Teknik kısıtlar

- Buradaki API **TFF'nin resmî verisi değildir**. Henüz anahtarlı canlı test yapılmadığı için erişim, oyuncu şeması, reyting/ilk 11 alanı ve güvenilirlik **doğrulanmış değildir**.
- Sağlayıcının ücretsiz kotası ayda 500 istektir; maç başına fark yöntemi kotayı azaltır ama yoğun takvim veya yeniden çekimler kotayı aşabilir.
- Başlangıç oyuncu listesi **224 aday içerir**, bütün TFF lisans ve geçiş hakkı kayıtları bağımsız teyit gerektirir.
- Şu an otomasyon yalnızca **Süper Lig** istatistiklerini toplar; Ziraat Türkiye Kupası, Avrupa kupaları ve milli maçlar ayrı turnuvalar olarak sonradan entegre edilmelidir.
- 2027-28 kontenjan statüsü resmî olarak yayımlanana kadar öngörü olarak kalır.

## Kod
`src/rapidapi_sync.py`: yeni API adaptörü ve günlük veri eşleştirme.
`.github/workflows/daily-stats.yml`: Türkiye saatiyle 23:50 tetikleyici.
`src/update_stats.py`: eski komut için yeni adaptöre yönlendirme.
