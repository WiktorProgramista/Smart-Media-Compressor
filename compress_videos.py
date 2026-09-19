#!/usr/bin/env python3
"""
Smart Media Compressor
======================
Analizuje filmy, ocenia potencjał kompresji (na podstawie BPP, kodeka,
rozdzielczości) i proponuje które pliki warto skompresować — tak, aby
NIE stracić zauważalnie jakości.

Cechy:
  • Analiza przed kompresją (raport + rekomendacje)
  • Ocena A–F dla każdego pliku (jak bardzo marnuje miejsce)
  • Pomija pliki już dobrze skompresowane
  • Zachowuje metadane (EXIF, GPS, daty, rozdziały)
  • Zachowuje nazwy plików i strukturę katalogów
  • Wynik w 'generated_output/' — oryginały nietknięte
  • Używa enkodera sprzętowego Apple (cicho!) lub libx265 (lepsza kompresja)

Wymagania: ffmpeg + ffprobe (brew install ffmpeg)

Użycie:
    # 1. Sam raport — co warto skompresować i ile zaoszczędzisz
    python smart_compress.py --path ~/Movies

    # 2. Kompresja tylko plików z rekomendacją (ocena C, D, F)
    python smart_compress.py --path ~/Movies --apply

    # 3. Kompresja WSZYSTKICH plików (również tych z oceną A/B)
    python smart_compress.py --path ~/Movies --apply --force

    # 4. Tryb software (lepsza kompresja, głośniej, wolniej)
    python smart_compress.py --path ~/Movies --apply --encoder libx265
"""

import os
import sys
import json
import argparse
import subprocess
import time
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Konfiguracja
# ---------------------------------------------------------------------------

VIDEO_EXTENSIONS = {
    '.mov', '.mp4', '.avi', '.mkv', '.wmv', '.flv', '.webm',
    '.m4v', '.3gp', '.mpg', '.mpeg', '.mts', '.m2ts', '.ts', '.vob'
}

DEFAULT_OUTPUT_DIR = 'generated_output'

# Współczynnik efektywności kodeka (im niżej, tym mniej bitrate potrzebuje)
# Wartości względem H.264 = 1.0
CODEC_FACTOR = {
    'h264':  1.00,
    'hevc':  0.65,   # H.265
    'av1':   0.45,
    'vp9':   0.65,
    'vp8':   1.10,
    'mpeg4': 1.60,   # DivX/Xvid
    'msmpeg4v3': 1.80,
    'wmv3':  1.80,
    'mpeg2video': 2.00,
    'prores': 4.0,   # edycyjny, olbrzymi
    'dnxhd': 4.0,
}

# Docelowy "efektywny BPP" dla H.265 przy CRF 24 (jakość bardzo dobra)
# BPP = bity / (szerokość × wysokość × fps) — miara "jak bardzo skompresowane"
TARGET_BPP_BY_HEIGHT = [
    (240,  0.080),
    (480,  0.065),
    (720,  0.055),
    (1080, 0.048),
    (1440, 0.043),
    (2160, 0.038),   # 4K
    (4320, 0.032),   # 8K
]


# ---------------------------------------------------------------------------
# Narzędzia
# ---------------------------------------------------------------------------

def check_tools():
    for tool in ('ffmpeg', 'ffprobe'):
        try:
            r = subprocess.run([tool, '-version'], capture_output=True,
                               text=True, timeout=10)
            if r.returncode != 0:
                print(f"❌ {tool} zwrócił błąd")
                return False
        except FileNotFoundError:
            print(f"❌ {tool} nie znaleziony. Zainstaluj: brew install ffmpeg")
            return False
    return True


def format_size(num_bytes):
    num_bytes = float(num_bytes)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def get_ffprobe(path):
    try:
        r = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_format', '-show_streams',
             '-of', 'json', str(path)],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode != 0:
            return None
        return json.loads(r.stdout)
    except Exception:
        return None


def parse_fraction(s):
    """'30000/1001' -> 29.97; '30/1' -> 30.0"""
    try:
        if '/' in s:
            a, b = s.split('/')
            b = float(b)
            return float(a) / b if b else 0.0
        return float(s)
    except Exception:
        return 0.0


