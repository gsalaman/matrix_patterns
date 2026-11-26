# Sight: cycles through six color displays, about 15 seconds each.
#   1. Prism            - white beam splits into a shimmering rainbow
#   2. Color wheel      - rotating, breathing hue wheel
#   3. Kaleidoscope     - mirrored, ever-changing color pattern
#   4. Optical illusion - a hypnotic spiral, then a rushing tunnel
#   5. Raindrops        - green, blue and purple ripples land and fade
#   6. Symbol           - the aofc symbol turns clockwise, then back
# Put aofc_just_symbol_small.jpg in the same folder as this file.
# Same framework as image_view.py: RGBMatrixOptions + PIL image + SetImage.
# Needs numpy: sudo apt install python3-numpy

# Used in main loop
from time import sleep, time
import math
import os
import random
import colorsys

###################################
# Graphics imports, constants and structures
###################################
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw, ImageChops
import numpy as np

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
# Display settings
###################################
scene_seconds = 15   # how long each scene runs
fade_seconds = 0.6   # fade out / fade in between scenes
frame_delay = 0.02   # small pause between frames

###################################
# Shared helpers
###################################
# Pixel coordinates measured from the center of the panel, computed once.
ys, xs = np.mgrid[0:total_rows, 0:total_columns].astype(np.float32)
center_x = (total_columns - 1) / 2.0
center_y = (total_rows - 1) / 2.0
dx = xs - center_x
dy = ys - center_y
radius = np.hypot(dx, dy)
angle = np.arctan2(dy, dx)

def hsv_to_rgb(h, s, v):
  # h, s, v are arrays (or numbers) from 0 to 1. Returns a rows x cols x 3 array 0-255.
  h = np.broadcast_to(h, radius.shape) % 1.0
  s = np.broadcast_to(s, radius.shape)
  v = np.broadcast_to(v, radius.shape)
  i = np.floor(h * 6).astype(int) % 6
  f = h * 6 - np.floor(h * 6)
  p = v * (1 - s)
  q = v * (1 - f * s)
  t = v * (1 - (1 - f) * s)
  r = np.choose(i, [v, q, p, p, t, v])
  g = np.choose(i, [t, v, v, q, p, p])
  b = np.choose(i, [p, p, t, v, v, q])
  return np.stack([r, g, b], axis = -1) * 255

def soft_stripes(wave, sharpness = 3.0):
  # turns a sine wave into stripes with slightly soft edges (0 to 1)
  return np.clip(wave * sharpness, -1, 1) * 0.5 + 0.5

###################################
# Scene 1: Prism
###################################
prism_top = (22, 14)
prism_left = (10, 44)
prism_right = (34, 44)
beam_entry = (16, 30)     # where the white beam hits the left face
beam_exit = (28, 30)      # where the light leaves the right face
exit_dist = np.hypot(xs - beam_exit[0], ys - beam_exit[1])
prism_falloff = np.clip(1.25 - exit_dist / 70.0, 0.35, 1.0)[..., None]

def draw_prism(t):
  screen = Image.new("RGB", (total_columns, total_rows), (0, 0, 0))
  draw = ImageDraw.Draw(screen)

  # rainbow fan: spread slowly breathes, and a shimmer runs across the bands
  bands = 24
  spread = 0.75 + 0.15 * math.sin(t * 0.8)
  center_dir = 0.12 + 0.05 * math.sin(t * 0.5)
  far = 120
  for i in range(bands):
    a1 = center_dir - spread / 2 + spread * i / bands
    a2 = center_dir - spread / 2 + spread * (i + 1) / bands
    hue = 0.78 * i / (bands - 1)          # red on top, violet on the bottom
    shimmer = 0.7 + 0.3 * math.sin(t * 4 - i * 0.6)
    r, g, b = hsv_to_rgb(np.array(hue), np.array(1.0), np.array(shimmer))[0, 0]
    p1 = (beam_exit[0] + far * math.cos(a1), beam_exit[1] + far * math.sin(a1))
    p2 = (beam_exit[0] + far * math.cos(a2), beam_exit[1] + far * math.sin(a2))
    draw.polygon([beam_exit, p1, p2], fill = (int(r), int(g), int(b)))

  # fade the rainbow a bit as it travels away from the prism
  pixels = np.asarray(screen).astype(np.float32) * prism_falloff
  screen = Image.fromarray(pixels.astype(np.uint8), "RGB")
  draw = ImageDraw.Draw(screen)

  # white beam coming in from the left, gently wobbling
  start_y = 38 + 2 * math.sin(t * 0.7)
  glow = int(70 + 30 * math.sin(t * 3))
  draw.line([(0, start_y), beam_entry], fill = (glow, glow, glow), width = 3)
  draw.line([(0, start_y), beam_entry], fill = (255, 255, 255), width = 1)

  # light inside the glass, then the prism outline on top
  draw.polygon([prism_top, prism_left, prism_right], fill = (12, 12, 20))
  draw.line([beam_entry, beam_exit], fill = (200, 200, 200), width = 1)
  draw.polygon([prism_top, prism_left, prism_right], outline = (170, 170, 190))

  return np.asarray(screen).astype(np.float32)

