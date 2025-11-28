import pygame

# --- Sabitler ve Renkler ---
PANEL_WIDTH = 340
# Modern Koyu Tema
BG_MAIN = (30, 33, 40)
BG_CARD = (40, 44, 52)
BG_CAM = (10, 10, 15) 

TXT_MAIN = (236, 240, 241)
TXT_DIM = (160, 170, 180)

BTN_IDLE = (60, 65, 75)
BTN_HOVER = (80, 85, 95)
BTN_SHADOW = (20, 20, 25)

ACCENT_CYAN = (0, 200, 255)      
ACCENT_GREEN = (46, 204, 113)    
ACCENT_RED = (231, 76, 60)       
ACCENT_YELLOW = (241, 196, 15)   
ACCENT_PURPLE = (155, 89, 182)

# Özel Buton Renkleri (Daha Canlı)
VIVID_GREEN = (0, 230, 64)    # GO butonu için parlak yeşil
VIVID_RED = (220, 20, 60)     # CANCEL butonu için parlak kırmızı

class UIState:
    def __init__(self):
        self.algo_list = ["BFS", "DFS", "A*", "Greedy"]
        self.current_algo_index = 0
        self.selected_algorithm = self.algo_list[self.current_algo_index]
        
        self.status_message = "Ready"
        self.agent_pos = (0, 0)
        self.path_cost = 0
        self.visited_count = 0
        self.is_running = False
        self.path_found = None 
        self.mode = 'VIEW' 
        self.traffic_light_info = None
        
        # Yeni durum: Onay bekliyor muyuz?
        self.awaiting_confirmation = False

    def cycle_algorithm(self):
        self.current_algo_index = (self.current_algo_index + 1) % len(self.algo_list)
        self.selected_algorithm = self.algo_list[self.current_algo_index]
        self.status_message = f"Switched to: {self.selected_algorithm}"

    def update_log(self, status, pos, cost, visited, found):
        self.status_message = status
        self.agent_pos = pos
        self.path_cost = cost
        self.visited_count = visited
        self.path_found = found

    def add_to_history(self, algo, cost, visited, is_best): pass 
    def clear_history(self): pass

