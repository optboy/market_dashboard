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

- [ ] Calculate moving averages: 20, 60, 120 days.
- [ ] Calculate RSI 14.
- [ ] Calculate MACD and signal line.
- [ ] Calculate Bollinger Bands.
- [ ] Calculate 20-day average volume.

## Phase 4: Rule-Based Scoring

- [ ] Define positive signal weights.
- [ ] Define negative signal weights.
- [ ] Generate buy score and sell score.
- [ ] Generate concise reasons for each score.
- [ ] Save processed output under `data/processed/`.

## Phase 5: Streamlit UI

- [ ] Show index score table.
- [ ] Add market/index filters.
- [ ] Add detail view per index.
- [ ] Add basic charts.
- [ ] Add update status.

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
