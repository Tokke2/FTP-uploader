# FTP-uploader

Python-app för Windows, macOS och Linux. Ingen virtuell miljö, BAT eller Git-installation behövs. Valfria startfiler: `Starta.vbs` för Windows och `Starta.sh` för macOS/Linux.

## Installation och start

Installera en aktuell stabil Python med Tcl/Tk från python.org. Python måste installeras innan Python-kod kan köras; appen kan inte installera Python om Python saknas.

Ladda ned projektet och packa upp det i en skrivbar mapp.

- **Windows:** öppna `start.pyw` med Pythonw för start utan konsol. Filassociationen för `.pyw` måste peka på Pythonw. Ingen separat startfil eller virtuell miljö behövs.
- **macOS/Linux:** starta `python3 start.pyw` med installerad Python. GUI kräver en grafisk session. På Linux behövs systempaketet för Tk, exempelvis `python3-tk` på Debian/Ubuntu. Start från en redan öppen terminal stänger inte terminalen.

Både `start.pyw` och `main.pyw` använder veckoschemat när appen körs.

## Sökning efter installerad Python

Startarna använder befintlig, gemensam Python med Tk-stöd, utan att skapa en egen miljö. Den nuvarande fungerande installationen prioriteras; om den inte duger provas bas-Python bakom en virtuell miljö, PATH och vanliga installationsplatser. Sökningen är lokal och kontrollerar inte versionsnyheter på nätet. Den installerar eller uppgraderar inte Python.

- **Windows:** PEP 514-registret i HKCU/HKLM och 32-/64-bitarsvyer, Python-startarens `py --list-paths`, `%LOCALAPPDATA%/Programs/Python/Python*`, `%LOCALAPPDATA%/Python/pythoncore-*`, Program Files och `C:/Python*` (systemdisken). CLI-Python verifieras och matchande Pythonw används för konsolfri start och appens genvägar. WindowsApps-alias som kan öppna installationsgränssnittet körs inte.
- **macOS:** Python Framework, `/opt/homebrew/bin`, `/usr/local/bin` och `/usr/bin`.
- **Linux:** `/usr/bin`, `/usr/local/bin`, vanliga `/opt/python*`-installationer och `~/.local/bin`.

Varje kandidat måste gå att köra, vara minst Python 3.10, ligga utanför en vanlig virtuell miljö och kunna importera Tk. Kandidater körs med isolerad probning och tidsgräns. Vid byte startas rätt tolk med samma argument, före instanslås och paketkontroll. Sökvägar loggas i appens `logs/python-discovery.log`. Saknas en användbar installation visas/rapporteras ett fel i stället för att en extra Python installeras. Veckounderhållet förblir separat.

Python måste fortfarande kunna starta själva `.pyw`-filen; Python-kod kan inte reparera en trasig Windows-filassociation innan den har börjat köras. Sökningen täcker vanliga platser, inte varje tänkbar specialinstallation eller nätverksdisk.

## Python-tillägg

Vid det schemalagda veckounderhållet kontrolleras samtliga appberoenden i `requirements.txt` med pip `install --upgrade`. Saknade paket installeras och befintliga uppgraderas till senaste stabila version som är kompatibel med aktuell Python och plattform. Plattformsberoenden filtreras för macOS/Linux. Status visas i ett fönster och fel visas/loggas i `logs/deps.log`.

Ingen virtuell miljö skapas eller krävs. Paketen installeras för den Python som startar appen; användarinstallation provas om normal installation misslyckas. Detta kan påverka andra program som använder samma Python. OS-hanterade Python-installationer kan blockera pip-installationer (PEP 668); appen kringgår inte systemets skydd. Installera då beroendena via systemets pakethanterare eller använd en separat, användarinstallerad Python.

Nätverk behövs för att verifiera senaste paketversioner. Vid fel försöker appen fortsätta med befintliga paket. Nyaste paket garanterar inte kompatibilitet med appkoden. Tk är en systemkomponent, inte ett pip-paket.

## Inställningar

Inställningar kopieras en gång från projektets `config/` till användarens mapp, utan att befintliga användarfiler skrivs över:

- Windows: `%APPDATA%\FTP-uploader\config`
- macOS: `~/Library/Application Support/FTP-uploader/config`
- Linux: `${XDG_CONFIG_HOME:-~/.config}/FTP-uploader/config`

JSON-filer och ikoner behålls eftersom appen behöver dem; programkoden och startaren är Python.

## Releaser – inga merges

**Inga grenar eller pull requests ska mergas. Appen kör inga Git-kommandon.**

Releasekontrollen använder Pythons standardbibliotek och GitHub API. Den jämför appens versionsnummer med senaste stabila GitHub Release, inte senaste commit på `main`. Taggar ska heta `vX.Y.Z` eller `X.Y.Z` (fyra versionsdelar stöds också). Prereleases/drafts används inte.

Menyn **Uppdateringar** innehåller automatisk uppdatering, fråga först (standard), avstängt och manuell sökning.
Uppdateraren laddar ner källarkivet för **den exakta publicerade release-taggen** från GitHub, aldrig `main`.
Manuell uppdatering inifrån appen laddas ned och installeras direkt när inga jobb eller kända osparade ändringar blockerar. Därefter erbjuds en avbrytbar omstart efter tre sekunder; se avsnittet om direktinstallation nedan.

Installationen använder bara Python. Den kontrollerar tagg mot `APP_VERSION`, arkivets sökvägar, storleksgränser och Python-syntax innan filer byts ut.
Programkod, `requirements.txt` och ikoner ersätts. Inställningar, exporter och andra filer lämnas orörda.
Gamla programfiler sparas under appmappens `backups/releases/`. Vid installationsfel försöker uppdateraren återställa alla ändrade filer.
Detta skyddar mot vanliga installationsfel, men inte mot strömavbrott; säkerhetskopian behålls för manuell återställning.
Gamla överflödiga programfiler tas inte bort automatiskt. Arkivet verifieras inte med en separat kryptografisk signatur.

En uppackad releaseinstallation kan uppdateras automatiskt. Utvecklingskopior med `.git` uppdateras inte, för att skydda arbetsgrenen och lokala ändringar. Ingen Git-installation behövs och inga merges görs.

Projektet behöver publicerade GitHub Releases för att kontrollen ska hitta en utgåva. Resultat loggas i appmappens `logs/update.log`. Sätt `FTP_UPLOADER_AUTOUPDATE=0` för att stoppa automatisk releasekontroll (påverkar inte pip-kontrollen).

## Tester

```sh
python -m unittest discover -s tests -v
```

GUI och konsolfri start behöver även verifieras på respektive operativsystem.

## Redigera en befintlig export

I fliken Bildgalleri: välj **Öppna export** och välj mappen som innehåller `index.html`.
Redigeraren kan lägga till bilder, ta bort markerade, flytta en bild upp/ned och ändra titel/beskrivning.
**Spara export** bygger om HTML och bildlistan utan att köra FTP-uppladdning. Minst en bild måste finnas kvar.

Nya exporter innehåller `gallery-project.json` med bildordning, galleriinställningar och egna HTML/CSS-tillägg.
Äldre standard-/flat-exporter kan läsas från bildkorten i HTML, men tema, beskrivning och egna tillägg kan behöva återskapas; en varning visas.
PDF/video tas med vid omsparning. Redigering av enskilda bildtexter och videor ingår inte i denna redigerare.

Sparning sker först i en temporär mapp. Därefter säkerhetskopieras den gamla exporten under appmappens `backups/editor/` och ersätts av den nya.
Originalbilder som läggs till ändras inte. Borttagning gäller bara den nya exporten; säkerhetskopian behåller den gamla.
Om omsparning misslyckas före utbytet är originalexporten orörd. Säkerhetskopior tas inte bort automatiskt.

## Logotyp, helskärm, tangentbordshjälp och flikpaus

- **Vattenstämpel med egen logotyp:** välj en **SVG-fil** och opacitet under bildinställningarna och markera **Inkludera vattenstämpel från SVG-logotyp**. Endast kryssrutan aktiverar märket; vald fil räcker inte. Standard är avstängt, även för äldre inställningar som bara innehåller en logotypsökväg. Avmarkerat läge försöker inte läsa logotypfilen. Logotypen placeras nere till höger, inom 20 % av bildens bredd/höjd med 3 % marginal. SVG rasteriseras med transparens för bildbearbetningen. Den appliceras efter nedskalning och före sparning, så webbilder, miniatyrer, responsiva varianter, omslag och nedskalade nedladdningar får märket. Bildprocessorn måste vara aktiverad. Källbilderna och byte-exakta originalnedladdningar ändras inte. Detta är inget kopieringsskydd.
- Kryssrutans läge, logotypens lokala sökväg och opacitet sparas i appinställningarna, inte som en privat lokal sökväg i webbprojektet. En befintlig export behåller sina redan märkta webbilder vid omsparning och får inte en andra stämpel. För att byta eller ta bort märket behöver du generera om från källbilderna. Äldre exporter får inte en ny stämpel enbart genom omsparning.
- SVG-stödet använder `resvg-py` och `defusedxml`. Använd fristående vektorgrafik, högst 2 MiB, med text omvandlad till banor. Skript, DTD/entiteter, inbäddade rasterbilder och externa fil-/nätverksreferenser tillåts inte. Ogiltig SVG när kryssrutan är på stoppar jobbet med ett fel i stället för att tyst utelämna märket.
- **Helskärm:** galleriet har en helskärmsknapp och F-kortkommando; bildspelets befintliga kontroll återanvänds. Stöd saknas i vissa webbläsare eller inbäddade visningar; knappen döljs när API saknas och avvisade anrop hanteras. Ingen automatisk helskärm begärs.
- **Tangentbordshjälp:** öppna med knappen eller **?** i både galleri och bildspel. Hjälpen beskriver kortkommandon, kan stängas med Escape och återför fokus. Kortkommandon stör inte inmatningsfält eller dialogens tangentbordsnavigering. Vissa avancerade kontroller saknas om exporten använder reservskript.
- **Paus vid flikbyte:** bildspelet avancerar inte när fliken är dold. Vid återkomst återställs tidsbasen utan att hoppa fram genom bilder; förlupen visningstid och användarens manuella pausval behålls. Bildanimationen pausas också när fliken är dold. Detta gäller både ordinarie och reservskript. Webbläsare kan begränsa bakgrundsbeteende olika.

