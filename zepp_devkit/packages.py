"""Packages from the .zab that `zeus build` writes: one device's .zpk, or one per screen.

A .zab holds one .zpk per screen size and chip. A QR install sends exactly one .zpk (the
Zepp app can't install a .zab), so it must be the one built for the watch: picking another
still installs, scaled for another screen. The store takes the .zab itself.
"""
import html
import io
import json
import zipfile
from pathlib import Path

from .qr import make as make_qr

BALANCE_3 = 11141376  # Amazfit Balance 3, 480x480 round


def _zab(dist):
    zabs = sorted(Path(dist).glob("*.zab"))
    if len(zabs) != 1:
        raise SystemExit(f"expected exactly one .zab in {dist}, found {len(zabs)}")
    return zabs[0]


def _sources(zpk):
    with zipfile.ZipFile(io.BytesIO(zpk)) as z, zipfile.ZipFile(io.BytesIO(z.read("device.zip"))) as d:
        return sorted({p.get("deviceSource") for p in json.loads(d.read("app.json")).get("platforms", [])} - {None})


def extract(dist, dest, device_source=BALANCE_3, device_zip=None):
    """Write the .zpk built for device_source (and, optionally, its inner device.zip for the emulator)."""
    zab = _zab(dist)
    with zipfile.ZipFile(zab) as z:
        for name in [n for n in z.namelist() if n.endswith(".zpk")]:
            zpk = z.read(name)
            if device_source in _sources(zpk):
                dest = Path(dest)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zpk)
                if device_zip:
                    with zipfile.ZipFile(io.BytesIO(zpk)) as inner:
                        Path(device_zip).parent.mkdir(parents=True, exist_ok=True)
                        Path(device_zip).write_bytes(inner.read("device.zip"))
                return name
    raise SystemExit(f"no package in {zab.name} targets deviceSource {device_source}")


def split(dist, dest, prefix):
    """One .zpk per screen and chip (<prefix>-r480-zps.zpk ...) plus packages.json:
    {file: {"screen", "chip", "sources"}}. -> that index."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    index = {}
    with zipfile.ZipFile(_zab(dist)) as zab:
        for entry in json.loads(zab.read("manifest.json"))["zpks"]:
            platform = entry["platforms"][0]
            zpk = zab.read(entry["name"])
            shape = "r" if platform["screenType"] == "round" else "s"
            size = platform["screenResolution"]
            res = size.split("x")[0] if shape == "r" else size
            name = f"{prefix}-{shape}{res}-{platform['cpuPlatform'].lower()}.zpk"
            (dest / name).write_bytes(zpk)
            index[name] = {"screen": f"{platform['screenType']} {size}", "chip": platform["cpuPlatform"], "sources": _sources(zpk)}
    (dest / "packages.json").write_text(json.dumps(index, indent=2) + "\n")
    return index


STATUS = {"tested": "tested", "emulator": "checked in the emulator", "untested": "untested"}


def picker(pkg_dir, url_base, models, default="Balance 3", colour="#14223A"):
    """HTML for an install page: a watch-model list choosing between the QR codes of the
    packages in pkg_dir/packages.json (written next to them). models: [{"name", "sources",
    "status"}] (status tested, emulator or untested; others aren't listed)."""
    pkg_dir = Path(pkg_dir)
    packages = json.loads((pkg_dir / "packages.json").read_text())
    by_source = {s: name for name, p in packages.items() for s in p["sources"]}
    options = []
    for m in models:
        if m.get("status") not in STATUS:
            continue
        pkg = next((by_source[s] for s in m["sources"] if s in by_source), None)
        if not pkg:
            continue
        qr = f"qr-{pkg.removesuffix('.zpk')}.png"
        if not (pkg_dir / qr).exists():
            make_qr(pkg_dir / qr, f"zpkd1://{url_base}/{pkg}", colour)
        selected = " selected" if m["name"] == default else ""
        label = f"{m['name']} ({STATUS[m['status']]})"
        options.append(f'<option value="{html.escape(pkg)}" data-qr="{html.escape(qr)}"{selected}>{html.escape(label)}</option>')
    first = next((o for o in options if " selected" in o), options[0] if options else "")
    if not first:
        return "<p>No packages.</p>"
    pkg0 = first.split('value="')[1].split('"')[0]
    qr0 = first.split('data-qr="')[1].split('"')[0]
    d = pkg_dir.name
    return f'''<label for="model">Your watch</label>
<select id="model">{"".join(options)}</select>
<p><img class="qr" id="qr" src="{d}/{qr0}" alt="Install QR code for the chosen watch"></p>
<p><a id="pkg" href="{d}/{pkg0}">{pkg0}</a></p>
<script>
document.getElementById('model').addEventListener('change', (e) => {{
  const o = e.target.selectedOptions[0];
  document.getElementById('qr').src = '{d}/' + o.dataset.qr;
  const a = document.getElementById('pkg'); a.href = '{d}/' + o.value; a.textContent = o.value;
}});
</script>'''
