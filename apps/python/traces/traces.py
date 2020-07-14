import ac
import acsys

import os
import sys
import platform
import math
import configparser

from collections import deque
from math import ceil

# Import Assetto Corsa shared memory library.
# Uses ctypes module, which is not included in AC python.
# Point to correct ctypes module based on platform architecture.
if platform.architecture()[0] == "64bit":
    sysdir = 'apps/python/traces/dll/stdlib64'
else:
    sysdir = 'apps/python/traces/dll/stdlib'

sys.path.insert(0, sysdir)
os.environ['PATH'] = os.environ['PATH'] + ";."

from lib.sim_info import info

from lib.ac_gl_utils import Point
from lib.ac_gl_utils import Line
from lib.ac_gl_utils import Triangle
from lib.ac_gl_utils import Quad


BASE_DIR = "apps/python/traces/"
CONFIG_REL_PATH = "config.ini"
config_file_path = BASE_DIR + CONFIG_REL_PATH


# Init objects
cfg = None
ac_data = None
app_window = None

traces_list = []
throttle_trace = None
brake_trace = None
clutch_trace = None

INITIALIZED = False

def acMain(ac_version):
    """Run upon startup of Assetto Corsa. """
    # Config should be first thing to load in AcMain.
    global cfg
    cfg = Config(config_file_path)

    global ac_data
    ac_data = ACData()

    # list of trace objects
    global traces_list
    global throttle_trace, brake_trace, clutch_trace
    # Initialize trace objects
    if cfg.display_throttle:
        throttle_trace = Trace(Colors.green)
        traces_list.append(throttle_trace)
    if cfg.display_brake:
        brake_trace = Trace(Colors.red)
        traces_list.append(brake_trace)
    if cfg.display_clutch:
        clutch_trace = Trace(Colors.blue)
        traces_list.append(clutch_trace)
    # Add steering...

    # Set up app window
    global app_window
    app_window = Renderer()

    global INITIALIZED
    INITIALIZED = True


def acUpdate(deltaT):
    """Run every physics tick of Assetto Corsa. """
    if not INITIALIZED:
        ac.log("Traces: Not yet initialized. Returning...")
        return
    global ac_data
    global traces_list
    # Update data
    ac_data.update(deltaT)

    # # Update trace objects
    # for trace in traces_list:
    #     trace[0].update(deltaT, trace[1])

    global throttle_trace, brake_trace, clutch_trace
    if cfg.display_throttle:
        throttle_trace.update(deltaT, ac_data.throttle)
    if cfg.display_brake:
        brake_trace.update(deltaT, ac_data.brake)
    if cfg.display_clutch:
        clutch_trace.update(deltaT, ac_data.clutch)


# GL Drawing
def app_render(deltaT):
    """Run every rendered frame of Assetto Corsa. """    
    app_window.render(deltaT)


class Config:
    """Handling of config information"""
    def __init__(self, file_path):
        """Set defaults and load config

        Args:
            file_path (str): config file path relative to Assetto Corsa
                installation root folder.
        """
        ac.log("Traces: Init Config") # TEMP
        self.file_path = file_path

        # Set app attributes that are non-configurable by user, therefore
        # don't appear in config file.
        self.app_name = "Traces"
        self.app_aspect_ratio = 4.27
        self.app_padding = 0.1 # Fraction of app height

        # Call load method
        self.load()

    def load(self):
        """Initialize config parser and load config"""
        ac.log("Traces: Load Config") # TEMP
        parser = configparser.ConfigParser()
        try:
            parser.read(self.file_path)
            self.app_height = parser.getint('GENERAL', 'app_height')
            self.time_window = parser.getint('GENERAL', 'time_window')
            self.traces_sample_rate = parser.getint('GENERAL', 'traces_sample_rate')
            self.use_kmh = parser.getboolean('GENERAL', 'use_kmh')

            self.display_throttle = parser.getboolean('TRACES', 'display_throttle')
            self.display_brake = parser.getboolean('TRACES', 'display_brake')
            self.display_clutch = parser.getboolean('TRACES','display_clutch')
            self.display_steering = parser.getboolean('TRACES', 'display_steering')
            # TODO add all other config items

        except Exception as e:
            ac.log("{app_name} - Error loading config:\n{error}".format(app_name=self.app_name, error=e))
            ac.log("{app_name} - Using config fallback defaults".format(app_name=self.app_name))
            self.fallback()

        self.app_width = self.app_height * self.app_aspect_ratio

    def fallback(self):
        # Defaults for adjustable items
        self.app_height = 500
        pass


