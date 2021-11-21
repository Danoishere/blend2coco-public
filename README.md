# blend2coco - Blender to COCO Dataset
Create a COCO (Common Objects in Context) dataset from Blender 2.82.
Parts of the code are based on ImmersiveLimits amazing tutorial on COCO datasets:
https://www.immersivelimit.com/tutorials/create-coco-annotations-from-scratch

The script basically switches to Workbench Flat Shading in the Background, makes some Color Range adjustments and renders an image. This image is then converted into polygons and merged into one big json-file.

To assign a class, you have to add a **Custom Property** to the object with the name **class** and an *Integer Value that corresponds to the class id*

```python
# I have troubles with importing modules while using the VSCode Blender extension
import sys,os
from importlib import reload
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())
import blend2coco as b2c
reload(b2c)


output_path = '<enter an output path here>'
width = 1024
height = 1024

categories = [{
            "supercategory": "shape",
            "id": 0,
            "name": "cube"
        },
        {
            "supercategory": "animal",
            "id": 1,
            "name": "monkey"
        }]

# Each frame corresponds in one output image
frames = list(range(1, 6))
b2c.scene_to_coco_file(width, height, frames, categories, output_path)

```

### That's how it looks if you use the COCO viewer

![Result of running the Coco2Blend script - Rectangular frames around two objects in blender](doc/screenshot-coco.png "Screenshot of the Result")
