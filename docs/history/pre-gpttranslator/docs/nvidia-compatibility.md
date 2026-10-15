# NVIDIA-kompatibilitás és egérakadás javítása

Dátum: 2026. október 15.

## Működés

A Gamer Translator beépített NVIDIA-kompatibilitási beállítása a fókuszban jelentkező egérakadás javítását szolgálja. A korábbi helyi próbában a Chrome alkalmazásprofiljával azonos G-SYNC/VRR-kikapcsolás megszüntette a felhasználó által jelzett akadást. A program ezt a beállítást a saját EXE-jéhez kezeli.

Az NVIDIA-profil a videokártya-illesztőprogram helyi beállítása, amely egy adott alkalmazásra vonatkozik. Maga a driverprofil nem kerül át másik gépre az EXE másolásával. A kész program tartalmazza azt a működést, amely a normál indításkor az adott gépen ellenőrzi és szükség esetén létrehozza a saját profilját. Így NVIDIA-val és elérhető profilkezeléssel rendelkező gépen nincs szükség minden új helyen külön kézi beállításra.

- A `NVIDIA egérakadás javítása` beállítás alapból bekapcsolt. A GPU-gyorsítás opciója alatt külön kapcsolóval vezérelhető.
- Az aktuális EXE pontos teljes útvonalára érvényes; átnevezett vagy másik mappába másolt EXE-hez a következő normál indítás az új útvonalat ellenőrzi.
- Egyetlen saját értéket állít be: a G-SYNC/VRR alkalmazásszintű használatának kikapcsolását.
- A globális profil és más programok, játékok profiljai változatlanok maradnak.
- NVIDIA vagy használható NVAPI nélkül az alkalmazás a szokásos módon továbbindul.
- Ha a driver nem engedi a profil mentését, a program továbbindul, és az eredményt a helyi naplóban rögzíti.

A profil ellenőrzése az ablak és a webes grafikus környezet létrehozása előtt történik. Új beállítás sikeres mentése és visszaellenőrzése után a program egyszer automatikusan újraindul, hogy friss folyamat használja a driverprofilt. A már megfelelő profil ismételt induláskor nem igényel új mentést vagy újraindítást. A kapcsoló módosítása és mentése szintén automatikus újraindítással lép érvénybe. A beállítás nem képkockaszám-korlát: a webes rajzolást a beágyazott Chromium kompozitora ütemezi.

## Meglévő profilok és kikapcsolás

A program megőrzi a felhasználó korábbi, kézzel létrehozott profilját. Ha az EXE már a megfelelő `FORCE_OFF` beállítással rendelkezik, az automatikus javítás sikeres meglévő beállításként kezeli, új mentés nélkül. Eltérő, idegen profil esetén nem írja felül az értéket; ezt a napló `existing_profile` eredménye jelzi.

A kapcsoló kikapcsolása csak a program által létrehozott saját automatikus profilt távolíthatja el. Ehhez az alkalmazás helyi tulajdonnyilvántartásának és a driverből frissen kiolvasott profilnak is egyeznie kell: egyetlen alkalmazás, a pontos EXE-útvonal és az egyetlen változatlan saját beállítás szükséges. A kézzel létrehozott korábbi tesztprofil, más alkalmazást tartalmazó profil és az utólag módosított automatikus profil megmarad.

A helyi tulajdonnyilvántartás elvesztésekor a program nem tekinti bizonyítottnak a profil tulajdonjogát, ezért nem törli. Az EXE áthelyezésekor a korábbi útvonalhoz tartozó profil szintén megmarad; a kapcsoló mindig az éppen futó EXE saját profilját kezeli.

## Technikai felépítés