class Renderer:
    def __init__(self):
        ac.log("Traces: Set up app window") # TEMP
        self.id = ac.newApp(cfg.app_name)
        ac.setSize(self.id, cfg.app_width, cfg.app_height)
        self.bg_texture_path = "apps/python/traces/img/bg.png"
        ac.setBackgroundTexture(self.id, self.bg_texture_path)
        ac.setBackgroundOpacity(self.id, 0)
        ac.drawBorder(self.id, 0)
        ac.setTitle(self.id, "")
        ac.setIconPosition(self.id, 0, -10000)

        ac.addRenderCallback(self.id, app_render)

    def render(self, deltaT):
        # When the user moves the window, the opacity is reset to default.
        # Therefore, opacity needs to be set to 0 every frame.
        ac.setBackgroundOpacity(self.id, 0)

        # ik denk dat dit werkt?
        for trace in traces_list:
            set_color(trace.color)
            for quad in trace.render_queue:
                ac.glBegin(acsys.GL.Quads)
                for point in quad.points:
                    ac.glVertex2f(point.x, point.y)
                ac.glEnd()


class ACData:
    """Handling ac data storing updating etc"""
    def __init__(self):
        ac.log("Traces: Init ACData") # TEMP
        self.speed = 0
        self.throttle = 0
        self.brake = 0
        self.clutch = 0
        self.steering = 0
        self.gear = 0
        self.ffb = 0
        self.focused_car = 0
        self.replay_time_multiplier = 1

        self.use_kmh = cfg.use_kmh

        # Timer
        self.timer_60_hz = 0
        self.period_60_hz = 1 / 60

    def update(self, deltaT):
        # Update timer
        self.timer_60_hz += deltaT

        if self.timer_60_hz > self.period_60_hz:
            self.timer_60_hz -= self.period_60_hz

            self.focused_car = ac.getFocusedCar()

            self.throttle = ac.getCarState(self.focused_car, acsys.CS.Gas)
            self.brake = ac.getCarState(self.focused_car, acsys.CS.Brake)
            self.clutch = 1 - ac.getCarState(self.focused_car, acsys.CS.Clutch)
            self.ffb = ac.getCarState(self.focused_car, acsys.CS.LastFF)
            self.steering = ac.getCarState(self.focused_car, acsys.CS.Steer) * math.pi / 180
            self.gear = ac.getCarState(self.focused_car, acsys.CS.Gear)

            # Add logic from cfg to select between MPH and KM/H
            if self.use_kmh:
                self.speed = ac.getCarState(self.focused_car, acsys.CS.SpeedKMH)
            else:
                self.speed = ac.getCarState(self.focused_car, acsys.CS.SpeedMPH)

            self.replay_time_multiplier = info.graphics.replayTimeMultiplier


