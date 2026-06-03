# storm-surge-border

Stage-1 implementation has started.

## Setup

```bash
pip install -r requirements.txt
```

## Run (Stage-1 skeleton)

```bash
python -m storm_surge_border \
	--video-a path/to/duo_a.mp4 \
	--video-b path/to/duo_b.mp4 \
	--offset-sec 0.0 \
	--sample-interval 0.1 \
	--out-csv outputs/estimated_border.csv \
	--out-review-csv outputs/review_candidates.csv \
	--corrections-csv outputs/review_candidates.csv \
	--out-png outputs/estimated_border.png
```

Current Stage-1 status:
- Aligns two videos by manual offset and builds a 0.1s timeline.
- Uses central-bottom HP ROI, central reticle ROI, top-right surge ROI definitions.
- Estimates received damage from central-bottom HP bar changes on both videos.
- Reflects cumulative received damage as `duo_damage_diff` (current stage: dealt damage is not included yet).
- Writes estimate CSV, review CSV for manual shaping, and border PNG.
- Reads surge gap and side (above/below) from top-right OCR with carry-forward between OCR intervals.

## Tests

```bash
pytest -q
```