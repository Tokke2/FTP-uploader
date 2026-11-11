# FTP-uploader

Python-app för Windows, macOS och Linux. Ingen virtuell miljö, BAT, VBS, shellstartare eller Git-installation behövs för att köra appen.

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
Manuell uppdatering inifrån appen schemaläggs till nästa start via `start.pyw`, så att aktiv kod inte byts ut medan appen körs.

Installationen använder bara Python. Den kontrollerar tagg mot `APP_VERSION`, arkivets sökvägar, storleksgränser och Python-syntax innan filer byts ut.
Programkod, `requirements.txt` och ikoner ersätts. Inställningar, exporter och andra filer lämnas orörda.
Gamla programfiler sparas i en syskonmapp med `.release-backup-<tid>` i namnet. Vid installationsfel försöker uppdateraren återställa alla ändrade filer.
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

Sparning sker först i en temporär mapp. Därefter flyttas den gamla exporten till en syskonmapp med `.backup-<tid>` i namnet och ersätts av den nya.
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
