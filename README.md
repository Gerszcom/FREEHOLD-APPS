# FREEHOLD's applications

The applications FREEHOLD's `GET` installs (FREEHOLD's `DECISIONS.md`,
D-107, D-115 and D-116). FREEHOLD ships without them; a machine that wants
one types its name:

```
C:\> GET                 the applications, and which are installed
C:\> GET TCC             installs C:\APPS\TCC
C:\> GET /U TCC          updates it; the old version stays as C:\APPS\TCC.OLD
C:\> GET /R TCC          removes it
```

`GET` reads [`CATALOG.TXT`](CATALOG.TXT) from this repository's main
branch over HTTPS (the first `CATALOG=` line of FREEHOLD's `CONFIG.SYS`),
checks each download against the length and SHA-256 listed there, and
unpacks it into `C:\APPS\NAME\`. Nothing else is written anywhere: what is
installed is what is in `C:\APPS`, and deleting a directory removes an
application completely.

## What is here

| Application | What it is | Licence |
|---|---|---|
| `TCC` | TinyCC: a C compiler that runs on FREEHOLD and makes FREEHOLD programs, with FREEHOLD's C library and its own source | LGPL-2.1-or-later |
| `LUA` | Lua 5.4.7's source, for TCC to build | MIT |
| `MUSIC` | A music player: WAV, FLAC, MP3, Ogg Vorbis, and MIDI through the FluidR3 Mono SoundFont | MIT |
| `DOOM` | DOOM's engine (doomgeneric) with Freedoom: Phase 1, and the engine's source | GPL-2.0-only; Freedoom BSD-3-Clause |
| `EGUIDEMO` | egui's demo, full-screen with the mouse | MIT, MIT or Apache-2.0 |
| `RIPGREP` | `rg`, ripgrep 15.2.0 | Unlicense or MIT |
| `FILESERVE` | `file-serve` 0.3.11: the current directory over HTTP | MIT or Apache-2.0 |
| `NONET` | A Sudoku solver that animates its search | MIT |

Each application's `PROGRAM.INF` (in `APPS/NAME/`) names it, its version,
its licence and the exact source it was built from, and its commands. The
same file is in its zip, and so in `C:\APPS\NAME\` once installed.

## How a release is made

Built files are made by FREEHOLD's own build, never by hand:

1. In a FREEHOLD checkout, `tools/build.sh` (it builds the ports and the
   std programs too).
2. Here, raise `Version=` in the application's `APPS/NAME/PROGRAM.INF`.
3. `tools/package.py /path/to/FREEHOLD NAME` assembles the directory as
   `GET` installs it, zips it into `ZIPS/NAME-VERSION.ZIP` (the same files
   always give the same bytes) and writes `CATALOG.TXT` again.
4. `tools/check.py /path/to/FREEHOLD NAME` boots FREEHOLD under QEMU,
   serves this repository to it over HTTPS and has `GET` install the
   application and run it, as a machine would.
5. Commit and push. Machines see the new version the next time they run
   `GET`.

The zips are kept in `ZIPS/` and served from the repository itself, so
nothing but a push is needed to publish. They could move to GitHub
releases without any change to `GET`: only the addresses in the catalog
would change.

## Licence

The files of this repository that are not an application's (this README,
`tools/`, `LICENSE`) are MIT, as FREEHOLD is. Each application keeps its own licence,
named in its `PROGRAM.INF` and carried in its zip.
