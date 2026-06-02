"""Parquet I/O for raw series and aligned panels."""
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR   = PROJECT_ROOT / "data_store" / "raw"
PANEL_DIR = PROJECT_ROOT / "data_store" / "panel"


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PANEL_DIR.mkdir(parents=True, exist_ok=True)


def save_raw(name: str, s: pd.Series) -> Path:
    ensure_dirs()
    path = RAW_DIR / f"{name}.parquet"
    s.to_frame(name=name).to_parquet(path)
    return path


def load_raw(name: str) -> pd.Series:
    return pd.read_parquet(RAW_DIR / f"{name}.parquet").iloc[:, 0]


def save_panel(df: pd.DataFrame, name: str = "master_panel") -> Path:
    ensure_dirs()
    path = PANEL_DIR / f"{name}.parquet"
    df.to_parquet(path)
    return path


def load_panel(name: str = "master_panel") -> pd.DataFrame:
    return pd.read_parquet(PANEL_DIR / f"{name}.parquet")
