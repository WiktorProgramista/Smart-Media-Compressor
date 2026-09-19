# 🧠 Smart Media Compressor

Inteligentny kompresor wideo, który **najpierw analizuje** Twoją bibliotekę filmów,
**ocenia** które pliki warto skompresować (i o ile), a dopiero potem — na Twoją
komendę — kompresuje je z zachowaniem **metadanych**, **nazw** i **struktury
katalogów**. Oryginały zostają nietknięte, wyniki lądują w `generated_output/`.

Domyślnie używa **enkodera sprzętowego Apple (VideoToolbox)** — cisza, szybko
i niskie zużycie energii. Dla lepszej kompresji można przełączyć na `libx265`.

---

## ✨ Cechy

- 🔍 **Analiza przed kompresją** — raport z oceną każdego pliku (A–F)
- 🎯 **Rekomendacje** — kompresuje tylko to, co faktycznie warto
- 🛡️ **Bezpieczeństwo** — oryginały nietknięte, wszystko idzie do `generated_output/`
- 📋 **Metadane** — EXIF, GPS, daty, rozdziały (chapters) zachowane
- 📁 **Nazwy i struktura** — ta sama nazwa pliku, ta sama struktura katalogów
- ⏰ **Timestamps** — data modyfikacji/utworzenia zachowana (`os.utime`)
- 🍎 **Cichy tryb** — sprzętowy enkoder Apple (Media Engine), CPU prawie nie pracuje
- ♻️ **Idempotentny** — pomija pliki już skompresowane (można wznawiać)
- 🚫 **Bez rekompresji stratnej** — pliki już zoptymalizowane (ocena A) są pomijane

---

## 📦 Wymagania

- **Python 3.8+**
- **ffmpeg** + **ffprobe** (w `PATH`)

### Instalacja ffmpeg

```bash
# macOS
brew install ffmpeg

# Linux (Debian/Ubuntu)
sudo apt install ffmpeg

# Windows
# Pobierz z https://ffmpeg.org/download.html i dodaj do PATH
