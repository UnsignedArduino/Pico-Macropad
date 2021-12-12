from adafruit_debouncer import Debouncer
from adafruit_dotstar import DotStar
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from board import GP5, GP4, GP17, GP18, GP19, GP25
from busio import I2C
from community_tca9555 import TCA9555
from digitalio import DigitalInOut, Direction
from json import load
from math import sin
from rainbowio import colorwheel
from random import choice
from time import sleep, monotonic_ns
from usb_hid import devices

from idle_animations import BlankAnimation

# Constants
CONFIG_PATH = "config.json"
IDLE_TIME = 5_000_000_000


class MacroPad:
    def __init__(self, config):
        self.config = config
        # Holds settings like default key color for unused keys
        self.default_config = self.config["default"]
        # Holds all the sets
        self.set_config = self.config["sets"]
        self.selected_set = 0
        # Initialize hardware
        self.init_hardware()
        # Last time since we idled
        self.last_use_time = monotonic_ns()

    def init_hardware(self):
        # Create I2C
        self.i2c = I2C(scl=GP5, sda=GP4)
        # Create expander
        self.expander = TCA9555(self.i2c)
        # Create DotStar
        self.leds = DotStar(GP18, GP19, 16, brightness=0.1, auto_write=False)

        # Create DotStar CS pin but since we don't have to share SPI we can
        # keep it low (selected) forever
        self.led_cs = DigitalInOut(GP17)
        self.led_cs.direction = Direction.OUTPUT
        self.led_cs.value = False

        # Create builtin LED
        self.builtin_led = DigitalInOut(GP25)
        self.builtin_led.direction = Direction.OUTPUT
        # This LED lights up whenever USB stuff is happening
        self.builtin_led.value = True

        # Race condition prevention
        sleep(0.5)

        # Make keyboard object
        self.keyboard = Keyboard(devices)
        # Make keyboard layout object so we can type strings
        self.keyboard_layout = KeyboardLayoutUS(self.keyboard)

        # No more USB activity for now
        self.builtin_led.value = False

        # Create Debouncer instances that just read the expander
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
        # Run a macro that looks something like this:
        # [
        #   {
        # 	  "action": "press",
        # 	  "key": [224, 225, 16]
        # 	},
        # 	{
        # 	  "action": "release",
        # 	  "key": [224, 225, 16]
        # 	}
        # ]
        # Find keycodes at:
        # https://circuitpython.readthedocs.io/projects/hid/en/latest/api.html#adafruit-hid-keycode-keycode
        # USB activity LED
        self.builtin_led.value = True
        for action in macro:
            # Get the key
            key = action["key"]
            # Pressing action
            if action["action"] == "press":
                if isinstance(key, list):
                    for k in key:
                        self.keyboard.press(k)
                else:
                    self.keyboard.press(key)
            # Releasing action
            elif action["action"] == "release":
                if isinstance(key, list):
                    for k in key:
                        self.keyboard.release(k)
                else:
                    self.keyboard.release(key)
            # Typing action
            elif action["action"] == "type":
                if isinstance(key, int):
                    self.keyboard.send(key)
                elif isinstance(key, list):
                    for k in key:
                        self.keyboard.send(k)
                else:
                    for letter in key:
                        # Press every key needed to type out the letter
                        self.keyboard.press(
                            *self.keyboard_layout.keycodes(letter)
                        )
                        # Release all
                        self.keyboard.release_all()
        self.keyboard.release_all()
        # No more USB activity
        self.builtin_led.value = False

    def is_idle(self):
        # Returns whether we are idle or not
        return monotonic_ns() - self.last_use_time > IDLE_TIME

    def pick_idle_animation(self):
        if self.idle_anim is None:
            animations = [BlankAnimation]
            # Get a random animation class and initiate it
            self.idle_anim = choice(animations)(self.leds)

    def handle_button(self, button, index):
        macro = None
        # Is this button a set selector
        if index > 11:
            if f"{index - 12}" in self.set_config:
                set_config = self.set_config[f"{index - 12}"]
                selected_color = set_config["selected_color"]
                unselected_color = set_config["unselected_color"]
                pressed_color = set_config["pressed_color"]
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
            # Is this key not defined in the configuration
            if f"{self.selected_set}" not in self.set_config:
                # Yes, set default colors
                off_color = self.default_config["off_color"]
                on_color = self.default_config["on_color"]
                self.leds[index] = on_color if button.value else off_color
                return None
            # Get key configuration
            keys_config = self.set_config[f"{self.selected_set}"]["keys"]
            if f"{index}" in keys_config:
                key_config = keys_config[f"{index}"]
                off_color = key_config["off_color"]
                on_color = key_config["on_color"]
                # Queue macro to run only if the button has been
                # pressed
                if button.rose:
                    macro = key_config["macro"]
            else:
                off_color = self.default_config["off_color"]
                on_color = self.default_config["on_color"]
            self.leds[index] = on_color if button.value else off_color
        return macro

    def run(self):
        # So that the LEDs turn off on exception
        with self.leds:
            self.idle_anim = None
            previously_idle = False
            while True:
                # Run AFTER the LEDs have updated - looks better
                macros_to_run = []

                # Check every button
                for index, button in enumerate(self.buttons):
                    button.update()
                    if self.is_idle():
                        # Idle animation
                        if not previously_idle:
                            self.pick_idle_animation()
                            previously_idle = True
                        self.idle_anim.tick()
                        if button.value:
                            self.last_use_time = monotonic_ns()
                            previously_idle = False
                            macro = self.handle_button(button, index)
                            if macro is not None:
                                # Queue macro to run
                                macros_to_run.append(macro)
                            # Runs macro immediately, so then we can start the
                            # next paint cycle
                            break
                    else:
                        macro = self.handle_button(button, index)
                        if macro is not None:
                            # Queue macro to run
                            macros_to_run.append(macro)
                        if button.value:
                            self.last_use_time = monotonic_ns()

                self.leds.show()

                # Run queued macros
                for macro in macros_to_run:
                    self.run_macro(macro)

                # Delay a teensy bit
                sleep(0.01)


# Load JSON configuration
with open(CONFIG_PATH, mode="rt") as file:
    config = load(file)

mp = MacroPad(config)
mp.run()
