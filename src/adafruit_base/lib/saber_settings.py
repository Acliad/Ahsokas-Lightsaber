import json
import storage

def rgb_to_hsv(rgb):
    """
    Convert RGB values to HSV values.

    Args:
        rgb (tuple): The RGB values as a tuple of three integers between 0 and 1.0.

    Returns:
        tuple: The corresponding HSV values as a tuple of three floats between 0 and 1.0.
    """
    r, g, b = rgb
    max_value = max(r, g, b)
    min_value = min(r, g, b)
    delta = max_value - min_value

    if delta == 0:
        h = 0
    elif max_value == r:
        h = (g - b) / delta % 6
    elif max_value == g:
        h = (b - r) / delta + 2
    else:
        h = (r - g) / delta + 4

    h *= 60
    if h < 0:
        h += 360

    if max_value == 0:
        s = 0
    else:
        s = delta / max_value

    v = max_value

    return [h / 360, s, v]

class SaberSettings:
    """A simple class to save and retrieve saber settings."""
    
    def __init__(self, settings_path) -> None:
        """
        Initializes a new instance of the SaberSettings class.

        Args:
            settings_path (str): The path to the settings file.

        Returns:
            None
        """
        self.settings_path = settings_path
        self.settings = {'blade_color': None, 'volume': None}
        self._load_settings()

    def _load_settings(self) -> None:
            """
            Load the settings from the settings file.

            This method reads the settings file and loads the settings into the `settings` attribute. If no file exists,
            it creates a new settings file with the current settings

            """
            try:
                with open(self.settings_path, "r") as f:
                    self.settings = json.load(f)
            except OSError:
                self.save_settings()

    def save_settings(self, path=None) -> None:
        """
        Saves the settings to a JSON file.

        Args:
            path (str, optional): The path to the JSON file. If not provided, the path provided during initialization
            will be used. This overwrites the loaded settings file.

        Returns:
            None
        """
        storage.remount("/", False)
        if path:
            self.settings_path = path
        with open(self.settings_path, "w") as f:
            json.dump(self.settings, f)
        storage.remount("/", True)
        
    @property
    def blade_color(self) -> list:
        return self.settings.get('blade_color', None)
    
    @blade_color.setter
    def blade_color(self, color) -> None:
        # Ensure that color is a list or tuple
        if not isinstance(color, (list, tuple)):
            raise ValueError("Color must be a list or tuple.")
        self.settings['blade_color'] = list(color)

    @property
    def volume(self) -> float:
        return self.settings.get('volume', None)
    
    @volume.setter
    def volume(self, volume) -> None:
        self.settings['volume'] = volume