###################################
# Scene 2: Color wheel
###################################
wheel_radius = 30.0

def draw_color_wheel(t):
  hue = angle / (2 * math.pi) + t * 0.08              # slowly rotates
  ripple = 0.5 + 0.5 * np.sin(radius * 0.35 - t * 3)  # soft rings move outward
  sat = np.clip(radius / (wheel_radius * 0.6), 0, 1) * (0.8 + 0.2 * ripple)
  val = (0.75 + 0.25 * math.sin(t * 1.5)) * (0.85 + 0.15 * ripple)
  edge = np.clip(wheel_radius + 1 - radius, 0, 1)[..., None]   # smooth circle edge
  return hsv_to_rgb(hue, sat, val) * edge

###################################
# Scene 3: Kaleidoscope
###################################
kaleido_segments = 6

def draw_kaleidoscope(t):
  # fold every angle into one mirrored wedge, then turn the whole thing slowly
  wedge = 2 * math.pi / kaleido_segments
  a = (angle + t * 0.25) % wedge
  a = np.where(a > wedge / 2, wedge - a, a)
  kx = radius * np.cos(a)
  ky = radius * np.sin(a)

  # a pattern made from a few overlapping waves that drift over time
  pattern = (np.sin(kx * 0.35 + t * 1.1) +
             np.sin(ky * 0.55 - t * 0.8) +
             np.sin((kx + ky) * 0.22 + t * 0.6) +
             np.sin(radius * 0.3 - t * 1.4))
  hue = pattern * 0.12 + t * 0.04
  val = (np.sin(pattern * 2.2) * 0.5 + 0.5) ** 0.8
  return hsv_to_rgb(hue, 0.9, 0.15 + 0.85 * val)

###################################
# Scene 4: Optical illusions
###################################
def draw_spiral(t):
  # spinning 3-arm spiral; stare at it and it seems to expand
  wave = np.sin(3 * angle + radius * 0.55 - t * 5)
  stripes = soft_stripes(wave)
  hue = radius / 45.0 - t * 0.1
  return hsv_to_rgb(hue, 1.0, stripes)

def draw_tunnel(t):
  # checkerboard tunnel rushing toward you while it twists
  depth = 45.0 / (radius + 2) + t * 3
  twist = angle * 4 / math.pi + t * 0.6
  check = np.sin(depth * math.pi) * np.sin(twist * math.pi)
  tiles = soft_stripes(check, 8.0)
  shade = np.clip(radius / 22.0, 0.08, 1.0)       # dark in the distance
  hue = depth * 0.05
  return hsv_to_rgb(hue, 0.9, tiles * shade)

def draw_illusion(t):
  if t < scene_seconds / 2:
    return draw_spiral(t)
  return draw_tunnel(t - scene_seconds / 2)

###################################
# Scene 5: Raindrops
###################################
rain_max_drops = 20        # most drops on screen at once
rain_drops_per_second = 8  # average rate new drops appear

# Hue range in degrees: ~100 = green, ~200 = cyan, ~240 = blue, ~290 = purple
rain_hue_min = 100
rain_hue_max = 290

