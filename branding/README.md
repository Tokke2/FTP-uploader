# FTP Uploader – vektorfiler och ikoner

Copyright Rickard Längkvist © 2026. Projektets befintliga licens gäller; DejaVu-typsnittets villkor finns i FONT-LICENSE.txt.

- `logo.svg`: transparent bakgrund, mörk text för ljus yta.
- `logo-dark.svg`: mörk bakgrund, vit text.
- `logo-monochrome.svg`: enfärgad svart version för en färg/gravyr.
- `symbol.svg`: fristående symbol, transparent bakgrund.
- `logo-preview.png`: förhandsvisning, inte tryckoriginal.
- `logo-concept.png`: valt AI-genererat skissunderlag, inte tryckoriginal.

SVG-filerna är omritade vektororiginal med geometriska banor och text konverterad till banor. Ingen inbäddad bitmap, inga externa teckensnitt. Färgpalett: cyan #26DCE0, turkos #12ACC9, lila #8E2ED2, magenta #F445A4, marin #090F26. Skalbara utan pixelbaserad upplösningsgräns.

Filerna använder RGB, inte en specificerad CMYK/spotprofil. För tryck ska tryckeriet välja profil och göra provtryck; neonliknande skärmfärger blir inte identiska med vanlig CMYK. Ingen utfallsmån är inbyggd. Anpassa till trycksakens format innan produktion.

`icon/` innehåller samma identitet som PNG 16/32/64/256/1024, flerupplöst Windows ICO, macOS ICNS och vektororiginal `icon.svg`. ICNS gör inte Python till ett paketerat macOS-program; Dock-identitet kräver vid behov en separat .app-paketering.

Återskapa med `python tools/build_branding.py --font /sökväg/DejaVuSans-Bold.ttf` efter installation av byggberoendena fonttools, resvg-py och Pillow. Dessa behövs inte för att appen ska läsa de färdiga ikonerna.
