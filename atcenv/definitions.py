"""
Definitions module
"""
from shapely.geometry import Point, Polygon
from dataclasses import dataclass, field
import atcenv.units as u
import math
import random
from typing import Optional, Tuple


@dataclass
class Airspace:
    """
    Airspace class
    """
    polygon: Polygon

    @classmethod
    def random(cls, min_area: float, max_area: float):
        """
        Creates a random airspace sector with min_area < area <= max_area
        :param max_area: maximum area of the sector (in nm^2)
        :param min_area: minimum area of the sector (in nm^2)
        :return: random airspace
        """
        R = math.sqrt(max_area / math.pi)

        def random_point_in_circle(radius: float) -> Point:
            alpha = 2 * math.pi * random.uniform(0., 1.)
            r = radius * math.sqrt(random.uniform(0., 1.))
            x = r * math.cos(alpha)
            y = r * math.sin(alpha)
            return Point(x, y)

        p = [random_point_in_circle(R) for _ in range(3)]
        polygon = Polygon(p).convex_hull

        while polygon.area < min_area:
            p.append(random_point_in_circle(R))
            polygon = Polygon(p).convex_hull

        return cls(polygon=polygon)


@dataclass
class Flight:
    """
    Flight class
    """
    position: Point
    target: Point
    optimal_airspeed: float

    airspeed: float = field(init=False)
    track: float = field(init=False)
    planned_distance: float = field(init=False)
    actual_distance: float = 0
    action: int = field(init=False)
    action_step: int = 0
    angle_goal: int = 0
    speed_goal: int = 0
    n_turns: int = 0
    distance_to_closest_flight: int = 10e9

    def __post_init__(self) -> None:
        """
        Initialises the track and the airspeed
        and computes the trajectory length
        :return:
        """
        self.track = self.bearing
        self.airspeed = self.optimal_airspeed
        self.planned_distance = self.position.distance(self.target)

    @property
    def bearing(self) -> float:
        """
        Bearing from current position to target
        :return:
        """
        dx = self.target.x - self.position.x
        dy = self.target.y - self.position.y
        compass = math.atan2(dx, dy)
        return (compass + u.circle) % u.circle

    @property
    def prediction(self, dt: Optional[float] = 120) -> Point:
        """
        Predicts the future position after dt seconds, maintaining the current speed and track
        :param dt: prediction look-ahead time (in seconds)
        :return:
        """
        dx, dy = self.components
        return Point([self.position.x + dx * dt, self.position.y + dy * dt])

    @property
    def components(self) -> Tuple:
        """
        X and Y Speed components (in kt)
        :return: speed components
        """
        dx = self.airspeed * math.sin(self.track)
        dy = self.airspeed * math.cos(self.track)
        return dx, dy

    @property
    def distance(self) -> float:
        """
        Current distance to the target (in meters)
        :return: distance to the target
        """
        return self.position.distance(self.target)

    @property
    def drift(self) -> float:
        """
        Drift angle (difference between track and bearing) to the target
        :return:
        """
        drift = self.bearing - self.track

        if drift > math.pi:
            return -(u.circle - drift)
        elif drift < -math.pi:
            return (u.circle + drift)
        else:
            return drift

    @classmethod
    def random(cls, airspace: Airspace, min_speed: float, max_speed: float, tol: float = 0.):
        """
        Creates a random flight
        :param airspace: airspace where the flight is located
        :param max_speed: maximum speed of the flights (in kt)
        :param min_speed: minimum speed of the flights (in kt)
        :param tol: tolerance to consider that the target has been reached (in meters)
        :return: random flight
        """
        def random_point_in_polygon(polygon: Polygon) -> Point:
            minx, miny, maxx, maxy = polygon.bounds
            while True:
                point = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
                if polygon.contains(point):
                    return point

        # random position
        position = random_point_in_polygon(airspace.polygon)

        # random target
        boundary = airspace.polygon.boundary
        while True:
            d = random.uniform(0, airspace.polygon.boundary.length)
            target = boundary.interpolate(d)
            if target.distance(position) > tol:
                break

        # random speed
        airspeed = random.uniform(min_speed, max_speed)

        return cls(position, target, airspeed)
