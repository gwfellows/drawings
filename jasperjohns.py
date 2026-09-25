"""Jasper Johns style hatched Voronoi panel, exported as a cuttable DXF profile.

Seed points make a Voronoi tessellation; each cell is hatched with parallel
stripes at its own random angle.  Every stripe becomes a slot -- a stadium of
the given radius swept along the stripe -- and the DXF holds the outer panel
boundary plus the outline of each slot, all in inches.
"""
import argparse
import math
import random
from pathlib import Path

import ezdxf
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
import numpy as np
import shapely.geometry
import shapely.ops
from scipy.spatial import Voronoi

TOL = 1e-9


def parse_size(text):
    """Parse a 'LxW' size in inches."""
    parts = text.lower().replace("*", "x").split("x")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("size must look like 31x36")
    try:
        length, width = (float(p) for p in parts)
    except ValueError:
        raise argparse.ArgumentTypeError("size must look like 31x36") from None
    if length <= 0 or width <= 0:
        raise argparse.ArgumentTypeError("size must be positive")
    return length, width


def cells(length, width, count, rng):
    """Voronoi cells covering the panel.

    Points are scattered over a region half again the size of the panel so the
    unbounded outer cells -- the ones with a -1 vertex -- fall clear of it.
    """
    pad = 0.25
    pts = rng.random((max(count, 3), 2))
    pts = pts * (length * (1 + 2 * pad), width * (1 + 2 * pad))
    pts -= (length * pad, width * pad)
    vor = Voronoi(pts)
    ridges = [
        shapely.geometry.LineString(vor.vertices[ridge])
        for ridge in vor.ridge_vertices
        if -1 not in ridge
    ]
    panel = shapely.geometry.box(0, 0, length, width)
    return [cell for cell in shapely.ops.polygonize(ridges) if cell.intersects(panel)]


def stripes(region, angle, pitch):
    """Parallel chords across `region`, `pitch` apart centre to centre."""
    minx, miny, maxx, maxy = region.bounds
    cx, cy = region.centroid.coords[0]
    reach = math.hypot(maxx - minx, maxy - miny)
    along = math.radians(angle)
    dx, dy = math.cos(along), math.sin(along)
    nx, ny = -dy, dx
    for i in range(-int(reach / pitch) - 1, int(reach / pitch) + 2):
        ox, oy = cx + nx * i * pitch, cy + ny * i * pitch
        yield shapely.geometry.LineString(
            [(ox - dx * reach, oy - dy * reach), (ox + dx * reach, oy + dy * reach)]
        )


def parts(geom, types):
    """Flatten a geometry down to the components of the given types."""
    if geom.is_empty:
        return
    if geom.geom_type in types:
        yield geom
    elif hasattr(geom, "geoms"):
        for part in geom.geoms:
            yield from parts(part, types)


def centrelines(length, width, radius, strut, border, pitch, count, rng, rand):
    """The centreline of every slot, as (start, end) point pairs."""
    # Centrelines stop `radius` short of the border so the slot outline, which
    # grows by `radius` in every direction, leaves the border itself solid.
    edge = radius + border
    # shapely.box happily builds an inverted rectangle when minx > maxx, so
    # check the span rather than trusting is_empty.
    if length <= 2 * edge or width <= 2 * edge:
        raise SystemExit(
            f"panel {length:g}x{width:g} in is too small to hold a slot of radius "
            f"{radius:g} in inside a {border:g} in border"
        )
    panel = shapely.geometry.box(edge, edge, length - edge, width - edge)
    # Each region gives up half a strut, so two neighbours leave a whole one.
    inset = radius + strut / 2
    for cell in cells(length, width, count, rng):
        angle = rand.uniform(0, 360)
        for region in parts(cell.buffer(-inset).intersection(panel), {"Polygon"}):
            for stripe in stripes(region, angle, pitch):
                for cut in parts(stripe.intersection(region), {"LineString"}):
                    coords = list(cut.coords)
                    yield coords[0], coords[-1]


def add_slot(msp, start, end, radius, attribs):
    """Draw one stadium: two flanks and two end caps, as exact DXF arcs."""
    (x0, y0), (x1, y1) = start, end
    span = math.hypot(x1 - x0, y1 - y0)
    if span < TOL:
        msp.add_circle(start, radius, dxfattribs=attribs)
        return
    dx, dy = (x1 - x0) / span, (y1 - y0) / span
    nx, ny = -dy * radius, dx * radius
    msp.add_line((x0 + nx, y0 + ny), (x1 + nx, y1 + ny), dxfattribs=attribs)
    msp.add_line((x1 - nx, y1 - ny), (x0 - nx, y0 - ny), dxfattribs=attribs)
    # DXF arcs sweep counter-clockwise, so each cap runs from its right-hand
    # flank round to its left-hand one.
    heading = math.degrees(math.atan2(dy, dx))
    msp.add_arc(end, radius, heading - 90, heading + 90, dxfattribs=attribs)
    msp.add_arc(start, radius, heading + 90, heading + 270, dxfattribs=attribs)


