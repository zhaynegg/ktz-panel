"""
Export simulation data as static JSON for the Next.js frontend.

From repo root:
  python scripts/export_train_chart_json.py

Output:
  frontend/public/data/train_simulation.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from locomotive_simulator import run_scenario, simple_quality_check  # noqa: E402


def main() -> None:
    rows = run_scenario(ticks=200, seed=42, locomotive_type="electric")
    q = simple_quality_check(rows)

    payload = {
        "series": [
            {
                "tick": r["tick"],
                "speed_kmh": r["speed_kmh"],
                "traction_power_kw": r["traction_power_kw"],
                "engine_temp_c": r["engine_temp_c"],
                "transformer_temp_c": r["transformer_temp_c"],
                "brake_pipe_pressure_bar": r["brake_pipe_pressure_bar"],
                "vibration_mm_s": r["vibration_mm_s"],
                "state": r["state"],
                "fault_code": r["fault_code"],
            }
            for r in rows
        ],
        "quality": {
            "passed": q["passed"],
            "avg_residual": q["avg_residual"],
            "max_residual": q["max_residual"],
            "fault_ticks": q["fault_ticks"],
            "total_ticks": q["total_ticks"],
            "message": q["message"],
        },
    }

    out = Path(__file__).resolve().parents[1] / "frontend" / "public" / "data" / "train_simulation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"Quality: passed={q['passed']}, {q['message']}")


if __name__ == "__main__":
    main()
