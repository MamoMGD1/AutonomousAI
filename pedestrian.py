import pygame
import sys
import random
import map

# Import constants and grid parameters from the map module
CELL_SIZE = map.CELL_SIZE
GRID_WIDTH = map.GRID_WIDTH
GRID_HEIGHT = map.GRID_HEIGHT
SCREEN_WIDTH = map.SCREEN_WIDTH
SCREEN_HEIGHT = map.SCREEN_HEIGHT
FPS = map.FPS

# Short aliases for tile classes
Road = map.Road
Crosswalk = map.Crosswalk
TrafficLight = map.TrafficLight
Grass = map.Grass
Building = map.Building

# ---------- PEDESTRIAN SIMULATION LOGIC ----------

class Pedestrian(pygame.sprite.Sprite):
    """
    Represents a single pedestrian that knows its near and far edges (entry and exit points)
    and moves between them depending on its state.
    """
    def __init__(self, near_edge_px, far_edge_px, speed_px, sprite_surface, crossing_idx, scale=1.0):
        super().__init__()
        # Scale the pedestrian image based on cell size and optional scaling factor
        base = int(CELL_SIZE * 0.9 * scale)
        self.image = pygame.transform.smoothscale(sprite_surface, (base, base))
        self.rect = self.image.get_rect()

        # Position vectors for start (near edge) and destination (far edge)
        self.pos = pygame.Vector2(near_edge_px[0], near_edge_px[1])
        self.near_edge = pygame.Vector2(near_edge_px[0], near_edge_px[1])
        self.far_edge = pygame.Vector2(far_edge_px[0], far_edge_px[1])

        # Movement speed in pixels per second
        self.speed = speed_px
        self.rect.center = (round(self.pos.x), round(self.pos.y))

        # State machine: walking_to_edge → waiting → crossing → done
        self.state = 'walking_to_edge'
        self.crossing_idx = crossing_idx  # which crosswalk this pedestrian belongs to

    def bbox(self):
        """Returns the bounding box of the pedestrian for collision or visualization."""
        return self.rect.x, self.rect.y, self.rect.w, self.rect.h

    def update(self, dt):
        """Handles movement between states according to position and distance."""
        # Choose a target based on the current state
        target = None
        if self.state == 'walking_to_edge':
            target = self.near_edge
        elif self.state == 'crossing':
            target = self.far_edge

        # Move toward the target and handle state transitions
        if target is not None:
            direction = (target - self.pos)
            dist = direction.length()
            if dist > 1e-6:
                direction = direction.normalize()
            step = self.speed * dt

            # Snap to target if close enough, otherwise keep moving
            if dist <= step:
                self.pos = pygame.Vector2(target.x, target.y)
                if self.state == 'walking_to_edge':
                    self.state = 'waiting'   # reached the waiting spot near the light
                elif self.state == 'crossing':
                    self.state = 'done'      # finished the crossing
            else:
                # Move toward the target
                self.pos += direction * step

            # Update drawing position
            self.rect.center = (round(self.pos.x), round(self.pos.y))


