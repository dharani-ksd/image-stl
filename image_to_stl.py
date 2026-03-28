"""
image_to_stl.py - Convert a grayscale heightmap image to a solid STL file.

Usage:
    python image_to_stl.py [INPUT_IMAGE] [OUTPUT_STL] [OPTIONS]

Arguments:
    INPUT_IMAGE   Path to the input image (default: DSC_2695.jpg)
    OUTPUT_STL    Path for the output STL file (default: <input_stem>.stl)

Options:
    --max-size N      Downsample image so the longest edge is at most N pixels
                      (default: 300)
    --xy-scale F      Millimetres per pixel in X and Y (default: 0.5)
    --z-scale F       Maximum height in millimetres (default: 10.0)
    --base-height F   Height of the flat base in millimetres (default: 1.0)
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from stl import mesh


def image_to_heightmap(img_path: str, max_size: int = 300) -> np.ndarray:
    """Load an image and return a 2-D float array in [0, 1]."""
    img = Image.open(img_path).convert("L")  # grayscale

    # Downsample so the longest edge is at most max_size pixels.
    w, h = img.size
    scale = min(max_size / max(w, h), 1.0)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    img = img.resize((new_w, new_h), Image.LANCZOS)

    data = np.array(img, dtype=np.float32) / 255.0  # shape: (rows, cols)
    return data


def heightmap_to_mesh(
    heightmap: np.ndarray,
    xy_scale: float = 0.5,
    z_scale: float = 10.0,
    base_height: float = 1.0,
) -> mesh.Mesh:
    """
    Convert a 2-D heightmap to a watertight STL mesh.

    The mesh consists of:
      - Top surface (triangulated heightmap)
      - Flat bottom face
      - Four side walls
    """
    rows, cols = heightmap.shape

    # Build vertex grid for the top surface.
    # z = base_height + pixel_value * z_scale
    xs = np.arange(cols, dtype=np.float32) * xy_scale
    ys = np.arange(rows, dtype=np.float32) * xy_scale
    zs = base_height + heightmap * z_scale

    # ------------------------------------------------------------------ #
    # Top surface triangles (two per quad cell)                           #
    # ------------------------------------------------------------------ #
    top_triangles = []
    for r in range(rows - 1):
        for c in range(cols - 1):
            # Four corners of each quad
            v00 = (xs[c],     ys[r],     zs[r,   c  ])
            v10 = (xs[c + 1], ys[r],     zs[r,   c+1])
            v01 = (xs[c],     ys[r + 1], zs[r+1, c  ])
            v11 = (xs[c + 1], ys[r + 1], zs[r+1, c+1])

            # Triangle 1: v00 - v10 - v11
            top_triangles.append((v00, v10, v11))
            # Triangle 2: v00 - v11 - v01
            top_triangles.append((v00, v11, v01))

    # ------------------------------------------------------------------ #
    # Bottom face (flat quad split into two triangles, winding reversed)  #
    # ------------------------------------------------------------------ #
    x_min, x_max = xs[0], xs[-1]
    y_min, y_max = ys[0], ys[-1]
    z_bot = 0.0

    b00 = (x_min, y_min, z_bot)
    b10 = (x_max, y_min, z_bot)
    b01 = (x_min, y_max, z_bot)
    b11 = (x_max, y_max, z_bot)

    bottom_triangles = [
        (b00, b11, b10),
        (b00, b01, b11),
    ]

    # ------------------------------------------------------------------ #
    # Side walls (four walls, each split into triangles)                  #
    # ------------------------------------------------------------------ #
    wall_triangles = []

    # Front wall  (r = 0, y = y_min)
    for c in range(cols - 1):
        tl = (xs[c],     y_min, zs[0, c  ])
        tr = (xs[c + 1], y_min, zs[0, c+1])
        bl = (xs[c],     y_min, z_bot)
        br = (xs[c + 1], y_min, z_bot)
        wall_triangles.append((tl, bl, br))
        wall_triangles.append((tl, br, tr))

    # Back wall  (r = rows-1, y = y_max)
    for c in range(cols - 1):
        tl = (xs[c],     y_max, zs[-1, c  ])
        tr = (xs[c + 1], y_max, zs[-1, c+1])
        bl = (xs[c],     y_max, z_bot)
        br = (xs[c + 1], y_max, z_bot)
        wall_triangles.append((tl, br, bl))
        wall_triangles.append((tl, tr, br))

    # Left wall  (c = 0, x = x_min)
    for r in range(rows - 1):
        tl = (x_min, ys[r],     zs[r,   0])
        tr = (x_min, ys[r + 1], zs[r+1, 0])
        bl = (x_min, ys[r],     z_bot)
        br = (x_min, ys[r + 1], z_bot)
        wall_triangles.append((tl, br, bl))
        wall_triangles.append((tl, tr, br))

    # Right wall  (c = cols-1, x = x_max)
    for r in range(rows - 1):
        tl = (x_max, ys[r],     zs[r,   -1])
        tr = (x_max, ys[r + 1], zs[r+1, -1])
        bl = (x_max, ys[r],     z_bot)
        br = (x_max, ys[r + 1], z_bot)
        wall_triangles.append((tl, bl, br))
        wall_triangles.append((tl, br, tr))

    # ------------------------------------------------------------------ #
    # Assemble all triangles into a numpy-stl Mesh                        #
    # ------------------------------------------------------------------ #
    all_triangles = top_triangles + bottom_triangles + wall_triangles
    n = len(all_triangles)

    stl_mesh = mesh.Mesh(np.zeros(n, dtype=mesh.Mesh.dtype))
    for i, (v0, v1, v2) in enumerate(all_triangles):
        stl_mesh.vectors[i] = [v0, v1, v2]

    stl_mesh.update_normals()
    return stl_mesh


def main():
    parser = argparse.ArgumentParser(
        description="Convert an image to an STL heightmap relief."
    )
    parser.add_argument(
        "input_image",
        nargs="?",
        default="DSC_2695.jpg",
        help="Input image path (default: DSC_2695.jpg)",
    )
    parser.add_argument(
        "output_stl",
        nargs="?",
        default=None,
        help="Output STL path (default: <input_stem>.stl)",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=300,
        metavar="N",
        help="Downsample so the longest edge is at most N pixels (default: 300)",
    )
    parser.add_argument(
        "--xy-scale",
        type=float,
        default=0.5,
        metavar="F",
        help="Millimetres per pixel in X and Y (default: 0.5)",
    )
    parser.add_argument(
        "--z-scale",
        type=float,
        default=10.0,
        metavar="F",
        help="Maximum relief height in millimetres (default: 10.0)",
    )
    parser.add_argument(
        "--base-height",
        type=float,
        default=1.0,
        metavar="F",
        help="Flat base height in millimetres (default: 1.0)",
    )

    args = parser.parse_args()

    input_path = args.input_image
    output_path = args.output_stl or str(Path(input_path).with_suffix(".stl"))

    print(f"Loading image: {input_path}")
    heightmap = image_to_heightmap(input_path, max_size=args.max_size)
    rows, cols = heightmap.shape
    print(f"  Downsampled to {cols}×{rows} pixels")

    print("Building STL mesh …")
    stl_mesh = heightmap_to_mesh(
        heightmap,
        xy_scale=args.xy_scale,
        z_scale=args.z_scale,
        base_height=args.base_height,
    )

    top = 2 * (rows - 1) * (cols - 1)
    walls = 2 * (2 * (cols - 1) + 2 * (rows - 1))
    bottom = 2
    total = top + walls + bottom
    size_x = (cols - 1) * args.xy_scale
    size_y = (rows - 1) * args.xy_scale
    size_z = args.base_height + args.z_scale
    print(
        f"  Triangles: {total:,}  "
        f"({top:,} top + {walls} walls + {bottom} bottom)"
    )
    print(
        f"  Object size: {size_x:.1f} × {size_y:.1f} × {size_z:.1f} mm"
    )

    stl_mesh.save(output_path)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
