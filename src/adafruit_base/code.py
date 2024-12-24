# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import board # type: ignore
import audiobusio
import rotaryio
import alarm
import colorsys
import saber_settings
import time
from adafruit_debouncer import Button
from digitalio import DigitalInOut, Direction, Pull
import neopixel
import adafruit_lis3dh
from blade import Blade

# CUSTOMIZE SENSITIVITY HERE: smaller numbers = more sensitive to motion
ENCODER_SENSITIVITY = 0.01
HIT_THRESHOLD = 120
SWING_THRESHOLD = 145
VOLUME_MODE_COLOR = (255, 100, 0)

DEFAULT_BLADE_COLOR = (0, 100, 255) # Cyan
DEFAULT_VOLUME = 1.0

# The time the lightsaber is in off mode before going to deep sleep
SLEEP_TIMEOUT_TIME_SECONDS = 10*60

# The amount of time to debounce button presses
BUTTON_DEBOUNCE_TIME_S = 0.035

# Load settings
blade_settings = saber_settings.SaberSettings("/settings.json")
# Ensure defaults are set (this should probably be done in the settings class with an optional defaults dict)
if blade_settings.blade_color is None:
    blade_settings.blade_color = DEFAULT_BLADE_COLOR
# TODO: Volume not yet implemented
if blade_settings.volume is None:
    blade_settings.volume = DEFAULT_VOLUME
# Values need to be normalized for colorsys
blade_hsv = saber_settings.rgb_to_hsv([x / 255 for x in blade_settings.blade_color]) 
blade_volume = blade_settings.volume

# Set up the neopixels
num_pixels = 129
pixels = neopixel.NeoPixel(board.EXTERNAL_NEOPIXELS, num_pixels, auto_write=False)
pixels.brightness = 0.8

# enable external power pin
# provides power to the neopixels
external_power = DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = Direction.OUTPUT
external_power.value = True
# Make sure the neopixels are off
pixels.fill(0)
pixels.show()

# Create the audio out object
audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)

# Power button
power_btn_pin = DigitalInOut(board.D13)
power_btn_pin.direction = Direction.INPUT
power_btn_pin.pull = Pull.UP
switch = Button(power_btn_pin, short_duration_ms = 20, long_duration_ms = 1000, interval = BUTTON_DEBOUNCE_TIME_S)

# Rotary encoder
encoder = rotaryio.IncrementalEncoder(board.D12, board.D11)
last_rotary_position = encoder.position
def get_encoder_delta():
    global last_rotary_position
    position = encoder.position
    delta = position - last_rotary_position
    last_rotary_position = position
    return delta

# Accelerometer
i2c = board.I2C()
int1 = DigitalInOut(board.ACCELEROMETER_INTERRUPT)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, int1=int1)
# Accelerometer Range (can be 2_G, 4_G, 8_G, 16_G)
lis3dh.range = adafruit_lis3dh.RANGE_2_G
lis3dh.set_tap(1, HIT_THRESHOLD)

# Set up the blade
blade = Blade(pixels, audio, color=blade_settings.blade_color)

# Main state machine
def animate_hue_config():
    temp_hsv = blade_hsv.copy()
    hue_delta = ENCODER_SENSITIVITY
    while hue_delta <= 1:
        temp_hsv[0] = (blade_hsv[0] + hue_delta)%1
        blade.color = colorsys.hsv_to_rgb(temp_hsv[0], temp_hsv[1], temp_hsv[2])
        blade.update()
        hue_delta += ENCODER_SENSITIVITY
        time.sleep(0.001)
    
def animate_sat_config():
    temp_hsv = blade_hsv.copy()
    sat_delta = ENCODER_SENSITIVITY
    while sat_delta <= 1:
        temp_hsv[1] = (blade_hsv[1] + sat_delta)%1
        blade.color = colorsys.hsv_to_rgb(temp_hsv[0], temp_hsv[1], temp_hsv[2])
        blade.update()
        sat_delta += ENCODER_SENSITIVITY
        time.sleep(0.001)

def animate_volume_config():
    # Linearly inerpolate between the current color and VOLUME_MODE_COLOR
    step_size = 50 # Number of steps to take to get to the final color
    temp_color = blade.color
    slopes = [(VOLUME_MODE_COLOR[i] - temp_color[i]) / step_size for i in range(3)]
    while [round(c) for c in temp_color] != list(VOLUME_MODE_COLOR):
        temp_color = [min(max(temp_color[i] + slopes[i], 0), 255) for i in range(3)]
        blade.color = [round(c) for c in temp_color]
        blade.update()
        # time.sleep(0.001)

