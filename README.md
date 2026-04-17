# Run_rm1s_and_compare

A Python script that runs cmsolver.exe simulations and compares the results against measured values.

## What it does

1. **Run simulations** -- Searches recursively for `*.rm1` files and runs `cmsolver.exe` on each with up to 4 processes in parallel.
2. **Parse simulation results** -- Reads the `*_DOE2_*.txt` output files and extracts dimension rows (distance, angle, flatness, coordinates, etc.) identified by their DIM IDs.
3. **Read measurement data** -- For each DOE2 file, looks for measured values in two formats:
   - `*_meas_*.txt` (tab-separated: index, current_value, set_value) next to the DOE2 file
   - `Messung.csv` (semicolon-separated, first N values = IST, next N = SOLL) in a parent directory -- used as fallback when no meas file exists
4. **Compute deviation** -- For each dimension index, calculates:
   ```
   nenner = 0.03 * |meas_current| + |meas_current - meas_set| + 0.02
   ProzAbweichung = 100 * (meas_current - sim_current - meas_set + sim_set) / nenner
   ```
5. **Write results**:
   - `*_result_*.txt` per DOE2 file with per-index deviations and the average of absolute deviations
   - `result_all.txt` at the search root collecting all file sums

## Usage

```
python src/Run_rm1s_and_compare.py
```

The script prompts for three inputs:

| Input | Description |
|-------|-------------|
| **exepath** | Path to the `cmsolver.exe` executable |
| **rm1_root** | Root directory to search recursively for `*.rm1` files |
| **Commandstring** | Additional command line options passed to cmsolver |

Each solver invocation runs as:
```
cmsolver.exe -rm1 <rm1_file> -sim 15 <Commandstring>
```

## Important: set_value in DOE2 files

The `set_value` column in the `*_DOE2_*.txt` files must correspond to the dimensions of the input geometry used for the simulation. These are the nominal target values against which both simulated and measured results are compared. The deviation formula uses `set_value` from both the simulation (DOE2) and the measurement (meas/Messung.csv) to compute how well simulation and measurement agree relative to the nominal geometry.

## Directory structure example

```
rm1_root/
  project_A/
    Messung.csv              <-- measurement data (IST/SOLL, semicolon-separated)
    V1/
      project_A_001.rm1      <-- solver input
      project_A_DOE2_001.txt <-- solver output (simulation results)
      project_A_result_001.txt <-- generated comparison result
  project_B/
    V1/
      project_B_001.rm1
      project_B_DOE2_001.txt
      project_B_meas_001.txt <-- measurement data (alternative format)
      project_B_result_001.txt
  result_all.txt             <-- aggregated results across all projects
```

## DIM IDs

The script filters DOE2 rows by dimension type IDs defined in `information/dim.cpp`. Only rows with the following IDs are compared against measurements:

| ID | Type |
|----|------|
| 3312 | Roundness 2D |
| 3313 | Straightness |
| 3314 | Flatness |
| 3320 | Distance |
| 3321 | Angle |
| 3909 | Roundness 3D |
| 5055 | Geodesic distance |
| 5524--5526 | Coordinate X/Y/Z |
| 5537--5539 | X/Y/Z distance |
| 5540--5542 | Combined distances (YZ, ZX, XY) |
| 5598 | Hydraulic diameter |
