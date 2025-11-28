import pygame
import sys
import random
from typing import Tuple, List, Dict, Union

# initialize pygame (safe to call again from main)
pygame.init()

# --- Grid-based Constants ---
CELL_SIZE = 17
GRID_WIDTH = 56
GRID_HEIGHT = 36

SCREEN_WIDTH = GRID_WIDTH * CELL_SIZE
SCREEN_HEIGHT = GRID_HEIGHT * CELL_SIZE
FPS = 60

# --- Professional palette ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# ground / surfaces
COLOR_GRASS_BASE = (55, 120, 55)
COLOR_ASPHALT = (45, 45, 50)
COLOR_MARKING = (250, 250, 250)
COLOR_SIDEWALK = (160, 160, 160)

# building colors
BUILDING_PALETTE = [
    (180, 160, 140), (140, 150, 160), (160, 140, 140),
    (150, 160, 140), (200, 190, 180), (120, 100, 100)
]
COLOR_WINDOW_LIT = (255, 240, 150)
COLOR_WINDOW_DARK = (40, 40, 50)

# traffic light colors
COLOR_RED_DIM = (100, 0, 0)
COLOR_RED_BRIGHT = (255, 50, 50)
COLOR_YELLOW_DIM = (100, 100, 0)
COLOR_YELLOW_BRIGHT = (255, 220, 0)
COLOR_GREEN_DIM = (0, 90, 0)
COLOR_GREEN_BRIGHT = (50, 255, 50)
COLOR_POLE = (30, 30, 30)


# --- Base tile class ---
class Tile:
    """Base class inherited by all grid elements."""
    def __init__(self, type_name: str):
        self.type = type_name

    def draw(self, screen: pygame.Surface, x: int, y: int):
        pass

    def __repr__(self):
        return f"<{self.type}>"


# --- Tile classes ---

class Road(Tile):
    def __init__(self, orientation: str = 'horizontal', direction: Union[str, None] = None):
        super().__init__('Road')
        self.orientation = orientation
        self.direction = direction

    def draw(self, screen: pygame.Surface, x: int, y: int):
        px, py = x * CELL_SIZE, y * CELL_SIZE

        # asphalt base
        pygame.draw.rect(screen, COLOR_ASPHALT, (px, py, CELL_SIZE, CELL_SIZE))

        # lane markings (improved)
        if self.direction:
            line_len = 5
            gap_len = 7
            thickness = 1

            if self.orientation == 'horizontal' and self.direction == 'W':
                cy = py + CELL_SIZE - 1
                for i in range(px, px + CELL_SIZE, line_len + gap_len):
                    pygame.draw.line(screen, COLOR_MARKING, (i, cy), (i + line_len, cy), thickness)

            elif self.orientation == 'vertical' and self.direction == 'S':
                cx = px + CELL_SIZE - 1
                for i in range(py, py + CELL_SIZE, line_len + gap_len):
                    pygame.draw.line(screen, COLOR_MARKING, (cx, i), (cx, i + line_len), thickness)


class Crosswalk(Tile):
    def __init__(self, orientation: str = 'horizontal'):
        super().__init__('Crosswalk')
        self.orientation = orientation

    def draw(self, screen: pygame.Surface, x: int, y: int):
        px, py = x * CELL_SIZE, y * CELL_SIZE

        # asphalt base
        pygame.draw.rect(screen, COLOR_ASPHALT, (px, py, CELL_SIZE, CELL_SIZE))

        # zebra stripes
        stripe_width = 3
        gap = 4

        if self.orientation == 'vertical':
            for i in range(2, CELL_SIZE - 2, stripe_width + gap):
                y_pos = py + i
                pygame.draw.rect(screen, COLOR_MARKING, (px + 2, y_pos, CELL_SIZE - 4, stripe_width))
        else:
            for i in range(2, CELL_SIZE - 2, stripe_width + gap):
                x_pos = px + i
                pygame.draw.rect(screen, COLOR_MARKING, (x_pos, py + 2, stripe_width, CELL_SIZE - 4))


