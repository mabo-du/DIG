import pyvista as pv
import numpy as np

grid = pv.ImageData()
grid.dimensions = (10, 10, 10)
grid.spacing = (1, 1, 1)
print(dir(grid))
