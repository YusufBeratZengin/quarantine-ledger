# quarantine-ledger

Karantinaya alınan testlere sahip, son tarih ve bütçe koyar.

`quarantine-ledger`, elle tutulan bir karantina dosyasını okuyan ve muafiyetin
süresi dolduğunda, sahibi kaybolduğunda, issue bağlantısı geçersiz olduğunda,
kayıt yinelendiğinde veya takımın belirlediği bütçe aşıldığında kalite kapısını
düşüren küçük ve bağımlılıksız bir komut satırı aracıdır. Test sonuçlarını
değiştirmez: hiçbir testi `skip`/`xfail` yapmaz, silmez ve ağa çıkmaz.

- Türkçe belge: bu dosya
- English documentation: [README.md](README.md)

## Kurulum

Python 3.11 veya üzeri. Çalışma zamanı bağımlılığı yoktur.

```bash
python -m pip install .
```

Geliştirme için (test, lint, tip denetimi; CI ile birebir aynı kilitli sürümler için `-c requirements-dev.lock`):

```bash
python -m pip install -c requirements-dev.lock -e ".[dev]"
```

## 30 saniyelik örnek

```bash
quarantine-ledger --version
quarantine-ledger demo --dir demo-out
quarantine-ledger check demo-out/quarantine.toml --inventory demo-out/tests.json --today 2026-11-02
```

Gerçek çıktı (Windows, Python 3.14; yalnız yol ayırıcıları işletim sistemine özgü).
Proje standardı gereği komut satırı çıktıları, bulgu kodları ve JSON alanları
işletim sistemi yerel ayarlarından (`LANG`/`LC_ALL`) bağımsız olarak bilinçli
biçimde İngilizce tutulur; böylece CI betikleri çıktıyı deterministik olarak
ayrıştırır, kullanıcı belgeleri ise hem İngilizce ([README.md](README.md)) hem
Türkçe (`README.tr.md`) sunulur. Aşağıdaki blok birebir terminal kaydıdır;
satırların Türkçe karşılığı bloğun altındadır.

```text
Demo created in demo-out
Run: quarantine-ledger check demo-out\quarantine.toml --inventory demo-out\tests.json --today 2026-11-02

FAIL: 5 finding(s)
  EXPIRED [test_login_timeout]: Entry 'test_login_timeout': expires 2026-11-01 <= today 2026-11-02
  MAX_AGE_EXCEEDED [test_login_timeout]: Entry 'test_login_timeout': age 32 days > max_age_days 30
  EXPIRED [test_expired_example]: Entry 'test_expired_example': expires 2026-10-01 <= today 2026-11-02
  MAX_AGE_EXCEEDED [test_expired_example]: Entry 'test_expired_example': age 62 days > max_age_days 30
  MISSING_FROM_INVENTORY [test_expired_example]: Test 'test_expired_example' not found in inventory (it may have been renamed or deleted)
```

Çıkış kodu: `1`.

Satır satır Türkçe karşılığı:

- `EXPIRED [test_login_timeout]`: `test_login_timeout` kaydının son tarihi
  (2026-11-01) denetim gününe (2026-11-02) eşit veya ondan eski.
- `MAX_AGE_EXCEEDED [test_login_timeout]`: kayıt 32 günlük, politika sınırı 30.
- `EXPIRED` / `MAX_AGE_EXCEEDED [test_expired_example]`: aynı iki kural, 62
  günlük kayıt için.
- `MISSING_FROM_INVENTORY [test_expired_example]`: kimlik `--inventory`
  listesinde yok; test yeniden adlandırılmış veya silinmiş olabilir.

`demo` var olan dosyaların üzerine yazmayı reddeder. Hem hedef dosya adlarını hem de
geçici çalışma dosyalarını (örneğin `.quarantine.toml.tmp`) önceden denetler; her dosyayı
özel oluşturma kipinde (`open("x")`) açarak var olan verileri kesmeyi veya silmeyi
engeller. İkinci çalıştırma temiz bir kullanım hatası verir:

```text
Error: refusing to overwrite existing file(s) in 'demo-out': README.md, quarantine.toml, tests.json; pass an empty --dir
```

Çıkış kodu: `2`.

## Karantina dosyası