Exportera om för att uppdatera ett äldre galleri med de nya webbfunktionerna. Desktop-/mobilwebbläsare och verklig helskärm behöver också verifieras manuellt.

## Omslagsbild och länkkontroll

I bildinställningarna och exportredigeraren väljer du **Omslagsbildens nummer i nuvarande bildordning** samt en valfri **Publicerad galleri-URL**, exempelvis `https://example.se/galleri/` eller `https://example.se/galleri/index.html`. Nummer 1 är standard. Vid ändrad ordning följer numret positionen, inte den tidigare bildfilen; kontrollera omslagsvalet efter omordning/borttagning.

Exporten får en `cover.jpg` på 1200 × 630 px. Hela den valda webbilden ryms utan beskärning eller uppskalning, med mörka marginaler där det behövs. Omslaget får ingen EXIF. När publik URL anges läggs absoluta Open Graph-/Twitter-bildtaggar till. Utan URL skapas bilden men inga bildtaggar för delning. Den publika adressen måste motsvara den verkliga exportplatsen. Delningstjänstens egen cache, åtkomlighet och presentation kan inte garanteras eller kontrolleras offline.

Varje generering och omsparning kontrollerar lokala HTML-länkar, bild-/video-/PDF-referenser, `srcset`, HTML-ankare och bildfiler i projektmanifestet, inklusive nedladdningar och omslag. Resultatet sparas som `link-report.html` och `link-report.json`. Öppna det med **Öppna länkkontroll** i inställningarna/redigeraren. Trasiga lokala länkar stoppar genereringen innan nästa pipeline-steg kan ladda upp. Vid misslyckad omsparning lämnas den tidigare exporten orörd.

Detta är en offlinekontroll: externa adresser hämtas inte, JavaScript/CSS analyseras inte generellt och korrekt serverkonfiguration eller länkdelning verifieras inte. Lightboxens syntaktiskt giltiga hash-rutter undantas från vanlig ankarkontroll. Rapporterna och omslagsfilen ingår i FTP-fillistan.

## Responsiva bilder, bildrapport och nedladdningar

Under **Inställningar → Bildinställningar** (och i **Öppna export**) finns:

- **Responsiva webbilder**, på som standard: skapar varianter med 480, 960 och 1600 pixels bredd när webbilden är större. Bildkort, lightbox och bildspel använder `srcset`/`sizes`; webbläsaren väljer fil efter visningsyta och skärmens pixeltäthet. Ingen uppskalning eller beskärning sker. Fullstor webbild finns kvar som reserv. Extra filer ökar exportens diskutrymme, även när besökaren hämtar mindre filer.
- **Besökares nedladdning**, av som standard: du väljer **Avstängd**, **1280 px**, **1920 px** (längsta sidan) eller **Originalfil** för galleriets bilder. När det är på visas en nedladdningsknapp i lightboxen med filens faktiska mått eller originalbeteckning. 1280/1920 px skapas från webbilden och kan därför bli mindre än valt tak. Avstängd tar bort knappen, men är inget kopieringsskydd.
- **Bildoptimeringsrapport**: varje export får `optimization-report.html` och `optimization-report.json`. Knappen **Öppna bildoptimeringsrapport** i inställningarna eller **Bildrapport** i exportredigeraren öppnar HTML-rapporten i webbläsaren. Den visar källa/webbstorlek, sparade bytes/procent, pixelmått och noteringar om exempelvis webbilder över 1 MiB. Miniatyrer, responsiva varianter och nedladdningsfiler redovisas separat i JSON och räknas in i totalen. Negativ besparing betyder att webbilden är större än källan, inte ett mätfel. HTML/övriga tillbehör ingår inte i bildfilstotalen.

**Integritet:** Originalfil kopieras byte för byte och kan innehålla EXIF/GPS och andra privata metadata. Välj bara detta när originalen ska publiceras. Genererade mindre varianter och nedskalade nedladdningar får ingen EXIF. Inställningen ändrar inte den befintliga hanteringen av den fullstora webbilden. Transparens behålls med PNG i de nya varianterna. Animerade filer får inga statiska varianter eller nedskalade nedladdningar; originalvalet kan däremot bevara hela filen. Den vanliga bildprocessorn kan redan ha gjort om källan till en stillbild före exporten.

Valen sparas i appinställningarna och i exportens portabla projektfil. Vid omsparning används tidigare exporterade webbilder som jämförelsekälla om inget genuint original finns kvar. **Originalfil** tillåts bara när originalet ingår i exporten eller bilden nyss lagts till från disk, aldrig genom att kalla en webbild för original. Om original saknas stoppas omsparningen med ett felmeddelande; välj då 1280/1920 px eller avstängt. Bildernas ordning och koppling till original bevaras vid redigering. När varianter/nedladdning stängs av tas gamla, numrerade filer för dessa funktioner bort ur den nya exporten; säkerhetskopian behåller dem. FTP-listan innehåller de nya filerna och rapporterna.

## Förbättrade gallerivyer

- **Appens bildgalleri:** jämnstora bildytor utan beskärning, filnamn som tooltip och tydlig bock vid markering. Sökning och formatfilter kombineras; en tom sökning visar ett meddelande i stället för att felaktigt visa alla bilder.
- **Exportredigeraren:** bläddringsbar bildlista med miniatyrer, större förhandsvisning, pixelmått och filstorlek. Ctrl/⌘ och Shift markerar flera bilder för borttagning; Upp/Ned flyttar en markerad bild i ordningen.
- **Webbgalleriet:** tydligare tangentbordsfokus, större mobilkontroller och lugnare hoverbeteende på pekskärm. Bekvämt visningsläge visar hela bilden utan beskärning och håller bildtexten synlig. Exportera om för att få de nya stilarna i en befintlig export.

Visuella GUI-tester behöver göras på en dator med Tkinter och grafisk session; de automatiska testerna täcker filtrering, layoutberäkning och CSS-regler men är inte skärmbildstester.

### Ändrad release med samma versionsnummer

Även om versionsnumret är oförändrat (t.ex. `v1.0.0`) kontrolleras commit-ID:t bakom den publicerade release-taggen.
Om taggen pekar på en annan commit än den installerade laddas den uppdaterade releasekoden ner enligt valt uppdateringsläge.
Installerat tagg-/commit-ID sparas i `.release-state.json`; en installation som saknar denna information installeras om en gång för att skapa jämförelseunderlag.
Arkivet hämtas för exakt det kontrollerade commit-ID:t, aldrig för `main`. Annoterade taggar stöds också.

För att publicera ändrad programkod under samma release måste release-taggen flyttas till den nya commiten.
Att bara ändra releasebeskrivningen eller byta uppladdade bilagor ändrar inte källarkivet och utlöser inte denna uppdatering.
Äldre versionsnummer installeras inte över nyare. Utvecklingskopior med `.git` skyddas fortfarande från installation.

## Veckokontroll måndag kl. 08.00

Automatisk kontroll och uppdatering av **appreleaser, befintlig Python och appens tillägg** sker en gång i veckan, måndag **08.00 enligt datorns lokala tid**. Den tidigare tolvtimmarskontrollen och uppgraderingen vid varje start är borttagna.
Schemat sparas i användarinställningarnas `weekly-checks.json`. Första gången planeras nästa framtida måndag kl. 08; det körs inte en kontroll bara för att appen startar.
Om appen är stängd vid den planerade tiden körs en förfallen kontroll när appen är igång igen. Ingen Windows-/OS-schemaläggare installeras och datorn väcks inte.

Kontrollen av appreleaser körs tyst i bakgrunden. Python-/paketunderhållet väntar på sparat arbete och avslutade jobb, stänger appen kontrollerat och körs i en separat Python-process innan appen startas igen.
Det innebär en underhållsomstart även om ingen ny apprelease finns. Administratörsgodkännande kan fortfarande krävas för Python-systemuppgraderingen.
Apprelease installeras automatiskt i läget **Uppdatera automatiskt**; **Fråga först** tillåter endast manuell bekräftelse av appreleasen. Veckounderhåll av Python/tillägg gäller båda lägena.
**Avstängt** eller `FTP_UPLOADER_AUTOUPDATE=0` stoppar automatiska veckokontroller och underhåll. Manuella menyval fungerar fortfarande utan att ändra veckoschemat.
Fel loggas i appmappens `logs/`. En misslyckad kontroll försöks normalt igen nästa vecka, inte vid varje omstart.

## Arbetsstatus i systray

Trayikonens tooltip och en inaktiv **Status**-rad överst i högerklicksmenyn visar **Redo**, aktuellt pipeline-steg, **Bearbetar 12/80**, **Laddar upp 4/20**, **Avbrutet** eller **Fel – se felloggen**. Räknarna visar färdigbehandlade/försökta bilder eller filer, inte procent av hela jobbet. Andra steg visar stegets namn utan en påhittad procentmätare. Detaljer om fel finns i de ordinarie loggarna, inte i tooltipen.

Status uppdateras högst fyra gånger per sekund, även när huvudfönstret är dolt. Både tray-plugin och inbyggd fallback använder samma status; omladdning av plugins bevarar den. Vid flera samtidiga pipeline-jobb visas antalet jobb och det senast startade jobbets steg tills alla är klara. Fel försvinner inte bara för att ett annat samtidigt jobb lyckas; ett nytt jobb efteråt påbörjar en ny status. Ingen extra trayikon eller automatisk fönsteröppning skapas. Detta avser jobb som körs genom appens pipeline, inte separat extern aktivitet. Operativsystemet kan begränsa tooltip-stödet; menyraden finns som alternativ när tray stöds.

