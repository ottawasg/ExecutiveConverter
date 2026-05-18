"""
Release script — jalankan ini tiap mau release versi baru.

Usage:
    python release.py 1.2.0 "Fix bug X, tambah fitur Y"
"""
import sys
import os
import json
import subprocess
from pathlib import Path

# ── Load .env ────────────────────────────────────────────────────
_env = Path(".env")
if _env.exists():
    for _line in _env.read_text().splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
GITHUB_REPO     = "ExecutiveConverter"
EXE_PATH        = Path("dist/ExecutiveConverter.exe")
VERSION_FILE    = Path("version.json")

# Tambahkan gh CLI ke PATH (Windows)
_gh_path = r"C:\Program Files\GitHub CLI"
if _gh_path not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _gh_path + ";" + os.environ.get("PATH", "")


def run(cmd, fatal=False):
    print(f"  > {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.stdout.strip():
        print("   ", r.stdout.strip())
    if r.returncode != 0 and r.stderr.strip():
        print("   ERR:", r.stderr.strip())
    if fatal and r.returncode != 0:
        sys.exit(1)
    return r


def get_github_user():
    r = subprocess.run("gh api user --jq .login", shell=True, capture_output=True, text=True)
    return r.stdout.strip()


def build_exe():
    print("\n[1/5] Building exe...")
    run("python -m PyInstaller ExecutiveConverter.spec --clean", fatal=True)
    print("  Build OK")

    # Sync supporting files ke dist
    dst = Path("dist")
    for f in ["config.json", "upload.json", "urls_youtube.txt", "urls_soundcloud.txt",
              "logo.png", "logo.ico", "version.json"]:
        if Path(f).exists():
            import shutil
            shutil.copy2(f, dst / f)
    for d in ["downloads", "uploaded"]:
        (dst / d).mkdir(exist_ok=True)


def notify_discord(version, changelog, download_url):
    import urllib.request
    if not DISCORD_WEBHOOK:
        print("  No DISCORD_WEBHOOK in .env, skip.")
        return
    print("\n[5/5] Sending Discord notification...")
    payload = {
        "embeds": [{
            "title": f"\U0001f680 Executive Converter v{version}",
            "description": f"**Changelog:**\n{changelog}",
            "color": 0x2f81f7,
            "fields": [
                {"name": "\U0001f4e5 Download",
                 "value": f"[ExecutiveConverter.exe]({download_url})", "inline": False},
            ],
            "footer": {"text": "Executive Converter Auto-Release"}
        }]
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        DISCORD_WEBHOOK, data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        print("  Discord notified ✓")
    except Exception as e:
        print(f"  Discord failed: {e}")


def main():
    if len(sys.argv) < 3:
        print('Usage: python release.py <version> "changelog"')
        print('Example: python release.py 1.2.0 "Fix download bug"')
        sys.exit(1)

    version   = sys.argv[1].lstrip("v")
    changelog = sys.argv[2]
    tag       = f"v{version}"

    # 1. Build + sync dist
    build_exe()

    # 2. Update version.json
    print("\n[2/5] Updating version.json...")
    VERSION_FILE.write_text(json.dumps({"version": version, "changelog": changelog}, indent=2))
    print(f"  version → {version}")

    # 3. Git commit + tag + push
    print("\n[3/5] Git commit & push...")
    run("git add version.json")
    run(f'git commit -m "release: v{version}"')
    run(f"git tag {tag}")
    # support both master and main
    branch = subprocess.run("git rev-parse --abbrev-ref HEAD",
                            shell=True, capture_output=True, text=True).stdout.strip()
    run(f"git push origin {branch} --tags", fatal=True)

    # 4. GitHub release + upload exe
    print("\n[4/5] Creating GitHub release...")
    gh_user = get_github_user()
    if not gh_user:
        print("  ERR: gh not logged in. Run: gh auth login"); sys.exit(1)

    r = run(
        f'gh release create {tag} "{EXE_PATH}" '
        f'--title "Executive Converter {tag}" '
        f'--notes "{changelog}" '
        f'--repo {gh_user}/{GITHUB_REPO}'
    )
    if r.returncode != 0:
        print("GitHub release failed!"); sys.exit(1)

    download_url = (f"https://github.com/{gh_user}/{GITHUB_REPO}"
                    f"/releases/download/{tag}/ExecutiveConverter.exe")

    # 5. Discord
    notify_discord(version, changelog, download_url)

    print(f"\n✓ Release {tag} complete!")
    print(f"  {download_url}")


if __name__ == "__main__":
    main()
