"""
train.py — Training Pipeline for ChargingETANet

Full training pipeline with:
  - Data loading and 80/20 train/validation split
  - Feature standardization (saved for inference)
  - Adam optimizer with ReduceLROnPlateau scheduler
  - Early stopping with patience of 10 epochs
  - Model checkpointing (saves best model by validation loss)
  - Training curve visualization
"""

import os
import sys
import time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib

from model import ChargingETANet

# ──────────────────────── Configuration ────────────────────────

class TrainConfig:
    """Training hyperparameters — tweak these to experiment."""
    DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "training_data.csv")
    MODEL_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
    MODEL_PATH = os.path.join(MODEL_DIR, "charging_eta_model.pth")
    SCALER_PATH = os.path.join(MODEL_DIR, "feature_scaler.joblib")

    # Features and target
    FEATURE_COLS = [
        "current_soc",
        "charger_max_kw",
        "battery_capacity_kwh",
        "ambient_temp_c",
    ]
    TARGET_COL = "time_to_disconnect_minutes"

    # Training
    BATCH_SIZE = 256
    LEARNING_RATE = 1e-3
    WEIGHT_DECAY = 1e-5
    EPOCHS = 100
    VALIDATION_SPLIT = 0.20
    RANDOM_SEED = 42

    # Early stopping
    PATIENCE = 10
    MIN_DELTA = 0.01  # Minimum improvement to count as progress

    # Scheduler
    LR_PATIENCE = 5
    LR_FACTOR = 0.5
    MIN_LR = 1e-6

    # Device
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def load_and_prepare_data(config: TrainConfig):
    """
    Load CSV, split into train/val, standardize features.
    
    Returns train/val DataLoaders and the fitted scaler.
    """
    print(f"Loading data from: {config.DATA_PATH}")
    df = pd.read_csv(config.DATA_PATH)
    print(f"  Loaded {len(df):,} samples")

    X = df[config.FEATURE_COLS].values.astype(np.float32)
    y = df[config.TARGET_COL].values.astype(np.float32).reshape(-1, 1)

    # Train/validation split
    X_train, X_val, y_train, y_val = train_test_split(
        X, y,
        test_size=config.VALIDATION_SPLIT,
        random_state=config.RANDOM_SEED,
    )
    print(f"  Train: {len(X_train):,}  |  Val: {len(X_val):,}")

    # Note: We do NOT standardize here because the model's _engineer_features()
    # needs raw values. Instead, we store the scaler for the DERIVED features.
    # The feature engineering happens inside the model, and we scale the
    # 7-feature output in the serve.py inference path.
    #
    # For training, we pass raw features directly and let the model's
    # BatchNorm layers handle normalization.

    # However, we DO fit a scaler on raw features for the inference API
    # to validate input ranges
    scaler = StandardScaler()
    scaler.fit(X_train)

    # Save scaler
    os.makedirs(config.MODEL_DIR, exist_ok=True)
    joblib.dump(scaler, config.SCALER_PATH)
    print(f"  Feature scaler saved to: {config.SCALER_PATH}")

    # Create DataLoaders
    train_dataset = TensorDataset(
        torch.tensor(X_train, dtype=torch.float32),
        torch.tensor(y_train, dtype=torch.float32),
    )
    val_dataset = TensorDataset(
        torch.tensor(X_val, dtype=torch.float32),
        torch.tensor(y_val, dtype=torch.float32),
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=config.BATCH_SIZE,
        shuffle=True,
        num_workers=0,
        pin_memory=(config.DEVICE == "cuda"),
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=config.BATCH_SIZE * 2,  # Larger batch for validation (no grads)
        shuffle=False,
        num_workers=0,
        pin_memory=(config.DEVICE == "cuda"),
    )

    return train_loader, val_loader, scaler


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: str,
) -> float:
    """Train for one epoch, return average loss."""
    model.train()
    total_loss = 0.0
    num_batches = 0

    for X_batch, y_batch in loader:
        X_batch = X_batch.to(device)
        y_batch = y_batch.to(device)

        optimizer.zero_grad()
        predictions = model(X_batch)
        loss = criterion(predictions, y_batch)
        loss.backward()

        # Gradient clipping to prevent exploding gradients
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

        optimizer.step()

        total_loss += loss.item()
        num_batches += 1

    return total_loss / num_batches


@torch.no_grad()
def validate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: str,
) -> tuple:
    """Validate and return (avg_loss, MAE_minutes)."""
    model.eval()
    total_loss = 0.0
    total_mae = 0.0
    num_samples = 0

    for X_batch, y_batch in loader:
        X_batch = X_batch.to(device)
        y_batch = y_batch.to(device)

        predictions = model(X_batch)
        loss = criterion(predictions, y_batch)

        total_loss += loss.item() * len(X_batch)
        total_mae += torch.abs(predictions - y_batch).sum().item()
        num_samples += len(X_batch)

    avg_loss = total_loss / num_samples
    avg_mae = total_mae / num_samples
    return avg_loss, avg_mae


