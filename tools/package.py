#!/usr/bin/env python3
"""Package FREEHOLD's applications from a FREEHOLD build, and write the
catalog GET reads.

    tools/package.py /path/to/FREEHOLD [NAME ...]

The FREEHOLD checkout must be built (tools/build.sh there). For each
application (all of them, or those named) this assembles its directory
exactly as GET installs it into C:\\APPS\\NAME: the files named in FILES
below, from the build, and APPS/NAME/PROGRAM.INF from here. It is zipped
into ZIPS/NAME-VERSION.ZIP, entries sorted and dated 2026-01-01 so the
same files always give the same zip, and CATALOG.TXT is written again from
every zip in ZIPS whose version is the one in its PROGRAM.INF.

A catalog line is NAME VERSION BYTES SHA256 ADDRESS DESCRIPTION (D-122);
the address is relative to the catalog, which GitHub serves from the
repository's main branch.
"""

import hashlib
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Application -> (path in the FREEHOLD checkout, path inside the
# application's directory); a directory is copied whole.
FILES = {
    "TCC": [("dist/extras/APPS/TCC", "")],
    "LUA": [("dist/extras/APPS/LUA", "")],
    "MUSIC": [("dist/extras/APPS/MUSIC", "")],
    "DOOM": [("dist/extras/APPS/DOOM", ""),
             ("target/ports/build/DOOM.EXE", "DOOM.EXE"),
             ("target/ports/games/GAMES/FREEDOOM1.WAD", "FREEDOOM1.WAD"),
             ("target/ports/games/GAMES/FREEDOOM.TXT", "FREEDOOM.TXT")],
    "EGUIDEMO": [("dist/extras/APPS/EGUIDEMO.EXE", "EGUIDEMO.EXE")],
    "RIPGREP": [("dist/extras/APPS/RG.EXE", "RG.EXE"),
                ("@crate:ripgrep-15.2.0/COPYING", "COPYING"),
                ("@crate:ripgrep-15.2.0/UNLICENSE", "UNLICENSE"),
                ("@crate:ripgrep-15.2.0/LICENSE-MIT", "LICENSE-MIT")],
    "FILESERVE": [("dist/extras/APPS/FILE-SERVE.EXE", "FILE-SERVE.EXE"),
                  ("@crate:file-serve-0.3.11/LICENSE-MIT", "LICENSE-MIT"),
                  ("@crate:file-serve-0.3.11/LICENSE-APACHE", "LICENSE-APACHE")],
    "NONET": [("dist/extras/APPS/NONET.EXE", "NONET.EXE")],
}

STAMP = (2026, 1, 1, 0, 0, 0)


def crate_file(rel):
    """A file of a crate in the local cargo registry (licence texts)."""
    base = os.path.expanduser("~/.cargo/registry/src")
    for index in sorted(os.listdir(base)):
        path = os.path.join(base, index, rel)
        if os.path.exists(path):
            return path
    sys.exit(f"package: {rel} is not in ~/.cargo/registry (build FREEHOLD's std programs first)")


def program_inf(name):
    path = os.path.join(HERE, "APPS", name, "PROGRAM.INF")
    text = open(path, encoding="utf-8").read()
    fields = dict(re.findall(r"^(\w+)=(.*)$", text.split("[Commands]")[0], re.M))
    return path, fields["Version"].strip(), fields["Description"].strip()


def entries(freehold, name):
    """(name in the zip, bytes) for every file of the application."""
    out = {}
    for src, dst in FILES[name]:
        path = crate_file(src[7:]) if src.startswith("@crate:") else os.path.join(freehold, src)
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for f in files:
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, path).replace(os.sep, "/")
                    out[(dst + "/" + rel).lstrip("/")] = open(full, "rb").read()
        elif os.path.isfile(path):
            out[dst] = open(path, "rb").read()
        else:
            sys.exit(f"package: {path} is missing (build FREEHOLD first: tools/build.sh)")
    inf, _, _ = program_inf(name)
    out["PROGRAM.INF"] = open(inf, "rb").read()
    return out


def package(freehold, name):
    _, version, _ = program_inf(name)
    files = entries(freehold, name)
    os.makedirs(os.path.join(HERE, "ZIPS"), exist_ok=True)
    out = os.path.join(HERE, "ZIPS", f"{name}-{version}.ZIP")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        dirs = sorted({"/".join(n.split("/")[:i]) + "/" for n in files for i in range(1, n.count("/") + 1)})
        for d in dirs:
            info = zipfile.ZipInfo(d, STAMP)
            info.external_attr = 0o40755 << 16 | 0x10
            z.writestr(info, b"")
        for n in sorted(files):
            info = zipfile.ZipInfo(n, STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, files[n])
    print(f"package: ZIPS/{name}-{version}.ZIP, {len(files)} files, {os.path.getsize(out)} bytes")


def catalog():
    lines = ["; FREEHOLD's applications: GET reads this file (FREEHOLD's DECISIONS.md, D-122).",
             "; NAME VERSION BYTES SHA256 ADDRESS DESCRIPTION; addresses are relative to this file.",
             "; Written by tools/package.py; do not edit by hand."]
    for name in sorted(FILES):
        _, version, what = program_inf(name)
        zip_path = os.path.join(HERE, "ZIPS", f"{name}-{version}.ZIP")
        if not os.path.exists(zip_path):
            print(f"package: no ZIPS/{name}-{version}.ZIP; {name} left out of the catalog")
            continue
        data = open(zip_path, "rb").read()
        lines.append(f"{name} {version} {len(data)} {hashlib.sha256(data).hexdigest()} ZIPS/{name}-{version}.ZIP {what}")
    with open(os.path.join(HERE, "CATALOG.TXT"), "w", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"package: CATALOG.TXT, {len(lines) - 3} applications")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    freehold = os.path.abspath(sys.argv[1])
    names = [n.upper() for n in sys.argv[2:]] or sorted(FILES)
    for name in names:
        if name not in FILES:
            sys.exit(f"package: no application {name}")
        package(freehold, name)
    catalog()


if __name__ == "__main__":
    main()