class Drop:
  def __init__(self):
    self.x = random.randint(0, total_columns - 1)
    self.y = random.randint(0, total_rows - 1)
    self.radius = 0.0
    self.max_radius = random.uniform(5, 16)   # how far the ripple spreads
    self.speed = random.uniform(10, 20)       # pixels per second

    hue = random.uniform(rain_hue_min, rain_hue_max) / 360.0
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

rain_drops = []
rain_last_t = 0.0
rain_next_drop_t = 0.0

def draw_raindrops(t):
  global rain_drops, rain_last_t, rain_next_drop_t

  # a new pass through this scene starts with a clear sky
  if t < rain_last_t:
    rain_drops = []
    rain_next_drop_t = t
  dt = max(0.0, t - rain_last_t)
  rain_last_t = t

  # random spacing between drops so it feels like real rain
  while t >= rain_next_drop_t:
    if len(rain_drops) < rain_max_drops:
      rain_drops.append(Drop())
    rain_next_drop_t = rain_next_drop_t + random.expovariate(rain_drops_per_second)

  for drop in rain_drops:
    drop.update(dt)
  rain_drops = [drop for drop in rain_drops if drop.alive()]

  # each drop gets its own layer, then we add the layers together so
  # overlapping ripples blend instead of covering each other up
  screen = Image.new("RGB", (total_columns, total_rows), (0, 0, 0))
  for drop in rain_drops:
    layer = Image.new("RGB", (total_columns, total_rows), (0, 0, 0))
    drop.draw(ImageDraw.Draw(layer))
    screen = ImageChops.add(screen, layer)

  return np.asarray(screen).astype(np.float32)

###################################
# Scene 6: Rotating symbol
###################################
symbol_file = "aofc_just_symbol_small.jpg"
symbol_rotation_seconds = 7.5   # time for one full turn in each direction

# Load once at startup. We keep a copy 3x the panel size, rotate that, and
# shrink it down each frame so the edges stay smooth while it turns.
symbol_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), symbol_file)
symbol_big = Image.open(symbol_path).convert("RGB")
symbol_big = symbol_big.resize((total_columns * 3, total_rows * 3), Image.LANCZOS)

def draw_symbol(t):
  # one full turn clockwise, then one full turn counter-clockwise, repeating.
  # Each turn eases in and out so it slows to a stop before reversing.
  turn_number = int(t // symbol_rotation_seconds)
  phase = (t % symbol_rotation_seconds) / symbol_rotation_seconds
  eased = phase * phase * (3 - 2 * phase)
  if turn_number % 2 == 0:
    degrees = -360 * eased           # clockwise (PIL turns counter-clockwise for positive angles)
  else:
    degrees = -360 + 360 * eased     # back the other way
  turned = symbol_big.rotate(degrees, resample = Image.BICUBIC, fillcolor = (0, 0, 0))
  turned = turned.resize((total_columns, total_rows), Image.BOX)
  return np.asarray(turned).astype(np.float32)

###################################
# Main loop
###################################
scenes = [draw_prism, draw_color_wheel, draw_kaleidoscope, draw_illusion,
          draw_raindrops, draw_symbol]

# Draw on an off-screen canvas and swap it in each frame so there's no flicker
canvas = matrix.CreateFrameCanvas()
start_time = time()

try:
  print("Press CTRL-C to stop")
  while True:
    elapsed = time() - start_time
    scene_number = int(elapsed // scene_seconds) % len(scenes)
    scene_time = elapsed % scene_seconds

    pixels = scenes[scene_number](scene_time)

    # fade in at the start of each scene and out at the end
    fade = min(1.0, scene_time / fade_seconds, (scene_seconds - scene_time) / fade_seconds)
    pixels = np.clip(pixels * fade, 0, 255).astype(np.uint8)

    screen = Image.fromarray(pixels, "RGB")
    canvas.SetImage(screen, 0, 0)
    canvas = matrix.SwapOnVSync(canvas)

    sleep(frame_delay)

except KeyboardInterrupt:
  exit(0)
