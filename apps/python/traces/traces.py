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



# Start configparser
config = configparser.ConfigParser()
configfile = "apps/python/traces/config.ini"
config.read(configfile)

# Initialize app_info, dict in which basic app info is stored.
app_info = {}
app_info['name'] = "Traces"

try:
    app_info['height'] = config.getint('GENERAL', 'app_height')
    app_info['time_window'] = config.getint('GENERAL', 'time_window')
    app_info['traces_sample_rate'] = config.getint('GENERAL', 'traces_sample_rate')
except Exception as error:
    app_info['height'] = 150
    ac.log("{}: app_height Error: {}".format(app_info['name'], str(error)))

app_info['aspect_ratio'] = 4.27
app_info['title'] = "" 
app_info['padding'] = 0.1
app_info['width'] = app_info['height'] * app_info['aspect_ratio']
app_info['scale'] = app_info['height'] / 500

# Initialize empty dict in which the text labels are stored.
labels = {}

# Initialize empty dict in which fetched Assetto Corsa data is stored.
ac_data = {}
ac_data['speed'] = 0
ac_data['gear'] = 0
ac_data['throttle'] = 0
ac_data['brake'] = 0
ac_data['clutch'] = 0
ac_data['ffb'] = 0
ac_data['steer'] = 0
ac_data['time_multiplier'] = 1


# Initialize traces deques
deque_length = app_info['time_window'] * app_info['traces_sample_rate']
traces = {}
traces['throttle'] = deque([0] * deque_length, deque_length)
traces['brake'] = deque([0] * deque_length, deque_length)
traces['clutch'] = deque([0] * deque_length, deque_length)
# TODO can also add steering angle. 


# Timers
data_timer_60_hz = 0
PERIOD_60_HZ = 1 / 60

traces_calc_timer = 0
traces_calc_hz = 1 / app_info['traces_sample_rate']

# Colors
colors = {
    'throttle': {
        'r': 0.16,
        'g': 1,
        'b': 0,
        'a': 1
    },
    'brake': {
        'r': 1,
        'g': 0.16,
        'b': 0,
        'a': 1
    },
    'clutch': {
        'r': 0.16,
        'g': 1,
        'b': 1,
        'a': 1
    },
    'ffb': {
        'r': 0.35,
        'g': 0.35,
        'b': 0.35,
        'a': 1
    },
    'steer': {
        'r': 1,
        'g': 0.8,
        'b': 0,
        'a': 1
    }
}



# Init objects
cfg = None
ac_data = None






def acMain(ac_version):
    """Run upon startup of Assetto Corsa. """
    global app_info, app_window
    global labels
    global wheel_ring

    # Initialize app window
    app_window = ac.newApp(app_info['name'])
    ac.setSize(
            app_window, 
            app_info['width'], 
            app_info['height']
        )
    background = "apps/python/traces/img/bg.png"
    ac.setBackgroundTexture(app_window, background)
    ac.setBackgroundOpacity(app_window, 0)
    ac.drawBorder(app_window, 0)
    ac.setTitle(app_window, app_info['title'])
    ac.setIconPosition(app_window, 0, -10000)

    # run onFormRender every render call
    ac.addRenderCallback(app_window, onFormRender)

    # Calculate fontsize based on padding and app height
    fontsize = 20

    # Start the left-aligned text labels
    labels['speed'] = ac.addLabel(app_window, "100 km/h")
    ac.setFontSize(labels['speed'], fontsize)
    ac.setPosition(labels['speed'], 10, 10)

    labels['gear'] = ac.addLabel(app_window, "G")
    ac.setFontSize(labels['gear'], fontsize)
    ac.setPosition(labels['gear'], 10, 50)

    labels['time'] = ac.addLabel(app_window, "T")
    ac.setFontSize(labels['time'], fontsize)
    ac.setPosition(labels['time'], 10, 100)


    wheel_ring = ac.newTexture("apps/python/traces/img/wheel_ring_texture.png")


    # Config should be first thing to load in AcMain.
    global cfg
    cfg = Config(config_file_path)

    global ac_data
    ac_data = ACData()


