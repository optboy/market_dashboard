from src.data.index_config import load_indices


def test_load_indices_includes_expected_providers() -> None:
    indices = load_indices()
    providers = {index["data_provider"] for index in indices}

    assert providers == {"pykrx", "yfinance"}
    assert {index["id"] for index in indices} == {
        "kospi",
        "kosdaq",
        "sp500",
        "nasdaq",
        "dow",
        "wti_oil",
        "us10y",
    }
