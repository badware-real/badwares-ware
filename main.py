import pygame
import sys
import math

pygame.init()

WIDTH, HEIGHT = 1280, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Portal Platformer")
clock = pygame.time.Clock()
FPS = 60

WHITE = (240, 240, 240)
BLACK = (20, 20, 20)
ORANGE = (255, 140, 0)
BLUE = (0, 140, 255)
PLAYER_COLOR = (50, 200, 50)
BG_COLOR = (20, 20, 40)
EXIT_COLOR = (255, 215, 0)
TEXT_COLOR = (220, 220, 220)
BUTTON_COLOR = (70, 70, 120)
BUTTON_HOVER = (100, 100, 180)
BOX_COLOR = (160, 100, 40)
BOX_BORDER = (120, 70, 20)
BTN_ON = (50, 220, 50)
BTN_OFF = (200, 50, 50)
TRAPDOOR_COLOR = (180, 120, 60)

GRAVITY = 0.5
JUMP_SPEED = -13
MOVE_SPEED = 4
PORTAL_THIN = 10
PORTAL_LONG = 44

font_large = pygame.font.SysFont(None, 72)
font_med = pygame.font.SysFont(None, 48)
font_small = pygame.font.SysFont(None, 30)


class Platform:
    def __init__(self, x, y, w, h, portalable=True):
        self.rect = pygame.Rect(x, y, w, h)
        self.portalable = portalable
        self.color = (210, 210, 210) if portalable else (50, 50, 55)

    def draw(self, surf, cx, cy):
        r = self.rect.move(-cx, -cy)
        pygame.draw.rect(surf, self.color, r)
        border = (160, 160, 160) if self.portalable else (80, 80, 85)
        pygame.draw.rect(surf, border, r, 2)


class Trapdoor:
    """Solid gate when closed; passable when open."""
    portalable = False

    def __init__(self, linkname, x, y, w, h):
        self.linkname = linkname
        self.rect = pygame.Rect(x, y, w, h)
        self.open = False

    def draw(self, surf, cx, cy):
        r = self.rect.move(-cx, -cy)
        if self.open:
            # faint ghost outline so the player can see where it was
            pygame.draw.rect(surf, (60, 40, 20), r, 1)
        else:
            pygame.draw.rect(surf, TRAPDOOR_COLOR, r)
            pygame.draw.rect(surf, (220, 160, 80), r, 2)
            pygame.draw.line(surf, (220, 160, 80), r.topleft, r.bottomright, 1)
            pygame.draw.line(surf, (220, 160, 80), r.topright, r.bottomleft, 1)


