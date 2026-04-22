#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


MAX_PARALLEL = 4


# DIM IDs taken from information/dim.cpp (DIM::DIM2ID). Only rows in a DOE2
# file whose first column (id) is in this set are considered measured
# dimensions and compared against the meas file.
DIM_IDS: set[int] = {
    3312,  # ROUNDNESS_2D
    3313,  # STRAIGHTNESS
    3314,  # FLATNESS
    3320,  # DISTANCE (also X|Y|Z combined)
    3321,  # ANGLE_*
    3909,  # ROUNDNESS_3D
    5055,  # GEODESIC_DISTANCE
    5524,  # COORDINATE_X
    5525,  # COORDINATE_Y
    5526,  # COORDINATE_Z
    5537,  # X_DISTANCE
    5538,  # Y_DISTANCE
    5539,  # Z_DISTANCE
    5540,  # Y|Z
    5541,  # Z|X
    5542,  # X|Y
    5598,  # HYDRAULIC_DIAMETER
}


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


# ---------------------------------------------------------------------------
# Analysis phase: compare DOE2 (simulated) with meas (measured) and compute
# percent deviation per dimension.
# ---------------------------------------------------------------------------


def parse_doe2_file(path: Path) -> tuple[list[int], list[float], list[float]]:
    """Return (indices, sim_current, sim_set) for rows whose id is in DIM_IDS.

    DOE2 layout: 4 header lines, then rows
        id  index  current_value  set_value  lower_limit  upper_limit  name_unit
    Only the first 6 columns are needed.
    """
    indices: list[int] = []
    sim_current: list[float] = []
    sim_set: list[float] = []

    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line_no, raw in enumerate(fh, start=1):
            if line_no <= 4:
                continue
            line = raw.strip()
            if not line:
                continue
            parts = line.split(None, 6)
            if len(parts) < 6:
                continue
            try:
                id_ = int(parts[0])
            except ValueError:
                continue
            if id_ not in DIM_IDS:
                continue
            try:
                index = int(parts[1])
                current = float(parts[2])
                set_val = float(parts[3])
            except ValueError:
                print(f"  [warn] {path.name}:{line_no} unparseable row, skipping")
                continue
            indices.append(index)
            sim_current.append(current)
            sim_set.append(set_val)

    return indices, sim_current, sim_set


def parse_meas_file(path: Path) -> tuple[list[int], list[float], list[float]]:
    """Return (indices, meas_current, meas_set).

    Meas layout: 1 header line, then rows
        index  current  set
    """
    indices: list[int] = []
    meas_current: list[float] = []
    meas_set: list[float] = []

    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line_no, raw in enumerate(fh, start=1):
            if line_no == 1:
                continue
            line = raw.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            try:
                index = int(parts[0])
                current = float(parts[1])
                set_val = float(parts[2])
            except ValueError:
                print(f"  [warn] {path.name}:{line_no} unparseable row, skipping")
                continue
            indices.append(index)
            meas_current.append(current)
            meas_set.append(set_val)

    return indices, meas_current, meas_set


def parse_messung_csv(path: Path, indices: list[int]) -> tuple[list[int], list[float], list[float]]:
    """Read a Messung.csv and return (indices, meas_current, meas_set).

    Messung.csv layout (semicolon-separated):
        Line 1: headers like  "Messstelle 1 - IST; ... ; Messstelle 1 - SOLL; ..."
        Line 2: values like   "74.5; 84.; 13.1; ...; 75.; 84.51; 13.3; ..."
    First N values are current (IST), next N are set (SOLL).
    The indices are taken from the DOE2 file (positional pairing).
    """
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        lines = [l.strip() for l in fh if l.strip()]

    if len(lines) < 2:
        print(f"  [warn] {path}: too few lines in Messung.csv")
        return [], [], []

    values = [v.strip() for v in lines[1].split(";") if v.strip()]
    if len(values) % 2 != 0:
        print(
            f"  [warn] {path}: odd number of values ({len(values)}), "
            f"expected even (N current + N set)"
        )
        return [], [], []

    n = len(values) // 2
    try:
        meas_current = [float(v) for v in values[:n]]
        meas_set = [float(v) for v in values[n:]]
    except ValueError as exc:
        print(f"  [warn] {path}: unparseable value: {exc}")
        return [], [], []

    if len(indices) != n:
        m = min(len(indices), n)
        print(
            f"  [warn] {path}: {n} measurements but DOE2 has {len(indices)} "
            f"dimension rows — using first {m}"
        )
        return indices[:m], meas_current[:m], meas_set[:m]

    return indices, meas_current, meas_set


def find_messung_csv(doe2_path: Path) -> Path | None:
    """Walk up from the DOE2 file's directory looking for Messung.csv."""
    d = doe2_path.parent
    for _ in range(5):  # don't walk up more than 5 levels
        candidate = d / "Messung.csv"
        if candidate.is_file():
            return candidate
        parent = d.parent
        if parent == d:
            break
        d = parent
    return None


