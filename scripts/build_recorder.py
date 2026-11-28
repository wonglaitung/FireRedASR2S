from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_recorder")
    parser.add_argument("--name", default="FireRedRecorder")
    parser.add_argument("--onefile", action="store_true", help="Single-file build")
    parser.add_argument("--console", action="store_true", help="Keep a console window")
    parser.add_argument(
        "--no-collect-all",
        action="store_true",
        help="Do not collect every PyQt6 module (smaller, may miss plugins)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    dist = ROOT / "dist"
    work = ROOT / "build"
    for path in (dist, work):
        if path.exists():
            shutil.rmtree(path)
    work.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        args.name,
        "--paths",
        str(ROOT / "src"),
        "--specpath",
        str(work),
    ]
    if not args.console and sys.platform in {"win32", "darwin"}:
        cmd.append("--windowed")
    if args.onefile:
        cmd.append("--onefile")
    if not args.no_collect_all:
        cmd.extend(["--collect-all", "PyQt6"])
    cmd.extend(["--add-data", f"{ROOT / 'assets'}{os.pathsep}assets"])
    cmd.append(str(ROOT / "src" / "firered_recorder" / "__main__.py"))

    subprocess.run(cmd, check=True, cwd=ROOT)

    if args.onefile:
        artifact = dist / (f"{args.name}.exe" if sys.platform == "win32" else args.name)
    else:
        artifact = dist / args.name / (
            f"{args.name}.exe" if sys.platform == "win32" else args.name
        )
    print(f"artifact: {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
