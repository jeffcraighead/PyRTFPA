# tests/test_running_d.py
import pytest
import math
from datetime import datetime
from rtfpa.running_d import RunningD
from rtfpa.line_tools import Point3D

@pytest.fixture
def sample_point3d():
    """Create a sample 3D point for testing"""
    return Point3D(1.0, 2.0, 3.0)

@pytest.fixture
def sample_points_list():
    """Create a list of 3D points for testing"""
    return [
        Point3D(0.0, 0.0, 0.0),
        Point3D(1.0, 1.0, 1.0),
        Point3D(2.0, 2.0, 2.0),
        Point3D(3.0, 3.0, 3.0),
        Point3D(4.0, 4.0, 4.0)
    ]

@pytest.fixture
def sample_datetime():
    """Create a sample datetime for testing"""
    return datetime(2023, 1, 1, 12, 0, 0)

@pytest.fixture
def sample_running_d():
    """Create a sample RunningD object for testing"""
    timestamp = datetime(2023, 1, 1, 12, 0, 0)
    return RunningD("test_subject", Point3D(1.0, 2.0, 3.0), timestamp, 0.5, 10.0)

class TestRunningD:
    """Test cases for RunningD class"""

    def test_running_d_initialization(self, sample_datetime):
        """Test RunningD initialization"""
        rd = RunningD("test_subject", Point3D(1.0, 2.0, 3.0), sample_datetime, 0.5, 10.0)
        
        assert rd.subject_id == "test_subject"
        assert rd.position.x == 1.0
        assert rd.position.y == 2.0
        assert rd.position.z == 3.0
        assert rd.timestamp == sample_datetime
        
        # Check array initializations
        assert len(rd.min_sphere_center) == 4
        assert len(rd.max_sphere_center) == 4
        assert len(rd.min_path_length) == 4
        assert len(rd.max_path_length) == 4
        
        # Check initial values
        assert rd.min_sphere_center[0] is not None
        assert rd.max_sphere_center[0] is not None
        assert all(length == 0.0 for length in rd.min_path_length)
        assert all(length == 0.0 for length in rd.max_path_length)
        
        # Check numeric field initialization
        assert rd.real_path_length == 0.0
        assert rd.number_of_steps == 0
        assert rd.D == 0.0

    def test_running_d_repr(self, sample_running_d):
        """Test RunningD string representation"""
        repr_str = repr(sample_running_d)
        assert "RunningD" in repr_str
        assert "test_subject" in repr_str
        assert "D=" in repr_str
        assert "steps=" in repr_str

    def test_fractal_with_zero_scales(self, sample_running_d):
        """Test fractal calculation with zero scales"""
        # Set step sizes to zero
        sample_running_d.min_step_size = 0.0
        sample_running_d.max_step_size = 0.0
        
        sample_running_d.fractal(constrain_to_plane=False, use_velocity=False)
        
        # Should handle gracefully and set D to 0
        assert sample_running_d.D == 0.0

    def test_fractal_velocity_mode(self, sample_running_d):
        """Test fractal calculation in velocity mode"""
        # Set up velocity values
        sample_running_d.min_step_velocity = 1.0
        sample_running_d.max_step_velocity = 5.0
        sample_running_d.min_step_size = 0.0  # Should be ignored in velocity mode
        sample_running_d.max_step_size = 0.0  # Should be ignored in velocity mode
        
        sample_running_d.fractal(constrain_to_plane=False, use_velocity=True)
        
        # Should use velocity values instead of step sizes
        # Exact result depends on implementation, but should not crash
        assert isinstance(sample_running_d.D, float)

    def test_fractal_constrain_to_plane(self, sample_running_d):
        """Test fractal calculation with plane constraint"""
        # Set up some basic values
        sample_running_d.min_step_size = 1.0
        sample_running_d.max_step_size = 2.0
        
        sample_running_d.fractal(constrain_to_plane=True, use_velocity=False)
        
        # Should handle plane constraint without error
        assert isinstance(sample_running_d.D, float)

    def test_calculate_path_length_invalid_scale(self, sample_running_d):
        """Test calculate_path_length with invalid scale"""
        sphere_centers = [Point3D(0, 0, 0), None, None, None]
        path_lengths = [0.0, 0.0, 0.0, 0.0]
        new_point = Point3D(1, 1, 1)
        
        # Test with zero scale
        sample_running_d.calculate_path_length(
            sphere_centers, 0.0, path_lengths, new_point, False
        )
        
        # Should handle gracefully without modifying path lengths significantly
        assert all(length == 0.0 for length in path_lengths)

    def test_calculate_path_length_no_intersections(self, sample_running_d):
        """Test calculate_path_length when no intersections occur"""
        sphere_centers = [Point3D(0, 0, 0), None, None, None]
        path_lengths = [0.0, 0.0, 0.0, 0.0]
        new_point = Point3D(0.1, 0.1, 0.1)  # Very close point
        scale = 1.0  # Large scale relative to distance
        
        sample_running_d.calculate_path_length(
            sphere_centers, scale, path_lengths, new_point, False
        )
        
        # Should handle case where distance < scale
        assert isinstance(path_lengths[0], float)

    def test_fractal_calculation_edge_cases(self, sample_running_d):
        """Test fractal calculation edge cases"""
        # Test with very small positive values
        sample_running_d.min_step_size = 1e-10
        sample_running_d.max_step_size = 1e-9
        sample_running_d.min_path_length = [1e-8, 0.0, 0.0, 0.0]
        sample_running_d.max_path_length = [1e-7, 0.0, 0.0, 0.0]
        
        sample_running_d.fractal(constrain_to_plane=False, use_velocity=False)
        
        # Should handle very small numbers without NaN/inf
        assert not math.isnan(sample_running_d.D)
        assert not math.isinf(sample_running_d.D)

    def test_fractal_with_negative_path_lengths(self, sample_running_d):
        """Test fractal calculation with negative path lengths"""
        sample_running_d.min_step_size = 1.0
        sample_running_d.max_step_size = 2.0
        sample_running_d.min_path_length = [-1.0, 0.0, 0.0, 0.0]  # Invalid
        sample_running_d.max_path_length = [1.0, 0.0, 0.0, 0.0]
        
        sample_running_d.fractal(constrain_to_plane=False, use_velocity=False)
        
        # Should handle invalid values gracefully
        assert sample_running_d.D == 0.0