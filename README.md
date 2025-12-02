# paycheckbot

Lightweight PSD text replacer powered by psd-tools + Pillow.

- Replaces text for specific PSD layers and exports PNG.
- No Photoshop dependency.

## Quick start
1. Place `assets/template.psd` and a font file `assets/Arial.ttf`.
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python bot.py`

## Config
- Edit `replacements` in `bot.py` or wire input parsing.
- Use `src/utils.py` for date/sum/name helpers.
