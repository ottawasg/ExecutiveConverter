import json
import re
import time
import requests
from pathlib import Path
from cfg import ROBLOX_API_KEY, ROBLOX_USER_ID, DOWNLOADS_FOLDER, UPLOAD_JSON

ROBLOX_API_URL = "https://apis.roblox.com/assets/v1/assets"

KNOWN_ARTISTS = {
    "psy", "rombongan bodonk koplo", "siti badriah", "tuty wibowo",
}


def extract_song_title(filename):
    name = filename

    # Ekstrak "Part X" dari nama file sebelum diproses
    part_match = re.search(r'\bPart\s+(\d+)\b', name, re.IGNORECASE)
    part_suffix = f" Part {part_match.group(1)}" if part_match else ""

    # Remove fullwidth and regular quotes
    name = name.replace('\uff02', '').replace('"', '').replace('\u201c', '').replace('\u201d', '')

    # Remove everything after ｜
    name = re.split(r'[｜|]', name)[0]

    # Remove parenthetical blocks
    name = re.sub(r'\([^)]*\)', '', name)

    # Remove "Part X" dari processing (akan ditambahkan kembali di akhir)
    name = re.sub(r'\bPart\s+\d+\b', '', name, flags=re.IGNORECASE)

    # Remove version/noise markers
    noise = [
        r'Korean\s*(Ver\.?|Version|Style\s+Cover)',
        r'Korea\s+Version',
        r'Versi\s+(Jepang|Korea|koplo)',
        r'Thailand\s+HD',
        r'M[⧸/]V',
        r'\bLirik\b',
        r'\bFull\s+Song\b',
        r'\bMix\s+.*',
        r'\bcover\s+by\s+.*',
        r'\bfeat\.?\s+.*',
        r'Koplo\s+Version',
        r'Official\s+Music\s+Video',
        r'\bVisualizer\b',
        r'\bLYRICS\b',
        r'Final\s+Version',
        r'Male\s+Full\s+Cover',
        r'Viral\s+TikTok',
    ]
    for p in noise:
        name = re.sub(p, '', name, flags=re.IGNORECASE)

    # Split by " - " or " – "
    parts = re.split(r'\s+[-–]\s+', name)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) >= 2:
        first = parts[0]
        # Check if first part looks like an artist name
        first_lower = first.lower().strip()
        is_artist = (
            first_lower in KNOWN_ARTISTS
            or (',' in first and '&' in first)
        )
        if is_artist:
            title = parts[1]
        else:
            title = first
    elif parts:
        title = parts[0]
    else:
        title = filename

    # Final cleanup
    title = re.sub(r'\s+', ' ', title).strip()
    title = title.strip('-– .')

    # Tambahkan kembali Part suffix
    title = title + part_suffix
    return title


def load_uploaded():
    path = Path(UPLOAD_JSON)
    if path.exists():
        with open(path) as f:
            data = json.load(f)
        return {entry.get("_filename", entry["title"]): entry for entry in data}
    return {}


def save_uploaded(uploaded_dict):
    with open(UPLOAD_JSON, "w") as f:
        json.dump(list(uploaded_dict.values()), f, indent=2, ensure_ascii=False)


def poll_operation(operation_path):
    """Return (asset_id, error_msg) tuple."""
    if not operation_path:
        return None, "no operation path"

    url = f"https://apis.roblox.com/assets/v1/{operation_path}"
    headers = {"x-api-key": ROBLOX_API_KEY}

    for attempt in range(30):
        time.sleep(3)
        resp = requests.get(url, headers=headers)
        print(f"  [POLL #{attempt+1}] Status: {resp.status_code} | Body: {resp.text[:300]}")
        if resp.status_code == 200:
            data = resp.json()
            if data.get("done"):
                # Cek error dulu
                error = data.get("error")
                if error:
                    err_msg = error.get("message", "Unknown error")
                    print(f"  [POLL] Done tapi ERROR: {err_msg}")
                    return None, err_msg

                response = data.get("response", {})
                asset_id = response.get("assetId")
                if not asset_id:
                    asset_id = response.get("asset_id") or response.get("id")
                if not asset_id and "assetId" in str(data):
                    import re
                    match = re.search(r'"assetId"\s*:\s*"?(\d+)"?', str(data))
                    if match:
                        asset_id = match.group(1)
                print(f"  [POLL] Done! asset_id = {asset_id}")
                return asset_id, None
        elif resp.status_code != 200:
            print(f"  [POLL] Error response, stopping poll")
            return None, f"poll error ({resp.status_code})"
    print(f"  [POLL] Timeout setelah 30 attempts")
    return None, "poll timeout"


def check_asset_status(asset_id):
    """Check moderation status: approved / reviewing / rejected."""
    url = f"https://apis.roblox.com/assets/v1/assets/{asset_id}"
    resp = requests.get(url, headers={"x-api-key": ROBLOX_API_KEY})

    if resp.status_code == 200:
        data = resp.json()
        state = data.get("moderationResult", {}).get("moderationState", "Unknown")
        return state
    return f"ERROR ({resp.status_code})"


