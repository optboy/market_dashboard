from src.data.build_scores import build_index_scores


def main() -> None:
    scores = build_index_scores()
    print(f"saved data/processed/index_scores.csv ({len(scores)} rows)")


if __name__ == "__main__":
    main()
