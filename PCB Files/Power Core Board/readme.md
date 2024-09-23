This board contains all the control and driver circuitry for the lightsaber's power core. The original prototype was built with an [Adafruit RP2040 Prop-Maker Feather](https://learn.adafruit.com/adafruit-rp2040-prop-maker-feather/overview?gad_source=1&gbraid=0AAAAADx9JvSYvroxZ-rMhNv60DHCdfj1e&gclid=Cj0KCQjwgL-3BhDnARIsAL6KZ68s_8NPtJWohHZQhYD6guZvRnboexCSJRLxrmSgvO_vFlvhVqaqsGYaAtTnEALw_wcB). This board is designed to have the same outline and generally accomplish the same feature set. The primary functional differences are this Power Core board:

- Uses an STM32L4 instead of a RP2040
- Uses a 6-axis IMU instead of a 3-axis accelerometer
- Contains a 5V boost converter to power the LEDs at full brightness across battery voltage

## Requirements
The Power Core board main requirements are:

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
- MCU: [STM32L431RC](https://www.st.com/content/ccc/resource/technical/document/datasheet/group3/83/b3/60/f6/b1/cc/47/7e/DM00257211/files/DM00257211.pdf/jcr:content/translations/en.DM00257211.pdf) (64-pin LQFP, 80MHz, 256KB Flash, 64KB RAM)
- Flash: [W25N01GV](https://www.winbond.com/resource-files/w25n01gv%20revl%20050918%20unsecured.pdf) (1Gb, QSPI)
- IMU: [LSM6DSR](https://www.st.com/resource/en/datasheet/lsm6dsr.pdf) (Accelerometer + Gyroscope)
- Audio Amplifier: [MAX98357](https://www.analog.com/media/en/technical-documentation/data-sheets/max98357a-max98357b.pdf) (3.2W @ 4Ω)
- Battery Charger: [MCP73831](https://ww1.microchip.com/downloads/en/DeviceDoc/MCP73831-Family-Data-Sheet-DS20001984H.pdf) (500mA, 4.2V)
- 5V Boost Converter: [TPS61230ARNSR](https://www.ti.com/lit/ds/symlink/tps61230a.pdf?ts=1727034032758&ref_url=https%253A%252F%252Fwww.ti.com%252Fproduct%252FTPS61230A%252Fpart-details%252FTPS61230ARNSR) (2.4A at 5V out with 2.5V in)
- 3.3V Regulator: [WL9005S5-33](https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2302091109_WPMtek-Wei-Pan-Microelectronics-WL9005S3-18_C5357196.pdf) (or any SOT-23-5 3.3V regulator, watch IQ and minimize dropout voltage)