time_turned_off = time.monotonic()
config_pages = ['hue', 'saturation', 'volume']
active_config_page = config_pages[0]
last_config_page = None

# Track the state of the state machine. Modes are:
#   - startup: The lightsaber is starting up
#   - run: The lightsaber is running normally
#   - shutdown: The lightsaber is shutting down
#   - retracted: The lightsaber is retracted but can be turned on
#   - off: The lightsaber is off and can go to sleep. Requires a long press to turn on
#   - config: The lightsaber is in configuration mode

mode = 'off' # Default to off
while True:
    switch.update()
    blade.update()
    # startup
    if mode == 'startup':
        blade.startup()
        mode = 'run'
    # default
    elif mode == 'run':
        x, y, z = lis3dh.acceleration
        accel_total = x * x + y * y + z * z 
        if accel_total >= SWING_THRESHOLD and blade.mode == "run":
            blade.mode = 'swing'
        if switch.short_count > 0:
            mode = 'shutdown'
        if switch.long_press:
            print("Config...")
            # Call get_encoder_delta() to clear the encoder state
            get_encoder_delta()
            mode = 'config'
            blade.mode = 'config'
    # turn off
    elif mode == 'shutdown':
        blade.shutdown()
        mode = 'retracted'
        time_turned_off = time.monotonic()
    # go to startup from retracted if button is pressed
    elif mode == 'retracted':
        if switch.short_count > 0:
            external_power.value = True
            mode = 'startup'
        # Turn off if the saber has been retracted for a while
        if time.monotonic() - time_turned_off > SLEEP_TIMEOUT_TIME_SECONDS:
            mode = 'off'
    # go to sleep
    elif mode == 'off':
        # From off mode, we want require a long press to turn the saber back on
        if switch.long_press:
            mode = 'startup'
        # Go to sleep if the saber has been off for a while
        if time.monotonic() - time_turned_off > SLEEP_TIMEOUT_TIME_SECONDS:
            print("Going to sleep...")
            external_power.value = False
            # Set up the sleep alarm
            power_btn_pin.deinit()
            edge_alarm = alarm.pin.PinAlarm(board.D13, value=False, pull=True)
            alarm.exit_and_deep_sleep_until_alarms(edge_alarm)

    # config state
    elif mode == 'config':
        encoder_increment = get_encoder_delta() * ENCODER_SENSITIVITY
        if active_config_page == 'hue':
            if last_config_page != active_config_page:
                animate_hue_config()
            
            if encoder_increment:
                blade_hsv[0] += (encoder_increment)%1
                blade.color = colorsys.hsv_to_rgb(blade_hsv[0], blade_hsv[1], blade_hsv[2])
        elif active_config_page == 'saturation':
            if last_config_page != active_config_page:
                animate_sat_config()
            
            if encoder_increment:
                # Saturation of 0 causes the blade to turn off. Set minimum to 0.01
                blade_hsv[1] = min(max(blade_hsv[1] + encoder_increment, 0.01), 1)
                blade.color = colorsys.hsv_to_rgb(blade_hsv[0], blade_hsv[1], blade_hsv[2])
        elif active_config_page == 'volume':
            if last_config_page != active_config_page:
                animate_volume_config()
            if encoder_increment:
                # TODO: implement volume control. I know that this is currenlty bad practice because they name doesn't
                # quite match the function. It will be fixed (or rather completely replaced) in a future commit.
                # Making blade_volume a float just so the rest of the code is consistent with volume being a float
                blade_volume = float(not blade.muted) 
                blade.muted = blade_volume

        last_config_page = active_config_page
        
        if switch.long_press:
            # Save the updated settings
            blade.color = colorsys.hsv_to_rgb(blade_hsv[0], blade_hsv[1], blade_hsv[2])
            blade_settings.blade_color = colorsys.hsv_to_rgb(blade_hsv[0], blade_hsv[1], blade_hsv[2])
            blade_settings.volume = blade_volume
            try:
                blade_settings.save_settings()
            except RuntimeError as e:
                print("Error saving settings. Cannot save while mounted as a drive.\n", e)
            active_config_page = 'hue'
            last_config_page = None
            blade.mode = 'run'
            mode = 'run'
        if switch.short_count > 0:
            active_config_page = config_pages[(config_pages.index(active_config_page) + 1) % len(config_pages)]
