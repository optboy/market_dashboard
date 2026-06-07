from src.data.update_indices import update_raw_index_data


def main() -> None:
    saved_paths = update_raw_index_data()
    for path in saved_paths:
        print(f"saved {path}")


if __name__ == "__main__":
    main()
