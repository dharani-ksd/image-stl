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

---

# food_organizer.py

Generate a parametric **food-organizer tray** STL for 3-D printing.

The tray is a rectangular open-top box divided into a configurable grid of
compartments by solid internal dividers.

## Usage

```
python food_organizer.py [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--output FILE` | `food_organizer.stl` | Output STL file path |
| `--width F` | `200` | Overall tray width (X) in mm |
| `--depth F` | `150` | Overall tray depth (Y) in mm |
| `--height F` | `50` | Overall tray height (Z) in mm |
| `--wall-thickness F` | `2.0` | Outer wall thickness in mm |
| `--bottom-thickness F` | `2.0` | Base plate thickness in mm |
| `--cols N` | `3` | Number of compartment columns |
| `--rows N` | `2` | Number of compartment rows |
| `--divider-thickness F` | `2.0` | Internal divider thickness in mm |

### Examples

Default 3 × 2 tray (200 × 150 × 50 mm):
```bash
python food_organizer.py
```

Large kitchen drawer organizer, 4 columns × 3 rows:
```bash
python food_organizer.py --width 300 --depth 200 --height 60 --cols 4 --rows 3 --output drawer.stl
```

Single-row spice rack, 6 compartments:
```bash
python food_organizer.py --width 240 --depth 80 --height 40 --cols 6 --rows 1 --output spice_rack.stl
```

## How it works

The tray geometry is built from non-overlapping axis-aligned solid boxes:

1. **Bottom plate** – full footprint, `bottom_thickness` mm tall.
2. **Four outer walls** – sit on top of the bottom plate and reach the full
   `height`.  Left/right walls span the full depth; front/back walls fit
   between them so corners are solid with no duplicate faces.
3. **Column dividers** – one solid plate per column gap, running the full
   inner depth.
4. **Row dividers** – split into segments at each column divider position so
   they abut the column dividers without volumetric overlap.

Shared faces between adjacent parts carry opposite normals and are merged
correctly by any slicer that evaluates a Boolean union (Cura, PrusaSlicer,
Bambu Studio, etc.).
