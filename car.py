import pygame
import random
import map  # Access to map module (map.py)

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
        self.always_drive = always_drive
        self.needs_reroute = False

        # Assign stable car id
        self.car_id = Car.next_id
        Car.next_id += 1

        # Find the spawn point and set related grid/pixel coordinates
        self.grid_y, self.grid_x = self.find_spawn_point()
        self.pixel_x = self.grid_x * map.CELL_SIZE
        self.pixel_y = self.grid_y * map.CELL_SIZE

        # Load car image
        try:
            # Try to load images/car.png
            self.image_orig = pygame.image.load("images/car.png").convert_alpha()
        except pygame.error:
            # If not found, use a red square as default
            print("Warning: 'images/car.png' not found. Using a blue square as default.")
            self.image_orig = pygame.Surface((map.CELL_SIZE, map.CELL_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(self.image_orig, (0, 0, 255, 200), (0, 0, map.CELL_SIZE, map.CELL_SIZE))

        # As large as possible -> Close to cell size (with a small margin)
        scale_factor = 1.5
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

        # Add stuck detection
        self.stuck_timer = 0
        self.max_stuck_time = 6 * map.FPS  # 6 seconds at 60 FPS
        self.last_position = (0, 0)

    def find_spawn_point(self):
        """Find a random valid road cell on the map to spawn the car."""
        road_tiles = []
        for r in range(map.GRID_HEIGHT):
            for c in range(map.GRID_WIDTH):
                tile = self.world.grid[r][c]
                # Only start on roads that have a lane direction (not intersections)
                if isinstance(tile, map.Road) and tile.direction is not None:
                    road_tiles.append((r, c)) # (y, x) -> (col, row)
        
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
        Returns: (obstacle_type, distance) or None
        """
        if getattr(self, "always_drive", False):
            return None
        if self.direction_vector.length() == 0:
            return None

        for i in range(1, scan_distance + 1):
            check_x = self.grid_x + int(self.direction_vector.x * i)
            check_y = self.grid_y + int(self.direction_vector.y * i)

            if not (0 <= check_x < map.GRID_WIDTH and 0 <= check_y < map.GRID_HEIGHT):
                break

            tile = self.world.grid[check_y][check_x]

            # CHECK CROSSWALK/PEDESTRIANS FIRST (highest priority)
            if isinstance(tile, map.Crosswalk):
                # Check for pedestrians (law-breakers or legal crossers)
                if hasattr(self.world, "pedestrian_manager") and self.world.pedestrian_manager:
                    for ped in self.world.pedestrian_manager.group:
                        # Calculate pedestrian's grid position from pixel position
                        ped_grid_x = int(ped.rect.centerx // map.CELL_SIZE)
                        ped_grid_y = int(ped.rect.centery // map.CELL_SIZE)
                        
                        if ped_grid_x == check_x and ped_grid_y == check_y:
                            return ('pedestrian', i)  # ← Stop for pedestrians!

                # Then check traffic light
                light = self.find_correct_light(check_y, check_x)
                if light and light.state == 'red':
                    return ('red_light', i)

            # CHECK CARS AFTER (lower priority than pedestrians)
            if other_cars:
                for car in other_cars:
                    if car is not self and car.grid_x == check_x and car.grid_y == check_y:
                        return ('car_ahead', i)
        
        return None

    def find_correct_light(self, crow, ccol):
        """
        Find the traffic light to the RIGHT of the crosswalk (from car's perspective).
        crow = row, ccol = col of the crosswalk
        """
        # Determine which direction to look based on car's movement
        if self.direction_vector.y == -1:  # Moving North
            # Light should be to the right: col + 1
            light_row, light_col = crow, ccol + 1
        elif self.direction_vector.y == 1:  # Moving South
            # Light should be to the right: col - 1
            light_row, light_col = crow, ccol - 1
        elif self.direction_vector.x == -1:  # Moving West
            # Light should be to the right: row - 1
            light_row, light_col = crow - 1, ccol
        elif self.direction_vector.x == 1:  # Moving East
            # Light should be to the right: row + 1
            light_row, light_col = crow + 1, ccol
        else:
            return None
        
        # Check if that position is valid and has a traffic light
        if 0 <= light_row < map.GRID_HEIGHT and 0 <= light_col < map.GRID_WIDTH:
            tile = self.world.grid[light_row][light_col]
            if isinstance(tile, map.TrafficLight):
                return tile
        
        return None

    def update_state(self, obstacle_info):
        """Update state based on obstacle and its distance."""
        if getattr(self, "always_drive", False):
            self.state = 'driving'
            return
        
        if obstacle_info is None:
            # No obstacle, drive normally
            if self.state in ('stopping', 'stopped'):
                self.state = 'driving'
        else:
            obstacle_type, distance = obstacle_info
            
            # If very close (1 cell away) and still moving, must stop
            if distance == 1:
                if self.state == 'driving':
                    self.state = 'stopping'
                elif self.state == 'stopping' and self.speed == 0:
                    self.state = 'stopped'
            else:
                # Far away, start gradual braking
                if self.state == 'driving':
                    self.state = 'braking'  # New state for gradual slowdown

    def update_speed(self, obstacle_info=None):
        """Update speed based on state and distance to obstacle."""
        
        if self.state == 'driving':
            # Accelerate towards max speed
            self.speed = min(self.max_speed, self.speed + self.acceleration)
        
        elif self.state == 'braking':
            # NEW: Gradual braking based on distance
            if obstacle_info:
                obstacle_type, distance = obstacle_info
                # Calculate target speed based on distance
                # At distance 5: slow down to 80% speed
                # At distance 3: slow down to 50% speed
                # At distance 2: slow down to 30% speed
                # At distance 1: stop
                
                if distance >= 4:
                    target_speed = self.max_speed * 0.7
                elif distance == 3:
                    target_speed = self.max_speed * 0.5
                elif distance == 2:
                    target_speed = self.max_speed * 0.3
                else:  # distance == 1
                    target_speed = 0
                    self.state = 'stopping'
                
                # Gradually adjust to target speed
                if self.speed > target_speed:
                    self.speed = max(target_speed, self.speed - self.deceleration)
                else:
                    self.speed = min(target_speed, self.speed + self.acceleration)
            else:
                # No obstacle info, resume driving
                self.state = 'driving'
        
        elif self.state == 'stopping':
            # Hard brake to full stop
            self.speed = max(0, self.speed - self.deceleration)
            if self.speed == 0:
                self.state = 'stopped'
        
        elif self.state == 'stopped':
            self.speed = 0

    def update_position(self, other_cars=None):
        """Update pixel position according to speed and direction."""
        
        # Track if we're stuck (not moving)
        current_pos = (int(self.pixel_x), int(self.pixel_y))
        if current_pos == self.last_position:
            self.stuck_timer += 1
            
            # After 7 seconds (420 frames at 60 FPS), force movement
            if self.stuck_timer > 420:
                # Force the car to find a new direction NOW
                self.force_find_new_direction(other_cars)
                self.stuck_timer = 0
                return
        else:
            self.stuck_timer = 0  # Reset if moving
            self.last_position = current_pos
        
        if self.speed == 0:
            return

        # Calculate next position
        next_pixel_x = self.pixel_x + self.direction_vector.x * self.speed
        next_pixel_y = self.pixel_y + self.direction_vector.y * self.speed
        
        # Create a smaller collision box
        collision_shrink_w = 1.55
        collision_shrink_h = 0.55
        if abs(self.direction_vector.x) > 0:  # horizontal (east/west)
            smaller_width = int(map.CELL_SIZE * collision_shrink_w)
            smaller_height = int(map.CELL_SIZE * collision_shrink_h)
        else:  # vertical (north/south)
            smaller_width = int(map.CELL_SIZE * collision_shrink_h)
            smaller_height = int(map.CELL_SIZE * collision_shrink_w)
        
        next_collision_rect = pygame.Rect(0, 0, smaller_width, smaller_height)
        next_collision_rect.center = (next_pixel_x + map.CELL_SIZE // 2, next_pixel_y + map.CELL_SIZE // 2)

        # Check pixel-level collision with other cars
        collision_detected = False
        if other_cars:
            for car in other_cars:
                if car is self:
                    continue
                
                # Create smaller collision box for the other car
                other_collision_rect = pygame.Rect(0, 0, smaller_width, smaller_height)
                other_collision_rect.center = car.rect.center
                
                # If collision detected
                if next_collision_rect.colliderect(other_collision_rect):
                    # Calculate current distance and next distance
                    current_distance_sq = (self.pixel_x - car.pixel_x)**2 + (self.pixel_y - car.pixel_y)**2
                    next_distance_sq = (next_pixel_x - car.pixel_x)**2 + (next_pixel_y - car.pixel_y)**2
                    
                    # If moving AWAY, allow escape
                    if next_distance_sq > current_distance_sq:
                        continue
                    
                    collision_detected = True
                    break
        
        if collision_detected:
            self.speed = max(0, self.speed - self.deceleration * 3)
            self.state = 'stopped' if self.speed == 0 else 'stopping'
            return

        # No collision - apply movement
        self.pixel_x = next_pixel_x
        self.pixel_y = next_pixel_y
        
        self.rect.center = (self.pixel_x + map.CELL_SIZE // 2, self.pixel_y + map.CELL_SIZE // 2)

        new_grid_x = int(self.pixel_x / map.CELL_SIZE)
        new_grid_y = int(self.pixel_y / map.CELL_SIZE)

        if new_grid_x != self.grid_x or new_grid_y != self.grid_y:
            self.grid_x = new_grid_x
            self.grid_y = new_grid_y
            self.on_new_tile_ai(other_cars)

    def force_find_new_direction(self, other_cars):
        """Force the car to find and move in an open direction when stuck."""
        
        # Check all 4 directions for an open path
        moves = [
            ('N', (0, -1)),
            ('S', (0, 1)),
            ('E', (1, 0)),
            ('W', (-1, 0))
        ]
        
        open_directions = []
        
        for move_dir_str, (dx, dy) in moves:
            nx = self.grid_x + dx
            ny = self.grid_y + dy
            
            # Check if within bounds
            if not (0 <= nx < map.GRID_WIDTH and 0 <= ny < map.GRID_HEIGHT):
                continue
            
            tile = self.world.grid[ny][nx]
            
            # Check if it's a valid road/crosswalk
            if not isinstance(tile, (map.Road, map.Crosswalk)):
                continue
            
            # Check if blocked by another car
            is_blocked = False
            if other_cars:
                for car in other_cars:
                    if car is not self and car.grid_x == nx and car.grid_y == ny:
                        is_blocked = True
                        break
            
            if not is_blocked:
                open_directions.append(move_dir_str)
        
        # Choose a direction
        if open_directions:
            # Prefer any direction that's not a U-turn
            current_opposite = None
            if self.direction_vector.x == 1: current_opposite = 'W'
            elif self.direction_vector.x == -1: current_opposite = 'E'
            elif self.direction_vector.y == 1: current_opposite = 'N'
            elif self.direction_vector.y == -1: current_opposite = 'S'
            
            # Remove U-turn if other options exist
            if current_opposite in open_directions and len(open_directions) > 1:
                open_directions.remove(current_opposite)
            
            chosen_dir = random.choice(open_directions)
            self.follow_road_direction(chosen_dir)
            
            # Force the car to start moving
            self.state = 'driving'
            self.speed = self.max_speed * 0.5  # Give it decent speed
            
        else:
            # ALL directions blocked - make a U-turn anyway
            if self.direction_vector.x == 1: self.follow_road_direction('W')
            elif self.direction_vector.x == -1: self.follow_road_direction('E')
            elif self.direction_vector.y == 1: self.follow_road_direction('N')
            elif self.direction_vector.y == -1: self.follow_road_direction('S')
            
            self.state = 'driving'
            self.speed = self.max_speed * 0.5
            
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
                        
                        # Check if this path is open
                        is_blocked = False
                        if other_cars:
                            for car in other_cars:
                                if car != self and car.grid_x == nx and car.grid_y == ny:
                                    is_blocked = True
                                    break
                        
                        if not is_blocked:
                            possible_dirs.append(move_dir_str)

        if possible_dirs:
            # If we need to reroute (collision happened), AVOID going straight
            if getattr(self, 'needs_reroute', False):
                straight_move_str = None
                if current_dir_vec.x == 1: straight_move_str = 'E'
                elif current_dir_vec.x == -1: straight_move_str = 'W'
                elif current_dir_vec.y == 1: straight_move_str = 'S'
                elif current_dir_vec.y == -1: straight_move_str = 'N'
                
                # Remove straight direction from options (force a turn)
                if straight_move_str and straight_move_str in possible_dirs:
                    possible_dirs.remove(straight_move_str)
                
                # If still have options after removing straight, pick one
                if possible_dirs:
                    chosen_dir = random.choice(possible_dirs)
                else:
                    # No choice but to go straight or turn around
                    chosen_dir = straight_move_str if straight_move_str else random.choice(['N', 'S', 'E', 'W'])
                
                self.needs_reroute = False  # Reset flag
            else:
                # Normal intersection behavior (prefer straight)
                straight_move_str = None
                if current_dir_vec.x == 1: straight_move_str = 'E'
                elif current_dir_vec.x == -1: straight_move_str = 'W'
                elif current_dir_vec.y == 1: straight_move_str = 'S'
                elif current_dir_vec.y == -1: straight_move_str = 'N'

                # 70% chance to go straight (if possible)
                if straight_move_str in possible_dirs and random.random() < 0.7: 
                    chosen_dir = straight_move_str
                else:
                    chosen_dir = random.choice(possible_dirs)
            
            self.follow_road_direction(chosen_dir)
        else:
            # Stuck, make a U-turn
            if -current_dir_vec != pygame.math.Vector2(0, 0):
                self.direction_vector = -current_dir_vec
                self.angle = (self.angle + 180) % 360
                self.needs_reroute = False  # Reset flag
            else:
                self.respawn()

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
        self.grid_y, self.grid_x = self.find_spawn_point()
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
        
        # 1. Look ahead (returns (type, distance) or None)
        obstacle_info = self.look_ahead(other_cars, scan_distance=5)
        
        # 2. Update state based on obstacle and distance
        self.update_state(obstacle_info)
        
        # 3. Update speed based on state and distance
        self.update_speed(obstacle_info)
        
        # 4. Update position
        self.update_position(other_cars)
        
        # 5. Rotate image
        self.rotate_image()

    def draw(self, screen):
        """Draw the car on the screen."""
        screen.blit(self.image, self.rect)