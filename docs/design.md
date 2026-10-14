# Szürke felület

Dátum: 2026. október 15.

Alkalmazásverzió: `5.18`.

## Jelenlegi felépítés

A program főoldala közvetlenül a beágyazott `chatgpt.com` oldal. A szürke felső állapotsáv és a beállítások a két megadott Gamer Translator mintakép stílusát követik. Az eredeti képek 1672 × 941 képpontosak, a Windows címsorával együtt. A natív alkalmazás tartalmi ablaka 1680 × 900 képpontos alapméretet kapott, 1080 × 720 képpontos minimummal.

- Fent 82 képpontos állapotsáv, ChatGPT, Beállítások és Prompt elküldése gomb.
- A ChatGPT webnézete a felső sáv alatti teljes tartalmi szélességet használja.
- A webnézet 19 logikai képpontos maszkolása és az élsimított, 20 képpontos külső szegély együtt követi a keret sarokívét, az első ablaknyitásnál, átméretezés és háttérből visszatérés után is.
- A webnézet szegélye és a beállításréteg a tartalmi panel tényleges méretéhez igazodik. A panel megjelenítési és méretváltozási eseményei frissítik a rétegeket akkor is, ha a főablak mérete nem változik.
- A külön URL-sor és a program saját bal oldali navigációja eltávolítva. A saját kezdőlap, Chat/Work beviteli sor és ajánlókártyák helyét a ChatGPT oldala veszi át.
- A beállításoknál balra az általános kártya, jobbra a gyorsbillentyűk és az overlay. A mentés és visszaállítás állandó alsó sávban érhető el.
- 1200 képpontnál keskenyebb tartalmi panelen a beállítások egy oszlopba rendeződnek és függőlegesen görgethetők.

## Színek és vezérlők

| Elem | Szín |
| --- | --- |
| Ablakháttér | `#141414` |
| Mély felület | `#171717` |
| Kártyák | `#212121`–`#292929` |
| Finom keretek | `#383838`–`#484848` |
| Fő szöveg és ikonok | `#ececec` |
| Másodlagos szöveg | `#b2b2b2`–`#b6b6b6` |
| Világos műveleti gomb | `#aaaaaa`–`#d0d0d0` |