def train(config: TrainConfig = None):
    """
    Full training loop with early stopping and checkpointing.
    """
    if config is None:
        config = TrainConfig()

    print("=" * 65)
    print("  Project Antigravity — ChargingETANet Training")
    print("=" * 65)
    print(f"  Device:      {config.DEVICE}")
    print(f"  Epochs:      {config.EPOCHS}")
    print(f"  Batch size:  {config.BATCH_SIZE}")
    print(f"  LR:          {config.LEARNING_RATE}")
    print(f"  Patience:    {config.PATIENCE}")
    print("=" * 65)

    # Load data
    train_loader, val_loader, scaler = load_and_prepare_data(config)

    # Initialize model
    model = ChargingETANet(dropout_rate=0.2).to(config.DEVICE)
    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\n  Model parameters: {total_params:,}")

    # Loss, optimizer, scheduler
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config.LEARNING_RATE,
        weight_decay=config.WEIGHT_DECAY,
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=config.LR_FACTOR,
        patience=config.LR_PATIENCE,
        min_lr=config.MIN_LR,
    )

    # Training loop
    best_val_loss = float("inf")
    epochs_without_improvement = 0
    history = {"train_loss": [], "val_loss": [], "val_mae": [], "lr": []}

    print(f"\n{'Epoch':>6} | {'Train Loss':>12} | {'Val Loss':>12} | "
          f"{'Val MAE (min)':>14} | {'LR':>10} | {'Status':>10}")
    print("-" * 80)

    start_time = time.time()

    for epoch in range(1, config.EPOCHS + 1):
        # Train
        train_loss = train_one_epoch(
            model, train_loader, criterion, optimizer, config.DEVICE
        )

        # Validate
        val_loss, val_mae = validate(
            model, val_loader, criterion, config.DEVICE
        )

        # LR scheduling
        current_lr = optimizer.param_groups[0]["lr"]
        scheduler.step(val_loss)

        # Record history
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_mae"].append(val_mae)
        history["lr"].append(current_lr)

        # Check for improvement
        status = ""
        if val_loss < best_val_loss - config.MIN_DELTA:
            best_val_loss = val_loss
            epochs_without_improvement = 0
            status = "* BEST"

            # Save best model
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": val_loss,
                "val_mae": val_mae,
            }, config.MODEL_PATH)
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= config.PATIENCE // 2:
                status = f"! {epochs_without_improvement}/{config.PATIENCE}"

        print(f"{epoch:>6} | {train_loss:>12.4f} | {val_loss:>12.4f} | "
              f"{val_mae:>14.2f} | {current_lr:>10.1e} | {status:>10}")

        # Early stopping
        if epochs_without_improvement >= config.PATIENCE:
            print(f"\nEarly stopping at epoch {epoch} — "
                  f"no improvement for {config.PATIENCE} epochs.")
            break

    elapsed = time.time() - start_time

    # Load best model for final evaluation
    checkpoint = torch.load(config.MODEL_PATH, map_location=config.DEVICE,
                            weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])
    _, final_mae = validate(model, val_loader, criterion, config.DEVICE)

    print(f"\n{'=' * 65}")
    print(f"  Training Complete!")
    print(f"  Time:            {elapsed:.1f}s")
    print(f"  Best epoch:      {checkpoint['epoch']}")
    print(f"  Best val loss:   {checkpoint['val_loss']:.4f}")
    print(f"  Final val MAE:   {final_mae:.2f} minutes")
    print(f"  Model saved to:  {config.MODEL_PATH}")
    print(f"  Scaler saved to: {config.SCALER_PATH}")
    print(f"{'=' * 65}")

    # Save training history
    history_df = pd.DataFrame(history)
    history_path = os.path.join(config.MODEL_DIR, "training_history.csv")
    history_df.to_csv(history_path, index_label="epoch")
    print(f"  History saved to: {history_path}")

    # Plot training curves if matplotlib is available
    try:
        plot_training_curves(history, config.MODEL_DIR)
    except Exception as e:
        print(f"  (Skipped plotting: {e})")

    return model, history


def plot_training_curves(history: dict, output_dir: str):
    """Generate and save training curve plots."""
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    epochs = range(1, len(history["train_loss"]) + 1)

    # Loss curves
    axes[0].plot(epochs, history["train_loss"], label="Train", color="#6366f1")
    axes[0].plot(epochs, history["val_loss"], label="Val", color="#f43f5e")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("MSE Loss")
    axes[0].set_title("Training & Validation Loss")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # MAE curve
    axes[1].plot(epochs, history["val_mae"], color="#10b981")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("MAE (minutes)")
    axes[1].set_title("Validation MAE")
    axes[1].grid(True, alpha=0.3)

    # Learning rate
    axes[2].plot(epochs, history["lr"], color="#f59e0b")
    axes[2].set_xlabel("Epoch")
    axes[2].set_ylabel("Learning Rate")
    axes[2].set_title("Learning Rate Schedule")
    axes[2].set_yscale("log")
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plot_path = os.path.join(output_dir, "training_curves.png")
    plt.savefig(plot_path, dpi=150)
    plt.close()
    print(f"  Training curves saved to: {plot_path}")


if __name__ == "__main__":
    # Allow quick smoke test with fewer epochs
    config = TrainConfig()
    if "--quick" in sys.argv:
        config.EPOCHS = 10
        config.PATIENCE = 5
        print("[QUICK MODE: 10 epochs]")

    train(config)
