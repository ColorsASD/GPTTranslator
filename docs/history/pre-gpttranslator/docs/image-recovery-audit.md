# Képküldési helyreállítás vizsgálati jelentése

Ellenőrzés dátuma: 2026. október 15. Javított forrásverzió: `6.0`. Kiinduló commit: `fdfd598`.

## A hiba vizsgálata

A felhasználó az `Alt + C` után időnként elmaradó képküldést jelzett, különösen terhelés alatt. A kérés szerint az elakadt előkészítést a már elkészült képből kell újraindítani; a beszélgetésben már megjelent képes kérés válaszát végig kell várni.

A friss helyi napló a korábban futtatott `5.18` alkalmazásból származik. A hat megmaradt naplófájl 102 435 bejegyzést tartalmazott a 2026. október 15. 01:47:53.957 és 01:48:04.756 közötti, 10,799 másodperces időszakból. Ebben 15 193, egyenként 5000 ms-nak jelzett JavaScript-időtúllépés, 11 828 ismételt eredménylekérdezés és 57 603 Qt-figyelmeztetés szerepelt. Az ismétlésszámláló 58 891-ig jutott. A háttéríró túlterhelődése miatt további 51 405 eldobott naplóbejegyzést jelzett.

Ez a bizonyíték a megszaladó ellenőrzést igazolja. A naplórotációból a kérés eleje, a képcsatolás és a chatben megjelenés eseményei már hiányoztak. A Qt-üzeneteknek csak a típusa és hossza szerepel a naplóban, ezért az eredeti figyelmeztetés pontos szövege és a kép tényleges beküldése ezekből nem állapítható meg.

A forrásban külön igazolható kilépési rés volt: a kilépés és újraindítás már az `exit_requested` állapot beállítása után megszakíthatja a beágyazott Qt eseményhurkokat, miközben az ellenőrzés még csak az `operations_cancelled` állapotot figyelte. Az idő előtt visszatérő eseményhurok tényleges időzítőlejárat nélkül is JavaScript-időtúllépésnek számított, és újabb lekérdezést indíthatott.

## Javított működés

- Az automatikus képküldés legfeljebb három teljes próbálkozást végez. Az egyszer elkészített képfájl minden próbálkozásban ugyanabból a mentett képadatból származik; a helyreállítás nem olvassa újra a vágólapot és nem indít képkivágót.
- A csatolás, az esetleges prompt és a beküldés előkészítése is újraindulhat. A korábbi felhasználói és assistant üzenetek alapállapota az első tényleges beküldés előtt rögzül, és az ismétlések alatt megmarad.
- A beviteli mező kiürülése, a csatolmány eltűnése és a küldésgomb letiltása önmagában nem igazolja, hogy a kép bekerült a beszélgetésbe. A program külön, legfeljebb nyolc másodperces visszaigazolási ablakban figyeli az új képes felhasználói üzenetet vagy az ahhoz kapcsolt új assistant működését.
- A visszaigazolt képes kérés után nincs új csatolás vagy újraküldés; a meglévő válaszvárás és késői válaszfigyelés folytatódik. Új, de még felhasználói kéréshez nem köthető assistant megjelenése is megállítja az újraküldést, miközben a kész fordítás elfogadásához továbbra is szükséges a kérésazonosság.
- Új próbálkozás előtt csak az aktuális művelet saját fájlkiválasztása, promptja és igazoltan saját csatolmányelőnézete távolítható el. Az eltávolítás az oldal saját csatolmánytörlő gombját használja, és megvárja a törlés visszaigazolását. Elérhetetlen törlőgomb vagy bizonytalan tulajdon esetén hiba jelzi a leállást.
- A már meglévő kézi piszkozat, idegen csatolmány vagy a művelet közbeni kézi szerkesztés megállítja az automatikus helyreállítást. A program saját promptbeillesztése külön, csak a szinkron művelet idejére kap kivételt.
- A megszakítás minden helyreállítási lépésre érvényes. A három sikertelen teljes próbálkozás után a művelet hibával lezárul; nincs korlátlan újrapróbálás.
- A natív időkeret külön tartalékot biztosít az előkészítés ismétléseire, hogy azok ne fogyasszák el a visszaigazolt kérés teljes válaszvárását.
- Az indítás natív visszahívásának késése nem indít második kézbesítést, és nem szakítja meg a már esetleg beküldött képet. A program ugyanannak az eredeti műveletnek az eredményét figyeli tovább; ezt külön valódi Qt/Chromium-próba ellenőrzi késleltetett visszahívással és egyetlen tényleges beküldéssel.
- A JavaScript-visszahívás csak a saját időzítőjének tényleges lejáratakor számít időtúllépésnek. A korán megszakadt eseményhurok külön hibát ad, a kilépési kérés megszakításnak számít. A böngészőművelet és a rövid Qt-várakozás ellenőrzi a GUI szálat is.
- A helyreállítás próbálkozásai, a saját piszkozat törlése, a visszaigazolás és az újrapróbálás blokkolásának oka tartalommentes naplóeseményt kap.

