"""
Victim Loader — Simulates a data scientist loading a dataset.

This is the "trigger" file that runs on the victim machine.
It loads the malicious pickle, triggering the attack chain.

Usage on victim:
    python3 loader.py
    python3 loader.py --dataset /tmp/imagenet_labels.pkl
    python3 loader.py --vector yaml --dataset /tmp/dataset_config.yaml
"""

import argparse
import os
import pickle
import sys


def load_pickle(path: str):
    """Load a pickle dataset — triggers RCE if malicious."""
    print(f"[DataLoader] Loading dataset: {path}")
    print("[DataLoader] Format: pickle (imagenet labels)")

    with open(path, "rb") as f:
        data = pickle.load(f)  # RCE HERE if malicious

    print(f"[DataLoader] Dataset loaded: {type(data)}")
    return data


def load_yaml(path: str):
    """Load a YAML dataset config — triggers RCE via unsafe_load."""
    try:
        import yaml
    except ImportError:
        print("[DataLoader] PyYAML not installed. Run: pip install pyyaml")
        sys.exit(1)

    print(f"[DataLoader] Loading dataset config: {path}")
    print("[DataLoader] Format: YAML configuration")

    with open(path) as f:
        config = yaml.unsafe_load(f)  # RCE HERE if malicious

    print(f"[DataLoader] Config loaded: {type(config)}")
    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Dataset loader — simulates ML pipeline data ingestion"
    )
    parser.add_argument(
        "--dataset",
        default="/tmp/imagenet_labels.pkl",
        help="Path to dataset file"
    )
    parser.add_argument(
        "--vector",
        choices=["pickle", "yaml"],
        default="pickle",
        help="Dataset format"
    )
    args = parser.parse_args()

    if not os.path.exists(args.dataset):
        print(f"[DataLoader] ERROR: Dataset not found: {args.dataset}")
        print("[DataLoader] Generate it with:")
        print("  python -m attacker.techniques.dataset_poison --output /tmp/imagenet_labels.pkl")
        sys.exit(1)

    try:
        if args.vector == "pickle":
            load_pickle(args.dataset)
        else:
            load_yaml(args.dataset)
    except Exception as e:
        # Expected — the payload launches a subprocess and may not return a valid object
        print(f"[DataLoader] Exception during load: {e}")
        print("[DataLoader] (This may be expected if payload launched subprocess)")
