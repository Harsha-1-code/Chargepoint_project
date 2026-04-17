"""
charging_physics.py — CC-CV Charging Curve Simulator

Models the real-world EV charging behavior:
  - Constant Current (CC) phase: flat power delivery up to ~80% SoC
  - Constant Voltage (CV) phase: exponential taper from 80% → 100%
  - Temperature derating: reduced efficiency in extreme heat/cold
  - Idle tail: random delay after reaching 100% (driver behavior)
"""

import numpy as np
from typing import Tuple, Dict


# ─────────────────────────── Physical Constants ───────────────────────────

TAPER_START_SOC = 0.80          # SoC at which CC→CV transition begins
TAPER_EXPONENT = 2.5            # Controls how aggressively power tapers
OPTIMAL_TEMP_LOW = 20.0         # °C — lower bound of optimal range
OPTIMAL_TEMP_HIGH = 35.0        # °C — upper bound of optimal range
TEMP_DERATE_FACTOR = 0.012      # 1.2% efficiency loss per °C outside optimal
CHARGER_EFFICIENCY = 0.92       # AC→DC conversion losses
MIN_CHARGE_POWER_FRACTION = 0.05  # Minimum power as fraction of max (trickle)


def temperature_derate(temp_c: float) -> float:
    """
    Calculate temperature derating factor.
    
    Returns a multiplier in (0, 1] that reduces effective charging power
    when temperature is outside the optimal 20-35°C window.
    
    Cold batteries have higher internal resistance → slower ion diffusion.
    Hot batteries trigger thermal throttling in the BMS.
    """
    if OPTIMAL_TEMP_LOW <= temp_c <= OPTIMAL_TEMP_HIGH:
        return 1.0

    if temp_c < OPTIMAL_TEMP_LOW:
        deviation = OPTIMAL_TEMP_LOW - temp_c
        # Cold penalty is harsher — exponential below 0°C
        if temp_c < 0:
            return max(0.3, 1.0 - TEMP_DERATE_FACTOR * deviation * 1.5)
        return max(0.5, 1.0 - TEMP_DERATE_FACTOR * deviation)
    else:
        deviation = temp_c - OPTIMAL_TEMP_HIGH
        return max(0.6, 1.0 - TEMP_DERATE_FACTOR * deviation)


def effective_power_kw(
    soc: float,
    charger_max_kw: float,
    temp_c: float
) -> float:
    """
    Calculate instantaneous charging power at a given SoC.
    
    Below TAPER_START_SOC (80%): full power (CC phase).
    Above TAPER_START_SOC: power tapers exponentially (CV phase).
    
    The taper models the BMS reducing current to protect cell voltage
    as individual cells approach their max voltage (typically 4.2V).
    """
    temp_factor = temperature_derate(temp_c)
    base_power = charger_max_kw * CHARGER_EFFICIENCY * temp_factor

    if soc <= TAPER_START_SOC:
        return base_power

    # Exponential taper: power drops from 100% to ~5% between 80-100% SoC
    taper_progress = (soc - TAPER_START_SOC) / (1.0 - TAPER_START_SOC)
    taper_multiplier = max(
        MIN_CHARGE_POWER_FRACTION,
        (1.0 - taper_progress) ** TAPER_EXPONENT
    )
    return base_power * taper_multiplier


