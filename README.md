# Market Dashboard

Streamlit dashboard for reviewing technical-analysis signals across major market indices.

## MVP Scope

The first version intentionally starts with indices instead of all individual stocks.

- KOSPI
- KOSDAQ
- S&P 500
- Nasdaq
- Dow Jones Industrial Average

Data will be updated once per day. The Streamlit app should read precomputed results from local files instead of calling external market-data APIs on every page load.

## Data Providers

- Korean indices: `pykrx`
- US indices: `yfinance`

## Scoring Approach

The first scoring engine is rule based:

1. Load daily OHLCV data.
2. Calculate common technical indicators.
3. Evaluate positive and negative signals.
4. Produce buy score, sell score, and human-readable reasons.
5. Save the result for the Streamlit app.

GPT API integration is planned later as an explanation layer. It should summarize and interpret rule-based results, not directly decide buy/sell scores.

## Planned Deployment

Initial deployment is for the owner and a small group of trusted users on a MacBook.

Likely stack:

- Streamlit
- Local CSV/Parquet files initially
- Simple authentication for private access
- Daily update script
- Cloudflare Tunnel or Tailscale for limited external access

## Project Structure

```text
config/              Market/index configuration
data/raw/            Downloaded OHLCV data
data/processed/      Precomputed dashboard outputs
src/data/            Data loading and saving
src/indicators/      Technical indicators
src/scoring/         Rule-based scoring
src/analysis/        Future GPT explanation layer
src/auth/            Authentication helpers
tests/               Tests
app.py               Streamlit entry point
```

## Current Status

Project skeleton and first-pass data downloader modules are in place. Production scoring rules and UI details are not implemented yet.

## Commands

Run tests:

```bash
python -m pytest
```

Download daily index data:

```bash
conda activate market_dashboard
MPLCONFIGDIR=.cache/matplotlib python -m scripts.update_indices
```

Download index and stock universe data:

```bash
MPLCONFIGDIR=.cache/matplotlib python -m scripts.update_assets
```

Build technical indicators and score data:

```bash
python -m scripts.build_index_scores
```

Run the Streamlit app:

```bash
streamlit run streamlit_app.py
```

Upload processed data to Cloudflare R2:

```bash
export R2_ENDPOINT_URL="https://<account-id>.r2.cloudflarestorage.com"
export R2_ACCESS_KEY_ID="..."
export R2_SECRET_ACCESS_KEY="..."
export R2_BUCKET_NAME="..."
python -m scripts.upload_processed_to_r2
```

Streamlit reads from R2 when those environment variables are configured. If they are not configured, it falls back to local files under `data/processed/`.
