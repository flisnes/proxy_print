# Proxy Print

A Python script to generate printable MTG proxy cards in PDF format.

## Requirements

- Python 3.x
- Required Python packages: `requests`, `Pillow`, `reportlab`

## Usage

1. Create a text file (e.g. `deck.txt`) containing your card list in the following format:

```
1 Black Lotus (2ED) 233
1 Ancestral Recall (2ED) 48
1 Time Walk (2ED) 84
1 Mox Sapphire (2ED) 266
1 Mox Jet (2ED) 263
1 Mox Pearl (2ED) 264
1 Mox Ruby (2ED) 265
1 Mox Emerald (2ED) 262
1 Sol Ring (SUM) 274
```

Each line should follow the format: `{quantity} {card name} ({set code}) {collector number}`

2. Run the script:

```bash
python proxy-print.py deck.txt