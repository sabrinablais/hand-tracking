import cv2
import mediapipe as mp
import pygame
import random
import math
import numpy as np
import time
import os

# ------------------------------
# Initialize Hand Tracking
# ------------------------------
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.6, min_tracking_confidence=0.6)

# ------------------------------
# Pygame Setup
# ------------------------------
pygame.init()
win = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
pygame.display.set_caption("SPACE AIR VR SHOOTER")
clock = pygame.time.Clock()
font_big = pygame.font.SysFont("Arial", 80)
font_small = pygame.font.SysFont("Arial", 40)

# ------------------------------
# Colors
# ------------------------------
BLACK = (0,0,0)
WHITE = (255,255,255)
GREEN = (0,255,0)
RED = (255,0,0)
YELLOW = (255,255,0)
BLUE = (0,150,255)
PARTICLE_COLOR = (255,200,50)

# ------------------------------
# Load Assets
# ------------------------------
def load_image(filename, scale=1.0):
    img = pygame.image.load(os.path.join("space_game", filename)).convert_alpha()
    if scale != 1.0:
        w, h = img.get_size()
        img = pygame.transform.smoothscale(img, (int(w*scale), int(h*scale)))
    return img

player_img = load_image("ship.png", scale=2.5)  # bigger player
enemy_img = load_image("enemy.png", scale=2.5)
boss_img = load_image("boss.png", scale=3.0)
heart_img = load_image("heart.png", scale=1.5)

# Sounds
pygame.mixer.init()
try:
    laser_sound = pygame.mixer.Sound(os.path.join("space_game", "laser1.wav"))
    enemy_attack_sound = pygame.mixer.Sound(os.path.join("space_game", "enemy_attack.wav")) if os.path.exists(os.path.join("space_game", "enemy_attack.wav")) else None
    explosion_sound = pygame.mixer.Sound(os.path.join("space_game", "explosion.wav")) if os.path.exists(os.path.join("space_game", "explosion.wav")) else None
    powerup_sound = pygame.mixer.Sound(os.path.join("space_game", "powerup.wav")) if os.path.exists(os.path.join("space_game", "powerup.wav")) else None
    pygame.mixer.music.load(os.path.join("space_game","background.mp3"))
    pygame.mixer.music.play(-1)
except Exception as e:
    print("Error loading sounds:", e)

