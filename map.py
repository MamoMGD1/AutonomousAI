import pygame
import sys
import random
random.seed(42)

# Initialize Pygame
pygame.init()

# --- Grid-based Constants ---
CELL_SIZE = 17  # Set according to your screen size (15-20)
GRID_WIDTH = 56  # 1120 / 20 <-- "world become wider"
GRID_HEIGHT = 36 # 720 / 20  <-- "world become wider"

# Screen size is now calculated from the grid
SCREEN_WIDTH = GRID_WIDTH * CELL_SIZE
SCREEN_HEIGHT = GRID_HEIGHT * CELL_SIZE
FPS = 60
# --- End of new constants ---

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
GREEN = (34, 139, 34)
DARK_GREEN = (0, 100, 0)
YELLOW = (255, 255, 0)
RED = (255, 0, 0)
LIGHT_GRAY = (200, 200, 200)
BROWN = (139, 69, 19)
BLUE = (70, 130, 180)
ORANGE = (255, 140, 0)
PURPLE = (147, 112, 219)

# --- REFACTORED TILE CLASSES ---
# These classes no longer store x/y/width/height.
# They are simple types, and their drawing is handled by the world grid.

class Road:
    """Represents a road tile. Pathfinding algorithms will check for this type."""
    def __init__(self, orientation='horizontal', direction=None):
        self.orientation = orientation
        self.direction = direction # 'N', 'S', 'E', 'W', or None
        
    def draw(self, screen, x, y):
        # Calculate pixel position
        pixel_x = x * CELL_SIZE
        pixel_y = y * CELL_SIZE
        
        # Draw road surface
        pygame.draw.rect(screen, DARK_GRAY, (pixel_x, pixel_y, CELL_SIZE, CELL_SIZE))
        
        # This logic creates ONE line between two lanes.
        if self.orientation == 'horizontal' and self.direction == 'W':
            center_y = pixel_y + CELL_SIZE - 0.1
            for i in range(pixel_x, pixel_x + CELL_SIZE, 10): # Dotted line
                pygame.draw.line(screen, WHITE, (i, center_y), (i + 5, center_y), 4)
        elif self.orientation == 'vertical' and self.direction == 'S': 
            center_x = pixel_x + CELL_SIZE - 0.1
            for i in range(pixel_y, pixel_y + CELL_SIZE, 10): # Dotted line
                pygame.draw.line(screen, WHITE, (center_x, i), (center_x, i + 5), 4)
        elif not self.direction:
            center_x = pixel_x + CELL_SIZE // 2
            center_y = pixel_y + CELL_SIZE // 2
            pygame.draw.circle(screen, LIGHT_GRAY, (center_x, center_y), 2)


class Crosswalk:
    """Represents a crosswalk tile."""
    def __init__(self, orientation='horizontal'):
        self.orientation = orientation
        
    def draw(self, screen, x, y):
        pixel_x = x * CELL_SIZE
        pixel_y = y * CELL_SIZE
        
        # Draw road background for the crosswalk
        pygame.draw.rect(screen, DARK_GRAY, (pixel_x, pixel_y, CELL_SIZE, CELL_SIZE))
        
        if self.orientation == 'vertical': # Vertical road, horizontal stripes
            stripe_height = 4 # <-- SCALED DOWN
            num_stripes = CELL_SIZE // (stripe_height + 2) # <-- Adjusted padding
            for i in range(num_stripes):
                y_pos = pixel_y + 2 + i * (stripe_height + 2) # <-- Adjusted padding
                pygame.draw.rect(screen, WHITE, (pixel_x, y_pos, CELL_SIZE, stripe_height))
        else:  # Horizontal road, vertical stripes
            stripe_width = 4 # <-- SCALED DOWN
            num_stripes = CELL_SIZE // (stripe_width + 2) # <-- Adjusted padding
            for i in range(num_stripes):
                x_pos = pixel_x + 2 + i * (stripe_width + 2) # <-- Adjusted padding
                pygame.draw.rect(screen, WHITE, (x_pos, pixel_y, stripe_width, CELL_SIZE))


