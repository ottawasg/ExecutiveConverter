import yt_dlp
import subprocess
from pathlib import Path
from cfg import SPEED, AMPLIFY_DB, DOWNLOADS_FOLDER

URL_FILES = {
    "1": ("YouTube", "urls_youtube.txt"),
    "2": ("SoundCloud", "urls_soundcloud.txt"),
}


def load_urls(filepath):
    path = Path(filepath)
    if not path.exists():
        print(f"File {filepath} tidak ditemukan!")
        return []
    with open(path) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


MAX_DURATION = 360  # 3 menit dalam detik (Roblox limit ~7 menit, tapi speed 2.3x bikin durasi decoded jadi ~2.3x lebih panjang)


def get_duration(filepath):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(filepath),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        return float(result.stdout.strip())
    return 0


def split_audio(filepath, max_seconds=MAX_DURATION):
    duration = get_duration(filepath)
    if duration <= max_seconds:
        return [filepath]

    num_parts = int(duration // max_seconds) + (1 if duration % max_seconds > 0 else 0)
    stem = filepath.stem
    parts = []

    print(f"  ✂ Durasi {duration:.0f}s (>{max_seconds}s), dipotong jadi {num_parts} part...")

    for p in range(num_parts):
        start = p * max_seconds
        part_path = filepath.parent / f"{stem} Part {p + 1}.ogg"
        cmd = [
            "ffmpeg", "-y", "-i", str(filepath),
            "-ss", str(start), "-t", str(max_seconds),
            "-c:a", "libopus", "-b:a", "192k",
            str(part_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            part_dur = get_duration(part_path)
            print(f"    Part {p + 1}: {part_dur:.0f}s")
            parts.append(part_path)
        else:
            print(f"    ✗ Part {p + 1} gagal")

    if parts:
        filepath.unlink()

    return parts


def convert_speed_amplify(filepath, speed, amplify_db):
    ogg_path = filepath.with_suffix(".ogg")
    new_rate = int(44100 * speed)
    audio_filter = f"asetrate={new_rate},aresample=44100,volume={amplify_db}dB"

    cmd = [
        "ffmpeg", "-y", "-i", str(filepath),
        "-filter:a", audio_filter,
        "-c:a", "libopus", "-b:a", "192k",
        str(ogg_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        # Hapus file MP3 asli
        if filepath != ogg_path:
            filepath.unlink(missing_ok=True)
        dur = get_duration(ogg_path)
        print(f"  ✓ Converted → OGG (speed {speed}x, amplify {amplify_db}dB) - {dur:.0f}s")

        # Split jika lebih dari 7 menit
        split_audio(ogg_path)
        return True
    else:
        print(f"  ✗ Convert gagal: {result.stderr.splitlines()[-1] if result.stderr else 'unknown error'}")
        ogg_path.unlink(missing_ok=True)
        return False


def download_and_convert(url, output_folder=DOWNLOADS_FOLDER):
    Path(output_folder).mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "outtmpl": f"{output_folder}/%(title)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Downloading: {url}")
            info = ydl.extract_info(url, download=True)

        # Ambil filepath final setelah post-processing
        mp3_path = None
        if info.get("requested_downloads"):
            mp3_path = Path(info["requested_downloads"][0]["filepath"])
        else:
            mp3_path = Path(ydl.prepare_filename(info)).with_suffix(".mp3")

        if not mp3_path or not mp3_path.exists():
            print(f"  ✗ File tidak ditemukan: {mp3_path}")
            return False

        return convert_speed_amplify(mp3_path, SPEED, AMPLIFY_DB)

    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        return False


def menu_download():
    print("=" * 50)
    print("Download & Bypass → OGG")
    print(f"Speed: {SPEED}x | Amplify: {AMPLIFY_DB}dB")
    print("=" * 50)
    print("\nPilih source:")
    for key, (name, filename) in URL_FILES.items():
        urls = load_urls(filename)
        print(f"  [{key}] {name} ({len(urls)} link) - {filename}")
    print()

    choice = input("Pilih (1/2): ").strip()
    if choice not in URL_FILES:
        print("Pilihan tidak valid!")
        return

    source_name, url_file = URL_FILES[choice]
    urls = load_urls(url_file)

    if not urls:
        print(f"Tidak ada URL di {url_file}!")
        return

    print(f"\n{source_name} → {len(urls)} link\n")

    success = 0
    failed = 0

    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}]")
        if download_and_convert(url):
            success += 1
        else:
            failed += 1
        print()

    print("=" * 50)
    print(f"Selesai! Berhasil: {success} | Gagal: {failed}")
    print("=" * 50)


def menu_upload():
    from upload import main as upload_main
    upload_main()


def menu_check_status():
    from check_status import main as check_main
    check_main()


def main():
    print()
    print("=" * 50)
    print("  Roblox Audio Tool")
    print("=" * 50)
    print()
    print("  [1] Download & Bypass")
    print("  [2] Upload ke Roblox")
    print("  [3] Check Status")
    print()

    choice = input("Pilih menu (1/2/3): ").strip()
    print()

    if choice == "1":
        menu_download()
    elif choice == "2":
        menu_upload()
    elif choice == "3":
        menu_check_status()
    else:
        print("Pilihan tidak valid!")


if __name__ == "__main__":
    main()
