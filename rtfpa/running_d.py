import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from line_tools import Point3D, LineToolsRT


@dataclass
class RunningD:
    """
    Data structure holding intermediate values for fractal dimension calculation.
    This tracks the running calculations for real-time fractal path analysis.
    """

    # Required parameters
    subject_id: str
    position: Point3D
    start_timestamp: datetime
    min_multiplier: float
    max_multiplier: float

    # Lists for sphere centers and path lengths (4 scales)
    min_sphere_center: List[Optional[Point3D]] = field(default_factory=lambda: [None, None, None, None])
    max_sphere_center: List[Optional[Point3D]] = field(default_factory=lambda: [None, None, None, None])
    min_path_length: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    max_path_length: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])

    # Path and step measurements
    real_path_length: float = 0.0
    number_of_steps: int = 0
    min_step_size: float = 0.0
    max_step_size: float = 0.0
    mean_step_size: float = 0.0
    velocity_mode: bool = False
    end_timestamp: datetime = None

    # Time and velocity measurements
    step_time: float = 0.0  # Time between successive readings
    step_velocity: float = 0.0
    total_step_velocity: float = 0.0
    mean_step_velocity: float = 0.0
    max_step_velocity: float = 0.0
    min_step_velocity: float = 0.0

    # Fractal dimension result
    D: float = 0.0

    def __post_init__(self):
        self.min_sphere_center[0] = self.position
        self.max_sphere_center[0] = self.position
        self.end_timestamp = self.start_timestamp


    def add_point(self, point: Point3D, timestamp: datetime, constrain_to_plane = False):
        """Continue an existing path"""
        self.number_of_steps += 1

        # Calculate distance
        if constrain_to_plane:
            # Create copies for XY distance calculation
            p1 = Point3D(self.position.x, self.position.y, 0.0)
            p2 = Point3D(point.x, point.y, 0.0)
            dist_to_last_point = Point3D.distance(p1, p2)
        else:
            dist_to_last_point = Point3D.distance(self.position, point)

        # Update path measurements
        self.real_path_length += dist_to_last_point
        self.mean_step_size = self.real_path_length / self.number_of_steps

        # Calculate time between readings
        self.step_time = (timestamp - self.end_timestamp).total_seconds()
        self.end_timestamp = timestamp

        if self.velocity_mode:
            self.mean_step_size /= self.step_time

        self.min_step_size = self.mean_step_size * self.min_multiplier
        self.max_step_size = self.mean_step_size * self.max_multiplier

        # Update position
        self.position = point


        # Fill sphere centers if needed
        for i in range(4):
            if self.min_sphere_center[i] is None:
                self.min_sphere_center[i] = self.position
                self.max_sphere_center[i] = self.position
                break

        self.fractal(constrain_to_plane, self.velocity_mode)

    def fractal(self, constrain_to_plane: bool = False, use_velocity: bool = False) -> None:
        """
        Calculate fractal dimension using the box-counting method.
        Updates the D value in the RunningD object.

        Args:
            constrain_to_plane: If True, only use XY coordinates (ignore Z)
            use_velocity: If True, use velocity-based scales instead of distance-based
        """

        new_point = Point3D(self.position.x, self.position.y, self.position.z)

        # Choose appropriate scale based on mode
        if use_velocity:
            min_scale = self.min_step_velocity
            max_scale = self.max_step_velocity
        else:
            min_scale = self.min_step_size
            max_scale = self.max_step_size

        # Constrain to XY plane if requested
        if constrain_to_plane:
            new_point.z = 0


        # Calculate the four minimum path lengths
        self.calculate_path_length(self.min_sphere_center, min_scale, self.min_path_length, new_point, constrain_to_plane)

        # Calculate the four maximum path lengths
        self.calculate_path_length(self.max_sphere_center, max_scale, self.max_path_length, new_point, constrain_to_plane)

        # Calculate fractal dimensions for each of the 4 scales
        fractal_dimensions = []

        for i in range(4):
            if (self.min_path_length[i] > 0 and self.max_path_length[i] > 0 and
                    min_scale > 0 and max_scale > 0):
                try:
                    # Fractal dimension formula: D = 1 - slope of log(length) vs log(scale)
                    log_length_diff = math.log10(self.min_path_length[i]) - math.log10(self.max_path_length[i])
                    log_scale_diff = math.log10(min_scale) - math.log10(max_scale)

                    if log_scale_diff != 0:
                        fd = 1.0 - (log_length_diff / log_scale_diff)

                        # Only include valid values
                        if not math.isnan(fd) and not math.isinf(fd):
                            fractal_dimensions.append(fd)

                except (ValueError, ZeroDivisionError):
                    # Skip invalid calculations
                    pass

        # Calculate mean fractal dimension
        if fractal_dimensions:
            self.D = sum(fractal_dimensions) / len(fractal_dimensions)
        else:
            self.D = 0.0


    def calculate_path_length(self, sphere_center_list, scale, path_length_list, new_point, constrain_to_plane):
        running_total = 0.0
        i = 0
        # Calculate the four minimum path lengths
        # for i in range(4):
        while i < 4:
            if sphere_center_list[i] is None:
                break

            if scale <= 0.0:
                i += 1
                continue

            # If constraining to plane, modify sphere center Z coordinate
            sphere_center = sphere_center_list[i]
            if constrain_to_plane:
                sphere_center = Point3D(sphere_center.x, sphere_center.y, 0)

            distance = Point3D.distance(sphere_center, new_point)

            if distance < scale:
                i += 1
                continue

            # Get intersection points
            intersect_points = LineToolsRT.line_sphere_intersect(
                sphere_center, new_point, sphere_center, scale, True
            )

            if intersect_points is None:
                i += 1
                continue

            # Determine which intersection point is closer to new_point
            d0 = Point3D.distance(intersect_points[0], new_point)
            d1 = Point3D.distance(intersect_points[1], new_point) if len(intersect_points) > 1 else float('inf') # set d1 to inf if there is only 1 intersection point

            if d0 < d1:
                running_total += scale
                sphere_center_list[i] = intersect_points[0]
            else:
                running_total += scale
                sphere_center_list[i] = intersect_points[1]

            # Check if we need to continue measuring
            distance_to_new_point = Point3D.distance(sphere_center_list[i], new_point)
            # if distance_to_new_point >= scale:
            #     pass # Continue with same index to keep walking the line with the ruler of scale size
            # else:
            if distance_to_new_point <= scale: # if the new point is within the scale ruler size, move on to the next set of calculations
                path_length_list[i] += running_total
                running_total = 0
                i += 1  # increase the loop index




    def __repr__(self):
        return (f"RunningD(subject_id='{self.subject_id}', "
                f"position={self.position}, "
                f"D={self.D:.4f}, "
                f"steps={self.number_of_steps})")