A profilkezelés a telepített NVIDIA-illesztőprogram NVAPI felületét használja. Nem telepít új drivert, és nem igényel külső profilkezelő programot. A [hivatalos NVIDIA-definíció](https://github.com/NVIDIA/nvapi/blob/main/NvApiDriverSettings.h) szerint a használt érték `VRR_APP_OVERRIDE_ID` (`0x10A879CF`) = `VRR_APP_OVERRIDE_FORCE_OFF` (`1`).

A saját profil neve `ColorsASD Gamer Translator - auto ` kezdetű, utána a normalizált teljes EXE-útvonal SHA-256 azonosítójának első 16 karaktere szerepel. A tulajdonnyilvántartás az alkalmazás helyi adatmappájának `nvidia-compat` könyvtárában készül, Windows alatt alapból a `%LOCALAPPDATA%\Gamer Translator\nvidia-compat` útvonalon. Az automatikus mentést új driversessionből végzett ellenőrzés követi. Az első mentés utáni egyszeri újraindítás külön indulási jelzővel védi ki az ismétlődő újraindulást.

| Indítás módja | NVIDIA-profilkezelés |
| --- | --- |
| Kész EXE normál indítása | Ellenőrzés, szükség esetén saját profil létrehozása vagy kikapcsoláskor eltávolítása |
| Forrásból indított `main.py` | Nem módosít driverprofilt |
| `--staging` | Nem módosít driverprofilt |
| Offline `--self-test-report` | Nem módosít driverprofilt |

A profilkezelés eredményét a meglévő [helyi diagnosztikai napló](debug-system.md) rögzíti. A `failed`, `unsupported`, `existing_profile` és `ownership_unproven` eredmények elkülönítik a mentési hibát, a hiányzó támogatást, a megőrzött idegen profilt és a nem igazolt tulajdonjogot. A program ezek után is továbbindul.

## A korábbi kézi próba

A beépítés előtt a `dist/staging/rounded-browser/Gamer Translator.exe` külön, kézzel létrehozott `ColorsASD Gamer Translator – steady refresh` profilt kapott. A globális és a Chrome profil állapota a művelet előtt és után egyezett. Új NVAPI session igazolta a saját profilból érvényesülő `FORCE_OFF` értéket.

A felhasználó a fókuszban lévő program 10–15 másodperces tétlen szakasza után az egér mozgatásával ellenőrizte az eredményt, és megerősítette: „Megszűnt az akadás”. Ez kézi felhasználói visszajelzés, nem műszeres egérkésés- vagy játék-FPS-mérés. A korábbi próba részletes ellenőrzési adatai a [felületi leírásban](design.md) szerepelnek. Az automatikus profilkezelés ezt a kézi profilt nem veszi át saját tulajdonként.

## A beépített működés ellenőrzése

Ellenőrzés dátuma: 2026. október 14.

| Ellenőrzés | Eredmény |
| --- | --- |
| Python regressziók | 391/391 sikeres, 96,292 másodperc |
| Ebből NVIDIA-profilkezelés | 28/28 sikeres, driver-adatbázismintával |
| Ebből NVIDIA-indulási integráció | 12/12 sikeres |
| Ebből felületi regresszió | 14/14 sikeres |
| JavaScript regressziók | 55/55 sikeres |
| Csomagolt források és futtatókörnyezet | 41/41 egyezés |
| Offline EXE-önteszt | 12/12 sikeres, 9 ciklus, 14,414 másodperc, mindkét OCR-motor: `Hello gamer`, kilépési kód 0 |
| Valódi NVAPI és normál EXE-indulás | 3/3 kör sikeres |

A valódi driverpróba külön alkalmazásadat-mappával és a normál, csomagolt EXE-vel futott. A teljes EXE-útvonalhoz kezdetben sem alkalmazásbejegyzés, sem saját automatikus profil nem tartozott.

1. Az első indítás létrehozta és új sessionből igazolta a saját profilt: `applied`, `changed: true`, `verified: true`. Pontosan egyszer indult új folyamat; az ablakot már az `already_applied` állapotot olvasó új folyamat nyitotta meg.
2. A következő indítás `already_applied`, `changed: false`, `verified: true` eredményt adott, és nem indult újra.
3. A beállítás kikapcsolása `restored`, `changed: true`, `verified: true` eredménnyel eltávolította a bizonyított saját profilt. Pontosan egyszer indult új folyamat. A friss sessionben az alkalmazásbejegyzés és a profil egyaránt hiányzott; a következő folyamat `disabled` állapottal nyitotta meg az ablakot.

Mindhárom normál ablak szabályos kilépési kérés után bezárult, a napló `app.exit` eseménye 0 kilépési kódot rögzített, és a folyamat az operációs rendszerben is megszűnt. A profilpróba előtti és utáni, külön friss lekérdezések három globális VRR-értéke és a Chrome override értéke egyezett. A korábbi kézi `steady refresh` profil megmaradt.

Az akkor ellenőrzött köztes EXE 381 655 865 bájt volt. SHA-256: `54df976c8ae66b8cdc10cefc211cb1e78659153bf93a1a360734dd704ad66eae`. Az elkülönített build a `dist/staging/portable-nvidia/Gamer Translator.exe` útvonalon készült; az azonos hashű program a `dist/staging/rounded-browser/Gamer Translator.exe` helyére is bekerült. Ezen a korábbi útvonalon a meglévő bevált kézi profil érvényesült, amelyet a beépített kezelés nem módosított.

A nyers jelentések a `dist/nvidia-compat-preview` mappában, a tartalommentes összesített eredmények az [ellenőrzési állományban](evidence/nvidia-compatibility-checks.json) találhatók. Az új ellenőrzés a profilkezelést, az indulást és a meglévő alkalmazásfunkciókat igazolja; új műszeres egérkésés- vagy játék-FPS-mérés nem történt.
