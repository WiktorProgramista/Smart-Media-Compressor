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
```

---

## 🚀 Szybki start

```bash
# 1. Sam raport — nic nie zmienia
python compress_videos.py --path ~/Movies

# 2. Kompresja plików z rekomendacją (C/D/F)
python compress_videos.py --path ~/Movies --apply

# 3. Lepsza kompresja (głośniej, wolniej)
python compress_videos.py --path ~/Movies --apply --encoder libx265 --crf 22
```

---

## ⚙️ Opcje CLI — szczegółowy opis parametrów

Poniżej pełna dokumentacja każdego argumentu. Kolejność w tabeli odpowiada
kolejności w `--help`.

### `--path` *(wymagane)*

| | |
|---|---|
| **Typ** | `string` (ścieżka) |
| **Wymagane** | ✅ TAK |
| **Domyślna** | *(brak — musisz podać)* |
| **Przykład** | `--path ~/Movies` |

Katalog startowy do przeskanowania. Przeszukiwanie jest **rekurencyjne** — skrypt
wejdzie do wszystkich podkatalogów i znajdzie każdy plik wideo z listy obsługiwanych
rozszerzeń (`.mov`, `.mp4`, `.avi`, `.mkv`, `.wmv`, `.flv`, `.webm`, `.m4v`,
`.3gp`, `.mpg`, `.mpeg`, `.mts`, `.m2ts`, `.ts`, `.vob`).

Automatycznie pomija:

- katalogi zaczynające się od `.` (np. `.git`, `.Trash`)
- `__pycache__` i `node_modules`
- sam katalog wynikowy `--output` (żeby nie kompresować własnych wyników)

**Przykłady:**

```bash
--path ~/Movies                    # cała biblioteka
--path ~/Movies/2023               # tylko jeden rok
--path /Volumes/Dysk/Filmy         # zewnętrzny dysk
--path .                           # bieżący katalog
```

Jeśli ścieżka nie istnieje — skrypt przerwie działanie z błędem `❌ Katalog nie istnieje`.

---

### `--output`

| | |
|---|---|
| **Typ** | `string` (ścieżka) |
| **Wymagane** | ❌ NIE |
| **Domyślna** | `generated_output` |
| **Przykład** | `--output /Volumes/Dysk/Filmy_compressed` |

Katalog, do którego trafią skompresowane pliki. Zostanie utworzony, jeśli nie istnieje.

**Kluczowa zasada:** zachowana jest **ta sama struktura katalogów i nazwy plików**
co w `--path`. Czyli jeśli masz:

```
~/Movies/2023/wakacje.mov
```

to wynik znajdzie się w:

```
<output>/2023/wakacje.mov
```

**Kiedy zmieniać domyślną wartość:**

| Sytuacja | Zalecenie |
|---|---|
| Testujesz na małej próbce | `--output /tmp/test` |
| Chcesz trzymać wyniki na innym dysku | `--output /Volumes/Backup/Movies` |
| Chcesz porównać dwa enkodery | `--output /tmp/bench_hw` i `--output /tmp/bench_265` |
| Domyślne `generated_output` Ci wystarcza | *(pomiń opcję)* |

Katalog `generated_output` jest pomijany przy skanowaniu wejścia, więc kolejne
uruchomienia nie skompresują już-skompresowanych plików.

---

### `--apply`

| | |
|---|---|
| **Typ** | `flag` (boolean) |
| **Wymagane** | ❌ NIE |
| **Domyślna** | `False` (tylko raport) |
| **Przykład** | `--apply` |

**Bez tej flagi skrypt tylko analizuje i wypisuje raport — nic nie kompresuje.**

To celowe zabezpieczenie: domyślne uruchomienie jest **całkowicie bezpieczne**.

Z `--apply` skrypt:

1. Wybierze pliki z oceną **C / D / F** (te, które warto skompresować)
2. Uruchomi `ffmpeg` dla każdego z nich
3. Zapisze wyniki do `--output` (mirror struktury)
4. **Nie tknie oryginałów**

**Rekomendowany workflow:**

```bash
# Krok 1: najpierw raport (bez --apply)
python compress_videos.py --path ~/Movies