# ------------------------------
# Game State
# ------------------------------
def create_state():
    return {
        "player": {"x": WIDTH//2, "y": HEIGHT-150, "prev_x": None, "prev_y": None, "shield": False, "pinch_cooldown": 0, "life": 5},
        "bullets": [],
        "enemies": [],
        "enemy_spawn_timer": 0,
        "score": 0,
        "particles": [],
        "powerups": [],
        "gravity_zones": [(WIDTH//2, HEIGHT//2, 100)],
        "running": True,
        "level":1,
        "boss": None,
        "show_level_text": True,
        "level_timer": 120
    }

# Stars
stars = [[random.randint(0,WIDTH), random.randint(0,HEIGHT), random.randint(1,3)] for _ in range(120)]

# ------------------------------
# Drawing Functions
# ------------------------------
def draw_game(state):
    win.fill(BLACK)
    
    # Stars warp
    for star in stars:
        pygame.draw.circle(win, WHITE, (star[0], star[1]), star[2])
        star[1]+=max(1, abs(state["player"]["x"] - state["player"]["prev_x"] if state["player"]["prev_x"] else 0)//10)
        if star[1]>HEIGHT:
            star[0]=random.randint(0,WIDTH)
            star[1]=0
            star[2]=random.randint(1,3)
    
    # Player
    px, py = state["player"]["x"], state["player"]["y"]
    player_rect = player_img.get_rect(center=(px, py))
    win.blit(player_img, player_rect)
    
    # Bullets
    for b in state["bullets"]:
        pygame.draw.rect(win, YELLOW, (b["x"]-5,b["y"],10,20))
        for t in b.get("trail",[]):
            pygame.draw.circle(win, YELLOW, t, 3)
    
    # Enemies
    for e in state["enemies"]:
        enemy_rect = enemy_img.get_rect(center=(e["x"], e["y"]))
        win.blit(enemy_img, enemy_rect)
    
    # Boss
    if state["boss"]:
        boss_rect = boss_img.get_rect(center=(state["boss"]["x"], state["boss"]["y"]))
        win.blit(boss_img, boss_rect)
    
    # Particles
    for p in state["particles"]:
        pygame.draw.circle(win, PARTICLE_COLOR, (int(p[0]),int(p[1])), p[2])
    
    # Powerups
    for pu in state["powerups"]:
        win.blit(heart_img, (pu[0], pu[1]))
    
    # Score
    score_text = font_small.render(f"Score: {state['score']}", True, WHITE)
    win.blit(score_text, (10,10))
    
    # Life
    life_text = font_small.render(f"Life: {state['player']['life']}", True, RED)
    win.blit(life_text, (10,50))
    
    # Level text
    if state["show_level_text"]:
        level_text = font_big.render(f"Level {state['level']}", True, YELLOW)
        win.blit(level_text, (WIDTH//2 - level_text.get_width()//2, HEIGHT//2 - 50))
    
    pygame.display.update()

# ------------------------------
# Physics / Game Functions
# ------------------------------
def apply_gravity(state):
    for gz in state["gravity_zones"]:
        gx, gy, r = gz
        for b in state["bullets"]:
            dx, dy = gx-b["x"], gy-b["y"]
            dist = math.hypot(dx, dy)
            if dist<r:
                b["x"] += dx/dist*0.5
                b["y"] += dy/dist*0.5
        for e in state["enemies"]:
            dx, dy = gx-e["x"], gy-e["y"]
            dist = math.hypot(dx, dy)
            if dist<r:
                e["x"] += dx/dist*0.3
                e["y"] += dy/dist*0.3

def spawn_explosion(state, x, y):
    for _ in range(15):
        state["particles"].append([x, y, random.randint(2,5), random.uniform(-2,2), random.uniform(-2,2)])

def spawn_enemy(state):
    ex = random.randint(50, WIDTH-50)
    state["enemies"].append({"x":ex,"y":0,"split":random.choice([False, True, False])})

# ------------------------------
# Main Game Loop
# ------------------------------
state = create_state()

# Intro text
intro_text = font_big.render("SPACE AIR VR SHOOTER", True, BLUE)
author_text = font_small.render("by Sabrina Blais (who should be sleeping by now...)", True, WHITE)
show_intro = True
intro_counter = 0

while show_intro:
    win.fill(BLACK)
    win.blit(intro_text, (WIDTH//2 - intro_text.get_width()//2, HEIGHT//2 - 100))
    win.blit(author_text, (WIDTH//2 - author_text.get_width()//2, HEIGHT//2))
    pygame.display.update()
    intro_counter +=1
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); cap.release(); cv2.destroyAllWindows(); exit()
        elif event.type==pygame.KEYDOWN and event.key==pygame.K_RETURN:
            show_intro=False
    if intro_counter>180: # auto skip after 3 sec
        show_intro=False

while state["running"]:
    clock.tick(60)
    success, frame = cap.read()
    if not success:
        break
    frame = cv2.flip(frame,1)
    h,w,c = frame.shape
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)
    
    player = state["player"]
    player["shield"]=False
    
    # -------------------
    # Hand Control
    # -------------------
    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]  # single player
        index_tip = hand_landmarks.landmark[8]
        thumb_tip = hand_landmarks.landmark[4]
        px, py = int(index_tip.x*WIDTH), int(index_tip.y*HEIGHT)
        
        # Smooth movement
        if player["prev_x"] is not None:
            dx = px - player["prev_x"]
            dy = py - player["prev_y"]
            player["x"] += dx
            player["y"] += dy
        player["prev_x"], player["prev_y"] = px, py
        
        # Pinch distance for shooting
        pinch = math.hypot((index_tip.x - thumb_tip.x)*w,(index_tip.y - thumb_tip.y)*h)
        if pinch<40 and player["pinch_cooldown"]==0:
            state["bullets"].append({"x":player["x"],"y":player["y"],"trail":[]})
            if 'laser_sound' in globals(): laser_sound.play()
            player["pinch_cooldown"]=15
        if player["pinch_cooldown"]>0:
            player["pinch_cooldown"]-=1
        
        # Open palm for shield
        wrist = hand_landmarks.landmark[0]
        fingertips = [hand_landmarks.landmark[i] for i in [8,12,16,20]]
        if all(f.y < wrist.y for f in fingertips):
            player["shield"]=True
    
    # -------------------
    # Bullets movement
    # -------------------
    for b in state["bullets"][:]:
        b["trail"].append((b["x"], b["y"]))
        if len(b["trail"])>5: b["trail"].pop(0)
        b["y"]-=12
        if b["y"]<0: state["bullets"].remove(b)
    
    # -------------------
    # Enemy spawn & movement
    # -------------------
    state["enemy_spawn_timer"] +=1
    if state["enemy_spawn_timer"]>= max(30, 60 - state["level"]*2):
        state["enemy_spawn_timer"]=0
        spawn_enemy(state)
    
    for e in state["enemies"][:]:
        # Follow player if close
        dist = math.hypot(player["x"]-e["x"], player["y"]-e["y"])
        if dist<300:
            e["x"] += (player["x"]-e["x"])/50
            e["y"] += (player["y"]-e["y"])/50
        else:
            e["y"] += 3  # default move down
        
        # Enemy attack
        if enemy_attack_sound and random.random()<0.002:
            enemy_attack_sound.play()
        
        # Bullet collision
        for b in state["bullets"][:]:
            if e["x"]-20<b["x"]<e["x"]+20 and e["y"]-15<b["y"]<e["y"]+15:
                state["score"]+=1
                spawn_explosion(state, e["x"], e["y"])
                if explosion_sound: explosion_sound.play()
                if e["split"]:
                    state["enemies"].append({"x":e["x"]-30,"y":e["y"],"split":False})
                    state["enemies"].append({"x":e["x"]+30,"y":e["y"],"split":False})
                state["enemies"].remove(e)
                state["bullets"].remove(b)
                break
        
        # Player collision
        if e["y"]+15 >= player["y"] and abs(e["x"]-player["x"])<50 and not player["shield"]:
            player["life"]-=1
            spawn_explosion(state, player["x"], player["y"])
            state["enemies"].remove(e)
            if player["life"]<=0:
                state["running"]=False
    
    # -------------------
    # Particles
    # -------------------
    for p in state["particles"][:]:
        p[0]+=p[3]
        p[1]+=p[4]
        p[2]-=0.1
        if p[2]<=0: state["particles"].remove(p)
    
    # Gravity
    apply_gravity(state)
    
    draw_game(state)
    
    # -------------------
    # Event handling
    # -------------------
    for event in pygame.event.get():
        if event.type==pygame.QUIT:
            pygame.quit(); cap.release(); cv2.destroyAllWindows(); exit()
        elif event.type==pygame.KEYDOWN:
            if event.key==pygame.K_ESCAPE:
                pygame.quit(); cap.release(); cv2.destroyAllWindows(); exit()
