import bpy
from mathutils import *
import bpy
from time import time
import numpy as np
import cv2
import os
import random
import numpy as np

from PIL import Image
import numpy as np                                 
from skimage import measure             
from shapely.geometry import Polygon, MultiPolygon
import json
import datetime
import tempfile

D = bpy.data
C = bpy.context

def render_segmentation_img(w,h):
    try:
        disp_scene = bpy.context.scene.display
        old_light = disp_scene.shading.light
        disp_scene.shading.light = 'FLAT'

        old_color_type = disp_scene.shading.color_type
        disp_scene.shading.color_type = 'MATERIAL'

        old_render_engine = bpy.context.scene.render.engine
        bpy.context.scene.render.engine = 'BLENDER_WORKBENCH'

        old_aa = disp_scene.render_aa
        disp_scene.render_aa = 'OFF'

        old_dither = bpy.context.scene.render.dither_intensity
        bpy.context.scene.render.dither_intensity = 0

        old_disply_device = bpy.context.scene.display_settings.display_device
        bpy.context.scene.display_settings.display_device = 'sRGB'

        old_view_transform = bpy.context.scene.view_settings.view_transform
        bpy.context.scene.view_settings.view_transform = 'Raw'

        path = 'C:\\Users\\Dano\\Documents\\ZHAW\\bachelor-thesis\\delete_me.png'
        start = time()
        bpy.context.scene.render.filepath = path
        bpy.context.scene.render.resolution_x = w
        bpy.context.scene.render.resolution_y = h
        bpy.ops.render.render(write_still = True)
        end = time()
        

        rgb = cv2.imread(path)
        rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)

    except BaseException as e:
        print(e)
    finally:
        disp_scene.shading.light = old_light
        disp_scene.shading.color_type = old_color_type
        bpy.context.scene.render.engine = old_render_engine
        bpy.context.scene.render.dither_intensity = old_dither
        disp_scene.render_aa = old_aa
        bpy.context.scene.display_settings.display_device = old_disply_device
        bpy.context.scene.view_settings.view_transform = old_view_transform


    return Image.fromarray(rgb, 'RGB')

def to_blender_color(rgba_tuple):
    float_srgb = np.append(np.array(rgba_tuple)/255.0, 1.0)
    return float_srgb #float_rgb

def get_unused_color(colors_used):
    color = tuple(np.random.randint(0,256, 3))
    while color in colors_used:
        color = tuple(np.random.randint(0,256, 3))
    colors_used.append(color)
    return color

def get_category_for_color(mapping, rgb_tuple):
    for obj_name in mapping:
        if str(mapping[obj_name]['color']) == rgb_tuple:
            return mapping[obj_name]['class']
    return -1

def create_sub_masks(mask_image):
    width, height = mask_image.size

    # Initialize a dictionary of sub-masks indexed by RGB colors
    sub_masks = {}
    for x in range(width):
        for y in range(height):
            # Get the RGB values of the pixel
            pixel = mask_image.getpixel((x,y))[:3]

            # If the pixel is not black...
            if pixel != (0, 0, 0):
                # Check to see if we've created a sub-mask...
                pixel_str = str(pixel)
                sub_mask = sub_masks.get(pixel_str)
                if sub_mask is None:
                   # Create a sub-mask (one bit per pixel) and add to the dictionary
                    # Note: we add 1 pixel of padding in each direction
                    # because the contours module doesn't handle cases
                    # where pixels bleed to the edge of the image
                    sub_masks[pixel_str] = Image.new('1', (width+2, height+2))

                # Set the pixel value to 1 (default is 0), accounting for padding
                sub_masks[pixel_str].putpixel((x+1, y+1), 1)

    return sub_masks