def acUpdate(deltaT):
    """Run every physics tick of Assetto Corsa. """
    global app_info
    global ac_data
    global traces

    global data_timer_60_hz
    global traces_calc_timer

    global shift_timer
    
    # Update timers
    data_timer_60_hz += deltaT
    traces_calc_timer += deltaT



    # Fetch data at 60 hz
    if data_timer_60_hz > PERIOD_60_HZ:
        # Reset timer
        data_timer_60_hz -= PERIOD_60_HZ

        ac_data['focused_car'] = ac.getFocusedCar()

        ac_data['time_multiplier'] = info.graphics.replayTimeMultiplier

        # TODO Add logic for kph / mph selection.

        # Any lag variables
        ac_data['gear_lag'] = ac_data['gear']

        ac_data['speed'] = ac.getCarState(ac_data['focused_car'], acsys.CS.SpeedKMH)
        ac_data['gear'] = ac.getCarState(ac_data['focused_car'], acsys.CS.Gear)
        ac_data['throttle'] = ac.getCarState(ac_data['focused_car'], acsys.CS.Gas)
        ac_data['brake'] = ac.getCarState(ac_data['focused_car'], acsys.CS.Brake)
        ac_data['clutch'] = 1 - ac.getCarState(ac_data['focused_car'], acsys.CS.Clutch)
        ac_data['ffb'] = ac.getCarState(ac_data['focused_car'], acsys.CS.LastFF)
        ac_data['steer'] = ac.getCarState(ac_data['focused_car'], acsys.CS.Steer) * math.pi / 180

        if ac_data['gear'] != ac_data['gear_lag']:
            shift_timer = 1/4


    if traces_calc_timer > traces_calc_hz:
        # Reset timer
        traces_calc_timer -= traces_calc_hz

        if ac_data['time_multiplier'] > 0:
            # Update traces if sim time multiplier is positive
            traces['throttle'].append(ac_data['throttle'])
            traces['brake'].append(ac_data['brake'])
            traces['clutch'].append(ac_data['clutch'])
        elif ac_data['time_multiplier'] == 0:
            # If sim time is paused, dont update traces, freeze.
            pass
        else:
            # If sim time multiplier is negative, clear traces to empty defaults
            traces['throttle'].extend([0] * deque_length)
            traces['brake'].extend([0] * deque_length)
            traces['clutch'].extend([0] * deque_length)


    # Update text data lables
    ac.setText(labels['speed'], "{:.2f}%".format(ac_data['time_multiplier']))
    ac.setText(labels['gear'], "{} T".format(ac_data['throttle']))
    ac.setText(labels['time'], "{} B".format(ac_data['brake']))


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
            # TODO add all other config items

        except Exception as e:
            ac.log("{app_name} - Error loading config:\n{error}".format(app_name=self.app_name, error=e))
            ac.log("{app_name} - Using config fallback defaults".format(app_name=self.app_name))
            self.fallback()

    def fallback(self):
        # Defaults for adjustable items
        self.app_height = 500
        pass


class ACData:
    """Handling ac data storing updating etc"""
    def __init__(self, use_kmh):
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

        self.use_kmh = use_kmh

        # Timer
        self.timer_60_hz = 0
        self.period_60_hz = 1 / 60

    def update(self, deltaT):
        # Update timer
        self.timer_60_hz += deltaT

        if self.timer_60_hz > self.period_60_hz:
            self.timer_60_hz -= self.period_60_hz

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


# Example of how it should work...
my_traces_list = [[throttle_obj, data.throttle], 'brake', 'steering']

for trace in my_traces_list:
    trace.update(...)


