# Steaming ramen — best-looking food picture

Entry for the [make.fun](https://make.fun) bounty `food-picture-01`:
make the best-looking food picture.

## The picture

A bowl of tonkotsu-style ramen, drawn from scratch in code: amber broth in
a dark ceramic bowl, wavy noodles (some lifted by chopsticks), a soft egg,
two slices of chashu, narutomaki, green onions, chilli oil and sesame,
with steam rising over a warm wooden table — and two dried chillies on the
side. Clean vector-style illustration, no text, reads clearly at 300 px.

## Run

```sh
python3 main.py   # writes $MAKEFUN_OUTPUT_DIR/entry.png (default /output)
```

Python 3.13, standard library only (zlib for PNG compression), deterministic
(two runs are byte-identical), no network. Output: one PNG, 1024×1024,
~190 KB (limit 1 MiB).

## How it is drawn

`main.py` has a small scanline rasteriser (spans, discs, ellipses, rings,
wavy strands, soft-edged discs for steam and shading) and a hand-written
PNG encoder (filter 0 + zlib level 9), then draws the scene: table gradient
and plank lines, bowl body tapered from rim to foot, broth with radial
gradient and gloss, toppings, chopsticks with a lifted noodle clump, and
soft steam columns.
