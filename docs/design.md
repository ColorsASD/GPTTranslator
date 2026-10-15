# Szürke felület

Alkalmazásverzió: `6.0`.

## Jelenlegi felépítés

A program főoldala közvetlenül a beágyazott `chatgpt.com` oldal. A szürke felső állapotsáv és a beállítások a megadott mintaképek stílusát követik. Az eredeti képek 1672 × 941 képpontosak, a Windows címsorával együtt. A natív alkalmazás tartalmi ablaka 1680 × 900 képpontos alapméretet kapott, 1080 × 720 képpontos minimummal.

- Fent 82 képpontos állapotsáv, ChatGPT, Beállítások és Prompt elküldése gomb.
- A ChatGPT webnézete a felső sáv alatti teljes tartalmi szélességet használja.
- A webnézet 19 logikai képpontos maszkolása és az élsimított, 20 képpontos külső szegély együtt követi a keret sarokívét, az első ablaknyitásnál, átméretezés és háttérből visszatérés után is.
- A webnézet szegélye és a beállításréteg a tartalmi panel tényleges méretéhez igazodik. A panel megjelenítési és méretváltozási eseményei frissítik a rétegeket akkor is, ha a főablak mérete nem változik.
- A külön URL-sor és a program saját bal oldali navigációja eltávolítva. A saját kezdőlap, Chat/Work beviteli sor és ajánlókártyák helyét a ChatGPT oldala veszi át.
- A beállításoknál balra az általános kártya, jobbra a gyorsbillentyűk és az overlay. A mentés és visszaállítás állandó alsó sávban érhető el.
- 1200 képpontnál keskenyebb tartalmi panelen a beállítások egy oszlopba rendeződnek és függőlegesen görgethetők.
- A gyors chat a főfelület natív, semleges szürke paneljét, visszafogott hullámait és ChatGPT ikonját használja. A legfeljebb 860 logikai képpontos panelen felül a cím és a bezárás, középen a lekerekített szövegmező, alul a billentyűs súgó és a világos küldésgomb látható. Keskeny nézetben a küldésgomb külön sorba kerül; kisebb magasságnál a margó és a szövegmező minimuma csökken.

Az alkalmazás saját ikonja külön monokróm beszédbuborékot és fordítási nyilakat használ. A Windows-ikon a `gpttranslator/assets/icon.ico`, a méretezett PNG-változatok ugyanebben a könyvtárban találhatók.

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

A ChatGPT szolgáltatásjelölés pontos vektoros körvonala a [Simple Icons 11.15.0 OpenAI SVG](https://cdn.jsdelivr.net/npm/simple-icons@11.15.0/icons/openai.svg) változatából származik. Az ikonadat CC0 licencű; a márkajelzés tulajdonjoga ettől változatlan.

## Működés

- Induláskor a ChatGPT webnézete látható. A felső ChatGPT gomb a beállításokból visszavált a webnézetre, és a meglévő oldalmegnyitási műveletet használja.
- A Beállítások gomb a szürke beállítási felületet nyitja meg. A Bezárás gomb és az Escape visszatér a ChatGPT webnézetéhez.
- A felső Prompt elküldése gomb a beállított kézi promptot küldi a meglévő ChatGPT-beszélgetésbe.
- Az előzmények és a profil a valódi ChatGPT beszélgetéslistájában és fiókmenüjében érhetők el.
- A beállítások megőrzik az összes korábbi kapcsolót, gyorsbillentyűt, promptot, időzítést és overlayértéket. Az állapotmező helyi menüjéből a naplómappa megnyitható.
- A natív felület alatt a böngésző munkamenete aktív marad. A fedett webnézet nem szerepel a billentyűzetes fókuszsorrendben.
- Az URL-sor eltávolítása csak a megjelenést érinti. A webes eredet ellenőrzése továbbra is korlátozza az automatizálást az engedélyezett ChatGPT oldalra.
- A gyors chatben az Enter küld, a Ctrl+Enter sortörést szúr be, az Esc és a panelen kívüli kattintás bezárja az ablakot. Küldés közben a szövegmező csak olvasható, a gombok tiltottak; a folyamat és a hibák külön szürke állapotsorban jelennek meg. A háttér egyszeri képernyőkép elmosásával készül, folyamatos háttérrögzítés vagy új animációs időzítő nélkül.
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
.\.venv313\Scripts\python.exe tools\preview_design.py --quick-chat-only --output dist\quick-chat-preview
.\.venv313\Scripts\python.exe -m unittest discover -s tests -p test_design_ui.py -v
.\.venv313\Scripts\python.exe -m unittest discover -s tests -p test_browser_hover.py -v
.\.venv313\Scripts\python.exe -m unittest discover -s tests -v
node --test tests\test_automation.cjs
.\build.ps1 -PythonExecutable .\.venv313\Scripts\python.exe -OutputDirectory dist\staging\browser-home -SkipDependencyInstall
```


A korábbi felületi próbák, kiadási hash-ek és helyi EXE-útvonalak a [történeti felületi leírásban](history/pre-gpttranslator/docs/design.md) maradtak meg. Ezek az átnevezés előtti buildhez tartoznak.