class Trace:
    """Trace Object..."""
    def __init__(self, time_window, sample_rate, color):
        """Initialize Class

        Args:
            color (tuple): r,g,b,a on 0 to 1 scale
        """
        # Initialize double ended queue...
        self.time_window = time_window
        self.sample_rate = sample_rate
        self.sample_size = self.time_window * self.sample_rate
        self.data = deque([0] * self.sample_size, self.sample_size)

        self.color = color

        self.graph_origin = Point(
            cfg.app_height * cfg.app_padding,
            cfg.app_height * (1- cfg.app_padding))
        self.graph_height = cfg.app_height * (1 - 2 * cfg.app_padding)
        self.graph_width = cfg.app_height * 2.5
        self.trace_width = 1

        self.update_timer = 0
        self.update_timer_period = 1 / self.sample_rate

        # Calc fill render_queue with a list of quads, which are a list of points.
        self.render_queue = []

    def update(self, deltaT, new_data_point):
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

            # Start with clear raw render queue
            self.render_queue_raw = []

            p_new = Point(0,0)

            # Iterate over data deque
            for i, val in enumerate(self.data):
                # Lag points
                p_lag = p_new.copy()

                p_new.x = (self.graph_origin.x 
                           + (self.graph_width * (i + 1) / self.sample_size))
                p_new.y = (self.graph_origin.y
                           - (val * self.graph_height))

                # Calc square for point p_new with a w,h of 2 * trace_width
                # And add to render queue list
                p1 = Point(p_new.x - self.trace_width,
                           p_new.y - self.trace_width)
                p2 = Point(p_new.x + self.trace_width,
                           p_new.y - self.trace_width)
                p3 = Point(p_new.x + self.trace_width,
                           p_new.y + self.trace_width)
                p4 = Point(p_new.x - self.trace_width,
                           p_new.y + self.trace_width)
                square = Quad(p1.copy(), p2.copy(), p3.copy(), p4.copy())

                self.render_queue_raw.append(square.copy())

                if i == 0:
                    pass
                elif val > trace[i-1]:
                    # If new datapoint is higher than previous
                    p1 = Point(p_lag.x - self.trace_width,
                               p_lag.y - self.trace_width)
                    p2 = Point(p_new.x - self.trace_width,
                               p_new.y - self.trace_width)
                    p3 = Point(p_new.x + self.trace_width,
                               p_new.y + self.trace_width)
                    p4 = Point(p_lag.x + self.trace_width,
                               p_lag.y + self.trace_width)
                    # Make connecting quad between squares... add to render queue
                    conn_quad = Quad(p1, p2, p3, p4)
                    self.render_queue_raw.append(conn_quad.copy())
                else:
                    p1 = Point(p_lag.x + self.trace_width,
                               p_lag.y - self.trace_width)
                    p2 = Point(p_new.x + self.trace_width,
                               p_new.y - self.trace_width)
                    p3 = Point(p_new.x - self.trace_width,
                               p_new.y + self.trace_width)
                    p4 = Point(p_lag.x - self.trace_width,
                               p_lag.y + self.trace_width)
                    # Make connecting quad between squares... add to render queue
                    conn_quad = Quad(p1, p2, p3, p4)
                    self.render_queue_raw.append(conn_quad.copy())

            # Once building the raw render queue has completed,
            # it replaces the actual render queue.
            self.render_queue = self.render_queue_raw



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
        p1 = Point(p[i].x - half_width,
                   p[i].y - half_width)
        p2 = Point(p[i].x + half_width,
                   p[i].y - half_width)
        p3 = Point(p[i].x + half_width,
                   p[i].y + half_width)
        p4 = Point(p[i].x - half_width,
                   p[i].y + half_width)
        square = Quad(p1, p2, p3, p4)
        render_queue.append(square.copy())
        
        if i == 0:
            pass
        elif (p[i].x > p[i-1].x) == (p[i].y > p[i-1].y):
            # If x and y are both greater or smaller than lag x and y
            p1 = Point(p[i-1].x + half_width,
                       p[i-1].y - half_width)
            p2 = Point(p[i].x + half_width,
                       p[i].y - half_width)
            p3 = Point(p[i].x - half_width,
                       p[i].y + half_width)
            p4 = Point(p[i-1].x - half_width,
                       p[i-1].y + half_width)
            conn_quad = Quad(p1, p2, p3, p4)
            render_queue.append(conn_quad.copy())
        else:
            p1 = Point(p[i-1].x - half_width,
                       p[i-1].y - half_width)
            p2 = Point(p[i].x - half_width,
                       p[i].y - half_width)
            p3 = Point(p[i].x + half_width,
                       p[i].y + half_width)
            p4 = Point(p[i-1].x + half_width,
                       p[i-1].y + half_width)
            conn_quad = Quad(p1, p2, p3, p4)
            render_queue.append(conn_quad.copy())

    return render_queue



class PedalBar:
    """Pedal bar..."""
    pass


