import pygame, random
import map
from car import Car

class Agent(Car):
    """
    Agent follows waypoints using Car's natural driving behavior.
    Key differences from Car:
    - Follows predetermined path (no random turns)
    - Waits indefinitely at red lights/traffic (no forced rerouting)
    - Replans only when waypoint becomes obstacle
    """

    def __init__(self, world, spawn=None):
        super().__init__(world, always_drive=False)

        # Agent sprite
        try:
            self.image_orig = pygame.image.load("images/agent.png").convert_alpha()
        except pygame.error:
            self.image_orig = pygame.Surface((map.CELL_SIZE, map.CELL_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(self.image_orig, (255, 0, 0, 200), (0, 0, map.CELL_SIZE, map.CELL_SIZE))

        scale_factor = 1.75
        self.image_orig = pygame.transform.scale(
            self.image_orig,
            (int(map.CELL_SIZE * scale_factor), int(map.CELL_SIZE * scale_factor))
        )
        self.image = self.image_orig
        self.rect = self.image.get_rect(center=(self.pixel_x + map.CELL_SIZE // 2, self.pixel_y + map.CELL_SIZE // 2))

        # Path state
        self.path = []
        self.path_index = 0
        self.is_active = False

        # Replanning state
        self.replan_needed = False
        self.blocked_tile = None
        self.destination = None
        self.awaiting_approval = False  # NEW: waiting for user to approve new path
        self.pending_path = None  # NEW: stores the replanned path

        self.is_agent = True

        # Start stopped
        self.state = 'stopped'
        self.speed = 0

        self.doing_uturn = False
        self.uturn_stage = 0
        self.uturn_timer = 0

        if spawn is not None:
            try:
                self.set_position(int(spawn[0]), int(spawn[1]))
            except Exception:
                pass

    def set_position(self, grid_y, grid_x):
        if not (0 <= grid_x < map.GRID_WIDTH and 0 <= grid_y < map.GRID_HEIGHT):
            raise ValueError("Position outside bounds")
        tile = self.world.grid[grid_y][grid_x]
        if not isinstance(tile, (map.Road, map.Crosswalk)):
            raise ValueError("Position not on road")

        self.grid_x = grid_x
        self.grid_y = grid_y
        self.pixel_x = self.grid_x * map.CELL_SIZE
        self.pixel_y = self.grid_y * map.CELL_SIZE
        self.rect.center = (self.pixel_x + map.CELL_SIZE // 2, self.pixel_y + map.CELL_SIZE // 2)
        self.current_tile = tile

        if isinstance(tile, map.Road) and getattr(tile, 'direction', None):
            self.follow_road_direction(tile.direction)
        self.rotate_image()

    def move(self, path):
        """Start following a new path."""
        if not path:
            return
        
        self.path = [(int(p[0]), int(p[1])) for p in path]
        
        # Skip first if already there
        if (self.grid_y, self.grid_x) == self.path[0]:
            self.path_index = 1
        else:
            self.path_index = 0
        
        self.is_active = True
        self.state = 'driving'
        self.destination = self.path[-1]
        self.awaiting_approval = False  # Reset approval flag
        self.pending_path = None
        
        self.doing_uturn = False
        self.uturn_stage = 0
        self.uturn_timer = 0

        print(f"[Agent] Following {len(self.path)} waypoints to {self.destination}")

    def stop(self):
        """Stop the agent completely."""
        self.path = []
        self.path_index = 0
        self.is_active = False
        self.state = 'stopped'
        self.speed = 0

    def approve_replan(self, new_path):
        """Called by main.py after user approves the replanned path."""
        if new_path:
            print(f"[Agent] Replan approved! Resuming journey.")
            self.replan_needed = False
            self.blocked_tile = None
            self.move(new_path)
        else:
            print(f"[Agent] No valid path found. Agent remains stopped.")
            self.stop()

    def look_ahead(self, other_cars, scan_distance=5):
        """
        OVERRIDE: Agent's look_ahead ignores grass/obstacles in the distance.
        Only checks for: pedestrians, red lights, and other cars.
        Grass is handled separately by waypoint checking.
        """
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
                # Check for pedestrians
                if hasattr(self.world, "pedestrian_manager") and self.world.pedestrian_manager:
                    for ped in self.world.pedestrian_manager.group:
                        ped_grid_x = int(ped.rect.centerx // map.CELL_SIZE)
                        ped_grid_y = int(ped.rect.centery // map.CELL_SIZE)
                        
                        if ped_grid_x == check_x and ped_grid_y == check_y:
                            return ('pedestrian', i)

                # Check traffic light
                light = self.find_correct_light(check_y, check_x)
                if light and light.state == 'red':
                    return ('red_light', i)

            # CHECK CARS
            if other_cars:
                for car in other_cars:
                    if car is not self and car.grid_x == check_x and car.grid_y == check_y:
                        return ('car_ahead', i)
            
            # DON'T check for grass/obstacles here - agent handles that separately!
            # (removed the grass/obstacle check from Car's version)
            
        return None

    def on_new_tile_ai(self, other_cars):
        """
        CRITICAL OVERRIDE: Agent follows path waypoints, no random behavior.
        - Checks if reached waypoint
        - Follows road directions naturally
        - At intersections, chooses direction toward next waypoint
        - NEVER makes random turns or U-turns
        """
        # Out of bounds check
        if not (0 <= self.grid_x < map.GRID_WIDTH and 0 <= self.grid_y < map.GRID_HEIGHT):
            print("[Agent] Out of bounds! Stopping.")
            self.stop()
            return

        new_tile = self.world.grid[self.grid_y][self.grid_x]
        self.current_tile = new_tile

        # If agent drove onto grass - shouldn't happen but handle it
        if not isinstance(new_tile, (map.Road, map.Crosswalk)):
            print(f"[Agent] Drove onto {type(new_tile).__name__}! Requesting replan...")
            self.replan_needed = True
            self.blocked_tile = (self.grid_y, self.grid_x)
            self.stop()
            return

        # Check if reached current waypoint
        if self.is_active and self.path_index < len(self.path):
            if (self.grid_y, self.grid_x) == self.path[self.path_index]:
                self.path_index += 1
                
                # Check if reached final destination
                if self.path_index >= len(self.path):
                    print(f"[Agent] DESTINATION REACHED!")
                    self.stop()
                    return

        # Follow road/intersection logic
        if isinstance(new_tile, map.Road):
            if new_tile.direction is None:
                # At intersection - use agent's path-following logic
                self.handle_intersection(other_cars)
            else:
                # On directional road - follow its direction
                self.follow_road_direction(new_tile.direction)
        # If crosswalk, continue without direction change

    def handle_intersection(self, other_cars):
        """
        OVERRIDE: At intersections, choose direction toward next waypoint.
        NO random turns, NO U-turns unless absolutely necessary.
        """
        if not self.is_active or self.path_index >= len(self.path):
            # No active path - shouldn't happen, but stop if it does
            print("[Agent] At intersection but no active path. Stopping.")
            self.stop()
            return
        
        # Get next waypoint
        next_wp = self.path[self.path_index]
        target_y, target_x = next_wp
        
        # Calculate direction toward waypoint
        dy = target_y - self.grid_y
        dx = target_x - self.grid_x
        
        # Determine preferred direction based on largest delta
        if abs(dx) > abs(dy):
            preferred = 'E' if dx > 0 else 'W'
        else:
            preferred = 'N' if dy < 0 else 'S'
        
        # Check all 4 directions for validity
        moves = {'N': (0, -1), 'S': (0, 1), 'E': (1, 0), 'W': (-1, 0)}
        possible_dirs = []
        current_dir_vec = self.direction_vector
        
        for move_dir_str, (ddx, ddy) in moves.items():
            nx, ny = self.grid_x + ddx, self.grid_y + ddy
            
            # Check bounds
            if not (0 <= nx < map.GRID_WIDTH and 0 <= ny < map.GRID_HEIGHT):
                continue
            
            tile = self.world.grid[ny][nx]
            
            # Must be road or crosswalk
            if not isinstance(tile, (map.Road, map.Crosswalk)):
                continue
            
            forward_blocked = preferred not in possible_dirs

            # Allow U-turn ONLY IF forward is blocked AND the next waypoint is grass AND replan failed
            if (pygame.math.Vector2(ddx, ddy) == -current_dir_vec):
                if self.replan_needed:
                    possible_dirs.append(move_dir_str)   # Allow U-turn
                else:
                    continue

            
            # Don't check for car blocking - agent waits for cars to move
            possible_dirs.append(move_dir_str)
        
        # Choose direction
        if not possible_dirs:
            # All directions blocked - WAIT (don't turn around like normal car)
            print(f"[Agent] Intersection blocked. Waiting...")
            self.state = 'stopped'
            self.speed = 0
            return
        
        # Prefer the direction toward waypoint
        if preferred in possible_dirs:
            chosen_dir = preferred
            #print(f"[Agent] Intersection: choosing {chosen_dir} toward waypoint {next_wp}")
        else:
            # Preferred direction not available - pick another valid one
            # Agent trusts its path, so any forward direction should eventually work
            chosen_dir = random.choice(possible_dirs)
        
        self.follow_road_direction(chosen_dir)

    def update(self, other_cars):
        """
        OVERRIDE: Agent-specific update logic.
        - Uses Car's physics (speed, collision, red lights, pedestrians)
        - DISABLES stuck timer that forces direction changes
        - Checks for obstacles on path waypoints
        """
        # ---------------------------------------------
        # U-TURN STATE MACHINE
        # ---------------------------------------------
        if self.doing_uturn:
            # Stage 0: waiting 3 seconds (180 frames @ 60fps)
            if self.uturn_stage == 0:
                self.uturn_timer += 1
                self.state = 'stopped'
                self.speed = 0

                if self.uturn_timer >= 180:
                    self.uturn_stage = 1
                return

            # Stage 1: first 90° left turn
            elif self.uturn_stage == 1:
                self.turn_left()
                self.uturn_stage = 2
                return

            # Stage 2: move forward 1 tile
            elif self.uturn_stage == 2:
                if self.move_forward_one_tile():
                    self.uturn_stage = 3
                return

            # Stage 3: second 90° left turn
            elif self.uturn_stage == 3:
                self.turn_left()
                self.doing_uturn = False
                self.uturn_stage = 0
                self.uturn_timer = 0

                # Now facing opposite direction — request replanning from main.py
                print("[Agent] U-turn complete. Requesting replan from new position.")
                # set flags so main.py will recompute a new path from the agent's current tile
                self.replan_needed = True
                self.awaiting_approval = True
                self.pending_path = ((self.grid_y, self.grid_x), self.destination)
                # keep the agent stopped until main.py approves/moves it
                self.state = 'stopped'
                self.speed = 0
                return

        # --- REPLAN CHECK ---
        if self.replan_needed:
            self.try_replan()
            if not self.is_active:
                return

        if not self.is_active:
            self.state = 'stopped'
            self.speed = 0
            self.rotate_image()
            return

        # Check if next waypoint has become an obstacle
        if self.path_index < len(self.path):
            next_wp = self.path[self.path_index]
            try:
                tile = self.world.grid[next_wp[0]][next_wp[1]]
                if not isinstance(tile, (map.Road, map.Crosswalk)):
                    print(f"[Agent] Waypoint {next_wp} is now {type(tile).__name__}!")

                    # If the blocked waypoint is directly in front of the car, perform the deterministic U-turn
                    fx = self.grid_x + int(self.direction_vector.x)
                    fy = self.grid_y + int(self.direction_vector.y)
                    if (fy, fx) == next_wp and not self.doing_uturn:
                        print(f"[Agent] Blocked tile is directly ahead at {next_wp} → initiating U-turn.")
                        # initialize U-turn state machine
                        self.doing_uturn = True
                        self.uturn_stage = 0
                        self.uturn_timer = 0
                        # make sure the car is stopped while preparing the U-turn
                        self.state = 'stopped'
                        self.speed = 0
                        return

                    # Otherwise request a replan (existing architecture: main.py will perform it)
                    print(f"[Agent] Requesting replan from position {(self.grid_y, self.grid_x)} to {self.destination}")
                    self.replan_needed = True
                    self.blocked_tile = next_wp
                    self.stop()
                    return
            except Exception as e:
                print(f"[Agent] Error checking waypoint: {e}")

        # ---------------------------------------------------
        # DETECT SUDDEN GRASS DIRECTLY IN FRONT OF THE AGENT
        # ---------------------------------------------------
        fx = self.grid_x + int(self.direction_vector.x)
        fy = self.grid_y + int(self.direction_vector.y)

        if 0 <= fx < map.GRID_WIDTH and 0 <= fy < map.GRID_HEIGHT:
            front_tile = self.world.grid[fy][fx]

            # Unexpected grass means it was NOT grass during planning
            if isinstance(front_tile, map.Grass) and not self.doing_uturn:
                print(f"[Agent] Sudden grass detected in ({fy}, {fx}) → initiating U-turn.")
                self.doing_uturn = True
                self.state = 'stopped'
                self.speed = 0
                return

        # Use Car's look_ahead for pedestrians, red lights, obstacles
        obstacle_info = self.look_ahead(other_cars, scan_distance=5)
        
        # Use Car's state machine (respects red lights, pedestrians, cars)
        self.update_state(obstacle_info)
        
        # Use Car's speed control (acceleration, braking)
        self.update_speed(obstacle_info)
        
        # Use Car's position update (collision detection)
        # BUT we need to override the stuck detection behavior
        # So we'll call a modified version:
        self.update_position_no_forced_reroute(other_cars)
        
        # Rotate image
        self.rotate_image()

    def try_replan(self):
        """
        Agent does NOT compute paths.
        It only requests a replan from main.py.
        """
        if not self.destination:
            print("[Agent] No destination stored. Cannot replan.")
            self.stop()
            return

        start = (self.grid_y, self.grid_x)
        goal = self.destination

        print(f"[Agent] Requesting replan from {start} → {goal}")

        self.replan_needed = True
        self.awaiting_approval = True
        self.pending_path = (start, goal)

        # Stop until main.py provides a new path
        self.stop()

    def turn_left(self):
        """Rotate direction vector 90° left."""
        dx, dy = self.direction_vector.x, self.direction_vector.y
        self.direction_vector.x = dy
        self.direction_vector.y = -dx
        self.rotate_image()

    def move_forward_one_tile(self):
        """Move exactly 1 tile forward based on direction vector."""
        target_x = self.grid_x + int(self.direction_vector.x)
        target_y = self.grid_y + int(self.direction_vector.y)

        # Bounds + road check
        if not (0 <= target_x < map.GRID_WIDTH and 0 <= target_y < map.GRID_HEIGHT):
            return True  # consider it 'done'

        tile = self.world.grid[target_y][target_x]
        if not isinstance(tile, (map.Road, map.Crosswalk)):
            return True  # cannot move, treat as completed

        # Move instantly 1 tile
        self.grid_x = target_x
        self.grid_y = target_y
        self.pixel_x = self.grid_x * map.CELL_SIZE
        self.pixel_y = self.grid_y * map.CELL_SIZE
        self.rect.center = (self.pixel_x + map.CELL_SIZE//2,
                            self.pixel_y + map.CELL_SIZE//2)

        # Update current tile and align ANGLE (not direction_vector) with road
        self.current_tile = tile
        if isinstance(tile, map.Road) and tile.direction:
            # Just update the visual angle, don't change direction_vector
            direction_to_angle = {'N': 0, 'S': 180, 'E': -90, 'W': 90}
            self.angle = direction_to_angle.get(tile.direction, self.angle)
            self.rotate_image()
        else:
            self.rotate_image()
        return True

    def update_position_no_forced_reroute(self, other_cars):
        """
        Modified version of Car's update_position that DISABLES forced rerouting.
        Agent waits indefinitely instead of forcing new direction after 3 seconds.
        """
        # Track position for stuck detection (but don't force reroute)
        current_pos = (int(self.pixel_x), int(self.pixel_y))
        if current_pos == self.last_position:
            self.stuck_timer += 1
            # Agent NEVER forces a new direction when stuck
            # It waits for obstacles to clear
        else:
            self.stuck_timer = 0
            self.last_position = current_pos
        
        if self.speed == 0:
            return

        # Calculate next position
        next_pixel_x = self.pixel_x + self.direction_vector.x * self.speed
        next_pixel_y = self.pixel_y + self.direction_vector.y * self.speed
        
        # Create smaller collision box (same as Car)
        collision_shrink_w = 1.55
        collision_shrink_h = 0.55
        if abs(self.direction_vector.x) > 0:  # horizontal
            smaller_width = int(map.CELL_SIZE * collision_shrink_w)
            smaller_height = int(map.CELL_SIZE * collision_shrink_h)
        else:  # vertical
            smaller_width = int(map.CELL_SIZE * collision_shrink_h)
            smaller_height = int(map.CELL_SIZE * collision_shrink_w)
        
        next_collision_rect = pygame.Rect(0, 0, smaller_width, smaller_height)
        next_collision_rect.center = (next_pixel_x + map.CELL_SIZE // 2, next_pixel_y + map.CELL_SIZE // 2)

        # Check collision with other cars
        collision_detected = False
        if other_cars:
            for car in other_cars:
                if car is self:
                    continue
                
                other_collision_rect = pygame.Rect(0, 0, smaller_width, smaller_height)
                other_collision_rect.center = car.rect.center
                
                if next_collision_rect.colliderect(other_collision_rect):
                    # Check if moving away
                    current_distance_sq = (self.pixel_x - car.pixel_x)**2 + (self.pixel_y - car.pixel_y)**2
                    next_distance_sq = (next_pixel_x - car.pixel_x)**2 + (next_pixel_y - car.pixel_y)**2
                    
                    if next_distance_sq > current_distance_sq:
                        continue  # Moving away, allow
                    
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

        # Check if entered new grid cell
        new_grid_x = int(self.pixel_x / map.CELL_SIZE)
        new_grid_y = int(self.pixel_y / map.CELL_SIZE)

        if new_grid_x != self.grid_x or new_grid_y != self.grid_y:
            self.grid_x = new_grid_x
            self.grid_y = new_grid_y
            self.on_new_tile_ai(other_cars)

    def draw(self, screen):
        """Draw agent and its path."""
        # Draw remaining path
        try:
            if self.is_active and self.path and self.path_index < len(self.path):
                pts = [(int(self.pixel_x + map.CELL_SIZE // 2), 
                       int(self.pixel_y + map.CELL_SIZE // 2))]
                
                for i in range(self.path_index, len(self.path)):
                    wp = self.path[i]
                    pts.append((wp[1] * map.CELL_SIZE + map.CELL_SIZE // 2,
                               wp[0] * map.CELL_SIZE + map.CELL_SIZE // 2))
                                
                # Draw path line (RED if replanning, GREEN if active)
                path_color = (255, 0, 0) if self.replan_needed else (0, 255, 0)
                for i in range(len(pts) - 1):
                    pygame.draw.line(screen, path_color, pts[i], pts[i+1], 4)
                
        except Exception:
            pass

        # Draw agent sprite
        screen.blit(self.image, self.rect)