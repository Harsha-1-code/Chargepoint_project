"""
generate_dataset.py — Synthetic EV Charging Session Generator

Generates 50,000 charging sessions with realistic parameter distributions
using the CC-CV physics simulator. Output is saved to data/training_data.csv.

Parameter distributions are modeled to reflect real-world EV charging patterns:
  - SoC at plug-in: skewed toward 20-50% (people charge when low)
  - Charger types: weighted mix of L2 (7-19kW), DCFC (50-150kW), Ultra (250-350kW)
  - Battery sizes: clustered around common EV models (40, 60, 75, 82, 100, 120 kWh)
  - Temperature: normal distribution centered on regional climate
"""

import os
import numpy as np
import pandas as pd
from charging_physics import simulate_charging_session

# ──────────────────────── Configuration ────────────────────────

NUM_SESSIONS = 100
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "training_data.csv")
RANDOM_SEED = 42


def sample_charger_type(rng: np.random.Generator, n: int) -> np.ndarray:
    """
    Sample charger max kW with realistic type distribution.
    
    Distribution:
      - 40% Level 2 AC   (7 – 19 kW)
      - 35% DCFC          (50 – 150 kW)
      - 25% Ultra-fast     (200 – 350 kW)
    """
    charger_types = rng.choice(
        ["L2", "DCFC", "ULTRA"],
        size=n,
        p=[0.40, 0.35, 0.25]
    )

    kw_values = np.zeros(n)
    for i, ctype in enumerate(charger_types):
        if ctype == "L2":
            kw_values[i] = rng.uniform(7, 19)
        elif ctype == "DCFC":
            kw_values[i] = rng.uniform(50, 150)
        else:  # ULTRA
            kw_values[i] = rng.uniform(200, 350)

    return np.round(kw_values, 1)


def sample_battery_capacity(rng: np.random.Generator, n: int) -> np.ndarray:
    """
    Sample battery capacities clustered around common EV models.
    Adds ±5 kWh jitter to avoid exact discrete values.
    """
    base_capacities = [30, 40, 58, 62, 75, 77, 82, 100, 120]
    bases = rng.choice(base_capacities, size=n)
    jitter = rng.normal(0, 3, size=n)
    return np.clip(np.round(bases + jitter, 1), 25, 130)


def sample_starting_soc(rng: np.random.Generator, n: int) -> np.ndarray:
    """
    Sample starting SoC with beta distribution skewed toward lower values.
    Most people plug in between 15-50% SoC.
    """
    # Beta(2, 5) gives a right-skewed distribution peaking around 20-30%
    soc = rng.beta(2, 5, size=n)
    # Scale to 5-95% range
    soc = 0.05 + soc * 0.90
    return np.round(soc * 100, 1)  # Return as percentage


def sample_temperature(rng: np.random.Generator, n: int) -> np.ndarray:
    """
    Sample ambient temperature from a mixture of climate zones.
    """
    # Mixture of 3 climate zones
    zones = rng.choice(["cold", "temperate", "hot"], size=n, p=[0.2, 0.5, 0.3])

    temps = np.zeros(n)
    for i, zone in enumerate(zones):
        if zone == "cold":
            temps[i] = rng.normal(5, 8)
        elif zone == "temperate":
            temps[i] = rng.normal(20, 6)
        else:
            temps[i] = rng.normal(33, 5)

    return np.clip(np.round(temps, 1), -15, 48)


def generate_dataset():
    """Generate the full synthetic dataset."""
    print(f"Generating {NUM_SESSIONS:,} synthetic charging sessions...")
    rng = np.random.default_rng(RANDOM_SEED)

    # Sample all input parameters
    soc_values = sample_starting_soc(rng, NUM_SESSIONS)
    charger_values = sample_charger_type(rng, NUM_SESSIONS)
    battery_values = sample_battery_capacity(rng, NUM_SESSIONS)
    temp_values = sample_temperature(rng, NUM_SESSIONS)

    # Run simulations
    records = []
    for i in range(NUM_SESSIONS):
        if (i + 1) % 5000 == 0:
            print(f"  Progress: {i + 1:,} / {NUM_SESSIONS:,} "
                  f"({(i + 1) / NUM_SESSIONS * 100:.0f}%)")

        result = simulate_charging_session(
            soc_start=soc_values[i] / 100.0,  # Convert % to fraction
            charger_max_kw=charger_values[i],
            battery_capacity_kwh=battery_values[i],
            temp_c=temp_values[i],
            include_idle=True,
            rng=rng,
        )

        records.append({
            "current_soc": soc_values[i],
            "charger_max_kw": charger_values[i],
            "battery_capacity_kwh": battery_values[i],
            "ambient_temp_c": temp_values[i],
            "charging_duration_minutes": result["charging_duration_minutes"],
            "idle_duration_minutes": result["idle_duration_minutes"],
            "time_to_disconnect_minutes": result["total_duration_minutes"],
            "energy_delivered_kwh": result["energy_delivered_kwh"],
            "avg_power_kw": result["avg_power_kw"],
        })

    df = pd.DataFrame(records)

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    # Print dataset statistics
    print(f"\n{'=' * 60}")
    print(f"Dataset saved to: {OUTPUT_FILE}")
    print(f"Shape: {df.shape}")
    print(f"\n--- Feature Statistics ---")
    print(df.describe().round(2).to_string())
    print(f"\n--- Target Distribution ---")
    target = df["time_to_disconnect_minutes"]
    print(f"  Mean:   {target.mean():.1f} min")
    print(f"  Median: {target.median():.1f} min")
    print(f"  Std:    {target.std():.1f} min")
    print(f"  Min:    {target.min():.1f} min")
    print(f"  Max:    {target.max():.1f} min")

    return df


if __name__ == "__main__":
    generate_dataset()