class Building(Tile):
    def __init__(self, color: Tuple[int, int, int], width: int = 2, height: int = 2):
        super().__init__('Building')
        self.color = color
        self.width = width
        self.height = height

    def draw(self, screen: pygame.Surface, x: int, y: int):
        px, py = x * CELL_SIZE, y * CELL_SIZE
        w_px, h_px = self.width * CELL_SIZE, self.height * CELL_SIZE

        # sidewalk / base
        pygame.draw.rect(screen, COLOR_SIDEWALK, (px, py, w_px, h_px))

        # building body with shadow and depth
        margin = 3
        body_rect = (px + margin, py + margin, w_px - 2 * margin, h_px - 2 * margin)

        shadow_offset = 3
        pygame.draw.rect(screen, (30, 30, 30),
                         (px + margin + shadow_offset, py + margin + shadow_offset,
                          w_px - 2 * margin, h_px - 2 * margin), border_radius=3)

        pygame.draw.rect(screen, self.color, body_rect, border_radius=3)

        # roof detail (darker)
        roof_color = (max(0, self.color[0] - 40), max(0, self.color[1] - 40), max(0, self.color[2] - 40))
        pygame.draw.rect(screen, roof_color, (px + margin, py + margin, w_px - 2 * margin, 2), border_radius=3)

        # windows
        win_size = 3
        win_gap = 4

        cols = (w_px - 2 * margin) // (win_size + win_gap)
        rows = (h_px - 2 * margin) // (win_size + win_gap)

        for r in range(1, int(rows)):
            for c in range(1, int(cols)):
                wx = px + margin + c * (win_size + win_gap) - 2
                wy = py + margin + r * (win_size + win_gap) + 2

                is_lit = (x * y * r * c + pygame.time.get_ticks() // 1000) % 7 == 0
                win_color = COLOR_WINDOW_LIT if is_lit else COLOR_WINDOW_DARK

                if wx + win_size < px + w_px - margin and wy + win_size < py + h_px - margin:
                    pygame.draw.rect(screen, win_color, (wx, wy, win_size, win_size))


class Grass(Tile):
    def __init__(self):
        super().__init__('Grass')
        self.color = COLOR_GRASS_BASE
        self.has_tree = random.random() < 0.15
        self.tree_size = random.randint(3, 5)

    def draw(self, screen: pygame.Surface, x: int, y: int):
        px, py = x * CELL_SIZE, y * CELL_SIZE

        # base grass
        pygame.draw.rect(screen, self.color, (px, py, CELL_SIZE, CELL_SIZE))

        if self.has_tree:
            cx, cy = px + CELL_SIZE // 2, py + CELL_SIZE // 2
            pygame.draw.circle(screen, (50, 40, 20), (cx + 1, cy + 3), 2)  # trunk / shadow
            pygame.draw.circle(screen, (34, 100, 34), (cx, cy), self.tree_size)  # leaves
            pygame.draw.circle(screen, (60, 140, 60), (cx - 1, cy - 1), self.tree_size // 2)  # leaf highlight


class TrafficLight(Tile):
    def __init__(self, initial_state: str = None, state_duration: Dict[str, int] = None, base_tile: Tile = None):
        super().__init__('TrafficLight')
        # initialize with a random state if not provided
        self.state = initial_state if initial_state in ('red', 'yellow', 'green') else random.choice(['red', 'yellow', 'green'])
        self.timer = 0
        # if durations provided use them, otherwise create per-light randomized durations
        self.state_duration = state_duration if state_duration else {'red': 180, 'yellow': 60, 'green': 300}
        
        self.group_id: Union[int, None] = None
        # tile to draw beneath the pole (preserve underlying tile like grass/road)
        self.base_tile = base_tile

    def update(self):
        """Advance this light independently when its timer expires."""
        self.timer += 1
        dur = self.state_duration.get(self.state)
        if self.timer >= dur:
            # cycle: red -> green -> yellow -> red
            if self.state == 'red':
                self.state = 'green'
            elif self.state == 'green':
                self.state = 'yellow'
            elif self.state == 'yellow':
                self.state = 'red'
            self.timer = 0

    def set_state(self, new_state: str):
        self.state = new_state
        self.timer = 0

    def draw(self, screen: pygame.Surface, x: int, y: int):
        px, py = x * CELL_SIZE, y * CELL_SIZE

        # draw underlying tile (grass/road/crosswalk) if available
        if self.base_tile:
            try:
                self.base_tile.draw(screen, x, y)
            except Exception:
                pygame.draw.rect(screen, COLOR_SIDEWALK, (px, py, CELL_SIZE, CELL_SIZE))

        # draw only the small pole/box and lights on top (no full-tile opaque background)
        box_w, box_h = 6, 14
        bx, by = px + (CELL_SIZE - box_w) // 2, py + (CELL_SIZE - box_h) // 2

        # subtle shadow under the box
        pygame.draw.rect(screen, (0, 0, 0), (bx + 1, by + 1, box_w, box_h), border_radius=2)
        pygame.draw.rect(screen, COLOR_POLE, (bx, by, box_w, box_h), border_radius=2)

        # lights (with bright/dim states)
        r_col = COLOR_RED_BRIGHT if self.state == 'red' else COLOR_RED_DIM
        y_col = COLOR_YELLOW_BRIGHT if self.state == 'yellow' else COLOR_YELLOW_DIM
        g_col = COLOR_GREEN_BRIGHT if self.state == 'green' else COLOR_GREEN_DIM

        cx = bx + box_w // 2

        pygame.draw.circle(screen, r_col, (cx, by + 3), 2)
        if self.state == 'red':
            pygame.draw.circle(screen, (255, 100, 100, 150), (cx, by + 3), 1)

        pygame.draw.circle(screen, y_col, (cx, by + 7), 2)
        pygame.draw.circle(screen, g_col, (cx, by + 11), 2)
        if self.state == 'green':
            pygame.draw.circle(screen, (100, 255, 100, 150), (cx, by + 11), 1)


# --- World class ---
class World:
    def __init__(self, width: int, height: int):
        self.grid_width = width
        self.grid_height = height
        self.grid: List[List[Tile]] = [[Grass() for _ in range(width)] for _ in range(height)]
        # remove grouped traffic light structures; lights are independent now
        self.default_duration = {'red': 180, 'yellow': 60, 'green': 300}

        self._generate_grid()
        # keep _organize_lights for compatibility but it will not group/synchronize lights
        self._organize_lights()

    def get_original_tile(self, r: int, c: int) -> Road:
        """Helper to return a default Road object when needed."""
        # This is a lightweight helper returning a default Road instance.
        return Road(direction=None)

    def _paint_road(self, r1: int, c1: int, r2: int, c2: int):
        if c1 == c2:
            for r in range(min(r1, r2), max(r1, r2) + 1):
                if 0 <= r < self.grid_height and 0 <= c1 < self.grid_width:
                    self.grid[r][c1] = Road('vertical', 'S')
                if 0 <= r < self.grid_height and 0 <= c1 + 1 < self.grid_width:
                    self.grid[r][c1 + 1] = Road('vertical', 'N')
        elif r1 == r2:
            for c in range(min(c1, c2), max(c1, c2) + 1):
                if 0 <= r1 < self.grid_height and 0 <= c < self.grid_width:
                    self.grid[r1][c] = Road('horizontal', 'W')
                if 0 <= r1 + 1 < self.grid_height and 0 <= c < self.grid_width:
                    self.grid[r1 + 1][c] = Road('horizontal', 'E')

    def _place_crosswalk_and_light(self, r: int, c: int, orientation: str, light_state: str = None, position: str = 'default'):
        """
        Place crosswalks and a TrafficLight. Lights are initialized with random states/durations
        and preserve whatever tile was under them (grass/road).
        """
        if orientation == 'vertical':
            if 0 <= r < self.grid_height and 0 <= c < self.grid_width: self.grid[r][c] = Crosswalk('vertical')
            if 0 <= r < self.grid_height and 0 <= c + 1 < self.grid_width: self.grid[r][c + 1] = Crosswalk('vertical')

            if position == 'top-right' or position == 'default': light_pos = (r, c + 2)
            elif position == 'top-left': light_pos = (r, c - 1)
            elif position == 'bottom-right': light_pos = (r + 1, c + 2)
            elif position == 'bottom-left': light_pos = (r, c - 1)
            else: light_pos = (r, c + 2)

            lr, lc = light_pos
            if 0 <= lr < self.grid_height and 0 <= lc < self.grid_width:
                # preserve underlying tile (grass, road, etc.)
                base = self.grid[lr][lc] if self.grid[lr][lc] is not None else Grass()
                # initialize light randomly (ignore synchronized grouping)
                initial = random.choice(['red', 'yellow', 'green'])
                
                self.grid[lr][lc] = TrafficLight(initial_state=initial, state_duration=self.default_duration, base_tile=base)

        else:  # horizontal
            if 0 <= r < self.grid_height and 0 <= c < self.grid_width: self.grid[r][c] = Crosswalk('horizontal')
            if 0 <= r + 1 < self.grid_height and 0 <= c < self.grid_width: self.grid[r + 1][c] = Crosswalk('horizontal')

            if position == 'bottom-right' or position == 'default': light_pos = (r + 2, c)
            elif position == 'top-right': light_pos = (r - 1, c)
            elif position == 'bottom-left': light_pos = (r + 2, c)
            elif position == 'top-left': light_pos = (r - 1, c)
            else: light_pos = (r + 2, c)

            lr, lc = light_pos
            if 0 <= lr < self.grid_height and 0 <= lc < self.grid_width:
                base = self.grid[lr][lc] if self.grid[lr][lc] is not None else Grass()
                initial = random.choice(['red', 'yellow', 'green'])
                durations = {
                    'red': random.randint(150, 360),
                    'yellow': random.randint(40, 90),
                    'green': random.randint(150, 360)
                }
                self.grid[lr][lc] = TrafficLight(initial_state=initial, state_duration=durations, base_tile=base)

    def _organize_lights(self):
        """No grouping: lights remain independent. This method kept for compatibility."""
        return

    def update(self):
        """Update dynamic elements. Each TrafficLight updates independently."""
        # Update all traffic lights independently
        for r in range(self.grid_height):
            for c in range(self.grid_width):
                tile = self.grid[r][c]
                if isinstance(tile, TrafficLight):
                    tile.update()

    def draw(self, screen: pygame.Surface):
        """Draw the entire world grid."""
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                tile = self.grid[y][x]
                tile.draw(screen, x, y)

    def _put_intersection(self, r: int, c: int):
        """Mark a 2x2 block as an intersection by clearing direction flags on roads."""
        if 0 <= r < self.grid_height and 0 <= c < self.grid_width and isinstance(self.grid[r][c], Road):
            self.grid[r][c].direction = None
        if 0 <= r + 1 < self.grid_height and 0 <= c < self.grid_width and isinstance(self.grid[r + 1][c], Road):
            self.grid[r + 1][c].direction = None
        if 0 <= r < self.grid_height and 0 <= c + 1 < self.grid_width and isinstance(self.grid[r][c + 1], Road):
            self.grid[r][c + 1].direction = None
        if 0 <= r + 1 < self.grid_height and 0 <= c + 1 < self.grid_width and isinstance(self.grid[r + 1][c + 1], Road):
            self.grid[r + 1][c + 1].direction = None

    def _generate_grid(self):
        """Create the map layout: paint roads, place intersections, crosswalks, lights and buildings."""
        # major road segments
        self._paint_road(0, 6, 17, 6)
        self._paint_road(20, 6, 34, 6)
        self._paint_road(6, 12, 9, 12)
        self._paint_road(4, 18, 5, 18)
        self._paint_road(8, 18, self.grid_height - 1, 18)
        self._paint_road(0, 32, 28, 32)
        self._paint_road(6, 44, self.grid_height - 1, 44)
        self._paint_road(0, 53, 3, 53)
        self._paint_road(14, 53, 19, 53)
        self._paint_road(12, 26, 19, 26)
        self._paint_road(16, 13, 19, 13)
        self._paint_road(22, 39, 25, 39)

        self._paint_road(4, 0, 4, 42)
        self._paint_road(4, 44, 4, 46)
        self._paint_road(4, 46, 4, self.grid_width - 1)

        self._paint_road(12, 0, 12, 25)
        self._paint_road(12, 34, 12, self.grid_width - 1)

        self._paint_road(20, 8, 20, 27)
        self._paint_road(20, 32, 20, self.grid_width - 1)

        self._paint_road(28, 0, 28, 16)
        self._paint_road(28, 20, 28, 42)
        self._paint_road(28, 46, 28, self.grid_width - 1)

        self._paint_road(8, 14, 8, 17)
        self._paint_road(33, 0, 33, 5)
        self._paint_road(16, 8, 16, 12)
        self._paint_road(24, 34, 24, 38)

        # place intersections and attach crosswalks + lights
        intersections_4way = [
            (4, 6, 'green'), (4, 32, 'yellow'), (12, 6, 'red'),
            (12, 44, 'yellow'), (20, 18, 'green'), (20, 32, 'red'),
            (20, 44, 'green'), (28, 6, 'red'), (28, 18, 'green'),
            (28, 32, 'red'), (28, 44, 'green'),
        ]

        for r, c, state in intersections_4way:
            self._put_intersection(r, c)
            # crosswalks + lights around the intersection
            self._place_crosswalk_and_light(r - 1, c, 'vertical', state, 'top-right')
            self._place_crosswalk_and_light(r + 2, c, 'vertical', 'green' if state == 'red' else 'red', 'bottom-left')
            self._place_crosswalk_and_light(r, c - 1, 'horizontal', 'green' if state == 'red' else 'red', 'top-left')
            self._place_crosswalk_and_light(r, c + 2, 'horizontal', state, 'bottom-right')

        # T-junctions
        t_junctions = [
            (4, 32, 'green'), (4, 44, 'red'), (12, 18, 'green'),
            (12, 32, 'yellow'), (12, 44, 'red'),
        ]
        for r, c, state in t_junctions:
            self._put_intersection(r, c)
            if r > 1 and isinstance(self.grid[r - 2][c], Road):
                self._place_crosswalk_and_light(r - 1, c, 'vertical', state)
            if r + 3 < self.grid_height and isinstance(self.grid[r + 3][c], Road):
                self._place_crosswalk_and_light(r + 2, c, 'vertical', 'green' if state == 'red' else 'red')
            if c > 1 and isinstance(self.grid[r][c - 2], Road):
                self._place_crosswalk_and_light(r, c - 1, 'horizontal', state)
            if c + 3 < self.grid_width and isinstance(self.grid[r][c + 3], Road):
                self._place_crosswalk_and_light(r, c + 2, 'horizontal', 'green' if state == 'red' else 'red')

        # additional intersections to ensure connectivity
        l_turns = [
            (20, 26), (20, 13), (20, 6), (24, 32), (20, 53), (12, 53),
            (33, 6), (4, 12), (4, 53), (8, 12), (8, 18), (12, 26),
            (20, 39), (24, 39), (16, 13), (16, 6),
        ]
        for r, c in l_turns:
            self._put_intersection(r, c)

        # place buildings near roads with some probability
        for r in range(self.grid_height):
            for c in range(self.grid_width):
                tile = self.grid[r][c]
                if not isinstance(tile, Grass):
                    continue

                # check adjacency to road/crosswalk
                is_near_road = False
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.grid_height and 0 <= nc < self.grid_width:
                            if isinstance(self.grid[nr][nc], (Road, Crosswalk)):
                                # avoid placing building on a true intersection cell with direction=None
                                near_tile = self.grid[nr][nc]
                                if not (isinstance(near_tile, Road) and near_tile.direction is None):
                                    is_near_road = True
                                    break
                    if is_near_road:
                        break

                if is_near_road and random.random() <= 0.30:
                    color = random.choice(BUILDING_PALETTE)
                    self.grid[r][c] = Building(color)