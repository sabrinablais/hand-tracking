import cv2
import mediapipe as mp
import pygame
import numpy as np

pygame.init()
screen_width, screen_height = 800, 600  # start windowed
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Eye Tracker Debug")

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1)

cap = cv2.VideoCapture(0)

prev_dot = np.array([screen_width//2, screen_height//2], dtype=float)
SMOOTH_ALPHA = 0.5

def get_iris_position(landmarks, w, h):
    try:
        # Using landmark 468 for right iris center
        iris = landmarks[468]
        return np.array([iris.x * w, iris.y * h])
    except:
        return None

running = True
while running:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    iris_pos = None
    if results.multi_face_landmarks:
        lm = results.multi_face_landmarks[0].landmark
        iris_pos = get_iris_position(lm, w, h)

    if iris_pos is not None:
        # Smooth movement
        prev_dot = SMOOTH_ALPHA * prev_dot + (1 - SMOOTH_ALPHA) * iris_pos
    dot = prev_dot

    screen.fill((0, 0, 0))
    pygame.draw.circle(screen, (255, 0, 0), dot.astype(int), 20)
    pygame.display.flip()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_q:
            running = False

cap.release()
pygame.quit()