```toml
[policy]
max_age_days = 30          # isteğe bağlı: bu yaştan eski kayıtları reddet
max_entries_per_team = 5   # isteğe bağlı: owner_team başına bütçe
max_total_entries = 20     # isteğe bağlı: tüm defter için bütçe

[[entries]]
id = "test_login_timeout"                                   # tam test kimliği, joker yok
owner_team = "auth-team"                                    # takım etiketi için tasarlandı; '@' reddedilir
issue = "https://github.com/example/project/issues/123"     # http(s) adresi, çevrimdışı sözdizimi denetimi
reason = "Flaky due to network timing in CI"                # boş olamaz
created = "2026-10-01"                                      # YYYY-MM-DD
expires = "2026-11-01"                                      # YYYY-MM-DD
```

Dosya okunurken uygulanan kurallar (ihlal, çıkış kodu `2` ile ve **tüm** hatalar
birlikte raporlanır, yalnız ilki değil):

- hem `quarantine.toml` hem de `--inventory` JSON dosyası geçerli UTF-8
  kodlamasında olmalıdır. Okunamayan veya geçersiz UTF-8 bayt dizisi içeren
  dosyalar (örneğin UTF-16 yönlendirmeleri) traceback yerine temiz bir hata
  mesajı ve çıkış kodu `2` ile reddedilir.
- kökte yalnız iki anahtar olabilir: `entries` ve `policy`. Başka bir kök
  anahtar hatadır; böylece `[[entry]]` (tekil) yazım hatası defteri sessizce
  boşaltıp "0 kayıt denetlendi" ile geçiremez. Tamamen boş dosya da aynı
  nedenle hatadır. Yalnız `[policy]` tablosu içeren dosya geçerli, boş bir
  karantina listesidir.
- `policy` bir tablo olmalıdır; yalnız `max_age_days`, `max_entries_per_team` ve
  `max_total_entries` kabul edilir ve hepsi pozitif tamsayıdır (`true`/`false`
  veya tırnaklı sayılar dönüştürülmek yerine reddedilir).
- her kayıt yukarıdaki altı anahtarı taşıyan bir tablo olmalıdır; bilinmeyen
  anahtarlar ve metin olmayan değerler hata verir. Böylece `expires_at` gibi bir
  yazım hatası "son tarih yok" anlamına gelmek yerine açıkça başarısız olur.
- `created` ve `expires` katı ve sıfır dolgulu `YYYY-MM-DD` dizgileri olmalıdır
  (örneğin `2026-01-02`). `2026-1-2` gibi sıfır dolgusuz tarihler veya bozuk
  dizgiler sessizce kabul edilmez, doğrudan kullanım hatası verir.

Alan *içeriği* kuralları `check` sırasında uygulanır; bu yüzden süre ve bütçe
bulgularıyla birlikte görünürler (yine çıkış kodu `2`, yine hepsi birden):

- `id` tam bir test kimliği olmalıdır: bölümler içinde harf, rakam ve `.`, `_`,
  `-`, `/`; bölümler arasında isteğe bağlı `::` ayıracı.
  `tests/test_auth.py::TestLogin::test_timeout` gibi koşucu kimlikleri olduğu
  gibi kabul edilir; tek iki nokta (`test:login`), bozuk iki nokta dizileri
  (`:::`) ve jokerler (`test_*`) `INVALID_ID` ile reddedilir, çünkü tek bir
  joker bir test ailesinin tamamını muaf tutardı.
- `owner_team` boş olamaz ve `@` içeremez (e-posta adresleri ve `@kullanici`
  etiketleri `OWNER_TEAM_LOOKS_LIKE_EMAIL` ile reddedilir). Çevrimdışı sözdizimi
  denetimi bir kişi adını veya kullanıcı adını takım etiketinden ayırt edemez;
  kişi adı yerine takım etiketi kullanmak ekip incelemesiyle korunmalıdır.
- `issue` bir host belirten `http://` veya `https://` adresi olmalıdır. Tek
  başına `https://` değeri `INVALID_ISSUE_URL` ile reddedilir. Yalnız sözdizimi
  denetlenir; adres hiçbir zaman çağrılmaz, erişilebilirlik iddiası yoktur.

## `check` neleri bildirir

