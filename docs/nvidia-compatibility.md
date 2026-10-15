# NVIDIA-kompatibilitás és egérakadás javítása

## Működés

A GPTTranslator beépített NVIDIA-kompatibilitási beállítása a fókuszban jelentkező egérakadás javítását szolgálja. A G-SYNC/VRR alkalmazásszintű használatát a saját EXE-jéhez kezeli.

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

A saját profil neve `ColorsASD GPTTranslator - auto ` kezdetű, utána a normalizált teljes EXE-útvonal SHA-256 azonosítójának első 16 karaktere szerepel. A tulajdonnyilvántartás az alkalmazás helyi adatmappájának `nvidia-compat` könyvtárában készül, Windows alatt alapból a `%LOCALAPPDATA%\GPTTranslator\nvidia-compat` útvonalon. Az automatikus mentést új driversessionből végzett ellenőrzés követi. Az első mentés utáni egyszeri újraindítás külön indulási jelzővel védi ki az ismétlődő újraindulást.

| Indítás módja | NVIDIA-profilkezelés |
| --- | --- |
| Kész EXE normál indítása | Ellenőrzés, szükség esetén saját profil létrehozása vagy kikapcsoláskor eltávolítása |
| Forrásból indított `main.py` | Nem módosít driverprofilt |
| `--staging` | Nem módosít driverprofilt |
| Offline `--self-test-report` | Nem módosít driverprofilt |

A profilkezelés eredményét a meglévő [helyi diagnosztikai napló](debug-system.md) rögzíti. A `failed`, `unsupported`, `existing_profile` és `ownership_unproven` eredmények elkülönítik a mentési hibát, a hiányzó támogatást, a megőrzött idegen profilt és a nem igazolt tulajdonjogot. A program ezek után is továbbindul.


## Korábbi ellenőrzések

A kézi és automatikus driverprofil-próbák korábbi eredményei, EXE-útvonalai és hash-ei a [történeti NVIDIA-leírásban](history/pre-gpttranslator/docs/nvidia-compatibility.md) maradtak meg.
