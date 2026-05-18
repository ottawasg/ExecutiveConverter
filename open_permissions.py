import json
import webbrowser
import time
from pathlib import Path
from cfg import UPLOAD_JSON


def main():
    path = Path(UPLOAD_JSON)
    if not path.exists():
        print(f"File {UPLOAD_JSON} tidak ditemukan!")
        return

    with open(path) as f:
        assets = json.load(f)

    if not assets:
        print("Tidak ada asset di upload.json!")
        return

    print("=" * 60)
    print("Buka halaman Permissions untuk semua asset")
    print("=" * 60)
    print(f"Total: {len(assets)} asset\n")

    for i, entry in enumerate(assets, 1):
        title = entry.get("title", "?")
        sound_id = entry.get("soundId", "")
        asset_id = sound_id.replace("rbxassetid://", "")

        if not asset_id:
            print(f"  [{i}] {title} - Tidak ada asset ID, skip")
            continue

        url = f"https://create.roblox.com/dashboard/creations/store/{asset_id}/configure"
        print(f"  [{i}] {title} -> {asset_id}")
        webbrowser.open(url)
        time.sleep(1)

    print(f"\n{len(assets)} tab dibuka di browser.")
    print("Di setiap halaman: Permissions -> Collaborators -> Add collaborators -> cari futurewayys -> Done")


if __name__ == "__main__":
    main()
