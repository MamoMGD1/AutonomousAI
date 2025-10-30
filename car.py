import pygame
import random
import math
import map  # Access to map module (map.py)
# Removed the incorrect line 'from car import Car'.

class Car:
    # Stable monotonically increasing id to break head-on ties
    next_id = 0
    def __init__(self, world, always_drive=False):
        """
        Car class constructor.
        world: A reference to the World object from map.py.
        This class is only for AI-controlled vehicles.
        """
        self.world = world
        self.always_drive = always_drive  # <-- Added always_drive flag

        # Assign stable car id
        self.car_id = Car.next_id
        Car.next_id += 1

        # Find the spawn point and set related grid/pixel coordinates
        self.grid_x, self.grid_y = self.find_spawn_point()
        self.pixel_x = self.grid_x * map.CELL_SIZE
        self.pixel_y = self.grid_y * map.CELL_SIZE

        # Load car image
        try:
            # Try to load images/car.png
            self.image_orig = pygame.image.load("images/car.png").convert_alpha()
        except pygame.error:
            # If not found, use a red square as default
            print("Warning: 'images/car.png' not found. Using a red square as default.")
            self.image_orig = pygame.Surface((map.CELL_SIZE, map.CELL_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(self.image_orig, (255, 0, 0, 200), (0, 0, map.CELL_SIZE, map.CELL_SIZE))

        # As large as possible -> Close to cell size (with a small margin)
        scale_factor = 0.9
        self.image_orig = pygame.transform.scale(self.image_orig, (int(map.CELL_SIZE * scale_factor), int(map.CELL_SIZE * scale_factor)))
        self.image = self.image_orig
        self.rect = self.image.get_rect(center=(self.pixel_x + map.CELL_SIZE // 2, self.pixel_y + map.CELL_SIZE // 2))

        # Physics and Movement
        # Each car has random speed and acceleration
        self.max_speed = random.uniform(1.5, 3.0)  # Pixels/frame
        self.speed = 0.0
        self.acceleration = random.uniform(0.05, 0.15) # Acceleration
        self.deceleration = 0.3  # Deceleration (braking)
        
        # ANGLE CORRECTION: Assumes image is facing RIGHT (East)
        self.angle = 0 # 0 degrees = Right (East)
        
        self.direction_vector = pygame.math.Vector2(0, 0) # Movement direction
        
        # State Machine
        self.state = 'stopped'  # 'driving', 'stopping', 'stopped'

        # Set initial direction
        if 0 <= self.grid_y < map.GRID_HEIGHT and 0 <= self.grid_x < map.GRID_WIDTH:
             self.current_tile = self.world.grid[self.grid_y][self.grid_x]
             self.set_initial_direction()
        else:
            self.respawn() # Spawned at invalid location, respawn

    def find_spawn_point(self):
        """Find a random valid road cell on the map to spawn the car."""
        road_tiles = []
        for r in range(map.GRID_HEIGHT):
            for c in range(map.GRID_WIDTH):
                tile = self.world.grid[r][c]
                # Only start on roads that have a lane direction (not intersections)
                if isinstance(tile, map.Road) and tile.direction is not None:
                    road_tiles.append((c, r)) # (x, y) -> (col, row)
        
        if road_tiles:
            return random.choice(road_tiles)
        else:
            # If no road cell is found, return (0, 0) and print an error
            print("Error: No road cell found in the map. (0, 0) is used.")
            return (0, 0)

    def set_initial_direction(self):
        """Set initial direction and angle based on the current tile (AI)."""
        if isinstance(self.current_tile, map.Road) and self.current_tile.direction:
            self.follow_road_direction(self.current_tile.direction)
            self.state = 'driving' # Start driving
        else:
            # If it's an intersection or an invalid location, choose a random direction
            self.follow_road_direction(random.choice(['N', 'S', 'E', 'W']))
            self.state = 'driving'

    def follow_road_direction(self, direction_str):
        """
        Set direction vector and angle for the given direction ('N','S','E','W').
        Assumes the car image is facing RIGHT (East).
        """
        if direction_str == 'N':
            self.direction_vector = pygame.math.Vector2(0, -1)
            self.angle = 0
        elif direction_str == 'S':
            self.direction_vector = pygame.math.Vector2(0, 1)
            self.angle = 180
        elif direction_str == 'E':
            self.direction_vector = pygame.math.Vector2(1, 0)
            self.angle = -90
        elif direction_str == 'W':
            self.direction_vector = pygame.math.Vector2(-1, 0)
            self.angle = 90

        # Snap to lane center on direction change to avoid corner cuts into grass
        # Align orthogonal axis to the center of the current grid cell
        if self.direction_vector.y != 0:  # Moving North/South → align X to lane center
            self.pixel_x = self.grid_x * map.CELL_SIZE
        elif self.direction_vector.x != 0:  # Moving East/West → align Y to lane center
            self.pixel_y = self.grid_y * map.CELL_SIZE

        # Refresh drawing center after snapping
        self.rect.center = (self.pixel_x + map.CELL_SIZE // 2, self.pixel_y + map.CELL_SIZE // 2)

    def look_ahead(self, other_cars, scan_distance=5):
        """
        Scans ahead and reports obstacles:
        - red_light: a crosswalk ahead with a red traffic light
        - car_ahead: another car occupying a cell in our path
        """
        if getattr(self, "always_drive", False):
            return None
        if self.direction_vector.length() == 0:
            return None

        # Scan the cells ahead for red lights; only the immediate next cell blocks for cars
        for i in range(1, scan_distance + 1):
            check_x = self.grid_x + int(self.direction_vector.x * i)
            check_y = self.grid_y + int(self.direction_vector.y * i)

            # If out of bounds, just stop scanning further (do not flag obstacle)
            if not (0 <= check_x < map.GRID_WIDTH and 0 <= check_y < map.GRID_HEIGHT):
                break

            # 1) Check for other cars ONLY in the immediate next cell to avoid far-look deadlocks
            if i == 1 and other_cars:
                for car in other_cars:
                    if car is not self and car.grid_x == check_x and car.grid_y == check_y:
                        # If we're head-on, yield based on stable id (lower id goes first)
                        if self.direction_vector == -car.direction_vector:
                            if self.car_id > car.car_id:
                                return 'car_ahead'  # we yield
                            else:
                                continue  # we have priority, don't block
                        # Otherwise (same direction), block
                        return 'car_ahead'

            tile = self.world.grid[check_y][check_x]

            # 2) Consider traffic lights at crosswalks
            if isinstance(tile, map.Crosswalk):
                light = self.find_correct_light(check_x, check_y)
                if light and light.state == 'red':
                    return 'red_light'
        return None

    def find_correct_light(self, cx, cy):
        """
        Find the correct traffic light associated with the crosswalk at (cx, cy).
        Searches to the sides perpendicular to the car's movement direction.
        """
        light = None
        # Perpendicular vectors to the direction (right/left)
        # Perpendicular of (x, y) is (-y, x) or (y, -x)
        perp_vec_1 = pygame.math.Vector2(self.direction_vector.y, -self.direction_vector.x)
        perp_vec_2 = pygame.math.Vector2(-self.direction_vector.y, self.direction_vector.x)

        # 1. Look to the right (e.g., 2 cells)
        for i in range(1, 3):
            lx, ly = cx + int(perp_vec_1.x * i), cy + int(perp_vec_1.y * i)
            if 0 <= lx < map.GRID_WIDTH and 0 <= ly < map.GRID_HEIGHT:
                tile = self.world.grid[ly][lx]
                if isinstance(tile, map.TrafficLight):
                    return tile # Found the light

        # 2. Look to the left (e.g., 2 cells)
        for i in range(1, 3):
            lx, ly = cx + int(perp_vec_2.x * i), cy + int(perp_vec_2.y * i)
            if 0 <= lx < map.GRID_WIDTH and 0 <= ly < map.GRID_HEIGHT:
                tile = self.world.grid[ly][lx]
                if isinstance(tile, map.TrafficLight):
                    return tile # Found the light
        
        return None # No light found for this crosswalk

    def update_state(self, obstacle):
        """Update state based on seen obstacle (red lights or cars cause stopping)."""
        if getattr(self, "always_drive", False):
            self.state = 'driving'
            return
        if self.state == 'driving':
            if obstacle in ('red_light', 'car_ahead'):
                self.state = 'stopping'
        elif self.state == 'stopping':
            if self.speed == 0:
                self.state = 'stopped'
            elif obstacle is None:
                self.state = 'driving'
        elif self.state == 'stopped':
            if obstacle is None:
                self.state = 'driving'

    def update_speed(self):
        """Update speed (accelerate/decelerate) based on current state."""
        
        if self.state == 'driving':
            # Accelerate towards the target speed (max_speed)
            self.speed = min(self.max_speed, self.speed + self.acceleration)
        elif self.state == 'stopping' or self.state == 'stopped':
            # Decelerate
            self.speed = max(0, self.speed - self.deceleration)

    def update_position(self, other_cars=None):
        """Update pixel position according to speed and direction."""
        if self.speed == 0:
            return

        # Update pixel position
        self.pixel_x += self.direction_vector.x * self.speed
        self.pixel_y += self.direction_vector.y * self.speed
        
        # Update car's center for drawing
        self.rect.center = (self.pixel_x + map.CELL_SIZE // 2, self.pixel_y + map.CELL_SIZE // 2)

        # Calculate which grid cell we are in based on pixel position
        new_grid_x = int(self.pixel_x / map.CELL_SIZE)
        new_grid_y = int(self.pixel_y / map.CELL_SIZE)

        # If we entered a new grid cell
        if new_grid_x != self.grid_x or new_grid_y != self.grid_y:
            self.grid_x = new_grid_x
            self.grid_y = new_grid_y
            # AI runs the new tile logic
            self.on_new_tile_ai(other_cars) 

    def on_new_tile_ai(self, other_cars):
        """Called when the car enters a new grid cell (handles turns and lane following)."""
        # If we went out of map bounds
        if not (0 <= self.grid_x < map.GRID_WIDTH and 0 <= self.grid_y < map.GRID_HEIGHT):
            self.respawn() # Respawn
            return

        new_tile = self.world.grid[self.grid_y][self.grid_x]
        self.current_tile = new_tile

        if isinstance(new_tile, map.Road):
            if new_tile.direction is None:
                # Reached an intersection
                self.handle_intersection(other_cars)
            else:
                # We are on a road with a direction, follow the road
                self.follow_road_direction(new_tile.direction)
        elif isinstance(new_tile, map.Crosswalk):
            # Crosswalk is also a road, continue (don't turn)
            pass
        else:
            # Went off the road (grass, building, etc.), respawn
            self.respawn()

    def handle_intersection(self, other_cars):
        """AI intersection handling: find valid and open directions and choose one (gridlock fix)."""
        possible_dirs = []
        current_dir_vec = self.direction_vector
        
        # Check all 4 possible directions
        # (move_dir, (dx, dy))
        moves = {'N': (0, -1), 'S': (0, 1), 'E': (1, 0), 'W': (-1, 0)}

        for move_dir_str, (dx, dy) in moves.items():
            nx, ny = self.grid_x + dx, self.grid_y + dy
            # Is it within map bounds?
            if 0 <= nx < map.GRID_WIDTH and 0 <= ny < map.GRID_HEIGHT:
                tile = self.world.grid[ny][nx]
                # Is it an adjacent road or crosswalk?
                if isinstance(tile, (map.Road, map.Crosswalk)):
                    # Prevent U-turn (going back to the direction you came from)
                    if pygame.math.Vector2(dx, dy) != -current_dir_vec:
                        
                        # --- Check if this path is open (AI gridlock fix) ---
                        # Is there a car in this direction (1 cell)?
                        is_blocked = False
                        if other_cars:
                            for car in other_cars:
                                if car != self and car.grid_x == nx and car.grid_y == ny:
                                    is_blocked = True
                                    break
                        
                        if not is_blocked:
                            possible_dirs.append(move_dir_str)
                        # --- End check ---

        if possible_dirs:
            # Prefer to go straight (if possible)
            straight_move_str = None
            if current_dir_vec.x == 1: straight_move_str = 'E'
            elif current_dir_vec.x == -1: straight_move_str = 'W'
            elif current_dir_vec.y == 1: straight_move_str = 'S'
            elif current_dir_vec.y == -1: straight_move_str = 'N'

            # 70% chance to go straight (if possible)
            if straight_move_str in possible_dirs and random.random() < 0.7: 
                chosen_dir = straight_move_str
            else:
                # If cannot go straight or decided to turn randomly
                chosen_dir = random.choice(possible_dirs)
            
            self.follow_road_direction(chosen_dir)
        else:
            # Stuck (e.g., dead end), make a U-turn
            if -current_dir_vec != pygame.math.Vector2(0, 0):
                self.direction_vector = -current_dir_vec
                # Angle correction
                self.angle = (self.angle + 180) % 360
            else:
                self.respawn() # Completely stuck

    def rotate_image(self):
        """
        Rotate the car image based on the current angle.
        Avoids continuous spin artifact by rotating the original image.
        """
        # Rotate the original image (to prevent quality loss)
        self.image = pygame.transform.rotate(self.image_orig, self.angle)
        # Set the center of the rotated image
        self.rect = self.image.get_rect(center=self.rect.center)

    def respawn(self):
        """Teleport the car to a random valid starting road cell on the map."""
        self.grid_x, self.grid_y = self.find_spawn_point()
        self.pixel_x = self.grid_x * map.CELL_SIZE
        self.pixel_y = self.grid_y * map.CELL_SIZE
        self.speed = 0
        self.state = 'stopped'
        
        if 0 <= self.grid_y < map.GRID_HEIGHT and 0 <= self.grid_x < map.GRID_WIDTH:
            self.current_tile = self.world.grid[self.grid_y][self.grid_x]
            self.set_initial_direction()
        else:
            print("Error: Respawn failed, no valid spawn point found.")

    # --- MAIN UPDATE ---

    def update(self, other_cars):
        """Main per-frame AI update for the car."""
        
        # 1. Look ahead (default AI scan is 5 cells)
        obstacle = self.look_ahead(other_cars, scan_distance=5)
        
        # 2. Update state (stop/go)
        self.update_state(obstacle)
        
        # 3. Update speed (accelerate/decelerate)
        self.update_speed()
        
        # 4. Update position (triggers on_new_tile_ai)
        self.update_position(other_cars)
        
        # 5. Rotate image
        self.rotate_image()

    def draw(self, screen):
        """Draw the car on the screen."""
        screen.blit(self.image, self.rect)