def meas_path_for(doe2_path: Path) -> Path:
    """Derive the sibling meas filename: <stem>_DOE2_<NNN>.txt -> <stem>_meas_<NNN>.txt"""
    new_name = re.sub(r"_DOE2_", "_meas_", doe2_path.name, count=1)
    return doe2_path.with_name(new_name)


def result_path_for(doe2_path: Path) -> Path:
    """Derive the per-file result filename: <stem>_DOE2_<NNN>.txt -> <stem>_result_<NNN>.txt"""
    new_name = re.sub(r"_DOE2_", "_result_", doe2_path.name, count=1)
    return doe2_path.with_name(new_name)


def compare_pair(doe2_path: Path) -> tuple[Path, float] | None:
    """Compare a DOE2 file against its meas sibling. Write <stem>_result_<NNN>.txt.

    Tries *_meas_*.txt first; if not found, falls back to Messung.csv
    in the parent directories.

    Returns (result_path, sum_of_ProzAbweichung) on success, None if skipped.
    """
    sim_idx, sim_cur, sim_set_arr = parse_doe2_file(doe2_path)

    meas_source: str = ""
    meas_path = meas_path_for(doe2_path)
    if meas_path.is_file():
        meas_idx, meas_cur, meas_set_arr = parse_meas_file(meas_path)
        meas_source = meas_path.name
    else:
        csv_path = find_messung_csv(doe2_path)
        if csv_path is not None:
            meas_idx, meas_cur, meas_set_arr = parse_messung_csv(csv_path, sim_idx)
            meas_source = str(csv_path)
        else:
            print(
                f"  [skip] no meas file for {doe2_path.name} "
                f"(no {meas_path.name} and no Messung.csv found)"
            )
            return None

    n = min(len(sim_idx), len(meas_idx))
    if n == 0:
        print(f"  [skip] no comparable rows in {doe2_path.name}")
        return None

    if len(sim_idx) != len(meas_idx):
        print(
            f"  [warn] {doe2_path.name}: DOE2 has {len(sim_idx)} rows, "
            f"meas has {len(meas_idx)} rows — comparing first {n}"
        )

    result_path = result_path_for(doe2_path)
    total = 0.0
    rows: list[str] = []

    for i in range(n):
        if sim_idx[i] != meas_idx[i]:
            print(
                f"  [warn] {doe2_path.name}: index mismatch at position {i} "
                f"(DOE2={sim_idx[i]}, meas={meas_idx[i]}) — using positional pairing"
            )

        mc = meas_cur[i]
        ms = meas_set_arr[i]
        sc = sim_cur[i]
        ss = sim_set_arr[i]

        nenner = 0.03 * abs(mc) + abs(mc - ms) + 0.02
        proz = 100.0 * (mc - sc - ms + ss) / nenner
        total += abs(proz)

        rows.append(
            f"{meas_idx[i]:>6d}  "
            f"meas_cur={mc:>15.8g}  meas_set={ms:>15.8g}  "
            f"sim_cur={sc:>15.8g}  sim_set={ss:>15.8g}  "
            f"ProzAbweichung={proz:>15.8g}"
        )
    total /= n

    with result_path.open("w", encoding="utf-8") as fh:
        fh.write(f"# source DOE2: {doe2_path.name}\n")
        fh.write(f"# source meas: {meas_source}\n")
        fh.write(f"# rows compared: {n}\n")
        fh.write(
            "# columns: index  meas_current  meas_set  sim_current  sim_set  ProzAbweichung\n"
        )
        for line in rows:
            fh.write(line + "\n")
        fh.write(f"\nSUM = {total:.8g}\n")

    return result_path, total


def analyse_results(rm1_root: Path) -> None:
    """Find every *_DOE2_*.txt under rm1_root, compare with its meas sibling,
    write per-file results, and collect all sums into rm1_root/result.txt."""
    doe2_files = sorted(p.resolve() for p in rm1_root.rglob("*_DOE2_*.txt") if p.is_file())

    if not doe2_files:
        print(f"\nNo *_DOE2_*.txt files found below: {rm1_root}")
        return

    print(f"\nAnalysing {len(doe2_files)} DOE2 result file(s).")

    summary: list[tuple[Path, float]] = []
    for doe2 in doe2_files:
        outcome = compare_pair(doe2)
        if outcome is not None:
            result_path, total = outcome
            summary.append((result_path, total))
            print(f"  wrote {result_path.name}  SUM = {total:.8g}")

    collected = rm1_root / "result_all.txt"
    with collected.open("w", encoding="utf-8") as fh:
        summ_all = 0.	
        fh.write("# result_file\tsum_ProzAbweichung\n")
        for result_path, total in summary:
            try:
                rel = result_path.relative_to(rm1_root)
            except ValueError:
                rel = result_path
            fh.write(f"{rel}\t{total:.8g}\n")
            summ_all += total
        fh.write(f"\n Summ: {summ_all:.8g}\n")
    print(f"\nCollected summary written to: {collected}")


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

    analyse_results(rm1_root)


if __name__ == "__main__":
    main()
