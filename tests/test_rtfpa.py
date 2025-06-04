# tests/test_rtfpa.py
import pytest
from datetime import datetime, timedelta
from rtfpa.rtfpa import RTFPA
from rtfpa.running_d import RunningD
from rtfpa.line_tools import Point3D


@pytest.fixture
def sample_datetime():
    """Create a sample datetime for testing"""
    return datetime(2023, 1, 1, 12, 0, 0)

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
def sample_rtfpa():
    """Create a sample RTFPA object for testing"""
    return RTFPA(min_mul=0.5, max_mul=5.0)

class TestRTFPA:
    """Test cases for RTFPA class"""

    def test_rtfpa_initialization(self):
        """Test RTFPA initialization with default and custom parameters"""
        # Test default initialization
        rtfpa = RTFPA()
        assert rtfpa.min_multiplier == 0.5
        assert rtfpa.max_multiplier == 10.0
        assert rtfpa.velocity_mode == False
        assert rtfpa.seconds_till_new_path == 60
        assert rtfpa.constrain_to_plane == False
        assert len(rtfpa.tracked_objects_running_d) == 0

        # Test custom initialization
        rtfpa_custom = RTFPA(min_mul=0.3, max_mul=15.0)
        assert rtfpa_custom.min_multiplier == 0.3
        assert rtfpa_custom.max_multiplier == 15.0

    def test_new_reading_new_subject(self, sample_rtfpa, sample_datetime):
        """Test new_reading with a new subject"""
        result = sample_rtfpa.new_reading(
            "subject1", 1.0, 2.0, 3.0, sample_datetime
        )
        
        assert result is not None
        assert result.subject_id == "subject1"
        assert result.position.x == 1.0
        assert result.position.y == 2.0
        assert result.position.z == 3.0
        assert result.timestamp == sample_datetime
        assert "subject1" in sample_rtfpa.tracked_objects_running_d

    def test_new_reading_same_position(self, sample_rtfpa, sample_datetime):
        """Test new_reading with same position (should return existing object)"""
        # First reading
        result1 = sample_rtfpa.new_reading(
            "subject1", 1.0, 2.0, 3.0, sample_datetime
        )
        
        # Second reading at same position
        result2 = sample_rtfpa.new_reading(
            "subject1", 1.0, 2.0, 3.0, sample_datetime + timedelta(seconds=5)
        )
        
        # Should return the same object (by reference)
        assert len(sample_rtfpa.tracked_objects_running_d) == 1
        assert result1 is result2

    def test_new_reading_same_position_xy_constrained(self, sample_rtfpa, sample_datetime):
        """Test new_reading with same XY position when constrained to plane"""
        sample_rtfpa.set_plane_constraint(True)
        
        # First reading
        result1 = sample_rtfpa.new_reading(
            "subject1", 1.0, 2.0, 3.0, sample_datetime
        )
        
        # Second reading at same XY but different Z
        result2 = sample_rtfpa.new_reading(
            "subject1", 1.0, 2.0, 5.0, sample_datetime + timedelta(seconds=5)
        )
        
        # Should return the same object when constrained to plane
        assert len(sample_rtfpa.tracked_objects_running_d) == 1
        assert result1 is result2

    def test_new_reading_continue_path(self, sample_rtfpa, sample_datetime):
        """Test new_reading that continues an existing path"""
        # First reading
        result1 = sample_rtfpa.new_reading(
            "subject1", 1.0, 2.0, 3.0, sample_datetime
        )
        
        # Second reading within timeout, different position
        result2 = sample_rtfpa.new_reading(
            "subject1", 2.0, 3.0, 4.0, sample_datetime + timedelta(seconds=30)
        )
        
        assert result2.number_of_steps == 1
        assert result2.real_path_length > 0
        assert result2.position.x == 2.0
        assert result2.position.y == 3.0
        assert result2.position.z == 4.0

    def test_new_reading_new_path_timeout(self, sample_rtfpa, sample_datetime):
        """Test new_reading that starts a new path due to timeout"""
        # First reading
        result1 = sample_rtfpa.new_reading(
            "subject1", 1.0, 2.0, 3.0, sample_datetime
        )
        
        # Second reading after timeout
        result2 = sample_rtfpa.new_reading(
            "subject1", 2.0, 3.0, 4.0, sample_datetime + timedelta(seconds=120)
        )
        
        # Should start a new path
        assert result2.number_of_steps == 0
        assert result2.real_path_length == 0.0

    def test_start_new_path(self, sample_rtfpa, sample_datetime):
        """Test start_new_path method"""
        point = Point3D(1.0, 2.0, 3.0)
        sample_rtfpa.start_new_path("subject1", point, sample_datetime)
        
        assert "subject1" in sample_rtfpa.tracked_objects_running_d
        rd = sample_rtfpa.tracked_objects_running_d["subject1"]
        assert rd.subject_id == "subject1"
        assert rd.position == point
        assert rd.timestamp == sample_datetime

    def test_continue_path_measurements(self, sample_rtfpa, sample_datetime):
        """Test _continue_path method measurements"""
        # Create initial RunningD
        rd = RunningD("subject1", 0.0, 0.0, 0.0, sample_datetime)
        sample_rtfpa.tracked_objects_running_d["subject1"] = rd
        
        # Continue path
        new_point = Point3D(3.0, 4.0, 0.0)  # 5 units away
        new_timestamp = sample_datetime + timedelta(seconds=10)
        sample_rtfpa._continue_path(rd, new_point, new_timestamp)
        
        assert rd.number_of_steps == 1
        assert rd.real_path_length == 5.0
        assert rd.mean_step_size == 5.0
        assert rd.position == new_point
        assert rd.timestamp == new_timestamp

    def test_continue_path_measurements_five_steps(self, sample_rtfpa, sample_datetime):
        """Test _continue_path method measurements"""
        # Create initial RunningD
        rd = RunningD("subject1", 0.0, 0.0, 0.0, sample_datetime)
        rd.min_multiplier = sample_rtfpa.min_multiplier
        rd.max_multiplier = sample_rtfpa.max_multiplier
        sample_rtfpa.tracked_objects_running_d[rd.subject_id] = rd

        # Continue path
        sample_rtfpa._continue_path(rd, Point3D(10.0, 0.0, 0.0), sample_datetime + timedelta(seconds=5))
        sample_rtfpa._continue_path(rd, Point3D(20.0, 0.0, 0.0), sample_datetime + timedelta(seconds=10))
        sample_rtfpa._continue_path(rd, Point3D(30.0, 0.0, 0.0), sample_datetime + timedelta(seconds=15))
        sample_rtfpa._continue_path(rd, Point3D(40.0, 0.0, 0.0), sample_datetime + timedelta(seconds=20))
        sample_rtfpa._continue_path(rd, Point3D(50.0, 0.0, 0.0), sample_datetime + timedelta(seconds=25))
        sample_rtfpa._continue_path(rd, Point3D(60.0, 0.0, 0.0), sample_datetime + timedelta(seconds=30))

        end_point = Point3D(70.0, 0.0, 0.0)
        end_time = sample_datetime + timedelta(seconds=35)
        sample_rtfpa._continue_path(rd, end_point, end_time)

        assert rd.number_of_steps == 7
        assert rd.real_path_length == 70.0
        # assert rd.mean_step_size == 5.0
        assert rd.position == end_point
        assert rd.timestamp == end_time
        assert 1.1 > rd.D > 0.90

    def test_continue_path_xy_constraint(self, sample_rtfpa, sample_datetime):
        """Test _continue_path with XY plane constraint"""
        sample_rtfpa.set_plane_constraint(True)
        
        rd = RunningD("subject1", 0.0, 0.0, 0.0, sample_datetime)
        sample_rtfpa.tracked_objects_running_d["subject1"] = rd
        
        # Move in XY plane with Z difference
        new_point = Point3D(3.0, 4.0, 100.0)  # Z should be ignored
        sample_rtfpa._continue_path(rd, new_point, sample_datetime)
        
        # Should calculate distance only in XY plane (5 units)
        assert rd.real_path_length == 5.0

    def test_continue_path_velocity_mode(self, sample_rtfpa, sample_datetime):
        """Test _continue_path in velocity mode"""
        sample_rtfpa.set_velocity_mode(True)
        
        # rd = RunningD("subject1", 0.0, 0.0, 0.0, sample_datetime)
        # rd.step_time = 1.0  # Simulate step time
        # sample_rtfpa.tracked_objects_running_d["subject1"] = rd


        sample_rtfpa.start_new_path("subject1", Point3D(0.0, 0.0, 0.0), sample_datetime)
        rd = sample_rtfpa.tracked_objects_running_d["subject1"]
        new_point = Point3D(5.0, 0.0, 0.0)
        sample_rtfpa._continue_path(rd, new_point, sample_datetime+timedelta(seconds=10))
        
        # In velocity mode, mean_step_size should be divided by step_time
        # But step_time is calculated in _continue_path, so this tests the division
        assert rd.mean_step_size != rd.real_path_length  # Should be modified

    def test_set_timeout(self, sample_rtfpa):
        """Test set_timeout method"""
        sample_rtfpa.set_timeout(120)
        assert sample_rtfpa.seconds_till_new_path == 120

    def test_set_plane_constraint(self, sample_rtfpa):
        """Test set_plane_constraint method"""
        sample_rtfpa.set_plane_constraint(True)
        assert sample_rtfpa.constrain_to_plane == True
        
        sample_rtfpa.set_plane_constraint(False)
        assert sample_rtfpa.constrain_to_plane == False

    def test_set_velocity_mode(self, sample_rtfpa):
        """Test set_velocity_mode method"""
        sample_rtfpa.set_velocity_mode(True)
        assert sample_rtfpa.velocity_mode == True
        
        sample_rtfpa.set_velocity_mode(False)
        assert sample_rtfpa.velocity_mode == False

    def test_multiple_subjects(self, sample_rtfpa, sample_datetime):
        """Test tracking multiple subjects simultaneously"""
        # Add multiple subjects
        result1 = sample_rtfpa.new_reading(
            "subject1", 1.0, 1.0, 1.0, sample_datetime
        )
        result2 = sample_rtfpa.new_reading(
            "subject2", 2.0, 2.0, 2.0, sample_datetime
        )
        result3 = sample_rtfpa.new_reading(
            "subject3", 3.0, 3.0, 3.0, sample_datetime
        )
        
        assert len(sample_rtfpa.tracked_objects_running_d) == 3
        assert "subject1" in sample_rtfpa.tracked_objects_running_d
        assert "subject2" in sample_rtfpa.tracked_objects_running_d
        assert "subject3" in sample_rtfpa.tracked_objects_running_d
        
        # Verify they are independent
        assert result1.subject_id == "subject1"
        assert result2.subject_id == "subject2"
        assert result3.subject_id == "subject3"

    def test_sphere_center_initialization(self, sample_rtfpa, sample_datetime):
        """Test that sphere centers are properly initialized"""
        result = sample_rtfpa.new_reading(
            "subject1", 1.0, 2.0, 3.0, sample_datetime
        )
        
        # Move to trigger _continue_path
        sample_rtfpa.new_reading(
            "subject1", 2.0, 3.0, 4.0, sample_datetime + timedelta(seconds=5)
        )
        
        rd = sample_rtfpa.tracked_objects_running_d["subject1"]
        
        # Check that sphere centers are being set
        assert rd.min_sphere_center[0] is not None
        assert rd.max_sphere_center[0] is not None

    def test_rtfpa_full_suite(self, sample_rtfpa, sample_datetime):
        sample_rtfpa.new_reading("subject1", 1.0, 2.0, 3.0, sample_datetime)
        sample_rtfpa.new_reading("subject1", 2.0, 3.0, 4.0, sample_datetime+timedelta(seconds=1))
        sample_rtfpa.new_reading("subject1", 3.0, 4.0, 5.0, sample_datetime + timedelta(seconds=2))
        sample_rtfpa.new_reading("subject1", 4.0, 5.0, 6.0, sample_datetime + timedelta(seconds=3))
        sample_rtfpa.new_reading("subject1", 5.0, 6.0, 7.0, sample_datetime + timedelta(seconds=4))
        sample_rtfpa.new_reading("subject1", 6.0, 7.0, 8.0, sample_datetime + timedelta(seconds=5))

        assert len(sample_rtfpa.tracked_objects_running_d)==1
        assert "subject1" in sample_rtfpa.tracked_objects_running_d
        assert 0.9 < sample_rtfpa.tracked_objects_running_d["subject1"].D < 1.1