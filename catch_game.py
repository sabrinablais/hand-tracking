import cv2
import mediapipe as mp
import pyautogui
import pygame
import random
import time

# ------------------------------
# Setup MediaPipe
# ------------------------------
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

# ------------------------------
# Setup Pygame
# ------------------------------
pygame.init()
WIDTH, HEIGHT = 800, 600
win = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Catch the Objects")

clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 30)

# Player
player_w, player_h = 100, 20
player_x = WIDTH // 2 - player_w // 2
player_y = HEIGHT - player_h - 10
player_speed = 10

# Objects
objects = []
spawn_timer = 0
spawn_interval = 60  # frames
object_radius = 20
object_speed = 5

# Score
score = 0
missed = 0
max_missed = 5

# ------------------------------
# Helper function
# ------------------------------
def draw_game():
    win.fill((30, 30, 30))
    # Draw player
    pygame.draw.rect(win, (0, 200, 0), (player_x, player_y, player_w, player_h))
    # Draw objects
    for obj in objects:
        pygame.draw.circle(win, (200, 0, 0), (obj[0], obj[1]), object_radius)
    # Draw score
    text = font.render(f"Score: {score}  Missed: {missed}", True, (255, 255, 255))
    win.blit(text, (10, 10))
    pygame.display.update()

# ------------------------------
# Game loop
# ------------------------------
running = True
prev_x = None

while running:
    clock.tick(60)
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    h, w, c = frame.shape
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)

    hand_x = None

    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]
        mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        index_tip = hand_landmarks.landmark[8]
        middle_tip = hand_landmarks.landmark[12]
        wrist = hand_landmarks.landmark[0]

        # Map hand x-position to player movement
        hand_x = int(index_tip.x * WIDTH)

        # Optional: pinch to speed up
        thumb_tip = hand_landmarks.landmark[4]
        thumb_x, thumb_y = int(thumb_tip.x * w), int(thumb_tip.y * h)
        pinch_distance = ((index_tip.x * w - thumb_x) ** 2 + (index_tip.y * h - thumb_y) ** 2) ** 0.5
        speed_multiplier = 2 if pinch_distance < 40 else 1

        if prev_x is not None:
            dx = hand_x - prev_x
            player_x += int(dx * speed_multiplier)
        prev_x = hand_x

    # Keep player inside screen
    if player_x < 0: player_x = 0
    if player_x > WIDTH - player_w: player_x = WIDTH - player_w

    # Spawn objects
    spawn_timer += 1
    if spawn_timer >= spawn_interval:
        spawn_timer = 0
        obj_x = random.randint(object_radius, WIDTH - object_radius)
        objects.append([obj_x, 0])

    # Move objects
    for obj in objects[:]:
        obj[1] += object_speed
        # Check collision with player
        if player_y < obj[1] + object_radius < player_y + player_h and player_x < obj[0] < player_x + player_w:
            score += 1
            objects.remove(obj)
        elif obj[1] > HEIGHT:
            missed += 1
            objects.remove(obj)

    draw_game()

    # Quit events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    if missed >= max_missed:
        running = False

pygame.quit()
cap.release()
cv2.destroyAllWindows()
