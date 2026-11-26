# Raindrops: random drops of greens, blues and purples ripple out and fade.
# Same framework as image_view.py: RGBMatrixOptions + PIL image + SetImage.

# Used in main loop
from time import sleep, time
import random
import colorsys

###################################
# Graphics imports, constants and structures
###################################
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw, ImageChops

# this is the size of ONE of our matrixes.
matrix_rows = 64
matrix_columns = 64

# how many matrixes stacked horizontally and vertically
matrix_horizontal = 1
matrix_vertical = 1

total_rows = matrix_rows * matrix_vertical
total_columns = matrix_columns * matrix_horizontal

options = RGBMatrixOptions()
options.rows = matrix_rows
options.cols = matrix_columns
options.chain_length = matrix_horizontal
options.parallel = matrix_vertical
#options.hardware_mapping = 'adafruit-hat-pwm'  # If you have an Adafruit HAT: 'adafruit-hat'
#options.hardware_mapping = 'adafruit-hat'  # If you have an Adafruit HAT: 'adafruit-hat'
options.hardware_mapping = 'regular'

#options.gpio_slowdown = 2

matrix = RGBMatrix(options = options)

###################################
# Rain settings
###################################
max_drops = 20        # most drops on screen at once
drops_per_second = 10  # average rate new drops appear
frame_delay = 0.025   # seconds between frames (~40 fps)

# Hue range in degrees: ~100 = green, ~200 = cyan, ~240 = blue, ~290 = purple
hue_min = 100
hue_max = 290

bg_color = (0,0,0)

###################################
# Drop class
###################################
class Drop:
  def __init__(self):
    self.x = random.randint(0, total_columns - 1)
    self.y = random.randint(0, total_rows - 1)
    self.radius = 0.0
    self.max_radius = random.uniform(5, 16)   # how far the ripple spreads
    self.speed = random.uniform(10, 20)       # pixels per second

    hue = random.uniform(hue_min, hue_max) / 360.0
    sat = random.uniform(0.65, 1.0)
    r, g, b = colorsys.hsv_to_rgb(hue, sat, 1.0)
    self.color = (r * 255, g * 255, b * 255)

  def update(self, dt):
    self.radius = self.radius + self.speed * dt

  def alive(self):
    return self.radius < self.max_radius

  def scaled_color(self, level):
    # bright at first, then fades smoothly to nothing
    fade = 1.0 - self.radius / self.max_radius
    fade = fade * fade * level
    return (int(self.color[0] * fade),
            int(self.color[1] * fade),
            int(self.color[2] * fade))

  def draw(self, layer_draw):
    # splash at the point of impact
    if self.radius < 1.5:
      layer_draw.point((self.x, self.y), fill = self.scaled_color(1.0))

    # main ring, plus a fainter trailing ring inside it
    for ring_radius, level in ((self.radius, 1.0), (self.radius * 0.55, 0.35)):
      if ring_radius < 1:
        continue
      box = (self.x - ring_radius, self.y - ring_radius,
             self.x + ring_radius, self.y + ring_radius)
      layer_draw.ellipse(box, outline = self.scaled_color(level))

###################################
# Main loop
###################################
# Draw on an off-screen canvas and swap it in each frame so there's no flicker
canvas = matrix.CreateFrameCanvas()

drops = []
last_time = time()
next_drop_time = last_time

try:
  print("Press CTRL-C to stop")
  while True:
    now = time()
    dt = now - last_time
    last_time = now

    # random spacing between drops so it feels like real rain
    while now >= next_drop_time:
      if len(drops) < max_drops:
        drops.append(Drop())
      next_drop_time = next_drop_time + random.expovariate(drops_per_second)

    for drop in drops:
      drop.update(dt)
    drops = [drop for drop in drops if drop.alive()]

    screen = Image.new("RGB", (total_columns,total_rows), bg_color)

    # each drop gets its own layer, then we add the layers together so
    # overlapping ripples blend instead of covering each other up
    for drop in drops:
      layer = Image.new("RGB", (total_columns,total_rows), (0,0,0))
      drop.draw(ImageDraw.Draw(layer))
      screen = ImageChops.add(screen, layer)

    canvas.SetImage(screen, 0, 0)
    canvas = matrix.SwapOnVSync(canvas)

    sleep(frame_delay)

except KeyboardInterrupt:
  exit(0)