A saját felület Segoe UI betűkészletet, világos vonalikonokat, kerekített kártyákat és szürke kapcsolókat használ. A bejelölt opciók látható pipát kapnak. A háttér, a kártyák és a kapcsoló natív Qt rajzolással készülnek. Az OpenAI és ChatGPT jelölések a kapcsolódó szolgáltatást azonosítják; a márkák tulajdonosa az OpenAI: [arculati útmutató](https://openai.com/brand/).

A logó pontos vektoros körvonala a [Simple Icons 11.15.0 OpenAI SVG](https://cdn.jsdelivr.net/npm/simple-icons@11.15.0/icons/openai.svg) változatából származik. Az ikonadat CC0 licencű; a márkajelzés tulajdonjoga ettől változatlan.

## Működés

- Induláskor a ChatGPT webnézete látható. A felső ChatGPT gomb a beállításokból visszavált a webnézetre, és a meglévő oldalmegnyitási műveletet használja.
- A Beállítások gomb a szürke beállítási felületet nyitja meg. A Bezárás gomb és az Escape visszatér a ChatGPT webnézetéhez.
- A felső Prompt elküldése gomb a beállított kézi promptot küldi a meglévő ChatGPT-beszélgetésbe.
- Az előzmények és a profil a valódi ChatGPT beszélgetéslistájában és fiókmenüjében érhetők el.
- A beállítások megőrzik az összes korábbi kapcsolót, gyorsbillentyűt, promptot, időzítést és overlayértéket. Az állapotmező helyi menüjéből a naplómappa megnyitható.
- A natív felület alatt a böngésző munkamenete aktív marad. A fedett webnézet nem szerepel a billentyűzetes fókuszsorrendben.
- Az URL-sor eltávolítása csak a megjelenést érinti. A webes eredet ellenőrzése továbbra is korlátozza az automatizálást az engedélyezett ChatGPT oldalra.
- A böngészőprofil létrehozása előtt a program regisztrálja a Qt fő egérmutatóját. Ez javítja azt az indulási hibát, amelyben a Chromium `pointer: none` képességet tárolt, és az egérre megjelenő webes feliratok vagy menük precíz mutatóhoz kötött feltételei nem teljesültek.

A Windows címsora és ablakkezelése natív maradt. Windows 11-en a címsor és az ablakkeret a felső sávval azonos `#202020` színt, a címszöveg `#ececec` színt kap; a felső sáv külön elválasztó vonala megszűnt. A címsor színét megjelenítés és fókuszváltás után is újra alkalmazzuk. A beágyazott ChatGPT beszélgetésoldal megjelenését maga a szolgáltatás kezeli; a felső sáv és a beállítások a program saját felületei.

A tálcára rejtett, tétlen weboldal láthatatlan és `Frozen` állapotú; nincs saját újrarajzolási időzítő vagy képpontimpulzus. Betöltés, fordítás, válaszfigyelés vagy automatizálási inicializálás idejére a program felébreszti, majd az utolsó feladat lezárása után ismét felfüggeszti. Aktív mikrofon, WebRTC-kapcsolat vagy hanglejátszás közben a láthatatlanná tett lap Qt által ajánlott életciklusa `Active` maradhat; a program ezt követi, saját háttérbeli rajzolás és frissítőtimer nélkül. A média leállásakor az új ajánlott állapot alapján ismét felfüggeszti a tétlen lapot. Az előtérbe visszatérés aktiválja a lapot. A közvetlenül a ChatGPT felületén indított szöveges kéréshez nem tartozik alkalmazásszintű fordítási flag, ezért ilyen kérés közben a tálcára rejtés a weboldal JavaScriptjét is felfüggesztheti az ablak újbóli megnyitásáig.

A ChatGPT mikrofonkérését a `QWebEnginePage.permissionRequested` jelzés kezeli. A magyar `Engedélyezés` és `Tiltás` ablak a főablakhoz tartozó, nem blokkoló Qt párbeszédablak, alapértelmezett tiltással. Csak az aktuális főoldali `https://chatgpt.com` vagy `https://chat.openai.com` eredet mikrofonkérése engedélyezhető; kamerához és más webes engedélyhez nem ad hozzáférést. Oldalbetöltés, megjelenítőfolyamat-leállás vagy kilépés törli a függő kérést, és az engedélyezés pillanatában a program újraellenőrzi az eredetet. A részletek a [hangengedélyek leírásában](voice-permissions.md) szerepelnek.

Előtérben a Chromium saját kompozitora ütemezi a webes rajzolást. A korábbi, 60 ms-os saját frissítőtimer ott csak üresen ébredt, ezért eltávolítottuk ezt a szükségtelen ébresztést; ez korábban sem jelentett 16 FPS-es korlátot.

A fókuszban jelentkező egérakadás javításához a kész EXE normál indulása előtt automatikus NVIDIA-profilkezelés tartozik. A beállítások GPU-opciója alatt a `NVIDIA egérakadás javítása` kapcsoló vezérli, alapból bekapcsolt állapottal. A saját profil csak az aktuális EXE teljes útvonalára vonatkozik, és a G-SYNC/VRR alkalmazásszintű használatát kapcsolja ki. A globális és a játékokhoz tartozó beállítások megmaradnak. A kapcsoló mentése szükség esetén újraindítja a programot; új, ellenőrzött driverbeállítás után egyszer friss folyamat indul. Az NVIDIA-profilok az adott gépen maradnak; a kész EXE a létrehozásukhoz és ellenőrzésükhöz szükséges működést tartalmazza. A részletek az [NVIDIA-kompatibilitás leírásában](nvidia-compatibility.md) szerepelnek.

## Ellenőrzés és előnézet

Az előnézet külön ideiglenes beállítás- és böngészőprofillal, hálózat, Windows-vágólap és globális gyorsbillentyűk nélkül készül. A felület tényleges Qt-vezérlőinek renderelése történik. A webnézetben egyszerű helyi HTML szerepel a „ChatGPT nézet helye – offline felületi előnézet” felirattal; ez a program elrendezését mutatja, nem az élő ChatGPT oldal tartalmát. A `browser-desktop.png`, `browser-compact.png`, `settings-desktop.png` és `settings-compact.png` képek a `dist/browser-home-preview` mappába kerülnek.

```powershell
.\.venv313\Scripts\python.exe tools\preview_design.py --output dist\browser-home-preview
.\.venv313\Scripts\python.exe -m unittest discover -s tests -p test_design_ui.py -v
.\.venv313\Scripts\python.exe -m unittest discover -s tests -p test_browser_hover.py -v
.\.venv313\Scripts\python.exe -m unittest discover -s tests -v
node --test tests\test_automation.cjs
.\build.ps1 -PythonExecutable .\.venv313\Scripts\python.exe -OutputDirectory dist\staging\browser-home -SkipDependencyInstall
```

Az október 14-i, korábbi helyi EXE a `dist/staging/browser-home/Gamer Translator.exe` útvonalon készült, `5.17` alkalmazásverzióval. A build ellenőrzése minden saját Python-modul és a bejelölési SVG bájtpontos egyezését is vizsgálta. Az alábbi, külön dátumozott eredmények az adott köztes buildhez tartoznak; a v5.18 kiadás friss eredményei külön szerepelnek.

## A v5.18 kiadás ellenőrzése

Ellenőrzés dátuma: 2026. október 15.

| Ellenőrzés | Eredmény |
| --- | --- |
| Python regressziók | 419/419 sikeres, 100,374 másodperc |
| JavaScript regressziók | 55/55 sikeres |
| Csomagolt források és futtatókörnyezet | 42/42 egyezés |
| Offline EXE-önteszt | 12/12 sikeres, 55 ciklus, 64,41 másodperc, kilépési kód 0 |
| Csomagolt RapidOCR és Windows OCR | Mindkét motor: `Hello gamer` |
| Rögzített Python-függőségek friss auditja | 48 csomag, 0 ismert sérülékenység |

A kiadási build a `dist/staging/release-v5.18` mappában készült, `5.18` alkalmazásverzióval. Mérete 381 660 518 bájt, SHA-256 értéke: `52ed190d0711c90843f6c1e9d435e002ecbef9f405808ddb997959a0af0951ee`.

A korábbi kézi felhasználói próbák óta az alkalmazás forrásában kizárólag a verziószám változott; ezt a saját Python-modulok hash-összehasonlítása is ellenőrizte. A fókuszos egérakadás megszűnését, a hangbeszélgetés indulását és az első ablaknyitás helyes keretét a felhasználó korábban külön visszaigazolta. A végleges kiadási EXE új, elkülönített offline ellenőrzést kapott; az automatizált mikrofonpróba szintetikus hangforrást használ, és nem küld hangot az élő szolgáltatásba.

Az EXE Authenticode-állapota `NotSigned`. Személyes böngészőprofil, bejelentkezési adat, NVIDIA-tulajdonnyilvántartás és futásidejű napló nem része a csomagnak. A tartalommentes [kiadásellenőrzési állomány](evidence/release-v5.18-checks.json) a végleges buildhez tartozik; az alábbi külön dátumozott szekciók a korábbi köztes és kiadási ellenőrzések történeti eredményei.

## Az első ablaknyitás szegélyméretének ellenőrzése

Ellenőrzés dátuma: 2026. október 14.

Az első megnyitáskor a webnézet teljes méretű volt, de a fölötte rajzolt szegély és a beállításréteg a gyermekvezérlők kezdeti 640 × 480 képpontos méretén maradt. A főablak első méretváltozási eseménye még a tartalmi panel végleges layoutja előtt futott; a minimalizálás utáni visszaállítás újrarendezése ezért átmenetileg megszüntette a hibát.

A tartalmi panel saját `Resize` és `Show` eseményei most annak aktuális téglalapja alapján frissítik a rétegeket. Nincs hozzá folyamatos időzítő. Az elkülönített, hálózat nélküli valódi Qt-ablakpróba normál első `show()` hívást használ, kézi átméretezés vagy tálcára rejtés nélkül.

| Ellenőrzés | Eredmény |
| --- | --- |
| Első megjelenítés és szülőlayout változása | 2/2 regresszió sikeres; mindkettő hibát jelzett a korábbi kódon |
| Első tartalmi méret | A panel, a szegély és a beállításréteg 1644 × 788; a webnézet 1640 × 784 |
| Fejléc 37 képpontos növelése | Változatlan 1680 × 900 főablak mellett a panel és mindkét réteg 1644 × 751 méretre igazodik |
| Tétlen eseményfeldolgozás | A layout-hívások száma 20 tétlen kör után is 5; a szülőlayout változása után 6, újabb 20 tétlen kör után is 6 |
| Egymásba ágyazott layout-hívások | Legfeljebb 1; esemény-visszacsatolás nem keletkezett |

A próba privát profilt, blokkolt hálózatot és helyettesített natív integrációkat használt. Nem nyitott élő mikrofont, nem kezelt NVIDIA-profilt és nem vizsgálta az élő ChatGPT-beszélgetést. A hangengedély és a bevált NVIDIA-beállítás korábbi eredményei külön ellenőrzésekhez tartoznak. A tartalommentes eredmények az [ellenőrzési állományban](evidence/startup-geometry-checks.json), a nyers geometria- és eseményadatok a helyi `dist/startup-geometry-preview/event-filter-probe.json` fájlban szerepelnek.

| Az elkészült helyi program ellenőrzése | Eredmény |
| --- | --- |
| Python regressziók | 419/419 sikeres, 99,633 másodperc |
| JavaScript regressziók | 55/55 sikeres |
| Csomagolt források és futtatókörnyezet | 42/42 egyezés |
| Offline EXE-önteszt | 12/12 sikeres, 9 ciklus, 14,34 másodperc, kilépési kód 0 |
| Felhasználói első megnyitás | A keret az első indításkor is helyes |

A csomagolt RapidOCR és Windows OCR motor a helyi modellekkel egyaránt a várt `Hello gamer` szöveget ismerte fel. Az ellenőrzött köztes EXE 381 661 141 bájt volt. SHA-256: `9679b08b10b24df060dc3696c8314d0f806b9efd88211df3a13c4114ea092400`. Az ellenőrzéskor azonos hashű fájl volt a `dist/staging/startup-geometry/Gamer Translator.exe` buildútvonalon és a futó program helyén, `dist/staging/rounded-browser/Gamer Translator.exe` néven. A futó program fájlja atomikus cserével frissült.

A felhasználó kilépett a korábbi programból, majd a javított EXE friss első indítása után visszajelezte: „Igen, az első megnyitáskor is helyes”. Ez a normál alkalmazás első megnyitásának külön, felhasználó által megerősített kézi ellenőrzése; a regressziókban nem használtunk minimalizálást vagy más helyreállító műveletet.

## A ChatGPT főoldalt használó helyi módosítás ellenőrzése

Ellenőrzés dátuma: 2026. október 14.

| Ellenőrzés | Eredmény |
| --- | --- |
| Python regressziók | 337/337 sikeres, 96,577 másodperc |
| Ebből felületi regresszió | 11/11 sikeres |
| Ebből böngészős egérregresszió | 5/5 sikeres; az indulási próba külön folyamatban fut |
| JavaScript regressziók | 55/55 sikeres |
| Forrás-, asset- és futtatókörnyezet-egyezés a helyi EXE-ben | 40/40 sikeres |
| A helyi EXE offline öntesztje | 12/12 sikeres, 9 ismételt ciklus, három képes és egy szöveges kérés, kilépési kód 0 |
| UI-render | Böngészőnézet és beállítások 1672 × 900 és 1080 × 720 méretben |

A csomagolt RapidOCR és Windows OCR a helyi, hash-ellenőrzött modellekkel egyaránt a várt `Hello gamer` szöveget ismerte fel. A felületi próbák ellenőrzik az alapból látható teljes szélességű böngészőt, a saját navigáció és URL-sor hiányát, a beállítások bezárását és a háttérgazdából visszatérést. Az előnézet szoftveres rajzolással készül; ez a külön folyamat beállítása, az alkalmazás GPU-opcióját nem módosítja.

Az egérhiba külön Windows-folyamatban reprodukálható volt a változatlan v5.17 forrásával: az első profilban a `pointer:fine` hamis, a `pointer:none` igaz maradt, noha megbízható, `mouse` típusú egéresemények érkeztek. A precíz mutatóhoz kötött CSS-felirat és JavaScript-menü ezért nem jelent meg. A javított forrással a besorolás és mindkét megjelenés helyreállt; az új indulási regresszió a korábbi változatnál megbukik, a javítással sikeres. A használt [Qt-függvény](https://doc.qt.io/qt-6/qpointingdevice.html#primaryPointingDevice) szükség esetén létrehozza a fő virtuális egéreszközt.

Az élő, anoním ChatGPT-oldalon GPU-val és GPU nélkül is igazoltuk a helyes precízmutató-besorolást. Az összehúzott oldalsáv és az Új chat ikon hover-háttere az előzetes egérregisztrálással megjelent, majd az egér távozásakor eltűnt. A bejelentkezett felület konkrét Home-feliratát és menüjét ez az anoním vizsgálat nem ellenőrizte; a felirat és menü regresszióját a helyi mintalap fedi le.

Helyi EXE mérete: 381 634 911 bájt. SHA-256: `6f6d3b2a376533b1128235dfedd8d38d2ba164123838159790585aab6c952568`.

A nyers eredmények a `dist/browser-home-preview` mappában, a build-manifest a `dist/staging/browser-home` mappában található. A tartalommentes [ellenőrzési állomány](evidence/browser-home-checks.json) rögzíti a részletes eredményeket.

## A lekerekítés, natív fejléc és háttérműködés korábbi ellenőrzése

Ellenőrzés dátuma: 2026. október 14.

Az alábbi adatok az automatikus NVIDIA-profilkezelés beépítése előtti helyi EXE-hez tartoznak. A frissebb build ellenőrzése a következő szekcióban szerepel.

| Ellenőrzés | Eredmény |
| --- | --- |
| Python regressziók | 348/348 sikeres, 95,751 másodperc |
| JavaScript regressziók | 55/55 sikeres |
| Felületi és egérregressziók | 11/11 és 5/5 sikeres |
| Böngésző-életciklus | 17/17 sikeres; ebből 6 korábbi navigációs és megszakítási próba |
| Sarokrender | Mind a négy sarok megfelelő színű, két ablakméretben, beállításokból és háttérből visszatérve |
| Windows címsor | Az öt tényleges DWM-beállítás S_OK eredményt adott a külön Windows 11 próbaablakon |
| Csomagolt források és futtatókörnyezet | 40/40 egyezés |
| Offline EXE-önteszt | 12/12 sikeres, 9 ciklus, mindkét OCR-motor: `Hello gamer`, kilépési kód 0 |

A külön, GPU-gyorsított Windows böngészőpróba 239,76 Hz-es monitort és valódi ANGLE/RTX 3080/Direct3D11 renderert érzékelt. A webes animáció és a háttérből visszatérő animáció körülbelül 60 FPS-sel futott. A teljes, körülbelül 5,3 másodperces fagyasztott szakaszban nem érkezett új `requestAnimationFrame` képkocka. A rövid offline CPU-mintában a saját folyamatfa háttérterhelése 0,434%-ról 0,043%-ra változott; ez nem általános játék- vagy ChatGPT-teljesítménymérés. A Qt offscreen kompozitora és a [Chromium alapértelmezett BeginFrame-intervalluma](https://raw.githubusercontent.com/chromium/chromium/140.0.7339.225/components/viz/common/frame_sinks/begin_frame_args.h) magyarázatot adhat a 60 Hz-es mintára, de a tényleges fizikai egérkésés okát ez nem bizonyítja.

A kezdeti, csak olvasásra szolgáló NVIDIA-profilvizsgálat globálisan teljes képernyős G-SYNC módot talált; az ablakos mód nem volt engedélyezve. A Chrome saját előre definiált profiljában a VRR alkalmazásszintű override `FORCE_OFF`, a Gamer Translatorhoz nem találtunk külön profilt. A [hivatalos SDK-definíciók](https://github.com/NVIDIA/nvapi/blob/main/NvApiDriverSettings.h) alapján ez mérhető eltérés, a fókuszos egérakadás okát azonban nem igazolja.

A felhasználó külön jóváhagyása után létrehoztuk a `ColorsASD Gamer Translator – steady refresh` NVIDIA-tesztprofilt kizárólag a fenti `rounded-browser` EXE teljes útvonalára. Egyetlen helyi értéket kapott: `VRR_APP_OVERRIDE_ID` (`0x10A879CF`) = `1`, `FORCE_OFF`. Új NVAPI session igazolta az 1 alkalmazást, 1 helyi beállítást és a saját profilból érvényesülő értéket. A globális és a Chrome referenciaértékek egyeznek a művelet előtti állapottal; az azonos nevű korábbi `browser-home` EXE továbbra sem kap profilt. A program ezután szabályos kilépési kéréssel újraindult. A felhasználó a fókuszban lévő, 10–15 másodpercig tétlen oldalnál végzett egérpróba után megerősítette: „Megszűnt az akadás”. Ez felhasználói kézi ellenőrzés; műszeres egérkésés- vagy játék-FPS-mérés nem történt. A bevált kézi profil megmarad ehhez a helyi EXE-hez. A visszaállító script és a létrehozás előtti tranzakciós állapotmentés a helyi `dist/rounded-browser-preview` mappában található. Ez a korábbi kézi próba helyi driverbeállítása; a később beépített automatikus profilkezelés külön működését az [NVIDIA-kompatibilitás leírása](nvidia-compatibility.md) rögzíti.

A korábbi helyi EXE a `dist/staging/rounded-browser/Gamer Translator.exe` útvonalon készült, 381 639 784 bájt mérettel. SHA-256: `4e3c02f82dd2a6ba91c9b01c86bc176703bf058e49ea93589401a9769d5ce1d1`. A tartalommentes [ellenőrzési állomány](evidence/rounded-browser-checks.json) és a `dist/rounded-browser-preview` nyers jelentései ezt a korábbi állapotot rögzítik. Ezen az útvonalon azóta újabb helyi EXE található; az első megnyitás javításának friss eredményei fent külön szerepelnek.

## A beépített NVIDIA-profilkezelés ellenőrzése

Ellenőrzés dátuma: 2026. október 14.

| Ellenőrzés | Eredmény |
| --- | --- |
| Python regressziók | 391/391 sikeres, 96,292 másodperc |
| Ebből NVIDIA-profilkezelés | 28/28 sikeres, elkülönített driver-adatbázismintával |
| Ebből NVIDIA-indulási integráció | 12/12 sikeres |
| Ebből felületi regresszió | 14/14 sikeres |
| JavaScript regressziók | 55/55 sikeres |
| Csomagolt források és futtatókörnyezet | 41/41 egyezés |
| Offline EXE-önteszt | 12/12 sikeres, 9 ciklus, 14,414 másodperc, kilépési kód 0 |
| Valódi NVIDIA-profil és normál EXE-indulás | 3/3 kör sikeres: létrehozás, változatlan újraindítás, kikapcsolás |

A csomagolt RapidOCR és Windows OCR motor a helyi modellekkel egyaránt a várt `Hello gamer` szöveget ismerte fel. Az offline önteszt három képes és egy szöveges kérésen ellenőrizte a meglévő fordítási folyamatot; nem módosított driverprofilt.

A valódi normál EXE-próba külön alkalmazásadat-mappát és a `dist/staging/portable-nvidia/Gamer Translator.exe` teljes útvonalát használta. Kezdetben sem alkalmazásbejegyzés, sem saját profil nem létezett. Az első indítás `applied`, `changed: true`, `verified: true` eredményt adott, majd egyszer újraindult, és a friss folyamat `already_applied` állapottal nyitotta meg az ablakot. A következő indítás nem mentett és nem indult újra. Kikapcsolva a saját profil `restored` állapottal megszűnt, egyszer friss folyamat indult, és az új NVAPI session az alkalmazásbejegyzés és profil hiányát igazolta. Mindhárom ablak szabályos kilépési kéréssel bezárult, az alkalmazásnapló kilépési kódja 0 volt, és az operációs rendszerben megszűnt a folyamat.

A profilpróba előtt és után frissen kiolvasott három globális VRR-referenciaérték és a Chrome alkalmazásszintű override értéke egyezett. A korábbi `steady refresh` kézi profil megmaradt. Ez a profilkezelés és az indulási folyamat tényleges, helyi NVIDIA-ellenőrzése; új műszeres egérkésés- vagy játék-FPS-mérés nem történt.

Az akkor ellenőrzött EXE 381 655 865 bájt volt. SHA-256: `54df976c8ae66b8cdc10cefc211cb1e78659153bf93a1a360734dd704ad66eae`. Az ellenőrzéskor azonos fájl volt a `dist/staging/portable-nvidia/Gamer Translator.exe` buildútvonalon és a korábbi program helyén, `dist/staging/rounded-browser/Gamer Translator.exe` néven. Az utóbbi útvonal megőrzi a bevált kézi NVIDIA-profil hozzárendelését; a beépített automatikus kezelés azt sikeres meglévő beállításként kezeli.

A részletes működés az [NVIDIA-kompatibilitás leírásában](nvidia-compatibility.md), a tartalommentes eredmények az [ellenőrzési állományban](evidence/nvidia-compatibility-checks.json) szerepelnek. A nyers helyi jelentések a `dist/nvidia-compat-preview` mappában találhatók. A GitHubon közzétett v5.17 korábbi kiadási adatai alább külön szerepelnek.

## A v5.17 kiadás korábbi ellenőrzése

Az alábbi eredmények a 2026. október 14-én közzétett v5.17 kiadáshoz tartoznak, amely még a saját kezdőlapot és bal oldali navigációt tartalmazta. Ezek a korábbi kiadás ellenőrzési adatai; a fenti, ChatGPT főoldalt használó helyi módosítás friss eredményeit az előző szekció tartalmazza.

| Ellenőrzés | Eredmény |
| --- | --- |
| Python regressziók | 340/340 sikeres, 92,740 másodperc |
| Ebből új felületi regresszió | 19/19 sikeres |
| JavaScript regressziók | 55/55 sikeres |
| Forrás-, asset- és futtatókörnyezet-egyezés a kész EXE-ben | 40/40 sikeres |
| A kész EXE offline öntesztje | 12/12 sikeres, 55 ismételt ciklus, három képes és egy szöveges kérés, kilépési kód 0 |
| Python/JavaScript szintaxis, függőségek, Git whitespace | Sikeres |
| Tényleges UI-render | Kezdőlap és beállítások, 1672 × 900 és 1080 × 720 méretben |

EXE mérete: 381 647 753 bájt. SHA-256: `64a57db01b1ef1311df60000255da0c8434489e7661ca8c77097f78d99e79983`.

A korábbi kiadás nyers helyi jelentései a `dist/design-preview` mappában, a build-manifest a `dist/staging/gray-design-v5.17` mappában található. Az akkori önteszt nem indított hálózati kérést vagy natív gyorsbillentyűt. A csomagolt RapidOCR és Windows OCR motor a hash-ellenőrzött helyi modellekkel egyaránt a várt `Hello gamer` szöveget ismerte fel. A kiadáskor végzett függőségaudit 48 rögzített Python-csomagban nem talált ismert sérülékenységet. A verziózás után 9 indulási diagnosztikai teszt is sikeres volt. A tartalommentes [kiadásellenőrzési állomány](evidence/design-checks.json) rögzíti a korábbi kiadás részletes eredményeit.