def simulate_charging_session(
    soc_start: float,
    charger_max_kw: float,
    battery_capacity_kwh: float,
    temp_c: float,
    target_soc: float = 1.0,
    time_step_minutes: float = 0.5,
    include_idle: bool = True,
    rng: np.random.Generator = None
) -> Dict[str, float]:
    """
    Simulate a complete charging session from soc_start to target_soc.
    
    Uses numerical integration with small time steps to accurately model
    the CC-CV charging curve.
    
    Parameters
    ----------
    soc_start : float
        Starting state of charge as fraction (0.0 – 1.0)
    charger_max_kw : float
        Maximum charger output in kW
    battery_capacity_kwh : float
        Total battery capacity in kWh
    temp_c : float
        Ambient temperature in Celsius
    target_soc : float
        Target SoC to charge to (default 1.0 = 100%)
    time_step_minutes : float
        Simulation granularity in minutes
    include_idle : bool
        Whether to add random idle time after charging
    rng : np.random.Generator
        Random number generator for reproducibility
        
    Returns
    -------
    dict with keys:
        - charging_duration_minutes: time to reach target SoC
        - idle_duration_minutes: time car sits after reaching target
        - total_duration_minutes: charging + idle
        - energy_delivered_kwh: total energy added
        - avg_power_kw: average charging power
        - final_soc: actual final SoC reached
    """
    if rng is None:
        rng = np.random.default_rng()

    current_soc = soc_start
    elapsed_minutes = 0.0
    energy_delivered = 0.0
    time_step_hours = time_step_minutes / 60.0

    # Numerical integration of the charging curve
    while current_soc < target_soc:
        power = effective_power_kw(current_soc, charger_max_kw, temp_c)
        energy_step = power * time_step_hours  # kWh delivered this step
        soc_increment = energy_step / battery_capacity_kwh

        current_soc = min(target_soc, current_soc + soc_increment)
        energy_delivered += energy_step
        elapsed_minutes += time_step_minutes

        # Safety: prevent infinite loops for edge cases
        if elapsed_minutes > 1440:  # 24 hours max
            break

    charging_duration = elapsed_minutes

    # Idle time: log-normal distribution models the long-tail behavior
    # Most people unplug within 10-15 min, but some leave cars for hours
    idle_duration = 0.0
    if include_idle:
        idle_duration = float(rng.lognormal(mean=2.0, sigma=0.8))
        idle_duration = min(idle_duration, 180.0)  # Cap at 3 hours

    avg_power = (energy_delivered / (charging_duration / 60.0)
                 if charging_duration > 0 else 0.0)

    return {
        "charging_duration_minutes": round(charging_duration, 2),
        "idle_duration_minutes": round(idle_duration, 2),
        "total_duration_minutes": round(charging_duration + idle_duration, 2),
        "energy_delivered_kwh": round(energy_delivered, 2),
        "avg_power_kw": round(avg_power, 2),
        "final_soc": round(current_soc, 4),
    }


# ─────────────────────────── Quick Self-Test ──────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("CC-CV Charging Simulator — Self-Test")
    print("=" * 60)

    test_cases = [
        {"soc_start": 0.20, "charger_max_kw": 50,  "battery_capacity_kwh": 75, "temp_c": 22},
        {"soc_start": 0.20, "charger_max_kw": 150, "battery_capacity_kwh": 75, "temp_c": 22},
        {"soc_start": 0.80, "charger_max_kw": 150, "battery_capacity_kwh": 75, "temp_c": 22},
        {"soc_start": 0.50, "charger_max_kw": 150, "battery_capacity_kwh": 75, "temp_c": -5},
        {"soc_start": 0.50, "charger_max_kw": 7,   "battery_capacity_kwh": 60, "temp_c": 25},
    ]

    rng = np.random.default_rng(42)
    for i, tc in enumerate(test_cases, 1):
        result = simulate_charging_session(**tc, rng=rng)
        print(f"\nTest {i}: SoC={tc['soc_start']*100:.0f}% → 100% | "
              f"{tc['charger_max_kw']}kW | {tc['battery_capacity_kwh']}kWh | "
              f"{tc['temp_c']}°C")
        print(f"  Charging: {result['charging_duration_minutes']:.1f} min | "
              f"Idle: {result['idle_duration_minutes']:.1f} min | "
              f"Total: {result['total_duration_minutes']:.1f} min | "
              f"Energy: {result['energy_delivered_kwh']:.1f} kWh")