class Building:
    """Represents a building tile. The targets for pathfinding."""
    def __init__(self, color=BROWN, width=2, height=2):
        self.color = color
        self.width = width   # Number of cells wide
        self.height = height # Number of cells tall
        
    def draw(self, screen, x, y):
        pixel_x = x * CELL_SIZE
        pixel_y = y * CELL_SIZE
        
        # Draw building spanning multiple cells
        building_pixel_width = self.width * CELL_SIZE
        building_pixel_height = self.height * CELL_SIZE
        
        pygame.draw.rect(screen, self.color, (pixel_x, pixel_y, building_pixel_width, building_pixel_height))
        pygame.draw.rect(screen, DARK_GREEN, (pixel_x, pixel_y, building_pixel_width, building_pixel_height), 2)
        
        # Draw windows (scaled to building size)
        window_size = max(2, min(CELL_SIZE // 4, 8))
        num_windows_x = max(1, building_pixel_width // (window_size * 2))
        num_windows_y = max(1, building_pixel_height // (window_size * 2))
        
        for wx_i in range(num_windows_x):
            for wy_i in range(num_windows_y):
                wx = pixel_x + (wx_i + 1) * (building_pixel_width // (num_windows_x + 1)) - window_size // 2
                wy = pixel_y + (wy_i + 1) * (building_pixel_height // (num_windows_y + 1)) - window_size // 2
                pygame.draw.rect(screen, LIGHT_GRAY, (wx, wy, window_size, window_size))


class Grass:
    """Represents a grass tile. An obstacle for pathfinding."""
    def __init__(self):
        self.color = GREEN
        
    def draw(self, screen, x, y):
        pixel_x = x * CELL_SIZE
        pixel_y = y * CELL_SIZE
        pygame.draw.rect(screen, self.color, (pixel_x, pixel_y, CELL_SIZE, CELL_SIZE))


class TrafficLight:
    """
    Represents a traffic light tile.
    It draws a grass background for itself, then the light pole on top.
    """
    def __init__(self, initial_state='red'):
        self.state = initial_state  # 'red', 'yellow', 'green'
        self.timer = 0
        self.state_duration = {'red': 300, 'yellow': 120, 'green': 300} # 5s, 2s, 5s
        
        # Make the light smaller to fit inside a cell
        self.width = 8 # <-- SCALED DOWN
        self.height = 18 # <-- SCALED DOWN
        
    def update(self):
        """Update traffic light state based on timer"""
        self.timer += 1
        if self.timer >= self.state_duration[self.state]:
            self.timer = 0
            if self.state == 'red':
                self.state = 'green'
            elif self.state == 'green':
                self.state = 'yellow'
            elif self.state == 'yellow':
                self.state = 'red'
    
    def draw(self, screen, x, y):
        # 1. Draw the grass background tile first
        pixel_x_bg = x * CELL_SIZE
        pixel_y_bg = y * CELL_SIZE
        pygame.draw.rect(screen, GREEN, (pixel_x_bg, pixel_y_bg, CELL_SIZE, CELL_SIZE))
        
        # 2. Calculate position for the smaller pole, centered in the cell
        pole_x = pixel_x_bg + (CELL_SIZE - self.width) // 2
        pole_y = pixel_y_bg + (CELL_SIZE - self.height) // 2
        
        # 3. Draw the light pole
        pygame.draw.rect(screen, BLACK, (pole_x, pole_y, self.width, self.height))
        
        # 4. Draw lights (scaled down)
        light_radius = 2 # <-- SCALED DOWN
        red_y = pole_y + 3 # <-- SCALED DOWN
        yellow_y = pole_y + 9 # <-- SCALED DOWN
        green_y = pole_y + 15 # <-- SCALED DOWN
        
        center_x = pole_x + self.width // 2
        
        color = RED if self.state == 'red' else DARK_GRAY
        pygame.draw.circle(screen, color, (center_x, red_y), light_radius)
        
        color = YELLOW if self.state == 'yellow' else DARK_GRAY
        pygame.draw.circle(screen, color, (center_x, yellow_y), light_radius)
        
        color = GREEN if self.state == 'green' else DARK_GRAY
        pygame.draw.circle(screen, color, (center_x, green_y), light_radius)


class World:
    """Main world class that manages all objects"""
    def __init__(self, width, height):
        self.grid_width = width
        self.grid_height = height
        # Create the 2D grid
        self.grid = [[Grass() for _ in range(width)] for _ in range(height)]
        
        self._generate_grid()
    
    def _paint_road(self, r1, c1, r2, c2):
        """Helper function to paint 2-cell wide main road segments onto the grid.
        Coordinates are (row, col).
        """
        # Determine if vertical or horizontal
        if c1 == c2: # Vertical segment (same column)
            for r in range(min(r1, r2), max(r1, r2) + 1):
                if 0 <= r < self.grid_height and 0 <= c1 < self.grid_width:
                    self.grid[r][c1] = Road('vertical', 'S')
                if 0 <= r < self.grid_height and 0 <= c1 + 1 < self.grid_width:
                    self.grid[r][c1 + 1] = Road('vertical', 'N')
        elif r1 == r2: # Horizontal segment (same row)
            for c in range(min(c1, c2), max(c1, c2) + 1):
                if 0 <= r1 < self.grid_height and 0 <= c < self.grid_width:
                    self.grid[r1][c] = Road('horizontal', 'W')
                if 0 <= r1 + 1 < self.grid_height and 0 <= c < self.grid_width:
                    self.grid[r1 + 1][c] = Road('horizontal', 'E')

    def _place_crosswalk_and_light(self, r, c, orientation, light_state='red', position='default'):
        """Helper to place crosswalk spanning 2 lanes and a traffic light
        position can be: 'default', 'top-left', 'top-right', 'bottom-left', 'bottom-right'
        """
        if orientation == 'vertical':
            # Place crosswalk on both lanes of vertical road
            if 0 <= r < self.grid_height and 0 <= c < self.grid_width:
                self.grid[r][c] = Crosswalk('vertical')
            if 0 <= r < self.grid_height and 0 <= c + 1 < self.grid_width:
                self.grid[r][c + 1] = Crosswalk('vertical')
            
            # Place traffic light at corner based on position
            if position == 'top-right' or position == 'default':
                light_r, light_c = r, c + 2
            elif position == 'top-left':
                light_r, light_c = r, c - 1
            elif position == 'bottom-right':
                light_r, light_c = r + 1, c + 2
            elif position == 'bottom-left':
                light_r, light_c = r, c - 1
            else:
                light_r, light_c = r, c + 2
                
            if 0 <= light_r < self.grid_height and 0 <= light_c < self.grid_width:
                self.grid[light_r][light_c] = TrafficLight(light_state)
                
        else:  # horizontal
            # Place crosswalk on both lanes of horizontal road
            if 0 <= r < self.grid_height and 0 <= c < self.grid_width:
                self.grid[r][c] = Crosswalk('horizontal')
            if 0 <= r + 1 < self.grid_height and 0 <= c < self.grid_width:
                self.grid[r + 1][c] = Crosswalk('horizontal')
            
            # Place traffic light at corner based on position
            if position == 'bottom-right' or position == 'default':
                light_r, light_c = r + 2, c
            elif position == 'top-right':
                light_r, light_c = r - 1, c
            elif position == 'bottom-left':
                light_r, light_c = r + 2, c
            elif position == 'top-left':
                light_r, light_c = r - 1, c
            else:
                light_r, light_c = r + 2, c
                
            if 0 <= light_r < self.grid_height and 0 <= light_c < self.grid_width:
                self.grid[light_r][light_c] = TrafficLight(light_state)
    
    def _put_intersection(self, r, c):
        self.grid[r][c].direction = None
        self.grid[r+1][c].direction = None
        self.grid[r][c+1].direction = None
        self.grid[r+1][c+1].direction = None

    def _generate_grid(self):
        """Create the world map by placing objects into the grid"""
        
        # --- 1. Create Complex Road Network ---
        
        # Main vertical arterials (varied heights and starting points)
        self._paint_road(0, 6, 17, 6)           # Left arterial (almost full height)
        self._paint_road(20, 6, 34, 6)           # Left arterial (almost full height)
        self._paint_road(6, 12, 9, 12)         # Left arterial (almost full height)
        self._paint_road(4, 18, 5, 18)         # Left arterial (almost full height)
        self._paint_road(8, 18, self.grid_height - 1, 18)  # Left-center (starts lower)
        self._paint_road(0, 32, 28, 32)         # Center arterial (stops early)
        self._paint_road(6, 44, self.grid_height - 1, 44) # Right-center (starts mid)
        self._paint_road(0, 53, 3, 53)         # Right edge (partial)
        self._paint_road(14, 53, 19, 53)         # Right edge (partial)
        self._paint_road(12, 26, 19, 26)         # Right edge (partial)
        self._paint_road(16, 13, 19, 13)         # Right edge (partial)
        self._paint_road(22, 39, 25, 39)         # Right edge (partial)
        
        # Major horizontal roads (with breaks and gaps)
        self._paint_road(4, 0, 4, 42)           # Upper-left section
        self._paint_road(4, 44, 4, 46)          # Upper-center section (gap before)
        self._paint_road(4, 46, 4, self.grid_width - 1) # Upper-right section
        
        self._paint_road(12, 0, 12, 25)         # Mid-upper road (stops at center)
        self._paint_road(12, 34, 12, self.grid_width - 1) # Continues after gap
        
        self._paint_road(20, 8, 20, 27) # Middle road (offset start)
        self._paint_road(20, 32, 20, self.grid_width - 1) # Middle road (offset start)
        
        self._paint_road(28, 0, 28, 16)         # Lower-mid left
        self._paint_road(28, 20, 28, 42)        # Lower-mid center
        self._paint_road(28, 46, 28, self.grid_width - 1) # Lower-mid right
        
        # Secondary connector roads (create interesting intersections)
        self._paint_road(8, 14, 8, 17)          # Small connector
        self._paint_road(33, 0, 33, 5)          # Small connector
        self._paint_road(16, 8, 16, 12)         # Another connector
        self._paint_road(24, 34, 24, 38)        # Diagonal area connector
        
        # --- 2. Smart Crosswalk & Traffic Light Placement ---
        
        # Major 4-way intersections (crosswalks on all 4 approaches)
        intersections_4way = [
            (4, 6, 'green'),    # Upper-left major
            (4, 32, 'yellow'),  # Upper-left major
            (12, 6, 'red'),     # Mid-left
            #(12, 18, 'green'),     # Mid-left
            (12, 44, 'yellow'),     # Mid-left
            (20, 18, 'green'),  # Center-left important
            (20, 32, 'red'),    # Center major
            (20, 44, 'green'),  # Center-right
            (28, 6, 'red'),     # Lower-left
            (28, 18, 'green'),  # Lower-center-left
            (28, 32, 'red'),    # Lower-center important
            (28, 44, 'green'),  # Lower-center-right
        ]
        
        for r, c, state in intersections_4way:
            self._put_intersection(r, c)

            # North approach
            if r > 1 and isinstance(self.grid[r - 2][c], Road):
                self._place_crosswalk_and_light(r - 1, c, 'vertical', state, 'top-right')
            
            # South approach
            if r + 3 < self.grid_height and isinstance(self.grid[r + 3][c], Road):
                self._place_crosswalk_and_light(r + 2, c, 'vertical', 
                                                'green' if state == 'red' else 'red', 'bottom-left')
            
            # West approach
            if c > 1 and isinstance(self.grid[r][c - 2], Road):
                self._place_crosswalk_and_light(r, c - 1, 'horizontal', 
                                                'green' if state == 'red' else 'red', 'top-left')
            
            # East approach
            if c + 3 < self.grid_width and isinstance(self.grid[r][c + 3], Road):
                self._place_crosswalk_and_light(r, c + 2, 'horizontal', state, 'bottom-right')
        
        # T-junctions (crosswalks on 3 approaches)
        t_junctions = [
            (4, 32, 'green'),   # Upper-center T
            (4, 44, 'red'),     # Upper-right T
            (12, 18, 'green'),  # Mid T
            (12, 32, 'yellow'), # Mid T
            (12, 44, 'red'),    # Mid-right T
        ]
        
        for r, c, state in t_junctions:
            self._put_intersection(r, c)

            # Check all 4 directions and place crosswalks where roads exist
            if r > 1 and isinstance(self.grid[r - 2][c], Road):
                self._place_crosswalk_and_light(r - 1, c, 'vertical', state)
            if r + 3 < self.grid_height and isinstance(self.grid[r + 3][c], Road):
                self._place_crosswalk_and_light(r + 2, c, 'vertical', 'green' if state == 'red' else 'red')
            if c > 1 and isinstance(self.grid[r][c - 2], Road):
                self._place_crosswalk_and_light(r, c - 1, 'horizontal', state)
            if c + 3 < self.grid_width and isinstance(self.grid[r][c + 3], Road):
                self._place_crosswalk_and_light(r, c + 2, 'horizontal', 'green' if state == 'red' else 'red')
        
        # Define L-Turn Intersections
        l_turn = [
            (20, 26),
            (20, 13),
            (20, 6),
            (24, 32),
            (20, 53),
            (12, 53),
            (33, 6),
            (4, 12),
            (4, 53),
            (8, 12),
            (8, 18),
            (12, 26),
            (20, 39),
            (24, 39),
            (16, 13),
            (16, 6),
        ]
        for r, c in l_turn:
            self._put_intersection(r, c)

        # --- 3. Building Placement Around Streets ---
        # Define building types
        building_colors = [BROWN, BLUE, ORANGE, RED, YELLOW, WHITE]
        
        for r in range(self.grid_height):
            for c in range(self.grid_width):
                tile = self.grid[r][c]
                
                # Skip if not grass
                if not isinstance(tile, Grass):
                    continue
                
                # Check if this grass cell is adjacent to a road
                adjacent_to_road = False
                
                # Check all 4 directions
                if r > 0 and isinstance(self.grid[r-1][c], (Road, Crosswalk)):
                    adjacent_to_road = True
                if r < self.grid_height - 1 and isinstance(self.grid[r+1][c], (Road, Crosswalk)):
                    adjacent_to_road = True
                if c > 0 and isinstance(self.grid[r][c-1], (Road, Crosswalk)):
                    adjacent_to_road = True
                if c < self.grid_width - 1 and isinstance(self.grid[r][c+1], (Road, Crosswalk)):
                    adjacent_to_road = True
                
                # If adjacent to road, place a building with a probability
                if adjacent_to_road and random.random() <= 0.35:
                    color = random.choice(building_colors)
                    self.grid[r][c] = Building(color)

    def update(self):
        """Update all dynamic elements by iterating the grid"""
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                tile = self.grid[y][x]
                # Check if the tile is a TrafficLight and call its update
                if isinstance(tile, TrafficLight):
                    tile.update()
    
    def draw(self, screen):
        """Draw all world elements"""
        
        # --- Draw the grid ---
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                tile = self.grid[y][x]
                tile.draw(screen, x, y)


def main():
    # Create window
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Autonomous Vehicle")
    clock = pygame.time.Clock()
    
    # Create world
    world = World(GRID_WIDTH, GRID_HEIGHT)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # --- UPGRADED: Debugging event for mouse clicks ---
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 1 is the left mouse button
                    pos = pygame.mouse.get_pos()
                    
                    # This is now the *exact* grid coordinate
                    grid_col = pos[0] // CELL_SIZE # x maps to col
                    grid_row = pos[1] // CELL_SIZE # y maps to row
                    
                    # Check for out-of-bounds clicks
                    if 0 <= grid_col < GRID_WIDTH and 0 <= grid_row < GRID_HEIGHT:
                        tile = world.grid[grid_row][grid_col] # Access as grid[row][col]
                        coords = (grid_row, grid_col)
                        tile_type = type(tile)
                        state = None

                        # --- Check if the tile is a TrafficLight ---
                        if isinstance(tile, TrafficLight):
                            state = tile.state

                        # --- Check for Road direction ---
                        elif isinstance(tile, Road):
                            state = tile.direction if tile.direction else 'Intersection'
                        
                        print({'position': coords, 'type': tile_type, 'state': state})
  
                    else:
                        print(f"Clicked outside grid at Pixel Coords: {pos}")
        
        # Update world
        world.update()
        
        # Draw everything
        screen.fill(WHITE) # Fill with white just in case
        world.draw(screen)
        
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()