class Colors:
    """Class-level attributes with RGBA color tuples"""
    green = (0.16, 1, 0, 1)
    red = (1, 0.16, 0 , 1)
    blue = (0.16, 1, 1, 1)
    grey = (0.35, 0.35, 0.35, 1)
    yellow = (1, 0.8, 0, 1)


# GL Drawing
def onFormRender(deltaT):
    """Run every rendered frame of Assetto Corsa. """
    global shift_timer


    # When the user moves the window, the opacity is reset to default.
    # Therefore, opacity needs to be set to 0 every frame.
    ac.setBackgroundOpacity(app_window, 0)

    # Update text data lables
    # ac.setText(labels['speed'], "{:.2f}%".format(ac_data['time_multiplier']))
    # ac.setText(labels['gear'], "{} T".format(ac_data['throttle']))
    # ac.setText(labels['time'], "{} B".format(ac_data['brake']))


    if shift_timer > 0:
        shift_timer -= deltaT
        ac.glColor4f(1,1,1,4*shift_timer)    
        ac.glQuadTextured(
            1785 * app_info['scale'],
            150 * app_info['scale'],
            300 * app_info['scale'],
            300 * app_info['scale'],
            wheel_ring
        )

    draw_trace(traces['clutch'], colors['clutch'])
    draw_trace(traces['brake'], colors['brake'])
    draw_trace(traces['throttle'], colors['throttle'])

    # Draw pedals
    draw_pedal_bar(1405 * app_info['scale'], ac_data['clutch'], colors['clutch'])
    draw_pedal_bar(1480 * app_info['scale'], ac_data['brake'], colors['brake'])
    draw_pedal_bar(1555 * app_info['scale'], ac_data['throttle'], colors['throttle'])

    # Draw FFB
    if ac_data['ffb'] < 1:
        draw_pedal_bar(1630 * app_info['scale'], ac_data['ffb'], colors['ffb'])
    else:
        draw_pedal_bar(1630 * app_info['scale'], 1, colors['brake'])

    # Draw wheel
    draw_wheel_indicator(ac_data['steer'], colors['steer'])

def draw_pedal_bar(x_origin, pedal_input, rgba):
    set_color_legacy(rgba)
    pedals_w = app_info['height'] * app_info['padding']
    pedals_h = - app_info['height'] * (1 - (app_info['padding'] * 2)) * pedal_input
    pedals_y = 450 * app_info['scale']
    pedals_x = x_origin
    ac.glQuad(pedals_x, pedals_y, pedals_w, pedals_h)


def draw_trace_legacy(trace, rgba, x_offset=0, y_offset=0):
    startpoint_x = 300
    startpoint_y = 200
    windowheight = 150
    windowwidth = 800

    # per ac.glBegin/ac.glEnd max supported verts is 32, meaning 31 lines. 
    # On any call except first call it should start off with the lag value of where it left off with the previous call...
    MAX_LINES_PER_CALL = 31

    # calc render calls needed
    n_rendercalls = ceil(deque_length / MAX_LINES_PER_CALL)

    set_color_legacy(rgba)

    for call_n in range(n_rendercalls):
        # Start render call
        ac.glBegin(1)

        # If not the first call, start off with lag where previous call left off, to make sure it gets connected
        if call_n != 0:
            # start with lag
            i = call_n * MAX_LINES_PER_CALL - 1

            # Add vert
            x_pos = startpoint_x + (windowwidth * (i + 1) / deque_length) + x_offset
            y_pos = startpoint_y - (trace[i] * windowheight) - y_offset
            ac.glVertex2f(x_pos, y_pos)

        remaining_verts = deque_length - call_n * MAX_LINES_PER_CALL
        call_size = min(remaining_verts, MAX_LINES_PER_CALL)

        for n in range(call_size):
            # Calculate index
            i = call_n * MAX_LINES_PER_CALL + n

            # Add vert
            x_pos = startpoint_x + (windowwidth * (i + 1) / deque_length) + x_offset
            y_pos = startpoint_y - (trace[i] * windowheight) - y_offset
            ac.glVertex2f(x_pos, y_pos)

        # End rendercall
        ac.glEnd()