def upload_to_roblox(filepath):
    """Upload file, return (asset_id, status) or (None, error_msg)."""
    display_name = extract_song_title(filepath.stem)[:50]
    file_size = filepath.stat().st_size

    request_body = json.dumps({
        "assetType": "Audio",
        "displayName": display_name,
        "description": "",
        "creationContext": {
            "creator": {
                "userId": ROBLOX_USER_ID
            }
        }
    })

    print(f"  [DEBUG] Display name: {display_name}")
    print(f"  [DEBUG] File size: {file_size / 1024:.1f} KB")
    print(f"  [DEBUG] Sending POST to {ROBLOX_API_URL}...")

    start_time = time.time()
    try:
        with open(filepath, "rb") as f:
            resp = requests.post(
                ROBLOX_API_URL,
                headers={"x-api-key": ROBLOX_API_KEY},
                files={
                    "request": (None, request_body, "application/json"),
                    "fileContent": (filepath.name, f, "audio/ogg"),
                },
                timeout=60,
            )
        elapsed = time.time() - start_time
        print(f"  [DEBUG] Response: {resp.status_code} ({elapsed:.1f}s)")
        print(f"  [DEBUG] Response body: {resp.text[:500]}")
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"  [DEBUG] TIMEOUT setelah {elapsed:.1f}s")
        return None, "timeout"
    except requests.exceptions.ConnectionError as e:
        print(f"  [DEBUG] CONNECTION ERROR: {e}")
        return None, "connection_error"

    if resp.status_code != 200:
        error = resp.text[:300]
        print(f"  ✗ Upload gagal ({resp.status_code}): {error}")
        return None, error

    data = resp.json()
    operation_path = data.get("path", "")
    print(f"  [DEBUG] Operation path: {operation_path}")
    asset_id, poll_error = poll_operation(operation_path)

    if poll_error:
        print(f"  ✗ Roblox rejected: {poll_error}")
        return None, poll_error

    if not asset_id:
        print(f"  [DEBUG] Poll selesai tapi tidak dapat asset_id")
        return None, "no_asset_id"

    # Check moderation status
    print(f"  ✓ Uploaded! Asset ID: {asset_id}")
    print(f"  Checking status...", end=" ")
    time.sleep(2)
    status = check_asset_status(asset_id)

    if "APPROVED" in status.upper() or status == "Approved":
        print(f"✅ Approved - siap pakai!")
        return str(asset_id), "approved"
    elif "REVIEWING" in status.upper() or status == "Reviewing":
        print(f"✅ Approved - siap pakai!")
        return str(asset_id), "reviewing"
    elif "REJECTED" in status.upper() or status == "Rejected":
        print(f"❌ Rejected - ditolak moderasi!")
        return str(asset_id), "rejected"
    else:
        print(f"❓ {status}")
        return str(asset_id), status


def main():
    folder = Path(DOWNLOADS_FOLDER)
    audio_files = sorted(folder.glob("*.ogg"))

    print("=" * 50)
    print("Roblox Audio Uploader → upload.json")
    print("=" * 50)
    print(f"Folder: {folder.resolve()}")
    print(f"Total OGG: {len(audio_files)}")

    if not audio_files:
        print("Tidak ada file OGG di folder!")
        return

    # Preview title extraction
    print(f"\nPreview judul yang akan dipakai:")
    for af in audio_files:
        clean = extract_song_title(af.stem)
        print(f"  {af.stem[:50]}...  →  {clean}")
    print()

    # Load yang sudah pernah upload
    uploaded = load_uploaded()
    if uploaded:
        print(f"Sudah terupload sebelumnya: {len(uploaded)}")

    # Filter yang belum diupload
    to_upload = [f for f in audio_files if f.stem not in uploaded]
    print(f"Akan diupload: {len(to_upload)}\n")

    if not to_upload:
        print("Semua file sudah terupload!")
        return

    input("Tekan Enter untuk mulai upload (Ctrl+C untuk batal)...\n")

    success = 0
    failed = 0
    stopped = False

    for i, af in enumerate(to_upload, 1):
        size_mb = af.stat().st_size / (1024 * 1024)
        clean_title = extract_song_title(af.stem)
        print(f"[{i}/{len(to_upload)}] {clean_title} ({size_mb:.1f} MB)")

        asset_id, status = upload_to_roblox(af)

        # Retry sekali kalau gagal (fix upload pertama sering gagal)
        if not asset_id and status not in ("no_asset_id",):
            print(f"  ↻ Retry sekali lagi...")
            time.sleep(3)
            asset_id, status = upload_to_roblox(af)

        if asset_id:
            uploaded[af.stem] = {
                "_filename": af.stem,
                "playlistId": "6989936f04a6c8e0cdc770de",
                "title": clean_title,
                "soundId": f"rbxassetid://{asset_id}",
                "genre": "koplo",
                "playbackSpeed": 0.45,
                "thumbnail": "",
                "duration": 0,
            }
            save_uploaded(uploaded)
            success += 1

            # Pindahkan ke folder uploaded
            uploaded_folder = Path(DOWNLOADS_FOLDER) / ".." / "uploaded"
            uploaded_folder.mkdir(exist_ok=True)
            dest = uploaded_folder / af.name
            af.rename(dest)
            print(f"  📁 Dipindahkan ke uploaded/")

            if status == "rejected":
                print(f"\n  ⛔ STOP - \"{clean_title}\" ditolak moderasi.")
                print(f"  Upload dihentikan. Jalankan ulang untuk lanjut dari sini.")
                stopped = True
                break
        else:
            if status == "no_asset_id":
                # Upload terkirim tapi belum dapat ID, lanjut aja
                print(f"  ⚠ Lanjut ke file berikutnya...")
                failed += 1
            elif "moderated" in (status or "").lower():
                print(f"\n  ⛔ STOP - Akun kena moderasi. Upload dihentikan.")
                failed += 1
                stopped = True
                break
            else:
                print(f"\n  ⛔ STOP - Upload gagal. Cek error di atas.")
                failed += 1
                stopped = True
                break

        print()

    print()
    print("=" * 50)
    if stopped:
        print(f"Upload dihentikan!")
    else:
        print(f"Selesai!")
    print(f"Berhasil: {success} | Gagal: {failed} | Sisa: {len(to_upload) - i}")
    print(f"Total di upload.json: {len(uploaded)}")
    print("=" * 50)


if __name__ == "__main__":
    main()
