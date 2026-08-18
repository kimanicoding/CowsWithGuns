import sys
import random
import math
import pygame

# --- Pygame Initialization ---
pygame.init()
pygame.font.init()

CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 720
screen = pygame.display.set_mode((CANVAS_WIDTH, CANVAS_HEIGHT))
pygame.display.set_caption("Cows With Guns 🐄")
clock = pygame.time.Clock()

# --- Colors ---
COLOR_BG_DARK = (26, 26, 26)
COLOR_TEXT_YELLOW = (255, 204, 0)
COLOR_BTN_RED = (211, 47, 47)
COLOR_BTN_HOVER = (255, 68, 68)
COLOR_PANEL = (40, 30, 20)
COLOR_PANEL_BORDER = (139, 69, 19)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)

# --- Fonts ---
font_title = pygame.font.SysFont("Segoe UI", 64, bold=True)
font_h2 = pygame.font.SysFont("Segoe UI", 32, bold=True)
font_btn = pygame.font.SysFont("Segoe UI", 22, bold=True)
font_hud = pygame.font.SysFont("Segoe UI", 24, bold=True)
font_countdown = pygame.font.SysFont("Segoe UI", 120, bold=True)

# --- Fallback Sprite Creator ---
def create_fallback_cow(color, is_left=False):
    surf = pygame.Surface((60, 70), pygame.SRCALPHA)
    # Body
    pygame.draw.rect(surf, color, (10, 20, 40, 45), border_radius=6)
    # Spot
    pygame.draw.circle(surf, (50, 50, 50), (30, 35), 8)
    # Head
    head_x = 5 if is_left else 25
    pygame.draw.rect(surf, color, (head_x, 5, 30, 25), border_radius=4)
    # Snout
    snout_x = head_x - 5 if is_left else head_x + 20
    pygame.draw.rect(surf, (255, 180, 180), (snout_x, 15, 15, 12), border_radius=3)
    # Gun
    gun_x = head_x - 15 if is_left else head_x + 15
    pygame.draw.rect(surf, (60, 60, 60), (gun_x, 22, 25, 8))
    return surf

def create_fallback_bg():
    surf = pygame.Surface((CANVAS_WIDTH, CANVAS_HEIGHT))
    surf.fill((30, 30, 35))
    for i in range(0, CANVAS_WIDTH, 120):
        pygame.draw.line(surf, (45, 45, 50), (i, 0), (i, CANVAS_HEIGHT), 4)
    for j in range(0, CANVAS_HEIGHT, 100):
        pygame.draw.line(surf, (45, 45, 50), (0, j), (CANVAS_WIDTH, j), 4)
    return surf

def load_image(filename, scale_size, fallback_type=None):
    try:
        img = pygame.image.load(filename).convert_alpha()
        return pygame.transform.scale(img, scale_size)
    except Exception:
        if fallback_type == 'p1r':
            return create_fallback_cow((240, 240, 240), is_left=False)
        elif fallback_type == 'p1l':
            return create_fallback_cow((240, 240, 240), is_left=True)
        elif fallback_type == 'p2r':
            return create_fallback_cow((230, 180, 180), is_left=False)
        elif fallback_type == 'p2l':
            return create_fallback_cow((230, 180, 180), is_left=True)
        elif fallback_type == 'bg':
            return create_fallback_bg()
        surf = pygame.Surface(scale_size)
        surf.fill((120, 120, 120))
        return surf

# FIXED: Corrected file extensions to match p1l.png, p2l.png, and bg.png
bg_img = load_image('bg.png', (CANVAS_WIDTH, CANVAS_HEIGHT), 'bg')
p1r_img = load_image('p1r.png', (60, 70), 'p1r')
p1l_img = load_image('p1l.png', (60, 70), 'p1l')
p2r_img = load_image('p2r.png', (60, 70), 'p2r')
p2l_img = load_image('p2l.png', (60, 70), 'p2l')

# --- Game Configuration ---
WEAPONS = {
    'sniper': {'name': 'Sniper', 'damage': 5, 'cooldown': 50, 'speed': 22},
    'ar': {'name': 'Assault Rifle', 'damage': 2, 'cooldown': 14, 'speed': 14},
    'smg': {'name': 'SMG', 'damage': 1, 'cooldown': 6, 'speed': 13},
    'lmg': {'name': 'LMG', 'damage': 1.5, 'cooldown': 10, 'speed': 15, 'movementPenalty': 0.4},
    'shotgun': {'name': 'Shotgun', 'damage': 3, 'cooldown': 40, 'speed': 12, 'pellets': 3, 'spread': 0.12}
}