def preserve_timestamps(src, dst):
    try:
        st = os.stat(src)
        os.utime(dst, (st.st_atime, st.st_mtime))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Analiza
# ---------------------------------------------------------------------------

@dataclass
class VideoAnalysis:
    path: str
    size: int
    duration: float
    width: int = 0
    height: int = 0
    fps: float = 0.0
    codec: str = ''
    audio_codec: str = ''
    has_audio: bool = False

    # Wyliczone:
    bpp: float = 0.0            # raw bits-per-pixel
    eff_bpp: float = 0.0        # bpp / codec_factor (porównywalne między kodekami)
    target_bpp: float = 0.0     # docelowy eff_bpp dla H.265 CRF24
    predicted_size: int = 0     # przewidywany rozmiar po konwersji do H.265 CRF24
    savings_pct: float = 0.0    # % oszczędności (0-100)
    grade: str = '?'            # A..F
    reason: str = ''

    @property
    def verdict(self) -> str:
        if self.grade in ('A',):
            return 'POMIŃ'
        if self.grade in ('B',):
            return 'opcjonalnie'
        return 'KANDYDAT'


def target_bpp_for(height):
    for h_max, bpp in TARGET_BPP_BY_HEIGHT:
        if height <= h_max:
            return bpp
    return TARGET_BPP_BY_HEIGHT[-1][1]


def analyze_video(path):
    info = get_ffprobe(path)
    if not info:
        return None

    size = os.path.getsize(path)
    fmt = info.get('format', {})
    streams = info.get('streams', [])

    video_stream = next((s for s in streams if s.get('codec_type') == 'video'), None)
    audio_stream = next((s for s in streams if s.get('codec_type') == 'audio'), None)
    if not video_stream:
        return None

    duration = float(fmt.get('duration') or 0)
    if duration <= 0:
        for s in streams:
            duration = float(s.get('duration') or 0)
            if duration > 0:
                break
    if duration <= 0:
        return None

    # Bitrate: format.bit_rate jest wiarygodne, ale fallback do streamu
    try:
        bitrate = int(fmt.get('bit_rate') or 0)
    except Exception:
        bitrate = 0
    if bitrate <= 0:
        try:
            bitrate = int(video_stream.get('bit_rate') or 0)
        except Exception:
            bitrate = 0
    if bitrate <= 0:
        # wylicz z rozmiaru pliku
        bitrate = int(size * 8 / duration)

    width = int(video_stream.get('width') or 0)
    height = int(video_stream.get('height') or 0)
    fps = parse_fraction(video_stream.get('avg_frame_rate')
                         or video_stream.get('r_frame_rate') or '0')
    codec = (video_stream.get('codec_name') or '').lower()

    a = VideoAnalysis(
        path=path, size=size, duration=duration,
        width=width, height=height, fps=fps,
        codec=codec,
        audio_codec=(audio_stream.get('codec_name') or '').lower() if audio_stream else '',
        has_audio=audio_stream is not None,
    )

    # BPP (bity na piksel) — porównywalne między plikami
    if width > 0 and height > 0 and fps > 0:
        a.bpp = bitrate / (width * height * fps)
    else:
        # Bez fps traktuj jako 25
        fps_use = fps if fps > 0 else 25.0
        a.bpp = bitrate / (width * height * fps_use) if (width and height) else 0

    codec_factor = CODEC_FACTOR.get(codec, 1.0)
    a.eff_bpp = a.bpp / codec_factor if codec_factor else a.bpp

    a.target_bpp = target_bpp_for(height)

    # Przewidywany rozmiar po H.265 CRF 24
    if a.eff_bpp > 0 and a.target_bpp > 0:
        ratio = a.target_bpp / a.eff_bpp
        # Jeśli już jesteśmy poniżej target (bardzo dobrze skompresowany),
        # nie da się zmniejszyć — kompresja może wręcz zwiększyć
        ratio = min(ratio, 0.85)  # nie obiecuj więcej niż -15% przez rekompresję do HEVC
        # Audio zostaw ~10% sumy (nie kompresujemy agresywnie)
        a.predicted_size = int(size * ratio)
        a.savings_pct = max(0.0, (1 - ratio) * 100)
    else:
        a.predicted_size = size
        a.savings_pct = 0.0

    # Ocena A–F
    eb = a.eff_bpp
    tb = a.target_bpp
    if tb <= 0:
        a.grade = '?'
        a.reason = 'brak danych'
    elif eb <= tb * 0.9:
        a.grade = 'A'
        a.reason = f'już zoptymalizowany (eff-bpp {eb:.3f} ≤ target {tb:.3f})'
    elif eb <= tb * 1.2:
        a.grade = 'B'
        a.reason = f'blisko optimum (eff-bpp {eb:.3f}, target {tb:.3f})'
    elif eb <= tb * 2.0:
        a.grade = 'C'
        a.reason = f'umiarkowany potencjał (eff-bpp {eb:.3f})'
    elif eb <= tb * 3.5:
        a.grade = 'D'
        a.reason = f'duży potencjał (eff-bpp {eb:.3f})'
    else:
        a.grade = 'F'
        a.reason = f'bardzo duży potencjał (eff-bpp {eb:.3f})'

    # Bonusy / kary
    if codec in ('prores', 'dnxhd', 'mpeg2video'):
        a.grade = 'F'
        a.reason = f'kodek edycyjny/archaiczny ({codec}) — konwersja mocno zmniejszy plik'
    if codec in ('hevc', 'av1') and eb <= tb * 1.1:
        a.grade = 'A'
        a.reason = f'nowoczesny kodek {codec} — już efektywny'

    return a


