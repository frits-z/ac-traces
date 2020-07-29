import ac

class AppWindow:
    """Main window of the app.
    
    Args:
    cfg (obj:Config): Config object used to set
        attributes for the app window.
    """
    def __init__(self, cfg):
        # Config data
        self.cfg = cfg
        
        # Set up app window
        self.id = ac.newApp(self.cfg.app_name)
        ac.setSize(self.id, self.cfg.app_width, self.cfg.app_height)
        self.bg_texture_path = "apps/python/traces/img/bg.png"
        ac.setBackgroundTexture(self.id, self.bg_texture_path)
        ac.setBackgroundOpacity(self.id, 0)
        ac.drawBorder(self.id, 0)
        ac.setTitle(self.id, "")
        ac.setIconPosition(self.id, 0, -10000)

        # Initialize empty list of drawable objects.
        self.drawables = []

    def add_drawable(self, obj):
        """Add drawable object to list of drawables"""
        if obj not in self.drawables:
            self.drawables.append(obj)

    def remove_drawable(self, obj):
        """Remove drawable object from list of drawables"""
        if obj in self.drawables:
            self.drawables.remove(obj)

    def render(self, deltaT):
        """Draw graphics elements on the app window.

        Args:
            deltaT (float): Time delta since last tick in seconds.
                Assetto Corsa passes this argument automatically.

        This method calls the draw method on each object in the list of drawables.
        This method should be called on render callback of Assetto Corsa.
        """
        # When the user moves the window, the opacity is reset to default.
        # Therefore, opacity needs to be set to 0 every frame.
        ac.setBackgroundOpacity(self.id, 0)

        for drawable in self.drawables:
            drawable.draw()

