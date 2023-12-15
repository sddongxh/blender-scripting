import os
from typing import Any, Dict, List, Union  # noqa

import bpy
import numpy as np
from mathutils import Matrix, Vector  # noqa


def add_camera(location=(0.0, 0.0, 0.0), _type="PERSP") -> bpy.types.Object:
    assert _type in ["PERSP", "ORTHO", "PANO"]
    if False:
        cameraData = bpy.data.cameras.new("Camera")
        cameraData.type = _type
        cameraObj = bpy.data.objects.new("CameraObj", cameraData)
        cameraObj.location = location
        bpy.context.collection.objects.link(cameraObj)
    else:
        bpy.ops.object.add(type="CAMERA", location=(0, 0.0, 0))
        cameraObj = bpy.context.object
        cameraObj.data.type = _type

    bpy.context.scene.camera = cameraObj  # make it the current camera
    assert isinstance(cameraObj, bpy.types.Object)
    return cameraObj


def get_lookat_transfrom(location: Vector, target: Vector) -> Matrix:
    d = location - target
    rotation_quat = d.to_track_quat("Z", "Y")
    rotation_matrix = rotation_quat.to_matrix().to_4x4()
    translation_matrix = Matrix.Translation(location)
    transform_matrix = translation_matrix @ rotation_matrix
    return transform_matrix  # a.k.a. obj.matrix_world


def set_camera_lookat(obj: bpy.types.Object, location: Vector, target: Vector) -> None:
    d = location - target
    rotation_quat = d.to_track_quat("Z", "Y")
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = rotation_quat
    obj.location = location


def add_light(
    location=(0.0, 0.0, 0.0), _type="POINT", energy=1.0, color=(1.0, 1.0, 1.0)
) -> bpy.types.Object:
    assert _type in ["POINT", "SUN", "SPOT", "HEMI", "AREA"], f"type == {type}"
    bpy.ops.object.add(type="LIGHT", location=location)
    obj = bpy.context.object
    obj.data.type = _type
    obj.data.energy = energy
    obj.data.color = color
    assert isinstance(obj, bpy.types.Object)
    return obj


def set_background_lighting(color=(1.0, 1.0, 1.0), strength=0.0):
    world = bpy.data.worlds["World"]
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value[:3] = color
    bg.inputs[1].default_value = strength


def render_still(
    filepath: str,
    resolution_x=None,
    resolution_y=None,
    engine="CYCLES",
    samples=None,
):
    assert engine in ["BLENDER_EEVEE", "CYCLES"]

    if bpy.context.space_data:  # Check if script is executed inside Blender
        return
    bpy.context.scene.view_settings.view_transform = "Standard"

    s = bpy.context.scene
    if samples:
        s.cycles.samples = samples
    if resolution_x:
        s.render.resolution_x = resolution_x
    if resolution_y:
        s.render.resolution_y = resolution_y
    s.render.resolution_percentage = 100
    s.render.engine = engine
    s.render.filepath = filepath

    bpy.ops.render.render(write_still=True)


def set_camera_intrinsics_from_calibration_matrix(
    K: np.ndarray, image_width: int, image_height: int
):
    """
    Reference: https://blender.stackexchange.com/a/120063.
    The K matrix should have the format:
        [[fx, 0, cx],
         [0, fy, cy],
         [0, 0,  1]]
    """
    cam_ob = bpy.context.scene.camera
    cam = cam_ob.data

    assert abs(K[0][1]) < 1e-7, "Skew is not supported by Blender yet"

    fx, fy = K[0][0], K[1][1]  # focal length in pixels
    cx, cy = K[0][2], K[1][2]  # principal point in pixels

    pixel_aspect_ratio = fx / fy  # dy / dx

    # Determine the sensor fit mode to use
    if cam.sensor_fit == "AUTO":
        # determine which aspect of sensor is larger
        if image_width / fx >= image_height / fy:
            sensor_fit = "HORIZONTAL"
        else:
            sensor_fit = "VERTICAL"
    else:
        sensor_fit = cam.sensor_fit

    # Based on the sensor fit mode, determine the longer view aspect in pixels
    if sensor_fit == "HORIZONTAL":
        view_fac_in_px = image_width
    else:
        view_fac_in_px = pixel_aspect_ratio * image_height
    sensor_size_in_mm = (
        cam.sensor_height if cam.sensor_fit == "VERTICAL" else cam.sensor_width
    )

    # Convert focal length in px to focal length in mm
    f_in_mm = fx * sensor_size_in_mm / view_fac_in_px
    assert (
        f_in_mm >= 1
    ), "The focal length is smaller than 1mm which is not allowed in blender"

    cam.lens_unit = "MILLIMETERS"
    cam.lens = f_in_mm

    # principal point
    cam.shift_x = (cx - (image_width - 1) / 2) / -view_fac_in_px
    cam.shift_y = (cy - (image_height - 1) / 2) / view_fac_in_px * pixel_aspect_ratio

    # Set aspect ratio
    pixel_aspect_y = fx / fy if fx > fy else 1.0
    pixel_aspect_x = fy / fx if fx < fy else 1.0
    bpy.context.scene.render.pixel_aspect_x = pixel_aspect_x
    bpy.context.scene.render.pixel_aspect_y = pixel_aspect_y

    bpy.context.scene.render.resolution_x = image_width
    bpy.context.scene.render.resolution_y = image_height


def load_object(scene_file_path: str) -> bpy.types.Object:
    print("Loading scene: " + scene_file_path)
    bpy.ops.import_scene.gltf(filepath=scene_file_path)
    obj = bpy.context.selected_objects[0]
    print("model loaded: ", obj.name)
    assert isinstance(obj, bpy.types.Object)
    return obj


