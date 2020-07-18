import ac
import acsys

import os
import sys
import platform
import math
import configparser

from collections import deque

# TODO I dont use this anymore, I think. Need to double check.
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
DEFAULTS_REL_PATH = "config_defaults.ini"
config_file_path = BASE_DIR + CONFIG_REL_PATH
defaults_file_path = BASE_DIR + DEFAULTS_REL_PATH

# Init objects
cfg = None
ac_data = None
app_window = None

traces_list = []
throttle_trace = None
brake_trace = None
clutch_trace = None
steering_trace = None

timer1 = 0
timer2 = 0

throttle_bar = None
brake_bar = None
clutch_bar = None
ffb_bar = None

wheel_indicator = None

INITIALIZED = False 

label_speed = 0
label_gear = 0


def acMain(ac_version):
    """Run upon startup of Assetto Corsa."""
    # Config should be first thing to load in AcMain.
    global cfg
    cfg = Config(config_file_path, defaults_file_path)

    # Initialize ac_data object
    global ac_data
    ac_data = ACData()

    # Initialize trace objects
    global traces_list
    global throttle_trace, brake_trace, clutch_trace, steering_trace
    if cfg.display_steering:
        steering_trace = Trace(Colors.grey)
        traces_list.append(steering_trace)
    if cfg.display_clutch:
        clutch_trace = Trace(Colors.blue)
        traces_list.append(clutch_trace)
    if cfg.display_throttle:
        throttle_trace = Trace(Colors.green)
        traces_list.append(throttle_trace)
    if cfg.display_brake:
        brake_trace = Trace(Colors.red)
        traces_list.append(brake_trace)

    # Initialize pedal bars objects
    global throttle_bar, brake_bar, clutch_bar, ffb_bar
    throttle_bar = PedalBar(1555, Colors.green)
    brake_bar = PedalBar(1480, Colors.red)
    clutch_bar = PedalBar(1405, Colors.blue)
    ffb_bar = PedalBar(1630, Colors.grey)

    # Initialize wheel indicator objects
    global wheel_indicator
    wheel_indicator = SteeringWheel(Colors.yellow)

    # Set up app window
    global app_window
    app_window = Renderer()

    ac.initFont(0, 'ACRoboto300', 0, 0)
    ac.initFont(0, 'ACRoboto700', 0, 0)

    # Set up labels
    global label_speed, label_gear
    label_speed = ACLabel(app_window.id, 
                          Point(1935 * cfg.app_scale, 
                                cfg.app_padding * cfg.app_height - ((1/3) * 50 * cfg.app_scale)),
                          font='ACRoboto300',
                          size=50 * 1.4 * cfg.app_scale,
                          alignment='center')
    if cfg.use_kmh:
        label_speed.set_postfix(" km/h")
    else:
        label_speed.set_postfix(" mph")

    label_gear = ACLabel(app_window.id,
                         Point(1935 * cfg.app_scale,
                               (300 - 112) * cfg.app_scale),
                         font='ACRoboto700',
                         size= 224 * 0.84 * cfg.app_scale,
                         alignment='center')

    global INITIALIZED
    INITIALIZED = True


def acUpdate(deltaT):
    """Run every physics tick of Assetto Corsa. """
    if not INITIALIZED:
        ac.log("Traces: Not yet initialized. Returning...")
        return
    global ac_data
    global traces_list
    # Update data (Shouldnt do this every tick.., also probably dont need global ac_data or global traces_list ? 
    ac_data.update(deltaT)

    global timer1, timer2

    timer1 += deltaT
    timer2 += deltaT
    if timer1 > (1 / cfg.trace_sample_rate):
        timer1 -= (1 / cfg.trace_sample_rate)

        if cfg.display_clutch:
            clutch_trace.update(ac_data.clutch)
        if cfg.display_steering:
            steering_trace.update(ac_data.steering_normalized)
        if cfg.display_throttle:
            throttle_trace.update(ac_data.throttle)
        if cfg.display_brake:
            brake_trace.update(ac_data.brake)

    if timer2 > (1 / 60):
        timer2  -= 1 / 60
        wheel_indicator.update(ac_data.steering)
        throttle_bar.update(ac_data.throttle)
        brake_bar.update(ac_data.brake)
        clutch_bar.update(ac_data.clutch)

        if ac_data.ffb < 1:
            ffb_bar.color = Colors.grey
            ffb_bar.update(ac_data.ffb)
        else:
            ffb_bar.color = Colors.red
            ffb_bar.update(1)

        label_speed.set_text("{:.0f}".format(ac_data.speed))
        label_gear.set_text("{}".format(ac_data.gear_text))



