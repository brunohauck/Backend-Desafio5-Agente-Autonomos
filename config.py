from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "storage/datasets"
PROFILE_DIR = BASE_DIR / "storage/profiles"
PLOTS_DIR = BASE_DIR / "storage/plots"
MEMORY_DIR = BASE_DIR / "storage/memory"

for p in [DATASET_DIR, PROFILE_DIR, PLOTS_DIR, MEMORY_DIR]:
    p.mkdir(parents=True, exist_ok=True)