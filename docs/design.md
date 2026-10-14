# Szürke felület

Dátum: 2026. október 14.

Alkalmazásverzió: `5.17`.

## Referenciák és felépítés

A kezdőlap és a beállítások a két megadott Gamer Translator mintaképet követik. Az eredeti képek 1672 × 941 képpontosak, a Windows címsorával együtt. A natív alkalmazás tartalmi ablaka 1680 × 900 képpontos alapméretet kapott, 1080 × 720 képpontos minimummal.

- Fent 82 képpontos állapotsáv, ChatGPT, Beállítások és Prompt elküldése gomb.
- Az aktuális webes eredet külön sorban, személyes URL-paraméterek nélkül.
- Balra 96 képpontos navigáció: Kezdőlap, Előzmények, Felfedezés, Profil és Egyebek.
- A kezdőlapon Chat/Work választó, középre rendezett üdvözlés, 930 képpontig széles kapszula alakú beviteli sor és négy ajánlókártya.
- A háttérben felbontástól független görbék és halvány kontrollerrajz; a mintán szereplő szlogenek és Erik üdvözlőszövege.
- A beállításoknál balra az általános kártya, jobbra a gyorsbillentyűk és az overlay. A mentés és visszaállítás állandó alsó sávban érhető el.
- 1200 képpontnál keskenyebb tartalmi panelen a beállítások egy oszlopba rendeződnek és függőlegesen görgethetők.
- Alacsony ablaknál a kezdőlap betűméretei, logója és térközei csökkennek, hogy a beviteli sor és mind a négy kártya elérhető maradjon.

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

A felület Segoe UI betűkészletet, világos vonalikonokat, kerekített kártyákat és szürke kapcsolókat használ. A bejelölt opciók látható pipát kapnak. A háttér, a navigáció, a kártyák és a kapcsoló natív Qt rajzolással készülnek. Az OpenAI és ChatGPT jelölések a kapcsolódó szolgáltatást azonosítják; a márkák tulajdonosa az OpenAI: [arculati útmutató](https://openai.com/brand/).

A logó pontos vektoros körvonala a [Simple Icons 11.15.0 OpenAI SVG](https://cdn.jsdelivr.net/npm/simple-icons@11.15.0/icons/openai.svg) változatából származik. Az ikonadat CC0 licencű; a márkajelzés tulajdonjoga ettől változatlan.

## Működés

- A Chat mód változatlan kérdésszöveget küld a meglévő ChatGPT-beszélgetésbe, majd megnyitja a webnézetet.
- A Work mód a meglévő gyors chat fordítási folyamatát használja, és megmutatja a beszélgetést. A sikeres fordítás után törli a kezdőlap beviteli mezőjét; hibánál a szöveg megmarad.
- A játékfordítás-kártya Work módra vált és a fordítandó szöveg bevitelére fókuszál. A többi kártya szerkeszthető kérdéskezdést illeszt be. A kártyák önmagukban nem küldenek üzenetet.
- A plusz menü a meglévő, engedélyezett képkivágási fordítást indítja.
- A mikrofon gomb a ChatGPT webnézetére vált, ahol a szolgáltatás saját hangbevitele indítható.
- A modellgomb a ChatGPT oldalát nyitja meg; a referencia Pro-felirata helyén a szolgáltatás neve szerepel.
- Az előzmények és a profil a valódi ChatGPT beszélgetéslistájában és fiókmenüjében érhetők el.
- A beállítások megőrzik az összes korábbi kapcsolót, gyorsbillentyűt, promptot, időzítést és overlayértéket. Az állapotmező helyi menüjéből a naplómappa megnyitható.
- A natív felület alatt a böngésző munkamenete aktív marad. A fedett webnézet nem szerepel a billentyűzetes fókuszsorrendben.

A Windows címsora és ablakkezelése natív maradt. A beágyazott ChatGPT beszélgetésoldal megjelenését maga a szolgáltatás kezeli; a referencia szerinti kezdőlap és beállítások a program saját felületei.

## Ellenőrzés és előnézet

Az előnézet külön ideiglenes beállítás- és böngészőprofillal, hálózat, Windows-vágólap és globális gyorsbillentyűk nélkül készül. A felület tényleges Qt-vezérlőinek renderelése történik; a képek a `dist/design-preview` mappába kerülnek.

```powershell
.\.venv313\Scripts\python.exe tools\preview_design.py
.\.venv313\Scripts\python.exe -m unittest discover -s tests -p test_design_ui.py -v
.\.venv313\Scripts\python.exe -m unittest discover -s tests -v
node --test tests\test_automation.cjs
.\build.ps1 -PythonExecutable .\.venv313\Scripts\python.exe -OutputDirectory dist\staging\gray-design-v5.17 -SkipDependencyInstall
```

Az elkülönített EXE a `dist/staging/gray-design-v5.17/Gamer Translator.exe` útvonalon készül. A build ellenőrzése minden saját Python-modul és a bejelölési SVG bájtpontos egyezését is vizsgálja. A tényleges, bejelentkezett ChatGPT-fiók és játék közbeni használat külön kézi próbát igényel.

Végső helyi eredmények, 2026. október 14.:

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

A nyers helyi jelentések a `dist/design-preview` mappában, a build-manifest a `dist/staging/gray-design-v5.17` mappában található. Az önteszt nem indított hálózati kérést vagy natív gyorsbillentyűt. A csomagolt RapidOCR és Windows OCR motor a hash-ellenőrzött helyi modellekkel egyaránt a várt `Hello gamer` szöveget ismerte fel. A friss függőségaudit 48 rögzített Python-csomagban nem talált ismert sérülékenységet. A verziózás után 9 indulási diagnosztikai teszt is sikeres. A tartalommentes [kiadásellenőrzési állomány](evidence/design-checks.json) rögzíti a részletes eredményeket.
