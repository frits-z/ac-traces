import ac
import acsys

import os
import sys
import platform
import math

# Import Assetto Corsa shared memory library.
# It has a dependency on ctypes, which is not included in AC python version.
# Point to correct ctypes module based on platform architecture.
# First, get directory of the app, then add correct folder to sys.path.
app_dir = os.path.dirname(__file__)

if platform.architecture()[0] == "64bit":
    sysdir = os.path.join(app_dir, 'dll', 'stdlib64')
else:
    sysdir = os.path.join(app_dir, 'dll', 'stdlib')
# Python looks in sys.path for modules to load, insert new dir first in line.
sys.path.insert(0, sysdir)
os.environ['PATH'] = os.environ['PATH'] + ";."

from lib.sim_info import info


class ACGlobalData:
    """Handling all data from AC that is not car-specific.
    
    Args:
        cfg (obj:Config): App configuration.
    """
    def __init__(self, cfg):
        # Config object
        self.cfg = cfg

        # Data attributes
        self.focused_car = 0
        self.replay_time_multiplier = 1

    def update(self):
        """Update data."""
        self.focused_car = ac.getFocusedCar()
        self.replay_time_multiplier = info.graphics.replayTimeMultiplier


class ACCarData:
    """Handling all data from AC that is car-specific.
    
    Args:
        cfg (obj:Config): App configuration.
        car_id (int, optional): Car ID number to retrieve data from.
            Defaults to own car.
    """
    def __init__(self, cfg, car_id=0):
        self.cfg = cfg
        self.car_id = car_id

        # Initialize data attributes
        self.speed = 0
        self.throttle = 0
        self.brake = 0
        self.clutch = 0
        self.gear = 0
        self.steering = 0
        self.ffb = 0

        # Normalized steering for steering trace
        self.steering_normalized = 0.5
        self.steering_cap = self.cfg.trace_steering_cap * math.pi / 180

        self.gear_text = "N"
    
    def set_car_id(self, car_id):
        """Update car ID to retrieve data from.
        
        Args:
            car_id (int): Car ID number."""
        self.car_id = car_id

    def update(self):
        """Update data."""
        self.throttle = ac.getCarState(self.car_id, acsys.CS.Gas)
        self.brake = ac.getCarState(self.car_id, acsys.CS.Brake)
        self.clutch = 1 - ac.getCarState(self.car_id, acsys.CS.Clutch)
        self.ffb = ac.getCarState(self.car_id, acsys.CS.LastFF)
        self.steering = ac.getCarState(self.car_id, acsys.CS.Steer) * math.pi / 180
        self.gear = ac.getCarState(self.car_id, acsys.CS.Gear)

        if self.cfg.use_kmh:
            self.speed = ac.getCarState(self.car_id, acsys.CS.SpeedKMH)
        else:
            self.speed = ac.getCarState(self.car_id, acsys.CS.SpeedMPH)

        self.steering_normalized = 0.5 - (self.steering / (2 * self.steering_cap))
        if self.steering_normalized > 1:
            self.steering_normalized = 1
        elif self.steering_normalized < 0:
            self.steering_normalized = 0

        # Gear label
        if self.gear == 0:
            self.gear_text = "R"
        elif self.gear == 1:
            self.gear_text = "N"
        else:
            self.gear_text = str(self.gear - 1)