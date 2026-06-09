from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_TARGETS = [
    Path("data/processed/indicators"),
    Path(".cache/yfinance"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove local generated market data after R2 upload.")
    parser.add_argument(
        "--include-scores",
        action="store_true",
        help="Also remove data/processed/index_scores.csv and universe.csv.",
    )
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help="Also remove data/raw. This disables incremental updates until a full download is run again.",
    )
    args = parser.parse_args()

    targets = list(DEFAULT_TARGETS)
    if args.include_raw:
        targets.append(Path("data/raw"))
    if args.include_scores:
        targets.extend(
            [
                Path("data/processed/index_scores.csv"),
                Path("data/processed/universe.csv"),
            ]
        )

    removed = 0
    for target in targets:
        removed += remove_path_contents(target)

    print(f"removed {removed} local generated files")


def remove_path_contents(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        path.unlink()
        return 1

    removed = 0
    for child in path.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            removed += remove_path_contents(child)
            child.rmdir()
        else:
            child.unlink()
            removed += 1
    return removed


if __name__ == "__main__":
    main()