| Kod | Anlamı | Çıkış |
| --- | --- | --- |
| `EXPIRED` | `expires <= today` (sona erdiği gün de süresi geçmiş sayılır) | 1 |
| `MISSING_FROM_INVENTORY` | kimlik `--inventory` listesinde yok (test yeniden adlandırılmış/silinmiş) | 1 |
| `INVALID_DATE` | `created`, `expires` tarihinden sonra | 1 |
| `DUPLICATE_ID` | aynı kimlik birden fazla kez geçiyor (her satır için bir bulgu) | 2 |
| `MAX_AGE_EXCEEDED` | kayıt `policy.max_age_days` değerinden eski | 2 |
| `BUDGET_EXCEEDED_TOTAL` | kayıt sayısı `policy.max_total_entries` değerini aşıyor | 2 |
| `BUDGET_EXCEEDED_TEAM` | bir takım `policy.max_entries_per_team` sınırını aşıyor | 2 |
| `EMPTY_ID`, `EMPTY_OWNER_TEAM`, `EMPTY_ISSUE`, `EMPTY_REASON` | zorunlu alan boş | 2 |
| `OWNER_TEAM_LOOKS_LIKE_EMAIL` | `owner_team` içinde `@` var; takım etiketi kullanın | 2 |
| `INVALID_ID` | kimlik tam bir test kimliği değil (joker veya desteklenmeyen karakter) | 2 |
| `INVALID_ISSUE_URL` | issue host içeren bir `http(s)://` adresi değil, ör. `https://` | 2 |

### Çıkış kodları

`check` bir kalite kapısı komutudur; çıkış kodu defterin politikayı geçip geçmediğini gösterir:

| Kod | Anlamı |
| --- | --- |
| `0` | bulgu yok (kalite kapısı başarılı) |
| `1` | kapı şu anda kırık (süresi geçmiş, envanterde yok, imkânsız tarih) |
| `2` | kullanım/giriş hatası veya defter düzeyi politika ihlali (yinelenen kayıt, bütçe, geçersiz kimlik, boş alan, geçersiz adres) |

**Karışık bulgularda öncelik:** Kullanım ve girdi hataları (okunamayan veya
UTF-8 olmayan dosyalar, bozuk TOML/JSON, şema tür hataları, geçersiz `--today`)
politika denetiminden önce çalışmayı durdurur ve `2` döner. Politika denetimi
çalıştığında ise tüm bulgular birlikte raporlanır; aynı koşumda hem kapıyı
kıran bulgular (`1`: `EXPIRED`, `MISSING_FROM_INVENTORY`, `INVALID_DATE`) hem de
defter politikası ihlalleri (`2`: ör. `BUDGET_EXCEEDED_*`, `MAX_AGE_EXCEEDED`,
`DUPLICATE_ID`, `INVALID_*`, `EMPTY_*`, `OWNER_TEAM_LOOKS_LIKE_EMAIL`) birlikte
bulunursa çıkış kodu `1` öncelik alır. Böylece hâlihazırda kırık olan kalite
kapısı yalnızca yapılandırma sorunu gibi görünmez.

`--inventory` verilmeden çalıştırmada `MISSING_FROM_INVENTORY` hiç üretilmez:
"test artık yok" sonucu defterin kendisinden çıkarılamaz.

`report` bir kalite kapısı değil, inceleme ve raporlama komutudur: bulgular veya süresi geçmiş kayıtlar olsa dahi rapor başarıyla üretildiği sürece `0` ile çıkar (böylece CI rapor üretirken erken kırılmaz ve rapor çıktısı saklanabilir). Yalnızca kullanım veya dosya okuma hatalarında `2` ile çıkar.

## Rapor

```bash
quarantine-ledger report quarantine.toml --format summary
quarantine-ledger report quarantine.toml --format json > quarantine-report.json
```

`json` çıktısı `policy`, `summary` (içinde `by_code`), her kayıt için bir nesne
(`expired` ve `age_days` değerleri `--today` değerine göre hesaplanır) ve
`findings` dizisini içerir. `report` komutunun bulgular olsa bile rapor üretildiği
sürece `0` ile çıktığını unutmayın; CI hattını kırmak için `check` komutunu kullanın.
`check --format json` ise `exit_code`, `checked_entries`, `inventory_provided` ve
`findings` alanlarını verir.

## CI'da kullanım