## Ellenőrzés

| Ellenőrzés | Eredmény |
| --- | --- |
| Teljes Python regresszió | 435/435 sikeres, 119,839 másodperc |
| JavaScript regresszió | 69/69 sikeres |
| Képküldési helyreállítás valódi Qt/Chromium motorral | 6/6 sikeres; a Python-csomag része |
| Modern üzenetfelület valódi Qt/Chromium motorral | 17/17 sikeres; a Python-csomag része |
| Natív visszahívás, polling és eseményhurok | 21/21 sikeres; a Python-csomag része; késői indítási visszahívással is egyetlen beküldés |
| EXE forrás- és futtatókörnyezet-egyezése | 42/42 sikeres |
| Csomagolt EXE offline önteszt | 12/12 ellenőrzés sikeres, 9 gyorsfordítási ciklus, 3 modern képes és 1 modern szöveges kérés, 14,193 másodperc |
| Csomagolt OCR motorok | RapidOCR és Windows OCR egyaránt pontosan a szintetikus `Hello gamer` szöveget adta vissza |
| Függőség- és szintaxisellenőrzés | `pip check`, `compileall`, `node --check` és `git diff --check` sikeres |

A hat új Chromium-integráció külön ellenőrzi a vissza nem igazolt feltöltés megismétlését, a chatüzenet nélküli composerürülést, a saját csatolmányelőnézet törlését, a hárompróbás végleges leállást, a későn megjelenő képes kérés átengedését és a lassú válasz kivárását. A böngészőben ténylegesen beolvasott képbájtok minden ismétlésnél az eredeti mintával egyeznek. A régi üzenetfelismerési negatív próbák továbbra is elutasítják a hibás szerepjelölőt, rejtett képet és újrarajzolt régi választ.

A végleges EXE mérete `381665989` bájt, SHA-256 ellenőrzőösszege: `da6a53720db8f5a8000df9f1cc9d1661800ed78cb3bac36a5d44e9ef270e3b6d`. A helyi alkalmazásmásolat `C:\Saját\Alkalmazások\Gamer-Translator-v6.0.exe`; a staging és az alkalmazásmappába másolt fájl ellenőrzőösszege egyezik. Az alkalmazás normál profilos indítása nem része ennek az ellenőrzésnek.

A tartalommentes eredményösszesítés az [ellenőrzési állományban](evidence/image-recovery-checks.json) található. A részletes tesztkimenetek és a csomagmanifest a helyi `dist\staging` könyvtárban maradnak.

## Az ellenőrzés határai

A későbbi, ugyanazon a napon végzett élő `6.0` vizsgálat a ChatGPT magyar felületén ismételt elakadást igazolt. A `22:37:26`-kor indult kép feltöltése elkészült, az új kép és a kész fordítás a futó ablakban látható volt, de a program az `Ezt mondtad:` fejlécet nem ismerte fel felhasználói szerepként. Emiatt `request_user_unbound` állapotban kivárta a 180 másodperces válaszhatáridőt; a következő képek sorban maradtak, és a promptgomb foglalt állapotot jelzett. A futó ablak saját fejlécei az olvasó accessibility-vizsgálatban `Ezt mondtad:` és `A ChatGPT válasza:` alakban szerepeltek. A felhasználó az angol ChatGPT-felület használatát választotta; a megkezdett magyar felismerési módosítás vissza lett vonva. A jelenlegi változat képes működése ezért angol ChatGPT-felületet igényel. Ez a felületi nyelv korlátja, a fordítás célnyelve továbbra is lehet magyar.

A regressziók helyi, hálózattól elzárt DOM-mintákkal és elkülönített böngészőprofillal futnak. A képküldési integráció valódi Qt/Chromium motort és a képfájl tényleges bájtjait használja. Bejelentkezett ChatGPT-kérés, játék közbeni fizikai gyorsbillentyű és játékbeli teljesítménymérés nem része az automatikus ellenőrzésnek.

A webes DOM önmagában nem bizonyítja egy minden látható jel nélkül, csak a visszaigazolási ablak után elfogadott szerveres kérés kimenetelét. Az új felhasználói kör és assistant működésének ellenőrzése csökkenti a duplikálás veszélyét; abszolút szerveroldali egyszeri feldolgozást a webes felület automatizálása nem garantál.

Személyes profil, képtartalom, beszélgetésszöveg és teljes futásidejű napló nem kerül a repository-ba.
