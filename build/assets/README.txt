# Build Assets för Tobbes v2

## app.ico
Windows-ikon för applikationen.

Krav:
- Format: .ico
- Storlekar: 16x16, 32x32, 48x48, 256x256 pixlar
- Innehåll: FA-TEC logo eller projektikon

Skapa ikon:
1. Designa ikon i bildeditor
2. Konvertera till .ico format
3. Online verktyg: https://www.icoconverter.com/
4. Spara som: build/assets/app.ico

## version.txt
Versionsinformation för applikationen.

Format:
VERSION=2.0.0
BUILD_DATE=2025-10-07
BUILD_NUMBER=1

## Nuläge
app.ico är VALFRI - Nuitka-build fungerar utan ikon.

För produktionsbuilds på Windows:
1. Skapa app.ico enligt instruktionerna ovan
2. Placera i build/assets/app.ico
3. Nuitka build inkluderar automatiskt ikonen (se nuitka_build.py:102)

För macOS/Linux builds: Ikon används ej.