# GL Drawing
def app_render(deltaT):
    """Run every rendered frame of Assetto Corsa. """    
    app_window.render(deltaT)

# TODO acShutdown function. For Saving CFG.
def acShutdown():
    # TEMP
    ac.log("Traces: Preparing for shutdown...")
    if cfg.update_cfg:
        cfg.save()

class Config:
    """Handling of config information"""
    def __init__(self, cfg_file_path, defaults_file_path):
        """Set defaults and load config

        Args:
            file_path (str): config file path relative to Assetto Corsa
                installation root folder.
        """
        # TODO Docstrings
        self.cfg_file_path = cfg_file_path
        self.defaults_file_path = defaults_file_path

        # Set app attributes that are non-configurable by user, 
        # which therefore don't appear in the config file.
        self.app_name = "Traces"
        self.app_aspect_ratio = 4.27
        self.app_padding = 0.1 # Fraction of app height

        # Call load method
        self.update_cfg = False
        self.load()

    def load(self):
        """Initialize config parser and load config"""
        # Load config file parser
        self.cfg_parser = configparser.ConfigParser()
        self.cfg_parser.read(self.cfg_file_path)
        # Load config defaults file parser
        self.defaults_parser = configparser.ConfigParser(inline_comment_prefixes=";")
        self.defaults_parser.read(self.defaults_file_path)

        # Loop over sections in defaults. If any are missing in cfg, add them.
        for section in self.defaults_parser.sections():
            if not self.cfg_parser.has_section(section):
                self.cfg_parser.add_section(section)
                
        # Load attributes from config
        self.getint('GENERAL', 'app_height')
        self.getbool('GENERAL', 'use_kmh')

        self.getbool('TRACES', 'display_throttle')
        self.getbool('TRACES', 'display_brake')
        self.getbool('TRACES', 'display_clutch')
        self.getbool('TRACES', 'display_steering')
        self.getint('TRACES', 'trace_time_window')
        self.getint('TRACES', 'trace_sample_rate')
        self.getfloat('TRACES', 'trace_thickness')
        self.getfloat('TRACES', 'trace_steering_cap')

        # Generate attributes derived from config inputs
        self.app_width = self.app_height * self.app_aspect_ratio
        self.app_scale = self.app_height / 500

        # If update_cfg has been triggered (set to True), run save to update file.
        if self.update_cfg:
            self.save()
        

    def save(self):
        # TEMP
        ac.log("Traces: Saving Config...")
        with open(self.cfg_file_path, 'w') as cfgfile:
            self.cfg_parser.write(cfgfile)


    def getfloat(self, section, option):
        try:
            value = self.cfg_parser.getfloat(section, option)
        except:
            value = self.defaults_parser.getfloat(section, option)
            self.cfg_parser.set(section, option, str(value))
            self.update_cfg = True
        self.__setattr__(option, value)


    def getbool(self, section, option):
        try:
            value = self.cfg_parser.getboolean(section, option)
        except:
            value = self.defaults_parser.getboolean(section, option)
            self.cfg_parser.set(section, option, str(value))
            self.update_cfg = True
        self.__setattr__(option, value)


    def getint(self, section, option):
        try:
            value = self.cfg_parser.getint(section, option)
        except:
            try:
                value = int(self.cfg_parser.getfloat(section, option))
            except:
                value = self.defaults_parser.getint(section, option)
            self.cfg_parser.set(section, option, str(value))
            self.update_cfg = True
        self.__setattr__(option, value)


    def getstr(self, section, option):
        try: 
            value = self.cfg_parser.get(section, option)
        except:
            value = self.defaults_parser.get(section, option)
            self.cfg_parser.set(section, option, str(value))
            self.update_cfg = True
        self.__setattr__(option, value)


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

        # Draw traces
        for trace in traces_list:
            trace.draw()

        # Draw pedal bars
        throttle_bar.draw()
        brake_bar.draw()
        clutch_bar.draw()
        ffb_bar.draw()

        # Draw wheel
        wheel_indicator.draw()


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

        # Normalized steering for steering trace
        self.steering_normalized = 0.5
        self.steering_cap = cfg.trace_steering_cap * math.pi / 180

        # Gear text for use as label.
        self.gear_text = "N"

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

            if self.use_kmh:
                self.speed = ac.getCarState(self.focused_car, acsys.CS.SpeedKMH)
            else:
                self.speed = ac.getCarState(self.focused_car, acsys.CS.SpeedMPH)

            self.replay_time_multiplier = info.graphics.replayTimeMultiplier

            self.steering_normalized = 0.5 - (self.steering / (2 * self.steering_cap))
            if self.steering_normalized > 1:
                self.steering_normalized = 1
            elif self.steering_normalized < 0:
                self.steering_normalized = 0

            # Set up gear label
            if self.gear == 0:
                self.gear_text = "R"
            elif self.gear == 1:
                self.gear_text = "N"
            else:
                self.gear_text = str(self.gear - 1)


