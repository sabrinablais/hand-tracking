import cv2
import mediapipe as mp
import pygame
import random
import math
import time
import os

# ------------------------------
# Config
# ------------------------------
# Non-linear score thresholds for boss per level
LEVEL_BOSS_THRESHOLDS = [150, 500, 1000, 2000, 3500, 5500]  # extend as needed

# ------------------------------
# MediaPipe Hand Tracking
# ------------------------------
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.6, min_tracking_confidence=0.6)

# ------------------------------
# Pygame Setup
# ------------------------------
pygame.init()
win = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
pygame.display.set_caption("Air Space VR Shooter - Sabrina Blais (who should be sleeping by now...)")

clock = pygame.time.Clock()
font_big = pygame.font.SysFont("Arial", 80)
font_med = pygame.font.SysFont("Arial", 50)
font_small = pygame.font.SysFont("Arial", 30)

# ------------------------------
# Colors
# ------------------------------
BLACK = (0,0,0)
WHITE = (255,255,255)
RED = (255,0,0)
YELLOW = (255,255,0)
BLUE = (0,150,255)
STAR_COLOR = (200,200,255)
PARTICLE_COLOR = (255,200,50)

# ------------------------------
# Load Assets
# ------------------------------
ASSET_DIR = os.path.join(os.getcwd(), "space_game")
def load_image(name):
    return pygame.image.load(os.path.join(ASSET_DIR, name)).convert_alpha()
def load_sound(name):
    return pygame.mixer.Sound(os.path.join(ASSET_DIR, name))

# NOTE: If any file missing this will throw; keep assets in space_game folder.
ship_img = load_image("ship.png")
enemy_img = load_image("enemy.png")
boss_img = load_image("boss.png")
heart_img = load_image("heart.png")

laser_sounds = [load_sound("laser1.wav"), load_sound("laser13.wav")]
enemy_attack_sound = load_sound("enemy_attack.wav")
explosion_sound = load_sound("explosion.wav")
powerup_sound = load_sound("powerup.wav")
pygame.mixer.music.load(os.path.join(ASSET_DIR,"background.mp3"))
pygame.mixer.music.play(-1)

# ------------------------------
# Game State
# ------------------------------
def create_state():
    return {
        "player": {
            "x": WIDTH//2,
            "y": HEIGHT-150,
            "prev_x": None,
            "prev_y": None,
            "life": 5,
            "shield": False,
            "pinch_cooldown": 0,
            "invincible": 0  # frames of invincibility after taking damage
        },
        "bullets": [],
        "enemy_bullets": [],
        "enemies": [],
        "bosses": [],
        "particles": [],
        "powerups": [],
        "score": 0,
        "level": 1,
        "enemy_spawn_timer": 0,
        "boss_spawned": False,
        "running": True,
        "game_over": False,
        "menu": True
    }

# ------------------------------
# Stars
# ------------------------------
stars = [[random.randint(0,WIDTH), random.randint(0,HEIGHT), random.randint(1,3)] for _ in range(120)]

