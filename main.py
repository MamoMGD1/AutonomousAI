import pygame
import sys
import map  # Harita, karolar ve World sınıfı
from car import Car   # Rastgele dolaşan Car sınıfı (Sadece AI)
from agent import Agent # Oyuncu kontrollü Agent sınıfı

def main():
    """
    Ana simülasyon fonksiyonu.
    Pygame'i başlatır, dünyayı kurar, araçları oluşturur ve ana döngüyü çalıştırır.
    Oyuncu Kontrolü: Agent (agent.png)
    Yapay Zeka: Car (car.png)
    """
    # Pygame'i başlat
    pygame.init()

    # Pencere ve Ekran Ayarları (sabitleri map.py'den alır)
    try:
        screen = pygame.display.set_mode((map.SCREEN_WIDTH, map.SCREEN_HEIGHT))
        pygame.display.set_caption("Otonom Araç Simülasyonu")
        clock = pygame.time.Clock()
    except AttributeError as e:
        print(f"Hata: 'map.py' dosyasında gerekli ekran sabitleri (SCREEN_WIDTH, SCREEN_HEIGHT) bulunamadı.")
        print(f"Detay: {e}")
        return

    # Dünya (Harita) oluşturuluyor
    world = map.World(map.GRID_WIDTH, map.GRID_HEIGHT)
    
    # Araçların listesi (Hem Car hem de Agent nesnelerini tutacak)
    all_vehicles = []
    player_vehicle = None # Oyuncu aracını ayrı bir değişkende tut

    # 1. Rastgele dolaşan (AI) arabaları oluştur (car.png)
    num_cars = 20  # Simülasyondaki rastgele araba sayısı
    for _ in range(num_cars):
        all_vehicles.append(Car(world))
        
    # 2. Oyuncu Kontrollü Ajan'ı (agent.png) oluştur
    try:
        # Yolu ve dünyayı kullanarak Ajan'ı oluştur
        player_vehicle = Agent(world)
        # Ajanı da diğer araçların listesine ekle
        all_vehicles.append(player_vehicle)
    except Exception as e:
        print(f"Hata: Oyuncu Ajanı (Agent) oluşturulamadı. {e}")
        # Hata olsa bile simülasyona (sadece Car'larla) devam et
        pass

    # --- Ana Simülasyon Döngüsü ---
    running = True
    input_vector = pygame.math.Vector2(0, 0) # Oyuncu girdisini tutar

    while running:
        # Olay (Event) Yönetimi
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # --- YENİ: Oyuncu Kontrolü Olayları ---
            if player_vehicle: # Oyuncu aracı varsa
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
            # --- Oyuncu Kontrolü Sonu ---

            # map.py'den alınan fare ile tıklama (debug) özelliği
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Sol tık
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
                            state = tile.direction if tile.direction else 'Kavşak'
                        
                        print(f"[Debug] Tıklama: Pozisyon={coords}, Tip={tile_type}, Durum={state}")
                    else:
                        print(f"[Debug] Tıklama: Grid dışında.")
        
        # --- Güncelleme Aşaması ---
        
        # 1. Dünyayı güncelle (Trafik ışıklarının durumunu değiştirir)
        world.update()
        
        # 2. Oyuncu aracının girdisini işle
        if player_vehicle:
            player_vehicle.handle_input(input_vector)

        # 3. Tüm araçları (Car ve Agent) güncelle
        # Liste olarak 'all_vehicles' gönderilir, böylece araçlar birbirini görebilir.
        for vehicle in all_vehicles:
            vehicle.update(all_vehicles)
            
        # --- Çizim Aşaması ---
        
        # 1. Ekranı temizle
        screen.fill(map.GREEN) # Arka planı çim rengi yap
        
        # 2. Haritayı (yollar, binalar, ışıklar) çiz
        world.draw(screen)
        
        # 3. Tüm araçları (Car ve Agent) haritanın üzerine çiz
        for vehicle in all_vehicles:
            vehicle.draw(screen)
            
        # 4. Ekranı yenile
        pygame.display.flip()
        
        # FPS'i sabitle
        clock.tick(map.FPS)
    
    # Döngü bittiğinde Pygame'i kapat
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()