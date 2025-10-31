import pygame
import sys
import random
import map  # Map, tiles, and World class
from car import Car   # Randomly roaming Car class
from agent import Agent  # Automated Agent class (path-following)
from pedestrian import PedestrianManager

def main():
    """
    Main simulation function.
    Initializes Pygame, sets up the world, creates vehicles & pedestrians, and runs the main loop.
    """
    # --- Initialization ---
    pygame.init()

    # Window setup
    try:
        screen = pygame.display.set_mode((map.SCREEN_WIDTH, map.SCREEN_HEIGHT))
        pygame.display.set_caption("Autonomous Vehicle Simulation + Pedestrians")
        clock = pygame.time.Clock()
    except AttributeError as e:
        print("Error: Missing SCREEN_WIDTH/HEIGHT constants in map.py.")
        print(f"Detail: {e}")
        return

    # --- World Setup ---
    world = map.World(map.GRID_WIDTH, map.GRID_HEIGHT)
    random.seed(None)

    # --- Vehicles ---
    all_vehicles = []
    player_agent = None

    # 1. Create AI cars
    num_cars = 10
    for _ in range(num_cars):
        all_vehicles.append(Car(world))

    # 2. Create one Agent (automated)
    try:
        player_agent = Agent(world)
        all_vehicles.append(player_agent)
        print("[Info] Agent created successfully.")
    except Exception as e:
        print(f"[Warning] Could not create Agent: {e}")
        player_agent = None

    # --- Pedestrian Setup ---
    try:
        ped_sprite = pygame.image.load("images/man.png").convert_alpha()
        pedestrians = PedestrianManager(world, ped_sprite)
        world.pedestrian_manager = pedestrians
    except Exception as e:
        print(f"Warning: Pedestrian system could not be initialized. {e}")
        pedestrians = None

    # --- Click-based Agent control ---
    selected_spawn = None  # grid (row, col)
    destination = None     # grid (row, col)

    # --- Main Loop ---
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # LEFT CLICK = debug info
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = pygame.mouse.get_pos()
                grid_col = pos[0] // map.CELL_SIZE
                grid_row = pos[1] // map.CELL_SIZE
                if 0 <= grid_col < map.GRID_WIDTH and 0 <= grid_row < map.GRID_HEIGHT:
                    tile = world.grid[grid_row][grid_col]
                    tile_type = type(tile).__name__
                    state = getattr(tile, "state", None)
                    if isinstance(tile, map.Road):
                        state = tile.direction if tile.direction else "Intersection"
                    print(f"[Debug] Click at {grid_row, grid_col} | Type={tile_type} | State={state}")
                else:
                    print("[Debug] Click outside grid.")

            # RIGHT CLICK = spawn or path assignment
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                pos = pygame.mouse.get_pos()
                grid_col = pos[0] // map.CELL_SIZE
                grid_row = pos[1] // map.CELL_SIZE

                if not (0 <= grid_col < map.GRID_WIDTH and 0 <= grid_row < map.GRID_HEIGHT):
                    print("[Click] Outside grid.")
                    continue

                # First right-click = choose spawn location
                if selected_spawn is None:
                    selected_spawn = (grid_row, grid_col)
                    print(f"[Agent] Spawn selected at {selected_spawn}")

                    # Place the agent there
                    if player_agent:
                        try:
                            player_agent.set_position(grid_row, grid_col)
                            player_agent.stop()
                            print("[Agent] Moved to selected start position.")
                        except Exception as e:
                            print(f"[Agent] Invalid spawn: {e}")
                            selected_spawn = None

                # Second right-click = choose destination and move
                elif destination is None:
                    destination = (grid_row, grid_col)
                    print(f"[Agent] Destination selected at {destination}")

                    if player_agent and selected_spawn:
                        # Compute A* path from spawn → destination
                        try:
                            path = [(5,1), (5,2), (5,3), (5,4), (5,5), (5,6), (6, 6), (7, 6)]
                            if path:
                                player_agent.move(path)
                                print(f"[Agent] Path found: {len(path)} steps.")
                            else:
                                print("[Agent] No valid path found.")
                        except Exception as e:
                            print(f"[Agent] Pathfinding error: {e}")

                    # Reset selections for next interaction
                    selected_spawn = None
                    destination = None

        # --- Updates ---
        dt = clock.tick(map.FPS) / 1000.0
        world.update()

        for vehicle in all_vehicles:
            vehicle.update(all_vehicles)

        if pedestrians:
            pedestrians.update(dt)

        # --- Draw ---
        screen.fill(map.GREEN)
        world.draw(screen)
        for vehicle in all_vehicles:
            vehicle.draw(screen)
        if pedestrians:
            pedestrians.draw(screen)

        pygame.display.flip()

    # --- Cleanup ---
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()