# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.


import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Union  # noqa

import bpy

import numpy as np
from mathutils import Euler, Matrix, Vector  # noqa

project_path = os.path.dirname(__file__)
sys.path.append(project_path)

import utils.blender_util as butil
# import utils.manifold_util as mfd


def normalize_object(obj: bpy.types.Object):
    bbox_min = None
    bbox_max = None
    for v in obj.bound_box:
        v = obj.matrix_world @ Vector(v)
        bbox_max = np.maximum(bbox_max, v) if bbox_max is not None else v
        bbox_min = np.minimum(bbox_min, v) if bbox_min is not None else v
    scale = 1 / max(bbox_max - bbox_min)
    offset = -(bbox_min + bbox_max) / 2
    T = Matrix.Diagonal([scale, scale, scale, 1.0]) @ Matrix.Translation(offset)
    obj.matrix_world = T @ obj.matrix_world


def rotate_object_and_set_keyframes(obj, frames=360):
    # Make sure we're in object mode
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = frames - 1

    # Rotate and set keyframe for each frame
    for frame in range(frames):
        angle = (frame - 1) * (np.pi * 2 / frames)
        obj.rotation_mode = "XYZ"
        obj.rotation_euler[2] = angle  # Rotate around Z-axis
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)



def setup_depth_and_normal_layers(result_dir: str):
    bpy.context.scene.render.use_compositing = True
    bpy.context.scene.use_nodes = True
    tree = bpy.context.scene.node_tree

    bpy.context.view_layer.use_pass_z = True
    bpy.context.view_layer.use_pass_normal = True

    # get current render layer node
    render_layer_node = [
        node for node in tree.nodes if "CompositorNodeRLayers" in node.bl_idname
    ][0]

    normal_output_node = tree.nodes.new("CompositorNodeOutputFile")
    normal_output_node.base_path = os.path.join(result_dir, "normal")
    normal_output_node.format.file_format = "PNG"
    normal_output_node.format.color_depth = "8"
    normal_output_node.format.color_mode = "RGBA"
    tree.links.new(
        render_layer_node.outputs["Normal"], normal_output_node.inputs["Image"]
    )

    # depth_output_node = tree.nodes.new("CompositorNodeOutputFile")
    # depth_output_node.base_path = os.path.join(result_dir, "depth")
    # depth_output_node.format.file_format = "PNG"  #'OPEN_EXR'
    # depth_output_node.format.color_depth = "16"
    # depth_output_node.format.color_mode = "BW"
    # depth_normalize_node = tree.nodes.new("CompositorNodeNormalize")
    # # tree.links.new(
    # #     render_layer_node.outputs["Depth"], depth_normalize_node.inputs[0]
    # # )
    # # tree.links.new(
    # #     depth_normalize_node.outputs[0], depth_output_node.inputs["Image"]
    # # )
    # tree.links.new(
    #     render_layer_node.outputs["Depth"], depth_output_node.inputs["Image"]
    # )



# def setup_diffuse_rendering(obj: bpy.types.Object) -> bool:
#     principled = get_principled_bsdf_node(obj)
#     if not principled:
#         print("Failed to get principled BSDF node")
#         return False
#     link = get_shader_node_input_link(principled, "Base Color")
#     if not link:
#         print("Failed to get base color link")
#         return False
#     if not obj.active_material or not obj.active_material.node_tree:
#         print("Not active material or not using node")
#         return False
#     tree = obj.active_material.node_tree
#     output_node = tree.nodes.new(type="ShaderNodeOutputMaterial")
#     tree.links.new(link.from_socket, output_node.inputs[0])
#     output_node.is_active_output = True
#     return True




def render_showreel(config: Dict, save_dir: str) -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    bpy.context.scene.render.film_transparent = True
    bpy.context.scene.render.image_settings.color_mode = "RGBA"

    plane_obj = butil.load_object(config["plane_file"])
    if config["set_plane_material"]:
        plane_obj.active_material.use_nodes = True
        tree = plane_obj.active_material.node_tree
        output_node = tree.nodes.new(type="ShaderNodeOutputMaterial")
        glossy_node = tree.nodes.new(type="ShaderNodeBsdfGlossy")
        color_value = 0.2
        glossy_node.inputs[0].default_value = (color_value, color_value, color_value, 1)
        glossy_node.inputs[1].default_value = 0.1
        tree.links.new(glossy_node.outputs[0], output_node.inputs[0])
        output_node.is_active_output = True



    model_obj = butil.load_object(config["model_file"])
    normalize_object(model_obj)
    if True:
        model_obj.active_material.use_nodes = True
        tree = model_obj.active_material.node_tree
        output_node = tree.nodes.new(type="ShaderNodeOutputMaterial")
        diffuse_node = tree.nodes.new(type="ShaderNodeBsdfDiffuse")
        tree.links.new(diffuse_node.outputs[0], output_node.inputs[0])
        output_node.is_active_output = True



    plane_obj.location += model_obj.location

    cam_obj = butil.add_camera()
    cam_obj.data.lens_unit = "FOV"
    cam_obj.data.angle = np.radians(15)

    radius = config["radius"]
    angle = config["angle"] / 180 * np.pi
    camera_center = Vector([radius * np.cos(angle), 0, radius * np.sin(angle)])
    cam_obj.matrix_world = butil.get_lookat_transfrom(camera_center, Vector([0, 0, 0]))

    if config["bg_lighting"]:
        butil.set_world_background_hdr(img_path=config["bg_file"], strength=1.0)
    else:
        light_obj1 = butil.add_light([5, 2, 3], "SPOT", 300)
        light_obj1.matrix_world = butil.get_lookat_transfrom(
            light_obj1.location, Vector([0, 0, 0])
        )
        light_obj2 = butil.add_light([3, 0.5, 0.1], "SPOT", 130)
        light_obj2.matrix_world = butil.get_lookat_transfrom(
            light_obj2.location, Vector([0, 0, 0])
        )

    setup_depth_and_normal_layers(save_dir)



    rotate_object_and_set_keyframes(model_obj, config["frames"])

    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = config["samples"]
    bpy.context.scene.render.resolution_x = config["resolution"]
    bpy.context.scene.render.resolution_y = config["resolution"]

    if not save_dir.endswith("/"):
        save_dir += "/"

    if config["video"]:
        bpy.context.scene.render.image_settings.file_format = "FFMPEG"
        bpy.context.scene.render.ffmpeg.format = "MPEG4"
        bpy.context.scene.render.filepath = os.path.join(save_dir, "video.mp4")
        bpy.context.scene.render.fps = 24
    else:
        bpy.context.scene.render.image_settings.file_format = "PNG"
        bpy.context.scene.render.filepath = save_dir

    bpy.ops.render.render(animation=True)









config = {}
config["plane_file"] = "data/glbs/plane_round.glb"
config["set_plane_material"] = True
config["model_file"]  = "/Users/xihuadong/data/LODs/Dino/DinoGreenPinacosaurus_LOD1.glb"
config["model_file"] = "TeaPot_B088M9JPDS_BlueWhiteFlowers_LOD1.glb"
# config["model_file"] = "BirdHouse_B08DKC6Y97_TanWallsBrownRoof_LOD1.glb"
save_dir = "teapot"


config["radius"] = 5
config["angle"] = 5
config["resolution"] = 2048
config["video"] = False 
config["samples"] = 64
config["frames"] = 24*8
config["bg_lighting"] = False

render_showreel(config=config, save_dir=save_dir)