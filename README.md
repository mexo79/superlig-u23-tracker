# Süper Lig U23 2026-27 — Veri Takip

[Google Sheets](https://docs.google.com/spreadsheets/d/1eyhOf-1Vv3LmYCRmodFMBsxAflYIRH7l3iUThRHdVuM/edit)

## En son durum (29 Ekim 2026)

- GitHub bağlantısı doğrulandı; GOAL API secret `GOAL_API_KEY` **mevcut**. Gizli anahtar değeri okunmadı.
- Güvenli test: [GitHub Actions GOAL API bağlantı testi](https://github.com/mexo79/superlig-u23-tracker/actions/workflows/goal-api-test.yml).
- Testte `/leagues`, Süper Lig `/leagues/:id` ve `/players/search` isteklerinin tümü HTTP **403** döndü.
- Yanıt JSON açıklaması: **"The site owner has blocked access based on your browser's signature."** Bu mesaj GOAL API'nin Cloudflare güvenlik katmanından geldi. Bu, anahtarın geçerliliğini kanıtlamaz ya da reddetmez; güvenlik katmanı veri isteklerini doğrulanmadan engellemektedir.
- API sağlayıcısına GitHub Actions üzerinden sunucu-sunucu erişimin desteklenip desteklenmediği sorulmalı. Güvenlik engeli atlatılmamalı.
- Google Sheet'teki 224 oyuncu adayı ve 3 liste mevcut; performans sütunları **henüz canlı veriyle dolmadı**, TFF kayıtlarının hepsi doğrulanmadı.
- Google Sheets'e otomatik yazma için `GOOGLE_SERVICE_ACCOUNT_JSON` GitHub Actions secret ve service-account Editor paylaşımı henüz doğrulanmadı.

## Kaynaklar
- [GOAL API documentation](https://goal-api.com/documentation), Bearer authentication
- [GOAL API Süper Lig coverage](https://goal-api.com/coverage/turkey-super-lig-api)
- [TFF](https://www.tff.org)

## Plan
1. GOAL API sağlayıcısı erişim engelini kaldırırsa uç noktalar ve 2026-27 veri alanları örnek istekle doğrulanır.
2. GOAL API oyuncu ID'leri 224 aday oyuncuyla eşleştirilir; belirsiz eşleşmeler manuel doğrulamaya gönderilir.
3. Dakika, maç, ilk 11, gol, asist, kartlar ve **sadece kaynağın sağladığı** reyting Süper Lig alanlarına yazılır. Diğer müsabakalar ayrı tutulur.
4. Google Sheets yetki bağlantısı kurulur, manuel test çalıştırılır, ardından her gece 23:50 (Europe/Istanbul) istatistik yenilemesi etkinleştirilir.
5. TFF kontenjanı yılın Temmuz ayında kontrol edilir; günlük performans verileri bu alanları etkilemez.

## Kod
`.github/workflows/daily-stats.yml`: şu anda **yalnızca GOAL API erişim durumunu** kontrol eder. Veri tablosunu güncellemez.
`.github/workflows/goal-api-test.yml`: GOAL API uç nokta testi.
`src/rapidapi_sync.py`: önceki sağlayıcıya ait prototip; GOAL API ile uyumlu değildir ve aktif değildir.
`src/update_stats.py`: eski sağlayıcının prototip giriş noktası; aktif değildir.

**Not:** GOAL API ile Süper Lig oyuncu istatistiklerinin tam kapsamı ve GitHub Actions erişimi doğrulanana kadar otomatik veriler hazır olarak sunulmamalıdır.
