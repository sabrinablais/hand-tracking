import pygame
import cv2
import mediapipe as mp
import random
import math
import numpy as np
import os
import time

# ----------------------------
# Hand Tracking Setup
# ----------------------------
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)
hands = mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

# ----------------------------
# Pygame Setup
# ----------------------------
pygame.init()
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
win = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Space Air: By Sabrina Blais (who should be sleeping by now...)")
clock = pygame.time.Clock()
FPS = 60

# ----------------------------
# Colors
# ----------------------------
BLACK = (0,0,0)
WHITE = (255,255,255)
RED = (255,0,0)
GREEN = (0,255,0)
BLUE = (0,150,255)
YELLOW = (255,255,0)
STAR_COLOR = (200,200,255)
PARTICLE_COLOR = (255,200,50)
MENU_BG = (20,20,40)
BUTTON_COLOR = (50,150,255)
BUTTON_HOVER = (80,200,255)

# ----------------------------
# Fonts
# ----------------------------
pygame.font.init()
font_large = pygame.font.SysFont("Arial", 100)
font_medium = pygame.font.SysFont("Arial", 60)
font_small = pygame.font.SysFont("Arial", 40)

# ----------------------------
# Asset Loading
# ----------------------------
ASSET_DIR = os.path.join(os.getcwd(), "space_game")
def load_image(filename, scale=None):
    path = os.path.join(ASSET_DIR, filename)
    img = pygame.image.load(path).convert_alpha()
    if scale:
        img = pygame.transform.scale(img, scale)
    return img

def load_sound(filename):
    path = os.path.join(ASSET_DIR, filename)
    return pygame.mixer.Sound(path)

# Player & enemy assets
player_img = load_image("ship.png", scale=(120,120))
enemy_img = load_image("enemy.png", scale=(80,80))
boss_img = load_image("boss.png", scale=(200,200))
heart_img = load_image("heart.png", scale=(50,50))

# Sounds
pygame.mixer.init()
laser_sounds = [load_sound("laser1.wav"), load_sound("laser12.wav"), load_sound("laser13.wav")]
explosion_sound = load_sound("laser12.wav")
enemy_attack_sound = load_sound("laser13.wav")
powerup_sound = load_sound("laser12.wav")
swipe_sound = load_sound("laser1.wav")
pygame.mixer.music.load(os.path.join(ASSET_DIR, "background.mp3"))
pygame.mixer.music.play(-1)

# ----------------------------
# Stars Background
# ----------------------------
NUM_STARS = 150
stars = [[random.randint(0,WIDTH), random.randint(0,HEIGHT), random.randint(1,3)] for _ in range(NUM_STARS)]

# ----------------------------
# Game State
# ----------------------------
class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.prev_x = None
        self.prev_y = None
        self.width = 120
        self.height = 120
        self.shield = False
        self.pinch_cooldown = 0
        self.health = 5
        self.bullets = []

class Enemy:
    def __init__(self, x, y, enemy_type="normal"):
        self.x = x
        self.y = y
        self.type = enemy_type
        self.width = 80
        self.height = 80
        self.split = random.choice([False, True, False])
        self.health = 1 if enemy_type=="normal" else 20
        self.bullets = []

class Bullet:
    def __init__(self, x, y, dx=0, dy=-12, owner="player"):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.owner = owner
        self.trail = []

class PowerUp:
    def __init__(self, x, y, type_="health"):
        self.x = x
        self.y = y
        self.type = type_
        self.width = 50
        self.height = 50

class Particle:
    def __init__(self, x, y, radius=3, dx=0, dy=0, color=PARTICLE_COLOR):
        self.x = x
        self.y = y
        self.radius = radius
        self.dx = dx
        self.dy = dy
        self.color = color