def set_world_background_hdr(
    img_path: str, strength: float = 1.0, rotation_euler: List = None
):

    if not rotation_euler:
        rotation_euler = [0.0, 0.0, 0.0]

    if not os.path.exists(img_path):
        raise FileNotFoundError(f"file does not exists: {img_path}")

    world = bpy.context.scene.world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links

    background_node = nodes["Background"]
    background_node.inputs["Strength"].default_value = strength

    texture_node = nodes.new(type="ShaderNodeTexEnvironment")
    texture_node.image = bpy.data.images.load(img_path, check_existing=True)

    links.new(texture_node.outputs["Color"], background_node.inputs["Color"])

    # add UV mapping to apply rotation
    mapping_node = nodes.new("ShaderNodeMapping")
    tex_coords_node = nodes.new("ShaderNodeTexCoord")
    links.new(tex_coords_node.outputs["Generated"], mapping_node.inputs["Vector"])
    links.new(mapping_node.outputs["Vector"], texture_node.inputs["Vector"])
    mapping_node.inputs["Rotation"].default_value = rotation_euler


def get_scene_meshes():
    for obj in bpy.context.scene.objects.values():
        if isinstance(obj.data, (bpy.types.Mesh)):
            yield obj


def get_scene_root_objects():
    for obj in bpy.context.scene.objects.values():
        if not obj.parent:
            yield obj


def get_scene_bbox():
    meshes = [
        obj
        for obj in bpy.context.scene.objects.values()
        if isinstance(obj.data, bpy.types.Mesh)
    ]
    assert len(meshes) > 0, "No mesh found in the scene"
    bbox_min = None
    bbox_max = None
    for obj in meshes:
        for v in obj.bound_box:
            v = obj.matrix_world @ Vector(v)
            bbox_max = np.maximum(bbox_max, v) if bbox_max is not None else v
            bbox_min = np.minimum(bbox_min, v) if bbox_min is not None else v
    return bbox_min, bbox_max


def normalize_scene():
    bbox_min, bbox_max = get_scene_bbox()
    scale = 1 / max(bbox_max - bbox_min)
    offset = -(bbox_min + bbox_max) / 2
    for obj in get_scene_root_objects():
        T = Matrix.Diagonal([scale, scale, scale, 1.0]) @ Matrix.Translation(offset)
        obj.matrix_world = T @ obj.matrix_world


def get_nodes_by_idname(nodes, idname: str):
    return [node for node in nodes if node.bl_idname == idname]


def get_principled_bsdf_node(
    obj: bpy.types.Object,
) -> Union[bpy.types.ShaderNodeBsdfPrincipled, None]:
    if not obj.material_slots or len(obj.material_slots) == 0:
        print("no material found")
        return None
    for slot in obj.material_slots:
        mat = slot.material
        if mat and mat.use_nodes:
            nodes = mat.node_tree.nodes
            for node in nodes:
                if node.type == "BSDF_PRINCIPLED":
                    return node
    return None


# get input node to the named input port
def get_principled_bsdf_node_input(
    node: bpy.types.ShaderNode, input_name: str
) -> Union[bpy.types.ShaderNode, None]:
    if node.type != "BSDF_PRINCIPLED":
        print("not a principled BSDF node")
        return None
    if input_name not in node.inputs:
        print("input port does not exist: ", input_name)
        return None
    input = node.inputs[input_name]
    if not input.is_linked:
        print("input port is not linked: ", input_name)
        return None
    return input.links[0].from_node


def get_shader_node_input_link(
    node: bpy.types.ShaderNode, port_name: str
) -> Union[bpy.types.NodeLink, None]:
    if port_name not in node.inputs:
        print("Input port does not exist: ", port_name)
        return None
    input = node.inputs[port_name]
    if not input.is_linked:
        print("Input port is not linked: ", port_name)
        return None
    assert len(input.links) == 1
    return input.links[0]


def setup_base_color_rendering(obj: bpy.types.Object) -> bool:
    principled = get_principled_bsdf_node(obj)
    if not principled:
        print("Failed to get principled BSDF node")
        return False
    link = get_shader_node_input_link(principled, "Base Color")
    if not link:
        print("Failed to get base color link")
        return False
    if not obj.active_material or not obj.active_material.node_tree:
        print("Not active material or not using node")
        return False
    tree = obj.active_material.node_tree
    output_node = tree.nodes.new(type="ShaderNodeOutputMaterial")
    tree.links.new(link.from_socket, output_node.inputs[0])
    output_node.is_active_output = True
    return True


def setup_metallic_roughness_rendering(obj: bpy.types.Object) -> bool:
    principled = get_principled_bsdf_node(obj)
    if not principled:
        print("Failed to get principled BSDF node")
        return False
    metallic_link = get_shader_node_input_link(principled, "Metallic")
    if not metallic_link:
        print("Failed to get base metallic link")
        return False

    roughness_link = get_shader_node_input_link(principled, "Roughness")
    if not roughness_link:
        print("Failed to get base roughness link")
        return False

    if not obj.active_material or not obj.active_material.node_tree:
        print("Not active material or not using node")
        return False
    tree = obj.active_material.node_tree
    output_node = tree.nodes.new(type="ShaderNodeOutputMaterial")

    combine_color_node = tree.nodes.new(type="ShaderNodeCombineColor")
    tree.links.new(combine_color_node.outputs[0], output_node.inputs[0])
    tree.links.new(metallic_link.from_socket, combine_color_node.inputs["Red"])
    tree.links.new(roughness_link.from_socket, combine_color_node.inputs["Green"])
    tree.links.new(combine_color_node.outputs[0], output_node.inputs[0])
    output_node.is_active_output = True

    return True
