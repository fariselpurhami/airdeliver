"""CPU-only candidate training. Run from backend/api: python -m scripts.train_behavior --help."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from app.services.ai_behavior_engine import OmniNetConfig
from app.services.behavior_training import train_behavior_candidate


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Train an offline behavior candidate. Never activates or approves serving.')
    parser.add_argument('--dataset', required=True, type=Path, help='Local validated interaction JSONL, not a URL')
    parser.add_argument('--config', required=True, type=Path, help='Explicit OmniNetConfig JSON; no large implicit architecture')
    parser.add_argument('--output', required=True, type=Path, help='New local candidate checkpoint path')
    parser.add_argument('--model-version', required=True)
    parser.add_argument('--warm-start', type=Path)
    parser.add_argument('--epochs', type=int, default=3)
    parser.add_argument('--batch-size', type=int, default=8)
    parser.add_argument('--context-length', type=int, default=16)
    parser.add_argument('--learning-rate', type=float, default=3e-4)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--threads', type=int, default=1)
    args = parser.parse_args(argv)
    if not 1 <= args.threads <= 16:
        parser.error('--threads must be between 1 and 16')
    if args.output.exists() or Path(str(args.output)+'.metrics.json').exists():
        parser.error('Output exists. Choose a new versioned candidate path; serving artifacts must not be overwritten.')
    if args.config.stat().st_size > 65536:
        parser.error('Config exceeds 64KiB')
    config = OmniNetConfig.model_validate_json(args.config.read_text(encoding='utf-8'))
    torch.set_num_threads(args.threads)
    report = train_behavior_candidate(
        args.dataset, args.output, config, model_version=args.model_version,
        epochs=args.epochs, batch_size=args.batch_size, context_length=args.context_length,
        seed=args.seed, learning_rate=args.learning_rate, warm_start=args.warm_start,
    )
    # Output contains aggregate evaluation only, never events, subject IDs or vectors.
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
