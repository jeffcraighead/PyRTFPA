# tests/test_line_tools.py
import math
from rtfpa.line_tools import Point3D, LineToolsRT


class TestPoint3D:
    """Test cases for Point3D class"""

    def test_point3d_initialization(self):
        """Test Point3D initialization with default and custom values"""
        # Test default initialization
        p1 = Point3D()
        assert p1.x == 0.0
        assert p1.y == 0.0
        assert p1.z == 0.0

        # Test custom initialization
        p2 = Point3D(1.5, 2.5, 3.5)
        assert p2.x == 1.5
        assert p2.y == 2.5
        assert p2.z == 3.5

    def test_point3d_repr(self):
        """Test Point3D string representation"""
        p = Point3D(1.0, 2.0, 3.0)
        expected = "Point3D(x=1.0, y=2.0, z=3.0)"
        assert repr(p) == expected

    def test_distance_same_point(self):
        """Test distance calculation between same points"""
        p1 = Point3D(1.0, 2.0, 3.0)
        p2 = Point3D(1.0, 2.0, 3.0)
        assert Point3D.distance(p1, p2) == 0.0

    def test_distance_different_points(self):
        """Test distance calculation between different points"""
        p1 = Point3D(0.0, 0.0, 0.0)
        p2 = Point3D(3.0, 4.0, 0.0)
        expected_distance = 5.0  # 3-4-5 triangle
        assert Point3D.distance(p1, p2) == expected_distance

    def test_distance_3d(self):
        """Test 3D distance calculation"""
        p1 = Point3D(0.0, 0.0, 0.0)
        p2 = Point3D(1.0, 1.0, 1.0)
        expected_distance = math.sqrt(3)
        assert abs(Point3D.distance(p1, p2) - expected_distance) < 1e-10

    def test_xy_distance_same_point(self):
        """Test XY distance calculation between same points"""
        p1 = Point3D(1.0, 2.0, 3.0)
        p2 = Point3D(1.0, 2.0, 5.0)  # Different Z
        assert Point3D.xy_distance(p1, p2) == 0.0

    def test_xy_distance_different_points(self):
        """Test XY distance calculation ignoring Z coordinate"""
        p1 = Point3D(0.0, 0.0, 0.0)
        p2 = Point3D(3.0, 4.0, 100.0)  # Large Z difference
        expected_distance = 5.0  # Only XY distance matters
        assert Point3D.xy_distance(p1, p2) == expected_distance

    def test_distance_negative_coordinates(self):
        """Test distance calculation with negative coordinates"""
        p1 = Point3D(-1.0, -2.0, -3.0)
        p2 = Point3D(1.0, 2.0, 3.0)
        expected_distance = math.sqrt(4 + 16 + 36)  # sqrt(56)
        assert abs(Point3D.distance(p1, p2) - expected_distance) < 1e-10


