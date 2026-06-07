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
	--surge-source-video a \
	--ocr-min-confidence-for-border 0.4 \
	--out-csv outputs/estimated_border.csv \
	--out-review-csv outputs/review_candidates.csv \
	--corrections-csv outputs/review_candidates.csv \
	--out-png outputs/estimated_border.png
```

`--out-review-csv` is the review-target CSV generated from rows where confidence falls below `--confidence-threshold` or any required field (`duo_damage_diff`, `surge_gap_value`, `is_above_border`, `estimated_border`) is missing. `--corrections-csv` is the file a reviewer edits and feeds back into the pipeline. During the roundtrip workflow, both can point to the same path.

If `easyocr` is not installed and you still want to run HP-only flow, use:

```bash
python -m storm_surge_border ... --allow-missing-easyocr
```

Current Stage-1 status:
- Aligns two videos by manual offset and builds a 0.1s timeline.
- Uses central-bottom HP ROI, central reticle ROI, top-right surge ROI definitions.
- Estimates received damage from central-bottom HP bar changes on both videos.
- Reflects cumulative received damage as `duo_damage_diff` (current stage: dealt damage is not included yet).
- Writes estimate CSV, review CSV for manual shaping, and border PNG.
- Supports review CSV roundtrip so manual corrections can be written back and reapplied.
- Reads surge gap and side (above/below) from top-right OCR with carry-forward between OCR intervals.
- Skips `estimated_border` computation when OCR confidence is below `--ocr-min-confidence-for-border`.
- Marks carry-based border rows with `border-provisional-carry` in `source_flags`.
- Adds `estimated_border_status` column to explain why border is computed/skipped.
- Emits `hp-provisional` when a short damage sequence ends before `--hp-confirm-frames`.

## Tests

```bash
pytest -q
```