## Alltid minimerad start

Appen startar alltid minimerad, även om äldre inställningar säger något annat. När en synlig trayikon finns hålls huvudfönstret dolt där. Om tray saknas, kraschar eller inte blir synlig används ett vanligt minimerat fönster i aktivitetsfältet i stället; appen ska inte bli onåbar. En ny start eller ett medvetet klick på Visa öppnar fortfarande den befintliga appen. Fördröjda startåtgärder får inte gömma fönstret igen efter ett sådant öppnande. Inställningen för minimerad start kan inte stängas av.

## Lokalt, löpande lärande

**Hjälp → Lärande och förslag** visar lokal, regelbaserad statistik som förbättrar underlaget när appen används. Detta är inte en AI som tränar om sig eller skriver om sin kod:

- Efter varje lyckad export registreras bildmapp, ett urval exportinställningar samt sammanlagda bildstorlekar och antal stora webbilder. Vanliga val/mappar föreslås utifrån de senaste 20 exporterna; bildförslag kräver minst tre observationer. Exportredigeraren registrerar först efter lyckat mappbyte.
- Bildförslag kan rekommendera att prova mindre maxstorlek/lägre kvalitet när stora filer återkommer. Ingen bildanalys eller bedömning av visuell kvalitet görs; jämför alltid visuellt. Statistik bevisar inte att en inställning är optimal.
- Återkommande öppna fel och tidigare manuella åtgärdskommentarer läses ur det befintliga felregistret. En gammal kommentar är en möjlig ledtråd, **inte en verifierad lösning**. Fel markeras aldrig automatiskt som åtgärdade. Loggträffar kan innehålla speglingar av samma fel.

Insamlingen är på som standard och sker när nya exporter görs, även medan appen är minimerad. Förslagsfönstret uppdateras var femte sekund medan det är öppet. Utan nya händelser finns inget nytt att lära. Ingen data skickas till en AI-tjänst och inga paket installeras av lärandefunktionen. Den ändrar inte bilder, källkod, uppdateringsschemat eller dina inställningar på egen hand.

Högst 200 exportobservationer lagras i användarens datamapp under `learning/observations.sqlite3`. Denna databas innehåller lokala mappsökvägar, men inte bilder, bildtitlar eller FTP-lösenord. Ordinarie felregistret kan innehålla feldetaljer som tidigare. I förslagsfönstret kan du pausa nya exportobservationer och radera exporternas inlärningshistorik. Det raderar inte det separata felregistret, ordinarie inställningar eller säkerhetskopior.

## En enda körande instans

Både `start.pyw` och direktstart av `main.pyw` tar samma instanslås **före** paketkontroll, releaseinstallation och huvudfönster. Ett nytt startförsök skickar en lokal aktiveringsbegäran till den redan körande appen och avslutas utan en extra dialog eller en andra trayikon. Den första appen visar sitt fönster även om det är minimerat eller dolt i systemfältet. En begäran under en långsam start behålls tills gränssnittet är klart. Olika arbetsmappar eller kopior av appen använder samma port, inte separata triggerfiler.

Kommunikationen använder endast loopback (`127.0.0.1:47200`), inte nätverket. Om porten är upptagen av något som inte svarar som appen startas ingen extra instans. Låset släpps vid avslut/krasch; ingen gammal låsfil behöver raderas. Operativsystemet kan begränsa förgrundsfokus; Windows-startaren överför därför förgrundsrättigheter till den befintliga processen. Funktionen behöver även provas med verklig tray/minimering på respektive operativsystem.

## Appikon och autostart på Windows

Appen har en gemensam ikon (bildram + uppladdningspil) i `icon/`: PNG för 16/32/64/256 px samt en flerstorleks-ICO.
Samma ikon används av huvudfönster, dialoger som ärver fönsterikonen, tray, Windows-genvägar och favicon i nya webbexporter.
En explicit Windows AppUserModelID skiljer appens aktivitetsfältsidentitet från Python.

Vid start på Windows skapas en vanlig Start-menygenväg **FTP-uploader** med appens ikon. Starta via den i stället för att dubbelklicka på `.pyw`-filen.
När autostart väljs skapas **FTP-uploader.lnk** i användarens Autostart-mapp. Den gamla `GalleryUploader`-posten i HKCU Run tas bort så appen inte startar dubbelt.
Båda autostartreglagen använder samma funktion. När autostart stängs av tas Autostart-genvägen bort, inte den vanliga Start-menygenvägen.

Genvägarna använder Pythonw som konsolfri motor, med appens egen ICO som synlig genvägsikon; `.pyw` registreras inte direkt för autostart.
Windows Aktivitetshanterares detaljvy kan fortfarande visa Python/Pythonw och dess exe-ikon eftersom det är den körbara processen. **100 % ersättning av Python-identiteten överallt kan inte garanteras med en ren `.pyw`-app.** Ingen delad Python-installation modifieras.

Windows filassociation för lösa `.pyw`-filer och ikonen på själva `pythonw.exe` ändras inte. Aktivitetsfält/Alt-Tab får fönstrets egen ikon.
För en separat exe-ikon eller macOS Dock-/Finder-identitet krävs en paketerad app; detta projekt skapar inte någon sådan binär.
Windows COM/genvägar och skalets ikoncache måste verifieras på en Windows-dator. Äldre fästa Python-genvägar kan behöva lossas och ersättas med appens Start-menygenväg.

### Filkontroll även när version och commit är samma

När installerad tagg och commit stämmer hämtas även GitHubs fillista för exakt den release-commiten.
Appens Python-filer, `requirements.txt` och ikoner jämförs byte för byte via Git blob-hash (beräknad i Python, utan Git-kommandon).
Saknad eller ändrad programfil utlöser ominstallation från releasen, även vid oförändrad version/commit. Tidsstämpel och filstorlek används inte som bevis på samma innehåll.
Inställningar, exporter och loggar ingår inte i jämförelsen. Lokala ändringar i själva programfilerna kan alltså återställas av automatiken i en releaseinstallation; arbetskopior med `.git` skyddas fortfarande.

Ändringar som endast finns på `main`, i ett releaseutkast eller i separat uppladdade releasebilagor används inte.
Den publicerade release-taggens källkod är uppdateringskällan. För nya källfiler under samma versionsnummer ska taggen peka på den nya commiten.

## Samlad fellogg för felsökning

**Hjälp → Öppna samlad fellogg** öppnar `<appmapp>/logs/all_errors.log` på alla operativsystem.

En bakgrundssamlare läser nya rader från `.log`-filer under appmappens `logs/` ungefär varannan sekund. Den tar med felmarkeringar, undantag och efterföljande traceback-rader. Dedikerade krasch-, stderr-, launcher- och errors-loggar samlas också in. Befintliga historiska loggar läses in stegvis första gången.

Varje rad innehåller insamlingstid, full sökväg till källoggen och originaltext (inklusive ursprunglig tidsstämpel om sådan finns). Det är insamlingsordning, inte en omsortering av alla historiska händelser. Samma fel kan förekomma från flera källoggar när appen redan speglar felet; källorna behålls för spårbarhet.

Läspositioner sparas i `.all_errors-cursors.json`, så tidigare lästa loggar normalt inte läses om vid omstart. Avkortade/utbytta källoggar upptäcks och läses från början. Samlaren läser aldrig in sin egen logg. Originalens loggskrivare ändras inte och deras filer lämnas kvar.

Den samlade loggen roteras vid cirka **5 MB**, med **tre äldre filer** (`all_errors.log.1`–`.3`). Mycket långa enskilda felrader kan överskrida gränsen. Saknas loggmappen eller är en fil tillfälligt oläsbar påverkas inte appens normala arbete. Startfel via `start.pyw` samlas även in innan startarens felruta visas.

Textbaserad insamling kan bara fånga fel som faktiskt skrivs till en logg och känns igen som fel; tyst bortfångade undantag utan loggning kan inte återskapas. Kontrollera innehållet innan du delar felloggen: ursprungsloggar kan innehålla privata filnamn, serveradresser eller andra känsliga uppgifter.

## Gemensam loggmapp i appen

All ny loggning går till **`logs/` direkt under appmappen**, oavsett vilken arbetskatalog appen startas från.
Det gäller startup, launcher, beroendeinstallation, uppdateringar, stderr/krascher, pluginloggar och `all_errors.log` inklusive dess rotation och läspositionsfil.
**Hjälp → Öppna loggmapp** öppnar samma mapp. Inga alternativa loggmappar i aktuell arbetskatalog används om loggmappen inte är skrivbar.
Appen måste därför ligga i en skrivbar mapp. Inställningar ligger fortsatt i användarens inställningsmapp.
Tidigare loggar i användarmappen flyttas eller raderas inte automatiskt; de kan flyttas manuellt till appens `logs/` om de ska tas med i insamlingen.

## Datumarkiv och kvarstående fel

Loggposter från datum **före dagens lokala datum** arkiveras till `logs/archive/ÅÅÅÅ-MM-DD/`.
Exempel: den 4 november hamnar poster från den 3 november under `logs/archive/2026-11-03/`. Även äldre dagar tas med.
Datum i loggraden används i första hand. Äldre loggar med enbart klockslag använder filnamnets datum och identifierade midnattspassager; helt odaterade loggar använder filens ändringsdatum. Exakt händelsedatum kan inte återskapas om källan saknar datum.

