"""
Run the locomotive simulator, show graphs, and print a quality check.

Prerequisites:
  pip install -r scripts/requirements.txt

From repository root:
  python scripts/run_simulation.py
  python scripts/run_simulation.py --ticks 300 --seed 7

Matplotlib window will open; PNGs saved to scripts/output/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure scripts/ is on sys.path so locomotive_simulator can be imported directly.
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from locomotive_simulator import LocomotiveSimulator, run_scenario, simple_quality_check  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run simulation, plot graphs, quality check")
    parser.add_argument("--ticks", type=int, default=200, help="Number of simulation ticks")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility")
    parser.add_argument("--type", default="electric", choices=["electric", "diesel"])
    parser.add_argument("--no-show", action="store_true", help="Save PNGs but don't open window")
    args = parser.parse_args()

    # ---- Run simulation ----
    rows = run_scenario(ticks=args.ticks, seed=args.seed, locomotive_type=args.type)

    # ---- Quality check ----
    q = simple_quality_check(rows)
    print("=" * 60)
    print("  QUALITY CHECK (power-balance consistency)")
    print("=" * 60)
    print(f"  Passed:        {q['passed']}")
    print(f"  Avg residual:  {q['avg_residual']:.4f}  (threshold 0.25)")
    print(f"  Max residual:  {q['max_residual']:.4f}")
    print(f"  Fault ticks:   {q['fault_ticks']}/{q['total_ticks']}")
    print(f"  Message:       {q['message']}")
    print("=" * 60)

    # ---- Plotting ----
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed — run:  pip install -r scripts/requirements.txt", file=sys.stderr)
        return

    out_dir = _SCRIPTS / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    ticks = [r["tick"] for r in rows]
    speed = [r["speed_kmh"] for r in rows]
    power = [r["traction_power_kw"] for r in rows]
    eng_t = [r["engine_temp_c"] for r in rows]
    xfm_t = [r["transformer_temp_c"] for r in rows]
    brake = [r["brake_pipe_pressure_bar"] for r in rows]
    vib = [r["vibration_mm_s"] for r in rows]
    states = [r["state"] for r in rows]

    fig, axes = plt.subplots(3, 2, figsize=(14, 10), sharex=True)
    fig.suptitle(f"Locomotive Simulation — {args.ticks} ticks, seed={args.seed}, type={args.type}", fontsize=13)

    # 1) Speed
    ax = axes[0, 0]
    ax.plot(ticks, speed, color="#2563eb", linewidth=1.2)
    ax.set_ylabel("Speed (km/h)")
    ax.set_title("Speed")
    ax.grid(True, alpha=0.3)

    # 2) Traction power
    ax = axes[0, 1]
    ax.plot(ticks, power, color="#16a34a", linewidth=1.2)
    ax.set_ylabel("Power (kW)")
    ax.set_title("Traction Power")
    ax.grid(True, alpha=0.3)

    # 3) Temperatures
    ax = axes[1, 0]
    ax.plot(ticks, eng_t, color="#ea580c", linewidth=1.2, label="Engine")
    ax.plot(ticks, xfm_t, color="#d946ef", linewidth=1.2, label="Transformer")
    ax.set_ylabel("Temperature (C)")
    ax.set_title("Temperatures")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 4) Brake pressure
    ax = axes[1, 1]
    ax.plot(ticks, brake, color="#0891b2", linewidth=1.2)
    ax.set_ylabel("Pressure (bar)")
    ax.set_title("Brake Pipe Pressure")
    ax.grid(True, alpha=0.3)

    # 5) Vibration
    ax = axes[2, 0]
    ax.plot(ticks, vib, color="#b45309", linewidth=1.2)
    ax.set_ylabel("Vibration (mm/s)")
    ax.set_xlabel("Tick")
    ax.set_title("Vibration")
    ax.grid(True, alpha=0.3)

    # 6) State timeline (color-coded)
    ax = axes[2, 1]
    state_map = {"IDLE": 0, "ACCELERATING": 1, "CRUISING": 2, "BRAKING": 3}
    state_colors = {"IDLE": "#94a3b8", "ACCELERATING": "#2563eb", "CRUISING": "#16a34a", "BRAKING": "#dc2626"}
    state_nums = [state_map.get(s, 0) for s in states]
    for i in range(len(ticks) - 1):
        ax.fill_between([ticks[i], ticks[i + 1]], 0, 1, color=state_colors.get(states[i], "#ccc"), alpha=0.7)
    ax.set_yticks([])
    ax.set_xlabel("Tick")
    ax.set_title("Operating State")
    # Legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=c, label=s) for s, c in state_colors.items()]
    ax.legend(handles=legend_elements, fontsize=7, ncol=4, loc="upper center")

    plt.tight_layout()
    png_path = out_dir / "simulation_dashboard.png"
    plt.savefig(png_path, dpi=140)
    print(f"\nSaved: {png_path}")

    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
