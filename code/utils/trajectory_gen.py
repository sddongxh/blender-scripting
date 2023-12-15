# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.
from typing import List

import numpy as np


def generate_spiral_trajectory(
    center: List[float],
    radius: float,
    num_points: int,
    num_loops: int = 1,
    extra=False,
    random=False,
) -> List:

    phi = np.arccos((1 - np.linspace(0, 1, num_points)) * 2 - 1)  # polar angles
    theta = np.linspace(0, 2.0 * np.pi * num_loops, num_points)  # azimuthal angles
    if random:
        theta += np.random.rand() * np.pi * 2
    # Convert spherical coordinates to Cartesian coordinates
    x = center[0] + radius * np.sin(phi) * np.cos(theta)
    y = center[1] + radius * np.sin(phi) * np.sin(theta)
    z = center[2] + radius * np.cos(phi)
    points = list(zip(x, y, z))
    extra_points = []
    if extra:
        for phi in [np.pi / 3, np.pi / 2]:
            for theta in [0, np.pi / 2, np.pi, np.pi * 3 / 2]:
                x = center[0] + radius * np.sin(phi) * np.cos(theta)
                y = center[1] + radius * np.sin(phi) * np.sin(theta)
                z = center[2] + radius * np.cos(phi)
                extra_points.append([x, y, z])
    return points + extra_points


# This is an common random sampling method and is used by zero123, prepared for the future use.
def generate_uniform_sampled_trajectory(
    center: List[float], radius_min: float, radius_max: float, num_points: int
):
    points = []
    for _ in range(num_points):
        vec = np.random.uniform(-1, 1, 3)
        radius = np.random.uniform(radius_min, radius_max, 1)
        vec = vec / np.linalg.norm(vec, axis=0) * radius[0]
        points.append(vec)
    return points


available_trajectory_types = [
    "SPIRAL_TRAJECTORY_FIXED",
    "SPIRAL_TRAJECTORY_RANDOM_EXTRA",
    "SPIRAL_TRAJECTORY_FIXED_EXTRA",
]
