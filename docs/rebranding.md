# GPTTranslator átnevezési ellenőrzés

## Elvégzett módosítások

A program neve GPTTranslator lett. Az átnevezés a főablakra, a beállításokra, a tálcaikonra, a Windows-azonosítóra, a Python-csomagra, a JavaScript-névterekre, a buildre, az EXE verzióadataira, a naplókra és az aktív dokumentációra is kiterjed. A GitHub repository és a helyi projekt gyökérmappája szintén GPTTranslator nevet kapott.

Az új ikon két, fordítást jelképező beszédbuborékból áll, ezüst és grafitszürke színekkel. Az [ikonkészlet](../gpttranslator/assets/) PNG-fájljai és a tíz méretet tartalmazó ICO ugyanabból az átlátszó hátterű képből készültek. A [generálási prompt](../gpttranslator/assets/icon-prompt.txt) az assetek mellett szerepel.

A program verziója 6.0 maradt. Az átnevezéshez nem készült új release vagy tag. A korábbi kiadások dokumentumai és mérési bizonyítékai bájtpontosan a [történeti archívumba](history/README.md) kerültek; a jegyzék 82 fájljának hash-ellenőrzése sikeres.

## Adatok és telepített példány

A lezárt helyi profilból 1873 fájl került át az új `%LOCALAPPDATA%\GPTTranslator` mappába. A teljes másolat SHA-256 összehasonlítása egyezett, és az eredeti forrásfájlok változatlanok maradtak. A másolat tartalmazta a beállításokat, a böngésző tárolóját és gyorsítótárát, az OCR-modelleket, az NVIDIA-állapotot és a naplókat. A régi példány zárolófájlja nem került át.

A telepített program `GPTTranslator.exe` néven indul. A telepített és a staging EXE SHA-256 értéke azonos:

```text
d31f089a779b714641936ea6189ec32093678835451e6ed54fc2e62b4c2f899f
```

A Start menüben GPTTranslator parancsikon készült az új EXE-hez és ikonhoz. A korábbi két helyi EXE az alkalmazások könyvtárán belüli `GPTTranslator-archivum/rebrand-elotti` mappába került, változatlan hash-sel.

A helyi alkalmazásadatok között az aktív profil, a gyorsítótárak és a megőrzött korábbi adatok is a `%LOCALAPPDATA%\GPTTranslator` könyvtár alatt vannak. A visszaállítási másolat a `backups/before-rebrand/profile` almappába került; az áthelyezés mind az 1874 fájl hash-ét megőrizte, a korábbi zárolófájlt is beleértve. A külön, korábbi EXE-névhez tartozó üres Qt-gyorsítótármappa a `backups/before-rebrand/qt-cache` almappába került. A két régi nevű felső szintű Local könyvtár megszűnt, és a GPTTranslator újraindult az új profilból.

Az új alkalmazás normál, helyi profillal elindult. Az új NVIDIA-profil ellenőrzése és az egyszeri automatikus újraindítás után a főablak megnyílt, a ChatGPT betöltődött, és az automatizálás az ApplicationWorld környezetbe bekerült. A tényleges felületen az új név és ikon, a megőrzött beállítások, valamint a bejelentkezett ChatGPT-munkamenet is látható volt.

## Ellenőrzési eredmények

| Ellenőrzés | Eredmény |
| --- | --- |
| Teljes Python tesztcsomag | 462/462 sikeres, 120,948 másodperc |
| JavaScript tesztek | 69/69 sikeres |
| Python fordíthatóság, JavaScript szintaxis, függőségek | Sikeres |
| EXE forrás-, asset-, név-, ikon- és futtatókörnyezet-ellenőrzése | 50/50 sikeres |
| Becsomagolt EXE offline öntesztje | 12/12 sikeres, 9 ciklus |
| RapidOCR és Windows OCR a helyi mintán | Mindkettő az elvárt szöveget adta |
| Lezárt tényleges profil másolata | 1873/1873 fájl azonos |
| Történeti archívum | 82/82 fájl azonos |

Az offline önteszt helyi DOM-mintával futott, élő ChatGPT-beküldés nélkül. A normál indítás ellenőrzése az alkalmazás, a böngésző, a munkamenet és az automatizálás betöltődését igazolja; a tartós, játékterhelés alatti működésre nem ad külön mérési eredményt. Az induláskor a weboldal konzolja egy tartalommentesen naplózott hibaeseményt jelzett, ezt sikeres lapbetöltés és scriptinjektálás követte.

A [tartalommentes ellenőrzési összesítés](evidence/rebranding-checks.json) az aktuális build és telepítés adatait rögzíti. Beállítások, cookie-k, fordításszövegek és böngészőadatbázisok nem kerültek a repositoryba.
