from random import randint


class BaseAnimation:
    def __init__(self, leds):
        self.leds = leds
        self.index = 0
        # Used to slow down how fast the colors change
        self.inc_index = 0
        self.max_inc = 10

    def tick(self):
        raise NotImplementedError

    def increment_index(self):
        # Increment the index incrementer
        self.inc_index += 1
        if self.inc_index >= self.max_inc:
            # Reset incrementer
            self.inc_index = 0
            # Actually increment the value used for colors
            self.index += 1

    def __repr__(self):
        return f"BaseAnimation(leds)"


# # Copied from
# # https://learn.adafruit.com/hacking-ikea-lamps-with-circuit-playground-express/generate-your-colors#colorwheel-or-wheel-explained-2982566-3
# def wheel(pos):
#     # Input a value 0 to 255 to get a color value.
#     # The colours are a transition r - g - b - back to r.
#     if pos < 0 or pos > 255:
#         return 0, 0, 0
#     if pos < 85:
#         return int(255 - pos * 3), int(pos * 3), 0
#     if pos < 170:
#         pos -= 85
#         return 0, int(255 - pos * 3), int(pos * 3)
#     pos -= 170
#     return int(pos * 3), 0, int(255 - (pos * 3))
#
#
# class RainbowAnimation(BaseAnimation):
#     def __init__(self, leds):
#         super().__init__(leds)
#
#     def tick(self):
#         for i in range(self.leds.n):
#             # Calculate a value
#             value = (self.index + (i * 2)) % 256
#             r, g, b = wheel(value)
#             self.leds[i] = (r, g, b, 0.1)
#         self.increment_index()
#
#     def increment_index(self):
#         # Increment the index incrementer
#         self.inc_index += 1
#         if self.inc_index >= self.max_inc:
#             # Reset incrementer
#             self.inc_index = 0
#             # Actually increment the value used for colors
#             self.index = (self.index + 1) % 256
#
#     def __repr__(self):
#         return f"RainbowAnimation(leds)"
#


class BasePresetAnimation(BaseAnimation):
    def __init__(self, leds, positions=()):
        super().__init__(leds)
        self.leds.fill((0, 0, 0))
        self.positions = positions
        self.brightness = 1
        self.direction = 1

    def tick(self):
        color = (self.brightness, self.brightness, self.brightness, 0.1)
        for position in self.positions[self.index]:
            self.leds[position] = color
        self.brightness += self.direction
        if self.brightness >= 255:
            self.direction = -1
        elif self.brightness <= 0:
            self.direction = 1
            self.increment_index()

    def increment_index(self):
        # Actually increment the value used for positions
        self.index = (self.index + 1) % len(self.positions)

    def __repr__(self):
        return f"BasePresetAnimation(leds, positions={self.positions})"


class PresetSnakeAnimation(BasePresetAnimation):
    def __init__(self, leds):
        super().__init__(leds, ((0, ), (1, ), (5, ), (6, ), (2, ), (3, ),
                                (7, ), (6, ), (10, ), (11, ), (15, ), (14, ),
                                (10, ), (9, ), (13, ), (12, ), (8, ), (9, ),
                                (5, ), (4, )))

    def __repr__(self):
        return f"SnakeAnimation(leds)"


class BaseRandomDotsAnimation(BaseAnimation):
    def __init__(self, leds, max_led):
        super().__init__(leds)
        self.leds.fill((0, 0, 0))
        self.max_led = max_led
        self.brightness = 1
        self.direction = 1
        self.indexes = []

    def tick(self):
        color = (self.brightness, self.brightness, self.brightness, 0.1)
        for index in self.indexes:
            self.leds[index] = color
        self.brightness += self.direction
        if self.brightness >= 255:
            self.direction = -1
        elif self.brightness <= 0:
            self.direction = 1
            self.increment_index()

    def increment_index(self):
        self.indexes = []
        for _ in range(self.max_led):
            new_val = randint(0, self.leds.n - 1)
            # Ensures we get a different one
            while new_val in self.indexes:
                new_val = randint(0, self.leds.n - 1)
            self.indexes.append(new_val)

    def __repr__(self):
        return f"BaseRandomDotsAnimation(leds, max_led={self.max_led})"


class RandomDotsAnimation(BaseRandomDotsAnimation):
    def __init__(self, leds):
        # Create a base random dots animation but with a variable amount of
        # dots
        super().__init__(leds, randint(1, 4))

    def __repr__(self):
        return f"RandomDotsAnimation(leds, max_led={self.max_led})"


# ALL_ANIMATIONS = [PresetSnakeAnimation, RandomDotsAnimation]
ALL_ANIMATIONS = [PresetSnakeAnimation]
