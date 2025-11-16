import pygame
import sys
import random
import map
import algorithm
from car import Car
from agent import Agent
from pedestrian import PedestrianManager

def main():
    """Main simulation function."""
    pygame.init()

    try:
        screen = pygame.display.set_mode((map.SCREEN_WIDTH, map.SCREEN_HEIGHT))
        pygame.display.set_caption("Autonomous Vehicle Simulation + Pedestrians")
        clock = pygame.time.Clock()
    except AttributeError as e:
        print("Error: Missing SCREEN_WIDTH/HEIGHT constants in map.py.")
        return

    world = map.World(map.GRID_WIDTH, map.GRID_HEIGHT)
    random.seed(None)

    all_vehicles = []
    player_agent = None

    # Create normal cars
    num_cars = 10
    for _ in range(num_cars):
        all_vehicles.append(Car(world))

    # Pedestrian setup
    try:
        ped_sprite = pygame.image.load("images/man.png").convert_alpha()
        pedestrians = PedestrianManager(world, ped_sprite)
        world.pedestrian_manager = pedestrians
    except Exception as e:
        print(f"Warning: Pedestrian system could not be initialized. {e}")
        pedestrians = None

    # Click-based agent control
    selected_spawn = None
    destination = None
    last_click_time = 0
    last_click_tile = None
    DOUBLE_CLICK_MS = 420
    
    # Store algorithm choice for replanning
    current_algorithm = "astar"

    # Main loop
    running = True
    while running:
        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # LEFT CLICK = debug info / double-click for obstacles
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = pygame.mouse.get_pos()
                grid_col = pos[0] // map.CELL_SIZE
                grid_row = pos[1] // map.CELL_SIZE
                if not (0 <= grid_col < map.GRID_WIDTH and 0 <= grid_row < map.GRID_HEIGHT):
                    continue

                now = pygame.time.get_ticks()
                clicked_tile = (grid_row, grid_col)
                if last_click_tile == clicked_tile and (now - last_click_time) <= DOUBLE_CLICK_MS:
                    # Double-click: place obstacle
                    try:
                        tile = world.grid[grid_row][grid_col]
                        if isinstance(tile, map.Road):
                            world.grid[grid_row][grid_col] = map.Grass()
                            print(f"[World] Obstacle placed at {clicked_tile}")
                        else:
                            print("[World] Target is not a road.")
                    except Exception as e:
                        print(f"[World] Toggle failed: {e}")
                    last_click_time = 0
                    last_click_tile = None
                    continue

                # Single click: debug info
                last_click_time = now
                last_click_tile = clicked_tile
                tile = world.grid[grid_row][grid_col]
                tile_type = type(tile).__name__
                state = getattr(tile, "state", None)
                if isinstance(tile, map.Road):
                    state = tile.direction if tile.direction else "Intersection"
                print(f"[Debug] {grid_row, grid_col} | Type={tile_type} | State={state}")

            # RIGHT CLICK = agent spawn / target
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                pos = pygame.mouse.get_pos()
                grid_col = pos[0] // map.CELL_SIZE
                grid_row = pos[1] // map.CELL_SIZE

                if not (0 <= grid_col < map.GRID_WIDTH and 0 <= grid_row < map.GRID_HEIGHT):
                    print("[Click] Outside grid.")
                    continue

                # First right-click = spawn
                if selected_spawn is None:
                    selected_spawn = (grid_row, grid_col)

                    try:
                        if player_agent is None:
                            player_agent = Agent(world)
                            all_vehicles.append(player_agent)
                            print(f"[Info] Agent created at {selected_spawn}.")
                        player_agent.set_position(grid_row, grid_col)
                        player_agent.stop()
                    except Exception as e:
                        print(f"[Agent] Invalid spawn: {e}")
                        selected_spawn = None

                # Second right-click = destination
                elif destination is None:
                    destination = (grid_row, grid_col)
                    print(f"[Agent] Destination selected at {destination}")

                    # Show highlight
                    try:
                        highlight = pygame.Surface((map.CELL_SIZE, map.CELL_SIZE), pygame.SRCALPHA)
                        highlight.fill((40, 220, 40, 60))
                        screen.fill(map.GREEN)
                        world.draw(screen)
                        for vehicle in all_vehicles:
                            vehicle.draw(screen)
                        screen.blit(highlight, (destination[1] * map.CELL_SIZE, destination[0] * map.CELL_SIZE))
                        pygame.display.flip()
                    except Exception:
                        pass

                    if player_agent and selected_spawn:
                        try:
                            print("Choose algorithm (dfs/bfs/greedy/astar):")
                            algo_choice = input().strip().lower()
                            current_algorithm = algo_choice if algo_choice in ["dfs", "bfs", "greedy", "astar"] else "astar"
                        except Exception:
                            current_algorithm = "astar"

                        visualizer = create_visualizer(current_algorithm, world, screen, clock)

                        try:
                            path = visualizer.search(selected_spawn, destination, speed=0.03)
                            if path:
                                player_agent.move(path)
                            else:
                                print(f"[Agent] No path found.")
                        except SystemExit:
                            raise
                        except Exception as e:
                            print(f"[Agent] Pathfinding error: {e}")

                    selected_spawn = None
                    destination = None

        # Handle agent replanning
        if player_agent and player_agent.awaiting_approval:
            start = (player_agent.grid_y, player_agent.grid_x)
            goal = player_agent.destination

            visualizer = create_visualizer(current_algorithm, world, screen, clock)
            new_path = visualizer.search(start, goal)

            player_agent.approve_replan(new_path)


        # --- Update ---
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

    pygame.quit()
    sys.exit()


def create_visualizer(algo_choice, world, screen, clock):
    """Helper function to create the appropriate visualizer."""
    if algo_choice == "dfs":
        return algorithm.DFSVisualizer(world, screen, map.CELL_SIZE, clock)
    elif algo_choice == "bfs":
        return algorithm.BFSVisualizer(world, screen, map.CELL_SIZE, clock)
    elif algo_choice in ("greedy", "gbfs"):
        return algorithm.GreedyBestFirstVisualizer(world, screen, map.CELL_SIZE, clock)
    else:
        return algorithm.AStarVisualizer(world, screen, map.CELL_SIZE, clock)


if __name__ == "__main__":
    main()