Vid appstart (efter att den egna instansvakten tagits) läses gamla fel in **före** arkiveringen, därefter flyttas äldre poster bort från vanliga loggfiler och dagens poster behålls.
Dagens startlogg behåller alla dagens starter i stället för att skrivas över vid varje körning. Antalsrotation får inte radera dagens sessioner. En andra start medan appen redan körs arkiverar inte öppna filer. Vid datumbyte under körning skapas säkra arkivkopior utan att kapa aktiva loggskrivare; originalen rensas nästa start.
Arkivnamn innehåller innehållshash för att undvika dubbla identiska kopior. Växande loggar kan ge överlappande ögonblicksbilder. Datumarkiv äldre än 14 kalenderdagar raderas automatiskt. Exakt 14 dagar gamla arkiv behålls; från dag 15 tas vanliga arkiverade loggfiler bort. Olösta fel och deras register undantas.

**`logs/unresolved_errors.log` arkiveras eller roteras aldrig bort.** Den innehåller aktiva fel med stabilt fel-ID, identifierad felkod/undantagstyp när sådan finns, källogg, första/senaste förekomst, antal och traceback-kontext.
Kvarstående fel sparas också i `error-register.sqlite3` så de överlever omstart och loggrotation. Arkiverade loggar och själva registret läses inte tillbaka som nya fel.

Via **Hjälp → Aktiva fel / markera åtgärdade** kan du granska felen och markera valda fel som åtgärdade.
Då försvinner de från den aktiva felloggen men deras status/historik finns kvar i registret. Samma fel öppnas igen om det faktiskt loggas på nytt.
Appen gissar inte att ett fel är åtgärdat bara för att en tid har gått eller en uppdatering installerats.

## Skydd för osparat arbete och förbättrad felsökning

### Automatisk omstart

En väntande uppdatering får inte starta om appen när galleriordning eller rotationer är osparade, när CSS/HTML-redigeraren har ändrats eller när galleriinställningar (inklusive titel/beskrivning) inte är sparade.
Exportredigeraren har egen ändringskontroll och frågar innan osparade ändringar kastas vid stängning.
Om ett plugins sparstatus inte kan kontrolleras skjuts omstarten upp. Anledningen loggas, och uppdateringen ligger kvar i väntan på att arbetet sparas.
Ett FTP-lösenord som bara finns i minnet blockerar också automatisk omstart, eftersom det avsiktligt inte sparas på disk. Manuell avslutning följer appens vanliga beteende.

### Datum, gruppering och historik

Nya loggposter har fullständigt lokalt datum och klockslag; traceback-fortsättningar hör till den föregående posten.
Speglade fel med samma normaliserade feltext grupperas i ett ärende med samtliga källoggar. Tidsstämplar och nivåprefix ignoreras vid jämförelsen, men olika feltexter hålls isär. Antalet avser loggträffar, inte garanterat unika incidenter.

Vid markering som åtgärdat sparas **tidpunkt, OS-användare, appversion och en valfri kommentar**. Välj **Visa åtgärdade / historik** i felvyn för att se även stängda ärenden och deras historik.
Om felet återkommer öppnas ärendet igen utan att tidigare åtgärdshistorik försvinner.

### Snabbare felregister

Aktiva och åtgärdade fel lagras i SQLite (`logs/error-register.sqlite3`, ingår i Python). Insamlingen använder en transaktion per läsomgång och exporterar `unresolved_errors.log` en gång per ändrad batch, inte för varje traceback-rad.
Det äldre `.error-register.json` migreras och behålls orört som säkerhetskopia. SQLite-filen och den aktiva felloggen ingår inte i datumarkiveringen.

## Copyright

Copyright © 2026 Rickard Längkvist.

## Kontroll och uppgradering av befintlig Python

**Hjälp → Kontrollera / uppgradera Python** identifierar den Python som faktiskt kör appen och jämför med senaste stabila CPython-taggen från det officiella Python-projektet på GitHub. Alfa-, beta- och RC-versioner väljs inte.
Kontrollen och pakethanteraren körs i bakgrunden. Manuell uppgradering via menyn begär bekräftelse; den aktiverade startkontrollen försöker uppgradera automatiskt när det stöds. Administratörsgodkännande kan krävas. Uppgraderingen kan påverka andra program som använder samma Python.

Appen använder aldrig en vanlig `install`-åtgärd som fallback när en befintlig Python hittats:

- **Windows:** kräver att aktuell Python finns registrerad och att motsvarande paket är känt för WinGet. Kör endast `winget upgrade` för paketet.
- **macOS:** kör endast `brew upgrade` för en redan installerad formel som äger den aktuella Python-körfilen. Python från annan installerare hanteras manuellt.
- **Linux:** för en identifierad Debian/Ubuntu-installation används endast `apt-get install --only-upgrade` för det befintliga versionspaketet, och bara om förrådet erbjuder den senaste stabila versionen. Administratörsgodkännande kan krävas. Andra distributioner eller egna Python-byggen ger instruktion om manuell uppgradering via ursprunglig installationsmetod.

Om senaste stabila Python hör till **en ny serie**, t.ex. 3.13 → 3.14, stoppas automatiken: dessa övergångar kan skapa parallella installationer och kan inte generellt göras utan det på alla tre OS. Därmed respekteras regeln att inte lägga in en extra Python. Kontrollfönstret visar senaste versionen och begränsningen i stället för att påstå att en äldre version är senaste.

Sparstatus och pågående appjobb kontrolleras före godkännande. Resultatet loggas i `logs/python-runtime.log`. Efter en lyckad paketuppgradering verifieras versionen med en ny process; appen behöver sedan startas om.
Python kontrolleras vid veckounderhållet och uppgraderas när befintlig installation kan uppgraderas utan en parallell Python. Nätåtkomst, faktisk pakethanterare och eventuell behörighet krävs. Uppgraderingstesterna använder mockade verktyg; inga riktiga systemuppgraderingar har körts i sandboxen.

**Om Python helt saknas kan appens Python-kod inte starta.** Den allra första installationen måste därför göras manuellt eller av en extern bootstrapper. Appen lägger inte tillbaka BAT/VBS eller något annat bootstrap-program för detta.

## Vanlig start utan uppdateringskontroller

Vanliga starter gör ingen nätbaserad Python-/release-/paketkontroll och uppgraderar inte redan installerade tillägg.
Endast saknade appberoenden installeras som en nödvändig första installation för att appen över huvud taget ska kunna öppnas.
Manuellt godkänd, väntande releaseinstallation kan fortfarande utföras vid start.

**Ingen egen miljö, `.venv`, `virtualenv`, inbäddad Python eller separat paketmapp skapas.** Den befintliga Python-installationen används.
Andra program som använder samma Python kan påverkas av veckouppgraderingarna. En dator helt utan Python behöver fortfarande sin första installation utanför appen.

## Om appen körs men inget fönster syns

`mainloop startar` och `Systray-ikon synlig` i loggen innebär att appen körs dolt, inte att loggen visar en startkrasch. Kontrollera Windows dolda trayikoner och välj Visa, eller starta samma app igen.

För uttrycklig återställning finns `visa_app.pyw`: lägg den bredvid den `main.pyw` som du faktiskt kör och öppna den. Den skickar en aktiveringsbegäran till nya versioner eller skapar `instance_show.trigger` för äldre versioner. Om ingen instans svarar startas appen med `--show` och en kompatibilitetstrigger. Ingen paketinstallation görs av själva visningshjälpen. Resultatet skrivs i `logs/show-app.log`. Normal start förblir minimerad. Startloggen anger nu programmapp, version och Python-sökväg så att olika programkopior kan skiljas åt.

## Publiceringspolicy för fortsatt utveckling

Ny färdig kod pushas till den aktuella arbetsgrenen och samma GitHub-release `v1.0.0` uppdateras utan versionsbyte. Ingen push till `main` och inga merges. Release-taggen ska peka på exakt den testade arbetsgrenscommitten; uppdateraren jämför även commit och filhashar för att upptäcka ändringar med samma versionsnummer. GitHub-publicering är ett utvecklarsteg, inte något den installerade appen själv gör.

### Timeout när ett dolt fönster ska visas

Äldre appversioner kan hålla instansporten öppen utan att läsa anslutningar. Efter upprepade försök kan även själva anslutningen få timeout. `visa_app.pyw` använder då triggerfilen även vid anslutnings-/sändningsfel, utan att starta ännu en instans. Loggen skiljer mellan skickad begäran och bekräftad fönsterhantering: kontrollera `show_window` i `logs/startup.log`. Lägg hjälpen i exakt samma programmapp som den körande appen. Den senaste huvudappen läser också IPC-begäran i sin UI-poll, inte vid avslut.


## Tidig startdiagnostik och tyst Pythonw-avslut

Felhanteringen installeras nu före Python-sökning, instanslås, Tk-import och paketkontroll även vid direktstart av `main.pyw`. Följande filer ligger i appens `logs/`:

- `startup-early.log`: process-ID, Python-sökväg, programmapp och passerade startsteg. Den skiljer normal vidarestart/aktivering av befintlig app från fönsteruppbyggnad och mainloop.
- `startup-crash.log`: Python-undantag med full traceback och senaste startsteg. Windows kan visa ett startfel även om Tk inte går att importera.
- `python-child_ÅÅÅÅMMDD_PID.log`: felutmatning från den nya Pythonw-processen, även syntaxfel som inträffar innan dess egen felhanterare har startat. PID i filnamnet identifierar förälderns startförsök; barnets PID står i `python-discovery.log`.
- `native_fault_ÅÅÅÅMMDD_PID.log` och vid behov `early_stderr_ÅÅÅÅMMDD_PID.log`: fataldiagnostik respektive tidig stderr när Pythonw saknar konsol. Dessa filer kan vara tomma vid normal körning.

Om barnprocessen avslutas med felkod under första sekunden rapporterar startaren det i stället för att bara avsluta tyst. Saknade beroenden som inte kunde installeras stoppar nu starten med ett tydligt fel; appen fortsätter inte som om paketinstallationen lyckades. Senare mainloop-fel skrivs också i startkraschloggen. Loggarna omfattas av ordinarie datumarkivering/retention. Ett strömavbrott, tvångsavslut eller alla typer av native-krasch kan fortfarande inte garanteras ge en fullständig logg.