STATES = {'MAIN_MENU': 0, 'ARENA_MENU': 1, 'COUNTDOWN': 2, 'PLAYING': 3, 'VICTORY': 4}
current_state = STATES['MAIN_MENU']
is_bot_mode = False

selections = {
    'p1': {'weapon': None, 'ready': False},
    'p2': {'weapon': None, 'ready': False}
}

class Player:
    def __init__(self, x, y, is_player_1, is_bot=False):
        self.x = x
        self.y = y
        self.width = 60
        self.height = 70
        self.vx = 0
        self.vy = 0
        self.speed = 5
        self.jump_force = -12.5
        self.gravity = 0.55
        self.is_grounded = False
        self.is_player_1 = is_player_1
        self.is_bot = is_bot
        
        self.max_jumps = 2
        self.jumps_left = 2
        self.prev_jump_key = False

        self.max_hp = 10
        self.hp = 10
        self.facing = 'right' if is_player_1 else 'left'
        
        weapon_key = selections['p1']['weapon'] if is_player_1 else selections['p2']['weapon']
        self.weapon = WEAPONS.get(weapon_key, WEAPONS['ar'])
        self.cooldown_timer = 0
        self.hit_flash_timer = 0

        self.bot_jump_cooldown = 0
        self.bot_stuck_timer = 0
        self.last_x = x
        self.wander_direction = 1 if random.random() > 0.5 else -1
        self.wander_timer = 0

    def update(self, keys, platforms, opponent):
        move_left = False
        move_right = False
        jump = False
        shoot = False
        current_speed = self.speed

        if self.is_bot:
            target = opponent
            dx = target.x - self.x
            dy = target.y - self.y
            preferred_distance = 280

            if abs(dx) > preferred_distance + 30:
                if dx < 0: move_left = True
                else: move_right = True
            elif abs(dx) < preferred_distance - 30:
                if dx < 0: move_right = True
                else: move_left = True
            else:
                self.facing = 'left' if dx < 0 else 'right'

            if abs(dx) > 30:
                self.facing = 'left' if dx < 0 else 'right'

            if dy > 60:
                if self.wander_timer <= 0:
                    self.wander_direction = 1 if random.random() > 0.5 else -1
                    self.wander_timer = 30 + random.random() * 30
                if self.wander_direction == 1: move_right = True
                else: move_left = True
                self.wander_timer -= 1

            if (move_left or move_right) and abs(self.x - self.last_x) < 0.5:
                self.bot_stuck_timer += 1
            else:
                self.bot_stuck_timer = 0
            self.last_x = self.x

            if self.bot_jump_cooldown > 0: 
                self.bot_jump_cooldown -= 1
            
            if self.bot_jump_cooldown <= 0 and self.jumps_left > 0:
                should_jump = False
                if self.is_grounded and (dy < -40 or self.bot_stuck_timer > 15 or random.random() < 0.01):
                    should_jump = True
                elif not self.is_grounded and dy < -80 and self.vy > -2:
                    should_jump = True

                if should_jump:
                    jump = True
                    self.bot_jump_cooldown = 15 + random.random() * 25

            is_facing_target = (math.copysign(1, dx) == (1 if self.facing == 'right' else -1)) or abs(dx) < 30
            if abs(dy) < 180 and is_facing_target:
                if random.random() < 0.85:
                    shoot = True

            if self.weapon == WEAPONS['lmg'] and shoot:
                current_speed *= (1 - WEAPONS['lmg']['movementPenalty'])
        else:
            is_firing = keys[pygame.K_c] if self.is_player_1 else (keys[pygame.K_k] or keys[pygame.K_c])
            if self.weapon == WEAPONS['lmg'] and is_firing:
                current_speed *= (1 - WEAPONS['lmg']['movementPenalty'])

            if self.is_player_1:
                move_left = keys[pygame.K_a]
                move_right = keys[pygame.K_d]
                jump = keys[pygame.K_w]
                shoot = keys[pygame.K_c]
            else:
                move_left = keys[pygame.K_LEFT] or (is_bot_mode and keys[pygame.K_a])
                move_right = keys[pygame.K_RIGHT] or (is_bot_mode and keys[pygame.K_d])
                jump = keys[pygame.K_UP] or (is_bot_mode and keys[pygame.K_w])
                shoot = keys[pygame.K_k] or (is_bot_mode and keys[pygame.K_c])

        if move_left:
            self.vx = -current_speed
            self.facing = 'left'
        elif move_right:
            self.vx = current_speed
            self.facing = 'right'
        else:
            self.vx *= 0.8

        jump_pressed = jump and not self.prev_jump_key
        self.prev_jump_key = jump

        if jump_pressed and self.jumps_left > 0:
            self.vy = self.jump_force
            self.is_grounded = False
            self.jumps_left -= 1

        self.vy += self.gravity

        self.x += self.vx
        self.resolve_x_collisions(platforms)

        self.y += self.vy
        self.is_grounded = False
        self.resolve_y_collisions(platforms)

        if self.x < 0: self.x = 0
        if self.x + self.width > CANVAS_WIDTH: self.x = CANVAS_WIDTH - self.width
        if self.y > CANVAS_HEIGHT + 200:
            self.hp = 0

        if self.cooldown_timer > 0:
            self.cooldown_timer -= 1

        if shoot and self.cooldown_timer == 0:
            self.fire_weapon()

        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= 1

    def fire_weapon(self):
        self.cooldown_timer = self.weapon['cooldown']
        spawn_x = self.x + self.width + 5 if self.facing == 'right' else self.x - 15
        spawn_y = self.y + self.height / 2 - 5
        dir_mult = 1 if self.facing == 'right' else -1

        if self.weapon == WEAPONS['shotgun']:
            for i in range(self.weapon['pellets']):
                angle_spread = (i - 1) * self.weapon['spread']
                projectiles.append(Projectile(spawn_x, spawn_y, dir_mult * self.weapon['speed'], angle_spread * self.weapon['speed'], self.weapon['damage'], self.is_player_1))
        else:
            projectiles.append(Projectile(spawn_x, spawn_y, dir_mult * self.weapon['speed'], 0, self.weapon['damage'], self.is_player_1))

    def resolve_x_collisions(self, platforms):
        rect = pygame.Rect(self.x, self.y, self.width, self.height)
        for p in platforms:
            if rect.colliderect(p):
                if self.vx > 0:
                    self.x = p.x - self.width
                elif self.vx < 0:
                    self.x = p.x + p.width
                rect.x = self.x

    def resolve_y_collisions(self, platforms):
        rect = pygame.Rect(self.x, self.y, self.width, self.height)
        for p in platforms:
            if rect.colliderect(p):
                if self.vy > 0:
                    self.y = p.y - self.height
                    self.vy = 0
                    self.is_grounded = True
                    self.jumps_left = self.max_jumps
                elif self.vy < 0:
                    self.y = p.y + p.height
                    self.vy = 0
                rect.y = self.y

    def draw(self, surf):
        if self.is_player_1:
            sprite = p1r_img if self.facing == 'right' else p1l_img
        else:
            sprite = p2r_img if self.facing == 'right' else p2l_img

        if self.hit_flash_timer > 0 and (self.hit_flash_timer // 3) % 2 == 0:
            flash_surf = sprite.copy()
            flash_surf.fill((255, 100, 100, 180), special_flags=pygame.BLEND_RGBA_ADD)
            surf.blit(flash_surf, (self.x, self.y))
        else:
            surf.blit(sprite, (self.x, self.y))

        bar_width = 60
        bar_height = 8
        bar_x = self.x + (self.width - bar_width) / 2
        bar_y = self.y - 18

        pygame.draw.rect(surf, (0, 0, 0, 128), (bar_x, bar_y, bar_width, bar_height))
        hp_ratio = max(0, self.hp) / self.max_hp
        pygame.draw.rect(surf, (46, 204, 113), (bar_x, bar_y, bar_width * hp_ratio, bar_height))
        pygame.draw.rect(surf, (0, 0, 0), (bar_x, bar_y, bar_width, bar_height), 1)

class Projectile:
    def __init__(self, x, y, vx, vy, damage, is_player_1_source):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.is_player_1_source = is_player_1_source
        self.radius = 5

    def update(self):
        self.x += self.vx
        self.y += self.vy

    def draw(self, surf):
        color = (255, 204, 0) if self.is_player_1_source else (0, 255, 255)
        pygame.draw.circle(surf, color, (int(self.x), int(self.y)), self.radius)

# Global Entities
player1 = None
player2 = None
platforms = []
projectiles = []

# UI Rect Definitions
btn_2p_rect = pygame.Rect(CANVAS_WIDTH // 2 - 160, 340, 320, 60)
btn_bot_rect = pygame.Rect(CANVAS_WIDTH // 2 - 160, 420, 320, 60)
btn_back_rect = pygame.Rect(CANVAS_WIDTH // 2 - 270, 560, 240, 60)
btn_start_rect = pygame.Rect(CANVAS_WIDTH // 2 + 30, 560, 240, 60)
btn_restart_rect = pygame.Rect(CANVAS_WIDTH // 2 - 270, 380, 240, 60)
btn_menu_rect = pygame.Rect(CANVAS_WIDTH // 2 + 30, 380, 240, 60)

p1_weapon_rects = []
p2_weapon_rects = []

def init_game():
    global player1, player2, platforms, projectiles
    platforms = [
        pygame.Rect(0, 640, CANVAS_WIDTH, 80),
        pygame.Rect(200, 540, 120, 100),
        pygame.Rect(960, 540, 120, 100),
        pygame.Rect(180, 430, 280, 20),
        pygame.Rect(820, 430, 280, 20),
        pygame.Rect(440, 300, 400, 20),
        pygame.Rect(180, 170, 280, 20),
        pygame.Rect(820, 170, 280, 20)
    ]
    player1 = Player(80, 570, True, is_bot_mode)
    player2 = Player(1140, 570, False, False)
    projectiles = []

countdown_val = 3
countdown_timer_event = pygame.USEREVENT + 1
winner_message = ""

def start_countdown():
    global current_state, countdown_val
    init_game()
    current_state = STATES['COUNTDOWN']
    countdown_val = 3
    pygame.time.set_timer(countdown_timer_event, 1000)

def draw_button(surf, rect, text, is_hovered, bg_color=COLOR_BTN_RED):
    color = COLOR_BTN_HOVER if is_hovered else bg_color
    pygame.draw.rect(surf, color, rect, border_radius=8)
    pygame.draw.rect(surf, COLOR_WHITE, rect, 2, border_radius=8)
    txt_surf = font_btn.render(text, True, COLOR_WHITE)
    txt_rect = txt_surf.get_rect(center=rect.center)
    surf.blit(txt_surf, txt_rect)

# --- Main Game Loop ---
def main():
    global current_state, is_bot_mode, winner_message, countdown_val

    while True:
        mouse_pos = pygame.mouse.get_pos()
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if current_state == STATES['MAIN_MENU']:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if btn_2p_rect.collidepoint(event.pos):
                        is_bot_mode = False
                        current_state = STATES['ARENA_MENU']
                        selections['p1'] = {'weapon': None, 'ready': False}
                        selections['p2'] = {'weapon': None, 'ready': False}
                    elif btn_bot_rect.collidepoint(event.pos):
                        is_bot_mode = True
                        current_state = STATES['ARENA_MENU']
                        random_w = random.choice(list(WEAPONS.keys()))
                        selections['p1'] = {'weapon': random_w, 'ready': True}
                        selections['p2'] = {'weapon': None, 'ready': False}

            elif current_state == STATES['ARENA_MENU']:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if btn_back_rect.collidepoint(event.pos):
                        current_state = STATES['MAIN_MENU']
                    elif selections['p1']['ready'] and selections['p2']['ready'] and btn_start_rect.collidepoint(event.pos):
                        start_countdown()
                    else:
                        for idx, w_key in enumerate(WEAPONS.keys()):
                            if idx < len(p2_weapon_rects) and p2_weapon_rects[idx].collidepoint(event.pos):
                                selections['p2']['weapon'] = w_key
                                selections['p2']['ready'] = True
                            if not is_bot_mode and idx < len(p1_weapon_rects) and p1_weapon_rects[idx].collidepoint(event.pos):
                                selections['p1']['weapon'] = w_key
                                selections['p1']['ready'] = True

            elif current_state == STATES['COUNTDOWN']:
                if event.type == countdown_timer_event:
                    countdown_val -= 1
                    if countdown_val < 0:
                        pygame.time.set_timer(countdown_timer_event, 0)
                        current_state = STATES['PLAYING']

            elif current_state == STATES['VICTORY']:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if btn_restart_rect.collidepoint(event.pos):
                        if is_bot_mode:
                            selections['p1']['weapon'] = random.choice(list(WEAPONS.keys()))
                        start_countdown()
                    elif btn_menu_rect.collidepoint(event.pos):
                        current_state = STATES['MAIN_MENU']

        # --- Game Logic ---
        if current_state == STATES['PLAYING']:
            player1.update(keys, platforms, player2)
            player2.update(keys, platforms, player1)

            for i in range(len(projectiles) - 1, -1, -1):
                p = projectiles[i]
                p.update()

                if p.x < 0 or p.x > CANVAS_WIDTH or p.y < 0 or p.y > CANVAS_HEIGHT:
                    projectiles.pop(i)
                    continue

                hit_plat = False
                for plat in platforms:
                    if plat.collidepoint(p.x, p.y):
                        hit_plat = True
                        break
                if hit_plat:
                    projectiles.pop(i)
                    continue

                target = player2 if p.is_player_1_source else player1
                target_rect = pygame.Rect(target.x, target.y, target.width, target.height)
                if target_rect.collidepoint(p.x, p.y):
                    target.hp -= p.damage
                    target.hit_flash_timer = 15
                    target.vx += (4 if p.is_player_1_source else -4)
                    target.vy -= 2
                    projectiles.pop(i)

                    if target.hp <= 0:
                        current_state = STATES['VICTORY']
                        if is_bot_mode:
                            winner_message = "Bot Wins!" if p.is_player_1_source else "Player Wins!"
                        else:
                            winner_message = "Player 1 Wins!" if p.is_player_1_source else "Player 2 Wins!"

        # --- Rendering ---
        screen.blit(bg_img, (0, 0))

        if current_state in [STATES['COUNTDOWN'], STATES['PLAYING'], STATES['VICTORY']]:
            for plat in platforms:
                pygame.draw.rect(screen, (58, 61, 64), plat)
                pygame.draw.rect(screen, (122, 126, 133), (plat.x, plat.y, plat.width, 6))
                pygame.draw.rect(screen, (34, 37, 42), plat, 2)

            for p in projectiles:
                p.draw(screen)

            if player1: player1.draw(screen)
            if player2: player2.draw(screen)

            p1_name = "BOT" if is_bot_mode else "P1"
            p2_name = "PLAYER" if is_bot_mode else "P2"
            p1_text = font_hud.render(f"{p1_name} HP: {max(0, math.ceil(player1.hp))} / 10", True, COLOR_WHITE)
            p2_text = font_hud.render(f"{p2_name} HP: {max(0, math.ceil(player2.hp))} / 10", True, COLOR_WHITE)
            
            screen.blit(p1_text, (40, 20))
            screen.blit(p2_text, (CANVAS_WIDTH - p2_text.get_width() - 40, 20))

        # --- Menu Overlays ---
        if current_state == STATES['MAIN_MENU']:
            overlay = pygame.Surface((CANVAS_WIDTH, CANVAS_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 10, 15, 215))
            screen.blit(overlay, (0, 0))

            title_surf = font_title.render("Cows with Guns", True, COLOR_TEXT_YELLOW)
            screen.blit(title_surf, (CANVAS_WIDTH // 2 - title_surf.get_width() // 2, 200))

            draw_button(screen, btn_2p_rect, "2 Player 1v1", btn_2p_rect.collidepoint(mouse_pos))
            draw_button(screen, btn_bot_rect, "VS Bot", btn_bot_rect.collidepoint(mouse_pos))

        elif current_state == STATES['ARENA_MENU']:
            overlay = pygame.Surface((CANVAS_WIDTH, CANVAS_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 10, 15, 215))
            screen.blit(overlay, (0, 0))

            title_surf = font_h2.render("Cows with Guns", True, COLOR_TEXT_YELLOW)
            screen.blit(title_surf, (CANVAS_WIDTH // 2 - title_surf.get_width() // 2, 40))

            panel_w, panel_h = 450, 420
            p1_panel_rect = pygame.Rect(140, 100, panel_w, panel_h)
            p2_panel_rect = pygame.Rect(690, 100, panel_w, panel_h)

            for p_rect, title_text in [(p1_panel_rect, "Bot AI" if is_bot_mode else "Player 1 (WASD + C)"), 
                                       (p2_panel_rect, "Player 2 (Arrows + K)")]:
                pygame.draw.rect(screen, COLOR_PANEL, p_rect, border_radius=12)
                pygame.draw.rect(screen, COLOR_PANEL_BORDER, p_rect, 4, border_radius=12)
                t_surf = font_h2.render(title_text, True, COLOR_WHITE)
                screen.blit(t_surf, (p_rect.x + 20, p_rect.y + 20))

            p1_weapon_rects.clear()
            p2_weapon_rects.clear()
            weapons_list = list(WEAPONS.items())

            for i, (w_key, w_data) in enumerate(weapons_list):
                y_offset = 75 + i * 55
                
                w_rect_p1 = pygame.Rect(p1_panel_rect.x + 20, p1_panel_rect.y + y_offset, 410, 45)
                p1_weapon_rects.append(w_rect_p1)
                p1_selected = (selections['p1']['weapon'] == w_key)
                p1_col = (46, 139, 87) if p1_selected else (92, 64, 51)
                pygame.draw.rect(screen, p1_col, w_rect_p1, border_radius=6)
                pygame.draw.rect(screen, (160, 82, 45), w_rect_p1, 2, border_radius=6)
                txt = font_btn.render(f"{w_data['name']} (Dmg: {w_data['damage']})", True, COLOR_WHITE)
                screen.blit(txt, (w_rect_p1.x + 15, w_rect_p1.y + 10))

                w_rect_p2 = pygame.Rect(p2_panel_rect.x + 20, p2_panel_rect.y + y_offset, 410, 45)
                p2_weapon_rects.append(w_rect_p2)
                p2_selected = (selections['p2']['weapon'] == w_key)
                p2_col = (46, 139, 87) if p2_selected else (92, 64, 51)
                pygame.draw.rect(screen, p2_col, w_rect_p2, border_radius=6)
                pygame.draw.rect(screen, (160, 82, 45), w_rect_p2, 2, border_radius=6)
                txt2 = font_btn.render(f"{w_data['name']} (Dmg: {w_data['damage']})", True, COLOR_WHITE)
                screen.blit(txt2, (w_rect_p2.x + 15, w_rect_p2.y + 10))

            p1_status_rect = pygame.Rect(p1_panel_rect.x + 20, p1_panel_rect.y + 360, 410, 40)
            p1_ready = selections['p1']['ready']
            pygame.draw.rect(screen, (92, 184, 92) if p1_ready else (217, 83, 79), p1_status_rect, border_radius=4)
            p1_stat_txt = font_btn.render("Bot Ready!" if is_bot_mode and p1_ready else ("Ready!" if p1_ready else "Choose Weapon"), True, COLOR_WHITE)
            screen.blit(p1_stat_txt, (p1_status_rect.centerx - p1_stat_txt.get_width()//2, p1_status_rect.y + 8))

            p2_status_rect = pygame.Rect(p2_panel_rect.x + 20, p2_panel_rect.y + 360, 410, 40)
            p2_ready = selections['p2']['ready']
            pygame.draw.rect(screen, (92, 184, 92) if p2_ready else (217, 83, 79), p2_status_rect, border_radius=4)
            p2_stat_txt = font_btn.render("Ready!" if p2_ready else "Choose Weapon", True, COLOR_WHITE)
            screen.blit(p2_stat_txt, (p2_status_rect.centerx - p2_stat_txt.get_width()//2, p2_status_rect.y + 8))

            draw_button(screen, btn_back_rect, "Main Menu", btn_back_rect.collidepoint(mouse_pos), bg_color=(85, 85, 85))
            
            can_start = selections['p1']['ready'] and selections['p2']['ready']
            start_bg = (255, 204, 0) if can_start else (85, 85, 85)
            draw_button(screen, btn_start_rect, "Start Battle", btn_start_rect.collidepoint(mouse_pos) and can_start, bg_color=start_bg)

        elif current_state == STATES['COUNTDOWN']:
            overlay = pygame.Surface((CANVAS_WIDTH, CANVAS_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            screen.blit(overlay, (0, 0))

            cd_text = str(countdown_val) if countdown_val > 0 else "FIGHT!"
            txt_surf = font_countdown.render(cd_text, True, COLOR_TEXT_YELLOW)
            screen.blit(txt_surf, (CANVAS_WIDTH // 2 - txt_surf.get_width() // 2, CANVAS_HEIGHT // 2 - txt_surf.get_height() // 2))

        elif current_state == STATES['VICTORY']:
            overlay = pygame.Surface((CANVAS_WIDTH, CANVAS_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 10, 15, 215))
            screen.blit(overlay, (0, 0))

            win_surf = font_title.render(winner_message, True, COLOR_TEXT_YELLOW)
            screen.blit(win_surf, (CANVAS_WIDTH // 2 - win_surf.get_width() // 2, 220))

            draw_button(screen, btn_restart_rect, "Play Again", btn_restart_rect.collidepoint(mouse_pos))
            draw_button(screen, btn_menu_rect, "Back to Menu", btn_menu_rect.collidepoint(mouse_pos))

        pygame.display.flip()
        clock.tick(60)

if __name__ == '__main__':
    main()