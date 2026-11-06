"""Checks every package in packages/, packs it, and writes dist/ for the "packages" release:
one <id>-<version>.cdwidget per package and index.txt: a "#" comment line, then one line per
package with tab-separated id, sha256, download url, version, author, category, name and
downloads. Calmdesk lists packages from it and downloads one only when its tile is shown.

With GH_TOKEN set (CI on main), downloads are the release's asset download counts summed per
id, and authors/<author>.md lists each author's packages and totals. featured.txt is checked
and copied to dist/ as well.

Run on Windows with widget-dev on PATH (cargo install --git https://github.com/rom5n/widgine widgine).
"""
import datetime, hashlib, os, pathlib, re, struct, subprocess, sys, tomllib

REPO = "rom5n/calmdesk-widgets"
URL = f"https://github.com/{REPO}/releases/download/packages/"
root = pathlib.Path(__file__).resolve().parent.parent
dist = root / "dist"
dist.mkdir(exist_ok=True)
errors, lines = [], []
# (author, id, name, version, downloads) per package, for the author pages.
credits = []


def download_counts():
    """{id: downloads} from the release assets <id>-<version>.cdwidget. Empty without GH_TOKEN."""
    if not os.environ.get("GH_TOKEN"):
        return {}
    out = subprocess.run(["gh", "api", f"repos/{REPO}/releases/tags/packages", "--jq", ".assets[] | [.name, .download_count] | @tsv"], capture_output=True, text=True)
    counts = {}
    # No release yet: no counts.
    for line in out.stdout.splitlines() if out.returncode == 0 else []:
        name, _, n = line.partition("\t")
        if name.endswith(".cdwidget") and n.isdigit():
            pid = name[: -len(".cdwidget")].rsplit("-", 1)[0]
            counts[pid] = counts.get(pid, 0) + int(n)
    return counts


counts = download_counts()


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
    downloads = counts.get(pid, 0)
    fields = [pid, sha, URL + file.name, version, manifest["author"], manifest.get("category", ""), manifest.get("name", pid), downloads]
    credits.append((" ".join(manifest["author"].split()), pid, manifest.get("name", pid), version, downloads))
    # Tabs and line breaks inside a field would break the line format.
    lines.append("\t".join(" ".join(str(f).split()) for f in fields) + "\n")

# featured.txt, edited by hand: title, from and to dates (YYYY-MM-DD) and comma-separated
# ids, tab-separated. Calmdesk shows the shelves whose dates include today.
ids = {c[1] for c in credits}
featured = root / "featured.txt"
shelves = featured.read_text(encoding="utf-8").splitlines() if featured.is_file() else []
for n, line in enumerate(shelves, 1):
    if not line.strip() or line.startswith("#"):
        continue
    f = line.split("\t")
    try:
        assert len(f) == 4, "4 tab-separated fields"
        datetime.date.fromisoformat(f[1]), datetime.date.fromisoformat(f[2])
        missing = [i for i in f[3].split(",") if i.strip() not in ids]
        assert not missing, f"unknown ids {missing}"
    except Exception as e:
        errors.append(f"featured.txt:{n}: {e}")

if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)
# Never empty: GitHub refuses to upload an empty file.
(dist / "index.txt").write_text("# Calmdesk widgets index\n" + "".join(lines), encoding="utf-8", newline="\n")
(dist / "featured.txt").write_text("# Calmdesk featured shelves\n" + "".join(l + "\n" for l in shelves if l.strip() and not l.startswith("#")), encoding="utf-8", newline="\n")

if os.environ.get("GH_TOKEN"):
    pages = root / "authors"
    pages.mkdir(exist_ok=True)
    for old in pages.glob("*.md"):
        old.unlink()
    for author in sorted({c[0] for c in credits}):
        mine = sorted((c for c in credits if c[0] == author), key=lambda c: -c[4])
        rows = "".join(f"| {name} | `{pid}` | {version} | {downloads} |\n" for _, pid, name, version, downloads in mine)
        total = sum(c[4] for c in mine)
        slug = re.sub(r"[^a-z0-9]+", "-", author.lower()).strip("-") or "author"
        (pages / f"{slug}.md").write_text(
            f"# {author}\n\n{len(mine)} widgets, {total} downloads in total.\n\n"
            f"| Widget | Id | Version | Downloads |\n|---|---|---|---|\n{rows}\n"
            "Downloads count every download of a package, including the ones Calmdesk makes to show a preview.\n",
            encoding="utf-8", newline="\n")
print(f"{len(lines)} packages")
