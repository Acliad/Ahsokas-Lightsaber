This board contains all the control and driver circuitry for the lightsaber's power core. The original prototype was built with a [Adafruit RP2040 Prop-Maker Feather](https://learn.adafruit.com/adafruit-rp2040-prop-maker-feather/overview?gad_source=1&gbraid=0AAAAADx9JvSYvroxZ-rMhNv60DHCdfj1e&gclid=Cj0KCQjwgL-3BhDnARIsAL6KZ68s_8NPtJWohHZQhYD6guZvRnboexCSJRLxrmSgvO_vFlvhVqaqsGYaAtTnEALw_wcB). This board is designed to have the same outline and generally accomplish the same feature set. The primary functional differences are:

- Uses an STM32L4 instead of a RP2040
- Uses a 6-axis IMU instead of a 3-axis accelerometer
- Contains a 5V boost converter to power the LEDs at full brightness across battery voltage

## Requirements
The main Power Core board requirements are:

- Contains >= 100MB of onboard storage
- Powered from a single-cell lithium-ion battery
    - Battery connector compatible with JST-PH
- USB-C charging and power from USB-C when connected
- USB-C data connection to the MCU
- 6-axis IMU for motion detection
- 5V boost converter to power the LEDs at full brightness across battery voltage
- 3.3V regulator to power the MCU and connected peripherals
- ~3W audio amplifier
- Terminal block for easy connection to the LED strip and speaker
- EN pin to enable/disable to put device into very low power shutdown mode
- Measurement of battery voltage

## Main Component Selection
- MCU: STM32L431RC (64-pin LQFP, 80MHz, 256KB Flash, 64KB RAM)
- Flash: W25N01GV (1Gb, QSPI)
- IMU: LSM6DSR (Accelerometer + Gyroscope)
- Audio Amplifier: MAX98357 (3.2W @ 4Ω)
- Battery Charger: MCP73831T (500mA, 4.2V)
- 5V Boost Converter: TPS61230ARNSR
- 3.3V Regulator: WL9005S5-33 (or any SOT-23-5 3.3V regulator, watch IQ and minimize dropout voltage)\