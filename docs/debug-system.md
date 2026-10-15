# Esemény- és hibanaplózás

## Naplók helye és működése

A normál alkalmazás automatikusan JSONL eseménynaplót ír a `%LOCALAPPDATA%\GPTTranslator\logs` könyvtárba. A Beállítások `Naplómappa megnyitása` gombja ezt a könyvtárat nyitja meg. A napló nem kerül feltöltésre.

Az aktuális fájl `gpttranslator.jsonl`. Az 5 MiB-os korlát elérésekor az előző fájl `.1` végződést kap; összesen öt korábbi fájl marad meg. A lemezírás külön háttérszálon fut, legfeljebb 4096 várakozó eseménnyel. A megtelt sor és a helyreállt lemezírás saját eseményt kap. Naplózási hiba nem állíthatja le a fordítást.

Minden sor helyi időzónás időbélyeget, folyamatazonosítót, szálazonosítót, alkalmazásverziót, munkamenet-azonosítót, eseménytípust és súlyosságot tartalmaz. A fordítási események közös `request_id` mezője összeköti a kérés teljes útját. A számszerű időtartamok ezredmásodpercben szerepelnek.

## Rögzített események

- alkalmazásindulás, Qt-importhiba, példánykezelés, kilépés és kezeletlen Python-kivételek
- ablak és böngésző betöltése, aktív vagy pihentetett állapot, háttérmód, újratöltés és böngészőfolyamat-leállás
- gyorsgombok regisztrálása, műveletindítás, várakoztatás, elutasítás és Windows-hibakódok
- képkivágási engedély, lejárat, kép mérete, előkészítési idő, sorba állítás és sorbetelés
- OCR-modellintegritás, motorindítás, feldolgozási variánsok, jelöltek száma, futásidő és hibák
- képbeillesztési kísérlet, feltöltés visszaigazolása, várakozás, tartalmi állapotjelzők és küldési szakasz
- válaszfelismerés, időtúllépés, késői válaszfigyelés, elavult eredmény elutasítása és fordítás mentése
- begépelés indítása, befejezése, fókuszváltás vagy új kérés miatti megszakítása
- beállításmentés, hibás beállításfájl és mentési hiba

A `runtime.snapshot` esemény 15 másodpercenként az alkalmazás és a megjelenítő folyamat CPU-idejét, memóriahasználatát, a szabad rendszermemóriát és az eseményhurok késését méri. A CPU-százalék a folyamat két mintavétel közötti CPU-idejéből számított, a gép logikai processzorszámára normalizált érték. Ez nem játékbeli FPS- vagy fizikai bemeneti késleltetés-mérés, és GPU-terhelést nem mér.

## Tartalomvédelem

A napló csak engedélyezett számlálókat, állapotjelöléseket és időtartamokat fogad el. Fordítás, prompt, OCR-szöveg, kép, vágólaptartalom, cookie, token, jelszó, teljes webcím és helyi fájlút nem kerül bele. A böngésző és a Qt által kiírt üzenetekből a súlyosság és a hossz marad meg. Kivételnél a típus, ismert forrásmodul, függvénynév és sorszám szerepel, a nyers hibaüzenet és a forrássor nem.

A napló nem rögzíti az összes lenyomott billentyűt: kizárólag az alkalmazás saját gyorsgombjaihoz tartozó műveleteket követi. Az offline önteszt és a staging külön ideiglenes naplómappát használ, a normál profilt nem éri el. A PyInstaller Python előtti bootloaderhibája nem jut el ehhez a naplózóhoz; ilyen esetben a Windows alkalmazáseseményeit is meg kell nézni.

## Hibakeresés

Hibánál jegyezd meg az időpontot és a műveletet. A kérés `request_id` mezőjével látszik, hogy a folyamat a kivágás, a csatolás, a küldés, a válasz vagy a begépelés szakaszában állt meg. Az előző fájlokat is meg kell tartani, mert a kérés kezdete már forgatott naplóba kerülhetett.

```powershell
.\.venv313\Scripts\python.exe tools\read_diagnostics.py --last 200
.\.venv313\Scripts\python.exe tools\read_diagnostics.py --level ERROR --last 50
.\.venv313\Scripts\python.exe tools\read_diagnostics.py --request-id <request_id>
.\.venv313\Scripts\python.exe tools\read_diagnostics.py --summary
```

A naplóolvasó a forgatott fájlokat időrendben olvassa. A hibás vagy félbeszakadt sorokat kihagyja és jelzi; a napló tartalmát nem módosítja.

## Javított működés

- Új fordítási kéréskor a régi mentett szöveg érvénytelenné válik. Sikertelen kérés után a begépelési gyorsgomb nem gépelheti be a korábbi választ.
- A válasz az új beküldött felhasználói üzenethez kötődik. Egy korábbi válasz újrarajzolása önmagában nem jelent új fordítást.
- A fájlkiválasztó mező saját beállítása nem igazolja a kép feltöltését. A kész csatoláshoz tényleges látható kép-előnézet és befejezett feldolgozás kell.
- Sikertelen csatolás után a saját, vissza nem igazolt fájlkijelölés törlődik, így nem blokkolja a következő kivágást. A valós csatolmány és a folyamatban levő feltöltés megmarad.
- A késői válaszfigyelés legfeljebb 120 másodpercig marad aktív. Új kérés után a korábbi válasz nem írhatja felül a legújabb eredményt.
- A késői válaszfigyelés lezárása megőrzi az utolsó választ akkor is, ha a felület eseménykezelése a lezárás idején késik.
- A várakozó jogosított képek sorba kerülnek. Begépelés közben a képkivágási gyorsgomb várakoztatható, nem vész el némán.
- Az automatikus képküldés legfeljebb három teljes próbálkozást végez ugyanazzal a mentett képpel. A beszélgetésben megjelent képes kérés után a válaszra vár; a már beküldött képet nem küldi el újra.
- A képfeldolgozás eseményei elkülönítik a csatolást, a beküldés visszaigazolását, a bizonytalan beküldést és a válaszra várást. A kéréshez nem köthető assistant üzenet önmagában nem igazolja a képes kérés sikerét.

## Korábbi ellenőrzések

A korábbi naplóvizsgálatok, verziónkénti tesztszámok és EXE-hash-ek a [történeti dokumentációban](history/README.md) szerepelnek. A régi mérések az ott megnevezett programfájlra érvényesek.
