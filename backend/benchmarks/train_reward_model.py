from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from ..database import close_mongo_connection, connect_to_mongo
from ..reward_training import train_reward_model_from_mongo


async def _run(output_path: Path, limit: int) -> None:
    await connect_to_mongo()
    try:
        result = await train_reward_model_from_mongo(limit=limit, output_path=output_path)
        print(f"Wrote reward weights to {result['saved_to']}")
        print(result["weights"])
        print(f"Trained with {result['trained_samples']} samples")
    finally:
        await close_mongo_connection()


def main() -> None:
    parser = argparse.ArgumentParser(description="Train reward-model weights from feedback + QA metadata")
    parser.add_argument(
        "--output",
        default="backend/benchmarks/reward_weights.json",
        help="Where to save learned weight JSON",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Maximum chat samples to include",
    )
    args = parser.parse_args()
    asyncio.run(_run(output_path=Path(args.output).resolve(), limit=max(50, int(args.limit))))


if __name__ == "__main__":
    main()

