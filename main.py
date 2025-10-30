import pygame
import sys
import map  # Map, tiles, and World class
from car import Car   # Randomly roaming Car class (AI only)
from agent import Agent # Player-controlled Agent class

def main():
    """
    Main simulation function.
    Initializes Pygame, sets up the world, creates vehicles, and runs the main loop.
    Player Control: Agent (agent.png)
    AI: Car (car.png)
    """
    # Initialize Pygame
    pygame.init()

    # Window and screen settings (constants from map.py)
    try:
        screen = pygame.display.set_mode((map.SCREEN_WIDTH, map.SCREEN_HEIGHT))
        pygame.display.set_caption("Autonomous Vehicle Simulation")
        clock = pygame.time.Clock()
    except AttributeError as e:
        print(f"Error: Required screen constants (SCREEN_WIDTH, SCREEN_HEIGHT) not found in 'map.py'.")
        print(f"Detail: {e}")
        return

    # Create world (map)
    world = map.World(map.GRID_WIDTH, map.GRID_HEIGHT)
    
    # List of vehicles (holds both Car and Agent objects)
    all_vehicles = []
    player_vehicle = None # Keep the player vehicle in a separate variable

    # 1. Create randomly roaming (AI) cars (car.png)
    num_cars = 20  # Number of random cars in the simulation
    for _ in range(num_cars):
        all_vehicles.append(Car(world))
        
    # 2. Create player-controlled Agent (agent.png)
    try:
        # Create the agent using the world
        player_vehicle = Agent(world)
        # Add the agent to the list of all vehicles
        all_vehicles.append(player_vehicle)
    except Exception as e:
        print(f"Error: Player Agent could not be created. {e}")
        # Continue simulation with only Cars if agent creation fails
        pass

    # --- Main Simulation Loop ---
    running = True
    input_vector = pygame.math.Vector2(0, 0) # Stores player input

    while running:
        # Event Management
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # --- NEW: Player Control Events ---
            if player_vehicle: # If player vehicle exists
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        input_vector.y = -1
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        input_vector.y = 1
                    elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        input_vector.x = -1
                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        input_vector.x = 1
                
                if event.type == pygame.KEYUP:
                    if event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                        input_vector.y = 0
                    if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                        input_vector.x = 0
            # --- End of Player Control ---

            # Mouse click (debug) feature from map.py
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    pos = pygame.mouse.get_pos()
                    grid_col = pos[0] // map.CELL_SIZE
                    grid_row = pos[1] // map.CELL_SIZE
                    
                    if 0 <= grid_col < map.GRID_WIDTH and 0 <= grid_row < map.GRID_HEIGHT:
                        tile = world.grid[grid_row][grid_col]
                        coords = (grid_row, grid_col)
                        tile_type = type(tile)
                        state = None

                        if isinstance(tile, map.TrafficLight):
                            state = tile.state
                        elif isinstance(tile, map.Road):
                            state = tile.direction if tile.direction else 'Intersection'
                        
                        print(f"[Debug] Click: Position={coords}, Type={tile_type}, State={state}")
                    else:
                        print(f"[Debug] Click: Outside grid.")
        
        # --- Update Stage ---
        
        # 1. Update the world (changes traffic light states)
        world.update()
        
        # 2. Process player vehicle input
        if player_vehicle:
            player_vehicle.handle_input(input_vector)

        # 3. Update all vehicles (Car and Agent)
        # Send the list 'all_vehicles' so that vehicles can see each other
        for vehicle in all_vehicles:
            vehicle.update(all_vehicles)
            
        # --- Drawing Stage ---
        
        # 1. Clear the screen
        screen.fill(map.GREEN) # Set background to grass color
        
        # 2. Draw the map (roads, buildings, traffic lights)
        world.draw(screen)
        
        # 3. Draw all vehicles (Car and Agent) on top of the map
        for vehicle in all_vehicles:
            vehicle.draw(screen)
            
        # 4. Refresh the screen
        pygame.display.flip()
        
        # Cap FPS
        clock.tick(map.FPS)
    
    # Quit Pygame when loop ends
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
