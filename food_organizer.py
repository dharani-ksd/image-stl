"""
food_organizer.py – Generate a parametric food-organizer tray STL for 3-D printing.

Creates a rectangular open-top tray divided into a configurable grid of
compartments.  All dimensions are in millimetres.

Usage:
    python food_organizer.py [OPTIONS]

Options:
    --output FILE            Output STL file path (default: food_organizer.stl)
    --width F                Overall tray width  (X) in mm (default: 200)
    --depth F                Overall tray depth  (Y) in mm (default: 150)
    --height F               Overall tray height (Z) in mm (default: 50)
    --wall-thickness F       Outer wall thickness in mm   (default: 2.0)
    --bottom-thickness F     Base plate thickness in mm   (default: 2.0)
    --cols N                 Number of compartment columns (default: 3)
    --rows N                 Number of compartment rows    (default: 2)
    --divider-thickness F    Internal divider thickness in mm (default: 2.0)

Examples:
    # Default 3×2 tray (200×150×50 mm)
    python food_organizer.py

    # Large kitchen drawer organizer, 4 columns × 3 rows
    python food_organizer.py --width 300 --depth 200 --height 60 --cols 4 --rows 3

    # Single-row spice rack, 6 compartments
    python food_organizer.py --width 240 --depth 80 --height 40 --cols 6 --rows 1

Mesh construction
-----------------
The tray is assembled from non-overlapping axis-aligned solid boxes:

  ┌──── outer wall (left) ────┐
  │  col  │  col  │  col  │  │  ← row divider runs between col dividers
  │  div  │  div  │  div  │  │
  └───────────────────────────┘
        bottom plate

  - Bottom plate   : full footprint, z ∈ [0, bottom_thickness]
  - Left/right walls : full depth,  z ∈ [bottom_thickness, height]
  - Front/back walls : between left & right walls, z ∈ [bottom_thickness, height]
  - Column dividers  : full inner depth, z ∈ [bottom_thickness, height]
  - Row dividers     : segmented by column dividers (no volumetric overlap)

Shared faces between adjacent parts carry opposite normals and are correctly
merged by any slicer that evaluates a Boolean union (Cura, PrusaSlicer,
Bambu Studio, etc.).
"""

import argparse

import numpy as np
from stl import mesh


# ---------------------------------------------------------------------------
# Low-level geometry helper
# ---------------------------------------------------------------------------

def _box_triangles(
    x0: float, y0: float, z0: float,
    x1: float, y1: float, z1: float,
) -> list:
    """Return 12 triangles (two per face) for a solid axis-aligned box.

    Winding order produces outward-facing normals on all six faces.
    """
    v = [
        (x0, y0, z0), (x1, y0, z0), (x0, y1, z0), (x1, y1, z0),  # z0 layer
        (x0, y0, z1), (x1, y0, z1), (x0, y1, z1), (x1, y1, z1),  # z1 layer
    ]
    return [
        # Bottom  (z = z0, normal −Z)
        (v[0], v[2], v[1]), (v[1], v[2], v[3]),
        # Top     (z = z1, normal +Z)
        (v[4], v[5], v[6]), (v[5], v[7], v[6]),
        # Front   (y = y0, normal −Y)
        (v[0], v[1], v[4]), (v[1], v[5], v[4]),
        # Back    (y = y1, normal +Y)
        (v[2], v[6], v[3]), (v[3], v[6], v[7]),
        # Left    (x = x0, normal −X)
        (v[0], v[4], v[2]), (v[2], v[4], v[6]),
        # Right   (x = x1, normal +X)
        (v[1], v[3], v[5]), (v[3], v[7], v[5]),
    ]


# ---------------------------------------------------------------------------
# Main model builder
# ---------------------------------------------------------------------------

