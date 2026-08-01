"""Tuning constants, colors, and logical resolution for VERT.

Everything gameplay-feel related lives in the TUNING block below so it is
trivial to find and adjust without hunting through physics code.
"""
from __future__ import annotations

# --- DISPLAY ---
LOGICAL_WIDTH = 1280
LOGICAL_HEIGHT = 720
FPS = 60

# --- COLORS (bright, saturated, sun-bleached arcade palette. No pastels.) ---
BLACK = (12, 10, 20)
WHITE = (255, 255, 255)
CYAN = (0, 235, 255)
HOT_CYAN = (0, 255, 240)
MAGENTA = (255, 0, 170)
HOT_PINK = (255, 25, 150)
ORANGE = (255, 130, 0)
SUNSET_ORANGE = (255, 90, 40)
LIME = (150, 255, 0)
YELLOW = (255, 225, 0)
PURPLE = (150, 40, 220)
FENCE_COLOR = (25, 20, 40)
SKY_TOP = (0, 220, 255)
SKY_BOTTOM = (255, 130, 210)
RAMP_FILL = (70, 30, 95)
RAMP_FILL_2 = (110, 30, 130)
UI_BG = (20, 10, 40)

# --- TUNING ---
GRAVITY_GROUND = 600.0        # accel factor applied via ramp slope while grounded
GRAVITY_AIR = 1600.0          # px/s^2 while airborne
FRICTION = 0.05               # fraction of speed bled per second (always-on damping)
MAX_SPEED = 850.0             # px/s cap on ground speed
PUMP_BOOST = 140.0            # px/s added per successful pump
MIN_LAUNCH_SPEED = 140.0      # px/s required at the coping to become airborne
LAUNCH_VY_FACTOR = 0.9        # converts horizontal speed into launch vy
POP_VELOCITY = 150.0          # extra upward pop added at launch
LANDING_ANGLE_TOLERANCE = 35.0  # degrees from a multiple of 180 that still lands clean
BAIL_RESPAWN_DELAY = 1.5      # seconds before respawn after a bail
BAIL_SPEED_MULT = 0.45        # fraction of pre-bail speed kept after respawn
SPIN_RATE = 320.0             # degrees/sec while a spin button is held
FLIP_DURATION = 0.35          # seconds for one flip rotation to animate
GRAB_HELD_THRESHOLD = 0.8     # seconds before a grab counts as "held"
RUN_DURATION = 90.0           # seconds per run

# --- RAMP GEOMETRY (vert halfpipe: deck | transition | flat | transition | deck) ---
DECK_WIDTH = 260.0
TRANSITION_RADIUS = 200.0
FLAT_WIDTH = 220.0
DECK_Y = 160.0
FLAT_Y = DECK_Y + TRANSITION_RADIUS
TOTAL_WIDTH = DECK_WIDTH * 2 + TRANSITION_RADIUS * 2 + FLAT_WIDTH

HIGH_SCORE_FILE = "vert_highscore.json"