# ------------------------------
# Helper Functions
# ------------------------------
def draw_text_centered(surface, text, font, color, y_offset=0):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(center=(WIDTH//2, HEIGHT//2 + y_offset))
    surface.blit(rendered, rect)

def spawn_explosion(state, x, y, count=15):
    for _ in range(count):
        state["particles"].append([x, y, random.randint(2,5), random.uniform(-2,2), random.uniform(-2,2)])

def draw_hearts(top_left_x, top_left_y, life):
    for i in range(max(0, life)):
        win.blit(pygame.transform.scale(heart_img, (36,36)), (top_left_x + i*40, top_left_y))

def apply_gravity(state):
    for gz in state.get("gravity_zones", []):
        gx, gy, r = gz
        for b in state["bullets"]:
            dx, dy = gx-b["x"], gy-b["y"]
            dist = math.hypot(dx, dy)
            if dist < r and dist != 0:
                b["x"] += dx/dist*0.5
                b["y"] += dy/dist*0.5
        for e in state["enemies"]:
            dx, dy = gx-e["x"], gy-e["y"]
            dist = math.hypot(dx, dy)
            if dist < r and dist != 0:
                e["x"] += dx/dist*0.3
                e["y"] += dy/dist*0.3

def draw_game(state):
    win.fill(BLACK)
    # Stars warp
    for star in stars:
        pygame.draw.circle(win, STAR_COLOR, (star[0], star[1]), star[2])
        # safe prev_x usage
        prev_x = state["player"]["prev_x"] if state["player"]["prev_x"] is not None else state["player"]["x"]
        star[1] += max(1, abs(state["player"]["x"] - prev_x)//15)
        if star[1] > HEIGHT:
            star[0] = random.randint(0, WIDTH)
            star[1] = 0
            star[2] = random.randint(1,3)

    # Player
    player = state["player"]
    img = pygame.transform.scale(ship_img, (100,100))
    win.blit(img, (player["x"]-50, player["y"]-50))

    # Draw hearts in top-left so they're always visible
    draw_hearts(10, 10, player["life"])

    # Bullets & trails
    for b in state["bullets"]:
        pygame.draw.rect(win, YELLOW, (b["x"]-5, b["y"], 10, 20))
        for t in b.get("trail", []):
            pygame.draw.circle(win, YELLOW, t, 3)

    # Enemy bullets
    for eb in state["enemy_bullets"]:
        pygame.draw.rect(win, RED, (eb["x"]-5, eb["y"], 10, 20))

    # Enemies
    for e in state["enemies"]:
        win.blit(pygame.transform.scale(enemy_img, (60,50)), (e["x"], e["y"]))

    # Bosses (with life bar)
    for boss in state["bosses"]:
        win.blit(pygame.transform.scale(boss_img, (150,150)), (int(boss["x"]), int(boss["y"])))
        # boss life bar
        max_life = boss.get("max_life", boss["life"])
        life_ratio = boss["life"] / max_life if max_life > 0 else 0
        bar_w = 300
        pygame.draw.rect(win, (100,100,100), (WIDTH//2 - bar_w//2, 20, bar_w, 18))
        pygame.draw.rect(win, RED, (WIDTH//2 - bar_w//2, 20, int(bar_w * life_ratio), 18))

    # Particles
    for p in state["particles"]:
        pygame.draw.circle(win, PARTICLE_COLOR, (int(p[0]), int(p[1])), int(p[2]))

    # Power-ups
    for pu in state["powerups"]:
        win.blit(pygame.transform.scale(heart_img, (36,36)), (pu[0]-18, pu[1]-18))

    # HUD
    score_text = font_small.render(f"Score: {state['score']}", True, WHITE)
    win.blit(score_text, (10, 56))
    level_text = font_small.render(f"Level: {state['level']}", True, WHITE)
    win.blit(level_text, (WIDTH-150, 10))

    pygame.display.update()

# ------------------------------
# Main Loop
# ------------------------------
state = create_state()

while True:
    clock.tick(60)
    success, frame = cap.read()
    if not success:
        break
    frame = cv2.flip(frame, 1)
    h, w, c = frame.shape
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)

    # ---- MENU: press ENTER to start ----
    if state["menu"]:
        win.fill(BLACK)
        draw_text_centered(win, "Air Space VR Shooter", font_big, WHITE, -100)
        draw_text_centered(win, "By Sabrina Blais (who should be sleeping by now...)", font_med, WHITE, -30)
        draw_text_centered(win, "Press ENTER to start", font_small, WHITE, 80)
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); cap.release(); cv2.destroyAllWindows(); exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    state["menu"] = False
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit(); cap.release(); cv2.destroyAllWindows(); exit()
        # allow menu to be controlled also by mouse click optionally
        continue

    # game running:
    # events (collect key events here too)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); cap.release(); cv2.destroyAllWindows(); exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit(); cap.release(); cv2.destroyAllWindows(); exit()

    # reset shield each frame
    state["player"]["shield"] = False

    # HAND INPUT
    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]
        player = state["player"]
        index_tip = hand_landmarks.landmark[8]
        thumb_tip = hand_landmarks.landmark[4]
        wrist = hand_landmarks.landmark[0]
        fingertips = [hand_landmarks.landmark[i] for i in [8,12,16,20]]

        # compute hand center (wrist + index + middle) for better alignment
        middle_tip = hand_landmarks.landmark[12]
        hand_cx = (wrist.x + index_tip.x + middle_tip.x) / 3
        hand_cy = (wrist.y + index_tip.y + middle_tip.y) / 3
        px, py = int(hand_cx * WIDTH), int(hand_cy * HEIGHT)

        # smoothing movement
        if player["prev_x"] is not None:
            player["x"] += (px - player["x"]) / 3.0
            player["y"] += (py - player["y"]) / 3.0
        else:
            player["x"], player["y"] = px, py
        player["prev_x"], player["prev_y"] = px, py

        # clamp to screen (so you can reach corners)
        player["x"] = max(50, min(WIDTH-50, int(player["x"])))
        player["y"] = max(50, min(HEIGHT-50, int(player["y"])))

        # pinch to shoot (with cooldown)
        pinch = math.hypot((index_tip.x - thumb_tip.x) * w, (index_tip.y - thumb_tip.y) * h)
        if pinch < 40 and player["pinch_cooldown"] == 0:
            state["bullets"].append({"x": player["x"], "y": player["y"], "trail": []})
            random.choice(laser_sounds).play()
            player["pinch_cooldown"] = 12
        if player["pinch_cooldown"] > 0:
            player["pinch_cooldown"] -= 1

        # open palm -> shield
        if all(f.y < wrist.y for f in fingertips):
            player["shield"] = True

    # Move bullets
    for b in state["bullets"][:]:
        b["trail"].append((b["x"], b["y"]))
        if len(b["trail"]) > 8:
            b["trail"].pop(0)
        b["y"] -= 14
        if b["y"] < -20:
            state["bullets"].remove(b)

    # Spawn enemies
    state["enemy_spawn_timer"] += 1
    if state["enemy_spawn_timer"] >= max(30, 50 - state["level"]*5):
        state["enemy_spawn_timer"] = 0
        ex = random.randint(30, WIDTH-90)
        state["enemies"].append({"x": ex, "y": -40, "split": random.choice([False, True, False])})

    player = state["player"]

    # Move enemies and handle collisions
    for e in state["enemies"][:]:
        e["y"] += 2 + state["level"] * 0.5
        # enemy shooting (later levels)
        if random.random() < 0.005 * state["level"]:
            state["enemy_bullets"].append({"x": e["x"] + 30, "y": e["y"] + 50})

        # collision with player bullets
        for b in state["bullets"][:]:
            if e["x"] < b["x"] < e["x"] + 60 and e["y"] < b["y"] < e["y"] + 50:
                state["score"] += 10
                spawn_explosion(state, e["x"] + 30, e["y"] + 25)
                explosion_sound.play()
                if e["split"]:
                    state["enemies"].append({"x": e["x"] - 30, "y": e["y"], "split": False})
                    state["enemies"].append({"x": e["x"] + 30, "y": e["y"], "split": False})
                if e in state["enemies"]:
                    state["enemies"].remove(e)
                if b in state["bullets"]:
                    state["bullets"].remove(b)
                break

        # collision with player (body)
        if e["y"] + 50 >= player["y"] and abs(e["x"] + 30 - player["x"]) < 50 and not player["shield"]:
            # only apply damage if not currently invincible
            if player["invincible"] == 0:
                player["life"] -= 1
                player["invincible"] = 60  # 1 second invincibility
                spawn_explosion(state, player["x"], player["y"])
                explosion_sound.play()
                if player["life"] <= 0:
                    state["game_over"] = True
                    state["running"] = False
            if e in state["enemies"]:
                state["enemies"].remove(e)

    # Move enemy bullets and handle collisions
    for eb in state["enemy_bullets"][:]:
        eb["y"] += 8 + state["level"]*0.2
        if eb["y"] > HEIGHT + 20:
            state["enemy_bullets"].remove(eb)
            continue
        if abs(eb["x"] - player["x"]) < 36 and abs(eb["y"] - player["y"]) < 36 and not player["shield"]:
            if player["invincible"] == 0:
                player["life"] -= 1
                player["invincible"] = 60
                spawn_explosion(state, player["x"], player["y"])
                explosion_sound.play()
                if player["life"] <= 0:
                    state["game_over"] = True
                    state["running"] = False
            if eb in state["enemy_bullets"]:
                state["enemy_bullets"].remove(eb)

    # Power-ups: heart drops
    if random.random() < 0.002:
        px = random.randint(50, WIDTH - 50)
        state["powerups"].append([px, -20])
    for pu in state["powerups"][:]:
        pu[1] += 2
        if abs(pu[0] - player["x"]) < 40 and abs(pu[1] - player["y"]) < 40:
            if player["life"] < 5:
                player["life"] += 1
            powerup_sound.play()
            state["powerups"].remove(pu)
        elif pu[1] > HEIGHT + 20:
            state["powerups"].remove(pu)

    # reduce invincibility timer
    if player["invincible"] > 0:
        player["invincible"] -= 1

    # Apply gravity (optional)
    apply_gravity(state)

    # Boss spawn using LEVEL_BOSS_THRESHOLDS
    current_threshold = LEVEL_BOSS_THRESHOLDS[min(state["level"] - 1, len(LEVEL_BOSS_THRESHOLDS) - 1)]
    if state["score"] >= current_threshold and not state["boss_spawned"]:
        boss_life = 50 + state["level"] * 20
        state["bosses"].append({"x": WIDTH//2 - 75, "y": 50, "life": boss_life, "max_life": boss_life, "speed_x": 3 + state["level"]*0.5})
        state["boss_spawned"] = True
        draw_text_centered(win, f"Level {state['level']} - Boss Incoming!", font_big, RED)
        pygame.display.update()
        pygame.time.delay(1400)

    # Move bosses (horizontal only) and handle their bullets & collisions
    for boss in state["bosses"][:]:
        boss["x"] += boss["speed_x"]
        if boss["x"] <= 0 or boss["x"] >= WIDTH - 150:
            boss["speed_x"] *= -1
        # boss shoots
        if random.random() < 0.02 + state["level"] * 0.001:
            state["enemy_bullets"].append({"x": boss["x"] + 75, "y": boss["y"] + 100})
            enemy_attack_sound.play()
        # collision with player bullets
        for b in state["bullets"][:]:
            if boss["x"] < b["x"] < boss["x"] + 150 and boss["y"] < b["y"] < boss["y"] + 150:
                boss["life"] -= 1
                spawn_explosion(state, b["x"], b["y"], count=6)
                if b in state["bullets"]:
                    state["bullets"].remove(b)
                if boss["life"] <= 0:
                    state["score"] += 50
                    explosion_sound.play()
                    if boss in state["bosses"]:
                        state["bosses"].remove(boss)
            
            
            
            
                    state["level"] += 1
                    state["boss_spawned"] = False
                    draw_text_centered(win, f"Level {state['level']}", font_big, BLUE)
                    pygame.display.update()
                    pygame.time.delay(1200)
                    break

    # Move particles
    for p in state["particles"][:]:
        p[0] += p[3]; p[1] += p[4]; p[2] -= 0.12
        if p[2] <= 0:
            state["particles"].remove(p)

    # Draw everything
    draw_game(state)

    # Game over handling inside loop (so UI updates before exit)
    if state["game_over"]:
        win.fill(BLACK)
        draw_text_centered(win, "GAME OVER", font_big, RED)
        pygame.display.update()
        pygame.time.wait(2500)
        pygame.quit(); cap.release(); cv2.destroyAllWindows(); exit()

# cleanup (won't reach normally because of exits above)
pygame.quit()
cap.release()
cv2.destroyAllWindows()
