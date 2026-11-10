#!/usr/bin/env python3
"""Check this repository's catalog on FREEHOLD itself, before a push.

    tools/check.py /path/to/FREEHOLD [NAME ...]

Boots FREEHOLD's shipped image (built, in the FREEHOLD checkout) under
QEMU with FREEHOLD's gate machinery, serves this repository over HTTPS
from the host with a test CA the test image trusts, and has GET install
every application in CATALOG.TXT (or those named) exactly as a machine
would, then runs a short check of each. Needs what FREEHOLD's gates need
(QEMU, OVMF, openssl).
"""

import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A command per application and what it must print.
CHECKS = {
    "TCC": [("C:\\APPS\\TCC\\TCC -o D:\\HELLO.EXE C:\\APPS\\TCC\\SAMPLES\\HELLO.C", r".*"),
            ("D:\\HELLO", r"Hello")],
    "LUA": [("DIR C:\\APPS\\LUA\\ONELUA.C", r"(?i)onelua\.c")],
    "MUSIC": [("C:\\APPS\\MUSIC\\MUSIC /?", r"C:\\APPS\\MUSIC\\FLUIDR3\.SF3")],
    "DOOM": [("DIR C:\\APPS\\DOOM", r"FREEDOOM1\.WAD")],
    "EGUIDEMO": [("DIR C:\\APPS\\EGUIDEMO", r"EGUIDEMO\.EXE")],
    "RIPGREP": [("C:\\APPS\\RIPGREP\\RG --version", r"ripgrep 15\.2\.0")],
    "FILESERVE": [("DIR C:\\APPS\\FILESERVE", r"FILE-SERVE\.EXE")],
    "NONET": [("DIR C:\\APPS\\NONET", r"NONET\.EXE")],
}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    freehold = os.path.abspath(sys.argv[1])
    sys.path.insert(0, os.path.join(freehold, "tools"))
    import gate  # FREEHOLD's tools/gate.py

    catalog = open(os.path.join(HERE, "CATALOG.TXT"), encoding="utf-8").read()
    names = [ln.split()[0] for ln in catalog.splitlines() if ln.strip() and not ln.startswith(";")]
    wanted = [n.upper() for n in sys.argv[2:]] or names

    workdir = tempfile.mkdtemp(prefix="apps-check-")
    pki = gate.make_test_pki(os.path.join(workdir, "pki"), print)
    root = os.path.join(workdir, "root")
    shutil.copytree(os.path.join(freehold, "dist", "root"), root)
    shutil.copy(os.path.join(pki, "ca.pem"), os.path.join(root, "FREEHOLD", "CERTS", "GATECA.PEM"))
    with open(os.path.join(root, "CONFIG.SYS"), "rb") as f:
        lines = [ln for ln in f.read().decode().replace("\r\n", "\n").split("\n") if not ln.upper().startswith("CATALOG=")]
    lines.insert(0, f"CATALOG=https://10.0.2.2:{gate.GET_PORTS['good']}/CATALOG.TXT")
    with open(os.path.join(root, "CONFIG.SYS"), "wb") as f:
        f.write("\r\n".join(lines).encode())
    image = os.path.join(workdir, "apps.img")
    r = gate.subprocess.run([gate.imagetool(), "build", "--out", image, "--kernel", os.path.join(freehold, "dist", "BOOTX64.EFI"),
                             "--root", root, "--data", os.path.join(freehold, "dist", "data"), "--c-mib", "160"],
                            capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"check: image: {r.stdout}{r.stderr}")

    # This repository, as GitHub would serve it.
    files = {}
    for name in os.listdir(os.path.join(HERE, "ZIPS")):
        files[name] = (open(os.path.join(HERE, "ZIPS", name), "rb").read(), None)
    servers = gate.CatalogServers(pki, files)
    servers_catalog = catalog.encode()
    gate.get_catalog = lambda _files, _version: servers_catalog

    vm = gate.Vm("primary", workdir, workdir, print, image)
    failed = []
    try:
        vm.start()
        gate.boot_to_prompt(vm)
        gate.expect_out(vm, "IPCFG DHCP", r"10\.0\.2\.15", "the network is up", timeout=60)
        gate.expect_out(vm, "GET", r"^" + names[0], "GET lists this repository's catalog")
        for name in wanted:
            try:
                gate.expect_out(vm, f"GET {name}", rf"{name} \S+ installed in C:\\APPS\\{name}", f"GET {name}", timeout=600)
                for command, pattern in CHECKS.get(name, []):
                    gate.expect_out(vm, command, pattern, f"{name}: {command}", timeout=120)
            except gate.GateFail as e:
                print(f"check: {name} FAILED: {e}")
                failed.append(name)
        gate.shutdown(vm)
    finally:
        vm.stop()
        servers.close()
    if failed:
        sys.exit(f"check: failed: {' '.join(failed)}")
    print(f"check: {len(wanted)} application(s) install from the catalog and run")


if __name__ == "__main__":
    main()
