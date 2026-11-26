# DOU Assess 6.19/6.19.1 → 6.20 Sunucu Yükseltme

## En kısa yol

6.20 ZIP'ini sunucuya yükleyin, **mevcut 6.19 klasörünün üstüne ZIP açmayın**. Yeni ZIP'i ayrı klasöre çıkarın ve scripti yeni klasörden çalıştırın.

```bash
cd /opt/dou-assess
unzip DOU-Assess-6.20-QUALITY360-SERVER-READY.zip
cd DOU-Assess-6.20-QUALITY360-SERVER-READY
chmod +x Upgrade-Server-6.20.sh
bash Upgrade-Server-6.20.sh
```

Script mevcut proje klasörünü `/opt/dou-assess` altında otomatik arar. Otomatik bulamazsa:

```bash
bash Upgrade-Server-6.20.sh --current-dir /opt/dou-assess/DOU-Assess-6.19-FINAL-SERVER-READY
```

6.19.1 kullanıyorsanız klasör adını ona göre verin.

## Script neyi korur?

- mevcut PostgreSQL named volume,
- evidence volume,
- scan volume,
- ops volume,
- mevcut `.env`,
- mevcut `secrets/`,
- kullanıcılar, ders/sınav/öğrenci/veri kayıtları,
- taramalar ve kanıt dosyaları.

Bunu, yeni kodu **mevcut çalışan Compose proje köküne** uygulayarak yapar. Böylece Docker Compose project name değişmediği için named volume kimliği de değişmez.

## Otomatik backup

Yükseltmeden önce hedef klasörde şu klasör oluşturulur:

```text
_upgrade_backups/6.20-YYYYMMDD-HHMMSS/
```

İçerik:
- `postgresql-before-6.20.dump`
- `postgresql-schema-before-6.20.sql`
- `persistent-data-before-6.20.tar.gz` (container'da tar varsa)
- `.env`
- `secrets/`
- compose/nginx checkpoint
- `code-before-6.20.tar.gz`
- upgrade öncesi/sonrası readiness çıktıları

## Yükseltme sonrası beklenen değerler

```text
version: 6.20-quality360-server-ready
schema_revision: 0019_quality360
```

Elle hızlı kontrol:

```bash
cd /opt/dou-assess/<mevcut-proje-klasoru>
bash Verify-6.20.sh --base-url http://127.0.0.1:8080
```

Port `.env` içinde farklıysa URL'yi değiştirin.

## Kesinlikle çalıştırmayın

```bash
docker compose down -v
```

`-v`, Compose named volume'lerini siler ve PostgreSQL/evidence/scan/ops verisini riske atar.
