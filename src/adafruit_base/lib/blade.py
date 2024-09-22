import audiocore
import neopixel
import time
import os
import random
from time_utils import ticks_diff, ticks_ms

class WaveBuffer:
    """
    A class representing a simple wave buffer.

    Attributes:
        played (bool): Indicates whether the buffer has been played.
        buffer: The buffer data.
    """

    def __init__(self, audio_i2s) -> None:
        self.played: bool = False
        self.buffer = None
        self.audio_i2s = audio_i2s

    def load_buffer(self, path: str) -> None:
        """Load a WAV file into the buffer."""
        try:
            wave_file = open(path, "rb")
            self.buffer = audiocore.WaveFile(wave_file)
            self._buffer_used = False
        except:
            return
        
    def play_buffer(self, loop=False):
        """
        Play the buffer.
        :param loop: if True, sound will repeat indefinitely (until interrupted
                    by another sound).
        """
        self.audio_i2s.stop()
        self.audio_i2s.play(self.buffer, loop=loop)
        self._buffer_used = True

    def stop(self) -> None:
        """Stops the player. Equivalent to calling `audio_i2s.stop()`.
        """
        self.audio_i2s.stop()

    @property
    def playing(self) -> bool:
        """Return True if the buffer is playing."""
        return self.audio_i2s.playing
    
    @property
    def buffer_used(self) -> bool:
        """Return True if the buffer has started playing. I.e. the buffer has been loaded into memory and can be updated
        again."""
        return self._buffer_used
    

