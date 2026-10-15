# Hangbeszélgetés és mikrofonengedély

Dátum: 2026. október 15.

Alkalmazásverzió: `5.18`.

## A javítás oka

A beágyazott ChatGPT oldalon a `Start voice` gombra kattintás után a weboldal mikrofonhozzáférést kérhet. A Gamer Translator korábban nem kezelte ezt a Qt WebEngine-jelzést, ezért nem jelent meg engedélykérő ablak. A javítás az alkalmazás saját böngészőjéhez ad natív mikrofonengedély-kezelést.

A hangbeszélgetéshez a mikrofon engedélyezése szükséges. A fejhallgató vagy hangszóró hangkimenetéhez nincs külön `QWebEnginePermission`-engedély; a lejátszás a Windows hangkimeneti beállításait követi. A program nem módosítja a Windows eszközválasztását vagy a rendszer mikrofonvédelmi beállításait.

## Működés

- A `Start voice` gomb után a ChatGPT mikrofonkérése magyar párbeszédablakot nyit: `Engedélyezed a ChatGPT számára a mikrofon használatát?`.
- Az `Engedélyezés` átadja a mikrofonengedélyt a megfelelő weboldali kérésnek. A `Tiltás`, az Escape vagy az ablak bezárása elutasítja a kérést.
- Az alapértelmezett gomb a `Tiltás`; az Enter önmagában nem jelent mikrofonengedélyt.
- A párbeszédablak a főablakhoz kötött, és `open()` hívással nyílik meg. Nem indít blokkoló, beágyazott eseményhurkot.
- Egyszerre egy engedélykérő ablak jelenik meg. Az egyidejű, azonos jogosultságú kérések annak döntését követik.
- Új oldalbetöltés, a böngésző megjelenítőfolyamatának leállása vagy a programból való kilépés elutasítja a függő kéréseket. Egy régi párbeszédablak későbbi döntése nem adhat engedélyt az új oldalnak.
- Az engedélyezés pillanatában a program ismét ellenőrzi a kérés érvényességét és az aktuális főoldali eredetet.