# Krok 2: przeczytaj raport, sprawdź sumaryczne oszczędności

# Krok 3: jeśli OK — dodaj --apply
python compress_videos.py --path ~/Movies --apply
```

---

### `--force`

| | |
|---|---|
| **Typ** | `flag` (boolean) |
| **Wymagane** | ❌ NIE |
| **Domyślna** | `False` |
| **Przykład** | `--apply --force` |

Bez `--force` kompresowane są tylko pliki z oceną **C / D / F** (rekomendacja skryptu).
Z `--force` skrypt kompresuje **również pliki A i B** — czyli te, które już są
dobrze skompresowane.

⚠️ **OSTRZEŻENIE:** rekompresja plików A/B to **strata jakości przy marginalnym zysku**:

- plik A (już zoptymalizowany) — możesz wręcz **zwiększyć** rozmiar
- plik B (blisko optimum) — zysk rzędu 5–15%, ale jakość spadnie

**Kiedy używać `--force`:**

- Chcesz ujednolicić kodek w całej bibliotece (np. wszystko na HEVC)
- Masz konkretny powód (np. stary odtwarzacz nie czyta H.264)
- Świadomie akceptujesz stratę jakości

**Kiedy NIE używać:**

- Standardowa kompresja biblioteki → użyj bez `--force`
- Chcesz zachować maksimum jakości → użyj bez `--force`

---

### `--encoder`

| | |
|---|---|
| **Typ** | `choice` z 3 opcji |
| **Wymagane** | ❌ NIE |
| **Domyślna** | `videotoolbox` |
| **Dozwolone** | `videotoolbox`, `libx265`, `libx264` |
| **Przykład** | `--encoder libx265` |

Wybór enkodera wideo. Każdy ma inne właściwości.

#### `videotoolbox` (domyślne)

Używa **dedykowanego chipu Apple Media Engine** (VideoToolbox API). Dostępny
na Macach z Apple Silicon (M1/M2/M3/M4) oraz nowszych Intelach.

- ⚡ **Bardzo szybki** (5–10× szybszy od libx265)
- 🔇 **Cichy** — CPU prawie nie pracuje, wentylatory się nie budzą
- 🔋 **Niskoenergetyczny** — świetny do laptopów na baterii
- 📦 Używa H.265 (HEVC) z `-q:v 60`
- ⚠️ Plik ~10–15% większy niż przy `libx265` CRF 24

**Kiedy:** codzienne użycie, nożyce do filmów z wakacji, praca na baterii.

#### `libx265`

Software'owy enkoder H.265 (HEVC) z projektu x265.

- 📦 **Najlepsza kompresja** — najmniejsze pliki przy tej samej jakości
- 🐌 **Wolny** (5–10× wolniejszy od videotoolbox)
- 🔊 **Głośny** — obciąża wszystkie rdzenie CPU
- 🎚️ Sterowany przez `--crf` (domyślnie 24) i `--preset`
- ✅ Szeroka zgodność z nowoczesnymi odtwarzaczami

**Kiedy:** archiwizacja, gdy zależy na każdym GB, kompresja overnight.

#### `libx264`

Software'owy enkoder H.264 (AVC) z projektu x264.

- 📦 Plik ~40% większy od HEVC przy tej samej jakości
- ✅ **Maksymalna kompatybilność** — działa na starych TV, DVD, odtwarzaczach
- 🐌 Wolny (ale szybszy od libx265)
- 🔊 Głośny — obciąża CPU

**Kiedy:** filmy dla starszych urządzeń, kompatybilność z Blu-ray, telewizory
bez HEVC.

#### Porównanie

| Enkoder | Szybkość | Głośność | Rozmiar | Kiedy |
|---|---|---|---|---|
| `videotoolbox` | ⚡⚡⚡⚡ | 🔇 | 1.10× | Codziennie |
| `libx265` | ⚡ | 🔊 | **1.00×** | Maks. oszczędność |
| `libx264` | ⚡⚡ | 🔊 | 1.40× | Kompatybilność |

*(współczynniki rozmiaru względem libx265 przy tej samej jakości wizualnej)*

---

### `--crf`

| | |
|---|---|
| **Typ** | `int` (0–51) |
| **Wymagane** | ❌ NIE |
| **Domyślna** | `24` |
| **Zakres** | `0` (bezstratna, olbrzymia) – `51` (maks. kompresja, okropna) |
| **Przykład** | `--crf 22` |

**CRF = Constant Rate Factor** — steruje jakością w enkoderach `libx265` i `libx264`.
**Ilość bitów jest automatycznie dopasowywana**, żeby utrzymać stałą jakość wizualną.

Działa **tylko dla `libx265` i `libx264`**. Dla `videotoolbox` jest ignorowany
(ten używa `-q:v 60`).

#### Skala CRF

| CRF | Jakość | Typowy wynik | Zastosowanie |
|---|---|---|---|
| 0 | matematycznie bezstratna | 100%+ | Nigdy (ogromne pliki) |
| 18 | praktycznie bezstratna | ~90% | Archiwum studyjne |
| 20 | bardzo wysoka | ~80% | Mastering |
| **22** | **bardzo dobra** | **~70%** | **Jakość priorytetem** |
| **24** | **dobra** | **~55%** | **Zbalansowany (domyślne)** |
| **26** | **dobra, zauważalna kompresja** | **~45%** | **Duże archiwum** |
| 28 | akceptowalna | ~35% | Gdy mało miejsca |
| 30 | zauważalna utrata przy ruchu | ~25% | Tylko gdy trzeba |
| 35+ | widoczna degradacja | ~15% | Nie polecam |
| 51 | fatalna | ~5% | Nigdy |

**Reguła praktyczna:** każde **+6 CRF ≈ 2× mniejszy plik** przy zachowaniu
subiektywnie podobnej jakości. Czyli CRF 24 → 30 to ~połowa rozmiaru.

#### Uwaga o H.265 vs H.264

To samo CRF daje **różną jakość** dla różnych kodeków:

- **CRF 24 w H.265** ≈ **CRF 20 w H.264** (jeśli chodzi o subiektywną jakość)
- Czyli H.265 przy tym samym CRF da **mniejszy plik** przy tej samej jakości

Dlatego domyślne 24 jest zbalansowane dla `libx265`, ale dla `libx264` może być
trochę za wysokie — rozważ `--crf 20` lub `--crf 22` gdy używasz `libx264`.

**Przykłady:**

```bash
--encoder libx265 --crf 20    # najwyższa jakość (dla archiwum)
--encoder libx265 --crf 24    # zbalansowane (domyślne)
--encoder libx265 --crf 28    # dużo mniejsze pliki, wciąż OK
--encoder libx264 --crf 20    # H.264 w dobrej jakości
--encoder libx264 --crf 23    # H.264 zbalansowane
```

---

### `--preset`

| | |
|---|---|
| **Typ** | `string` |
| **Wymagane** | ❌ NIE |
| **Domyślna** | `medium` |
| **Dozwolone** | `ultrafast`, `superfast`, `veryfast`, `faster`, `fast`, `medium`, `slow`, `slower`, `veryslow` |
| **Przykład** | `--preset slow` |

**Preset** decyduje jak długo enkoder „myśli" o każdym pikselu. Działa **tylko dla
`libx265` i `libx264`**.

- **Szybsze presety** → mniej czasu CPU → większy plik (przy tym samym CRF)
- **Wolniejsze presety** → więcej analizy → mniejszy plik (przy tym samym CRF)

To **nie jest** kompromis jakość/rozmiar w sensie subiektywnym — subiektywna jakość
przy danym CRF jest podobna. Preset zmienia **jak efektywnie enkoder wykorzystuje
dostępny bitrate**.

#### Tabela presetów

| Preset | Szybkość | Użycie CPU | Rozmiar przy CRF 24 | Uwagi |
|---|---|---|---|---|
| `ultrafast` | 10× | niskie | +15% | Do testów, nie do produkcji |
| `superfast` | 8× | niskie | +12% | |
| `veryfast` | 5× | średnie | +7% | **Dobry dla laptopów** |
| `faster` | 3× | średnie | +4% | |
| `fast` | 2× | wyższe | +2% | **Kompromis szybkość/rozmiar** |
| **`medium`** | **1×** | **wysokie** | **baseline** | **Domyślne, zalecane** |
| `slow` | 0.4× | bardzo wysokie | −5% | **Gdy zależy na rozmiarze** |
| `slower` | 0.25× | ekstremalne | −7% | |
| `veryslow` | 0.15× | ekstremalne | −8% | Marnowanie czasu za grosze |

#### Kiedy jaki preset

| Sytuacja | Preset |
|---|---|
| Laptop na baterii, chcę ciszy | `--preset veryfast` |
| Standardowa kompresja | `--preset medium` (domyślne) |
| Chcę szybciej, akceptuję +2% | `--preset fast` |
| Jednorazowa archiwizacja, kompresja przez noc | `--preset slow` |
| Benchmark / maksymalne oszczędności | `--preset veryslow` (rzadko warte) |

#### Uwaga o czasie

Na Macu M2 z 8 rdzeniami, film 5-minutowy 1080p H.264 → H.265:

| Preset | Czas | Uwaga |
|---|---|---|
| `ultrafast` | ~15s | |
| `veryfast` | ~40s | |
| `medium` | ~2 min | |
| `slow` | ~5 min | |
| `veryslow` | ~13 min | |

Różnica rozmiaru między `medium` a `veryslow`: **~8%**. Różnica czasu: **6×**.
Rzadko warto.

---

### `--min-size-mb`

| | |
|---|---|
| **Typ** | `float` |
| **Wymagane** | ❌ NIE |
| **Domyślna** | `10.0` |
| **Zakres** | `0` – ∞ |
| **Przykład** | `--min-size-mb 100` |

Pomija pliki **mniejsze** niż X megabajtów. Zapobiega marnowaniu czasu na
kompresowanie małych klipów, gdzie zysk byłby rzędu kilku MB.

#### Dlaczego to ważne

Masz 500 filmików z telefonu po 8 MB każdy. Łącznie 4 GB. Kompresja każdego z nich:

- **da zysk** rzędu 30–50% (czyli ~2.5 MB każdy)
- **zajmie** po ~5 sekund każdy → **~40 minut** łącznie
- **odzyskasz** ~1.5 GB

Ale jeśli masz jeden film 5 GB — kompresja:

- **da zysk** rzędu 60% (~3 GB!)
- **zajmie** ~15 minut
- **odzyskasz** 3 GB

Wniosek: lepiej filtrować duże pliki.

#### Rekomendacje

| Zastosowanie | Wartość |
|---|---|
| Test / zabawa | `--min-size-mb 1` |
| Standardowe użycie | `--min-size-mb 10` (domyślne) |
| Chcę tylko duże pliki | `--min-size-mb 100` |
| Chcę tylko bardzo duże | `--min-size-mb 500` |
| Kompresuj absolutnie wszystko | `--min-size-mb 0` |

**Uwaga:** pliki poniżej progu są **pomijane w raporcie** — nie zobaczysz ich
nawet z oceną.

---

### `--min-duration`

| | |
|---|---|
| **Typ** | `float` |
| **Wymagane** | ❌ NIE |
| **Domyślna** | `5.0` |
| **Zakres** | `0` – ∞ (sekundy) |
| **Przykład** | `--min-duration 30` |

Pomija klipy **krótsze** niż X sekund. Chroni przed sytuacjami gdzie:

- kilka sekund filmu, ale enkodowanie i tak zajmuje X sekund
- krótkie klipy są zwykle memami/zapiskami — strata jakości nie warta zysku
- Live Photos, Boomerangi, klipy z Instagrama

#### Rekomendacje

| Zastosowanie | Wartość |
|---|---|
| Wszystko, nawet sekundowe | `--min-duration 0` |
| Standardowe użycie | `--min-duration 5` (domyślne) |
| Tylko „prawdziwe" filmy | `--min-duration 30` |
| Tylko filmy pełnometrażowe | `--min-duration 300` |

---

## 📊 Jak działa analiza

### Metryka BPP (Bits Per Pixel)

Dla każdego pliku skrypt liczy **bity na piksel**:

```
BPP = bitrate / (szerokość × wysokość × fps)
```

To uniwersalna miara „jak bardzo plik jest skompresowany":

| BPP | Znaczenie |
|---|---|
| `> 0.15` | plik „puchnie" — dużo do zaoszczędzenia |
| `0.08 – 0.15` | duży potencjał |
| `0.05 – 0.08` | umiarkowany |
| `0.03 – 0.05` | już dobrze skompresowany |
| `< 0.03` | zoptymalizowany — nie ruszać |

### Kodek-aware

Ten sam BPP znaczy co innego dla H.264 i H.265. Skrypt normalizuje przez
`eff_bpp = bpp / codec_factor`:

| Kodek | Factor | Uwaga |
|---|---|---|
| `h264` | 1.00 | baseline |
| `hevc` / `h265` | 0.65 | ~35% mniej bitrate przy tej samej jakości |
| `av1` | 0.45 | najlepsza efektywność |
| `vp9` | 0.65 | |
| `vp8` | 1.10 | |
| `mpeg4` (DivX/Xvid) | 1.60 | stary, mało efektywny |
| `msmpeg4v3` | 1.80 | |
| `wmv3` | 1.80 | |
| `mpeg2video` | 2.00 | archaiczny |
| `prores` / `dnxhd` | 4.00 | edycyjne, olbrzymie |

### Docelowy BPP zależny od rozdzielczości

Większa rozdzielczość = więcej detali = bardziej efektywna kompresja.

| Wysokość | Target BPP |
|---|---|
| 240p | 0.080 |
| 480p | 0.065 |
| 720p | 0.055 |
| **1080p** | **0.048** |
| 1440p | 0.043 |
| **4K** | **0.038** |
| 8K | 0.032 |

### Przewidywanie rozmiaru

```
predicted_size = current_size × (target_bpp / eff_bpp)
```

Ograniczone do maksymalnie `-15%` (rekompresja do HEVC nie da więcej bez utraty jakości).

---

## 🎓 Ocena A–F

```
A: eff_bpp ≤ target × 0.9    → już zoptymalizowany, POMIŃ
B: eff_bpp ≤ target × 1.2    → blisko optimum, opcjonalnie
C: eff_bpp ≤ target × 2.0    → umiarkowany potencjał
D: eff_bpp ≤ target × 3.5    → duży potencjał
F: eff_bpp > target × 3.5    → bardzo duży potencjał
```

### Reguły specjalne

- **ProRes / DNxHD / MPEG-2** → zawsze **F**
- **HEVC / AV1** już przy optimum → wymuszone **A**

### Znaczenie ocen

| Ocena | Co znaczy | Rekomendacja |
|---|---|---|
| **A** | Już zoptymalizowany | **NIE kompresuj** |
| **B** | Blisko optimum | Kompresja da niewiele (~5–15%) |
| **C** | Umiarkowany potencjał | Warto rozważyć (20–40%) |
| **D** | Duży potencjał | Warto skompresować (40–60%) |
| **F** | Bardzo duży potencjał | Wyraźnie warto (>60%) |

---

## 📁 Struktura wynikowa

### Wejście

```
~/Movies/
├── 2020/
│   └── wakacje.mov
├── 2023/
│   ├── urodziny.mp4
│   └── ślub.mp4
└── śmietnik/
    └── stary_plik.avi
