import ac

from color_palette import Colors
from config_handler import Config
from ac_data import ACGlobalData, ACCarData 
from drawables import Trace, PedalBar, SteeringWheel
from app_window import AppWindow
from ac_label import ACLabel
from ac_gl_utils import Point

# Initialize general object variables
cfg = None
ac_global_data = None
ac_car_data = None
app_window = None

# Trace drawable objects
throttle_trace = None
brake_trace = None
clutch_trace = None
steering_trace = None

# Timers
timer_60_hz = 0
timer_10_hz = 0
timer_trace = 0
trace_update_batch = 0 

PERIOD_60_HZ = 1 / 60
PERIOD_10_HZ = 1 / 10

# Pedal bars drawable objects
throttle_bar = None
brake_bar = None
clutch_bar = None
ffb_bar = None

# Wheel indicator drawable object
wheel_indicator = None

# Text labels
label_speed = 0
label_gear = 0


def acMain(ac_version):
    """Run upon startup of Assetto Corsa.
    
    Args:
        ac_version (str): Version of Assetto Corsa.
            AC passes this argument automatically.
    """
    # Read config
    global cfg
    cfg = Config()

    # Initialize ac data objects
    global ac_global_data, ac_car_data
    ac_global_data = ACGlobalData(cfg)
    ac_car_data = ACCarData(cfg)

    # Set up app window
    global app_window
    app_window = AppWindow(cfg)
    ac.addRenderCallback(app_window.id, app_render)

    # Initialize trace objects and add to drawables list
    global throttle_trace, brake_trace, clutch_trace, steering_trace
    if cfg.display_steering:
        steering_trace = Trace(cfg, ac_global_data, Colors.light_grey)
        app_window.add_drawable(steering_trace)
    if cfg.display_clutch:
        clutch_trace = Trace(cfg, ac_global_data, Colors.blue)
        app_window.add_drawable(clutch_trace)
    if cfg.display_throttle:
        throttle_trace = Trace(cfg, ac_global_data, Colors.green)
        app_window.add_drawable(throttle_trace)
    if cfg.display_brake:
        brake_trace = Trace(cfg, ac_global_data, Colors.red)
        app_window.add_drawable(brake_trace)

    # Initialize pedal bars objects and add to drawables list
    global throttle_bar, brake_bar, clutch_bar, ffb_bar
    throttle_bar = PedalBar(cfg, 1555, Colors.green)
    app_window.add_drawable(throttle_bar)
    brake_bar = PedalBar(cfg, 1480, Colors.red)
    app_window.add_drawable(brake_bar)
    clutch_bar = PedalBar(cfg, 1405, Colors.blue)
    app_window.add_drawable(clutch_bar)
    ffb_bar = PedalBar(cfg, 1630, Colors.grey)
    app_window.add_drawable(ffb_bar)

    # Initialize wheel indicator and add to drawables list
    global wheel_indicator
    wheel_indicator = SteeringWheel(cfg, Colors.yellow)
    app_window.add_drawable(wheel_indicator)

    # Initialize fonts
    ac.initFont(0, 'ACRoboto300', 0, 0)
    ac.initFont(0, 'ACRoboto700', 0, 0)

    # Set up labels
    global label_speed, label_gear
    label_speed = ACLabel(app_window.id, font='ACRoboto300', alignment='center')
    label_speed.fill_height(Point(1935 * cfg.app_scale, cfg.app_padding * cfg.app_height), 50 * cfg.app_scale)

    # Speed unit selection
    if cfg.use_kmh:
        label_speed.set_postfix(" km/h")
    else:
        label_speed.set_postfix(" mph")

    label_gear = ACLabel(app_window.id, font='ACRoboto700', alignment='center')
    label_gear.fit_height(Point(1935 * cfg.app_scale, (300 - 112) * cfg.app_scale), 224 * cfg.app_scale)


def acUpdate(deltaT):
    """Run every physics tick of Assetto Corsa.
    
    Args:
        deltaT (float): Time delta since last tick in seconds.
            Assetto Corsa passes this argument automatically.
    """
    global timer_60_hz, timer_10_hz
    global timer_trace
    global trace_update_batch

    # Update timers
    timer_60_hz += deltaT
    timer_10_hz += deltaT
    timer_trace += deltaT

    # Run on 10hz
    if timer_10_hz > PERIOD_10_HZ:
        timer_10_hz -= PERIOD_10_HZ

        # Update ac global data
        ac_global_data.update()

        # Set car id for car data
        ac_car_data.set_car_id(ac_global_data.focused_car)

        # Update text labels
        label_speed.set_text("{:.0f}".format(ac_car_data.speed))
        label_gear.set_text("{}".format(ac_car_data.gear_text))

    # Run on 60hz
    if timer_60_hz > PERIOD_60_HZ:
        timer_60_hz -= PERIOD_60_HZ

        # Update ac car data
        ac_car_data.update()

        # Update data for pedalbar and wheelindicator drawables
        wheel_indicator.update(ac_car_data.steering)
        throttle_bar.update(ac_car_data.throttle)
        brake_bar.update(ac_car_data.brake)
        clutch_bar.update(ac_car_data.clutch)

        # Set FFB bar to red if FFB is clipping (greater than 1)
        if ac_car_data.ffb < 1:
            ffb_bar.color = Colors.grey
            ffb_bar.update(ac_car_data.ffb)
        else:
            ffb_bar.color = Colors.red
            ffb_bar.update(1)

    # Update traces data in batches
    # This is done to spread out calc load over physics update ticks.
    if timer_trace > (1 / cfg.trace_sample_rate):
        trace_update_batch += 1

        if trace_update_batch == 1:
            if cfg.display_clutch:
                clutch_trace.update(ac_car_data.clutch)

        elif trace_update_batch == 2:
            if cfg.display_steering:
                steering_trace.update(ac_car_data.steering_normalized)

        elif trace_update_batch == 3:
            if cfg.display_throttle:
                throttle_trace.update(ac_car_data.throttle)

        else:
            if cfg.display_brake:
                brake_trace.update(ac_car_data.brake)
            
            # On final batch, reset counter and timer
            trace_update_batch = 0
            timer_trace -= (1 / cfg.trace_sample_rate)


def app_render(deltaT):
    """Run every rendered frame of Assetto Corsa.

    Args:
        deltaT (float): Time delta since last tick in seconds.
            Assetto Corsa passes this argument automatically.
    """
    app_window.render(deltaT)


def acShutdown():
    """Run on shutdown of Assetto Corsa"""
    # Update config if necessary
    if cfg.update_cfg:
        cfg.save()