class PressureButton:
    def __init__(self, linkname, x, y, w=44, h=10):
        self.linkname = linkname
        self.rect = pygame.Rect(x, y, w, h)
        self.active = False

    def update(self, player_rect, boxes):
        # trigger zone extends a few pixels above the button surface
        trigger = pygame.Rect(self.rect.x, self.rect.y - 8, self.rect.w, self.rect.h + 8)
        self.active = trigger.colliderect(player_rect)
        if not self.active:
            for box in boxes:
                if not box.carried and trigger.colliderect(box.rect):
                    self.active = True
                    break

    def draw(self, surf, cx, cy):
        r = self.rect.move(-cx, -cy)
        pygame.draw.rect(surf, BTN_ON if self.active else BTN_OFF, r, border_radius=2)
        pygame.draw.rect(surf, (200, 200, 200), r, 1, border_radius=2)
        lbl = font_small.render("BTN", True, BLACK)
        surf.blit(lbl, (r.centerx - lbl.get_width() // 2, r.y - 22))


class Box:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 32, 32)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.carried = False

    def update(self, platforms):
        if self.carried:
            return
        self.vy = min(self.vy + GRAVITY, 15)

        self.rect.x += self.vx
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vx > 0:
                    self.rect.right = p.rect.left
                else:
                    self.rect.left = p.rect.right
                self.vx = 0

        self.on_ground = False
        self.rect.y += self.vy
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vy >= 0:
                    self.rect.bottom = p.rect.top
                    self.vy = 0
                    self.on_ground = True
                else:
                    self.rect.top = p.rect.bottom
                    self.vy = 0

    def draw(self, surf, cx, cy):
        r = self.rect.move(-cx, -cy)
        pygame.draw.rect(surf, BOX_COLOR, r, border_radius=3)
        pygame.draw.rect(surf, BOX_BORDER, r, 2, border_radius=3)
        pygame.draw.line(surf, BOX_BORDER, r.topleft, r.bottomright, 1)
        pygame.draw.line(surf, BOX_BORDER, r.topright, r.bottomleft, 1)


class Portal:
    def __init__(self, inner, outer):
        self.inner = inner
        self.outer = outer
        self.rect = None
        self.normal = None
        self.platform = None

    def place(self, rect, normal, plat):
        self.rect = rect
        self.normal = normal
        self.platform = plat

    def clear(self):
        self.rect = None
        self.normal = None
        self.platform = None

    def draw(self, surf, cx, cy):
        if self.rect is None:
            return
        r = self.rect.move(-cx, -cy)
        pygame.draw.ellipse(surf, self.outer, r.inflate(8, 8))
        pygame.draw.ellipse(surf, self.inner, r)


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 28, 48)
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.cooldown = 0
        self.held_box = None

    def reset(self, x, y):
        self.rect.topleft = (x, y)
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.cooldown = 0
        if self.held_box:
            self.held_box.carried = False
            self.held_box = None

    def update(self, platforms):
        keys = pygame.key.get_pressed()
        self.vx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vx = -MOVE_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vx = MOVE_SPEED
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vy = JUMP_SPEED

        self.vy += GRAVITY

        self.rect.x += self.vx
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vx > 0:
                    self.rect.right = p.rect.left
                else:
                    self.rect.left = p.rect.right

        self.on_ground = False
        self.rect.y += self.vy
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vy > 0:
                    self.rect.bottom = p.rect.top
                    self.vy = 0
                    self.on_ground = True
                elif self.vy < 0:
                    self.rect.top = p.rect.bottom
                    self.vy = 0

        if self.cooldown > 0:
            self.cooldown -= 1

        # Keep carried box floating above the player's head
        if self.held_box:
            self.held_box.rect.centerx = self.rect.centerx
            self.held_box.rect.bottom = self.rect.top - 2

    def draw(self, surf, cx, cy):
        r = self.rect.move(-cx, -cy)
        pygame.draw.rect(surf, PLAYER_COLOR, r, border_radius=4)
        ey = r.top + 13
        pygame.draw.circle(surf, BLACK, (r.left + 8, ey), 4)
        pygame.draw.circle(surf, BLACK, (r.right - 8, ey), 4)
        pygame.draw.circle(surf, WHITE, (r.left + 9, ey - 1), 2)
        pygame.draw.circle(surf, WHITE, (r.right - 7, ey - 1), 2)


def raycast(platforms, ox, oy, dx, dy, max_dist=2000):
    step = 3
    dist = 0
    px, py = ox, oy
    while dist < max_dist:
        nx = ox + dx * dist
        ny = oy + dy * dist
        for plat in platforms:
            if plat.rect.collidepoint(nx, ny):
                if abs(dx) >= abs(dy):
                    normal = 'left' if dx > 0 else 'right'
                else:
                    normal = 'top' if dy > 0 else 'bottom'
                return (px, py, normal, plat)
        px, py = nx, ny
        dist += step
    return None