Kodgranskningens regressioner: CSS-förhandsvisningen hanterar nu procenttecken korrekt i HTML-mallen. Loggstatistik skiljer på `error_file` (filnamnet) och `errors` (antalet), så startloggen visar inte längre felantalet som felfilens namn.


## Utökad händelse- och felinsamling

`logs/events_ÅÅÅÅMMDD.log` är en gemensam händelselogg med läsbar tids-/nivåprefix och JSON per rad. Varje post har lokal tid med tidszon, sessions-ID, process-ID, tråd och, för pipeline-jobb, jobb-ID. Filen delas vid 10 MiB i numrerade segment utan att dagens poster kastas. Ordinarie datumarkiv och 14-dagarsretention gäller; olösta fel ligger kvar i det separata registret.

Insamlingen omfattar:

- startsteg, normal vidarestart och avslut samt tillgängliga Python-undantag;
- appens befintliga loggmeddelanden, bakgrundstrådsfel, Tk-callbackfel och undantag i exempelvis destruktorer (`unraisablehook`);
- Python-varningar som faktiskt utfärdas och Python-loggingposter som når rotloggern (bibliotekens egna nivåfilter ändras inte);
- radbuffrad stdout/stderr, även fragmenterade skrivrader och slutflush;
- pipeline- och pluginstart/slut, tidsåtgång och fel med traceback;
- Tk-messageboxar som använder den vanliga `messagebox`-vägen, fönstrets visa/dölj/fokus samt klickad widgetklass, inte fältinnehåll;
- processstarter (enbart körbar fil, aldrig argument eller miljö) och anslutningsförsök (adress, inte trafikens innehåll). Ett försök är inte bevis för en lyckad anslutning;
- UI-livstecken en gång per minut och varning med huvudtrådens stack när pulsen är mer än 15 sekunder försenad, följt av en återhämtningspost. Långa jobb eller systemdialoger kan fördröja pulsen utan att appen har kraschat.

Ingen tangentloggning, skärminspelning, global filövervakning eller övervakning av andra program används. Ingen miljödump, FTP-PASS-kommandologgning eller nätverkspayload samlas in. Lösenords-/tokenfält, vanliga nyckel=värde-mönster, Bearer-token och URL-inloggning maskeras i den nya händelseloggen; appens vanliga logger och fångade stdout/stderr får också maskering. Lokala sökvägar och felmeddelanden kan fortfarande innehålla personuppgifter. Maskering är ett skydd på bästa möjliga grund, inte en garanti: granska alltid loggar före delning, särskilt native-felloggar och utdata från underprocesser.

Detta kan inte upptäcka bokstavligen allt. Fångade men avsiktligt ignorerade undantag som aldrig loggas, privata bibliotekshanterare som inte vidarebefordrar logging, icke-Tk/systemdialoger, tvångsavslut, strömavbrott och vissa native-krascher kan sakna fullständig information. Ingen generell tracing av varje Python-anrop/undantag aktiveras, eftersom det skulle belasta appen kraftigt. Speglade fel kan förekomma i flera loggar och ska inte tolkas som separata krascher enbart utifrån antal träffar.

## Minimera/stäng och flera operativsystem

Minimera och fönstrets X-knapp döljer nu till en **synlig** systemfältsikon. Gamla `close_to_tray=False`/`minimize_to_tray=False` ändrar inte detta. Avsluta uttryckligen med appens eller systemfältsmenyns **Avsluta**. Om systemfält saknas minimeras fönstret normalt, utan avslut; om fönsterhanteraren avvisar minimering lämnas fönstret synligt.

- **Windows:** Tk-fönster, pystray-systemfält, ICO och befintligt genvägs-/autostartstöd.
- **macOS:** Tk-fönster, PNG och medföljande ICNS. Tray-plugin och reservhanterare initierar nu pystray via `run_detached()` från Tk-tråden, i stället för Cocoa-loop i bakgrundstråd. Kräver fungerande Python/Tk/Pillow/pystray; verkligt menyrads-/Dock-beteende måste verifieras på macOS.
- **Linux X11:** systemfält när skrivbordet och installerad pystray-backend erbjuder det, annars vanlig minimering. Tk och backendens systembibliotek kan behöva installeras med distributionens pakethanterare.
- **Linux Wayland:** nuvarande konservativa reservläge använder vanlig minimering, inte garanterat systemfält. Ett skrivbord utan traystöd ska inte göra appen oåtkomlig.

Ingen plattform behöver Git eller egen virtuell miljö för normal drift. Att filformat och kodvägar stöds är inte samma sak som ett verifierat installerarpaket för alla operativsystem. Automatiska tester körs i Linux-sandbox; riktiga Windows-, macOS- och skrivbordstester återstår.

Ny grafisk identitet och tryckfiler: se `branding/README.md`. SVG-originalen innehåller enbart vektorer, inklusive konturkonverterad text.

### Autostart: minimerad inloggningsstart och verifiering

Autostartgenvägen får nu `--autostart` och Windows-kommandot för minimerad visning utan fokus. Tk startar fortsatt dolt och väljer synligt systemfält eller vanlig minimering. Om appen redan körs skickar en autostart **inte** SHOW; manuell dubbelstart öppnar fortfarande appen.

Genvägens faktiska innehåll verifieras med hash, inte bara en separat metadatafil. Saknad/tom genväg rapporteras som fel och ändrad genväg repareras när autostart är valt. Windows egen inaktivering under Inställningar > Appar > Autostart upptäcks och loggas som `autostart.status`/`autostart.disabled_by_windows`; den åsidosätts inte i hemlighet. Vid aktivering visas instruktion om Windows har blockerat posten. En korrekt installerad genväg kan fortfarande blockeras av systempolicy eller Windows inställningar.

Efter uppdatering: starta appen manuellt en gång så att gamla genvägar migreras, aktivera **Starta med Windows**, kontrollera Windows autostartinställningar och prova därefter utloggning/inloggning. Autostart betyder inloggning för aktuell användare, inte en tjänst före inloggning. Felsök med `logs/events_*.log`, `logs/startup-early.log` och `logs/python-discovery.log`.


## Starta utan förinstallerad Python: VBS och SH

I samma releasepaket ingår `Starta.vbs` (Windows, konsolfri start) och `Starta.sh` (macOS/Linux, kör `sh Starta.sh` i terminalen). Ingen `Installera senaste Python.bat` ingår.

Startarna kontrollerar PATH och vanliga Python-platser. Om Python går att köra startar de `start.pyw` direkt, utan installations-/uppgraderingsfråga. Saknad Tk eller för gammal befintlig Python är ett appfel, inte anledning att erbjuda en parallellinstallation. Den ordinarie Python-startaren väljer därefter en kompatibel installation och appen startar minimerad.

Endast när ingen körbar Python hittas erbjuds **guidad installation** efter godkännande: på Windows/macOS öppnas den officiella Python.org-sidan för senaste stabila installationsprogram; på Linux visas distributionsanpassade kommandon för stödd Python och Tk. Inget installationsprogram hämtas eller körs automatiskt, ingen administratörsbehörighet begärs av startaren. Slutför installationen själv och kör samma startfil igen. När Python sedan upptäcks visas ingen installationsfråga. En specialinstallation utanför sökplatserna behöver läggas i PATH.

Windows måste tillåta Windows Script Host/VBScript, vilket vissa nya Windows-installationer eller företagsregler kan stänga av. På macOS/Linux behöver SH-startaren köras i terminal för installationserbjudandet. Dessa begränsningar kan inte kringgås med själva VBS-/SH-filerna. Python-installationen är ett användarval, inte en automatisk uppdatering av systemets befintliga Python.

### Manuell uppdateringssökning och HTTP-fel

**Hjälp → Sök efter uppdateringar** öppnar den manuella releasekontrollen direkt, även om automatiska kontroller är avstängda. Befintlig meny Uppdateringar och systemfältsmenyn behålls.

Tillfälliga HTTP 404/429/5xx från GitHub får högst tre försök. Om `/releases/latest` svarar 404 provas listan med publicerade stabila releaser, aldrig main eller opublicerade taggar. Vid kvarstående fel visas HTTP-kod och den misslyckade adressen. Full traceback och historik läggs till i `logs/update.log` (tidigare fel skrivs inte längre över) och speglas i händelseloggen. En permanent 404 för en tagg/commit kräver fortfarande att releasekällan blir tillgänglig; ett fel döljs inte som ”redan uppdaterad”. VBS-/SH-startfilerna ingår nu också i uppdaterarens filomfång.


### Tolka loggarnas fönster- och felstatus

Fönsterdiagnostiken läser nu faktisk `icon.visible` utöver tray-pluginens fördröjda cache. Om en tray-tråd körs men synlighet inte bekräftats väntar startkontrollen upp till fyra extra kontroller med en sekunds mellanrum; utebliven bekräftelse är en varning, inte bevis för att appen är onåbar. Fönstrets nivå tas från fönsterkontrollen, inte andra fel i samma diagnosrapport.

Samlad felinsamling ignorerar statusrader som `fel: inga`, `fel: 0` och `Skrivna rader: ... (varav fel ...)`; riktiga felrader och tracebacks sparas som tidigare. Befintliga aktiva poster raderas eller markeras inte automatiskt – historiska falsklarm kan markeras som åtgärdade av användaren. Pip-varning om kvarlämnad `~il` efter lyckad Pillow-installation är en städvarning, inte bevis för att Pillow saknas. FFmpeg-varningen gäller videofunktionerna.

`startup-early.log` innehåller nu `Kodidentitet` med korta SHA-256-avtryck för centrala moduler. Det gör det möjligt att skilja blandade/äldre programfiler från aktuell release trots samma versionsnummer.


## Licens och frivilligt stöd