class Button:
    def __init__(self, x, y, w, h, text, action_code): 
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.action_code = action_code
        self.is_hovered = False
        self.is_active = False 

    def draw(self, surface, font, active_color=ACCENT_CYAN, override_text=None):
        shadow_rect = self.rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 3
        pygame.draw.rect(surface, BTN_SHADOW, shadow_rect, border_radius=6)

        if self.is_active:
            base_color = (max(0, active_color[0]-50), max(0, active_color[1]-50), max(0, active_color[2]-50))
            text_c = (255, 255, 255)
        elif self.is_hovered:
            base_color = BTN_HOVER
            text_c = (255, 255, 255)
        else:
            base_color = BTN_IDLE
            text_c = TXT_MAIN

        pygame.draw.rect(surface, base_color, self.rect, border_radius=6)
        
        if self.is_active:
            pygame.draw.rect(surface, active_color, self.rect, 2, border_radius=6)

        display_text = override_text if override_text else self.text
        text_surf = font.render(display_text, True, text_c)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    # Özel Çizim Fonksiyonu (GO ve CANCEL butonları için)
    def draw_special(self, surface, font, base_color, icon_type="NONE"):
        # Gölge
        shadow_rect = self.rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 3
        pygame.draw.rect(surface, (20, 20, 20), shadow_rect, border_radius=8)

        # Hover efekti (Rengi biraz aç)
        if self.is_hovered:
            draw_color = (min(base_color[0]+30, 255), min(base_color[1]+30, 255), min(base_color[2]+30, 255))
        else:
            draw_color = base_color

        # Ana Buton Gövdesi
        pygame.draw.rect(surface, draw_color, self.rect, border_radius=8)
        
        # Beyaz Çerçeve (Vurgu)
        pygame.draw.rect(surface, (255, 255, 255), self.rect, 2, border_radius=8)

        # Simge ve Metin Çizimi
        center_x, center_y = self.rect.centerx, self.rect.centery
        
        if icon_type == "CHECK":
            # "Tik" işareti (Checkmark) çizimi
            points = [
                (center_x - 30, center_y),
                (center_x - 20, center_y + 10),
                (center_x - 5, center_y - 15)
            ]
            pygame.draw.lines(surface, (255, 255, 255), False, points, 3)
            
            # Metni sağa kaydır
            text_surf = font.render(self.text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(midleft=(center_x + 5, center_y))
            surface.blit(text_surf, text_rect)

        elif icon_type == "CROSS":
            # "Çarpı" işareti (X) çizimi
            start_x, start_y = center_x - 35, center_y
            # X sol çizgi
            pygame.draw.line(surface, (255, 255, 255), (start_x, start_y - 8), (start_x + 16, start_y + 8), 3)
            # X sağ çizgi
            pygame.draw.line(surface, (255, 255, 255), (start_x + 16, start_y - 8), (start_x, start_y + 8), 3)
            
            # Metni sağa kaydır
            text_surf = font.render(self.text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(midleft=(center_x - 10, center_y))
            surface.blit(text_surf, text_rect)
            
        else:
            # Normal metin çizimi
            text_surf = font.render(self.text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=self.rect.center)
            surface.blit(text_surf, text_rect)

    def check_hover(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)

class Interface:
    def __init__(self, screen_width, screen_height):
        self.width = PANEL_WIDTH
        self.height = screen_height
        self.x_offset = screen_width
        self.state = UIState()
        
        self.font_header = pygame.font.SysFont("Arial", 20, bold=True)
        self.font_btn = pygame.font.SysFont("Arial", 14, bold=True)
        self.font_log = pygame.font.SysFont("Consolas", 12)
        self.font_label = pygame.font.SysFont("Arial", 11)
        self.font_cam = pygame.font.SysFont("Consolas", 12, bold=True)

        # Buton Listeleri
        self.static_buttons = []
        self.btn_start = None
        self.btn_go = None
        self.btn_cancel = None
        
        self.last_button_y = 0 
        self._init_buttons()

    def _init_buttons(self):
        bx = self.x_offset + 20
        bw = self.width - 40
        bh = 38 
        
        y = 175 
        gap = 45 

        # 1. Algoritma Değiştirici
        self.static_buttons.append(Button(bx, y, bw, bh, "ALGO_SWITCHER", "CMD_CYCLE_ALGO"))
        y += gap

        # 2. Dinamik Alan (Başlat VEYA Git/İptal)
        self.btn_start = Button(bx, y, bw, 42, "START SEARCH", "CMD_START")
        
        # Onay ve Red butonları (genişliği paylaşır)
        half_w = (bw - 10) // 2
        self.btn_go = Button(bx, y, half_w, 42, "GO", "CMD_CONFIRM") # Text shortened for icon space
        self.btn_cancel = Button(bx + half_w + 10, y, half_w, 42, "CANCEL", "CMD_REJECT")
        
        y += gap + 5

        # 3. Kontroller
        self.static_buttons.append(Button(bx, y, half_w, bh, "FREEZE", "CMD_FREEZE"))
        self.static_buttons.append(Button(bx + half_w + 10, y, half_w, bh, "RESUME", "CMD_RESUME"))
        y += gap

        # 4. Sıfırla
        self.static_buttons.append(Button(bx, y, bw, bh, "RESET SYSTEM", "CMD_RESET"))
        y += gap

        # 5. Araçlar
        self.static_buttons.append(Button(bx, y, half_w, bh, "Add Obstacle", "MODE_ADD"))
        self.static_buttons.append(Button(bx + half_w + 10, y, half_w, bh, "Del Obstacle", "MODE_DEL"))
        
        self.last_button_y = y + bh

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            for btn in self.static_buttons:
                btn.check_hover(event.pos)
            
            # Dinamik butonları kontrol et
            if self.state.awaiting_confirmation:
                self.btn_go.check_hover(event.pos)
                self.btn_cancel.check_hover(event.pos)
            else:
                self.btn_start.check_hover(event.pos)
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self.static_buttons:
                if btn.is_clicked(event.pos):
                    return self._process_action(btn.action_code)
            
            if self.state.awaiting_confirmation:
                if self.btn_go.is_clicked(event.pos): return "CMD_CONFIRM"
                if self.btn_cancel.is_clicked(event.pos): return "CMD_REJECT"
            else:
                if self.btn_start.is_clicked(event.pos):
                    return self._process_action("CMD_START")
        return None

    def _process_action(self, code):
        if code == "CMD_CYCLE_ALGO":
            self.state.cycle_algorithm()
        elif code == "MODE_ADD":
            self.state.mode = 'ADD_OBSTACLE'
            self.state.status_message = "Mode: Add Obstacles"
        elif code == "MODE_DEL":
            self.state.mode = 'REMOVE_OBSTACLE'
            self.state.status_message = "Mode: Remove Obstacles"
        return code

    def draw(self, screen, agent=None):
        # 1. Arka Plan
        panel_rect = pygame.Rect(self.x_offset, 0, self.width, self.height)
        pygame.draw.rect(screen, BG_MAIN, panel_rect)
        pygame.draw.line(screen, (20, 20, 20), (self.x_offset, 0), (self.x_offset, self.height), 2)

        # 2. Başlık
        title = self.font_header.render("CONTROL PANEL", True, TXT_MAIN)
        screen.blit(title, (self.x_offset + 20, 15))
        pygame.draw.rect(screen, ACCENT_CYAN, (self.x_offset + 20, 40, 40, 3))

        # 3. Durum Kartı
        self._draw_status_card(screen)

        # 4. Butonlar
        # Sabit butonları çiz
        for btn in self.static_buttons:
            btn.is_active = False
            active_col = ACCENT_CYAN
            
            if btn.action_code == "CMD_CYCLE_ALGO":
                btn.is_active = True
                btn.draw(screen, self.font_btn, ACCENT_PURPLE, override_text=f"Selected Algorithm: {self.state.selected_algorithm}")
                continue

            if self.state.mode == 'ADD_OBSTACLE' and btn.action_code == "MODE_ADD": 
                btn.is_active = True; active_col = ACCENT_RED
            if self.state.mode == 'REMOVE_OBSTACLE' and btn.action_code == "MODE_DEL": 
                btn.is_active = True; active_col = ACCENT_RED

            btn.draw(screen, self.font_btn, active_col)

        # Dinamik butonları çiz (Başlat vs Git/İptal)
        if self.state.awaiting_confirmation:
            # Bekleme durumu: Özelleştirilmiş GO ve CANCEL butonları
            # GO butonu (Check işareti ile)
            self.btn_go.draw_special(screen, self.font_btn, VIVID_GREEN, icon_type="CHECK")
            # CANCEL butonu (X işareti ile)
            self.btn_cancel.draw_special(screen, self.font_btn, VIVID_RED, icon_type="CROSS")
        else:
            # Normal durum: Başlat butonu
            if self.btn_start.is_hovered:
                self.btn_start.draw(screen, self.font_btn, ACCENT_GREEN)
            else:
                # Özel Başlat Görünümü
                shadow = self.btn_start.rect.copy(); shadow.x+=2; shadow.y+=3
                pygame.draw.rect(screen, BTN_SHADOW, shadow, border_radius=6)
                pygame.draw.rect(screen, (30, 100, 60), self.btn_start.rect, border_radius=6)
                pygame.draw.rect(screen, ACCENT_GREEN, self.btn_start.rect, 2, border_radius=6)
                txt = self.font_btn.render(self.btn_start.text, True, (255,255,255))
                screen.blit(txt, txt.get_rect(center=self.btn_start.rect.center))

        # 5. Takip Kamerası
        cam_y = self.last_button_y + 25
        self._draw_tracking_camera(screen, agent, cam_y)

    def _draw_tracking_camera(self, screen, agent, start_y):
        available_height = self.height - start_y - 20
        cam_h = max(150, available_height)
        cam_w = self.width - 40
        cam_rect = pygame.Rect(self.x_offset + 20, start_y, cam_w, cam_h)

        pygame.draw.rect(screen, BG_CAM, cam_rect)
        pygame.draw.rect(screen, ACCENT_CYAN, cam_rect, 2)

        if agent:
            zoom_factor = 2.0
            crop_w = int(cam_w / zoom_factor)
            crop_h = int(cam_h / zoom_factor)
            
            ax, ay = agent.rect.centerx, agent.rect.centery
            crop_x = ax - crop_w // 2
            crop_y = ay - crop_h // 2
            
            map_width = self.x_offset
            crop_x = max(0, min(crop_x, map_width - crop_w))
            crop_y = max(0, min(crop_y, self.height - crop_h))
            
            crop_rect = pygame.Rect(crop_x, crop_y, crop_w, crop_h)
            
            try:
                subsurf = screen.subsurface(crop_rect).copy()
                zoomed_surf = pygame.transform.smoothscale(subsurf, (cam_w, cam_h))
                screen.blit(zoomed_surf, cam_rect.topleft)
            except Exception:
                pass

            rec_color = ACCENT_RED if (pygame.time.get_ticks() // 500) % 2 == 0 else (100, 0, 0)
            pygame.draw.circle(screen, rec_color, (cam_rect.right - 20, cam_rect.top + 20), 6)
            rec_txt = self.font_cam.render("LIVE ZOOM x2", True, TXT_MAIN)
            screen.blit(rec_txt, (cam_rect.right - 110, cam_rect.top + 12))

            cx, cy = cam_rect.center
            pygame.draw.line(screen, ACCENT_CYAN, (cx - 15, cy), (cx + 15, cy), 1)
            pygame.draw.line(screen, ACCENT_CYAN, (cx, cy - 15), (cx, cy + 15), 1)
            
            coord_txt = self.font_cam.render(f"POS: {self.state.agent_pos}", True, ACCENT_RED)
            screen.blit(coord_txt, (cam_rect.left + 8, cam_rect.bottom - 20))

        else:
            txt = self.font_btn.render("NO SIGNAL", True, TXT_DIM)
            screen.blit(txt, txt.get_rect(center=cam_rect.center))

    def _draw_status_card(self, screen):
        card_rect = pygame.Rect(self.x_offset + 20, 50, self.width - 40, 115)
        pygame.draw.rect(screen, BG_CARD, card_rect, border_radius=10)
        pygame.draw.rect(screen, (60, 65, 75), card_rect, 1, border_radius=10)

        infos = [
            ("STATUS", self.state.status_message),
            ("ALGORITHM", self.state.selected_algorithm),
            ("POSITION", str(self.state.agent_pos)),
            ("COST", str(self.state.path_cost))
        ]
        
        last_label = "VISITED"
        last_val = str(self.state.visited_count)
        
        if self.state.traffic_light_info:
            last_label = "LIGHT"
            last_val = self.state.traffic_light_info
        elif self.state.path_found is True:
            last_label = "RESULT"
            last_val = "REACHED!"
        elif self.state.path_found is False:
            last_label = "RESULT"
            last_val = "NO PATH"

        # Column positions: adjust value_col_x to decrease/increase space between label and value
        label_x = self.x_offset + 30
        value_col_x = label_x + 140  # <-- reduce this to bring values closer, increase to push them right
        start_y = 60

        for i, (label, val) in enumerate(infos):
            lbl_surf = self.font_label.render(label, True, TXT_DIM)
            screen.blit(lbl_surf, (label_x, start_y))
            
            val_col = TXT_MAIN
            if "Reached" in str(val): val_col = ACCENT_GREEN
            if "No Path" in str(val): val_col = ACCENT_RED
            if "Frozen" in str(val): val_col = ACCENT_CYAN
            if "Waiting" in str(val) or "Approve?" in str(val): val_col = ACCENT_YELLOW
            
            val_str = str(val)
            # Allow longer visible text before truncating
            if len(val_str) > 28:
                val_str = val_str[:26] + ".."
            
            val_surf = self.font_log.render(val_str, True, val_col)
            val_rect = val_surf.get_rect(topleft=(value_col_x, start_y))
            screen.blit(val_surf, val_rect)
            
            start_y += 20

        lbl_surf = self.font_label.render(last_label, True, TXT_DIM)
        screen.blit(lbl_surf, (label_x, start_y + 4))
        
        val_col = TXT_MAIN
        if "REACHED" in last_val: val_col = ACCENT_GREEN
        elif "NO PATH" in last_val: val_col = ACCENT_RED
        elif "RED" in last_val: val_col = ACCENT_RED
        elif "GREEN" in last_val: val_col = ACCENT_GREEN
        elif "YELLOW" in last_val: val_col = ACCENT_YELLOW

        # Place final value in the same value column
        val_surf = self.font_btn.render(last_val, True, val_col)
        val_rect = val_surf.get_rect(topleft=(value_col_x, start_y + 4))
        screen.blit(val_surf, val_rect)