def portal_rect(hx, hy, normal, plat_rect):
    pt, pl = PORTAL_THIN, PORTAL_LONG
    if normal == 'left':
        x = plat_rect.left - pt // 2
        y = max(plat_rect.top + 4, min(int(hy) - pl // 2, plat_rect.bottom - pl - 4))
        return pygame.Rect(x, y, pt, pl)
    if normal == 'right':
        x = plat_rect.right - pt // 2
        y = max(plat_rect.top + 4, min(int(hy) - pl // 2, plat_rect.bottom - pl - 4))
        return pygame.Rect(x, y, pt, pl)
    if normal == 'top':
        y = plat_rect.top - pt // 2
        x = max(plat_rect.left + 4, min(int(hx) - pl // 2, plat_rect.right - pl - 4))
        return pygame.Rect(x, y, pl, pt)
    y = plat_rect.bottom - pt // 2
    x = max(plat_rect.left + 4, min(int(hx) - pl // 2, plat_rect.right - pl - 4))
    return pygame.Rect(x, y, pl, pt)


def teleport(player, p_in, p_out):
    if p_out.rect is None:
        return
    n = p_out.normal
    player.rect.centerx = p_out.rect.centerx
    player.rect.centery = p_out.rect.centery
    if n == 'left':
        player.rect.right = p_out.platform.rect.left - 2
        player.vx = -max(abs(player.vx), 3)
    elif n == 'right':
        player.rect.left = p_out.platform.rect.right + 2
        player.vx = max(abs(player.vx), 3)
    elif n == 'top':
        player.rect.bottom = p_out.platform.rect.top - 2
        player.vy = min(player.vy, -9)
    else:
        player.rect.top = p_out.platform.rect.bottom + 2
        player.vy = max(player.vy, 3)
    player.cooldown = 20


def check_teleport(player, pa, pb):
    if player.cooldown > 0:
        return
    if pa.rect and pb.rect:
        if player.rect.colliderect(pa.rect):
            teleport(player, pa, pb)
        elif player.rect.colliderect(pb.rect):
            teleport(player, pb, pa)


# ---------- LEVELS ----------

def make_level1():
    plats = [
        # Bounds
        Platform(0, 0, 1400, 50, False),
        Platform(0, 150, 450, 50, False),
        Platform(420, 50, 30, 60, False),
        Platform(0, 670, 1400, 50, False),
        Platform(0, -50, 50, 500, True),
        Platform(0, 450, 50, 300, True),
        Platform(0, 400, 150, 50, False),
        Platform(1350, 0, 50, 720, False),
        # Starting area floor (non-portalable)
        Platform(50, 590, 350, 80, False),
        # Big wall in middle
        Platform(400, 300, 40, 550, False),
        # White floor section (portalable) to place second portal
        Platform(640, 200, 10, 100, True),
        Platform(1230, 350, 10, 100, True),
        Platform(1230, 50, 10, 300, False),
        Platform(780, 200, 10, 100, False),
        Platform(640, 300, 150, 10, False),
        Platform(640, 450, 1000, 10, False),
        Platform(640, 200, 150, 10, False),
        # Upper platforms
        Platform(650, 50, 180, 10, True),
        # Platform(440, 510, 10, 160, True),
    ]
    boxes = [
        Box(100, 100),
        Box(600, 450),
    ]
    buttons = [
        PressureButton("Link1", 820, 440, 44, 10),
        PressureButton("Link2", 820, 660, 44, 10),
    ]
    trapdoors = [
        Trapdoor("Link1", 440, 450, 200, 10),
        Trapdoor("Link1", 640, 50, 10, 200),
        Trapdoor("Link2", 940, 460, 10, 210),
    ]
    return {
        'platforms': plats,
        'boxes': boxes,
        'buttons': buttons,
        'trapdoors': trapdoors,
        'spawn': (80, 520),
        'exit_rect': pygame.Rect(1250, 600, 50, 60),
        'name': 'Level 1: The Boxes',
        'hint': 'E = pick up / drop box   |   Place box on red button to open the gate',
    }


def make_level2():
    plats = [
        # Bounds
        Platform(0, 0, 1400, 50, False),
        Platform(0, 670, 1400, 50, False),
        Platform(0, 0, 50, 720, False),
        Platform(1350, 0, 50, 720, False),
        # Floor sections
        Platform(50, 610, 280, 60, False),
        Platform(420, 610, 200, 60, False),
        Platform(750, 610, 600, 60, False),
        # Blocking black wall — forces portal use
        Platform(330, 200, 90, 410, False),
        # White walls to use
        Platform(50, 50, 30, 560, True),
        Platform(700, 50, 30, 560, True),
        Platform(700, 570, 600, 25, True),
        # Middle platforms (black)
        Platform(50, 440, 280, 22, False),
        Platform(420, 330, 200, 22, False),
        # Upper area
        Platform(750, 350, 550, 22, False),
        Platform(750, 200, 550, 22, False),
        Platform(1300, 200, 50, 400, False),
        # White ceiling section for final portal shot
        Platform(800, 50, 500, 30, True),
        # Exit ledge
        Platform(1250, 140, 100, 60, False),
    ]
    return {
        'platforms': plats,
        'boxes': [],
        'buttons': [],
        'trapdoors': [],
        'spawn': (80, 540),
        'exit_rect': pygame.Rect(1260, 80, 50, 60),
        'name': 'Level 2: Ascent',
        'hint': 'Use portals to bypass the black wall and reach the top!',
    }


# ---------- GAME ----------

class Game:
    def __init__(self):
        self.state = 'menu'
        self.level_data = None
        self.player = Player(100, 500)
        self.pa = Portal(ORANGE, (255, 180, 50))
        self.pb = Portal(BLUE, (50, 180, 255))
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.buttons = [
            {'rect': pygame.Rect(WIDTH // 2 - 160, 300, 320, 65), 'label': 'Level 1: The Boxes', 'n': 1},
            {'rect': pygame.Rect(WIDTH // 2 - 160, 400, 320, 65), 'label': 'Level 2: Ascent', 'n': 2},
        ]

    def load_level(self, n):
        self.level_data = make_level1() if n == 1 else make_level2()
        self._current_level = n
        sx, sy = self.level_data['spawn']
        self.player.reset(sx, sy)
        self.pa.clear()
        self.pb.clear()
        self.cam_x = sx - WIDTH // 2
        self.cam_y = sy - HEIGHT // 2
        self.state = 'playing'

    def shoot(self, portal, mx, my):
        px, py = self.player.rect.centerx, self.player.rect.centery
        wx = mx + self.cam_x
        wy = my + self.cam_y
        d = math.hypot(wx - px, wy - py)
        if d == 0:
            return
        result = raycast(self.level_data['platforms'], px, py, (wx - px) / d, (wy - py) / d)
        if result:
            hx, hy, normal, plat = result
            if plat.portalable:
                portal.place(portal_rect(hx, hy, normal, plat.rect), normal, plat)

    def update(self):
        if self.state != 'playing':
            return

        boxes = self.level_data.get('boxes', [])
        btns = self.level_data.get('buttons', [])
        trapdoors = self.level_data.get('trapdoors', [])

        # Static solids: platforms + any closed trapdoors
        static = self.level_data['platforms'] + [td for td in trapdoors if not td.open]

        # Update boxes against static geometry only
        for box in boxes:
            box.update(static)

        # Player collides with static geometry + any non-carried box (can stand on it)
        solid = static + [box for box in boxes if not box.carried]
        self.player.update(solid)

        # Update pressure buttons
        for btn in btns:
            btn.update(self.player.rect, boxes)

        # All trapdoors open while any button is active
        # any_active = any(btn.active for btn in btns)
        # for td in trapdoors:
        #    td.open = any_active

        for btn in btns:
            for trp in trapdoors:
                if btn.linkname == trp.linkname:
                    trp.open = btn.active

        check_teleport(self.player, self.pa, self.pb)

        tx = self.player.rect.centerx - WIDTH // 2
        ty = self.player.rect.centery - HEIGHT // 2
        self.cam_x += (tx - self.cam_x) * 0.12
        self.cam_y += (ty - self.cam_y) * 0.12
        self.cam_x = max(0.0, self.cam_x)
        self.cam_y = max(0.0, self.cam_y)

        if self.player.rect.colliderect(self.level_data['exit_rect']):
            self.state = 'win'
        if self.player.rect.top > 800:
            sx, sy = self.level_data['spawn']
            self.player.reset(sx, sy)
            self.pa.clear()
            self.pb.clear()

    def draw(self):
        screen.fill(BG_COLOR)
        if self.state == 'menu':
            self._draw_menu()
        elif self.state in ('playing', 'win'):
            self._draw_game()
            if self.state == 'win':
                self._draw_win()

    def _draw_menu(self):
        t = font_large.render("PORTAL PLATFORMER", True, ORANGE)
        screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 140))
        s = font_small.render("Select a level to play", True, TEXT_COLOR)
        screen.blit(s, (WIDTH // 2 - s.get_width() // 2, 240))

        mx, my = pygame.mouse.get_pos()
        for b in self.buttons:
            col = BUTTON_HOVER if b['rect'].collidepoint(mx, my) else BUTTON_COLOR
            pygame.draw.rect(screen, col, b['rect'], border_radius=10)
            pygame.draw.rect(screen, ORANGE, b['rect'], 2, border_radius=10)
            lbl = font_med.render(b['label'], True, TEXT_COLOR)
            screen.blit(lbl, (b['rect'].centerx - lbl.get_width() // 2,
                               b['rect'].centery - lbl.get_height() // 2))

        legend = [
            ("LMB", ORANGE, "Orange portal"),
            ("RMB", BLUE,   "Blue portal"),
        ]
        for i, (key, col, desc) in enumerate(legend):
            k = font_small.render(f"[{key}]", True, col)
            d = font_small.render(desc, True, (180, 180, 180))
            screen.blit(k, (WIDTH // 2 - 120, 520 + i * 34))
            screen.blit(d, (WIDTH // 2 - 50, 520 + i * 34))

        ctrl = font_small.render("WASD / Arrow keys = Move    Space = Jump    E = Pick up box    R = Reset    ESC = Menu", True, (120, 120, 120))
        screen.blit(ctrl, (WIDTH // 2 - ctrl.get_width() // 2, HEIGHT - 50))

        pygame.draw.rect(screen, (210, 210, 210), pygame.Rect(WIDTH // 2 - 250, 590, 30, 30))
        wt = font_small.render("= portalable surface", True, (190, 190, 190))
        screen.blit(wt, (WIDTH // 2 - 210, 595))
        pygame.draw.rect(screen, (50, 50, 55), pygame.Rect(WIDTH // 2 + 60, 590, 30, 30))
        bt = font_small.render("= solid (no portal)", True, (120, 120, 120))
        screen.blit(bt, (WIDTH // 2 + 100, 595))

    def _draw_game(self):
        cx, cy = int(self.cam_x), int(self.cam_y)

        for td in self.level_data.get('trapdoors', []):
            td.draw(screen, cx, cy)

        for plat in self.level_data['platforms']:
            plat.draw(screen, cx, cy)

        for btn in self.level_data.get('buttons', []):
            btn.draw(screen, cx, cy)

        for box in self.level_data.get('boxes', []):
            box.draw(screen, cx, cy)

        er = self.level_data['exit_rect'].move(-cx, -cy)
        pygame.draw.rect(screen, EXIT_COLOR, er, border_radius=4)
        el = font_small.render("EXIT", True, BLACK)
        screen.blit(el, (er.centerx - el.get_width() // 2, er.centery - el.get_height() // 2))

        self.pa.draw(screen, cx, cy)
        self.pb.draw(screen, cx, cy)
        self.player.draw(screen, cx, cy)

        # Pickup hint when close to an uncarried box
        if not self.player.held_box:
            zone = self.player.rect.inflate(24, 24)
            for box in self.level_data.get('boxes', []):
                if not box.carried and zone.colliderect(box.rect):
                    br = box.rect.move(-cx, -cy)
                    hint = font_small.render("[E]", True, (220, 220, 80))
                    screen.blit(hint, (br.centerx - hint.get_width() // 2, br.top - 24))
                    break

        # Aiming line
        mx, my = pygame.mouse.get_pos()
        psx = self.player.rect.centerx - cx
        psy = self.player.rect.centery - cy
        pygame.draw.line(screen, (80, 80, 100), (psx, psy), (mx, my), 1)

        # HUD
        screen.blit(font_small.render(self.level_data['name'], True, TEXT_COLOR), (10, 10))
        screen.blit(font_small.render(self.level_data['hint'], True, (140, 140, 200)), (10, 38))
        screen.blit(font_small.render("R = Reset   ESC = Menu", True, (100, 100, 100)), (10, 66))
        screen.blit(font_small.render("[LMB] Orange portal", True, ORANGE), (WIDTH - 220, 10))
        screen.blit(font_small.render("[RMB] Blue portal", True, BLUE), (WIDTH - 220, 38))

    def _draw_win(self):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        screen.blit(ov, (0, 0))
        w = font_large.render("LEVEL COMPLETE!", True, EXIT_COLOR)
        screen.blit(w, (WIDTH // 2 - w.get_width() // 2, HEIGHT // 2 - 70))
        c = font_med.render("ESC = Menu    R = Replay", True, TEXT_COLOR)
        screen.blit(c, (WIDTH // 2 - c.get_width() // 2, HEIGHT // 2 + 30))

    def handle(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = 'menu'
            elif event.key == pygame.K_r and self.state in ('playing', 'win'):
                self.load_level(self._current_level)
            elif event.key == pygame.K_e and self.state == 'playing':
                boxes = self.level_data.get('boxes', [])
                if self.player.held_box:
                    # Drop the box to the side of the player
                    box = self.player.held_box
                    box.carried = False
                    box.vy = 0.0
                    box.vx = 0.0
                    if self.player.vx >= 0:
                        box.rect.left = self.player.rect.right + 2
                    else:
                        box.rect.right = self.player.rect.left - 2
                    box.rect.centery = self.player.rect.centery
                    self.player.held_box = None
                else:
                    # Pick up nearby box
                    zone = self.player.rect.inflate(24, 24)
                    for box in boxes:
                        if not box.carried and zone.colliderect(box.rect):
                            box.carried = True
                            self.player.held_box = box
                            break
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.state == 'playing':
                if event.button == 1:
                    self.shoot(self.pa, *event.pos)
                elif event.button == 3:
                    self.shoot(self.pb, *event.pos)
            elif self.state == 'menu' and event.button == 1:
                for b in self.buttons:
                    if b['rect'].collidepoint(event.pos):
                        self.load_level(b['n'])
        return True


def main():
    game = Game()
    running = True
    while running:
        for event in pygame.event.get():
            if not game.handle(event):
                running = False
        game.update()
        game.draw()
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
