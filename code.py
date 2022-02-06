from adafruit_debouncer import Debouncer
from adafruit_display_text.label import Label
from adafruit_displayio_ssd1306 import SSD1306
from adafruit_dotstar import DotStar
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from board import GP5, GP4, GP17, GP18, GP19, GP25
from busio import I2C
from community_tca9555 import TCA9555
from digitalio import DigitalInOut, Direction
from displayio import I2CDisplay, release_displays, Group
from json import load
from random import choice
from terminalio import FONT
from time import sleep, monotonic_ns
from usb_hid import devices

# Constants
CONFIG_PATH = "config.json"


class MacroPad:
    def __init__(self, config):
        self.config = config
        # Holds settings like default key color for unused keys
        self.default_config = self.config["default"]
        # Holds all the sets
        self.set_config = self.config["sets"]
        self.selected_set = 0
        # Last text and last time so we can "turn" off the display
        self.last_text = ""
        self.last_new_text = monotonic_ns()
        self.new_text_time = 3_000_000_000
        # Initialize hardware
        self.init_hardware()

    def init_display(self):
        # Create display and use the I2C bus for the expander
        self.display_bus = I2CDisplay(self.i2c, device_address=0x3C)
        self.display = SSD1306(self.display_bus, width=128, height=32)

        self.splash = Group()
        self.display.show(self.splash)

        self.label = Label(FONT, color=0xFFFFFF, x=4, y=4)
        self.splash.append(self.label)

    def init_hardware(self):
        # Release displays so we can remake the I2C bus
        release_displays()

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

        # Do display stuff
        self.init_display()

        # This LED lights up whenever USB stuff is happening
        self.builtin_led.value = True
        self.label.text = "Initializing USB"

        # Race condition prevention
        sleep(0.5)

        # Make keyboard object
        self.keyboard = Keyboard(devices)
        # Make keyboard layout object so we can type strings
        self.keyboard_layout = KeyboardLayoutUS(self.keyboard)

        # No more USB activity for now
        self.builtin_led.value = False
        self.label.text = ""

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
        # 	},
        #   "auto_release": false
        # ]
        # Find keycodes at:
        # https://circuitpython.readthedocs.io/projects/hid/en/latest/api.html#adafruit-hid-keycode-keycode
        # USB activity LED
        self.builtin_led.value = True
        auto_release = True
        for action in macro:
            if action == "no_auto_release":
                auto_release = False
                continue
            # Get the key
            key = action["key"]
            # Pressing action
            if action["action"] == "press":
                if isinstance(key, list):
                    for k in key:
                        if isinstance(k, str):
                            self.keyboard.press(getattr(Keycode, k))
                        else:
                            self.keyboard.press(k)
                else:
                    self.keyboard.press(key)
            # Releasing action
            elif action["action"] == "release":
                if isinstance(key, list):
                    for k in key:
                        if isinstance(k, str):
                            self.keyboard.release(getattr(Keycode, k))
                        else:
                            self.keyboard.release(k)
                else:
                    self.keyboard.release(key)
            # Typing action
            elif action["action"] == "type":
                if isinstance(key, int):
                    self.keyboard.send(key)
                elif isinstance(key, list):
                    for k in key:
                        if isinstance(k, str):
                            self.keyboard.send(getattr(Keycode, k))
                        else:
                            self.keyboard.send(k)
                else:
                    for letter in key:
                        # Press every key needed to type out the letter
                        self.keyboard.press(
                            *self.keyboard_layout.keycodes(letter)
                        )
                        # Release all
                        self.keyboard.release_all()
            # Hotkey action - press and then release all
            elif action["action"] == "hotkey":
                if isinstance(key, list):
                    for k in key:
                        if isinstance(k, str):
                            self.keyboard.press(getattr(Keycode, k))
                        else:
                            self.keyboard.press(k)
                else:
                    self.keyboard.press(key)
                self.keyboard.release_all()
        if auto_release:
            self.keyboard.release_all()
            # No more USB activity
            self.builtin_led.value = False

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
                self.label.text = f"Switch to page {self.selected_set + 1}"
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
            self.label.text = "Ready"

            while True:
                # Run AFTER the LEDs have updated - looks better
                macros_to_run = []

                # Check every button
                for index, button in enumerate(self.buttons):
                    button.update()
                    macro = self.handle_button(button, index)
                    if macro is not None:
                        # Queue macro to run
                        macros_to_run.append(macro)

                self.leds.show()

                # Run queued macros
                if len(macros_to_run) > 0:
                    print(f"Running {len(macros_to_run)} macro(s)")
                    macro_start = monotonic_ns()
                    for macro in macros_to_run:
                        self.label.text = f"Running macro..."
                        self.run_macro(macro)
                    macro_end = monotonic_ns()
                    macro_time = (macro_end - macro_start) / 1_000_000
                    self.label.text = f"Done ({macro_time:.1f} ms)"

                # Reset the last_new_text time if the text changed
                if self.label.text != self.last_text:
                    self.last_text = self.label.text
                    self.last_new_text = monotonic_ns()
                # Clear if it has went overtime
                if monotonic_ns() - self.last_new_text > self.new_text_time:
                    self.label.text = ""

                # Delay a teensy bit
                sleep(0.01)


# Load JSON configuration
with open(CONFIG_PATH, mode="rt") as file:
    config = load(file)

mp = MacroPad(config)
mp.run()
