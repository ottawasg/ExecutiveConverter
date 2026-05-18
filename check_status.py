import json
import requests
from pathlib import Path
from cfg import ROBLOX_API_KEY, UPLOAD_JSON

STATUS_ICONS = {
    "MODERATION_STATE_APPROVED": "✅",
    "MODERATION_STATE_REVIEWING": "⏳",
    "MODERATION_STATE_REJECTED": "❌",
    "Approved": "✅",
    "Reviewing": "⏳",
    "Rejected": "❌",
}


def check_asset(asset_id):
    url = f"https://apis.roblox.com/assets/v1/assets/{asset_id}"
    resp = requests.get(url, headers={"x-api-key": ROBLOX_API_KEY})

    if resp.status_code == 200:
        data = resp.json()
        moderation = data.get("moderationResult", {})
        state = moderation.get("moderationState", "Unknown")
        return state
    else:
        return f"ERROR ({resp.status_code})"


def main():
    path = Path(UPLOAD_JSON)
    if not path.exists():
        print(f"File {UPLOAD_JSON} tidak ditemukan!")
        return

    with open(path) as f:
        assets = json.load(f)

    print("=" * 60)
    print("Roblox Audio Asset Status Checker")
    print("=" * 60)
    print(f"Total assets: {len(assets)}\n")

    approved = 0
    reviewing = 0
    rejected = 0
    errors = 0

    for i, entry in enumerate(assets, 1):
        title = entry.get("title", "?")
        sound_id = entry.get("soundId", "")
        asset_id = sound_id.replace("rbxassetid://", "")

        if not asset_id:
            print(f"  [{i}] {title} - ⚠ Tidak ada asset ID")
            errors += 1
            continue

        state = check_asset(asset_id)
        icon = STATUS_ICONS.get(state, "❓")

        print(f"  [{i:2d}] {icon} {title:<35s}  {state}")

        if "APPROVED" in state.upper() or state == "Approved":
            approved += 1
        elif "REVIEWING" in state.upper() or state == "Reviewing":
            reviewing += 1
        elif "REJECTED" in state.upper() or state == "Rejected":
            rejected += 1
        else:
            errors += 1

    print()
    print("=" * 60)
    print(f"✅ Approved (siap pakai): {approved}")
    print(f"⏳ Reviewing (masih proses): {reviewing}")
    print(f"❌ Rejected (ditolak): {rejected}")
    if errors:
        print(f"❓ Error/Unknown: {errors}")
    print("=" * 60)


if __name__ == "__main__":
    main()