```

### Wynik po `--apply`

```
~/Movies/generated_output/
├── 2020/
│   └── wakacje.mov          ← ta sama nazwa, skompresowany
├── 2023/
│   ├── urodziny.mp4
│   └── ślub.mp4
└── śmietnik/
    └── stary_plik.avi
```

- ✅ Ta sama nazwa pliku
- ✅ Ta sama struktura katalogów
- ✅ Katalog `generated_output/` pomijany przy kolejnych skanach
- ✅ Oryginały nietknięte

---

## 💾 Co jest zachowane

| Element | Zachowane? | Jak |
|---|---|---|
| EXIF (Make, Model, DateTimeOriginal) | ✅ | `-map_metadata 0` |
| GPS | ✅ | `-map_metadata 0` |
| Container metadata | ✅ | `-map_metadata 0` |
| Rozdziały (chapters) | ✅ | `-map_chapters 0` |
| Data modyfikacji (mtime) | ✅ | `os.utime()` |
| Data dostępu (atime) | ✅ | `os.utime()` |
| Nazwa pliku | ✅ | bez zmian |
| Struktura katalogów | ✅ | mirror od `--path` |
| Data utworzenia (macOS birthtime) | ⚠️ | tylko częściowo |
| Wszystkie ścieżki audio | ❌ | tylko pierwsza |
| Napisy / subtitle tracks | ❌ | nie kopiowane |
| Wiele kątów / multiple video | ❌ | tylko pierwszy |

---

## 🔧 Szybka ściągawka

| Chcę… | Komenda |
|---|---|
| Zobaczyć raport | `--path ~/Movies` |
| Skompresować C/D/F | `--apply` |
| Cicho (Mac) | `--encoder videotoolbox` *(domyślne)* |
| Maksymalnie małe pliki | `--encoder libx265 --crf 26 --preset slow` |
| Szybko, „wystarczająco dobrze" | `--apply --preset veryfast` |
| Tylko duże pliki | `--min-size-mb 500` |
| Tylko długie filmy | `--min-duration 60` |
| Inny katalog wynikowy | `--output /inny/katalog` |
| Wszystko, nawet A/B | `--force` |
| Stary TV | `--encoder libx264 --crf 22` |

---

## ❓ FAQ

**Czy mogę przerwać w trakcie?**
Tak. Uruchom ponownie — skrypt pomija pliki już istniejące w `generated_output/`.

**Co się stanie z oryginałami?**
Nic. Są nietknięte. Skrypt nigdy nie modyfikuje oryginałów.

**Dlaczego pliki z oceną A są pomijane?**
Bo są już dobrze skompresowane. Rekompresja da zysk kilku % albo wręcz zwiększy
rozmiar, a **nieodwracalnie pogorszy jakość**. Jeśli chcesz — `--force`.

**Dlaczego wentylatory wyją?**
Używasz `libx265` lub `libx264`. Dla ciszy użyj `videotoolbox` (sprzętowy).

**Czy VideoToolbox daje gorszą jakość?**
Przy tym samym rozmiarze o ~10–15%, ale jest 5–10× szybszy, nie obciąża CPU
i nie budzi wentylatorów.

---

## 🐛 Znane ograniczenia

- Tylko **pierwsza ścieżka audio**
- **Napisy** nie są kopiowane
- **Data utworzenia pliku (macOS `st_birthtime`)** nie jest ustawiana przez `os.utime`
- **Przewidywany rozmiar** to szacunek (±20%)
- Tylko **wideo**, nie zdjęcia
- Windows/Linux: brak VideoToolbox → używaj `libx265` / `libx264`

---

## 📄 Licencja

MIT — używaj, modyfikuj, dziel się.

---

**Miłego odzyskiwania miejsca!** 🎉