```yaml
- name: Quarantine ledger
  run: |
    python -m pip install quarantine-ledger
    quarantine-ledger check quarantine.toml --inventory tests.json --today "$(date -u +%F)"
```

Testlerde sabit bir `--today` verin, üretimde CI gerçek UTC tarihini kullansın;
böylece sonuçlar deterministik kalır ve gece yarısı yerel saat farkı sorun
çıkarmaz.

## Geliştirme

```bash
bash scripts/check.sh
```

Betik, hangi dizinde çalıştırılırsa çalıştırılsın proje köküne geçer ve ruff
(lint + biçim), katı kip mypy ve dal kapsamı ölçümlü pytest
(`--cov-fail-under=85`) çalıştırır. Ayrıca başarılı saymadan önce ruff'ın
gerçekten Python dosyası bulduğunu doğrular: bu proje bir zamanlar
`.git/info/exclude` içeriği `*` olan bir üst deponun içindeydi ve ruff tüm
dosyaları atlayıp yine de `0` ile çıkıyordu. Bu yüzden ruff
`--no-respect-gitignore` ile çağrılır (varsayılana dönmek için
`QUARANTINE_LEDGER_RESPECT_GITIGNORE=1`).

- `src/quarantine_ledger/schema.py` - kayıt/politika veri sınıfları ve kuralları
- `src/quarantine_ledger/reader.py` - TOML/JSON okuma ve tam doğrulama
- `src/quarantine_ledger/policy.py` - denetimler, bulgular ve çıkış kodu eşlemesi
- `src/quarantine_ledger/dates.py` - katı `YYYY-MM-DD` ayrıştırma, UTC "bugün"
- `src/quarantine_ledger/cli.py` - argparse arayüzü, metin/JSON çıktısı, `demo`
- `examples/` - aynı örnek defterin statik dosyaları
- `.github/workflows/ci.yml` - Linux ve Windows, Python 3.11 ve 3.13
- [CHANGELOG.md](CHANGELOG.md) - sürüm geçmişi ve değişiklik notları
- [CONTRIBUTING.md](CONTRIBUTING.md) - geliştirici kurulumu ve katkı rehberi
- [SECURITY.md](SECURITY.md) - güvenlik politikası ve açık bildirme süreci
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) - topluluk davranış kuralları

## Kapsam ve dürüst sınırlar

- Elle tutulan bir dosyanın statik denetimi. Flaky test tespiti, otomatik
  `skip`/`xfail`, test silme, issue açma veya bildirim yoktur.
- Issue adresleri yalnız sözdizimi açısından (şema ve host) denetlenir;
  erişilebilirlik iddiası kurulmaz. Ağa hiçbir şey gönderilmez.
- Test kimlikleri tam eşleşmelidir. Joker karakterler bilinçli olarak
  reddedilir: tek satırlık bir joker geniş bir muafiyet yaratırdı.
- Pytest marker, Jest ve Playwright envanter adaptörleri henüz yok; `--inventory`
  test kimliklerinden oluşan bir JSON dizisi bekler ve herhangi bir koşucu bunu
  birkaç satırda üretebilir.
- GitHub Actions CI matrisi (`ubuntu-latest` + `windows-latest`, Python 3.11 ve
  3.13) bu ortamdan GitHub üzerinde çalıştırılmadı. Yerel doğrulama Windows'ta
  (Python 3.14) `bash scripts/check.sh` koşumunu ve Python 3.11 ile 3.14
  üzerinde yalıtılmış wheel kurulumu + CLI duman testlerini kapsar; sürüm
  yayınlamadan önce GitHub üzerindeki tam matris sonuçları doğrulanmalıdır.
- `owner_team` doğrulaması yalnızca alanın boş olmadığını ve `@` içermediğini
  (e-posta adreslerini ve `@kullanici` etiketlerini) denetler. Araç bir kurum
  dizini olmadan çevrimdışı çalıştığı için `@` içermeyen kişi adlarını veya
  kullanıcı adlarını takım etiketinden otomatik olarak ayırt edemez; `reason`
  gibi serbest metin alanları da kişisel veri taramasından geçirilmez. Deftere
  kişisel veri girmemek ekip sorumluluğundadır.

## Lisans

MIT, bkz. [LICENSE](LICENSE).