# ---------------------------------------------------------------------------
# Raport
# ---------------------------------------------------------------------------

def print_report(analyses):
    if not analyses:
        print("Brak plików do analizy.")
        return

    # Sortowanie: najpierw największe oszczędności bezwzględne
    def saving_bytes(a):
        return max(0, a.size - a.predicted_size)

    analyses_sorted = sorted(analyses, key=saving_bytes, reverse=True)

    print("\n" + "=" * 110)
    print("📊 RAPORT ANALIZY")
    print("=" * 110)
    print(f"{'Ocena':<6}{'Plik':<40}{'Kodek':<8}{'Res.':<11}{'Rozmiar':>11}{'Szac. po':>11}{'Oszcz.':>10}")
    print("-" * 110)

    total_size = 0
    total_pred = 0
    worth_size = 0
    worth_pred = 0

    for a in analyses_sorted:
        total_size += a.size
        total_pred += a.predicted_size

        if a.verdict == 'KANDYDAT':
            worth_size += a.size
            worth_pred += a.predicted_size

        name = os.path.basename(a.path)
        if len(name) > 38:
            name = name[:35] + '...'
        res = f"{a.width}x{a.height}" if a.width else '?'
        codec = a.codec.upper()[:7] if a.codec else '?'
        saving = a.size - a.predicted_size
        saving_abs = format_size(saving) if saving > 0 else '—'
        pct = f"{a.savings_pct:.0f}%" if a.savings_pct > 0 else '—'

        print(f"{a.grade:<6}{name:<40}{codec:<8}{res:<11}"
              f"{format_size(a.size):>11}{format_size(a.predicted_size):>11}"
              f"{saving_abs + ' (' + pct + ')':>18}")

    print("-" * 110)
    print(f"\n📦 RAZEM: {format_size(total_size)} → prognoza {format_size(total_pred)} "
          f"(oszczędność {format_size(total_size - total_pred)}, "
          f"{100 * (total_size - total_pred) / total_size:.1f}%)" if total_size else "")
    print(f"🎯 Warto skompresować (C/D/F): {format_size(worth_size)} → "
          f"{format_size(worth_pred)}  "
          f"oszczędność {format_size(worth_size - worth_pred)} "
          f"({100 * (worth_size - worth_pred) / worth_size:.1f}%)" if worth_size else "")

    # Podsumowanie po ocenach
    from collections import Counter
    counts = Counter(a.grade for a in analyses)
    print(f"\nRozkład ocen: "
          + "  ".join(f"{g}: {counts.get(g, 0)}" for g in 'ABCDF?'))

    print("\nLegenda ocen:")
    print("  A — już zoptymalizowany, NIE kompresuj (ryzyko pogorszenia jakości)")
    print("  B — blisko optimum, kompresja da niewiele")
    print("  C — umiarkowany potencjał, warto rozważyć")
    print("  D — duży potencjał, warto skompresować")
    print("  F — bardzo duży potencjał, wyraźnie warto")
    print()


