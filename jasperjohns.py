import numpy as np
from scipy.spatial import Voronoi, voronoi_plot_2d
import shapely.geometry
import shapely.ops
import shapely.affinity
import matplotlib.pyplot as plt
import random
import math
import ezdxf

# Create a new DXF document.
doc = ezdxf.new(dxfversion="R2010")
msp = doc.modelspace()

points = np.random.random((100, 2))
vor = Voronoi(points)
#voronoi_plot_2d(vor)

lines = [
    shapely.geometry.LineString(vor.vertices[line])
    for line in vor.ridge_vertices
    if -1 not in line
]

def stripes(ang):
    for x in range(-200,200,1):
        yield shapely.affinity.rotate(
            shapely.geometry.LineString(
            [[0.5,-1],[0.5,2]]), ang).parallel_offset(2*x/200)


for poly in shapely.ops.polygonize(lines):
    #plt.plot(*poly.buffer(-0.01, resolution=16).exterior.xy)
    ang = random.randint(0,360)
    for stripe in stripes(ang):
        l = poly.buffer(-0.01/2, resolution=16).intersection(
                stripe).intersection(
                shapely.geometry.Polygon([[0.2,0.2],[0.8,0.2],[0.8,0.8],[0.2,0.8]])
                ).xy
        plt.plot(*l, color="black")
        if all(len(n)>0 for n in l):
            #print(list(zip(*[tuple(n) for n in l])))
            msp.add_line(*list(zip(*[tuple(n) for n in l])))


plt.xlim([0.2,0.8])
plt.ylim([0.2,0.8])
doc.saveas("export.dxf")
plt.show()