class Trace:
    """Trace Object..."""
    def __init__(self, color):
        """Initialize Class

        Args:
            color (tuple): r,g,b,a on 0 to 1 scale
        """
        # Initialize double ended queue...
        # TODO change to grab this from config
        self.time_window = cfg.time_window
        self.sample_rate = cfg.traces_sample_rate
        self.sample_size = self.time_window * self.sample_rate
        self.data = deque([0] * self.sample_size, self.sample_size)

        self.color = color
        self.thickness = 1

        self.graph_origin = Point(
            cfg.app_height * cfg.app_padding,
            cfg.app_height * (1- cfg.app_padding))
        self.graph_height = cfg.app_height * (1 - 2 * cfg.app_padding)
        self.graph_width = cfg.app_height * 2.5
        self.trace_thickness = 1 # TODO DEPRECATED

        self.update_timer = 0
        self.update_timer_period = 1 / self.sample_rate

        # Calc fill render_queue with a list of quads, which are a list of points.
        self.render_queue = []

    def update(self, deltaT, new_data_point):
        # Update timer
        self.update_timer += deltaT

        if self.update_timer > self.update_timer_period:
            self.update_timer -= self.update_timer_period

            if ac_data.replay_time_multiplier > 0:
                # Update traces if sim time multiplier is positive
                self.data.append(new_data_point)
            elif ac_data.replay_time_multiplier == 0:
                # If sim time is paused, dont update traces, freeze.
                pass
            else:
                # If sim time multiplier is negative, clear traces to empty defaults
                self.data.extend([0] * self.sample_size)

            self.points = []

            for i, val in enumerate(self.data):
                p = Point(self.graph_origin.x 
                          + (self.graph_width * (i + 1) / self.sample_size),
                          self.graph_origin.y
                          - (val * self.graph_height))

                self.points.append(p.copy())

            self._render_queue = build_line_render_queue(self.points, self.thickness)
            self.render_queue = self._render_queue

def build_line_render_queue(points, thickness):
    """Build list of quads render queue for line with specified thickness.
    
    Args:
        points (list[obj:Point]): List of Point objects
        thickness (float): Line thickness in pixels

    Return:
        list[obj:Quad]: list of Quad objects
    """
    half_width = thickness / 2

    # Initialize render queue
    render_queue = []

    for i, p in enumerate(points):
        # Make a square
        p1 = Point(p.x - half_width,
                   p.y - half_width)
        p2 = Point(p.x + half_width,
                   p.y - half_width)
        p3 = Point(p.x + half_width,
                   p.y + half_width)
        p4 = Point(p.x - half_width,
                   p.y + half_width)
        square = Quad(p1, p2, p3, p4)
        render_queue.append(square.copy())
        
        p_lag = points[i-1]
        if i == 0:
            pass
        elif (p.x > p_lag.x) == (p.y > p_lag.y):
            # If x and y are both greater or smaller than lag x and y
            p1 = Point(p_lag.x + half_width,
                       p_lag.y - half_width)
            p2 = Point(p.x + half_width,
                       p.y - half_width)
            p3 = Point(p.x - half_width,
                       p.y + half_width)
            p4 = Point(p_lag.x - half_width,
                       p_lag.y + half_width)
            conn_quad = Quad(p1, p2, p3, p4)
            render_queue.append(conn_quad.copy())
        else:
            p1 = Point(p_lag.x - half_width,
                       p_lag.y - half_width)
            p2 = Point(p.x - half_width,
                       p.y - half_width)
            p3 = Point(p.x + half_width,
                       p.y + half_width)
            p4 = Point(p_lag.x + half_width,
                       p_lag.y + half_width)
            conn_quad = Quad(p1, p2, p3, p4)
            render_queue.append(conn_quad.copy())

    return render_queue


class Colors:
    """Class-level attributes with RGBA color tuples"""
    green = (0.16, 1, 0, 1)
    red = (1, 0.16, 0 , 1)
    blue = (0.16, 1, 1, 1)
    grey = (0.35, 0.35, 0.35, 1)
    yellow = (1, 0.8, 0, 1)


def set_color(rgba):
    """Apply RGBA color for GL drawing.

    Agrs:
        rgba (tuple): r,g,b,a on a 0-1 scale.
    """
    ac.glColor4f(rgba[0], rgba[1], rgba[2], rgba[3])