# ---------------------------------------------------------------------------
# Kompresja
# ---------------------------------------------------------------------------

def compress_one(a, output_base, search_root, encoder, crf, preset, dry_run):
    orig_size = a.size
    rel = os.path.relpath(a.path, search_root)
    output_path = os.path.join(output_base, rel)
    os.makedirs(os.path.dirname(output_path) or output_base, exist_ok=True)

    if os.path.exists(output_path):
        print(f"   ⏭  Pomijam (już istnieje): {os.path.basename(output_path)}")
        return None, None

    if dry_run:
        print(f"   [DRY-RUN] {format_size(orig_size)} → ~{format_size(a.predicted_size)}  "
              f"(ocena {a.grade})")
        return orig_size, a.predicted_size

    # Wybór enkodera
    if encoder == 'videotoolbox':
        v_enc = 'hevc_videotoolbox'
        v_args = ['-q:v', '60', '-tag:v', 'hvc1', '-allow_sw', '0']
        enc_label = 'hw hevc (VideoToolbox)'
    elif encoder == 'libx265':
        v_enc = 'libx265'
        v_args = ['-crf', str(crf), '-preset', preset, '-tag:v', 'hvc1']
        enc_label = f'sw libx265 CRF {crf}'
    elif encoder == 'libx264':
        v_enc = 'libx264'
        v_args = ['-crf', str(crf), '-preset', preset,
                  '-profile:v', 'high', '-level', '4.1']
        enc_label = f'sw libx264 CRF {crf}'
    else:
        raise ValueError(encoder)

    cmd = [
        'ffmpeg', '-y', '-i', a.path,
        '-map_metadata', '0',
        '-map_chapters', '0',
        '-map', '0:v:0',
    ]
    if a.has_audio:
        cmd += ['-map', '0:a:0']

    cmd += ['-c:v', v_enc, *v_args, '-pix_fmt', 'yuv420p']

    if a.has_audio:
        cmd += ['-c:a', 'aac', '-b:a', '160k', '-ac', '2']
    else:
        cmd += ['-an']

    cmd += ['-movflags', '+faststart', output_path]

    print(f"   ⏳ {enc_label} ...")
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        print(f"   ✗ {e}")
        return None, None

    elapsed = time.time() - t0

    if r.returncode != 0:
        tail = '\n'.join(r.stderr.strip().split('\n')[-4:])
        print(f"   ✗ ffmpeg exit {r.returncode}\n   {tail}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return None, None

    new_size = os.path.getsize(output_path)
    if new_size < 1024:
        print("   ✗ wynik zbyt mały, kasuję")
        os.remove(output_path)
        return None, None

    preserve_timestamps(a.path, output_path)
    pct = new_size / orig_size * 100
    print(f"   ✅ {format_size(orig_size)} → {format_size(new_size)} "
          f"({pct:.0f}%) w {elapsed:.1f}s")
    return orig_size, new_size


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def find_videos(search_path, output_dir):
    abs_out = os.path.abspath(output_dir)
    found = []
    for root, dirs, files in os.walk(search_path):
        dirs[:] = [d for d in dirs
                   if not d.startswith('.')
                   and d not in ('__pycache__', 'node_modules')
                   and os.path.abspath(os.path.join(root, d)) != abs_out]
        for f in files:
            if os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS:
                found.append(os.path.join(root, f))
    return found


def main():
    p = argparse.ArgumentParser(
        description='Smart Media Compressor — analizuje, rekomenduje, kompresuje.'
    )
    p.add_argument('--path', required=True, help='Katalog do przeszukania.')
    p.add_argument('--output', default=DEFAULT_OUTPUT_DIR,
                   help=f'Katalog wynikowy (domyślnie: {DEFAULT_OUTPUT_DIR}/).')
    p.add_argument('--apply', action='store_true',
                   help='Wykonaj kompresję plików z rekomendacją (C/D/F).')
    p.add_argument('--force', action='store_true',
                   help='Kompresuj także pliki A/B (nadpisuje logikę rekomendacji).')
    p.add_argument('--encoder', choices=['videotoolbox', 'libx265', 'libx264'],
                   default='videotoolbox',
                   help='Enkoder: videotoolbox (cicho/szybko), '
                        'libx265 (lepsza kompresja), libx264 (kompatybilność).')
    p.add_argument('--crf', type=int, default=24,
                   help='CRF dla libx265/libx264 (niżej = lepiej). Domyślnie 24.')
    p.add_argument('--preset', default='medium',
                   help='Preset ffmpeg dla libx265/libx264.')
    p.add_argument('--min-size-mb', type=float, default=10.0,
                   help='Pomijaj pliki < X MB (domyślnie 10).')
    p.add_argument('--min-duration', type=float, default=5.0,
                   help='Pomijaj klipy < X sekund (domyślnie 5).')

    args = p.parse_args()

    if not os.path.isdir(args.path):
        print(f"❌ Katalog nie istnieje: {args.path}")
        sys.exit(1)
    if not check_tools():
        sys.exit(1)

    output_base = os.path.abspath(args.output)

    print("=" * 110)
    print("🧠 SMART MEDIA COMPRESSOR")
    print("=" * 110)
    print(f"Ścieżka:      {os.path.abspath(args.path)}")
    print(f"Wynik:        {output_base}")
    print(f"Enkoder:      {args.encoder}  (CRF {args.crf}, preset {args.preset})")
    print(f"Tryb:         {'KOMPRESJA' if args.apply else 'RAPORT (bez kompresji)'}")
    print(f"Filtr:        ≥ {args.min_size_mb} MB i ≥ {args.min_duration}s")
    print("=" * 110)

    print("\n🔍 Skanuję pliki...")
    videos = find_videos(args.path, output_base)
    print(f"   Znaleziono {len(videos)} plików wideo.")

    print("\n🧠 Analizuję...")
    analyses = []
    for i, v in enumerate(videos, 1):
        try:
            if os.path.getsize(v) < args.min_size_mb * 1024 * 1024:
                continue
            a = analyze_video(v)
            if a and a.duration >= args.min_duration:
                analyses.append(a)
        except Exception as e:
            print(f"   ⚠ {os.path.basename(v)}: {e}")
        if i % 25 == 0:
            print(f"   ... {i}/{len(videos)}")

    if not analyses:
        print("\nBrak plików spełniających kryteria.")
        return

    print_report(analyses)

    if not args.apply:
        print("ℹ  To był tylko raport. Aby skompresować pliki C/D/F, dodaj --apply.")
        return

    # Wybór plików do kompresji
    if args.force:
        to_compress = [a for a in analyses if a.grade != '?']
    else:
        to_compress = [a for a in analyses if a.grade in ('C', 'D', 'F')]

    if not to_compress:
        print("✅ Nie ma plików wartych kompresji (wszystkie A/B).")
        print("   Użyj --force aby skompresować mimo to.")
        return

    total_in = sum(a.size for a in to_compress)
    total_pred = sum(a.predicted_size for a in to_compress)
    print(f"\n🎬 Do kompresji: {len(to_compress)} plików "
          f"({format_size(total_in)} → ~{format_size(total_pred)})")
    print(f"   Enkoder: {args.encoder}")

    ok = 0
    fail = 0
    real_in = 0
    real_out = 0
    t0 = time.time()

    for i, a in enumerate(to_compress, 1):
        name = os.path.basename(a.path)
        print(f"\n[{i}/{len(to_compress)}] {name}  (ocena {a.grade})")
        o, n = compress_one(a, output_base, args.path,
                            args.encoder, args.crf, args.preset,
                            dry_run=False)
        if o is not None:
            ok += 1
            real_in += o
            real_out += n
        else:
            fail += 1

    elapsed = time.time() - t0

    print("\n" + "=" * 110)
    print("📊 WYNIK KOŃCOWY")
    print("=" * 110)
    print(f"OK:                {ok} / {len(to_compress)}")
    print(f"Błędy:             {fail}")
    if real_in > 0:
        saved = real_in - real_out
        print(f"Przed:             {format_size(real_in)}")
        print(f"Po:                {format_size(real_out)}")
        print(f"Zaoszczędzono:     {format_size(saved)} ({saved / real_in * 100:.1f}%)")
    print(f"Czas:              {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"Wynik w:           {output_base}")
    print("=" * 110)


if __name__ == '__main__':
    main()