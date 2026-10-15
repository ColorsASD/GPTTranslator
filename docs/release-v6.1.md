# A v6.1 kiadás ellenőrzése

Ellenőrzés dátuma: 2026. október 15.

A kiadás neve GPTTranslator v6.1. A program és az EXE Windows-verzióadatai 6.1-et jelölnek. A kiadási csomag az új nevet, az új ikont és az átnevezett `gpttranslator` Python-csomagot tartalmazza.

## Ellenőrzési eredmények

| Ellenőrzés | Eredmény |
| --- | --- |
| Teljes Python regressziók | 462/462 sikeres, 119,911 másodperc |
| JavaScript regressziók | 69/69 sikeres |
| Csomagolt forrás, ikon, Windows-névadatok és futtatókörnyezet | 50/50 sikeres |
| Offline EXE-önteszt | 12/12 sikeres, 109 ciklus |
| Csomagolt RapidOCR és Windows OCR | Mindkét motor az elvárt `Hello gamer` mintaszöveget adta |
| Függőségek, Python-fordíthatóság, JavaScript-szintaxis | Sikeres |

Az EXE mérete 381 681 788 bájt. A `GPTTranslator-v6.1.exe` SHA-256 ellenőrzőösszege:

```text
543ca83e8333e2968d3c5cbec14860c3fed3037dd89801919ba41f72e7a5636a
```

A kiadási build saját Python-moduljai az [átnevezés után ellenőrzött buildhez](rebranding.md) képest kizárólag a verziószámban különböznek. A végleges EXE forrásait és assetjeit a `tools/verify_build.py` közvetlenül összevetette a munkafával. A Windows-fájltulajdonságok, a beágyazott ikon mind a tíz mérete és a csomagolt natív könyvtárak is az ellenőrzés részei.

## Ellenőrzési környezet

Az offline EXE-próba elkülönített profillal, memóriavágólappal és helyi DOM-mintával futott. A teszt 3 modern képes kérést és 1 utánuk küldött szöveges kérést teljesített. A becsomagolt RapidOCR és Windows OCR a helyi, hash-ellenőrzött modellekkel ténylegesen felismerte a mintaszöveget.

A regressziók és az önteszt nem küldenek élő ChatGPT-kérést. A játékterhelés alatti tartós működésre ez az ellenőrzés nem ad külön mérési eredményt. Az átnevezéskor végzett tényleges helyi profilátvétel és normál indulás adatai a [külön átnevezési jelentésben](rebranding.md) maradtak meg; annak 6.0 verziójú EXE-hash-e a korábbi helyi buildhez tartozik.

Az EXE Authenticode-állapota `NotSigned`. A Git commit és a verziótag GPG-aláírása külön ellenőrzés, önmagában nem írja alá az EXE-t. A kiadási assetek a programot, a `LICENSE.txt` fájlt és a `SHA256SUMS.txt` ellenőrzőösszeg-listát tartalmazzák. A böngészőprofil, a beállítások, a mentett fordítások és az OCR-modellek nem kerülnek a kiadási fájlok közé.

A tartalommentes [kiadásellenőrzési állomány](evidence/release-v6.1-checks.json) a fenti végleges build adatait tartalmazza.