def draw_trace(trace, rgba, width=1):
    startpoint_x = app_info['height'] * app_info['padding']
    startpoint_y = app_info['height'] * (1 - app_info['padding'])
    windowheight = app_info['height'] * (1 - 2 * app_info['padding'])
    windowwidth = app_info['height'] * 2.5

    set_color_legacy(rgba)

    x_new = 0
    y_new = 0

    for i, v in enumerate(trace):
        # Previous values
        x_lag = x_new
        y_lag = y_new

        # Calculate new ones
        x_new = startpoint_x + (windowwidth * (i + 1) / deque_length)
        y_new = y_new = startpoint_y - (v * windowheight)

        # Draw square
        ac.glBegin(3)
        # Top left
        ac.glVertex2f(x_new - width, y_new - width)
        # Top right
        ac.glVertex2f(x_new + width, y_new - width)
        # Bottom right
        ac.glVertex2f(x_new + width, y_new + width)
        # Bottom left
        ac.glVertex2f(x_new - width, y_new + width)
        ac.glEnd()

        if i == 0:
            pass
        else:
            if v > trace[i-1]:
                # Upward movement....
                ac.glBegin(3)
                # Lag top left
                ac.glVertex2f(x_lag - width, y_lag - width)
                # New top left
                ac.glVertex2f(x_new - width, y_new - width)
                # New bottom right
                ac.glVertex2f(x_new + width, y_new + width)
                # Lag bottom right
                ac.glVertex2f(x_lag + width, y_lag + width)
                ac.glEnd()
            else:
                # Downward/flat movement...
                ac.glBegin(3)
                # Lag top right
                ac.glVertex2f(x_lag + width, y_lag - width)
                # New top right
                ac.glVertex2f(x_new + width, y_new - width)
                # New bottom left
                ac.glVertex2f(x_new - width, y_new + width)
                # Lag bottom left
                ac.glVertex2f(x_lag - width, y_lag + width)
                ac.glEnd()


def draw_wheel_indicator(angle, rgba):
    set_color_legacy(rgba)

    origin = {'x': 1935 * app_info['scale'],
              'y': 300 * app_info['scale']}
    outer_radius = 150 * app_info['scale']
    ratio_inner_outer_radius = 112 / 150
    inner_radius = outer_radius * ratio_inner_outer_radius

    inner_new = 0
    outer_new = 0

    offsets = [-0.2, -0.15, -0.1, -0.05, 0, 0.05, 0.1, 0.15, 0.2]
    for i, n in enumerate(offsets):
        inner_lag = inner_new
        outer_lag = outer_new

        # Calculate new points
        inner_new = polar_to_cartesian_coords(origin, inner_radius, angle + n)
        outer_new = polar_to_cartesian_coords(origin, outer_radius, angle + n)

        if i == 0:
            pass
        else:
            # Draw the thing
            ac.glBegin(3)
            ac.glVertex2f(inner_lag['x'], inner_lag['y'])
            ac.glVertex2f(outer_lag['x'], outer_lag['y'])
            ac.glVertex2f(outer_new['x'], outer_new['y'])
            ac.glVertex2f(inner_new['x'], inner_new['y'])
            ac.glEnd()


def polar_to_cartesian_coords(origin, radius, phi):
    """Convert polar coordinate system to cartesian coordinate system around specified origin.

    Args:
        origin (dict): x,y origin cartesian coordinates.
        radius (float): length of the point to the origin.
        phi (float): Radians rotation (relative to north).

    Returns:
        dict: x,y cartesian coordinates.
    """
    # Add half-pi offset on phi because it takes the x-axis as a zero point.
    # This would be east for the wind directions application. Need to have north as zero point.
    phi -= 0.5 * math.pi
    cartesian_x = radius * math.cos(phi) + origin['x']
    cartesian_y = radius * math.sin(phi) + origin['y']
    return {'x': cartesian_x, 'y': cartesian_y}


def set_color_legacy(rgba):
    """Set RGBA color for GL drawing.

    Args:
        rgba (dict): r,g,b,a keys on 0-1 scale.

    """
    ac.glColor4f(rgba['r'], rgba['g'], rgba['b'], rgba['a'])


def set_color(rgba):
    """Apply RGBA color for GL drawing.

    Agrs:
        rgba (tuple): r,g,b,a on a 0-1 scale.
    """
    ac.glColor4f(rgba[0], rgba[1], rgba[2], rgba[3])