class PedestrianManager:
    """
    Controls all pedestrians in the world:
      - Handles spawn timing and limits
      - Connects pedestrians to crosswalks and traffic lights
      - Updates movement and state transitions
      - Removes finished pedestrians
    """
    INITIAL_BATCH = 15
    MIN_BATCH = 3
    MAX_BATCH = 15
    MAX_ACTIVE = 20
    SPAWN_INTERVAL = 1.5  # seconds between spawn attempts

    def __init__(self, world, sprite_surface):
        # Keep references to the world and the pedestrian sprite sheet/surface
        self.world = world
        self.sprite_surface = sprite_surface

        # Sprite group to manage and draw all active pedestrians
        self.group = pygame.sprite.Group()

        # Build an index of crosswalk clusters and their nearest traffic lights
        self.crossings = self._index_crosswalks_and_lights()

        # Initialize light state memory and waiting lists per crossing
        for cr in self.crossings:
            cr['prev_state'] = self._get_light_state(cr['light_rc'])
            cr['waiting_peds'] = set()

        # Spawn an initial batch of pedestrians and reset the spawn timer
        self._spawn_batch(self.INITIAL_BATCH)
        self._spawn_accum = 0.0

    # ---------- CROSSWALK AND LIGHT SETUP ----------
    def _index_crosswalks_and_lights(self):
        """
        Scans the map grid and groups crosswalk tiles into clusters.
        Associates each cluster with its nearest traffic light.

        IMPORTANT:
          The pedestrian waiting point is placed on the GRASS tile that contains
          the traffic light, offset slightly toward the crosswalk center
          (so pedestrians never stand on the road or crosswalk).
        """
        # Readability aliases for the grid and its dimensions
        g = self.world.grid
        H, W = self.world.grid_height, self.world.grid_width

        # Visited flags for BFS over crosswalk tiles
        visited = [[False]*W for _ in range(H)]

        # Accumulator for discovered crossing clusters
        crossings = []

        # Small helper: check bounds for (row, col)
        def inb(r, c): return 0 <= r < H and 0 <= c < W

        # Scan the entire grid for crosswalk tiles
        for r in range(H):
            for c in range(W):
                # Start a BFS when we find an unvisited crosswalk tile
                if isinstance(g[r][c], Crosswalk) and not visited[r][c]:
                    # BFS queue and the current cluster container
                    q = [(r, c)]
                    cluster = []
                    visited[r][c] = True

                    # Explore 4-connected neighbors to collect the cluster
                    while q:
                        rr, cc = q.pop()
                        cluster.append((rr, cc))
                        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
                            nr, nc = rr+dr, cc+dc
                            if inb(nr, nc) and not visited[nr][nc] and isinstance(g[nr][nc], Crosswalk):
                                visited[nr][nc] = True
                                q.append((nr, nc))

                    # Use the first tile's orientation as the cluster orientation
                    orient = g[cluster[0][0]][cluster[0][1]].orientation  # 'vertical' or 'horizontal'

                    # Search for the nearest traffic light around the cluster (within a small window)
                    light = None
                    for rr, cc in cluster:
                        for dr in range(-2, 3):
                            for dc in range(-2, 3):
                                nr, nc = rr+dr, cc+dc
                                if inb(nr, nc) and isinstance(g[nr][nc], TrafficLight):
                                    light = (nr, nc)
                                    break
                            if light: break
                        if light: break

                    # Convert (row, col) to pixel center of a cell
                    def px_center(rc):
                        rr, cc = rc
                        return ((cc+0.5)*CELL_SIZE, (rr+0.5)*CELL_SIZE)

                    # Compute cluster bounds and a representative midpoint
                    cols = [cc for rr, cc in cluster]
                    rows = [rr for rr, cc in cluster]
                    minc, maxc = min(cols), max(cols)
                    minr, maxr = min(rows), max(rows)
                    cw_mid_rc = cluster[len(cluster)//2]
                    cw_mid_px = px_center(cw_mid_rc)

                    # Offset distance used to place near/far points safely off the road
                    d = 0.45 * CELL_SIZE

                    # Compute the waiting point near the light (on grass, nudged toward the crosswalk)
                    if light is not None:
                        light_cx, light_cy = px_center(light)
                        v_to_cw = pygame.Vector2(cw_mid_px[0] - light_cx, cw_mid_px[1] - light_cy)
                        if v_to_cw.length() > 1e-6:
                            v_to_cw = v_to_cw.normalize()
                        near_from_light = (
                            light_cx + v_to_cw.x * (0.30 * CELL_SIZE),
                            light_cy + v_to_cw.y * (0.30 * CELL_SIZE)
                        )
                    else:
                        # Fallback near point if no light exists (still keep it on grass)
                        if orient == 'vertical':
                            near_from_light = ((minc+0.5)*CELL_SIZE - d, cw_mid_px[1])
                        else:
                            near_from_light = (cw_mid_px[0], (minr+0.5)*CELL_SIZE - d)

                    # Prepare entry/exit pairs and axis for jittering later
                    pairs = []
                    axis = 'x' if orient == 'vertical' else 'y'

                    if orient == 'vertical':
                        # Horizontal traverse across a vertical crosswalk cluster (left <-> right)
                        far = ((maxc+0.5)*CELL_SIZE + d, cw_mid_px[1])
                        pairs.append((near_from_light, far))
                    else:
                        # Vertical traverse across a horizontal crosswalk cluster (top <-> bottom)
                        far = (cw_mid_px[0], (maxr+0.5)*CELL_SIZE + d)
                        pairs.append((near_from_light, far))

                    # Record the discovered crossing cluster and metadata
                    crossings.append({
                        'orientation': orient,
                        'light_rc': light,
                        'pairs': pairs,
                        'axis': axis,
                        'bounds': (minr, maxr, minc, maxc)
                    })
        return crossings

    # ---------- TRAFFIC LIGHT DECISIONS ----------
    def _light_decision(self, state):
        # Probability model: often-cross-on-red (90%), slow-to-react-on-green (10%), never on yellow
        if state == 'red':   return random.random() < 0.10
        if state == 'green': return random.random() < 0.90
        return False

    def _get_light_state(self, rc):
        # Safely read current light state or treat as yellow if absent
        if rc is None: return 'yellow'
        r, c = rc
        tl = self.world.grid[r][c]
        return tl.state if isinstance(tl, TrafficLight) else 'yellow'

    # ---------- SPAWNING ----------
    def _spawn_one(self):
        # Abort if there are no crossings indexed
        if not self.crossings:
            return None

        # Choose a random crossing and a (near, far) pair
        idx = random.randrange(len(self.crossings))
        cr = self.crossings[idx]
        near, far = random.choice(cr['pairs'])

        # Randomize speed/scale and apply small jitter perpendicular to movement
        speed = random.uniform(CELL_SIZE * 1.2, CELL_SIZE * 2.8)
        scale = random.uniform(1.50, 1.75)
        j = 0.15 * CELL_SIZE
        if cr['axis'] == 'x':
            dy = random.uniform(-j, j)
            near = (near[0], near[1] + dy)
            far = (far[0], far[1] + dy)
        else:
            dx = random.uniform(-j, j)
            near = (near[0] + dx, near[1])
            far = (far[0] + dx, far[1])

        # Create and register the pedestrian in the group
        ped = Pedestrian(near, far, speed, self.sprite_surface, idx, scale)
        self.group.add(ped)
        return ped

    def _spawn_batch(self, n):
        # Spawn N pedestrians back-to-back
        for _ in range(n):
            self._spawn_one()

    # ---------- UPDATE LOOP ----------
    def update(self, dt):
        # Accumulate time and periodically attempt to spawn more pedestrians
        self._spawn_accum += dt
        if self._spawn_accum >= self.SPAWN_INTERVAL:
            self._spawn_accum = 0.0
            active = len(self.group)
            if active < self.MAX_ACTIVE:
                need = self.MAX_ACTIVE - active
                batch = random.randint(self.MIN_BATCH, self.MAX_BATCH)
                batch = min(batch, need)
                self._spawn_batch(batch)

        # Per-pedestrian update and transitions management
        to_remove = []
        for ped in list(self.group):
            prev_state = ped.state
            ped.update(dt)

            # When a pedestrian reaches the near point, add to waiting set and maybe allow crossing
            if prev_state != 'waiting' and ped.state == 'waiting':
                crw = self.crossings[ped.crossing_idx]
                crw['waiting_peds'].add(ped)
                current_now = self._get_light_state(crw['light_rc'])
                if self._light_decision(current_now):
                    ped.state = 'crossing'
                    crw['waiting_peds'].discard(ped)

            # Remove pedestrians that have finished crossing
            if ped.state == 'done':
                self.crossings[ped.crossing_idx]['waiting_peds'].discard(ped)
                to_remove.append(ped)

        # Physically delete finished pedestrians from the sprite group
        for p in to_remove:
            p.kill()

        # On light state change, re-evaluate waiting pedestrians
        for idx, cr in enumerate(self.crossings):
            current = self._get_light_state(cr['light_rc'])
            if current != cr['prev_state']:
                for ped in list(cr['waiting_peds']):
                    if ped.state == 'waiting' and self._light_decision(current):
                        ped.state = 'crossing'
                        cr['waiting_peds'].discard(ped)
                cr['prev_state'] = current

    # ---------- DETECTION & DRAW ----------
    def detect(self):
        # Build a list of lightweight detection records for each pedestrian
        boxes = []
        for ped in self.group:
            x, y, w, h = ped.bbox()
            grid_c = int((x + w/2) // CELL_SIZE)
            grid_r = int((y + h/2) // CELL_SIZE)
            boxes.append({'grid_rc': (grid_r, grid_c), 'bbox_px': (x, y, w, h), 'state': ped.state})
        return boxes

    def draw(self, screen):
        """Draws pedestrians on the screen."""
        self.group.draw(screen)


# ---------- MAIN EXECUTION LOOP ----------
def main():
    """Launches the simulation window and runs the pedestrian system."""
    # Initialize Pygame and create the main window
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Autonomous Vehicle + Pedestrians")
    clock = pygame.time.Clock()

    # Construct the world and the pedestrian manager
    world = map.World(GRID_WIDTH, GRID_HEIGHT)
    sprite = pygame.image.load("images/man.png").convert_alpha()
    peds = PedestrianManager(world, sprite)

    # Main loop: update simulation, then render a frame
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        # Handle OS-level quit event only (no debug keys)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Update world and pedestrians
        world.update()
        peds.update(dt)

        # Draw all elements
        screen.fill((255, 255, 255))
        world.draw(screen)
        peds.draw(screen)

        pygame.display.flip()

    # Clean up when the window is closed
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()