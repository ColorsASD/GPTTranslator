# Hangbeszélgetés és mikrofonengedély

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


## Korábbi ellenőrzések

A verzióhoz kötött helyi és felhasználói ellenőrzések a [történeti hangengedély-leírásban](history/pre-gpttranslator/docs/voice-permissions.md) szerepelnek. Az ottani eredmények az átnevezés előtti EXE-hez tartoznak.
