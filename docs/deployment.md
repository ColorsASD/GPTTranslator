# Telepítési útmutató

## Célkörnyezet és korlátok

A GPTTranslator Python/PySide6 Windows asztali alkalmazás. A program saját Qt WebEngine ablakban nyitja meg a ChatGPT webes felületét, és helyi JavaScript automatizálást használ.

A fejlesztői parancsok a repository gyökeréből, PowerShellben futnak. A Python-csomag neve `gpttranslator`, a kész program neve `GPTTranslator.exe`. A normál Windows-adatmappa `%LOCALAPPDATA%\GPTTranslator`.

Az aktív helyi adatok mind ebből a GPTTranslator könyvtárból működnek:

| Adat | Almappa vagy fájl |
| --- | --- |
| Beállítások és legutóbbi fordítás | `settings.json` |
| Böngésző-munkamenet és webhelyadatok | `browser/storage` |
| Böngésző-gyorsítótár | `browser/cache` |
| Qt-gyorsítótár | `cache` |
| OCR-modellek | `ocr` |
| Eseménynaplók | `logs` |
| NVIDIA-profil állapota | `nvidia-compat` |

Az átnevezéskor ezen a gépen megőrzött helyi mentés a `backups/before-rebrand` almappában található. Ez visszaállítási másolat, az aktív program a fenti közvetlen útvonalakat használja.

## Korábbi adatok átvétele

Az átnevezés előtti adatokhoz megtartott kompatibilitási útvonalak:

| Környezet | Korábbi adatforrás | GPTTranslator adatmappája |
| --- | --- | --- |
| Windows, elérhető `LOCALAPPDATA` | `%LOCALAPPDATA%\Gamer Translator` | `%LOCALAPPDATA%\GPTTranslator` |
| Felhasználói alapkönyvtár | `%USERPROFILE%\.gamer-translator` | `%USERPROFILE%\.gpttranslator` |

A normál indítás az alapértelmezett új profilmappához keres régi adatot. Windows alatt a helyi alkalmazásadat-mappa az elsődleges forrás; ennek hiányában a korábbi felhasználói alapkönyvtár is átvehető. Ha nincs `LOCALAPPDATA`, a program az új `.gpttranslator` mappát használja. Az önteszt, a staging és az egyedileg megadott tesztprofil nem indít ilyen átvételt.

Az első átvétel a beállításokat, a böngésző tárolóját, az OCR-modelleket és a többi helyi adatot külön átmeneti könyvtárba másolja. A másolat csak a teljes másolás után, egyetlen könyvtárátnevezéssel válik az új profillá. A régi forrásadatok megmaradnak. A már adatot tartalmazó új mappába nincs automatikus egyesítés vagy felülírás.

A program a másolás előtt ellenőrzi a régi példány zárolását, és a régi profil zárát a normál futás végéig megtartja. A korábbi programot az új indítása előtt teljesen zárd be a tálcaikonjánál is. Futó régi példány, nem biztonságosan másolható könyvtár vagy másolási hiba esetén az indítás figyelmeztetés után leáll; az alkalmazás nem folytatja üres profillal. A félbemaradt átmeneti másolat törlődik, a régi adatok megmaradnak.

## Elkülönített függőségtelepítés

```powershell
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv313\Scripts\python.exe -m pip check
```

A `requirements-lock.txt` a csomagolandó környezet pontos verzióit rögzíti. A dokumentált parancsok explicit `.venv313` futtatót használnak. A korábbi interpretertelepítés ellenőrzési adatai a [történeti archívumban](history/README.md) maradtak meg.

## Forrásellenőrzés

```powershell
.\.venv313\Scripts\python.exe -m unittest discover -s tests -v
node --check gpttranslator\automation.js
node --test tests\test_automation.cjs
.\.venv313\Scripts\python.exe -m compileall -q main.py gpttranslator tests tools
git diff --check
```

A WebEngine regressziók külön böngészőprofilt és helyi DOM-mintát használnak. A natív műveleteket vizsgáló tesztek helyettesített rendszerintegrációkkal futnak. A tesztek nem indítanak élő ChatGPT-beküldést.

A függőségaudit külön környezetből futtatható, hogy az audit eszközei ne módosítsák a csomagolandó környezetet:

```powershell
.\.venv313\Scripts\python.exe -m venv "$env:TEMP\gpttranslator-audit"
& "$env:TEMP\gpttranslator-audit\Scripts\python.exe" -m pip install pip-audit==2.10.1 bandit==1.9.4
& "$env:TEMP\gpttranslator-audit\Scripts\python.exe" -m pip_audit -r requirements-lock.txt
& "$env:TEMP\gpttranslator-audit\Scripts\python.exe" -m bandit -r main.py gpttranslator
```