A Qt a mikrofonhoz tartozó `MediaAudioCapture` engedélyt nem tárolja tartósan. A program minden új `permissionRequested` mikrofonkérésnél felhasználói döntést kér, és nem ment saját tartós mikrofonengedélyt. A webes `Start voice` gomb egy újabb kattintása önmagában nem jelenti, hogy a Qt szükségszerűen új engedélykérést küld. Az engedélykérés és az eredethez kötött döntés a [QWebEnginePermission dokumentációját](https://doc.qt.io/qt-6/qwebenginepermission.html) követi.

## Az engedély határai

Csak a `https://chatgpt.com` és a `https://chat.openai.com` pontos eredetéhez tartozó mikrofonkérés engedélyezhető, HTTPS és alapértelmezett 443-as port mellett. A kérő eredetnek egyeznie kell a főablak aktuális oldalának eredetével. Másik engedélyezett ChatGPT-host kérésére sem elegendő a jelenlegi oldalhoz tartozó döntés.

A program elutasítja a kamera, a kamera és mikrofon együttes, a képernyőmegosztás és az egyéb webes engedélyek kérését. Külső oldal, bizonytalan vagy hibás eredet, eltérő port, illetve felhasználónevet vagy jelszót tartalmazó webcím nem kap mikrofonengedélyt.

A napló csak a kérés típusát és az engedélyezés eredményét rögzíti. A teljes webcím, a beszélgetés szövege és a hang tartalma nem kerül az engedélykezelő naplójába.

## Háttérműködés

A rejtett weboldal továbbra is felfüggeszthető, amikor tétlen. A program a láthatatlanná tett oldal `recommendedState()` értékét ellenőrzi, így a Qt által aktívan tartandó mikrofon, WebRTC-kapcsolat vagy hanglejátszás közben `Active` marad. A rejtett oldal saját újrarajzolása és frissítőidőzítője ilyenkor is leáll.

A `recommendedStateChanged` jelzés után a program újraszinkronizálja az életciklust. Amikor a média befejeződik és nincs más alkalmazásfeladat, a lap ismét `Frozen` állapotba kerülhet. Az aktív hang használata az ablak előtérbe hozásától függetlenül marad meg. Az ajánlott életciklus a [QWebEnginePage dokumentációjában](https://doc.qt.io/qt-6/qwebenginepage.html#recommendedState-prop) szerepel.

## Offline ellenőrzés

Az engedélykezelő regressziói a jóváhagyást, elutasítást, Escape és ablakbezárás útján történő tiltást, az egyidejű kéréseket, a hibás vagy külső eredeteket, az érvénytelen Qt-objektumokat és az oldalváltás utáni döntést vizsgálják. A naplózás próbája ellenőrzi, hogy a beszélgetési adatok és webcímek ne kerüljenek a naplóba.

A valódi Qt WebEngine-próba külön folyamatban, privát böngészőprofillal és hálózati kérések nélkül fut. A Chromium `--use-fake-device-for-media-stream` kapcsolója szintetikus hangforrást ad; a valódi mikrofon nem vesz részt a tesztben. A próba nem használ `--use-fake-ui-for-media-stream` kapcsolót, ezért a program tényleges magyar engedélykérőjén keresztül halad.

A próba ellenőrzi a natív médiakérés engedélyezését és elutasítását, a külső eredet kérésének megtagadását, valamint azt, hogy rejtett hangrögzítés mellett a lap fut, majd a hangforrás leállítása után ismét felfüggesztődik. Az életciklus külön regressziói a háttérbeli újrarajzolás és saját frissítőtimer leállását is ellenőrzik.

A teszt szintetikus hangfolyamot használ, nem rögzít valódi mikrofonhangot és nem küld adatot az élő ChatGPT-nek. A bejelentkezett ChatGPT hangbeszélgetésének teljes szolgáltatási folyamatát és a tényleges fejhallgató hangkimenetét külön kézi használat igazolhatja.

```powershell
.\.venv313\Scripts\python.exe -m unittest discover -s tests -p test_browser_permissions.py -v
.\.venv313\Scripts\python.exe -m unittest discover -s tests -p test_browser_voice_media.py -v
.\.venv313\Scripts\python.exe -m unittest discover -s tests -p test_browser_lifecycle.py -v
```

## A helyi javítás ellenőrzése

Ellenőrzés dátuma: 2026. október 14.

| Ellenőrzés | Eredmény |
| --- | --- |
| Python regressziók | 417/417 sikeres, 99,178 másodperc |
| Ebből mikrofonengedély-kezelés | 20/20 sikeres |
| Ebből valódi Chromium médiakérés | 4/4 sikeres, szintetikus hangforrással és hálózat nélkül |
| Ebből böngésző-életciklus | 19/19 sikeres |
| JavaScript regressziók | 55/55 sikeres |
| Csomagolt források és futtatókörnyezet | 42/42 egyezés |
| Offline EXE-önteszt | 12/12 sikeres, 9 ciklus, 14,271 másodperc, kilépési kód 0 |
| Normál EXE-indulás | Ablak és automatizálás sikeresen elindult |
| Meglévő NVIDIA-profil | `already_configured`, `verified: true`, `changed: false` |
| Felhasználói hangbeszélgetés-próba | A magyar mikrofonablak megjelent, és a hangbeszélgetés elindult |

A csomagolt RapidOCR és Windows OCR motor a helyi modellekkel egyaránt a várt `Hello gamer` szöveget ismerte fel. Az offline médiapróba szintetikus hangot és blokkolt hálózatot használt; ez az automatizált ellenőrzés nem vett fel valódi mikrofonhangot, és nem indított beszélgetést az élő szolgáltatásban.

A felhasználó a normál, bejelentkezett alkalmazásban külön kipróbálta a `Start voice` gombot, és visszajelezte: „Megjelenik, és a hangbeszélgetés is elindul”. A normál alkalmazás tartalommentes naplója egy mikrofonengedély-kérést és egy `accepted: true` döntést rögzített. Ez a magyar engedélykérő és a hangbeszélgetés indulásának felhasználó által megerősített kézi ellenőrzése; műszeres hangminőség-, egérkésés- vagy játék-FPS-mérés nem történt.

Az akkor ellenőrzött EXE 381 660 901 bájt volt. SHA-256: `7854af819a273b6978609f69a942a97246d8d0a84171be9193061f0f1e4c6e3b`. Az ellenőrzéskor azonos fájl volt a `dist/staging/voice-permission/Gamer Translator.exe` buildútvonalon és a futó program helyén, `dist/staging/rounded-browser/Gamer Translator.exe` néven. Az utóbbi útvonalra azóta az első megnyitás szegélyméretét javító helyi EXE kerül; annak friss eredményei a [felületi leírásban](design.md) szerepelnek. A meglévő, bevált NVIDIA-profil a hangengedély ellenőrzésekor változatlan maradt.

A tartalommentes eredmények az [ellenőrzési állományban](evidence/voice-permission-checks.json) szerepelnek.
