from datetime import datetime, timedelta
from typing import Dict
from line_tools import Point3D
from running_d import RunningD

class RTFPA:
    """Real-Time Fractal Path Analysis class"""

    def __init__(self, min_mul: float = 0.5, max_mul: float = 10.0):
        self.min_multiplier = min_mul
        self.max_multiplier = max_mul
        self.velocity_mode = False
        self.tracked_objects_running_d: Dict[str, RunningD] = {}
        self.seconds_till_new_path = 60
        self.constrain_to_plane = False


    def new_reading(self, subject_id: str, x: float, y: float, z: float,
                    timestamp: datetime) -> RunningD:
        """Process a new reading with datetime object"""

        # Create temporary RunningD for comparisons
        new_point = Point3D(x,y,z)

        # If subject already exists in tracking
        if subject_id in self.tracked_objects_running_d:
            tracked_running_d = self.tracked_objects_running_d[subject_id]

            # Check if point is in same position as before
            if self.constrain_to_plane:
                if Point3D.xy_distance(new_point, tracked_running_d.position) == 0.0:
                    return tracked_running_d
            else:
                if Point3D.distance(new_point, tracked_running_d.position) == 0.0:
                    return tracked_running_d

            # Check if we need to start a new path
            time_diff_seconds = abs(timestamp - tracked_running_d.end_timestamp)

            if time_diff_seconds > timedelta(seconds=self.seconds_till_new_path):
                # Start a new path
                self.start_new_path(subject_id, new_point, timestamp)
            else:
                # Continue existing path
                self._continue_path(tracked_running_d, new_point, timestamp)

            #self.tracked_objects_running_d[subject_id] = tracked_running_d
        else:
            # New subject
            self.start_new_path(subject_id, new_point, timestamp)


        return self.tracked_objects_running_d[subject_id]


    def start_new_path(self, subject_id: str, new_point: Point3D, timestamp: datetime) -> None:
        """Start a new path for the subject"""
        self.tracked_objects_running_d[subject_id] = RunningD(subject_id, new_point, timestamp, self.min_multiplier, self.max_multiplier)
        self.tracked_objects_running_d[subject_id].velocity_mode = self.velocity_mode


    def _continue_path(self, current_path_rd: RunningD, new_point: Point3D, timestamp: datetime) -> None:
        current_path_rd.add_point(new_point, timestamp, self.constrain_to_plane)

    def set_timeout(self, timeout: int) -> None:
        """Set the timeout for starting a new path"""
        self.seconds_till_new_path = timeout

    def set_plane_constraint(self, constrain: bool) -> None:
        """Set whether to constrain calculations to XY plane"""
        self.constrain_to_plane = constrain

    def set_velocity_mode(self, vm: bool) -> None:
        """Set velocity mode"""
        self.velocity_mode = vm