class Blade:
    RED = (255, 0, 0)
    YELLOW = (125, 255, 0)
    GREEN = (0, 255, 0)
    CYAN = (0, 125, 255)
    BLUE = (0, 0, 255)
    PURPLE = (125, 0, 255)
    WHITE = (255, 255, 255)

    def __init__(self, 
                 neopixels, 
                 audio_i2s,
                 extend_time_seconds=1.230, 
                 retract_time_seconds=1.230, 
                 color=CYAN) -> None:
        # General blade properties
        self.extend_ticks_ms = extend_time_seconds * 1000.0
        self.retract_ticks_ms = retract_time_seconds * 1000.0
        self.transition_start_ticks_ms = 0 # ticks_ms() when a transition from on to off or off to on started
        self.mode = 'off'
        self.last_mode = 'off'
        
        # Neopixel properties
        self.neopixels = neopixels
        self.num_pixels_on = 0
        self.color = color
        self.num_total_pixels = len(self.neopixels)

        # Sound properties
        # This is used to prevent hiccups in the sound when the next sound is loaded.
        self.wav_buffer = WaveBuffer(audio_i2s)
        self.startup_sound_paths = self._get_wavs_in_folder('startup')
        self.shutdown_sound_paths = self._get_wavs_in_folder('shutdown')
        self.run_sound_paths = self._get_wavs_in_folder('run')
        self.swing_sound_paths = self._get_wavs_in_folder('swing')
        self.clash_sound_paths = self._get_wavs_in_folder('clash')
        self.config_sound_paths = self._get_wavs_in_folder('config')
        

    def startup(self) -> None:
        """Turn on the blade."""
        self.mode = 'startup'
        # Adjust the start time based on how many pixels are already on. Probably not the best way to do this, 
        # but it's simple and works for now.
        effective_elapsed_ms = int(self.num_pixels_on / self.num_total_pixels * self.extend_ticks_ms)
        self.transition_start_ticks_ms = ticks_diff(ticks_ms(), effective_elapsed_ms)

        self.wav_buffer.load_buffer(random.choice(self.startup_sound_paths))
        self.wav_buffer.play_buffer()
    
    def shutdown(self) -> None:
        """Turn off the blade."""
        self.mode = 'shutdown'
        # Adjust the start time based on how many pixels are already on. Probably not the best way to do this, 
        # but it's simple and works for now.
        effective_elapsed_ms = int((self.num_total_pixels - self.num_pixels_on) / self.num_total_pixels * \
                                                                                                self.retract_ticks_ms)
        self.transition_start_ticks_ms = ticks_diff(ticks_ms(), effective_elapsed_ms)

        self.wav_buffer.load_buffer(random.choice(self.shutdown_sound_paths))
        self.wav_buffer.play_buffer()

    def update(self) -> None:
        """Update the blade based on the current mode."""

        # Stop the sound if we're transitioning from config mode to another mode.
        if self.last_mode == "config" and self.mode != "config":
            self.wav_buffer.stop()
            
        if self._mode == 'off':
            pass
        elif self._mode == 'startup':
            self._update_startup()
        elif self._mode == 'run':
            self._update_run()
        elif self._mode == 'swing':
            self._update_swing()
        elif self._mode == 'shutdown':
            self._update_shutdown()
        elif self._mode == 'config':
            self._update_config()

        self.last_mode = self.mode
        
    def _update_startup(self) -> None:
        time_elapsed_ms = ticks_diff(ticks_ms(), self.transition_start_ticks_ms)
        self.num_pixels_on = min(int(time_elapsed_ms / self.extend_ticks_ms * self.num_total_pixels), 
                                 self.num_total_pixels)

        self.neopixels[0:self.num_pixels_on] = [self.color] * self.num_pixels_on
        self.neopixels.show()
        if self.num_pixels_on == len(self.neopixels):
            # Load the buffer here with the run sound to prevent hiccups in the sound.
            self.wav_buffer.load_buffer(random.choice(self.run_sound_paths))
            self.mode = 'run'

    def _update_shutdown(self) -> None:
        time_elapsed = ticks_diff(ticks_ms(), self.transition_start_ticks_ms)
        self.num_pixels_on = max(
                self.num_total_pixels - int(time_elapsed / self.retract_ticks_ms * self.num_total_pixels), 
                0
            )

        self.neopixels[self.num_pixels_on:] = [[0, 0, 0]] * (self.num_total_pixels - self.num_pixels_on)
        self.neopixels.show()
        if self.num_pixels_on == 0:
            self.mode = 'off'

    def _update_run(self) -> None:
        if self.wav_buffer.buffer_used:
            # Load the buffer here if a previous state hasn't already loaded it.
            self.wav_buffer.load_buffer(random.choice(self.run_sound_paths))
        if not self.wav_buffer.playing:
            self.wav_buffer.play_buffer(loop=True)

    def _update_swing(self) -> None:
        if self.last_mode != 'swing':
            self.wav_buffer.load_buffer(random.choice(self.swing_sound_paths))
            self.wav_buffer.play_buffer()
            # Load the run sound here to prevent hiccups in the sound.
            self.wav_buffer.load_buffer(random.choice(self.run_sound_paths))
        elif not self.wav_buffer.playing:
            self.mode = 'run'

    def _update_config(self) -> None:
        if self.last_mode != 'config':
            self.wav_buffer.stop()
            self.wav_buffer.load_buffer(random.choice(self.config_sound_paths))
            self.wav_buffer.play_buffer(loop=True)


    def _get_wavs_in_folder(self, folder: str) -> list:
        wavs = []
        for filename in os.listdir(f"/sounds/{folder}"):
            if filename.lower().endswith('.wav') and not filename.startswith('.'):
                wavs.append(f"/sounds/{folder}/{filename}")

        return wavs
    
    @property
    def mode(self) -> str:
        """Get the current mode of the blade."""
        return self._mode

    @mode.setter
    def mode(self, mode: str) -> None:
        """Set the mode of the blade. Valid modes are:
        - off
        - startup
        - run
        - swing
        - shutdown
        - config

        config mode is used to change the audio and color settings of the blade. This mode will load a sound in the
        config folder and play it indefinitely until the mode is changed. The user is responsible for changing the
        color of the blade or audio volume as needed.

        Args:
            mode (str): mode to set the blade to.
        """
        self._mode = mode

    @property
    def color(self) -> tuple:
        """Get the current color of the blade."""
        return self._color
    
    @color.setter
    def color(self, color: tuple) -> None:
        """Set the color of the blade."""
        self._color = color
        # Update the color of the neopixels
        for i in range(self.num_pixels_on):
            if self.neopixels[i] != [0, 0, 0]:
                self.neopixels[i] = color
        self.neopixels.show()