# Arbetsregler för FTP Uploader

Läs denna fil vid början av varje ny chatt och före ändringar. Reglerna är användarens bestående projektkrav; de ersätter inte högre prioriterade instruktioner eller sessionens branchlås. En nedskriven regel betyder inte att motsvarande funktion redan är implementerad.

## Hårda regler: Git och publicering

- Arbeta endast på sessionens aktiva arbetsbranch. Nuvarande avsedda enda arbets-/standardbranch är `arena/c3ec36f2-ftp-uploader`. Kontrollera Arena-branchinformationen, `git branch --show-current` och GitHubs default branch vid ny chatt. Vid konflikt: stoppa branchoperationen och förklara, byt inte branch själv.
- Arbeta aldrig mot `main`: ingen commit, push, updaterkälla eller merge dit. Skapa inte PR. Merga aldrig. Byt eller skapa inte branch i en branchlåst Arena-session.
- Användaren vill ha endast en kvarvarande branch och samma standardbranch över chattar. Radera inte brancher om sessionens verktygs-/branchrestriktioner förbjuder detta. Rapportera vad som återstår; påstå inte att städningen är utförd.
- Vid kodändring: testa relevant funktion och regressioner, granska diff, pusha endast aktiv branch och uppdatera befintlig GitHub Release `v1.0.0`, utan versionshöjning. Markera releasen Latest. Följ upp faktisk publiceringsstatus; inget tyst misslyckande.
- Appen hämtar från avsedd GitHub Release, aldrig från main-tip eller genom Git-merge. Updatern ska jämföra faktiska programfiler/innehåll, även om tagg eller commit-identitet återanvänds; enbart ändrad releasebeskrivning ska inte utlösa installation.
- Lagra aldrig GitHub-/FTP-hemligheter i koden eller chatten. Använd befintlig autentisering.
- När användaren anger nya krav med ”regel” eller ”hård regel”: uppdatera denna fil och publicera dokumentationsändringen till GitHub. Lägg inte till gissade krav.

## Hårda regler: uppdatering, start och säkerhet

- Inget nytt terminal-/konsolfönster vid start, skanning, FFmpeg/FFprobe, beroendekontroller eller uppdateringar. Behåll den gemensamma konsolfria processpolicyn.
- Vanlig start, autostart och automatisk omstart ska alltid börja minimerat; ingen av/på-inställning. Uttryckligt Visa via tray/återställningsverktyg/andra instansens SHOW får öppna appen. Native minimerad fallback om tray saknas.
- Endast en appinstans. Automatisk dubbelstart ska inte öppna huvudfönstret.
- Önskat schema: automatisk kontroll/uppdatering klockan 00:00 lokal tid varje dag, endast om uppdatering finns. Missad tid och sommartid ska hanteras utan loopar. Detta ersätter tidigare releasekontrollschema; verifiera implementationen innan det anges som klart. Python-/paketunderhåll ska inte oavsiktligt få ett nytt schema.
- Alla pågående jobb ska automatiskt stoppas säkert före installation. Ingen delvis publicerad export eller hängande FFmpeg-process.
- Efter uppdateringar ska automatisk återstart/start ske. Vid fel: tydlig logg och säker återställning; ingen okontrollerad omstartsloop.
- Förbättra updaterns integritetskontroll och transaktionella installation. Påstå inte att en osignerad release är signerad.
- Alla nya backuper måste ligga inom appens `backups/`, även om galleri/inställningar ligger på annan disk. Ingen extern fallback och inga symlänksutvägar. Radera inte gamla externa kopior automatiskt.
- Ta bort den aktuella uppdateringsbackupen först efter verifierat lyckad installation och godkänd uppstart/hälsokontroll. Behåll den vid fel eller osäkerhet. Detta ger inte tillstånd att radera galleri-/konfigurationsbackuper.
- Ingen destruktiv rensning av användarens projekt, original eller andra arbetsfiler.

## Loggar

- Gårdagens ordinarie loggar ska arkiveras. Arkiverade ordinarie loggar ska rensas efter 7 dagar (ersätter tidigare 14 dagar).
- Det ska finnas komplett applogg och en separat fellogg över alla aktiva, olösta fel.
- Åtgärdade fel ska tas bort från den aktiva felloggen; användaren ska kunna markera/rensa åtgärdade fel. Ålder är inte bevis för att ett fel är åtgärdat.
- Rensa aldrig aktiva fel genom vanlig arkivretention. Ingen tangentbordsövervakning eller hemligheter i loggar.

