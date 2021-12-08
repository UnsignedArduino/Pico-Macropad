from time import sleep
from adafruit_debouncer import Debouncer
from adafruit_dotstar import DotStar
from board import GP5, GP4, GP17, GP18, GP19, GP25
from busio import I2C
from community_tca9555 import TCA9555
from rainbowio import colorwheel
from digitalio import DigitalInOut, Direction
from json import load
from usb_hid import devices
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from math import sin

config_path = "config.json"

i2c = I2C(scl=GP5, sda=GP4)
expander = TCA9555(i2c)
leds = DotStar(GP18, GP19, 16, brightness=0.1, auto_write=False)

chip_select = DigitalInOut(GP17)
chip_select.direction = Direction.OUTPUT
chip_select.value = False

builtin_led = DigitalInOut(GP25)
builtin_led.direction = Direction.OUTPUT
builtin_led.value = True

sleep(0.5)
keyboard = Keyboard(devices)
keyboard_layout = KeyboardLayoutUS(keyboard)
builtin_led.value = False

buttons = (
    Debouncer(lambda: not expander.input_port_0_pin_0),
    Debouncer(lambda: not expander.input_port_0_pin_1),
    Debouncer(lambda: not expander.input_port_0_pin_2),
    Debouncer(lambda: not expander.input_port_0_pin_3),
    Debouncer(lambda: not expander.input_port_0_pin_4),
    Debouncer(lambda: not expander.input_port_0_pin_5),
    Debouncer(lambda: not expander.input_port_0_pin_6),
    Debouncer(lambda: not expander.input_port_0_pin_7),
    Debouncer(lambda: not expander.input_port_1_pin_0),
    Debouncer(lambda: not expander.input_port_1_pin_1),
    Debouncer(lambda: not expander.input_port_1_pin_2),
    Debouncer(lambda: not expander.input_port_1_pin_3),
    Debouncer(lambda: not expander.input_port_1_pin_4),
    Debouncer(lambda: not expander.input_port_1_pin_5),
    Debouncer(lambda: not expander.input_port_1_pin_6),
    Debouncer(lambda: not expander.input_port_1_pin_7),
)
button_names = ["0", "1", "2", "3", "4", "5", "6", "7",
                "8", "9", "A", "B", "C", "D", "E", "F"]

offset = 0

def run_macro(macro):
    builtin_led.value = True
    for action in macro:
        key = action["key"]
        if action["action"] == "press":
            if isinstance(key, list):
                for k in key:
                    keyboard.press(k)
            else:
                keyboard.press(key)
        elif action["action"] == "release":
            if isinstance(key, list):
                for k in key:
                    keyboard.release(k)
            else:
                keyboard.release(key)
        elif action["action"] == "type":
            if isinstance(key, int):
                keyboard.send(key)
            elif isinstance(key, list):
                for k in key:
                    keyboard.send(k)
            else:
                for letter in key:
                    keyboard.press(*keyboard_layout.keycodes(letter))
                    keyboard.release_all()
    keyboard.release_all()
    builtin_led.value = False


def constrain(x, minimum, maximum):
    return max(minimum, min(x, maximum))


with leds:
    try:
        with open(config_path, mode="rt") as file:
            config = load(file)

        key_config = config["keys"]

        while True:
            macros_to_run = []

            for index, button in enumerate(buttons):
                button.update()
                if button_names[index] in key_config:
                    name = button_names[index]
                    if button.value:
                        r, g, b = key_config[name]["on_color"]
                        leds[index] = (r, g, b)
                    else:
                        r, g, b = key_config[name]["off_color"]
                        leds[index] = (r, g, b)
                    if button.rose:
                        macros_to_run.append(name)
                else:
                    if button.value:
                        r, g, b = config["default_on_color"]
                        leds[index] = (r, g, b)
                    else:
                        r, g, b = config["default_off_color"]
                        leds[index] = (r, g, b)

            leds.show()
            
            for name in macros_to_run:
                run_macro(key_config[name]["macro"])
            
            sleep(0.01)
    except ValueError:
        while True:
            leds.fill((255, 0, 0))
            leds.show()
            sleep(1)
            leds.fill((0, 0, 0))
            leds.show()
            sleep(1)
    except Exception as err:
        print(err)
        while True:
            leds.fill((255, 64, 0))
            leds.show()
            sleep(1)
            leds.fill((0, 0, 0))
            leds.show()
            sleep(1)
