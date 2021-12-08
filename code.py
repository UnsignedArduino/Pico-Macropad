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


class Macropad:
    def __init__(self, config):
        self.config = config
        self.key_config = self.config["keys"]
        
        self.i2c = I2C(scl=GP5, sda=GP4)
        self.expander = TCA9555(self.i2c)
        self.leds = DotStar(GP18, GP19, 16, brightness=0.1, auto_write=False)

        self.expander_cs = DigitalInOut(GP17)
        self.expander_cs.direction = Direction.OUTPUT
        self.expander_cs.value = False

        self.builtin_led = DigitalInOut(GP25)
        self.builtin_led.direction = Direction.OUTPUT
        self.builtin_led.value = True

        sleep(0.5)
        self.keyboard = Keyboard(devices)
        self.keyboard_layout = KeyboardLayoutUS(self.keyboard)
        self.builtin_led.value = False

        self.buttons = (
            Debouncer(lambda: not self.expander.input_port_0_pin_0),
            Debouncer(lambda: not self.expander.input_port_0_pin_1),
            Debouncer(lambda: not self.expander.input_port_0_pin_2),
            Debouncer(lambda: not self.expander.input_port_0_pin_3),
            Debouncer(lambda: not self.expander.input_port_0_pin_4),
            Debouncer(lambda: not self.expander.input_port_0_pin_5),
            Debouncer(lambda: not self.expander.input_port_0_pin_6),
            Debouncer(lambda: not self.expander.input_port_0_pin_7),
            Debouncer(lambda: not self.expander.input_port_1_pin_0),
            Debouncer(lambda: not self.expander.input_port_1_pin_1),
            Debouncer(lambda: not self.expander.input_port_1_pin_2),
            Debouncer(lambda: not self.expander.input_port_1_pin_3),
            Debouncer(lambda: not self.expander.input_port_1_pin_4),
            Debouncer(lambda: not self.expander.input_port_1_pin_5),
            Debouncer(lambda: not self.expander.input_port_1_pin_6),
            Debouncer(lambda: not self.expander.input_port_1_pin_7),
        )
        self.button_names = ["0", "1", "2", "3", "4", "5", "6", "7",
                             "8", "9", "A", "B", "C", "D", "E", "F"]
    
    def run_macro(self, macro):
        self.builtin_led.value = True
        for action in macro:
            key = action["key"]
            if action["action"] == "press":
                if isinstance(key, list):
                    for k in key:
                        self.keyboard.press(k)
                else:
                    self.keyboard.press(key)
            elif action["action"] == "release":
                if isinstance(key, list):
                    for k in key:
                        self.keyboard.release(k)
                else:
                    self.keyboard.release(key)
            elif action["action"] == "type":
                if isinstance(key, int):
                    self.keyboard.send(key)
                elif isinstance(key, list):
                    for k in key:
                        self.keyboard.send(k)
                else:
                    for letter in key:
                        self.keyboard.press(*self.keyboard_layout.keycodes(letter))
                        self.keyboard.release_all()
        self.keyboard.release_all()
        self.builtin_led.value = False

    
    def run(self):
        with self.leds:
            while True:
                macros_to_run = []

                for index, button in enumerate(self.buttons):
                    button.update()
                    if self.button_names[index] in self.key_config:
                        name = self.button_names[index]
                        if button.value:
                            r, g, b = self.key_config[name]["on_color"]
                            self.leds[index] = (r, g, b)
                        else:
                            r, g, b = self.key_config[name]["off_color"]
                            self.leds[index] = (r, g, b)
                        if button.rose:
                            macros_to_run.append(name)
                    else:
                        if button.value:
                            r, g, b = self.config["default_on_color"]
                            self.leds[index] = (r, g, b)
                        else:
                            r, g, b = self.config["default_off_color"]
                            self.leds[index] = (r, g, b)

                self.leds.show()
                
                for name in macros_to_run:
                    self.run_macro(self.key_config[name]["macro"])
                
                sleep(0.01)


with open(config_path, mode="rt") as file:
    config = load(file)

mp = Macropad(config)
mp.run()