Appen är gratis att använda privat och kommersiellt, även inom företag och organisationer. Se `LICENSE` för fullständiga villkor: interna installations-/säkerhetskopior är tillåtna; försäljning av själva appen och omdistribution till tredje part ingår inte i tillståndet. Egna gallerier och annat eget material kan användas och säljas enligt villkoren. Detta är en användningslicens, inte en open-source-licens. Tredjepartskomponenternas villkor gäller separat.

**Hjälp → Donationer / Stöd utvecklingen…** visar en lokal Swish-QR för **0721817177** samt **PayPal**- och **Ko-fi**-knappar. Knapparna öppnar direkt `https://paypal.me/Rickard3dPrint` respektive `https://ko-fi.com/tokke2` i standardwebbläsaren. Ingen egen donationssida, receptstödsida eller beloppsruta i appen används. Skanna med Swish-appen och välj belopp där. QR-koden använder Swish C-format: `C46721817177;;;6` (mottagare i internationellt nummerformat, tomt belopp/meddelande och mask 6). Kontrollera alltid mottagarnamnet i Swish före godkännande.

QR-bilden levereras färdig i `icon/swish-donation.png` och omfattas av releaseuppdateringen. Ingen internetanslutning eller QR-tjänst används för att visa den. Den har svart/vita moduler, fri vit kant och ingen överlagrad logotyp. Byggverktyget `tools/build_swish_qr.py` kan återskapa den med byggberoendet `qrcode[pil]`; det är inte ett nytt runtime-beroende. Automatisk QR-avkodning verifierar payloaden, men faktiskt betalningsflöde behöver verifieras i Swish utan att någon betalning måste genomföras.

Swish-mottagaren ligger fast i programkoden och är inte redigerbara i inställningar eller donationsfönstret. Beloppet väljs i Swish och är valfritt. Detta är ett UI-/konfigurationslås, inte ett löfte om manipulationsskydd på en dator där användaren kan ändra Python-koden. Kontrollera alltid mottagare hos betaltjänsten. Licensen visas skrivskyddad via **Hjälp → Licens** och ingår i releasepaketet och uppdaterarens filomfång.


Donationsdialogen har en egen personlig tacktext om frivilligt stöd till utveckling, felsökning och underhåll. Den öppnas bara på begäran via Hjälp-menyn, aldrig som betalningspåminnelse vid start. Endast en dialog öppnas åt gången; upprepade menyval lyfter befintlig dialog. Stäng med knappen, X eller Escape. Längre innehåll kan rullas med dialogens rullningslist.

## HEIC/HEIF och QuickTime från exempelvis iPhone

HEIC/HEIF (`.heic`, `.heif`) ingår nu i bildval, mappövervakning, sortering, galleri och bildbehandling. `pillow-heif` registrerar avkodaren i Pillow. Den vanliga bildpipelinen skapar webbvänliga JPEG-bilder/miniatyrer och kan använda EXIF-rotation som tidigare. Originalen skrivs inte över. HEIC-bildsekvenser/Live Photo-rörelse importeras inte som animation: det är stillbilden som behandlas.

QuickTime (`.mov`, `.qt`, även stora bokstäver) känns igen som video. Vid galleri-export konverteras dessa till MP4 med H.264, AAC om ljud finns, yuv420p och faststart för bättre webbläsarstöd. Videofliken kan också öppna dem för manuell konvertering. FFmpeg söks i befintlig installation och därefter via `imageio-ffmpeg`, vars tillgängliga plattformshjul normalt innehåller FFmpeg. Ingen separat QuickTime Player behövs. FFprobe är fortfarande separat och krävs för vissa detaljerade metadatafunktioner.

Efter uppdatering installerar startaren de nya saknade beroendena `pillow-heif` och `imageio-ffmpeg` via den vanliga paketkontrollen. På plattformar/Python-versioner där kompatibla hjul eller systembibliotek saknas kan installation behöva lösas med operativsystemets pakethanterare; stöd för varje kodek eller skadad/DRM-skyddad fil kan inte garanteras. FFmpeg-/codec-licenser gäller separat.

Konvertering sker i temporär fil, ersätter destinationen först vid framgång och har tidsgräns på en timme per fil. Vid fel lämnas original och tidigare MP4 orörda; felutmatning rapporteras, inte en falsk lyckad videolänk. Långa/stora videor kan ta tid och diskplats. HDR/Dolby Vision-färgmatchning eller exakt metadata-/spårbevarande garanteras inte av denna webbkonvertering.


## Installera direkt och erbjud omstart inom tre sekunder

Vid manuell **Sök efter uppdateringar** laddas en hittad stabil release nu ned och installeras direkt, inte bara köas till nästa start. Automatläge installerar utan extra godkännande; schemalagt frågeläge behåller sitt godkännande. Ingen ny version betyder ingen installation eller omstart. Säkerhetskopiering, syntaxvalidering, återställning vid fel och skyddet för utvecklingskopior med `.git` behålls.

Efter lyckad installation i den körande appen visas **Starta om nu** och **Senare**, med en avbrytbar tresekundersnedräkning. Senare, Escape eller X avbryter den automatiska omstarten; den installerade uppdateringen används då vid nästa vanliga start. Omstart sparar inställningar och använder väntande hjälpprocess tills gamla appens instanslås släppts – ingen andra nedladdning. En installation före appstart behöver ingen separat omstartsdialog.

Pågående pipeline/bakgrundsjobb och kända osparade ändringar stoppar direktinstallation/omstart. Spara och avsluta jobbet, sök sedan igen. Installationsdialogen blockerar nya UI-åtgärder under filbytet och samtidig manuell kontroll förhindras. En ny säkerhetskontroll görs när nedräkningen löper ut. Vid fel erbjuds ingen automatisk omstart. Ladda ned/installation kan ta längre än tre sekunder; nedräkningen börjar först efter lyckad installation.

Har du laddat ned FFmpeg separat: packa upp arkivet och välj `bin/ffmpeg.exe` i Video-flikens FFmpeg-sökväg och testa den där. FFprobe kan väljas separat för detaljerad videoinformation.

## Synlig filbearbetning

Pipeline-körning (även från Kör-menyn) och bearbetning i Video-fliken visar nu en separat **Filbearbetning**-dialog. Den visar aktuellt steg/fil, procent när en plugin rapporterar mätbar progress och förfluten tid. Under exempelvis en lång QuickTime-konvertering används en animerad stapel utan påhittad procent eller ETA. Förfluten tid betyder att jobbet fortfarande är aktivt – det bevisar inte att en extern codec gör framsteg.

Worker-trådar lägger bara händelser i en trådsäker, begränsad kö; dialogen uppdateras av Tk-tråden var 100 ms. Täta progresshändelser slås ihop så att stora bildmängder inte fyller UI-kön. Varje jobb har egen status. Nästa plugin växlar tillbaka till rörlig stapel tills ny procent finns. Slutstatus skiljer klart, fel och avbrutet; befintliga Avbryt-knappar behålls. **Dölj** eller X döljer endast progressdialogen och avbryter inte jobbet. Dialogen är rullningsfri och kan storleksändras; verkligt utseende på Windows/macOS behöver verifieras.

### FFmpeg ser ut att stanna på 0 %

FFmpeg-körningen i Video-fliken läser nu stdout **och stderr samtidigt**. Tidigare kunde en full stderr-pipe blockera FFmpeg samtidigt som appen väntade på progressrader. Progressläsningen ligger nu i separata lästrådar och övervakningen väntar högst 200 ms åt gången, så tyst FFmpeg inte blockerar avbrotts-/timeoutkontrollen.

Status visar ett livstecken varje sekund och anger när inga nya statusdata har kommit på minst 30 sekunder. Det är en varning om brist på data, inte bevis för att processen har låst sig. Saknas ffprobe provas längdavläsning med FFmpeg. Om längden fortfarande är okänd visas ingen påhittad procent (tidigare antogs 60 sekunder); slutlig 100 % sätts först efter lyckad exitkod. Felutmatningens sista del följer med i felrapporten. Avbryt-signalen hanteras i bakgrunden utan att sova i Tk-tråden, och processen termineras/killas samt städas efter behov.

### Uppdatering blockerad trots avslutad bearbetning

Aktivitetskontrollen använder nu faktiska jobbflaggor (inklusive Video-flikens `processing`), levande extern FFmpeg-process och uttryckligt identifierade arbetstrådar. Permanenta kö-/status-/aktiveringstrådar blockerar inte längre bara för att deras namn innehåller `process` eller `upload`. Samma kontroll används för manuell direktinstallation och schemalagd omstart. Faktiskt pågående arbete och osparade ändringar är fortfarande skyddade.


### Synlig stapel direkt i Video-fliken

Den inbyggda stapeln **Aktuell** i Video-fliken startar nu animation omedelbart när Bearbeta klickas, före worker-tråd och längdavläsning. Varje ny fil återgår till rörlig stapel tills FFmpeg rapporterar mätbar procent. Vid okänd längd står den inte kvar osynlig på 0 %. Staplarna har en egen stil med ökad tjocklek; faktisk färgåtergivning beror på Tk-tema/operativsystem. Vid fel eller avbrott stoppas animationen utan falsk 100 %. Separata Filbearbetning-dialogen behålls. Startloggen i Video-fliken innehåller `Videoprogress: rörlig stapel direkt vid start` så att laddad kod kan identifieras.

## Automatisk videokonvertering vid Generera galleri

Du behöver inte köra Video-flikens manuella konvertering först. **Generera galleri** tar de valda/identifierade videofilerna och konverterar automatiskt varje video till MP4 med H.264, AAC om ljud finns, yuv420p och faststart. Det gäller även inkommande MP4, eftersom filändelsen inte garanterar webbläsarvänliga kodekar (en MP4 kan exempelvis innehålla HEVC). MOV/QT, AVI, MKV, WebM och övriga videoformat som appen känner igen hanteras på samma sätt, förutsatt att FFmpeg kan avkoda innehållet.

