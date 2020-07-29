import os
import configparser

class Config:
    """App configuration. Load config upon intialization."""
    def __init__(self):
        # Set up config paths
        self.app_dir = os.path.dirname(__file__)
        self.cfg_file_path = os.path.join(self.app_dir, "config.ini")
        self.defaults_file_path = os.path.join(self.app_dir, "config_defaults.ini")

        # Set app attributes that are non-configurable by user, 
        # which therefore don't appear in the config file.
        self.app_name = "Traces"
        self.app_aspect_ratio = 4.27
        self.app_padding = 0.1 # Fraction of app height

        # Load config
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
                
        # Load attributes from config.
        # If option is missing, get option from defaults and replace. 
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

        # Generate attributes derived from config options
        self.app_width = self.app_height * self.app_aspect_ratio
        self.app_scale = self.app_height / 500

        # If update_cfg has been triggered (set to True), run save to update file.
        if self.update_cfg:
            self.save()
        

    def save(self):
        """Save config file"""
        with open(self.cfg_file_path, 'w') as cfgfile:
            self.cfg_parser.write(cfgfile)


    def getfloat(self, section, option):
        """Get float variable from config.

        If missing from config, grab from defaults and save it to config.

        Args:
            section (str): Section in config file
            options (str): Option with specified section
        """
        try:
            value = self.cfg_parser.getfloat(section, option)
        except:
            value = self.defaults_parser.getfloat(section, option)
            self.cfg_parser.set(section, option, str(value))
            self.update_cfg = True
        self.__setattr__(option, value)


    def getbool(self, section, option):
        """Get boolean variable from config.

        If missing from config, grab from defaults and save it to config.

        Args:
            section (str): Section in config file
            options (str): Option with specified section
        """        
        try:
            value = self.cfg_parser.getboolean(section, option)
        except:
            value = self.defaults_parser.getboolean(section, option)
            self.cfg_parser.set(section, option, str(value))
            self.update_cfg = True
        self.__setattr__(option, value)


    def getint(self, section, option):
        """Get integer variable from config.

        If missing from config, grab from defaults and save it to config.

        Args:
            section (str): Section in config file
            options (str): Option with specified section
        """        
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
        """Get string variable from config.

        If missing from config, grab from defaults and save it to config.

        Args:
            section (str): Section in config file
            options (str): Option with specified section
        """
        try: 
            value = self.cfg_parser.get(section, option)
        except:
            value = self.defaults_parser.get(section, option)
            self.cfg_parser.set(section, option, str(value))
            self.update_cfg = True
        self.__setattr__(option, value)
