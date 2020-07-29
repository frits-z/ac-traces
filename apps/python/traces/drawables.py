import ac
import acsys

from collections import deque

from ac_gl_utils import Point
from ac_gl_utils import Line
from ac_gl_utils import Triangle
from ac_gl_utils import Quad


class Trace:
    """Driver input trace drawable.

    Args:
        cfg (obj:Config): Object for app configuration.
        ac_global_data (obj:ACGlobalData): Object to retrieve Assetto Corsa
            data that is non-car specific.
        color (tuple): r,g,b,a on 0 to 1 scale.
    """
    def __init__(self, cfg, ac_global_data, color):
        self.cfg = cfg
        self.ac_global_data = ac_global_data

        self.time_window = self.cfg.trace_time_window
        self.sample_rate = self.cfg.trace_sample_rate
        self.sample_size = self.time_window * self.sample_rate

        self.color = color
        self.thickness = self.cfg.trace_thickness
        self.half_thickness = self.thickness / 2

        # Trace line starting point
        self.graph_origin = Point(
            self.cfg.app_height * self.cfg.app_padding + self.half_thickness,
            self.cfg.app_height * (1 - self.cfg.app_padding) - self.half_thickness)
        
        # Trace graph dimensions
        self.graph_height = self.cfg.app_height * (1 - 2 * self.cfg.app_padding) - self.thickness
        self.graph_width = self.cfg.app_height * 2.5 - self.thickness

        # Set up render queue and points deques.
        # self.render_queue is a deque of quads, iterated over to draw.
        # (2*sample_size - 1) deque length because there are:
        # N (sample size) data points and N-1 connecting lines between points
        self.render_queue = deque(maxlen=(2 * self.sample_size - 1))
        
        # self.points is a deque of data points, the current and the lag data point.
        # This is used in calculating the quad connecting the data points.
        self.points = deque(maxlen=2)

    def update(self, data_point):
        """Update trace render queue.

        Args:
            data_point (float): New point to add to the trace.
        """
        if self.ac_global_data.replay_time_multiplier > 0:
            # Update traces only if sim time multiplier is positive

            # Offset all points by one
            for point in self.points:
                point.x -= self.graph_width / (self.sample_size - 1)

            # Move all quads in render queue left by one unit
            for quad in self.render_queue:
                quad.points[0].x -= self.graph_width / (self.sample_size - 1)
                quad.points[1].x -= self.graph_width / (self.sample_size - 1)
                quad.points[2].x -= self.graph_width / (self.sample_size - 1)
                quad.points[3].x -= self.graph_width / (self.sample_size - 1)

            # Add new point
            p = Point(self.graph_origin.x + self.graph_width,
                      self.graph_origin.y - (data_point * self.graph_height))
            self.points.append(p.copy())

            p_lag = self.points[0]
            # Make connecting quad if previous point exists
            # Checked by seeing if points deque is length of two...
            if len(self.points) != 2:
                pass
            elif (p.x > p_lag.x) == (p.y > p_lag.y):
                # If x and y are both greater or smaller than lag x and y
                p1 = Point(p_lag.x + self.half_thickness,
                           p_lag.y - self.half_thickness)
                p2 = Point(p.x + self.half_thickness,
                           p.y - self.half_thickness)
                p3 = Point(p.x - self.half_thickness,
                           p.y + self.half_thickness)
                p4 = Point(p_lag.x - self.half_thickness,
                           p_lag.y + self.half_thickness)
                # Points of a triangle/quad must be passed in CCW order,
                # as this defines the front facing side.
                # Clockwise is back face, which gets culled.
                conn_quad = Quad(p4, p3, p2, p1)
                self.render_queue.append(conn_quad.copy())
            else:
                p1 = Point(p_lag.x - self.half_thickness,
                           p_lag.y - self.half_thickness)
                p2 = Point(p.x - self.half_thickness,
                           p.y - self.half_thickness)
                p3 = Point(p.x + self.half_thickness,
                           p.y + self.half_thickness)
                p4 = Point(p_lag.x + self.half_thickness,
                           p_lag.y + self.half_thickness)
                conn_quad = Quad(p4, p3, p2, p1)
                self.render_queue.append(conn_quad.copy())

            # Make a square around the data point
            p1 = Point(p.x - self.half_thickness,
                       p.y - self.half_thickness)
            p2 = Point(p.x + self.half_thickness,
                       p.y - self.half_thickness)
            p3 = Point(p.x + self.half_thickness,
                       p.y + self.half_thickness)
            p4 = Point(p.x - self.half_thickness,
                       p.y + self.half_thickness)
            square = Quad(p4, p3, p2, p1)
            self.render_queue.append(square.copy())

        elif self.ac_global_data.replay_time_multiplier == 0:
            # If sim time is paused, dont update traces, skip.
            pass
        else:
            # If sim time multiplier is negative, clear traces to empty defaults
            self.points.clear()
            self.render_queue.clear()
            
    def draw(self):
        """Draw trace object"""
        set_color(self.color)
        try:
            for quad in self.render_queue:
                ac.glBegin(acsys.GL.Quads)
                ac.glVertex2f(quad.points[0].x, quad.points[0].y)
                ac.glVertex2f(quad.points[1].x, quad.points[1].y)
                ac.glVertex2f(quad.points[2].x, quad.points[2].y)
                ac.glVertex2f(quad.points[3].x, quad.points[3].y)
                ac.glEnd()
        except Exception as e:
            ac.log("{app_name} - Error: \n{error}".format(app_name=self.cfg.app_name, error=e))