class TestLineToolsRT:
    """Test cases for LineToolsRT class"""

    def test_line_sphere_intersect_no_intersection(self):
        """Test line-sphere intersection with no intersection"""
        line_p1 = Point3D(0.0, 0.0, 0.0)
        line_p2 = Point3D(1.0, 0.0, 0.0)
        sphere_center = Point3D(0.0, 2.0, 0.0)
        sphere_radius = 1.0

        result = LineToolsRT.line_sphere_intersect(
            line_p1, line_p2, sphere_center, sphere_radius
        )
        assert result is None

    def test_line_sphere_intersect_tangent(self):
        """Test line-sphere intersection with tangent line"""
        line_p1 = Point3D(-1.0, 1.0, 0.0)
        line_p2 = Point3D(1.0, 1.0, 0.0)
        sphere_center = Point3D(0.0, 0.0, 0.0)
        sphere_radius = 1.0

        result = LineToolsRT.line_sphere_intersect(
            line_p1, line_p2, sphere_center, sphere_radius
        )
        assert result is not None
        assert len(result) == 1
        assert abs(result[0].x - 0.0) < 1e-10
        assert abs(result[0].y - 1.0) < 1e-10

    def test_line_sphere_intersect_two_points(self):
        """Test line-sphere intersection with two intersection points"""
        line_p1 = Point3D(-2.0, 0.0, 0.0)
        line_p2 = Point3D(2.0, 0.0, 0.0)
        sphere_center = Point3D(0.0, 0.0, 0.0)
        sphere_radius = 1.0

        result = LineToolsRT.line_sphere_intersect(
            line_p1, line_p2, sphere_center, sphere_radius
        )
        assert result is not None
        assert len(result) == 2
        
        # Sort results by x coordinate for consistent testing
        result.sort(key=lambda p: p.x)
        assert abs(result[0].x - (-1.0)) < 1e-10
        assert abs(result[1].x - 1.0) < 1e-10

    def test_line_sphere_intersect_segment_inside_unconstrained(self):
        """Test line-sphere intersection with two intersection points - segment is inside sphere"""
        line_p1 = Point3D(-2.0, 0.0, 0.0)
        line_p2 = Point3D(2.0, 0.0, 0.0)
        sphere_center = Point3D(0.0, 0.0, 0.0)
        sphere_radius = 3.0

        result = LineToolsRT.line_sphere_intersect(
            line_p1, line_p2, sphere_center, sphere_radius, False
        )
        assert result is not None
        assert len(result) == 2

        # Sort results by x coordinate for consistent testing
        result.sort(key=lambda p: p.x)
        assert abs(result[0].x - (-3.0)) < 1e-10
        assert abs(result[1].x - 3.0) < 1e-10

    def test_line_sphere_intersect_segment_inside_constrained(self):
        """Test line-sphere intersection with two intersection points - segment is inside sphere"""
        line_p1 = Point3D(-2.0, 0.0, 0.0)
        line_p2 = Point3D(2.0, 0.0, 0.0)
        sphere_center = Point3D(0.0, 0.0, 0.0)
        sphere_radius = 3.0

        result = LineToolsRT.line_sphere_intersect(
            line_p1, line_p2, sphere_center, sphere_radius, True
        )
        assert result is not None
        assert len(result) == 2

        # Sort results by x coordinate for consistent testing
        result.sort(key=lambda p: p.x)
        assert abs(result[0].x - (-2.0)) < 1e-10
        assert abs(result[1].x - 2.0) < 1e-10

    def test_line_sphere_intersect_outside_segment(self):
        """Test line-sphere intersection outside segment when constrained"""
        line_p1 = Point3D(2.0, 0.0, 0.0)
        line_p2 = Point3D(3.0, 0.0, 0.0)
        sphere_center = Point3D(0.0, 0.0, 0.0)
        sphere_radius = 1.0

        result = LineToolsRT.line_sphere_intersect(
            line_p1, line_p2, sphere_center, sphere_radius, constrain_to_segment=True
        )
        assert result is None

    def test_line_sphere_intersect_unconstrained(self):
        """Test line-sphere intersection without segment constraint"""
        line_p1 = Point3D(2.0, 0.0, 0.0)
        line_p2 = Point3D(3.0, 0.0, 0.0)
        sphere_center = Point3D(0.0, 0.0, 0.0)
        sphere_radius = 1.0

        result = LineToolsRT.line_sphere_intersect(
            line_p1, line_p2, sphere_center, sphere_radius, constrain_to_segment=False
        )
        assert result is not None
        assert len(result) == 2

    def test_calculate_fractal_dimension_simple_empty_path(self):
        """Test fractal dimension calculation with empty path"""
        result = LineToolsRT.calculate_fractal_dimension_simple([], 0.1, 1.0)
        assert result == 0.0

    def test_calculate_fractal_dimension_simple_single_point(self):
        """Test fractal dimension calculation with single point"""
        points = [Point3D(0.0, 0.0, 0.0)]
        result = LineToolsRT.calculate_fractal_dimension_simple(points, 0.1, 1.0)
        assert result == 0.0

    def test_calculate_fractal_dimension_simple_straight_line(self):
        """Test fractal dimension calculation with straight line"""
        points = [
            Point3D(0.0, 0.0, 0.0),
            Point3D(2.0, 0.0, 0.0),
            Point3D(4.0, 0.0, 0.0),
            Point3D(6.0, 0.0, 0.0),
            Point3D(10.0, 0.0, 0.0)
        ]
        result = LineToolsRT.calculate_fractal_dimension_simple(points, 0.5, 2.0)
        # Straight line should have fractal dimension close to 1
        assert 0.8 <= result <= 1.2

    def test_calculate_fractal_dimension_simple_invalid_scales(self):
        """Test fractal dimension calculation with invalid scales"""
        points = [Point3D(0.0, 0.0, 0.0), Point3D(1.0, 1.0, 1.0)]
        
        # Test with same scales
        result = LineToolsRT.calculate_fractal_dimension_simple(points, 1.0, 1.0)
        assert result == 0.0

        # Test with zero scales
        result = LineToolsRT.calculate_fractal_dimension_simple(points, 0.0, 1.0)
        assert result == 0.0