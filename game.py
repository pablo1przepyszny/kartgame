import math
import random
import sys
import pygame
import json
import sys

# -----------------------------
# Simple configuration structs
# -----------------------------

class PlayerConfig:
    def __init__(self, name, left_key, right_key, accel_key, brake_key, color):
        self.name = name
        self.left_key = left_key
        self.right_key = right_key
        self.accel_key = accel_key
        self.brake_key = brake_key
        self.color = color


class GameConfig:
    def __init__(self,
                 width=1280,
                 height=720,
                 laps=3,
                 difficulty="medium",
                 player1=None,
                 player2=None):
        self.width = width
        self.height = height
        self.laps = laps
        self.difficulty = difficulty
        self.player1 = player1
        self.player2 = player2


# -----------------------------
# Track and kart definitions
# -----------------------------

class Track:
    """
    Very simplified "Hungaroring-like" track:
    - Represented as a loop of points.
    - We approximate with a few curves.
    """

    def __init__(self):
        self.points = self._generate_points()
        self.length = len(self.points)

    def _generate_points(self):
        # Simple parametric loop approximating a twisty circuit
        points = []
        for i in range(800):
            t = i / 800.0 * 2 * math.pi
            # Base oval
            x = 400 * math.cos(t)
            y = 250 * math.sin(t)
            # Add some "Hungaroring-ish" kinks
            if 0.2 < t < 0.35:
                x += 80
            if 1.0 < t < 1.4:
                y -= 60
            if 3.5 < t < 4.0:
                x -= 100
            points.append((x, y))
        return points

    def get_point(self, index):
        return self.points[index % self.length]

    def get_forward_index(self, index, offset):
        return (index + offset) % self.length


class Kart:
    def __init__(self, track, color, is_ai=False, difficulty="medium", name="AI"):
        self.track = track
        self.color = color
        self.is_ai = is_ai
        self.difficulty = difficulty
        self.name = name

        self.track_index = 0
        self.lap = 0
        self.progress = 0.0  # 0..1 of lap
        self.speed = 0.0
        self.max_speed = 1.2
        self.accel = 0.02
        self.brake = 0.04
        self.turn_speed = 0.04
        self.angle_offset = 0.0  # lateral offset from center line

        # Difficulty affects AI behavior
        if self.is_ai:
            if difficulty == "easy":
                self.max_speed = 0.9
                self.accel = 0.015
                self.turn_speed = 0.03
            elif difficulty == "hard":
                self.max_speed = 1.4
                self.accel = 0.025
                self.turn_speed = 0.05

    def update_ai(self, dt):
        # Simple AI: try to stay near center of track, adjust speed slightly
        self.speed += self.accel
        if self.speed > self.max_speed:
            self.speed = self.max_speed

        # Add small random wobble based on difficulty
        wobble = 0.0
        if self.difficulty == "easy":
            wobble = random.uniform(-0.02, 0.02)
        elif self.difficulty == "medium":
            wobble = random.uniform(-0.015, 0.015)
        elif self.difficulty == "hard":
            wobble = random.uniform(-0.01, 0.01)

        self.angle_offset += wobble
        self.angle_offset = max(-0.4, min(0.4, self.angle_offset))

        self._advance(dt)

    def update_player(self, dt, keys, config: PlayerConfig):
        # Acceleration / braking
        if keys[config.accel_key]:
            self.speed += self.accel
        elif keys[config.brake_key]:
            self.speed -= self.brake
        else:
            # natural drag
            self.speed *= 0.99

        self.speed = max(0.0, min(self.speed, self.max_speed))

        # Steering
        if keys[config.left_key]:
            self.angle_offset -= self.turn_speed
        if keys[config.right_key]:
            self.angle_offset += self.turn_speed

        self.angle_offset = max(-0.6, min(0.6, self.angle_offset))

        self._advance(dt)

    def _advance(self, dt):
        # Move along track based on speed
        distance = self.speed * dt * 60.0  # scale for frame rate
        self.track_index = int((self.track_index + distance) % self.track.length)
        self.progress = self.track_index / self.track.length

        # Lap counting: when wrapping around
        if self.track_index < 10 and self.progress > 0.0:
            # crude lap detection: if we just passed start line
            self.lap += 1

    def get_world_position(self):
        # Get base track point
        x, y = self.track.get_point(self.track_index)
        # Get direction of track ahead
        ahead_index = self.track.get_forward_index(self.track_index, 5)
        ax, ay = self.track.get_point(ahead_index)
        dx = ax - x
        dy = ay - y
        angle = math.atan2(dy, dx)

        # Offset sideways for lane position
        side_x = -math.sin(angle)
        side_y = math.cos(angle)
        x += side_x * self.angle_offset * 40
        y += side_y * self.angle_offset * 40
        return x, y, angle


# -----------------------------
# Rendering helpers (fake 3D)
# -----------------------------

