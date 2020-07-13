import math

# The classes below are used as building blocks for the OpenGL rendering of vector graphics in Assetto Corsa. 
# All classes are based on the two dimensional cartesian coordinate system.

class Point:
    """A point in a 2D cartesian coordinate system.
    
    Each point is described by an X and a Y coordinate.
    """
    def __init__(self, x=0, y=0):
        self.x = float(x)
        self.y = float(y)


    def add(self, val):
        """Addition of value to Point
        
        Args:
            val (obj:Point/float): Value to add to the Point x,y.
                Can pass Point obj to add different values to x and y,
                or a float to add same value to both x and y.
        """
        # Check if val is a Point object
        if isinstance(val, Point):
            # If true, add x,y of val to respective x,y of Point
            self.x += val.x
            self.y += val.y
        else:
            # If false, add val to both x and y 
            self.x += val
            self.y += val


    def subtract(self, val):
        # Check if val is a Point object
        if isinstance(val, Point):
            # If true, add x,y of val to respective x,y of Point
            self.x -= val.x
            self.y -= val.y
        else:
            # If false, add val to both x and y 
            self.x -= val
            self.y -= val


    def multiply(self, val):
        # Check if val is a Point object
        if isinstance(val, Point):
            # If true, multiply x,y of val with respective x,y of Point
            self.x *= val.x
            self.y *= val.y
        else:
            # If false, add val to both x,y of Point
            self.x *= val
            self.y *= val


    def divide(self, val):
        if isinstance(val, Point):
            self.x /= val.x
            self.y /= val.y
        else:
            self.x /= val
            self.y /= val


    def rotate_rad(self, angle, cor=0):
        """Rotate Point in positive counterclockwise direction.
        
        Rotation is done in radians, optionally around a specified 
        center of rotation. If no center of rotation is specified, 
        Point is rotated around origin (0,0).

        Args:
            angle (float): Rotation in radians.
            cor (obj:Point): Center of rotation (x,y).
        """
        # Calculate trig functions only once beforehand.
        c = math.cos(angle)
        s = math.sin(angle)

        self._rotate(c, s, cor)


    def rotate_deg(self, angle, cor=0):
        """Rotate Point in positive counterclockwise direction.

        Rotation is done in degrees, optionally around a specified 
        center of rotation. If no center of rotation is specified,
        Point is rotated around origin (0,0).

        Args:
            angle (float): Degrees of rotation.
            cor (obj:Point): Center of rotation (x,y).
        """
        # Convert degrees to radians
        angle = angle * math.pi / 180

        # Calculate trig functions
        c = math.cos(angle)
        s = math.sin(angle)

        self._rotate(c, s, cor)


    def _rotate(self, c, s, cor=0):
        """Rotate point in positive counterclockwise direction.

        Args:
            c (float): cosine of desired rotation angle.
            s (float): sine of desired rotation angle.
            cor (obj:Point): center of rotation (x,y).
        """
        # Separate calculation of rotation from trig functions
        # because sine and cosine don't change for same rotation angle
        # Wasteful to recalculate mutiple times when rotating e.g. a quad.
        p = Point(self.x, self.y)

        # Subtract center of rotation coords from Point, 
        # to rotate Point around origin (0,0).
        # After rotation is done, add back center of rotation coords.
        p.subtract(cor)

        # Positive Counterclockwise Rotation
        self.x = p.x * c - p.y * s 
        self.y = p.x * s + p.y * c
        self.add(cor)


class Line:
    """A line in a 2D cartesian coordinate system.
    
    Each line is described by a set of two points.
    """
    def __init__(self, p1=Point(), p2=Point()):
        self.points = [p1, p2]

    def add(self, val):
        for point in self.points:
            point.add(val)


class Triangle:
    """A triangle in a 2D cartesian coordinate system.

    Each triangle is described by a set of three points.
    """
    def __init__(self, 
                 p1=Point(), 
                 p2=Point(), 
                 p3=Point()):
        self.points = [p1, p2, p3]

    def add(self, val):
        for point in self.points:
            point.add(val)

class Quad:
    """A quad in a 2D cartesian coordinate system.

    Each quad is described by a set of four points.
    """
    def __init__(self, 
                 p1=Point(), 
                 p2=Point(), 
                 p3=Point(),
                 p4=Point()):
        self.points = [p1, p2, p3, p4]

    def add(self, val):
        for point in self.points:
            point.add(val)