class GameState:
    def __init__(self, num_players=1):
        self.players = [Player(WIDTH//2, HEIGHT-150)]
        self.num_players = num_players
        if num_players==2:
            self.players.append(Player(WIDTH//3, HEIGHT-150))
        self.enemies = []
        self.enemy_spawn_timer = 0
        self.score = 0
        self.particles = []
        self.powerups = []
        self.gravity_zones = [(WIDTH//2, HEIGHT//2, 150)]
        self.running = True
        self.level = 1
        self.level_timer = 0
        self.boss_active = False
        self.menu_active = True
        self.character_selected = 0
        self.gesture_combo_timer = 0

# ----------------------------
# Drawing Functions
# ----------------------------
def draw_stars():
    for star in stars:
        pygame.draw.circle(win, STAR_COLOR, (star[0], star[1]), star[2])
        star[1]+=max(1, random.randint(0,2))
        if star[1]>HEIGHT:
            star[0]=random.randint(0,WIDTH)
            star[1]=0
            star[2]=random.randint(1,3)

def draw_players(state):
    for player in state.players:
        img_rect = player_img.get_rect(center=(player.x, player.y))
        win.blit(player_img, img_rect)
        # Draw shield
        if player.shield:
            pygame.draw.circle(win, BLUE, (int(player.x), int(player.y)), 70, 5)
        # Draw health hearts
        for i in range(player.health):
            win.blit(heart_img, (10+i*55, HEIGHT-60))

def draw_bullets(state):
    for player in state.players:
        for b in player.bullets:
            pygame.draw.rect(win, YELLOW, (b.x-5, b.y, 10, 20))
            for t in b.trail:
                pygame.draw.circle(win, YELLOW, t, 3)
    for e in state.enemies:
        for b in e.bullets:
            pygame.draw.rect(win, RED, (b.x-5, b.y, 10, 20))

def draw_enemies(state):
    for e in state.enemies:
        if e.type=="boss":
            rect = boss_img.get_rect(center=(e.x,e.y))
            win.blit(boss_img, rect)
        else:
            rect = enemy_img.get_rect(center=(e.x,e.y))
            win.blit(enemy_img, rect)

def draw_powerups(state):
    for pu in state.powerups:
        win.blit(heart_img, (pu.x, pu.y))

def draw_particles(state):
    for p in state.particles:
        pygame.draw.circle(win, p.color, (int(p.x), int(p.y)), int(p.radius))

def draw_score(state):
    text = font_small.render(f"Score: {state.score}", True, WHITE)
    win.blit(text, (10,10))

def draw_level_intro(state):
    if state.level_timer < 90:
        text = font_large.render(f"LEVEL {state.level}", True, YELLOW)
        win.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 - text.get_height()//2))
        state.level_timer +=1

# ----------------------------
# Physics & Particles
# ----------------------------
def apply_gravity(state):
    for gx,gy,r in state.gravity_zones:
        for player in state.players:
            for b in player.bullets:
                dx, dy = gx-b.x, gy-b.y
                dist = math.hypot(dx, dy)
                if dist<r:
                    b.x += dx/dist*0.5
                    b.y += dy/dist*0.5
        for e in state.enemies:
            for b in e.bullets:
                dx, dy = gx-b.x, gy-b.y
                dist = math.hypot(dx, dy)
                if dist<r:
                    b.x += dx/dist*0.3
                    b.y += dy/dist*0.3

def spawn_explosion(state, x, y):
    for _ in range(15):
        dx, dy = random.uniform(-2,2), random.uniform(-2,2)
        state.particles.append(Particle(x,y,random.randint(2,5),dx,dy))

# ----------------------------
# Enemy Spawn
# ----------------------------
def spawn_enemy(state):
    x = random.randint(50, WIDTH-50)
    enemy_type = "boss" if state.level %5 == 0 and not state.boss_active else "normal"
    e = Enemy(x, 0, enemy_type)
    if enemy_type=="boss":
        state.boss_active=True
        e.health=50
    state.enemies.append(e)

# ----------------------------
# Gesture / Hand Controls
# ----------------------------
def hand_control(state, frame):
    h,w,c = frame.shape
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)

    if results.multi_hand_landmarks:
        for i, hand_landmarks in enumerate(results.multi_hand_landmarks[:state.num_players]):
            player = state.players[i]
            index_tip = hand_landmarks.landmark[8]
            thumb_tip = hand_landmarks.landmark[4]
            # Map hand coords to screen
            px, py = int(index_tip.x*WIDTH), int(index_tip.y*HEIGHT)
            if player.prev_x is not None:
                dx = px - player.prev_x
                dy = py - player.prev_y
                player.x += dx
                player.y += dy
            player.prev_x, player.prev_y = px, py
            # Pinch to shoot
            pinch_dist = math.hypot((index_tip.x - thumb_tip.x)*w, (index_tip.y - thumb_tip.y)*h)
            if pinch_dist<40 and player.pinch_cooldown==0:
                b = Bullet(player.x, player.y)
                player.bullets.append(b)
                random.choice(laser_sounds).play()
                player.pinch_cooldown=15
            if player.pinch_cooldown>0:
                player.pinch_cooldown-=1
            # Open hand for shield
            wrist = hand_landmarks.landmark[0]
            fingertips = [hand_landmarks.landmark[j] for j in [8,12,16,20]]
            if all(f.y < wrist.y for f in fingertips):
                player.shield=True

# ----------------------------
# Main Game Loop
# ----------------------------
state = GameState(num_players=1)
spawn_timer = 0

while True:
    clock.tick(FPS)
    success, frame = cap.read()
    if not success:
        continue
    frame = cv2.flip(frame,1)
    if not state.menu_active:
        hand_control(state, frame)

    # Update Stars
    draw_stars()

    # Level Intro
    draw_level_intro(state)

    # Spawn Enemies
    spawn_timer+=1
    if spawn_timer>=max(60,50 - state.level*2):
        spawn_timer=0
        spawn_enemy(state)

    # Update bullets
    for player in state.players:
        for b in player.bullets[:]:
            b.trail.append((b.x,b.y))
            if len(b.trail)>5: b.trail.pop(0)
            b.y += b.dy
            if b.y<0: player.bullets.remove(b)

    # Move enemies
    for e in state.enemies[:]:
        e.y += 2 + state.level*0.2
        # Boss attacks
        if e.type=="boss" and random.randint(0,50)==0:
            eb = Bullet(e.x, e.y, dy=8, owner="enemy")
            e.bullets.append(eb)
            enemy_attack_sound.play()
        # Collision with bullets
        for player in state.players:
            for b in player.bullets[:]:
                if abs(b.x-e.x)<e.width//2 and abs(b.y-e.y)<e.height//2:
                    e.health-=1
                    spawn_explosion(state, e.x, e.y)
                    if b in player.bullets: player.bullets.remove(b)
                    if e.health<=0:
                        state.enemies.remove(e)
                        state.score+=5 if e.type=="boss" else 1
                        break
        # Collision with player
        for player in state.players:
            if abs(player.x - e.x)<e.width//2 and abs(player.y - e.y)<e.height//2 and not player.shield:
                player.health-=1
                spawn_explosion(state, player.x, player.y)
                state.enemies.remove(e)
                if player.health<=0:
                    state.running=False

    # Draw everything
    draw_players(state)
    draw_bullets(state)
    draw_enemies(state)
    draw_powerups(state)
    draw_particles(state)
    draw_score(state)

    # Event Handling
    for event in pygame.event.get():
        if event.type==pygame.QUIT:
            pygame.quit(); cap.release(); cv2.destroyAllWindows(); exit()
        elif event.type==pygame.KEYDOWN:
            if event.key==pygame.K_ESCAPE:
                pygame.quit(); cap.release(); cv2.destroyAllWindows(); exit()

    pygame.display.update()
