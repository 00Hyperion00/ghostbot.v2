# Sürekli Denetim Merkezi v3.0 — Kurumsal Yama

Bu paket v2.9 üzerine eklenen kurumsal modüldür. Mevcut `data/audit.db` dosyasını silmez; yalnız `v3_` önekli tablolar oluşturur.

## Kurulum
1. v2.9 uygulamasını kapatın.
2. `data` klasörünü yedekleyin.
3. Bu paketin içeriğini v2.9 ana klasörüne kopyalayın.
4. `YUKSELT_V3.0.cmd` dosyasını çalıştırın.
5. Uygulamayı normal başlatma dosyanızla açın ve `/v3/` adresine gidin.

## Modüller
- Çoklu firma ve firma grubu
- Kullanıcı, rol, şirket kapsamı ve ayrıntılı izinler
- Güvenli oturum, parola hash'i ve CSRF koruması
- Kurumsal yönetim paneli
- Görev, termin, uygulama içi bildirim ve gecikme takibi
- 120/320 açık kalemleri için cari yaşlandırma
- Banka hareketi içe aktarma ve muhasebe kayıtlarıyla puanlı eşleştirme
- Yönetim ve detaylı denetim rapor şablonları
- Şifreli yedekleme ve SHA-256 bütünlük doğrulaması
- Değişiklik ve güvenlik günlüğü
- Büyük tablolar için sayfalama ve filtreleme

## Veri şablonları
Cari yaşlandırma dosyasında mümkün olduğunca şu başlıkları kullanın: `Hesap Kodu, Cari Kod, Cari Unvan, VKN, Belge No, Belge Tarihi, Vade Tarihi, Borç, Alacak, Bakiye`.

Banka dosyasında: `Tarih, Valör, Hesap No/IBAN, Referans, Açıklama, Döviz, Tutar, Bakiye`. Giriş/Çıkış ayrı kolonlardaysa sistem bunları da tanır.

## Güvenlik notu
İlk yönetici kurulum sırasında oluşturulur. Parola en az 10 karakter olmalıdır. Varsayılan parola kullanıldıysa ilk girişte değiştirilmelidir. Şifreli yedek parolası unutulursa geri getirilemez.

## Geri alma
`app.py.v2.9_backup_YYYYMMDD_HHMMSS` dosyasını tekrar `app.py` yapın. `v3_` tabloları mevcut v2.9 tablolarını etkilemez.

## Otomatik doğrulama
Paket; Python 3.12 söz dizimi, Flask test istemcisi, veritabanı şeması, yönetici girişi ve kurumsal gösterge paneli testlerinden geçirilir.
