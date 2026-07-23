# v3.0 Sürüm Notları

- Kurumsal modül ayrı Flask Blueprint olarak tasarlandı; v2.9 ekranları korunur.
- Tüm yeni veritabanı nesneleri `v3_` öneki taşır.
- Sistem yöneticisi, denetçi, denetçi yardımcısı, muhasebe sorumlusu, firma kullanıcısı ve salt okunur yönetici rolleri eklendi.
- Firma bazlı rol kapsamı ve izin denetimi eklendi.
- Görev/termin/bildirim, cari yaşlandırma, hareket bazlı banka eşleştirme, rapor tasarımı ve şifreli yedekleme eklendi.
- Denetim izi; giriş, değişiklik, yükleme, yedek ve indirme işlemlerini kaydeder.
- Yüksek hacimli görev, banka ve günlük tabloları sayfalıdır.
- Excel/CSV/TXT okuyucu Türkçe kolon adlarını normalize eder.
- Yama kurucusu `app.py` dosyasını değişiklikten önce zaman damgalı olarak yedekler.
