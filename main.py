import pygame
import sys
import random
import map
import algorithm
from car import Car
from agent import Agent
from pedestrian import PedestrianManager
from interface import Interface, PANEL_WIDTH

# Pencere Boyutları
TOTAL_WIDTH = map.SCREEN_WIDTH + PANEL_WIDTH
TOTAL_HEIGHT = map.SCREEN_HEIGHT

def main():
    pygame.init()
    try:
        # Ana ekran: hem harita hem kontrol paneli tek yüzeyde
        screen = pygame.display.set_mode((TOTAL_WIDTH, TOTAL_HEIGHT))
        pygame.display.set_caption("Autonomous Vehicle")
        clock = pygame.time.Clock()
    except AttributeError:
        print("Error: Missing constants in map.py.")
        return

    world = None
    ui = Interface(map.SCREEN_WIDTH, map.SCREEN_HEIGHT)
    all_vehicles = []
    player_agent = None
    pedestrians = None
    
    # Mantıksal Değişkenler
    destination = None          # Ajanın gitmek istediği hedef grid hücresi
    dragging_agent = False      # Ajanı fare ile sürüklüyor muyuz?
    is_simulation_frozen = False # Simülasyon zamanını dondurma kontrolü
    
    # Onay ve Görselleştirme Değişkenleri (YENİ)
    pending_path = None         # Onay bekleyen geçici yol
    active_visualizer = None    # Arama algoritmasının görselleştirmesini saklamak için

    def reset_simulation_state():
        """
        Tüm simülasyon durumunu sıfırlar:
        - Dünya (grid) yeniden oluşturulur.
        - Araçlar, yayalar ve ajan yeniden başlatılır.
        - Panel durumu temizlenir.
        """
        # TODO: [DEĞİŞTİRİLDİ] Yeni değişkenler (pending_path, active_visualizer) sıfırlama işlemine eklendi.
        nonlocal world, all_vehicles, player_agent, pedestrians, destination, is_simulation_frozen, pending_path, active_visualizer
        
        world = map.World(map.GRID_WIDTH, map.GRID_HEIGHT)
        all_vehicles = []
        
        # Normal araçları oluştur
        num_cars = 10
        for _ in range(num_cars):
            all_vehicles.append(Car(world))
            
        # Yayaları yükle (varsa sprite)
        try:
            ped_sprite = pygame.image.load("images/man.png").convert_alpha()
            pedestrians = PedestrianManager(world, ped_sprite)
            world.pedestrian_manager = pedestrians
        except Exception:
            pedestrians = None
            
        # Oyuncu ajanını oluştur
        player_agent = Agent(world)
        start_pos = (map.GRID_HEIGHT - 2, 2)
        try:
            player_agent.set_position(start_pos[0], start_pos[1])
        except:
            pass
        player_agent.stop()
        all_vehicles.append(player_agent)
        
        # Değişkenleri sıfırla
        destination = None
        is_simulation_frozen = False
        pending_path = None 
        active_visualizer = None
        
        # UI başlangıç değerleri
        ui.state.agent_pos = (player_agent.grid_y, player_agent.grid_x)
        ui.state.path_cost = 0
        ui.state.visited_count = 0
        ui.state.path_found = None
        ui.state.traffic_light_info = None
        ui.state.awaiting_confirmation = False
        ui.state.status_message = "System Reset Done"
        
        print("[System] Full Reset Complete.")

    reset_simulation_state()

    def get_visualizer(algo_choice):
        """
        Seçilen algoritma ismine göre uygun görselleştirici sınıfını döndürür.
        """
        if algo_choice == "bfs":
            return algorithm.BFSVisualizer(world, screen, map.CELL_SIZE, clock)
        elif algo_choice == "dfs":
            return algorithm.DFSVisualizer(world, screen, map.CELL_SIZE, clock)
        elif algo_choice == "greedy":
             return algorithm.GreedyBestFirstVisualizer(world, screen, map.CELL_SIZE, clock) 
        else: 
            return algorithm.AStarVisualizer(world, screen, map.CELL_SIZE, clock)

    def run_search_algorithm():
        """
        Ajanın mevcut konumundan hedefe yol arar.
        Yolu hemen uygulamaz, kullanıcı onayı için bekletir.
        """
        nonlocal pending_path, active_visualizer
        
        if not destination:
            ui.state.update_log("Set Target First!", (player_agent.grid_y, player_agent.grid_x), 0, 0, None)
            return

        ui.state.status_message = "Searching..."
        algo_choice = ui.state.selected_algorithm.lower()
        
        # TODO: [DEĞİŞTİRİLDİ] Gri renkli ziyaret edilen hücreleri daha sonra çizebilmek için görselleştirici örneği saklanıyor.
        active_visualizer = get_visualizer(algo_choice)

        start = (player_agent.grid_y, player_agent.grid_x)
        try:
            path = active_visualizer.search(start, destination, speed=0.02, auto_accept=True)
            
            visited_est = len(active_visualizer.visited_edges) if hasattr(active_visualizer, 'visited_edges') else 0
            cost = len(path) if path else 0
            
            if path:
                # TODO: [DEĞİŞTİRİLDİ] Hemen hareket etme. Yolu kaydet ve onay iste.
                pending_path = path 
                ui.state.awaiting_confirmation = True 
                ui.state.update_log("Path Found! Approve?", start, cost, visited_est, None)
            else:
                ui.state.update_log("No Path Found!", start, 0, visited_est, False)
                active_visualizer = None 
                
        except Exception as e:
            print(f"Algorithm Error: {e}")
            ui.state.update_log("Algo Error", start, 0, 0, False)

    # --- Ana Döngü ---
    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

            # Paneldeki buton etkileşimlerini işle
            action = ui.handle_event(event)
            
            if action:
                if action == "CMD_START":
                    run_search_algorithm()
                
                # TODO: [DEĞİŞTİRİLDİ] GO (Onayla) Butonu İşlemleri
                elif action == "CMD_CONFIRM":
                    if pending_path:
                        player_agent.move(pending_path)
                        ui.state.status_message = "Moving..."
                        
                        # [DÜZELTME 1] Ajanın onaylandığını bilmesini sağla. 
                        # Bu, bir sonraki güncelleme döngüsünün hala onay beklediğimizi veya yeniden planlama gerektiğini sanmasını engeller.
                        player_agent.awaiting_approval = False
                        player_agent.replan_needed = False
                    
                    # Değişkenleri temizle
                    pending_path = None
                    ui.state.awaiting_confirmation = False
                    active_visualizer = None 
                    
                # TODO: [DEĞİŞTİRİLDİ] CANCEL (Reddet) Butonu İşlemleri
                elif action == "CMD_REJECT":
                    pending_path = None
                    ui.state.awaiting_confirmation = False
                    active_visualizer = None 
                    ui.state.status_message = "Cancelled"
                    
                    # Ajanı tamamen durdur
                    player_agent.stop()
                    player_agent.awaiting_approval = False
                    player_agent.replan_needed = False

                elif action == "CMD_FREEZE":
                    is_simulation_frozen = True
                    ui.state.status_message = "Time Frozen"
                elif action == "CMD_RESUME":
                    is_simulation_frozen = False
                    ui.state.status_message = "Time Resumed"
                elif action == "CMD_RESET":
                    reset_simulation_state()
                    screen.fill(map.WHITE)

            mouse_pos = pygame.mouse.get_pos()
            
            # Sadece harita alanında (sol taraf) fare etkileşimini işle
            if mouse_pos[0] < map.SCREEN_WIDTH:
                grid_col = mouse_pos[0] // map.CELL_SIZE
                grid_row = mouse_pos[1] // map.CELL_SIZE
                
                # Sol Tıklama
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    agent_rect = player_agent.rect
                    if agent_rect.collidepoint(mouse_pos):
                        dragging_agent = True
                        player_agent.stop()
                        ui.state.traffic_light_info = None
                        # Sürükleme sırasında bekleyen durumları sıfırla
                        pending_path = None
                        ui.state.awaiting_confirmation = False
                        active_visualizer = None

                    elif isinstance(world.grid[grid_row][grid_col], map.TrafficLight):
                        tile = world.grid[grid_row][grid_col]
                        state_upper = tile.state.upper()
                        ui.state.traffic_light_info = f"{state_upper}"
                        ui.state.status_message = f"Light Info: {state_upper}"

                    elif ui.state.mode == 'ADD_OBSTACLE':
                         if 0 <= grid_row < map.GRID_HEIGHT and 0 <= grid_col < map.GRID_WIDTH:
                             current_tile = world.grid[grid_row][grid_col]
                             if not isinstance(current_tile, (map.TrafficLight, map.Crosswalk)):
                                world.grid[grid_row][grid_col] = map.Grass()
                                ui.state.traffic_light_info = None

                    elif ui.state.mode == 'REMOVE_OBSTACLE':
                         if 0 <= grid_row < map.GRID_HEIGHT and 0 <= grid_col < map.GRID_WIDTH:
                             world.grid[grid_row][grid_col] = map.Road()
                             ui.state.traffic_light_info = None

                # Sol Tıklamayı Bırakma
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if dragging_agent:
                        dragging_agent = False
                        if 0 <= grid_row < map.GRID_HEIGHT and 0 <= grid_col < map.GRID_WIDTH:
                            tile = world.grid[grid_row][grid_col]
                            if isinstance(tile, (map.Road, map.Crosswalk)):
                                player_agent.set_position(grid_row, grid_col)
                                ui.state.agent_pos = (grid_row, grid_col)
                                ui.state.status_message = "Agent Moved"
                            else:
                                player_agent.set_position(player_agent.grid_y, player_agent.grid_x)
                                ui.state.status_message = "Invalid Position!"

                # Fare Hareketi
                elif event.type == pygame.MOUSEMOTION:
                    if dragging_agent:
                        player_agent.rect.center = mouse_pos

                # Sağ Tıklama (Hedef Belirleme)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                     if 0 <= grid_row < map.GRID_HEIGHT and 0 <= grid_col < map.GRID_WIDTH:
                         destination = (grid_row, grid_col)
                         ui.state.status_message = f"Target Set: {destination}"
                         # Yeni hedef belirlendiğinde bekleyen durumları sıfırla
                         pending_path = None
                         ui.state.awaiting_confirmation = False
                         active_visualizer = None

        # --- Güncelleme Mantığı (Update Logic) ---
        
        # TODO: [DEĞİŞTİRİLDİ] Koşula 'not ui.state.awaiting_confirmation' eklendi.
        # Bu, kullanıcı GO veya CANCEL tuşuna basana kadar simülasyonun güncellenmesini 
        # (ve dolayısıyla sonsuz yeniden planlama döngülerine girmesini) engeller.
        if not is_simulation_frozen and not ui.state.awaiting_confirmation:
            dt = clock.tick(map.FPS) / 1000.0
            world.update()
            for vehicle in all_vehicles:
                vehicle.update(all_vehicles)
            if pedestrians:
                pedestrians.update(dt)
            
            # --- Otomatik Yeniden Planlama Mantığı (Düzeltildi) ---
            # Ajan yeni bir yol talep ederse ve halihazırda bekleyen bir yol yoksa
            if player_agent and player_agent.awaiting_approval and not pending_path:
                ui.state.status_message = "Obstacle! Searching..."
                
                algo_choice = ui.state.selected_algorithm.lower()
                active_visualizer = get_visualizer(algo_choice) 
                
                start = (player_agent.grid_y, player_agent.grid_x)
                goal = player_agent.destination
                
                try:
                    path = active_visualizer.search(start, goal, speed=0.02, auto_accept=True)
                    
                    visited_est = len(active_visualizer.visited_edges) if hasattr(active_visualizer, 'visited_edges') else 0
                    cost = len(path) if path else 0
                    
                    if path:
                        # Alternatif bir yol bulundu: Göster ve onay bekle
                        pending_path = path 
                        ui.state.awaiting_confirmation = True 
                        ui.state.update_log("Replan Found. Approve?", start, len(path), visited_est, None)
                    else:
                        # TODO: [DEĞİŞTİRİLDİ] [DÜZELTME 2] Yol bulunamadığında oluşan sonsuz döngü düzeltildi.
                        # Ajanı durdur ve tekrar denememesi için hedefini temizle.
                        ui.state.update_log("Stuck! No Path.", start, 0, visited_est, False)
                        player_agent.stop()
                        player_agent.destination = None 
                        player_agent.awaiting_approval = False
                        player_agent.replan_needed = False
                        active_visualizer = None 
                        
                except Exception as e:
                    print(f"Algorithm Error: {e}")
                    player_agent.stop()
                    player_agent.awaiting_approval = False
        else:
            clock.tick(map.FPS) 

        # UI'daki ajan konumunu canlı güncel tut
        if player_agent.is_active:
             ui.state.agent_pos = (player_agent.grid_y, player_agent.grid_x)

        # --- Çizim Aşaması ---
        # Harita alanını (sol taraf) kırp ve temizle
        screen.set_clip(pygame.Rect(0, 0, map.SCREEN_WIDTH, map.SCREEN_HEIGHT))
        screen.fill(map.WHITE) 
        world.draw(screen)
        
        # Hedef noktayı çiz
        if destination:
            dx, dy = destination[1] * map.CELL_SIZE, destination[0] * map.CELL_SIZE
            pygame.draw.circle(screen, (255, 0, 0), (dx + map.CELL_SIZE//2, dy + map.CELL_SIZE//2), 6)

        # TODO: [DEĞİŞTİRİLDİ] Arama işlemlerini çiz (Gri hücreler - active_visualizer içinde saklı)
        if active_visualizer and active_visualizer.overlay:
            screen.blit(active_visualizer.overlay, (0, 0))

        # TODO: [DEĞİŞTİRİLDİ] Bekleyen (onaylanmamış) Yeşil yolu çiz
        if pending_path and len(pending_path) > 1:
            points = []
            for r, c in pending_path:
                cx = c * map.CELL_SIZE + map.CELL_SIZE // 2
                cy = r * map.CELL_SIZE + map.CELL_SIZE // 2
                points.append((cx, cy))
            pygame.draw.lines(screen, (0, 255, 0), False, points, 4)

        for vehicle in all_vehicles:
            vehicle.draw(screen)
        if pedestrians:
            pedestrians.draw(screen)
        
        # Paneli çizmek için kırpmayı kaldır
        screen.set_clip(None)
        
        # TODO: [DEĞİŞTİRİLDİ] Kameranın konumunu çizmesi için ajanı parametre olarak gönder
        ui.draw(screen, player_agent)
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()