Exporterad HTML och videominiatyrer använder den konverterade MP4-filen. Originalen ändras inte. Vid omexport i samma mapp väljs ett annat utfilnamn om det normala namnet skulle krocka med någon av ingångsvideorna. FFmpeg-sökvägen från Video-pluginens konfiguration prioriteras när den är tillgänglig, annars används ordinarie sökning och paketets reservbinär. Progressdialogen visar vilken video som konverteras. Vid konverteringsfel avbryts exporten med fel i stället för att länka till en video som inte har konverterats.

Videoflikens manuella inställningar för andra kodekar påverkar inte webbnormaliseringen. Videor kodas om vid export; stora klipp kan därför ta tid och diskplats. H.264/AAC ger brett stöd men garanterar inte uppspelning på varje enhet eller av DRM-skyddat/skadat innehåll. HDR/Dolby Vision-matchning och bevarande av alla metadata/spår garanteras inte.

### Galleri med enbart originalvideor (inga stillbilder)

Källmappen får innehålla **bara videor**, bara PDF-filer eller en blandning med bilder. Tidigare krävde inställningsvalideringen stillbilder och HTML-steget hoppade också över tom bildlista, vilket kunde ge ett felaktigt ”Klart” utan ny export. Nu krävs minst en igenkänd bild/video/PDF i stället. HTML exporteras även utan bildkort; videokorten använder de automatiskt konverterade MP4-filerna. Utan stillbilder krävs ingen bildbaserad cover.jpg i manifestet.

Inställningsförberedelsen körs även om inställningspluginen valts bort från de valfria pipeline-stegen. Saknad källmapp och tom export rapporteras som fel. Kontroller-flikens slutdialog kräver en uttrycklig markering från aktuell HTML-generering samt en existerande indexfil; en gammal index.html räknas inte som en ny lyckad generering. HTML-generatorn måste fortfarande vara aktiverad. Originalvideor behöver inte bearbetas manuellt i Video-fliken först.

### Uppdatering stoppar arbeten automatiskt

När en release ska installeras begär appen automatiskt avbrott för pågående jobb och väntar tills de verkliga jobbflaggorna, pipeline-trådarna och externa processerna är avslutade. UI:t spärras under väntan så att nya manuella jobb inte startas. Avbrottskontrollen används mellan pipeline-stegen, av bild/FTP-jobb samt under FFmpeg-konvertering av gallerivideor. Inga trådar dödas och inga arbetsflaggor förfalskas till ”klar”; ett jobb som ännu inte svarat på avbrott håller installationen väntande. Osparade redigeringar raderas inte automatiskt: dessa måste fortfarande sparas före installation/omstart.

Videokortens JPEG-miniatyrer hämtas från den exporterade videofilen under gallerigenereringen (försök vid 1 sekund, sedan första rutan för korta klipp). De skapas om vid varje export så att en gammal miniatyr inte visas för en ny video. Ett integrationstest kontrollerar både MP4, JPEG-bildens färginnehåll från källvideon och HTML-länken till miniatyren.

Uppdatering inifrån den öppna appen återanvänder nu appens befintliga single-instance-skydd efter stopp- och sparstatuskontrollerna. Den försöker inte binda samma upptagna port igen. Installationsarbetaren verifierar att uppdateringsdialogen och stoppbegäran fortfarande är aktiva och att inga jobb återstår. Fristående installation/startuppdatering behåller portspärren mot en redan körande app; spärren är inte generellt borttagen.

## Säkrare uppdatering, videoexport och publicering

- **Separat uppdateringsprocess:** när en uppdatering godkänts stoppas jobb och osparade ändringar kontrolleras. Inställningar sparas, en separat Python-process startas och appen avslutas. Processen väntar på single-instance-skyddet, installerar exakt vald release-commit och startar appen igen. Vid installationsfel används befintlig rollback och appen startas ändå; detaljer finns i `update.log`. Om hjälpprocessen inte kan startas hålls appen öppen. Inga programfiler behöver längre bytas av den öppna GUI-processen i detta flöde.
- **Mindre omkodning:** när FFprobe finns bredvid FFmpeg eller i PATH kontrolleras video-/ljudströmmar. En H.264-video med yuv420p och AAC-ljud (eller utan ljud), utan identifierad HDR-transfer, packas om till faststart-MP4 med stream copy. HEVC/övriga format och osäker/otillgänglig probning använder H.264/AAC-konvertering. Detta är en konservativ kompatibilitetskontroll, inte en garanti för varje webbläsare eller H.264-profil.
- **Verifierad återanvändning:** en `.mp4.web.json` innehåller SHA-256 för källa och resultat samt exportprofilens identitet, inga originalsökvägar. En oförändrad video kodas inte om om även resultatets innehåll verifierats. Ändrad källa, profil eller skadad utfil tvingar nytt resultat. Hashning kräver fortfarande läsning av videon. Miniatyrer hämtas fortsatt från videon vid export.
- **Skyddad galleri-export:** pipeline-exporten arbetar i en syskonmapp redan från inställningssteget. Direkt HTML-export/redigerarens riktiga generator använder samma skydd. Galleriet länkkontrolleras före mappbytet; FTP körs först efter publicering. Vanliga fel/avbrott lämnar tidigare galleri kvar och rensar endast den tillfälliga arbetskopian. Föregående export behålls under appmappens `backups/galleries/`. Säkerhetskopior raderas inte automatiskt och kräver extra diskplats. Publicering är inte ett universellt atomiskt mappbyte; över olika diskar kopieras backupen färdigt innan den gamla exportplatsen frigörs; strömavbrott däremellan kan kräva manuell återställning från backupmappen. Externa filås kan stoppa publiceringen.
- **Tydligare status:** Om-dialogen och startloggen visar installerad commit (12 tecken) och installationsdatum från `.release-state.json`. Äldre/manuella installationer anges som okända. Jobbsteg, videoförberedelse, väntande stopp och publicering visas i befintlig status/progress. Datum gäller installationen, inte releasepubliceringen.

Windows-fönster, filås och verklig uppdatering från en äldre installerad kopia behöver fortfarande verifieras på Windows; automatiska tester här ersätter inte den kontrollen.

## Arbetsyta, navigation och visuell gallerilayout

Den nya **Start**-vyn samlar källmapp, vald exportmapp, senaste genererade galleri under aktuell körning, aktiva jobb och installerad releaseinformation. Snabbknappar använder appens befintliga funktioner för mappval, generering, förhandsvisning och output. Verktyg som saknas/inaktiverats rapporteras i stället för att ge ett tyst knapptryck.

Navigationen **Start → Projekt → Media → Utseende → Publicera** länkar till befintliga inställningar, bildgalleri, layoutredigerare och kontroller. **Avancerat** visar den gamla kompletta flikraden, inklusive Video, CSS, logg och övriga verktyg. Inga verktyg eller menyalternativ är borttagna. Det här är en ny navigationsyta ovanpå befintliga verktyg, inte en omskrivning av deras interna kontroller. Arbetsytan kan inaktiveras som plugin om den klassiska navigationen föredras.

Startsidan har en dragbar avdelare mellan åtgärder och status. Fördelningen sparas per användare i `workspace.json`, separat för liggande och stående läge. Vid mindre än 820 pixlars innehållsbredd staplas panelerna; navigationen radbryts och åtgärds-/statuspanelerna kan rullas. Sparad huvudfönsterstorlek begränsas till skärmen. Tk/operativsystemets skalning behålls. Gemensamma Studio-stilar ger den nya arbetsytan och layoutdialogens knappar konsekvent avstånd och cyan/violett/rosa-konceptet; äldre verktygs egna temastilar ersätts inte globalt.

**Utseende**, eller knappen **Visuell layout och liveförhandsvisning** under Inställningar, öppnar en redigerare för kolumner, mellanrum, hörnradie, textstorlek, bildformat och cover/contain-anpassning. Dator/surfplatta/mobil ger en **schematisk** direktförhandsvisning med exempelrutor, inte en inbäddad webbläsare eller exakt återgivning av egna bilder. ”Använd i projektet” uppdaterar inställningarna; ordinarie Spara/dirty-kontroll gäller. Valen följer med till HTML/CSS och den portabla gallerimanifestfilen. Avbryt förändrar inte inställningarna.

Videominiatyrer provas nu vid upp till fyra positioner i klippet (8, 25, 50 och 75 procent när längden kan läsas). Bilderna poängsätts efter kontrast/detaljer och straffas för stora svarta/vita ytor. Detta minskar risken för svarta inledningsrutor men garanterar inte ett estetiskt bästa motiv. Vid okänd längd provas början/1 sekund; befintlig extraktion är reservväg. Kandidatbilder städas bort och avbrott kontrolleras mellan/under extraktionerna. Originalvideon ändras aldrig.

Automatiska tester omfattar layoutvalidering, kontrast, sparad arbetsytedata, skärmgränser, faktisk CSS/manifest-export och en riktig video med svart intro. Tk saknas i testmiljön här: fönsterritning, dragavdelare, DPI och operativsystemens teman är **inte visuellt verifierade** och behöver kontrolleras i den installerade appen.

## Språk, panoraman, videokvaliteter och resursprofiler

Öppna **Inställningar → Galleri → Språk, panorama, videokvaliteter och resurser**. Funktionerna är uttryckliga val; tom språklista, panorama av och inga extra videokvaliteter är standard. Valen sparas med vanliga galleriinställningar och följer med i `gallery-project.json`.

### Flerspråkig statisk export

Ange exempelvis `{"en":{"title":"Gallery","description":"Welcome","labels":{"Stäng hjälpen":"Close help"}},"ar":{"dir":"rtl","title":"معرض"}}` i språkfältet. Exporten får `index.en.html`, `slideshow.en.html` osv. med språkväxlare, `lang`/`dir` och gemensamma mediefiler. Begränsade inbyggda ordlistor finns för engelska, tyska och arabiska; egna `labels` kompletterar/ersätter synliga texter och relevanta attribut. Detta är **inte automatisk fullständig översättning**: bildtexter, längre hjälpinstruktioner och övriga texter behöver egna översättningar. Skriptens källkod ändras inte genom textbyte; en DOM-översättare hanterar dynamiska etiketter. Högst 12 språk per export, validerade språkkoder och inga godtyckliga HTML-fält.