## Design, bildkvalitet och resurser

- Anpassa layout, dialoger, kolumner, text, knappar och ikoner till tillgänglig skärm/fönsterbredd och DPI. Allt viktigt ska gå att nå; minimera onödig scroll utan att gömma funktioner eller krympa text till oläsbarhet.
- När användaren öppnar huvudfönstret: önskad maximal användbar höjd för aktuell skärm och anpassad bredd; detta får inte ändra regeln om minimerad start. Undvik att täcka aktivitetsfältet.
- Skarp text/font, bilder, kolumner och ikoner; undvik onödig uppskalning och grumlig bitmapförstoring. Låt inte flera DPI-mekanismer dubbelskala UI.
- Enhetlig skarp logotyp överallt, med redigerbar vektor för tryck och högkvalitativa ikoner. Behåll cyan/violett/rosa varumärkesriktning om inte användaren ändrar den.
- Förbättra minneshantering, hastighet och energiförbrukning. Använd begränsade cacher/köer, stäng bildresurser och avbryt föråldrade jobb. Mät innan procentuella prestandavinster utlovas.
- Kolumner ska kunna sorteras/flyttas där appen använder kolumner; bevara kopplingen till rätt fil vid sortering.
- Profiler ska ha egen underflik under Inställningar endast i appar/funktioner som faktiskt använder profiler. Uppfinn inte en ny profilmodell enbart för att uppfylla en generell appregel.
- Återställ saknat val av ”ruta” i projektskaparen endast om appen tidigare hade det. Betydelsen är ännu oklar i detta repo: undersök äldre implementation eller be om precisering, gissa inte.
- Ingen tyst borttagning av beroenden, funktioner eller gränssnitt. Uppfinn inte innebörden av ”REQ-K4”; någon definition är inte given här.

## Förslag och kommunikation

- Skriv förslagslistor direkt i chatten, inte enbart i en fil.
- När användaren ber om 25 nya förslag: ge 25 tydligt numrerade, nya förslag. Undvik redan implementerade/tidigare föreslagna funktioner. Påstå inte utan aktuell evidens att konkurrenterna saknar dem eller att efterfrågan är verifierad.
- Efter 10 nya användarmeddelanden ska en ny lista med 10 icke återanvända förslag visas i chatten. Räkna användarmeddelanden, inte verktygsanrop. Vid ny chatt utan komplett räknare: redovisa osäkerheten i stället för att låtsas ha ett exakt historiskt antal.
- Räknarankare: användarmeddelandet som begärde denna AGENTS.md är meddelande 0 för nästa tiomeddelandecykel. Användare kan uttryckligen begära nya förslag tidigare. Uppdatera ankare/räknare vid nästa lista.
- Svara på svenska. Skilj mellan implementerat, testat, visuellt verifierat och återstående arbete. Testresultat med skips är inte full dependency-enabled verifiering.

## Befintliga produktskydd

- Multi-OS; inga privata venv-miljöer. Befintlig Python ska inte uppgraderas av startaren. Installationsförslag bara om Python saknas. Behåll Starta.vbs/Starta.sh.
- Inställningar per användare utanför repot, men nya inställningsbackuper inom appmappen.
- Originalvideor ska kunna exporteras automatiskt även utan stillbilder. Videominiatyrer ska komma från videon.
- Vattenstämpel uttryckligt opt-in, standard av.
- Stöddialog under Hjälp: endast lokal Swish-QR till 0721817177; PayPal och Ko-fi som direkta knappar, inga QR för dem. Frivilligt belopp, ingen betalvägg eller spårning.
- Copyright Rickard Längkvist © 2026. Behåll projektets användningslicens för privat/kommersiellt bruk; kalla den inte open source.

## Kontroll före ”klart”

1. Läs regler, aktuell branch och befintliga ändringar. Skriv inte över användararbete.
2. Kontrollera relevant kod och befintliga tester; verifiera app-specifik tillämpning.
3. Kör tester och statisk kontroll. Rapportera vad som inte kunnat provas (särskilt Windows/Tk, DPI och tray).
4. Granska diff och oavsiktliga genererade filer/hemligheter.
5. Publicera på endast aktiv branch och befintlig Latest-release enligt ovan; ingen PR eller merge.
6. Beskriv ärligt kvarvarande krav. AGENTS.md är en arbetsinstruktion, inte ett bevis på att alla funktioner finns.