class PedalBar:
    """Driver pedal input bar drawable.

    Args:
        cfg (obj:Config): App configuration.
        origin_x (float): x origin point on full app scale
            to start drawing the pedal bar from.
        color (tuple): r,g,b,a on a 0-1 scale.
    """
    def __init__(self, cfg, origin_x, color):
        self.cfg = cfg
        self.color = color

        self.origin = Point(origin_x * self.cfg.app_scale,
                            450 * self.cfg.app_scale)
        self.width = self.cfg.app_height * self.cfg.app_padding
        # Height will be multiplied by pedal input.
        self.full_height = self.cfg.app_height * (1- (self.cfg.app_padding * 2))

        self.pedal_input = 0

    def update(self, pedal_input):
        """Update pedal input data.
        
        Args:
            pedal_input (float): Pedal input data to draw.
        """
        self.pedal_input = pedal_input

    def draw(self):
        """Draw pedal bar"""
        set_color(self.color)
        ac.glBegin(acsys.GL.Quads)
        ac.glVertex2f(self.origin.x, 
                      self.origin.y)
        ac.glVertex2f(self.origin.x + self.width,
                      self.origin.y)
        ac.glVertex2f(self.origin.x + self.width,
                      self.origin.y - (self.full_height * self.pedal_input))
        ac.glVertex2f(self.origin.x,
                      self.origin.y - (self.full_height * self.pedal_input))
        ac.glEnd()


class SteeringWheel:
    """Driver steering wheel input indicator drawable.
    
    Args:
        cfg (obj:Config): App configuration.
        color (tuple): r,g,b,a on a 0-1 scale.
    """
    def __init__(self, cfg, color):
        self.cfg = cfg
        self.color = color

        # Center of rotation coordinates of the steering wheel.
        self.origin = Point(1935 * self.cfg.app_scale,
                            300 * self.cfg.app_scale)
        
        # Radius to inside and outside of steering wheel rim.
        self.outer_radius = 150 * self.cfg.app_scale
        self.ratio_inner_outer_radius = 112 / 150
        self.inner_radius = self.outer_radius * self.ratio_inner_outer_radius

        # Build initial renderqueue based on straight wheel.
        # This will get rotated by updating the steering wheel angle.
        self.center_p_outer = Point(self.origin.x,
                                 self.origin.y - self.outer_radius)
        self.center_p_inner = Point(self.origin.x,
                                 self.origin.y - self.inner_radius)

        # Built on the basis of one starting line connecting the inside and
        # outside of the rim at the center. Copy the center line with rotation offsets, 
        # and build a base renderqueue of quads from it.
        self.start_line = Line(self.center_p_inner, self.center_p_outer)

        self.line_list = []
        self.base_quads = []
        self.offsets = [-0.2, -0.15, -0.1, -0.05, 0, 0.05, 0.1, 0.15, 0.2]
        for i, offset in enumerate(self.offsets):
            line = self.start_line.copy()
            line.rotate_rad(offset, self.origin)
            self.line_list.append(line)

            if i == 0:
                pass
            else:
                line_lag = self.line_list[i-1]

                p1 = Point(line.points[0].x, line.points[0].y)
                p2 = Point(line.points[1].x, line.points[1].y)
                p3 = Point(line_lag.points[1].x, line_lag.points[1].y)
                p4 = Point(line_lag.points[0].x, line_lag.points[0].y)
                quad = Quad(p1, p2, p3, p4)
                self.base_quads.append(quad)

        # Initialize empty renderqueue
        self.render_queue = []

    def update(self, angle):
        """Update steering wheel indicator.

        Args:
            angle (float): Steering wheel angle in radians.
        """
        _render_queue = []

        for quad in self.base_quads:
            new_quad = quad.copy()
            new_quad.rotate_rad(angle, self.origin)
            _render_queue.append(new_quad)

        self.render_queue = _render_queue

    def draw(self):
        """Draw steering wheel indicator"""
        set_color(self.color)
        for quad in self.render_queue:
            ac.glBegin(acsys.GL.Quads)
            ac.glVertex2f(quad.points[0].x, quad.points[0].y)
            ac.glVertex2f(quad.points[1].x, quad.points[1].y)
            ac.glVertex2f(quad.points[2].x, quad.points[2].y)
            ac.glVertex2f(quad.points[3].x, quad.points[3].y)
            ac.glEnd()


def set_color(rgba):
    """Apply RGBA color for GL drawing.

    Agrs:
        rgba (tuple): r,g,b,a on a 0-1 scale.
    """
    ac.glColor4f(rgba[0], rgba[1], rgba[2], rgba[3])