def project_point(x, y, camera_x, camera_y, camera_angle, screen_w, screen_h):
    # Transform into camera space
    dx = x - camera_x
    dy = y - camera_y

    cos_a = math.cos(-camera_angle)
    sin_a = math.sin(-camera_angle)
    cx = dx * cos_a - dy * sin_a
    cy = dx * sin_a + dy * cos_a

    if cy <= 1:
        cy = 1

    # Simple perspective projection
    fov = 300
    sx = screen_w / 2 + (cx * fov) / cy
    sy = screen_h / 2 + (100 * fov) / cy
    return sx, sy, cy


def draw_horizon(screen, width, height):
    # Sky
    sky_color = (120, 170, 255)
    grass_color = (40, 120, 40)
    hill_color = (30, 90, 30)
    tree_color = (20, 70, 20)

    pygame.draw.rect(screen, sky_color, (0, 0, width, height // 2))
    pygame.draw.rect(screen, grass_color, (0, height // 2, width, height // 2))

    # Simple hills
    for i in range(8):
        hill_x = random.randint(0, width)
        hill_y = height // 2 + random.randint(-40, 40)
        hill_w = random.randint(120, 260)
        hill_h = random.randint(40, 90)
        pygame.draw.ellipse(screen, hill_color, (hill_x - hill_w // 2, hill_y, hill_w, hill_h))

    # Simple trees
    for i in range(12):
        tx = random.randint(0, width)
        ty = height // 2 + random.randint(10, 80)
        pygame.draw.rect(screen, tree_color, (tx - 5, ty - 30, 10, 30))
        pygame.draw.circle(screen, tree_color, (tx, ty - 35), 12)


def draw_track_and_karts(screen, track, karts, camera_kart, width, height):
    screen.fill((0, 0, 0))
    draw_horizon(screen, width, height)

    # Camera based on player kart
    cam_x, cam_y, cam_angle = camera_kart.get_world_position()

    # Draw road segments
    road_color = (80, 80, 80)
    edge_color = (200, 200, 200)
    grass_color = (40, 120, 40)

    max_depth = 200
    for i in range(0, max_depth, 2):
        idx1 = track.get_forward_index(camera_kart.track_index, i)
        idx2 = track.get_forward_index(camera_kart.track_index, i + 2)

        x1, y1 = track.get_point(idx1)
        x2, y2 = track.get_point(idx2)

        # Road width grows with distance for perspective
        base_road_width = 80
        w1 = base_road_width
        w2 = base_road_width

        # Project left/right edges
        for side in [-1, 1]:
            sx1, sy1, z1 = project_point(
                x1 + side * w1, y1, cam_x, cam_y, cam_angle, width, height
            )
            sx2, sy2, z2 = project_point(
                x2 + side * w2, y2, cam_x, cam_y, cam_angle, width, height
            )

        # Now draw quad for road
        left1 = project_point(x1 - w1, y1, cam_x, cam_y, cam_angle, width, height)
        right1 = project_point(x1 + w1, y1, cam_x, cam_y, cam_angle, width, height)
        left2 = project_point(x2 - w2, y2, cam_x, cam_y, cam_angle, width, height)
        right2 = project_point(x2 + w2, y2, cam_x, cam_y, cam_angle, width, height)

        poly = [(left1[0], left1[1]),
                (right1[0], right1[1]),
                (right2[0], right2[1]),
                (left2[0], left2[1])]

        pygame.draw.polygon(screen, road_color, poly)

        # Edges
        edge_poly_left = [
            (left1[0] - 4, left1[1]),
            (left1[0], left1[1]),
            (left2[0], left2[1]),
            (left2[0] - 4, left2[1]),
        ]
        edge_poly_right = [
            (right1[0], right1[1]),
            (right1[0] + 4, right1[1]),
            (right2[0] + 4, right2[1]),
            (right2[0], right2[1]),
        ]
        pygame.draw.polygon(screen, edge_color, edge_poly_left)
        pygame.draw.polygon(screen, edge_color, edge_poly_right)

    # Draw karts
    for kart in karts:
        x, y, angle = kart.get_world_position()
        sx, sy, z = project_point(x, y, cam_x, cam_y, cam_angle, width, height)
        size = max(4, int(40 / z))
        # Simple rectangle as kart
        rect = pygame.Rect(0, 0, size, size * 1.5)
        rect.center = (sx, sy)
        pygame.draw.rect(screen, kart.color, rect)


# -----------------------------
# Game loop
# -----------------------------

def run_game(config: GameConfig):
    pygame.init()
    screen = pygame.display.set_mode((config.width, config.height))
    pygame.display.set_caption("Simple Hungaroring Kart")

    clock = pygame.time.Clock()

    track = Track()

    # Create karts
    karts = []

    # Player 1
    p1_kart = Kart(track, config.player1.color, is_ai=False, name=config.player1.name)
    karts.append(p1_kart)

    # Player 2 (optional)
    p2_kart = None
    if config.player2 is not None:
        p2_kart = Kart(track, config.player2.color, is_ai=False, name=config.player2.name)
        karts.append(p2_kart)

    # AI karts
    for i in range(10):
        color = (
            random.randint(50, 255),
            random.randint(50, 255),
            random.randint(50, 255),
        )
        ai_kart = Kart(track, color, is_ai=True, difficulty=config.difficulty, name=f"AI{i+1}")
        ai_kart.track_index = (i * 40) % track.length
        karts.append(ai_kart)

    running = True
    winner = None

    while running:
        dt = clock.tick(60) / 1000.0  # seconds
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()

        # Update karts
        for kart in karts:
            if kart.is_ai:
                kart.update_ai(dt)
            else:
                if kart is p1_kart:
                    kart.update_player(dt, keys, config.player1)
                elif p2_kart is not None and kart is p2_kart:
                    kart.update_player(dt, keys, config.player2)

            # Check laps
            if kart.lap >= config.laps and winner is None:
                winner = kart.name

        # Choose camera: follow player 1
        camera_kart = p1_kart

        draw_track_and_karts(screen, track, karts, camera_kart, config.width, config.height)

        # HUD
        font = pygame.font.SysFont("Arial", 20)
        hud_text = f"P1 Lap: {p1_kart.lap}/{config.laps}"
        if p2_kart:
            hud_text += f" | P2 Lap: {p2_kart.lap}/{config.laps}"
        if winner:
            hud_text += f" | WINNER: {winner}"

        text_surf = font.render(hud_text, True, (255, 255, 255))
        screen.blit(text_surf, (20, 20))

        pygame.display.flip()

        if winner:
            # Wait a bit then exit
            pygame.time.wait(4000)
            running = False

    pygame.quit()
    sys.exit()


# -----------------------------
# Simple CLI setup for options
# -----------------------------

def ask_int(prompt, default):
    try:
        val = input(f"{prompt} [{default}]: ").strip()
        if not val:
            return default
        return int(val)
    except Exception:
        return default


def ask_str(prompt, default):
    val = input(f"{prompt} [{default}]: ").strip()
    return val or default


def ask_color(prompt, default):
    val = input(f"{prompt} as R,G,B (0-255) [{default[0]},{default[1]},{default[2]}]: ").strip()
    if not val:
        return default
    try:
        r, g, b = map(int, val.split(","))
        return (r, g, b)
    except Exception:
        return default

def main():
    # If launched with config file
    if len(sys.argv) > 1:
        cfg_path = sys.argv[1]
        with open(cfg_path, "r") as f:
            data = json.load(f)

        p1 = PlayerConfig(
            name="Player 1",
            left_key=pygame.K_LEFT,
            right_key=pygame.K_RIGHT,
            accel_key=pygame.K_RCTRL,
            brake_key=pygame.K_RSHIFT,
            color=tuple(data["player1_color"]),
        )

        p2 = None
        if data["player2_enabled"]:
            p2 = PlayerConfig(
                name="Player 2",
                left_key=pygame.K_a,
                right_key=pygame.K_d,
                accel_key=pygame.K_w,
                brake_key=pygame.K_s,
                color=tuple(data["player2_color"]),
            )

        config = GameConfig(
            width=data["width"],
            height=data["height"],
            laps=data["laps"],
            difficulty=data["difficulty"],
            player1=p1,
            player2=p2,
        )

        run_game(config)
        return


def main():
    print("=== Simple Hungaroring Kart ===")
    width = ask_int("Screen width", 1280)
    height = ask_int("Screen height", 720)
    laps = ask_int("Number of laps", 3)

    difficulty = ask_str("AI difficulty (easy/medium/hard)", "medium").lower()
    if difficulty not in ["easy", "medium", "hard"]:
        difficulty = "medium"

    # Player 1 config
    print("\nConfigure Player 1 (default: arrows + RCTRL/RSHIFT)")
    p1_color = ask_color("Player 1 kart color", (255, 0, 0))
    p1 = PlayerConfig(
        name="Player 1",
        left_key=pygame.K_LEFT,
        right_key=pygame.K_RIGHT,
        accel_key=pygame.K_RCTRL,
        brake_key=pygame.K_RSHIFT,
        color=p1_color,
    )

    # Player 2?
    two_players = ask_str("Enable Player 2? (y/n)", "n").lower().startswith("y")
    p2 = None
    if two_players:
        print("\nConfigure Player 2 (default: A/D/W/S)")
        p2_color = ask_color("Player 2 kart color", (0, 0, 255))
        # For simplicity, fixed keys: A/D for left/right, W accel, S brake
        p2 = PlayerConfig(
            name="Player 2",
            left_key=pygame.K_a,
            right_key=pygame.K_d,
            accel_key=pygame.K_w,
            brake_key=pygame.K_s,
            color=p2_color,
        )

    config = GameConfig(
        width=width,
        height=height,
        laps=laps,
        difficulty=difficulty,
        player1=p1,
        player2=p2,
    )

    run_game(config)


if __name__ == "__main__":
    main()
