import pygame
import map
from car import Car  # uses your existing Car implementation

class Agent(Car):
    """
    Automated-only Agent that inherits Car.
    - No manual/keyboard control.
    - Spawn coordinates can be set after construction using set_position(row, col).
    - Give it a path after instantiation using move(path), where path is a list of (row, col) tuples.
    - Agent will follow the path while still obeying car-world rules (lights, pedestrians, collisions).
    """

    def __init__(self, world, spawn=None):
        """
        world: World instance (map.World)
        spawn: optional (row, col) grid coordinate to place the agent immediately.
               If None, Car.find_spawn_point() will be used (via Car.__init__).
        """
        # Initialize like a normal Car (this will choose a random spawn internally)
        super().__init__(world, always_drive=False)

        # Make this an "agent" (slightly different image/size)
        try:
            self.image_orig = pygame.image.load("images/agent.png").convert_alpha()
        except pygame.error:
            # fallback
            self.image_orig = pygame.Surface((map.CELL_SIZE, map.CELL_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(self.image_orig, (255, 0, 0, 200), (0, 0, map.CELL_SIZE, map.CELL_SIZE))

        # scale agent image slightly larger than cars
        scale_factor = 1.75
        self.image_orig = pygame.transform.scale(
            self.image_orig,
            (int(map.CELL_SIZE * scale_factor), int(map.CELL_SIZE * scale_factor))
        )
        self.image = self.image_orig
        self.rect = self.image.get_rect(center=(self.pixel_x + map.CELL_SIZE // 2, self.pixel_y + map.CELL_SIZE // 2))

        # Agent-specific tuning (can be adjusted)
        self.max_speed = 3.0   # keep in realistic range similar to Car
        self.acceleration = 0.12
        self.deceleration = 0.35

        # Path-following state
        self.path = []           # list of (row, col)
        self.path_index = 0
        self.path_threshold = map.CELL_SIZE * 0.25  # pixels: when close enough to target cell center
        self.is_active = False   # True when a path is set and agent should move

        # Agent identity (optional)
        self.is_agent = True

        # If spawn provided, override initial spawn
        if spawn is not None:
            try:
                gy, gx = int(spawn[0]), int(spawn[1])
                self.set_position(gy, gx)
            except Exception:
                # if invalid spawn, keep whatever Car already set
                pass

        # Force driving state so it starts moving when path set
        self.state = 'stopped'
        self.rotate_image()

    # ------------------------------
    # External API
    # ------------------------------
    def set_position(self, grid_y, grid_x):
        """
        Place the agent at a specific grid cell immediately.
        Validates that the target tile is Road or Crosswalk before placing.
        """
        if not (0 <= grid_x < map.GRID_WIDTH and 0 <= grid_y < map.GRID_HEIGHT):
            raise ValueError("set_position: coordinates outside map bounds")

        tile = self.world.grid[grid_y][grid_x]
        if not isinstance(tile, (map.Road, map.Crosswalk)):
            raise ValueError("set_position: target tile is not road or crosswalk")

        # Set grid/pixel positions
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.pixel_x = self.grid_x * map.CELL_SIZE
        self.pixel_y = self.grid_y * map.CELL_SIZE
        self.rect.center = (self.pixel_x + map.CELL_SIZE // 2, self.pixel_y + map.CELL_SIZE // 2)

        # Update current tile & orientation
        self.current_tile = tile
        self.set_initial_direction()

    def move(self, path):
        """
        Give the agent a path to follow.
        Path: list of (row, col) grid coordinates.
        Example: [(10,15), (10,16), (11,16)]
        This can be called at any time after instantiation.
        """
        if not path:
            # clear any existing path
            self.path = []
            self.path_index = 0
            self.is_active = False
            self.state = 'stopped'
            self.speed = 0
            return

        # validate and normalize path entries to ints
        new_path = []
        for p in path:
            if not (isinstance(p, (tuple, list)) and len(p) == 2):
                raise ValueError("Each path element must be a (row, col) tuple")
            new_path.append((int(p[0]), int(p[1])))

        self.path = new_path
        self.path_index = 0
        self.is_active = True
        self.state = 'driving'  # start driving state; Car logic will manage speed/braking

        # quick safety: if path start is different from current location,
        # allow following from current position toward first target
        # (do not teleport)
        return

    # ------------------------------
    # Internal helpers
    # ------------------------------
    def _target_cell_center_pixels(self, grid_y, grid_x):
        """Return pixel center (x, y) for a grid cell."""
        cx = grid_x * map.CELL_SIZE + map.CELL_SIZE // 2
        cy = grid_y * map.CELL_SIZE + map.CELL_SIZE // 2
        return (cx, cy)

    def _set_cardinal_direction_towards(self, target_grid_y, target_grid_x):
        """
        Decide a CARDINAL direction (N,S,E,W) toward the target grid cell
        relative to current grid cell. This keeps compatibility with Car.look_ahead().
        If target is non-adjacent, choose the dominant axis.
        """
        dy = target_grid_y - self.grid_y
        dx = target_grid_x - self.grid_x

        # If exactly same cell - no change
        if dy == 0 and dx == 0:
            return

        # Prefer moving along the axis with larger absolute difference (dominant axis)
        if abs(dx) >= abs(dy):
            if dx > 0:
                self.follow_road_direction('E')
            else:
                self.follow_road_direction('W')
        else:
            if dy > 0:
                self.follow_road_direction('S')
            else:
                self.follow_road_direction('N')

    # ------------------------------
    # Overriding update()
    # ------------------------------
    def update(self, other_cars):
        """
        Main per-frame update for the Agent.
        - If agent has a path, compute the next target & set cardinal direction.
        - Then reuse Car's obstacle/speed/position logic.
        """
        # If no active path, fallback to Car behavior (idle)
        if not self.is_active or not self.path or self.path_index >= len(self.path):
            # Ensure stopped when no path
            self.is_active = False
            self.state = 'stopped'
            self.speed = 0
            self.rotate_image()
            return

        # Determine current target cell
        target_grid_y, target_grid_x = self.path[self.path_index]
        target_px, target_py = self._target_cell_center_pixels(target_grid_y, target_grid_x)

        # Distance from agent center to target center (pixels)
        agent_center = pygame.math.Vector2(self.pixel_x + map.CELL_SIZE // 2,
                                           self.pixel_y + map.CELL_SIZE // 2)
        target_center = pygame.math.Vector2(target_px, target_py)
        vec = target_center - agent_center
        dist = vec.length()

        # If close enough to the center of the target cell, advance index
        if dist <= max(self.path_threshold, map.CELL_SIZE * 0.12):
            self.path_index += 1
            # If finished path, stop
            if self.path_index >= len(self.path):
                self.is_active = False
                self.state = 'stopped'
                self.speed = 0
                self.rotate_image()
                return
            # else update new target
            target_grid_y, target_grid_x = self.path[self.path_index]
            target_px, target_py = self._target_cell_center_pixels(target_grid_y, target_grid_x)
            target_center = pygame.math.Vector2(target_px, target_py)
            vec = target_center - agent_center
            dist = vec.length()

        # Set CARDINAL direction toward the next grid step to remain compatible
        # with the grid-based look_ahead and intersection logic from Car.
        self._set_cardinal_direction_towards(target_grid_y, target_grid_x)

        # 1. Run Car look-ahead -> obstacle_info
        obstacle_info = self.look_ahead(other_cars, scan_distance=5)

        # 2. Update state based on obstacle_info
        self.update_state(obstacle_info)

        # 3. Update speed (braking/accelerating)
        self.update_speed(obstacle_info)

        # 4. Update position (handles collisions, grid updates, on_new_tile_ai)
        self.update_position(other_cars)

        # 5. Rotate image to match angle
        self.rotate_image()

    # ------------------------------
    # Optional: convenience for debugging / forcing stop
    # ------------------------------
    def stop(self):
        """Immediate stop and clear path."""
        self.path = []
        self.path_index = 0
        self.is_active = False
        self.state = 'stopped'
        self.speed = 0