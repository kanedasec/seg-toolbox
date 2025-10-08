import csv
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"


def _ensure_results_dir():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_DIR


def _normalize_value(v: Any) -> str:
    """Converte qualquer valor em string apropriada para CSV."""
    if v is None:
        return ""
    if isinstance(v, (str, int, float, bool)):
        return str(v)
    try:
        return json.dumps(v, ensure_ascii=False, default=str)
    except Exception:
        return str(v)


def save_result_csv(test_name: str, result: Dict[str, Any], filename: str | None = None) -> Path:
    """Salva resultado em CSV, adicionando automaticamente timestamp e duração."""
    _ensure_results_dir()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = filename or f"{test_name}-{ts}.csv"
    out_path = RESULTS_DIR / fname

    keys = sorted(result.keys())
    write_header = not out_path.exists()

    with out_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if write_header:
            writer.writerow(keys)
        row = [_normalize_value(result.get(k)) for k in keys]
        writer.writerow(row)

    return out_path


def save_result_json(test_name: str, result: Dict[str, Any], filename: str | None = None) -> Path:
    """Salva resultado em JSON bonito."""
    _ensure_results_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = filename or f"{test_name}-{ts}.json"
    out_path = RESULTS_DIR / fname

    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False, default=str)

    return out_path


def enrich_result(test_name: str, result: Dict[str, Any], start_time: float) -> Dict[str, Any]:
    """Adiciona metadados automáticos (timestamp e duração)."""
    enriched = dict(result)
    enriched["test_name"] = test_name
    enriched["run_timestamp"] = datetime.now().isoformat()
    enriched["duration_seconds"] = round(time.time() - start_time, 3)
    return enriched
