"""Checks every package in packages/, packs it, and writes dist/ for the "packages" release:
one <id>-<version>.cdwidget per package and index.txt (id, sha256, download url per line).

Run on Windows with widget-dev on PATH (cargo install --git https://github.com/rom5n/widgine widgine).
"""
import hashlib, pathlib, struct, subprocess, sys, tomllib

REPO = "rom5n/calmdesk-widgets"
URL = f"https://github.com/{REPO}/releases/download/packages/"
root = pathlib.Path(__file__).resolve().parent.parent
dist = root / "dist"
dist.mkdir(exist_ok=True)
errors, lines = [], []


def icon_error(pkg, icon):
    if not icon:
        return "no icon: add icon = \"assets/icon.svg\" (or a PNG) to widget.toml"
    f = pkg / icon
    if not f.is_file():
        return f"icon {icon} not found"
    if f.suffix.lower() == ".svg":
        return None
    data = f.read_bytes()[:24]
    if f.suffix.lower() != ".png" or data[:8] != b"\x89PNG\r\n\x1a\n":
        return "the icon must be an SVG or a PNG"
    w, h = struct.unpack(">II", data[16:24])
    if w != h or w < 64:
        return f"the PNG icon is {w}x{h}: it must be square and at least 64x64"
    return None


for pkg in sorted(p for p in (root / "packages").iterdir() if p.is_dir()):
    name = pkg.name
    try:
        manifest = tomllib.loads((pkg / "widget.toml").read_text(encoding="utf-8"))
    except Exception as e:
        errors.append(f"{name}: widget.toml: {e}")
        continue
    pid, version = manifest.get("id", ""), manifest.get("version", "")
    problems = []
    if pid != name:
        problems.append(f"the folder must be named after the id ({pid})")
    if pid.startswith("dev.widget-engine.") or pid.startswith("dev.widgine."):
        problems.append("ids starting with dev.widget-engine. or dev.widgine. are reserved")
    if not version:
        problems.append("no version")
    if not manifest.get("author"):
        problems.append("no author")
    if e := icon_error(pkg, manifest.get("icon")):
        problems.append(e)
    check = subprocess.run(["widget-dev", "--check", str(pkg)], capture_output=True, text=True)
    if check.returncode:
        problems.append((check.stderr or check.stdout).strip())
    if problems:
        errors.extend(f"{name}: {p}" for p in problems)
        continue
    file = dist / f"{pid}-{version}.cdwidget"
    subprocess.run(["widget-dev", "pack", str(pkg), str(file)], check=True, capture_output=True)
    sha = hashlib.sha256(file.read_bytes()).hexdigest()
    lines.append(f"{pid}\t{sha}\t{URL}{file.name}\n")

if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)
(dist / "index.txt").write_text("".join(lines), encoding="utf-8", newline="\n")
print(f"{len(lines)} packages")