### 360°-panorama

Opt-in för cirka 2:1-bilder skapar `panorama.html` med lokal WebGL-visare, drag/touch, piltangenter, återställning och synfältsreglage. Avsett för equirektangulära sfärpanoraman: proportionen ensam kan inte bevisa att bilden är ett sådant panorama. Vanliga 2:1-foton bör därför inte använda opt-in. Ingen extern JavaScript-tjänst/CDN behövs. Vid saknat WebGL eller lokala `file://`-begränsningar erbjuds bildlänk; en webbserver rekommenderas. Detta läge behandlar **bilder, inte 360°-video**.

### Manuella videokvaliteter

Välj extra MP4-varianter med maxhöjd 480/720/1080. De kodas sekventiellt från webbvideon, utan uppskalning, med faststart/H.264/AAC och innehållsverifierad cache. Små original blir alltså inte faktisk 1080p bara för att 1080 valts. En separat sektion i galleriet/bildspelssidan har kvalitetsknappar som försöker behålla tidspositionen vid byte. Ordinarie lightbox använder fortfarande standardvideon. Det är **inte HLS/DASH eller automatisk bandbreddsanpassning**. Fler kvaliteter kostar tid, disk och uppladdningsvolym.

### Resurser

`quiet`: högst 1 bildarbetare/1 FFmpeg-kodningstråd; `balanced`: högst 2/3; `fast`: högst 8/8, dessutom begränsat av CPU-antal och bildprocessorns befintliga tak. Resursvalet tillämpas när dialogens Använd väljs och lagras per användare i `resources.json`; redan startade jobb ändras inte. Gäller bildpipelinen, webbkonvertering, extra kvaliteter och manuella videoflikens trådval (det lägre taket används). Det är **begränsad parallellism**, inte en hård CPU-procent-, RAM-kvot eller garanti om fläktljud. Kodning sker fortsatt med avbrottskontroll och temporära utdata.

## Uppdateringshälsa, återställning och signaturstöd

Efter en lyckad installation som görs av den nya separata uppdateraren startas appen med en unik hälsotoken. Den måste inom 180 sekunder bekräfta rätt commit efter att Tk:s händelseloop kommit igång (5 sekunders fördröjning). Vid krasch/uteblivet svar avslutas endast den startade barnprocessen. Uppdateraren kontrollerar därefter single-instance-skyddet och återställer endast installerarens registrerade programfiler ur backup, inte användarinställningar/gallerier. Föregående app startas med automatisk uppdatering avstängd för den körningen. Om annan appinstans körs eller återställning inte kan göras säkert lämnas backup kvar och felet skrivs i `logs/update.log`; ingen osäker överskrivning görs. En uppstartssignal bevisar inte att alla plugins, exportflöden eller framtida användaråtgärder fungerar. Funktionen gäller installationer där **uppdaterarprocessen själv redan har det nya hälsokontrollstödet**.

Ed25519-verifiering finns men **dagens release är inte signerad och signaturkrav är inte aktiverat som standard**. Inga privata signeringsnycklar har skapats eller lagrats i projektet. För att aktivera krävs:

1. En separat, säkert förvaltad privat nyckel hos releaseutgivaren.
2. En betrodd publik Ed25519-nyckel (32 råa bytes, base64) installerad i användarens konfigurationsmapp som `release-trust.json`: `{"public_key":"BASE64_PUBLIC_KEY"}`. Nyckeln hämtas aldrig automatiskt från samma release den ska verifiera.
3. Release-assets `ftp-release-manifest.json` och `ftp-release-manifest.sig`. Manifestets exakta bytes signeras; `.sig` är base64 av 64 signaturbytes. Manifestet innehåller `tag`, `commit` och `archive_sha256` för **exakta zipball-bytes** som installeras. Ändrar GitHub arkivbytes måste hash/signatur uppdateras, annars stoppas installationen.

När trustfilen finns är kontrollen obligatorisk: saknad/ogiltig signatur, fel commit eller fel arkivhash stoppar installationen innan programfiler ändras. `cryptography` krävs för verifiering. Utan trustfil visas `unsigned` i ny installationsmetadata; detta får inte förväxlas med verifierad signatur. Key-distribution, rotation, signerad releaseproduktion och skydd mot en redan komprometterad lokal app är inte lösta genom att bara ha verifieringskoden.

Tester inkluderar verklig export med språk/panorama/videovariant, utebliven uppskalning, kryptografisk verifiering/tamper-rejection, hälsotoken och återställning av endast programfiler. Interaktiv WebGL, RTL-utseende, spelarbeteende och Windows-processhantering behöver fortfarande verifieras på riktiga klienter.

### Stöd via Hjälp-menyn

**Hjälp → Donationer / Stöd utvecklingen…** öppnar en egen, rullningsbar stöddialog med Swish-kort och separata PayPal-/Ko-fi-knappar. Kort visas bredvid varandra i breda fönster och staplas på mindre skärmar. Stäng-knappen ligger kvar utanför rullningsytan; Escape stänger och upprepad menyöppning återanvänder dialogen.

Swish använder den medföljande svarta/vita QR-bilden, payload `C46721817177;;;6`: fast mottagare, inget förvalt belopp eller meddelande, ändringsmask 6. Inga externa QR-tjänster anropas. Mottagarnumret 0721817177 visas också så att det kan anges manuellt; att lägga ett nummer i en QR-kod gör det inte hemligt. Kontrollera alltid mottagarnamn och belopp i Swish. QR-avkodning testas både från originalbilden och i dialogens heltalsskalade storlek, men faktisk betalning/Swish-bankapp har inte provats här.

PayPal öppnar direkt `https://paypal.me/Rickard3dPrint` och Ko-fi direkt `https://ko-fi.com/tokke2` i webbläsaren. Belopp väljs hos betaltjänsten. Inga stödnivåer, extra funktioner mot betalning, externa receptsidor, automatiska betalningar eller obestyrkta fördelningsprocent har införts. Betaltjänsterna har egna villkor och integritetspolicyer. Den inbyggda stöddialogen ersätter inte appens befintliga licens och beskriver inte appen som öppen källkod.


## Backup lagras alltid inuti appmappen

Alla **nya** säkerhetskopior lagras under appens `backups/`: `releases/` för programuppdateringar, `galleries/` för gallerigenerering, `editor/` för omsparade gallerier och `config/` för roterade/korrupta inställningsfiler. Inställningarnas aktiva filer ligger fortsatt i användarens konfigurationsmapp; deras nya backupkopior gör det inte. Kan appens backupmapp inte användas väljs aldrig någon extern reservplats. Symlänkar som leder backupmappar utanför appmappen avvisas. Rollback accepterar bara releasebackuper inom rätt apps `backups/releases/`, inte äldre externa backupmappar.

Även gallerier på annan disk säkerhetskopieras inuti appmappen. Då krävs en fullständig kopia över diskarna, vilket kan ta tid och extra diskutrymme. Tillfälliga exportarbetsmappar vid destinationen och OS-temporära nedladdningsfiler är arbetsfiler, inte permanenta säkerhetskopior; de följer sina befintliga städregler. Tidigare skapade externa säkerhetskopior flyttas/raderas **inte** automatiskt. Den här policyn ersätter äldre beskrivningar av syskonbackuper.

## Ingen konsol vid start eller skanning

Windows-startaren `Starta.vbs` kör dolt och väljer `pythonw.exe` när den finns. Alla egna Python-processanrop använder nu `quiet_process`, även Python-upptäckt/vidarestart, FFmpeg/FFprobe, hårdvaru- och filkontroller, skanning, pip och uppdateringshjälparen. På Windows läggs `CREATE_NO_WINDOW` till och `CREATE_NEW_CONSOLE` avvisas; befintliga pipes, loggutmatning, timeout och avbrott bevaras. Ingen global monkey-patch av tredjepartsbibliotek införs. Avsiktligt öppnade GUI-program som webbläsare och Utforskaren ska fortfarande visas.

Vanlig start, autostart och automatisk omstart börjar fortsatt minimerat/dolt till systemfältet, utan inställningsknapp för motsatsen. Om systemfält inte kan användas finns minimerad aktivitetsfältsfallback. Uttryckliga användaråtgärder (Visa via tray, återställningsverktyget `visa_app.pyw` eller andra instansens SHOW) får öppna appfönstret. En terminal som användaren själv startat på Linux/macOS är inte ett nytt fönster från appen och stängs inte av appen. Windows-fönsterblink är inte visuellt testat i denna miljö; tester verifierar policyargumenten och att egna processstarter inte kringgår dem.

### Uppdaterad skrivbordsdesign

Appens basfont väljs bland installerade Segoe UI Variable/Segoe UI, SF Pro Text, Inter, Noto Sans och DejaVu Sans, med Tk-standard som fallback. Bastext och menyer använder 11 punkter och respekterar Tk:s befintliga DPI-skalning; inga fonter laddas ned. Arbetsytan har större rubrik, konsekventa bildikoner med textetiketter (inga emoji-beroenden) och temafärger som uppdateras även på canvas, paneler och statusfält när ljust/mörkt/system byts. Ikonerna genereras lokalt och färgas om med temat.

Fönstret kan vid återställning utnyttja upp till 1760 × 1100 på stora skärmar, med skärmmarginaler och tidigare sparad mindre storlek bevarad. På små skärmar begränsas storleken fortsatt; navigationen byter till flera rader och arbetsytans paneler staplas vid smal bredd. Startbeteendet är oförändrat minimerat. Interaktiv kontroll av typsnitt, DPI och flera bildskärmar behövs fortfarande på respektive operativsystem.
