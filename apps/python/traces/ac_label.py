import ac
from ac_gl_utils import Point

class ACLabel:
    """Initialize Assetto Corsa text label.

    Args:
        window_id (obj:Renderer.id):
        position (obj:Point): Set x, y positon of label by passing a Point object.
            Optional. Defaults to 0, 0.
        text (str):
        font (str): Custom font name
        italics (0, 1): 1 for italics, 0 for regular.
        color (tuple): r,g,b,a on a 0-1 scale.
        size (int): Font size.
        alignment (str): "left", "center", "right"
        prefix (str): Prefix before main text.
        postfix (str): Postfix after main text.
    """
    def __init__(self, window_id, position=Point(), text=" ", font=None, italic=0, size=None, color=None, alignment='left', prefix="", postfix=""):
        # Create label
        self.id = ac.addLabel(window_id, "")
        # Set position
        self.set_position(position)
        # Set text
        self.prefix = prefix
        self.postfix = postfix
        self.set_text(text)
        # Set alignment
        self.set_alignment(alignment)
        # Optional items
        if font is not None: 
            self.set_custom_font(font, italic)
        if size is not None: 
            self.set_font_size(size)
        if color is not None: 
            self.set_color(color)

    def fill_height(self, position, height):
        """Set text label to position and fill height, may overflow vertically.
        
        Args:
            position (obj:Point): Point object with x,y coords.
            height (float): Height in pixels that the text label should fill.
        
        Important! Designed for Roboto font family.
        """
        # Calculate font size based on box height
        font_size = 1.4 * height
        # Adjust y pos. 
        position.y -= (1/3) * height
        self.set_font_size(font_size)
        self.set_position(position)

    def fit_height(self, position, height):
        """Set text label to position and fit label centered in given height with adequate spacing.
        
        Args:
            position (obj:Point): Point object with x,y coords.
            height (float): Height in pixels that the text label should be centered fit within.
            
        Important! Designed for Roboto font family.
        """
        # Calculate font size based on box height
        font_size = 0.84 * height
        # No need to make adjustment to position.
        self.set_font_size(font_size)
        self.set_position(position)

    def set_position(self, position):
        """Set label position.

        Args:
            position (obj:Point): Point object with x,y coords.
        """
        ac.setPosition(self.id, position.x, position.y)

    def set_prefix(self, prefix):
        """Set label prefix.

        Args:
            prefix (str): Label prefix.
        """
        self.prefix = prefix

    def set_postfix(self, postfix):
        """Set label postfix.

        Args:
            postfix (str): Label postfix.
        """
        self.postfix = postfix

    def set_text(self, text):
        """Set label text, making use of set pre/postfixes.

        Args:
            text (str): Label text.
        """
        text = self.prefix + text + self.postfix
        ac.setText(self.id, text)

    def set_alignment(self, alignment='left'):
        """Set text horizontal alignment

        Args:
            alignment (str): 'left', 'center', 'right'.
                defaults to left.
        """
        ac.setFontAlignment(self.id, alignment)

    def set_font_size(self, size):
        """Set text label font size.

        Args:
            size (float): Fontsize in PIXELS (not pt)

        Important: Fontsize in Assetto Corsa is done in pixels, not pt.
        Therefore vertically it scales linearly.
        """
        ac.setFontSize(self.id, size)

    def set_custom_font(self, font, italic=0):
        """Set custom font for text label.

        Args:
            font (str): Name of the font, must be initialized.
            italic (0/1): Optional, italics yes/no.
        """
        ac.setCustomFont(self.id, font, italic, 0)

    def set_color(self, color):
        """Set Color for Label.

        Args:
            color (tuple): r,g,b,a on a 0-1 scale.
        """
        ac.setFontColor(self.id, color[0], color[1], color[2], color[3])