import cv2
import mediapipe as mp
import pygame
import random
import math
import numpy as np
import time

# ------------------------------
# MediaPipe Hand Tracking
# ------------------------------
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.6, min_tracking_confidence=0.6)

# ------------------------------
# Pygame setup
# ------------------------------
pygame.init()
win = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
pygame.display.set_caption("Air Space VR Shooter")

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
STAR_COLOR = (200,200,255)
PARTICLE_COLOR = (255,200,50)
BUTTON_COLOR = (50,150,255)
BUTTON_HOVER = (80,200,255)

# ------------------------------
# Load Sounds
# ------------------------------
pygame.mixer.init()
try:
    laser_sound = pygame.mixer.Sound("laser.wav")
    explosion_sound = pygame.mixer.Sound("explosion.wav")
    powerup_sound = pygame.mixer.Sound("powerup.wav")
    swipe_sound = pygame.mixer.Sound("swipe.wav")
    pygame.mixer.music.load("background.mp3")
    pygame.mixer.music.play(-1)
except:
    print("Sounds missing. Place laser.wav, explosion.wav, powerup.wav, swipe.wav, background.mp3")

# ------------------------------
# Game state
# ------------------------------
def create_state():
    return {
        "players": [{"x":WIDTH//3, "y":HEIGHT-60, "prev_x":None, "prev_y":None, "shield":False, "pinch_cooldown":0},
                    {"x":2*WIDTH//3, "y":HEIGHT-60, "prev_x":None, "prev_y":None, "shield":False, "pinch_cooldown":0}],
        "bullets": [],
        "enemies": [],
        "enemy_spawn_timer":0,
        "score":0,
        "particles":[],
        "powerups":[],
        "gravity_zones":[(WIDTH//2, HEIGHT//2, 100)],
        "running":True
    }

# Stars
stars = [[random.randint(0,WIDTH), random.randint(0,HEIGHT), random.randint(1,3)] for _ in range(120)]

# ------------------------------
# Drawing functions
# ------------------------------
def draw_game(state):
    win.fill(BLACK)
    # Stars warp
    for star in stars:
        pygame.draw.circle(win, STAR_COLOR, (star[0], star[1]), star[2])
        star[1]+=max(1, abs(state["players"][0]["x"] - state["players"][0]["prev_x"] if state["players"][0]["prev_x"] else 0)//10)
        if star[1]>HEIGHT:
            star[0]=random.randint(0,WIDTH)
            star[1]=0
            star[2]=random.randint(1,3)
    # Players
    for player in state["players"]:
        px, py = player["x"], player["y"]
        color = GREEN if not player["shield"] else BLUE
        pygame.draw.polygon(win, color, [(px, py),(px-30, py+40),(px+30, py+40)])
    # Bullets
    for b in state["bullets"]:
        pygame.draw.rect(win, YELLOW, (b["x"]-5,b["y"],10,20))
        for t in b.get("trail",[]):
            pygame.draw.circle(win, YELLOW, t, 3)
    # Enemies
    for e in state["enemies"]:
        pygame.draw.rect(win, RED, (e["x"],e["y"],40,30))
    # Particles
    for p in state["particles"]:
        pygame.draw.circle(win, PARTICLE_COLOR, (int(p[0]),int(p[1])), p[2])
    # Powerups
    for pu in state["powerups"]:
        pygame.draw.rect(win, BLUE, (pu[0], pu[1], 30,30))
    # Score
    score_text = font_small.render(f"Score: {state['score']}", True, WHITE)
    win.blit(score_text, (10,10))
    pygame.display.update()

# ------------------------------
# Physics functions
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

# ------------------------------
# Main loop
# ------------------------------
state = create_state()
while state["running"]:
    clock.tick(60)
    success, frame = cap.read()
    if not success:
        break
    frame = cv2.flip(frame,1)
    h,w,c = frame.shape
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)
    
    # Reset shields and gestures
    for player in state["players"]:
        player["shield"]=False
    
    if results.multi_hand_landmarks:
        for i, hand_landmarks in enumerate(results.multi_hand_landmarks[:2]):
            # Player control by hand
            index_tip = hand_landmarks.landmark[8]
            thumb_tip = hand_landmarks.landmark[4]
            px, py = int(index_tip.x*WIDTH), int(index_tip.y*HEIGHT)
            player = state["players"][i]
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
            
            # Open palm gesture for shield
            wrist = hand_landmarks.landmark[0]
            fingertips = [hand_landmarks.landmark[i] for i in [8,12,16,20]]
            if all(f.y < wrist.y for f in fingertips):
                player["shield"]=True
    
    # Move bullets
    for b in state["bullets"][:]:
        b["trail"].append((b["x"],b["y"]))
        if len(b["trail"])>5: b["trail"].pop(0)
        b["y"]-=12
        if b["y"]<0: state["bullets"].remove(b)
    
    # Spawn enemies dynamically
    state["enemy_spawn_timer"]+=1
    if state["enemy_spawn_timer"]>=max(20,50- state["score"]//5):
        state["enemy_spawn_timer"]=0
        ex=random.randint(0,WIDTH-40)
        state["enemies"].append({"x":ex,"y":0,"split":random.choice([False,True,False])})
    
    # Move enemies
    for e in state["enemies"][:]:
        # Follow closest player if too close
        closest_player = min(state["players"], key=lambda p: math.hypot(p["x"]-e["x"], p["y"]-e["y"]))
        dist = math.hypot(closest_player["x"]-e["x"], closest_player["y"]-e["y"])
        if dist<300:
            e["x"] += (closest_player["x"]-e["x"])/50
            e["y"] += (closest_player["y"]-e["y"])/50
        else:
            e["y"]+=5
        
        # Bullet collisions
        for b in state["bullets"][:]:
            if e["x"]<b["x"]<e["x"]+40 and e["y"]<b["y"]<e["y"]+30:
                state["score"]+=1
                spawn_explosion(state,e["x"]+20,e["y"]+15)
                if 'explosion_sound' in globals(): explosion_sound.play()
                if e["split"]:
                    state["enemies"].append({"x":e["x"]-20,"y":e["y"],"split":False})
                    state["enemies"].append({"x":e["x"]+20,"y":e["y"],"split":False})
                state["enemies"].remove(e)
                state["bullets"].remove(b)
                break
        # Player collision
        for player in state["players"]:
            if e["y"]+30>=player["y"] and abs(e["x"]+20-player["x"])<30 and not player["shield"]:
                state["running"]=False
    
    # Move particles
    for p in state["particles"][:]:
        p[0]+=p[3]
        p[1]+=p[4]
        p[2]-=0.1
        if p[2]<=0: state["particles"].remove(p)
    
    # Apply gravity
    apply_gravity(state)
    
    draw_game(state)
    
    for event in pygame.event.get():
        if event.type==pygame.QUIT:
            pygame.quit(); cap.release(); cv2.destroyAllWindows(); exit()
        elif event.type==pygame.KEYDOWN:
            if event.key==pygame.K_ESCAPE:
                pygame.quit(); cap.release(); cv2.destroyAllWindows(); exit()