class Trace:
    """Trace Object..."""
    def __init__(self, color):
        """Initialize Class

        Args:
            color (tuple): r,g,b,a on 0 to 1 scale
        """
        # Initialize double ended queue...
        self.time_window = cfg.trace_time_window
        self.sample_rate = cfg.trace_sample_rate
        self.sample_size = self.time_window * self.sample_rate

        self.color = color
        self.thickness = cfg.trace_thickness
        self.half_thickness = self.thickness / 2

        self.graph_origin = Point(
            cfg.app_height * cfg.app_padding + self.half_thickness,
            cfg.app_height * (1 - cfg.app_padding) - self.half_thickness)
        self.graph_height = cfg.app_height * (1 - 2 * cfg.app_padding) - self.thickness
        self.graph_width = cfg.app_height * 2.5 - self.thickness

        # TODO DEPRECATED ? 
        self.update_timer = 0
        self.update_timer_period = 1 / self.sample_rate

        # Calc fill render_queue with a list of quads, which are a list of points.
        # self.render_queue = []
        # 2*size - 1 because n=size points and n=size-1 lines between points

        #USE CLEAR METHODS!!!
        self.render_queue = deque(maxlen=(2 * self.sample_size - 1))
        self.points = deque(maxlen=2)

    def update(self, data_point):
        if ac_data.replay_time_multiplier > 0:
            # Update traces if sim time multiplier is positive

            # Offset all current points by one
            for point in self.points:
                point.x -= self.graph_width / (self.sample_size - 1)

            # Move all quads one slot to the left. 
            # Actually.... renderqueue is really the only place I need a
            # deque with long length...
            # I don't need a big one for the points or data. For the data only need two.
            # ALSO!!!!! Using deques is actually smart for getting lag variables
            for quad in self.render_queue:
                quad.points[0].x -= self.graph_width / (self.sample_size - 1)
                quad.points[1].x -= self.graph_width / (self.sample_size - 1)
                quad.points[2].x -= self.graph_width / (self.sample_size - 1)
                quad.points[3].x -= self.graph_width / (self.sample_size - 1)

            # Add new point
            p = Point(self.graph_origin.x + self.graph_width,
                    self.graph_origin.y
                    - (data_point * self.graph_height))
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

            # Make a square
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

        elif ac_data.replay_time_multiplier == 0:
            # If sim time is paused, dont update traces, freeze.
            pass
        else:
            # If sim time multiplier is negative, clear traces to empty defaults
            # SHOULD JUST CLEAR RENDER QUEUE!!!
            self.points.clear()
            self.render_queue.clear()
            
    def draw(self):
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
            ac.log("{app_name} - Error: \n{error}".format(app_name=cfg.app_name, error=e))


