import pygame
import heapq
import map

# Colors
YELLOW = (255, 220, 0)
GREEN = (0, 255, 0)
GREY = (140, 140, 140)

class SearchVisualizer:
    def __init__(self, world, screen, cell_size=None, clock=None):
        self.world = world
        self.screen = screen
        self.cell_size = cell_size if cell_size is not None else map.CELL_SIZE
        self.clock = clock if clock is not None else pygame.time.Clock()
        self.overlay = pygame.Surface((map.SCREEN_WIDTH, map.SCREEN_HEIGHT), pygame.SRCALPHA)
        # edges are stored as frozenset({a,b}) where a=(r,c)
        self.visited_edges = set()

    def is_passable(self, cell):
        r, c = cell
        if not (0 <= r < map.GRID_HEIGHT and 0 <= c < map.GRID_WIDTH):
            return False
        tile = self.world.grid[r][c]
        return isinstance(tile, (map.Road, map.Crosswalk))

    def _movement_dir(self, a, b):
        dr = b[0] - a[0]
        dc = b[1] - a[1]
        if dr == -1 and dc == 0:
            return 'N'
        if dr == 1 and dc == 0:
            return 'S'
        if dr == 0 and dc == 1:
            return 'E'
        if dr == 0 and dc == -1:
            return 'W'
        return None

    def _can_move(self, a, b):
        # respects road direction and allows turns only at intersections (Road.direction is None)
        if not (self.is_passable(a) and self.is_passable(b)):
            return False
        atile = self.world.grid[a[0]][a[1]]
        btile = self.world.grid[b[0]][b[1]]
        move_dir = self._movement_dir(a, b)
        # treat Crosswalk as directional (no free turns): allow only moves that match the crosswalk orientation
        def tile_allows(tile, dir_):
            # Crosswalks only allow movement along their orientation (no turning while on/into crosswalk)
            if isinstance(tile, map.Crosswalk):
                # crosswalk.orientation expected 'horizontal' or 'vertical'
                if getattr(tile, "orientation", "horizontal") == "horizontal":
                    return dir_ in ("E", "W")
                else:
                    return dir_ in ("N", "S")
            if isinstance(tile, map.Road):
                # intersection (direction is None) allows turning when leaving it
                return (tile.direction is None) or (tile.direction == dir_)
            return False
        # allow turning only when leaving an intersection (current is intersection) OR following road direction
        return tile_allows(atile, move_dir) and tile_allows(btile, move_dir)

    def neighbors(self, cell):
        r, c = cell
        # prefer straight-ish order but actual direction awareness done in _can_move
        dirs = [(-1, 0), (0, -1), (0, 1), (1, 0)]
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < map.GRID_HEIGHT and 0 <= nc < map.GRID_WIDTH:
                yield (nr, nc)

    def pixel_center(self, cell):
        r, c = cell
        cx = c * self.cell_size + self.cell_size // 2
        cy = r * self.cell_size + self.cell_size // 2
        return (cx, cy)

    def _process_pygame_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

    def _animate_line(self, a_px, b_px, color=YELLOW, duration=0.06, steps=10):
        ax, ay = a_px
        bx, by = b_px
        for i in range(1, steps + 1):
            t = i / steps
            ix = int(ax + (bx - ax) * t)
            iy = int(ay + (by - ay) * t)
            self.overlay.fill((0,0,0,0))
            pygame.draw.line(self.overlay, color, a_px, (ix, iy), max(2, self.cell_size // 6))
            self.screen.blit(self.overlay, (0, 0))
            pygame.display.flip()
            self._process_pygame_events()
            self.clock.tick(max(1, int(1.0 / (duration / steps + 0.0001))))

    def draw_visited_edge(self, a, b, color=YELLOW):
        a_px = self.pixel_center(a)
        b_px = self.pixel_center(b)
        pygame.draw.line(self.overlay, color, a_px, b_px, max(2, self.cell_size // 6))
        self.visited_edges.add(frozenset((a,b)))
        self.screen.blit(self.overlay, (0,0))
        pygame.display.flip()

    def draw_final_path(self, path, color=GREEN):
        if not path:
            return
        for i in range(len(path)-1):
            a_px = self.pixel_center(path[i])
            b_px = self.pixel_center(path[i+1])
            pygame.draw.line(self.overlay, color, a_px, b_px, max(3, self.cell_size // 4))
        self.screen.blit(self.overlay, (0,0))
        pygame.display.flip()

    def _recolor_after_search(self, final_path):
        # Turn all visited edges grey, then draw final path green on top.
        self.overlay.fill((0,0,0,0))
        for fe in self.visited_edges:
            a,b = tuple(fe)
            a_px = self.pixel_center(a)
            b_px = self.pixel_center(b)
            pygame.draw.line(self.overlay, GREY, a_px, b_px, max(2, self.cell_size // 6))
        # draw final path in green
        if final_path:
            for i in range(len(final_path)-1):
                a_px = self.pixel_center(final_path[i])
                b_px = self.pixel_center(final_path[i+1])
                pygame.draw.line(self.overlay, GREEN, a_px, b_px, max(3, self.cell_size // 4))
        self.screen.blit(self.overlay, (0,0))
        pygame.display.flip()

    def _confirm_and_commit(self, final_path, auto_accept=False):
        # show all branches grey and path green then ask user in terminal
        self._recolor_after_search(final_path)
        if auto_accept:
            # commit immediately without prompting
            
# TODO [KALDIRILDI]: Eski mantık, kaplamayı hemen temizledi.
# Kullanıcı onayını beklerken main.py'nin gri çizgileri gösterebilmesi için bunu yorum satırına aldık.
            # self.overlay.fill((0,0,0,0))
            # if final_path:
            #     for i in range(len(final_path)-1):
            #         a_px = self.pixel_center(final_path[i])
            #         b_px = self.pixel_center(final_path[i+1])
            #         pygame.draw.line(self.overlay, GREEN, a_px, b_px, max(3, self.cell_size // 4))
            # self.screen.blit(self.overlay, (0,0))
            # pygame.display.flip()

          # TODO [EKLENDİ]: Hemen True değerini döndür ancak kaplamayı çizilmiş halde tut (gri + yeşil).
            return True

        try:
            print("Accept this path? (y/n) and Enter:") # ihtiyacimiz yok
            choice = input().strip().lower()
        except Exception:
            choice = 'y'
        if choice and choice[0] == 'y':
            # commit: keep only green path (clear grey by drawing only final path)
            self.overlay.fill((0,0,0,0))
            if final_path:
                for i in range(len(final_path)-1):
                    a_px = self.pixel_center(final_path[i])
                    b_px = self.pixel_center(final_path[i+1])
                    pygame.draw.line(self.overlay, GREEN, a_px, b_px, max(3, self.cell_size // 4))
            self.screen.blit(self.overlay, (0,0))
            pygame.display.flip()
            return True
        else:
            # clear overlay
            self.overlay.fill((0,0,0,0))
            self.screen.blit(self.overlay, (0,0))
            pygame.display.flip()
            return False

class DFSVisualizer(SearchVisualizer):
    def search(self, start, goal, speed=0.03, auto_accept=False):
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        if not self.is_passable(start) or not self.is_passable(goal):
            return []

        visited = set()
        parent = {}
        stack = [start]
        self.overlay.fill((0,0,0,0))
        self.visited_edges.clear()

        while stack:
            self._process_pygame_events()
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            if current in parent:
                p = parent[current]
                # only animate and commit this edge if movement obeys tile directions
                if self._can_move(p, current):
                    self._animate_line(self.pixel_center(p), self.pixel_center(current), color=YELLOW, duration=speed)
                    self.draw_visited_edge(p, current, color=YELLOW)
            else:
                cx, cy = self.pixel_center(current)
                pygame.draw.circle(self.overlay, YELLOW, (cx, cy), min(2, self.cell_size//8))
                self.screen.blit(self.overlay, (0,0))
                pygame.display.flip()

            if current == goal:
                # reconstruct path
                path = []
                node = current
                while True:
                    path.append(node)
                    if node == start:
                        break
                    node = parent[node]
                path.reverse()
                committed = self._confirm_and_commit(path, auto_accept=auto_accept)
                return path if committed else []

            # gather neighbors that obey tile-direction rules
            nbs = []
            for nb in self.neighbors(current):
                if nb in visited:
                    continue
                if not self._can_move(current, nb):
                    continue
                nbs.append(nb)
                if nb not in parent:
                    parent[nb] = current
            # push in reversed order to keep neighbor order preference
            for nb in reversed(nbs):
                stack.append(nb)

        # not found
        self.overlay.fill((0,0,0,0))
        self.screen.blit(self.overlay, (0,0))
        pygame.display.flip()
        return []

class BFSVisualizer(SearchVisualizer):
    def search(self, start, goal, speed=0.02, auto_accept=False):
        """
        Breadth-First Search with realtime visualization.
        Returns path list or [] if not found. Direction-aware via _can_move.
        """
        from collections import deque
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        if not self.is_passable(start) or not self.is_passable(goal):
            return []

        q = deque([start])
        parent = {}
        visited = set([start])

        self.overlay.fill((0,0,0,0))
        self.visited_edges.clear()

        while q:
            self._process_pygame_events()
            current = q.popleft()

            if current in parent:
                p = parent[current]
                if self._can_move(p, current):
                    self._animate_line(self.pixel_center(p), self.pixel_center(current), color=YELLOW, duration=speed)
                    self.draw_visited_edge(p, current, color=YELLOW)
            else:
                cx, cy = self.pixel_center(current)
                pygame.draw.circle(self.overlay, GREY, (cx, cy), max(2, self.cell_size//10))
                self.screen.blit(self.overlay, (0,0))
                pygame.display.flip()

            if current == goal:
                # reconstruct path
                path = []
                node = current
                while True:
                    path.append(node)
                    if node == start:
                        break
                    node = parent[node]
                path.reverse()
                committed = self._confirm_and_commit(path, auto_accept=auto_accept)
                return path if committed else []

            for nb in self.neighbors(current):
                if nb in visited:
                    continue
                if not self._can_move(current, nb):
                    continue
                visited.add(nb)
                parent[nb] = current
                q.append(nb)

        self.overlay.fill((0,0,0,0))
        self.screen.blit(self.overlay, (0,0))
        pygame.display.flip()
        return []

class AStarVisualizer(SearchVisualizer):
    def manhattan(self, a, b):
        return abs(a[0]-b[0]) + abs(a[1]-b[1])

    def search(self, start, goal, speed=0.02, auto_accept=False):
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        if not self.is_passable(start) or not self.is_passable(goal):
            return []

        open_heap = []
        heapq.heappush(open_heap, (self.manhattan(start, goal), 0, start))
        came_from = {}
        gscore = {start: 0}
        closed = set()
        self.overlay.fill((0,0,0,0))
        self.visited_edges.clear()

        while open_heap:
            self._process_pygame_events()
            _, g, current = heapq.heappop(open_heap)
            if current in closed:
                continue
            closed.add(current)

            if current in came_from:
                p = came_from[current]
                if self._can_move(p, current):
                    self._animate_line(self.pixel_center(p), self.pixel_center(current), color=YELLOW, duration=speed)
                    self.draw_visited_edge(p, current, color=YELLOW)
            else:
                cx, cy = self.pixel_center(current)
                pygame.draw.circle(self.overlay, GREY, (cx, cy), max(2, self.cell_size//10))
                self.screen.blit(self.overlay, (0,0))
                pygame.display.flip()

            if current == goal:
                # reconstruct path
                path = []
                node = current
                while node in came_from:
                    path.append(node)
                    node = came_from[node]
                path.append(start)
                path.reverse()
                committed = self._confirm_and_commit(path, auto_accept=auto_accept)
                return path if committed else []

            for nb in self.neighbors(current):
                if not self.is_passable(nb) or nb in closed:
                    continue
                if not self._can_move(current, nb):
                    continue
                tentative_g = gscore[current] + 1
                if tentative_g < gscore.get(nb, 1e9):
                    came_from[nb] = current
                    gscore[nb] = tentative_g
                    f = tentative_g + self.manhattan(nb, goal)
                    heapq.heappush(open_heap, (f, tentative_g, nb))

        self.overlay.fill((0,0,0,0))
        self.screen.blit(self.overlay, (0,0))
        pygame.display.flip()
        return []

class GreedyBestFirstVisualizer(SearchVisualizer):
    def manhattan(self, a, b):
        return abs(a[0]-b[0]) + abs(a[1]-b[1])

    def search(self, start, goal, speed=0.015, auto_accept=False):
        """
        Greedy Best-First Search using Manhattan heuristic (f = h only).
        Direction-aware via _can_move. Returns path or [].
        """
        import heapq
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        if not self.is_passable(start) or not self.is_passable(goal):
            return []

        open_heap = []
        heapq.heappush(open_heap, (self.manhattan(start, goal), start))
        came_from = {}
        closed = set()

        self.overlay.fill((0,0,0,0))
        self.visited_edges.clear()

        while open_heap:
            self._process_pygame_events()
            _, current = heapq.heappop(open_heap)
            if current in closed:
                continue
            closed.add(current)

            if current in came_from:
                p = came_from[current]
                if self._can_move(p, current):
                    self._animate_line(self.pixel_center(p), self.pixel_center(current), color=YELLOW, duration=speed)
                    self.draw_visited_edge(p, current, color=YELLOW)
            else:
                cx, cy = self.pixel_center(current)
                pygame.draw.circle(self.overlay, GREY, (cx, cy), max(2, self.cell_size//10))
                self.screen.blit(self.overlay, (0,0))
                pygame.display.flip()

            if current == goal:
                path = []
                node = current
                while node in came_from:
                    path.append(node)
                    node = came_from[node]
                path.append(start)
                path.reverse()
                committed = self._confirm_and_commit(path, auto_accept=auto_accept)
                return path if committed else []

            for nb in self.neighbors(current):
                if not self.is_passable(nb) or nb in closed:
                    continue
                if not self._can_move(current, nb):
                    continue
                if nb not in came_from:
                    came_from[nb] = current
                    heapq.heappush(open_heap, (self.manhattan(nb, goal), nb))

        self.overlay.fill((0,0,0,0))
        self.screen.blit(self.overlay, (0,0))
        pygame.display.flip()
        return []