def build_organizer(
    outer_width: float = 200.0,
    outer_depth: float = 150.0,
    height: float = 50.0,
    wall_thickness: float = 2.0,
    bottom_thickness: float = 2.0,
    n_cols: int = 3,
    n_rows: int = 2,
    divider_thickness: float = 2.0,
) -> mesh.Mesh:
    """Build and return a food-organizer tray as a numpy-stl Mesh.

    Args:
        outer_width:       Overall X dimension in millimetres.
        outer_depth:       Overall Y dimension in millimetres.
        height:            Overall Z dimension in millimetres.
        wall_thickness:    Thickness of the four outer walls in mm.
        bottom_thickness:  Thickness of the base plate in mm.
        n_cols:            Number of columns (≥ 1).
        n_rows:            Number of rows    (≥ 1).
        divider_thickness: Thickness of internal dividers in mm.

    Returns:
        A numpy-stl Mesh object ready to save as an STL file.

    Raises:
        ValueError: If the requested grid does not fit inside the tray.
    """
    W, D, H = outer_width, outer_depth, height
    Wt, Bt, Dt = wall_thickness, bottom_thickness, divider_thickness

    if n_cols < 1 or n_rows < 1:
        raise ValueError("n_cols and n_rows must each be at least 1.")
    if H <= Bt:
        raise ValueError(
            f"height ({H}) must be greater than bottom_thickness ({Bt})."
        )

    inner_w = W - 2 * Wt
    inner_d = D - 2 * Wt

    if inner_w <= 0:
        raise ValueError(
            f"outer_width ({W}) is too small for wall_thickness={Wt}."
        )
    if inner_d <= 0:
        raise ValueError(
            f"outer_depth ({D}) is too small for wall_thickness={Wt}."
        )
    if n_cols > 1 and inner_w <= (n_cols - 1) * Dt:
        raise ValueError(
            f"outer_width ({W}) is too small for {n_cols} columns with "
            f"wall_thickness={Wt} and divider_thickness={Dt}."
        )
    if n_rows > 1 and inner_d <= (n_rows - 1) * Dt:
        raise ValueError(
            f"outer_depth ({D}) is too small for {n_rows} rows with "
            f"wall_thickness={Wt} and divider_thickness={Dt}."
        )

    # Inner-space extents
    ix0, ix1 = Wt, W - Wt
    iy0, iy1 = Wt, D - Wt

    # ------------------------------------------------------------------
    # Column divider x-spans
    # Each of the n_cols compartments gets equal width; dividers fit between.
    # ------------------------------------------------------------------
    comp_w = (inner_w - (n_cols - 1) * Dt) / n_cols
    x_div_spans = [
        (
            ix0 + comp_w * (i + 1) + Dt * i,
            ix0 + comp_w * (i + 1) + Dt * (i + 1),
        )
        for i in range(n_cols - 1)
    ]

    # X-segments: the open gap in x between consecutive column dividers
    # (one segment per column, used to cut row dividers into non-overlapping pieces)
    x_segs: list[tuple[float, float]] = []
    prev = ix0
    for xd0, xd1 in x_div_spans:
        x_segs.append((prev, xd0))
        prev = xd1
    x_segs.append((prev, ix1))

    # ------------------------------------------------------------------
    # Row divider y-spans
    # ------------------------------------------------------------------
    comp_d = (inner_d - (n_rows - 1) * Dt) / n_rows
    y_div_spans = [
        (
            iy0 + comp_d * (j + 1) + Dt * j,
            iy0 + comp_d * (j + 1) + Dt * (j + 1),
        )
        for j in range(n_rows - 1)
    ]

    # ------------------------------------------------------------------
    # Collect all axis-aligned boxes that make up the tray
    # ------------------------------------------------------------------
    parts: list[tuple[float, ...]] = []

    # Bottom plate (full footprint)
    parts.append((0, 0, 0, W, D, Bt))

    # Outer walls (z starts at Bt so the bottom face of each wall coincides
    # with the top face of the bottom plate — opposite normals merge cleanly).
    # Left and right span the full depth; front and back fit between them.
    parts.append((0,      0,      Bt, Wt,     D,    H))   # left
    parts.append((W - Wt, 0,      Bt, W,      D,    H))   # right
    parts.append((Wt,     0,      Bt, W - Wt, Wt,   H))   # front
    parts.append((Wt,     D - Wt, Bt, W - Wt, D,    H))   # back

    # Column dividers (full inner depth, no x-overlap with row dividers below)
    for xd0, xd1 in x_div_spans:
        parts.append((xd0, iy0, Bt, xd1, iy1, H))

    # Row dividers (segmented so they abut column dividers without overlap)
    for yd0, yd1 in y_div_spans:
        for xs0, xs1 in x_segs:
            parts.append((xs0, yd0, Bt, xs1, yd1, H))

    # ------------------------------------------------------------------
    # Build the numpy-stl Mesh
    # ------------------------------------------------------------------
    triangles: list = []
    for box in parts:
        triangles.extend(_box_triangles(*box))

    n = len(triangles)
    stl_mesh = mesh.Mesh(np.zeros(n, dtype=mesh.Mesh.dtype))
    for i, (v0, v1, v2) in enumerate(triangles):
        stl_mesh.vectors[i] = [v0, v1, v2]
    stl_mesh.update_normals()
    return stl_mesh


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a parametric food-organizer tray STL for 3-D printing.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--output", "-o",
        default="food_organizer.stl",
        metavar="FILE",
        help="Output STL file path",
    )
    parser.add_argument(
        "--width", type=float, default=200.0, metavar="F",
        help="Overall tray width (X) in mm",
    )
    parser.add_argument(
        "--depth", type=float, default=150.0, metavar="F",
        help="Overall tray depth (Y) in mm",
    )
    parser.add_argument(
        "--height", type=float, default=50.0, metavar="F",
        help="Overall tray height (Z) in mm",
    )
    parser.add_argument(
        "--wall-thickness", type=float, default=2.0, metavar="F",
        help="Outer wall thickness in mm",
    )
    parser.add_argument(
        "--bottom-thickness", type=float, default=2.0, metavar="F",
        help="Base plate thickness in mm",
    )
    parser.add_argument(
        "--cols", type=int, default=3, metavar="N",
        help="Number of compartment columns",
    )
    parser.add_argument(
        "--rows", type=int, default=2, metavar="N",
        help="Number of compartment rows",
    )
    parser.add_argument(
        "--divider-thickness", type=float, default=2.0, metavar="F",
        help="Internal divider thickness in mm",
    )

    args = parser.parse_args()

    print("Building food-organizer tray …")
    print(f"  Size  : {args.width} × {args.depth} × {args.height} mm")
    print(f"  Grid  : {args.cols} cols × {args.rows} rows")
    print(
        f"  Thicknesses — wall: {args.wall_thickness} mm  "
        f"base: {args.bottom_thickness} mm  "
        f"divider: {args.divider_thickness} mm"
    )

    stl_mesh = build_organizer(
        outer_width=args.width,
        outer_depth=args.depth,
        height=args.height,
        wall_thickness=args.wall_thickness,
        bottom_thickness=args.bottom_thickness,
        n_cols=args.cols,
        n_rows=args.rows,
        divider_thickness=args.divider_thickness,
    )

    inner_w = args.width - 2 * args.wall_thickness
    inner_d = args.depth - 2 * args.wall_thickness
    Dt = args.divider_thickness
    comp_w = (inner_w - (args.cols - 1) * Dt) / args.cols
    comp_d = (inner_d - (args.rows - 1) * Dt) / args.rows
    comp_h = args.height - args.bottom_thickness
    n_parts = args.cols * args.rows
    print(f"  Compartments: {n_parts}  ({comp_w:.1f} × {comp_d:.1f} × {comp_h:.1f} mm each)")

    stl_mesh.save(args.output)
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
