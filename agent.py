import pygame
import random
import math
import map
from car import Car  # car.py'dan (Sadece AI) Car sınıfını içe aktar

class Agent(Car):
    def __init__(self, world):
        """
        Agent class constructor. Inherits from Car.
        world: World object from map.py.
        This class is Player Controlled.
        """
        # Call Car's (AI only) __init__ method
        super().__init__(world)
        
        # This is a Player vehicle
        self.is_player = True
        
        # 1. Change image to 'agent.png'
        try:
            # Try to load images/agent.png
            self.image_orig = pygame.image.load("images/agent.png").convert_alpha()
        except pygame.error:
            # If not found, use a blue square as default
            print("Warning: 'images/agent.png' not found. Using a blue square.")
            self.image_orig = pygame.Surface((map.CELL_SIZE, map.CELL_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(self.image_orig, (0, 0, 255, 200), (0, 0, map.CELL_SIZE, map.CELL_SIZE))
        
        # Scaling
        scale_factor = 0.9
        self.image_orig = pygame.transform.scale(self.image_orig, (int(map.CELL_SIZE * scale_factor), int(map.CELL_SIZE * scale_factor)))
        self.image = self.image_orig
        
        # Reset angle and speed (as inherited from Car)
        # ANGLE CORRECTION: Assume image faces RIGHT (East)
        self.angle = 0  # 0 degrees = Right (East)
        self.speed = 0
        self.rotate_image()  # Call the fixed rotate_image method
        
        # Slightly higher acceleration for player control
        self.acceleration = 0.2 
        self.max_speed = 3.5
        
        # Store player input
        self.input_vector = pygame.math.Vector2(0, 0)
        
        # Player will not use AI 'stopped' state machine, always 'driving'
        self.state = 'driving'

        # Render-only offset to visually avoid overlaps without affecting movement
        self.render_offset = pygame.math.Vector2(0, 0)

    # --- Overriding Methods from Car ---

    def handle_input(self, input_vector):
        self.input_vector = input_vector

        if self.input_vector.length() > 0:
            self.direction_vector = self.input_vector.copy()
        # Angles for a sprite that faces RIGHT (East) by default
        if self.direction_vector.x == 1:  # Right
            self.angle = -90
        elif self.direction_vector.x == -1:  # Left
            self.angle = 90
        elif self.direction_vector.y == 1:  # Down
            self.angle = 180
        elif self.direction_vector.y == -1:  # Up
            self.angle = 0

    def update_for_player(self):
        """Update speed and state logic while under player control."""
        if self.input_vector.length() > 0:
            self.speed = min(self.max_speed, self.speed + self.acceleration)
        else:
            self.speed = max(0, self.speed - self.deceleration)
        # Off-road check (for player)
        if self.speed > 0:
            # Check the next cell to move to
            front_x = self.pixel_x + (map.CELL_SIZE / 2) + (self.direction_vector.x * (map.CELL_SIZE / 2))
            front_y = self.pixel_y + (map.CELL_SIZE / 2) + (self.direction_vector.y * (map.CELL_SIZE / 2))
            check_grid_x = int(front_x / map.CELL_SIZE)
            check_grid_y = int(front_y / map.CELL_SIZE)
            if 0 <= check_grid_x < map.GRID_WIDTH and 0 <= check_grid_y < map.GRID_HEIGHT:
                tile = self.world.grid[check_grid_y][check_grid_x]
                # If the next tile is not road or crosswalk, stop
                if not isinstance(tile, (map.Road, map.Crosswalk)):
                    self.speed = 0
            else:
                self.speed = 0

    def update_position(self, other_cars=None):
        if self.speed == 0:
            # Reset any temporary render offset when not moving
            self.render_offset.update(0, 0)
            return
        # Calculate next position (pixels)
        next_x = self.pixel_x + self.direction_vector.x * self.speed
        next_y = self.pixel_y + self.direction_vector.y * self.speed

        # Predict the next grid cell in front of the car (use front point like off-road check)
        front_x = next_x + (map.CELL_SIZE / 2) + (self.direction_vector.x * (map.CELL_SIZE / 2))
        front_y = next_y + (map.CELL_SIZE / 2) + (self.direction_vector.y * (map.CELL_SIZE / 2))
        next_grid_x = int(front_x / map.CELL_SIZE)
        next_grid_y = int(front_y / map.CELL_SIZE)

        # 1) Off-road prevention: block move if the next grid is not road/crosswalk or out of bounds
        if not (0 <= next_grid_x < map.GRID_WIDTH and 0 <= next_grid_y < map.GRID_HEIGHT):
            self.speed = 0
            self.render_offset.update(0, 0)
            return
        next_tile = self.world.grid[next_grid_y][next_grid_x]
        if not isinstance(next_tile, (map.Road, map.Crosswalk)):
            self.speed = 0
            self.render_offset.update(0, 0)
            return

        # 2) Collision prevention: if another vehicle occupies the next grid cell, stop
        if other_cars:
            for car in other_cars:
                if car is self:
                    continue
                if getattr(car, 'grid_x', None) == next_grid_x and getattr(car, 'grid_y', None) == next_grid_y:
                    self.speed = 0
                    self.render_offset.update(0, 0)
                    return

        # No predicted overlap → reset render offset
        self.render_offset.update(0, 0)

        # 3) Apply movement
        self.pixel_x = next_x
        self.pixel_y = next_y
        self.rect.center = (self.pixel_x + map.CELL_SIZE // 2, self.pixel_y + map.CELL_SIZE // 2)
        # Update grid position
        self.grid_x = int(self.pixel_x / map.CELL_SIZE)
        self.grid_y = int(self.pixel_y / map.CELL_SIZE)

    def update(self, other_cars):
        """
        Main update loop for the Agent (Player).
        Overrides Car.update()
        """
        # 1. Update speed and state based on key input
        self.update_for_player()
        # 2. Update position
        self.update_position(other_cars)
        # 3. Rotate image (inherit from Car)
        self.rotate_image()

    def draw(self, screen):
        """Draw the agent with any temporary render offset applied."""
        if self.render_offset.length_squared() == 0:
            screen.blit(self.image, self.rect)
        else:
            offset_rect = self.image.get_rect(center=(self.rect.centerx + self.render_offset.x,
                                                      self.rect.centery + self.render_offset.y))
            screen.blit(self.image, offset_rect)