from dataclasses import dataclass
import math
from typing import Optional, List

@dataclass
class Point3D:
    """3D point representation"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __repr__(self):
        return f"Point3D(x={self.x}, y={self.y}, z={self.z})"

    @staticmethod
    def distance(p1: 'Point3D', p2: 'Point3D') -> float:
        """Calculate Euclidean distance between two 3D points"""
        import math
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

    @staticmethod
    def xy_distance(p1: 'Point3D', p2: 'Point3D') -> float:
        """Calculate distance between two points in XY plane only"""
        import math
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)


class LineToolsRT:
    """
    Line Tools for Real-Time fractal calculations.
    Contains methods for line-sphere intersection and fractal dimension calculation.
    """

    @staticmethod
    def line_sphere_intersect(
        line_point1: Point3D,
        line_point2: Point3D,
        sphere_center: Point3D,
        sphere_radius: float,
        constrain_to_segment: bool = True
    ) -> Optional[List[Point3D]]:
        """
        Determines where on the specified line segment the specified sphere intersects.

        Args:
            line_point1: First point defining the line
            line_point2: Second point defining the line
            sphere_center: Center of the sphere
            sphere_radius: Radius of the sphere
            constrain_to_segment: If True, only return intersections within the line segment

        Returns:
            List of intersection points (0, 1, or 2 points), or None if no intersection
        """
        # Calculate quadratic coefficients for line-sphere intersection
        # Line parameterized as P(t) = P1 + t(P2 - P1) where t ∈ [0,1] for segment
        dx = line_point2.x - line_point1.x
        dy = line_point2.y - line_point1.y
        dz = line_point2.z - line_point1.z

        # Coefficients for at² + bt + c = 0
        a = dx**2 + dy**2 + dz**2

        b = 2 * (
            dx * (line_point1.x - sphere_center.x) +
            dy * (line_point1.y - sphere_center.y) +
            dz * (line_point1.z - sphere_center.z)
        )

        c = (
            sphere_center.x**2 + sphere_center.y**2 + sphere_center.z**2 +
            line_point1.x**2 + line_point1.y**2 + line_point1.z**2 -
            2 * (sphere_center.x * line_point1.x +
                 sphere_center.y * line_point1.y +
                 sphere_center.z * line_point1.z) -
            sphere_radius**2
        )

        # Calculate discriminant
        discriminant = b**2 - 4*a*c

        # No intersection if discriminant is negative
        if discriminant < 0:
            return None

        # Single intersection (tangent) if discriminant is zero
        elif discriminant == 0:
            t = -b / (2*a)
            if constrain_to_segment and (t < 0 or t > 1):
                return None

            result = Point3D(
                line_point1.x + t * dx,
                line_point1.y + t * dy,
                line_point1.z + t * dz
            )
            return [result]

        # Two intersections if discriminant is positive
        else:
            sqrt_discriminant = math.sqrt(discriminant)
            t1 = (-b + sqrt_discriminant) / (2*a)
            t2 = (-b - sqrt_discriminant) / (2*a)

            # This incorrectly, but on purpose, forces the result to be a point on the line segment.
            # When walking along a path, the sphere center should always lie on the path, this
            # makes sure we end up with a points on the path.
            if constrain_to_segment:
                t1 = max(0.0, min(1.0, t1))
                t2 = max(0.0, min(1.0, t2))

            # Check each intersection point individually
            results = []
            for t in [t1, t2]:
                if not constrain_to_segment or (0.0 <= t <= 1.0):
                    point = Point3D(
                        line_point1.x + t * dx,
                        line_point1.y + t * dy,
                        line_point1.z + t * dz
                    )
                    if constrain_to_segment and Point3D.distance(point, sphere_center) > sphere_radius:
                        continue
                    results.append(point)

            return results if results else None



    @staticmethod
    def calculate_fractal_dimension_simple(
        path_points: List[Point3D],
        min_scale: float,
        max_scale: float
    ) -> float:
        """
        Simplified fractal dimension calculation for a complete path.
        This is a utility method for testing or batch processing.

        Args:
            path_points: List of points forming the path
            min_scale: Minimum measurement scale
            max_scale: Maximum measurement scale

        Returns:
            Estimated fractal dimension
        """
        if min_scale <= 0 or max_scale <= 0:
            return 0.0

        if len(path_points) < 2:
            return 0.0

        # Measure path length at minimum scale
        min_length = 0.0
        i = 0
        while i < len(path_points) - 1:
            j = i + 1
            accumulated = 0.0

            # Find next point at least min_scale away
            while j < len(path_points) and accumulated < min_scale:
                accumulated += Point3D.distance(path_points[j-1], path_points[j])
                j += 1

            min_length += accumulated
            i = j - 1

        # Measure path length at maximum scale
        max_length = 0.0
        i = 0
        while i < len(path_points) - 1:
            j = i + 1
            accumulated = 0.0

            # Find next point at least max_scale away
            while j < len(path_points) and accumulated < max_scale:
                accumulated += Point3D.distance(path_points[j-1], path_points[j])
                j += 1

            max_length += accumulated
            i = j - 1

        # Calculate fractal dimension
        try:
            if min_length > 0 and max_length > 0 and min_scale != max_scale:
                log_length_diff = math.log10(min_length) - math.log10(max_length)
                log_scale_diff = math.log10(min_scale) - math.log10(max_scale)
                return 1.0 - (log_length_diff / log_scale_diff)
        except (ValueError, ZeroDivisionError):
            pass

        return 0.0
