class BaseAnimation:
    def __init__(self, leds):
        self.leds = leds

    def tick(self):
        raise NotImplementedError


# Copied from
# https://learn.adafruit.com/hacking-ikea-lamps-with-circuit-playground-express/generate-your-colors#colorwheel-or-wheel-explained-2982566-3
def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return 0, 0, 0
    if pos < 85:
        return int(255 - pos * 3), int(pos * 3), 0
    if pos < 170:
        pos -= 85
        return 0, int(255 - pos * 3), int(pos * 3)
    pos -= 170
    return int(pos * 3), 0, int(255 - (pos * 3))


class RainbowAnimation(BaseAnimation):
    def __init__(self, leds):
        super().__init__(leds)
        self.index = 0
        # Used to slow down how fast the colors change
        self.inc_index = 0
        self.max_inc = 10

    def tick(self):
        for i in range(self.leds.n):
            # Calculate a value
            value = (self.index + (i * 2)) % 256
            r, g, b = wheel(value)
            self.leds[i] = (r, g, b, 0.1)
        # Increment the index incrementer
        self.inc_index += 1
        if self.inc_index >= self.max_inc:
            # Reset incrementer
            self.inc_index = 0
            # Actually increment the value used for colors
            self.index = (self.index + 1) % 256


ALL_ANIMATIONS = [RainbowAnimation]