A későbbi audit eredménye az újonnan közzétett sérülékenységek miatt eltérhet. A korábbi audit eredménye a jelentésében rögzített csomagverziókra vonatkozik.

## Tesztprogram készítése

```powershell
.\build.ps1 -PythonExecutable .\.venv313\Scripts\python.exe -OutputDirectory dist\staging\verified -SkipDependencyInstall
.\.venv313\Scripts\python.exe tools\verify_build.py '.\dist\staging\verified\GPTTranslator.exe'
Get-FileHash -LiteralPath 'dist\staging\verified\GPTTranslator.exe' -Algorithm SHA256
```

A buildhez használt interpreterrel futtasd a csomagellenőrzést is. A `tools\verify_build.py` összeveti a becsomagolt forrást és asseteket a munkafával, valamint ellenőrzi a natív futtatókörnyezetet. A részletes eredmény a build melletti `build-manifest.json` fájlba kerül. A `-SkipDependencyInstall` kapcsoló előzetesen telepített és ellenőrzött környezetet igényel.

Sikertelen függőségtelepítés vagy csomagolás hibával leáll, és nem írja felül a meglévő célprogramot. A build saját futására a Windows és a kiválasztott interpreter könyvtáraira szűkíti a PATH-ot, majd visszaállítja az eredeti értéket.

## A kész EXE offline próbája

```powershell
& '.\dist\staging\verified\GPTTranslator.exe' --self-test-report '.\dist\staging\verified\self-test.json' --self-test-duration 120
```

A jelentés `passed` mezőjének igaznak, a kilépési kódnak nullának kell lennie. Automatizált futtatáskor várd meg az elindított folyamat végét, és csak utána olvasd a jelentést.

Az önteszt ideiglenes profilt és memóriavágólapot használ. Nem regisztrál globális gyorsbillentyűt, nem indít képkivágót és nem használja a normál böngészőprofilt. A szöveg- és képpróba helyi HTML-mintával, blokkolt külső kérésekkel fut.

A becsomagolt OCR-motorok futtatásához a `--self-test-model-dir` kapcsolóval add meg az ellenőrzött helyi ONNX-modellek könyvtárát. Az önteszt másolatot készít az ideiglenes profilba, majd a hash-ellenőrzés után futtatja a motorokat. A modelleket nem tölti le automatikusan. Az OCR minősége külön a `tools\benchmark_ocr.py` eszközzel mérhető.

## Elkülönített élő felületi próba

```powershell
& '.\dist\staging\verified\GPTTranslator.exe' --staging
```

A staging az élő ChatGPT-t külön ideiglenes profillal nyitja meg. A figyelés kezdetben ki van kapcsolva, és a rendszerintegrációk tesztmódban nem működnek. A bejelentkezést és az esetleges CAPTCHA-t a tesztelő végzi el. A kézzel elküldött szöveg az élő szolgáltatáshoz kerül.

## Kiadás és visszaállítás

A kész EXE-t csak a forrás-, csomag- és offline ellenőrzés után cseréld a használt példányra. Zárt alkalmazás mellett készíts helyi biztonsági másolatot a `%LOCALAPPDATA%\GPTTranslator` könyvtárról. Ez bejelentkezési munkamenetet és fordításszöveget is tartalmazhat, ezért ne kerüljön repositoryba.

A kiadáshoz tartozó fájlméretet, SHA-256 értéket és teszteredményt mindig a tényleges új buildből rögzítsd. A [korábbi kiadásellenőrzések](history/README.md) az archívumban megnevezett korábbi EXE-kre érvényesek.

Az Authenticode-aláíráshoz a `tools\sign_release.ps1` a tanúsítvány ujjlenyomatát, a pontos kiadót, az elfogadott bemeneti SHA-256 értéket, a SignTool helyét és a hiteles időbélyegző URL-jét kéri. Alapértelmezett bemenete `dist\staging\verified\GPTTranslator.exe`, kimenete `dist\release-signed\GPTTranslator.exe`. A Git-commit vagy tag GPG-aláírása önmagában nem írja alá a Windows EXE-t.

Hiba esetén zárd be az új programot, és állítsd vissza a korábbi EXE-t. A böngészőprofil visszafelé kompatibilitása nem garantált; szükség esetén a zárt programhoz készített teljes adatmappa-másolatot használd.