def render(path, length, width, outlines, dpi, show):
    """Draw the plate solid, with the slots knocked out of it."""
    scale = 10 / max(length, width)
    fig = plt.figure(figsize=(length * scale, width * scale))
    # Axes fill the figure edge to edge, so the image is the plate and nothing
    # else -- no tight-bbox margin around it.
    ax = fig.add_axes((0, 0, 1, 1))
    ax.add_patch(MplPolygon([(0, 0), (length, 0), (length, width), (0, width)],
                            closed=True, facecolor="black", edgecolor="none"))
    for outline in outlines:
        ax.add_patch(MplPolygon(list(outline.exterior.coords), closed=True,
                                facecolor="white", edgecolor="none"))
    ax.set_xlim(0, length)
    ax.set_ylim(0, width)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(path, dpi=dpi, pil_kwargs={"quality": 92})
    if show:
        plt.show()
    plt.close(fig)


def main():
    # ArgumentDefaultsHelpFormatter prints each default, so help text cannot
    # drift out of step with the value above it.
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--size", type=parse_size, default="36x31", metavar="LxW",
                    help="panel length x width in inches, length along x")
    ap.add_argument("--diameter", type=float, default=1 / 4, metavar="IN",
                    help="slot width across the round end")
    ap.add_argument("--spacing", type=float, default=1 / 2, metavar="IN",
                    help="material between adjacent slots inside one region, edge "
                         "to edge")
    ap.add_argument("--strut", type=float, default=1 / 2, metavar="IN",
                    help="material between the slots of neighbouring regions")
    ap.add_argument("--border", type=float, default=1.0, metavar="IN",
                    help="solid border inset from the outer dimensions, no slots "
                         "intrude into it")
    ap.add_argument("--cells", type=int, default=100,
                    help="number of Voronoi seed points")
    ap.add_argument("--seed", type=int, default=None, help="seed for a repeatable panel")
    ap.add_argument("--out", default="export.dxf", help="DXF to write")
    ap.add_argument("--jpg", default=None,
                    help="JPG to write, defaults to --out with a .jpg suffix")
    ap.add_argument("--dpi", type=int, default=200, help="JPG resolution")
    ap.add_argument("--no-preview", action="store_true", help="skip the matplotlib preview")
    args = ap.parse_args()

    length, width = args.size
    if args.diameter <= 0:
        raise SystemExit("diameter must be positive")
    if args.spacing < 0:
        raise SystemExit("spacing cannot be negative")
    if args.strut < 0:
        raise SystemExit("strut cannot be negative")
    if args.border < 0:
        raise SystemExit("border cannot be negative")
    if args.dpi <= 0:
        raise SystemExit("dpi must be positive")
    radius = args.diameter / 2
    # Stripes are laid out centre to centre, so one slot plus one gap.
    pitch = args.diameter + args.spacing

    if args.no_preview:
        # Don't spin up a GUI backend just to write a file.
        matplotlib.use("Agg")

    rng = np.random.default_rng(args.seed)
    rand = random.Random(args.seed)

    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.IN
    doc.header["$INSUNITS"] = ezdxf.units.IN
    doc.layers.add("PROFILE", color=1)
    doc.layers.add("SLOTS", color=3)
    msp = doc.modelspace()

    msp.add_lwpolyline(
        [(0, 0), (length, 0), (length, width), (0, width)],
        close=True,
        dxfattribs={"layer": "PROFILE"},
    )

    outlines = []
    for start, end in centrelines(
        length, width, radius, args.strut, args.border, pitch, args.cells, rng, rand
    ):
        add_slot(msp, start, end, radius, {"layer": "SLOTS"})
        outlines.append(
            shapely.geometry.LineString([start, end]).buffer(radius, quad_segs=32)
        )

    doc.saveas(args.out)
    jpg = args.jpg if args.jpg else str(Path(args.out).with_suffix(".jpg"))
    render(jpg, length, width, outlines, args.dpi, not args.no_preview)
    print(f"{len(outlines)} slots, {length:g}x{width:g} in panel -> {args.out}, {jpg}")


if __name__ == "__main__":
    main()
