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
        self.default_config = self.config["default"]
        self.set_config = self.config["sets"]
        self.selected_set = 0
        self.init_hardware()
    
    def init_hardware(self):
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
                for index, button in enumerate(self.buttons):
                    button.update()
                    if index > 11:
                        if f"{index - 12}" in self.set_config:
                            selected_color = self.set_config[f"{index - 12}"]["selected_color"]
                            unselected_color = self.set_config[f"{index - 12}"]["unselected_color"]
                            pressed_color = self.set_config[f"{index - 12}"]["pressed_color"]
                        else:
                            selected_color = self.default_config["selected_color"]
                            unselected_color = self.default_config["unselected_color"]
                            pressed_color = self.default_config["pressed_color"]
                        if button.rose:
                            self.selected_set = index - 12
                        if button.value:
                            self.leds[index] = pressed_color
                        else:
                            if self.selected_set == index - 12:
                                self.leds[index] = selected_color
                            else:
                                self.leds[index] = unselected_color
                    else:
                        if f"{self.selected_set}" not in self.set_config:
                            off_color = self.default_config["off_color"]
                            on_color = self.default_config["on_color"]
                            self.leds[index] = on_color if button.value else off_color
                            continue
                        keys_config = self.set_config[f"{self.selected_set}"]["keys"]
                        if f"{index}" in keys_config:
                            key_config = keys_config[f"{index}"]
                            off_color = key_config["off_color"]
                            on_color = key_config["on_color"]
                        else:
                            off_color = self.default_config["off_color"]
                            on_color = self.default_config["on_color"]
                        self.leds[index] = on_color if button.value else off_color
                
                self.leds.show()
                sleep(0.01)


with open(config_path, mode="rt") as file:
    config = load(file)

mp = Macropad(config)
mp.run()
