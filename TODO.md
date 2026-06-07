# TODO

## Phase 1: Skeleton

- [x] Initialize Git repository.
- [x] Create basic folder structure.
- [x] Add README and project plan.
- [x] Add Streamlit app skeleton.
- [x] Add placeholder modules for data, indicators, scoring, and analysis.

## Phase 2: Index Data

- [x] Choose data providers for Korean and US indices.
- [x] Implement daily OHLCV download.
- [x] Save raw index data under `data/raw/`.
- [ ] Add update timestamp handling.

## Phase 3: Indicators

- [x] Calculate moving averages: 20, 60, 120 days.
- [x] Calculate RSI 14.
- [x] Calculate MACD and signal line.
- [x] Calculate Bollinger Bands.
- [x] Calculate 20-day average volume.
- [x] Save indicator data under `data/processed/indicators/`.

## Phase 4: Rule-Based Scoring

- [x] Define positive signal weights.
- [x] Define negative signal weights.
- [x] Generate bullish score and bearish score.
- [x] Generate concise reasons for each score.
- [x] Save processed output under `data/processed/`.
- [x] Show scoring configuration for transparency.

## Phase 5: Streamlit UI

- [x] Show index score table.
- [x] Add market/index filters.
- [ ] Add detail view per index.
- [x] Add initial detail view per index.
- [ ] Add basic charts.
- [x] Add update status.

## Phase 6: Private Deployment

- [ ] Add lightweight authentication.
- [ ] Decide MacBook hosting method.
- [ ] Configure daily update job.
- [ ] Configure limited external access.

## Phase 7: GPT Explanation Layer

- [ ] Define GPT prompt inputs from rule-based scoring output.
- [ ] Generate technical-analysis explanations.
- [ ] Add guardrails to avoid direct financial advice language.
- [ ] Cache GPT explanations to control cost.
