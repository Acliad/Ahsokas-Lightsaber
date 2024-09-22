# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import os
import random
import board
import pwmio
import audiocore
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
import simpleio
import re
from blade import Blade

# CUSTOMIZE SENSITIVITY HERE: smaller numbers = more sensitive to motion
ENCODER_SENSITIVITY = 0.01
HIT_THRESHOLD = 120
SWING_THRESHOLD = 145

DEFAULT_BLADE_COLOR = (0, 125, 255) # Cyan
DEFAULT_VOLUME = 1.0

# The time the lightsaber is in off mode before going to deep sleep
SLEEP_TIMEOUT_TIME_SECONDS = 10*60

# Load settings
blade_settings = saber_settings.SaberSettings("/settings.json")
# Ensure defaults are set (this should probably be done in the settings class with an optional defaults dict)
if blade_settings.blade_color is None:
    blade_settings.blade_color = DEFAULT_BLADE_COLOR
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
switch = Button(power_btn_pin, short_duration_ms = 10, long_duration_ms = 1000)

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

time_turned_off = 0
mode = 'startup' # Default to startup
config_pages = ['hue', 'saturation']
active_config_page = config_pages[0]
last_config_page = None
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
        mode = 'off'
        time_turned_off = time.monotonic()
    # go to startup from off if button is pressed
    elif mode == 'off':
        if switch.short_count > 0:
            external_power.value = True
            mode = 'startup'
        elif blade.num_pixels_on == 0 and (time.monotonic() - time_turned_off) > SLEEP_TIMEOUT_TIME_SECONDS:
            print("Going to sleep...")
            external_power.value = False
            # Set up the sleep alarm
            power_btn_pin.deinit()
            edge_alarm = alarm.pin.PinAlarm(board.D13, value=False, pull=True)
            alarm.exit_and_deep_sleep_until_alarms(edge_alarm)

    # change color
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
                blade_hsv[1] = min(max(blade_hsv[1] + encoder_increment, 0), 1)
                blade.color = colorsys.hsv_to_rgb(blade_hsv[0], blade_hsv[1], blade_hsv[2])
        last_config_page = active_config_page
        
        if switch.long_press:
            # Save the updated settings
            blade_settings.blade_color = blade.color
            blade_settings.volume = blade_volume
            blade_settings.save_settings()
            active_config_page = 'hue'
            last_config_page = None
            blade.mode = 'run'
            mode = 'run'
        if switch.short_count > 0:
            active_config_page = config_pages[(config_pages.index(active_config_page) + 1) % len(config_pages)]