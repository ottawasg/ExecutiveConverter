"""
Release script — jalankan ini tiap mau release versi baru.

Usage:
    python release.py 1.2.0 "Fix bug X, tambah fitur Y"
"""
import sys
import json
import subprocess
from pathlib import Path

DISCORD_WEBHOOK = "https://discordapp.com/api/webhooks/1505943503962771561/n0cuh3s9MCvQY_vBrUxkv04vw_d1mC-G5rL9-8Se2H09K8kXN9WW4SPPMD41UBlvfbeq"
GITHUB_USER     = ""   # diisi otomatis dari gh auth status
GITHUB_REPO     = "ExecutiveConverter"
EXE_PATH        = Path("dist/ExecutiveConverter.exe")
VERSION_FILE    = Path("version.json")


def run(cmd, **kw):
    print(f"  > {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)
    if r.stdout.strip():
        print("   ", r.stdout.strip())
    if r.returncode != 0 and r.stderr.strip():
        print("   ERR:", r.stderr.strip())
    return r


def get_github_user():
    r = subprocess.run("gh api user --jq .login", shell=True, capture_output=True, text=True)
    return r.stdout.strip()


def build_exe():
    print("\n[1/5] Building exe...")
    r = run("python -m PyInstaller ExecutiveConverter.spec --clean")
    if r.returncode != 0:
        print("Build failed!"); sys.exit(1)
    print("  Build OK")


def notify_discord(version, changelog, download_url):
    import urllib.request, urllib.parse
    print("\n[5/5] Sending Discord notification...")
    payload = {
        "embeds": [{
            "title": f"🚀 Executive Converter v{version}",
            "description": f"**Changelog:**\n{changelog}",
            "color": 0x2f81f7,
            "fields": [
                {"name": "Download", "value": f"[ExecutiveConverter.exe]({download_url})", "inline": False},
            ],
            "footer": {"text": "Executive Converter Auto-Release"}
        }]
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        DISCORD_WEBHOOK,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        print("  Discord notified ✓")
    except Exception as e:
        print(f"  Discord failed: {e}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python release.py <version> \"<changelog>\"")
        print("Example: python release.py 1.2.0 \"Fix download bug, improve UI\"")
        sys.exit(1)

    version   = sys.argv[1].lstrip("v")
    changelog = sys.argv[2]
    tag       = f"v{version}"

    if not EXE_PATH.exists():
        print(f"EXE not found at {EXE_PATH}, building first...")

    # 1. Build
    build_exe()

    # 2. Update version.json
    print("\n[2/5] Updating version.json...")
    VERSION_FILE.write_text(json.dumps({"version": version, "changelog": changelog}, indent=2))
    print(f"  version → {version}")

    # 3. Git commit + tag
    print("\n[3/5] Git commit & tag...")
    run("git add version.json")
    run(f'git commit -m "release: v{version}"')
    run(f"git tag {tag}")
    run("git push origin main --tags")

    # 4. GitHub release + upload exe
    print("\n[4/5] Creating GitHub release...")
    gh_user = get_github_user()
    r = run(
        f'gh release create {tag} "{EXE_PATH}" '
        f'--title "Executive Converter {tag}" '
        f'--notes "{changelog}" '
        f'--repo {gh_user}/{GITHUB_REPO}'
    )
    if r.returncode != 0:
        print("GitHub release failed!"); sys.exit(1)

    download_url = f"https://github.com/{gh_user}/{GITHUB_REPO}/releases/download/{tag}/ExecutiveConverter.exe"

    # 5. Discord webhook
    notify_discord(version, changelog, download_url)

    print(f"\n✓ Release {tag} complete!")
    print(f"  Download: {download_url}")


if __name__ == "__main__":
    main()
