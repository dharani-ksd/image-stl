# image-stl

Convert any image into a 3-D printable **STL heightmap relief**.

Bright pixels become raised areas; dark pixels become recessed areas (or vice-versa with `--invert`).

## Requirements

Python 3.8+ and the packages listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Usage

```
python image_to_stl.py [INPUT_IMAGE] [OUTPUT_STL] [OPTIONS]
```

| Argument / Option | Default | Description |
|---|---|---|
| `INPUT_IMAGE` | `DSC_2695.jpg` | Path to the input image |
| `OUTPUT_STL` | `<input_stem>.stl` | Path for the output STL file |
| `--max-size N` | `300` | Downsample so the longest edge is at most N pixels |
| `--xy-scale F` | `0.5` | Millimetres per pixel in X and Y |
| `--z-scale F` | `10.0` | Maximum relief height in millimetres |
| `--base-height F` | `1.0` | Flat base height in millimetres |
| `--invert` | off | Invert the heightmap — dark pixels become raised |

### Examples

Convert with default settings:
```bash
python image_to_stl.py photo.jpg
```

Convert with a larger relief and thicker base:
```bash
python image_to_stl.py photo.jpg photo.stl --z-scale 15 --base-height 2
```

Create a **lithophane** (dark pixels raised, back-lit display):
```bash
python image_to_stl.py photo.jpg lithophane.stl --invert --z-scale 3 --base-height 0.5
```

Convert at higher resolution:
```bash
python image_to_stl.py photo.jpg photo.stl --max-size 500 --xy-scale 0.3
```

## How it works

1. The image is converted to **grayscale** and downsampled to at most `--max-size` pixels on the longest edge.
2. Each pixel's brightness (0–255) is mapped to a height value between `--base-height` and `--base-height + --z-scale` millimetres.
3. A **watertight mesh** is built from:
   - Top surface (two triangles per pixel quad)
   - Four side walls
   - Flat bottom face
4. The mesh is saved as a binary STL file ready for slicing and 3-D printing.

## Sample output

The included `DSC_2695.jpg` → `DSC_2695.stl` was generated with default settings:
```
Object size: 149.5 × 99.0 × 11.0 mm  (300×199 px, 118,404 top triangles)
```