class PedalBar:
    """DOCSTRING HERE

    """
    def __init__(self, origin_x, color):
        self.color = color

        self.origin = Point(origin_x * cfg.app_scale,
                            450 * cfg.app_scale)
        self.width = cfg.app_height * cfg.app_padding
        # Height will be multiplied by pedal input.
        self.full_height = cfg.app_height * (1- (cfg.app_padding * 2))

        self.pedal_input = 0

    def update(self, pedal_input):
        self.pedal_input = pedal_input

    def draw(self):
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
    def __init__(self, color):
        self.color = color
        # Center of rotation?
        self.origin = Point(1935 * cfg.app_scale,
                            300 * cfg.app_scale)
        self.outer_radius = 150 * cfg.app_scale
        self.ratio_inner_outer_radius = 112 / 150
        self.inner_radius = self.outer_radius * self.ratio_inner_outer_radius

        # Build basic renderqueue... With update I will rotate the quads in renderqueue...
        self.center_p_outer = Point(self.origin.x,
                                 self.origin.y - self.outer_radius)
        self.center_p_inner = Point(self.origin.x,
                                 self.origin.y - self.inner_radius)

        # Maybe build it up as a collection of lines...
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

        self.render_queue = []

    def update(self, angle):
        _render_queue = []

        for quad in self.base_quads:
            new_quad = quad.copy()
            new_quad.rotate_rad(angle, self.origin)
            _render_queue.append(new_quad)

        self.render_queue = _render_queue

    def draw(self):
        set_color(self.color)
        for quad in self.render_queue:
            ac.glBegin(acsys.GL.Quads)
            ac.glVertex2f(quad.points[0].x, quad.points[0].y)
            ac.glVertex2f(quad.points[1].x, quad.points[1].y)
            ac.glVertex2f(quad.points[2].x, quad.points[2].y)
            ac.glVertex2f(quad.points[3].x, quad.points[3].y)
            ac.glEnd()


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


class ACLabel:
    def __init__(self, window_id, position, text=" ", font=None, italic=0, size=None, color=None, alignment='left', prefix="", postfix=""):
        """Initialize Assetto Corsa text label.

        Args:
            window_id (obj:Renderer.id):
            position (obj:Point):
            text (str):
            font (str): Custom font name
            italics (0, 1): 1 for italics, 0 for regular.
            color (tuple): r,g,b,a on a 0-1 scale.
            size (int): Font size.
            alignment (str): "left", "center", "right"
            prefix (str): Prefix before main text.
            postfix (str): Postfix after main text.
        """
        # Create label
        self.id = ac.addLabel(window_id, text)
        # Set position
        self.set_position(position)

        if font is not None: 
            self.set_custom_font(font, italic)
        if size is not None: 
            self.set_font_size(size)
        if color is not None: 
            self.set_color(color)

        self.set_alignment(alignment)

        self.prefix = prefix
        self.postfix = postfix
        self.set_text(text)

    def set_position(self, position):
        ac.setPosition(self.id, position.x, position.y)

    def set_prefix(self, prefix):
        self.prefix = prefix

    def set_postfix(self, postfix):
        self.postfix = postfix

    def set_text(self, text):
        text = self.prefix + text + self.postfix
        ac.setText(self.id, text)

    def set_alignment(self, alignment='left'):
        ac.setFontAlignment(self.id, alignment)

    def set_font_size(self, size):
        """KUNOS FONTSIZE IS IN PIXELS, NOT PT.
        Therefore, vertically it appears to scale linearly..."""
        ac.setFontSize(self.id, size)

    def set_custom_font(self, font, italic=0):
        ac.setCustomFont(self.id, font, italic, 0)

    def set_color(self, color):
        """Set Color for Label.

        Args:
            color (tuple): r,g,b,a on a 0-1 scale.
        """
        ac.setFontColor(self.id, color[0], color[1], color[2], color[3])