def create_sub_mask_annotation(sub_mask, image_id, category_id, annotation_id, is_crowd):
    # Find contours (boundary lines) around each sub-mask
    # Note: there could be multiple contours if the object
    # is partially occluded. (E.g. an elephant behind a tree)
    contours = measure.find_contours(sub_mask, 0.5, positive_orientation='low')

    segmentations = []
    polygons = []
    for contour in contours:
        # Flip from (row, col) representation to (x, y)
        # and subtract the padding pixel
        for i in range(len(contour)):
            row, col = contour[i]
            contour[i] = (col - 1, row - 1)

        # Make a polygon and simplify it
        poly = Polygon(contour)
        poly = poly.simplify(1.0, preserve_topology=False)
        polygons.append(poly)
        segmentation = np.array(poly.exterior.coords).ravel().tolist()
        segmentations.append(segmentation)

    # Combine the polygons to calculate the bounding box and area
    multi_poly = MultiPolygon(polygons)
    x, y, max_x, max_y = multi_poly.bounds
    width = max_x - x
    height = max_y - y
    bbox = (x, y, width, height)
    area = multi_poly.area

    annotation = {
        'segmentation': segmentations,
        'iscrowd': is_crowd,
        'image_id': image_id,
        'category_id': category_id,
        'id': annotation_id,
        'bbox': bbox,
        'area': area
    }

    return annotation

def scene_to_coco_annotations(width, height, image_id, annotation_start_id):
    mapping = {}
    old_colors = {}
    colors_used = []

    for obj in D.objects:
        if obj.type == 'MESH':
            if 'class' in obj:
                # Backup original viewport color
                old_colors[obj.name] = tuple(obj.active_material.diffuse_color)

                # Find new color
                color = get_unused_color(colors_used)
                mapping[obj.name] = {}
                mapping[obj.name]['color'] = color
                mapping[obj.name]['class'] = obj['class']

                obj.active_material.diffuse_color = to_blender_color(color)

    mask_img = render_segmentation_img(width,height)



    # Restore original viewport color
    for obj_name in old_colors:
        bpy.data.objects[obj_name].active_material.diffuse_color = old_colors[obj_name]

    # These ids will be automatically increased as we go
    annotation_id = annotation_start_id
    annotations = []
    sub_masks = create_sub_masks(mask_img)
    for color, sub_mask in sub_masks.items():
        category_id = get_category_for_color(mapping, color)
        if category_id == -1:
            raise ValueError("Could not assign class to color " + str(color))

        annotation = create_sub_mask_annotation(sub_mask, image_id, category_id, annotation_id, is_crowd=0)
        annotations.append(annotation)
        annotation_id += 1

    return annotations, annotation_id

def render_rgb_img(w,h):
    path = tempfile.gettempdir() + os.path.sep + "rgb-blender-render.png"
    start = time()
    bpy.context.scene.render.filepath = path
    bpy.context.scene.render.resolution_x = w
    bpy.context.scene.render.resolution_y = h
    bpy.ops.render.render(write_still = True)
    end = time()
    
    rgb = cv2.imread(path)
    rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
    return rgb

def scene_to_coco_file(width, height, frames, categories, output_path):
    images = []
    annotations = []
    annotation_start_id = 0
    image_id = 0


    for frame in frames:
        bpy.context.scene.frame_set(frame)
        image_id = frame
        img_name = 'img-' + str(frame) + ".png"
        img_annotations, annotation_start_id = scene_to_coco_annotations(
            width, 
            height, 
            image_id = image_id, 
            annotation_start_id = annotation_start_id)

        rgb = render_rgb_img(width, height)
        cv2.imwrite(output_path + os.path.sep + img_name, rgb)

        img = {
            "license": 1,
            "file_name": img_name,
            "coco_url": "output" + os.path.sep + img_name,
            "height": height,
            "width": width,
            "date_captured": str(datetime.datetime.now()),
            "flickr_url": "http://farm7.staticflickr.com/6116/6255196340_da26cf2c9e_z.jpg",
            "id": image_id
        }

        images.append(img)
        annotations += img_annotations



    coco = {
        "info": {
            "description": "CS-COCO - Completely Synthetic Coco Dataset",
            "version": "1.0",
            "year": 2020,
            "contributor": "Dano Roost",
            "date_created": "2020/02/28",
            "url" : "https://github.com/Danoishere"
        },
        "licenses": [
            {
                "url": "http://creativecommons.org/licenses/by-nc/2.0/",
                "id": 1,
                "name": "Attribution-NonCommercial License"
            }
        ],
        "images": images,
        "annotations": annotations,
        "categories": categories
    }

    with open("output" + os.path.sep + 'cs-coco.json', 'w') as outfile:
        json.dump(coco, outfile)