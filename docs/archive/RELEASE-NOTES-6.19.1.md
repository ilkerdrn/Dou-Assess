# DOU Assess 6.19.1 – Server Network Hotfix

Bu sürüm, kurumsal ağın HTTP/80 paket deposu trafiğini 403 ile engellediği ortamlarda Docker image build işlemini destekler.

Değişiklik:
- Dockerfile içindeki Debian APT kaynakları build öncesinde `http://` -> `https://` olarak normalize edilir.
- Uygulama kaynak kodu, veritabanı şeması, migration head (`0018_classic_assessment_standard`) ve işlevsel davranış değiştirilmemiştir.

Sunucu gözlemi:
- Ubuntu host APT depolarında aynı HTTP/80 engeli HTTPS kullanılarak aşılmıştır.
- Docker build sırasında `deb.debian.org` HTTP istekleri 403 döndürdüğü için bu hotfix gereklidir.
