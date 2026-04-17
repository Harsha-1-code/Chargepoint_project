"""
model.py — ChargingETANet: Physics-Informed Neural Network

A feed-forward regression network that predicts time-to-disconnect (minutes)
from 4 raw charging parameters. The key innovation is physics-informed
feature engineering inside the forward pass:

  Raw Inputs (4):
    1. current_soc (%)
    2. charger_max_kw (kW)
    3. battery_capacity_kwh (kWh)
    4. ambient_temp_c (°C)

  Derived Features (3) — computed in forward():
    5. energy_remaining_kwh = (1 - soc/100) × battery_capacity
    6. effective_charge_rate = charger_kw × temp_efficiency_factor
    7. taper_indicator = max(0, (soc - 80) / 20)  → 0-1 ramp above 80%

  Architecture: 7 → 64 → 128 → 64 → 1
"""

import torch
import torch.nn as nn


class ChargingETANet(nn.Module):
    """
    Physics-informed neural network for EV charging ETA prediction.
    
    The model augments raw inputs with domain-specific derived features
    that encode known physical relationships, making it easier for the
    network to learn the CC-CV charging dynamics.
    """

    def __init__(self, dropout_rate: float = 0.2):
        super().__init__()

        # After feature engineering: 4 raw + 3 derived = 7 input features
        self.network = nn.Sequential(
            # Layer 1: 7 → 64
            nn.Linear(7, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),

            # Layer 2: 64 → 128  (wider layer to capture interactions)
            nn.Linear(64, 128),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.BatchNorm1d(128),

            # Layer 3: 128 → 64
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),

            # Output: 64 → 1  (time_to_disconnect in minutes)
            nn.Linear(64, 1),
        )

        # Initialize weights using Kaiming (He) initialization
        # Optimal for ReLU activation functions
        self._init_weights()

    def _init_weights(self):
        """Apply Kaiming initialization to linear layers."""
        for module in self.network:
            if isinstance(module, nn.Linear):
                nn.init.kaiming_normal_(module.weight, nonlinearity='relu')
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def _engineer_features(self, x: torch.Tensor) -> torch.Tensor:
        """
        Compute physics-informed derived features.
        
        Input tensor columns (after standardization is reversed internally):
          [0] current_soc (%)
          [1] charger_max_kw (kW)
          [2] battery_capacity_kwh (kWh)
          [3] ambient_temp_c (°C)
          
        NOTE: These derived features are computed from the RAW (pre-scaled)
        inputs. The caller must pass raw values; the full input (raw + derived)
        is then standardized by the external scaler in train.py / serve.py.
        """
        soc = x[:, 0:1]              # (batch, 1)
        charger_kw = x[:, 1:2]
        battery_kwh = x[:, 2:3]
        temp_c = x[:, 3:4]

        # Feature 5: Energy remaining to charge (kWh)
        # Direct proxy for "how much work is left"
        energy_remaining = (1.0 - soc / 100.0) * battery_kwh

        # Feature 6: Effective charge rate (kW)
        # Temperature-adjusted power delivery
        temp_factor = torch.clamp(
            1.0 - 0.012 * torch.abs(temp_c - 25.0),
            min=0.3, max=1.0
        )
        effective_rate = charger_kw * temp_factor

        # Feature 7: Taper indicator (0.0–1.0)
        # Encodes how deep into the CV taper phase we are
        # 0 at ≤80% SoC, ramps to 1.0 at 100% SoC
        taper_indicator = torch.clamp((soc - 80.0) / 20.0, min=0.0, max=1.0)

        # Concatenate: raw inputs + derived features
        return torch.cat([
            x,                    # original 4 features
            energy_remaining,     # feature 5
            effective_rate,       # feature 6
            taper_indicator,      # feature 7
        ], dim=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass with inline feature engineering.
        
        Parameters
        ----------
        x : torch.Tensor, shape (batch_size, 4)
            Raw input features (soc%, kW, kWh, °C)
            
        Returns
        -------
        torch.Tensor, shape (batch_size, 1)
            Predicted time to disconnect in minutes
        """
        x_engineered = self._engineer_features(x)  # (batch, 7)
        return self.network(x_engineered)           # (batch, 1)


class ChargingETANetLarge(nn.Module):
    """
    Larger variant for higher accuracy with sufficient data.
    
    Architecture: 7 → 128 → 256 → 128 → 64 → 1
    Use when dataset exceeds 100K samples.
    """

    def __init__(self, dropout_rate: float = 0.3):
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(7, 128),
            nn.LeakyReLU(0.1),
            nn.BatchNorm1d(128),

            nn.Linear(128, 256),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout_rate),
            nn.BatchNorm1d(256),

            nn.Linear(256, 128),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout_rate),
            nn.BatchNorm1d(128),

            nn.Linear(128, 64),
            nn.LeakyReLU(0.1),
            nn.BatchNorm1d(64),

            nn.Linear(64, 1),
        )

        for module in self.network:
            if isinstance(module, nn.Linear):
                nn.init.kaiming_normal_(module.weight, nonlinearity='leaky_relu')
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def _engineer_features(self, x: torch.Tensor) -> torch.Tensor:
        """Same physics-informed features as ChargingETANet."""
        soc = x[:, 0:1]
        charger_kw = x[:, 1:2]
        battery_kwh = x[:, 2:3]
        temp_c = x[:, 3:4]

        energy_remaining = (1.0 - soc / 100.0) * battery_kwh
        temp_factor = torch.clamp(
            1.0 - 0.012 * torch.abs(temp_c - 25.0), min=0.3, max=1.0
        )
        effective_rate = charger_kw * temp_factor
        taper_indicator = torch.clamp((soc - 80.0) / 20.0, min=0.0, max=1.0)

        return torch.cat([x, energy_remaining, effective_rate, taper_indicator], dim=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(self._engineer_features(x))


# ─────────────────────────── Model Summary ────────────────────────────────

if __name__ == "__main__":
    model = ChargingETANet()
    print("ChargingETANet Architecture:")
    print(model)
    
    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\nTotal parameters:     {total_params:,}")
    print(f"Trainable parameters: {trainable_params:,}")

    # Test forward pass
    dummy_input = torch.tensor([[
        45.0,    # soc %
        150.0,   # charger kW
        75.0,    # battery kWh
        22.0,    # temp °C
    ]])
    
    model.eval()
    with torch.no_grad():
        output = model(dummy_input)
        print(f"\nTest prediction: {output.item():.2f} minutes")
