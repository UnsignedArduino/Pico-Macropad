class BaseAnimation:
    def __init__(self, leds):
        self.leds = leds

    def tick(self):
        raise NotImplementedError


class BlankAnimation(BaseAnimation):
    def tick(self):
        self.leds.fill((0, 0, 0))
