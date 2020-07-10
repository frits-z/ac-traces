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

from traces_lib.sim_info import info

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



# # Colors
# colors = {
#     'throttle': {'r': 0.16, 'g': 1, 'b': 0, 'a': 1},
#     'brake': {'r': 1, 'g': 0.16, 'b': 0, 'a': 1},
#     'clutch': {'r': 0.16, 'g': 1, 'b': 1, 'a': 1},
#     'ffb': {'r': 0.35, 'g': 0.35, 'b': 0.35, 'a': 1},
#     'steer': {'r': 1, 'g': 0.8, 'b': 0, 'a': 1}
# }



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
    set_color(rgba)
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

    set_color(rgba)

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

    set_color(rgba)

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
    set_color(rgba)

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


def set_color(rgba):
    """Set RGBA color for GL drawing.

    Args:
        rgba (dict): r,g,b,a keys on 0-1 scale.

    """
    ac.glColor4f(rgba['r'], rgba['g'], rgba['b'], rgba['a'])
