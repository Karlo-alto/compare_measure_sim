#!/usr/bin/env python3
from __future__ import annotations

import os
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


MAX_PARALLEL = 4


def ask_user_input() -> tuple[Path, Path, str]:
    exepath_str = input("Enter path to cmsolver.exe (exepath): ").strip().strip('"')
    rm1_root_str = input("Enter root path to search for .rm1 files (rm1_root): ").strip().strip('"')
    commandstring = input("Enter additional command line options (Commandstring): ").strip()

    exepath = Path(exepath_str)
    rm1_root = Path(rm1_root_str)

    if not exepath.is_file():
        raise FileNotFoundError(f"cmsolver.exe not found: {exepath}")

    if not rm1_root.is_dir():
        raise NotADirectoryError(f"Search root does not exist or is not a directory: {rm1_root}")

    return exepath, rm1_root, commandstring


def find_rm1_files(rm1_root: Path) -> list[Path]:
    return sorted(p.resolve() for p in rm1_root.rglob("*.rm1") if p.is_file())


def run_solver(exepath: Path, rm1_file: Path, commandstring: str) -> tuple[Path, int]:
    cmd = [
        str(exepath),
        "-rm1",
        str(rm1_file),
        "-sim",
        "15",
    ]

    if commandstring:
        cmd.extend(shlex.split(commandstring, posix=False))

    print(f"Starting: {' '.join(f'\"{c}\"' if ' ' in c else c for c in cmd)}")

    completed = subprocess.run(cmd, check=False)
    return rm1_file, completed.returncode


def main() -> None:
    try:
        exepath, rm1_root, commandstring = ask_user_input()
    except Exception as exc:
        print(f"Input error: {exc}")
        return

    rm1_files = find_rm1_files(rm1_root)

    if not rm1_files:
        print(f"No .rm1 files found below: {rm1_root}")
        return

    print(f"Found {len(rm1_files)} .rm1 file(s).")
    print(f"Running up to {MAX_PARALLEL} processes in parallel.\n")

    results: list[tuple[Path, int]] = []

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
        futures = {
            executor.submit(run_solver, exepath, rm1_file, commandstring): rm1_file
            for rm1_file in rm1_files
        }

        for future in as_completed(futures):
            rm1_file = futures[future]
            try:
                file_path, returncode = future.result()
                results.append((file_path, returncode))
                status = "OK" if returncode == 0 else f"FAILED ({returncode})"
                print(f"Finished: {file_path} -> {status}")
            except Exception as exc:
                results.append((rm1_file, -1))
                print(f"Error running {rm1_file}: {exc}")

    ok_count = sum(1 for _, code in results if code == 0)
    fail_count = len(results) - ok_count

    print("\nSummary")
    print("-------")
    print(f"Total files : {len(results)}")
    print(f"Succeeded   : {ok_count}")
    print(f"Failed      : {fail_count}")

    if fail_count:
        print("\nFailed files:")
        for file_path, code in results:
            if code != 0:
                print(f"  {file_path} -> {code}")


if __name__ == "__main__":
    main()