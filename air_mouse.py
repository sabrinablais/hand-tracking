import cv2
import mediapipe as mp
import pyautogui
import math
import numpy as np
import time

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)
screen_w, screen_h = pyautogui.size()

# Settings
smoothening = 7        # Cursor smoothness
dead_zone = 5          # Ignore tiny shakes
scroll_scale = 2       # Scroll speed
momentum_decay = 0.9   # Scroll momentum decay (0-1)

prev_x, prev_y = 0, 0
scroll_velocity = 0

with mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
) as hands:

    while True:
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        h, w, c = frame.shape
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(img_rgb)

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # --- Cursor control ---
            index_tip = hand_landmarks.landmark[8]
            x, y = int(index_tip.x * w), int(index_tip.y * h)

            screen_x = np.interp(x, (0, w), (0, screen_w))
            screen_y = np.interp(y, (0, h), (0, screen_h))

            dx = screen_x - prev_x
            dy = screen_y - prev_y

            if abs(dx) > dead_zone or abs(dy) > dead_zone:
                curr_x = prev_x + dx / smoothening
                curr_y = prev_y + dy / smoothening
                pyautogui.moveTo(curr_x, curr_y)
                prev_x, prev_y = curr_x, curr_y

            # --- Pinch for left click ---
            thumb_tip = hand_landmarks.landmark[4]
            thumb_x, thumb_y = int(thumb_tip.x * w), int(thumb_tip.y * h)
            pinch_distance = math.hypot(x - thumb_x, y - thumb_y)
            if pinch_distance < 40:
                pyautogui.click()

            # --- Fist for right click ---
            fingertips = [hand_landmarks.landmark[i] for i in [8, 12, 16, 20]]
            wrist = hand_landmarks.landmark[0]
            if all(f.y > wrist.y for f in fingertips):
                pyautogui.rightClick()

            # --- Two-finger scroll (index + middle) ---
            middle_tip = hand_landmarks.landmark[12]

            # Check if only index and middle fingers are up
            if index_tip.y < wrist.y and middle_tip.y < wrist.y:
                dy_scroll = y - prev_y
                if abs(dy_scroll) > 2:  # dead zone
                    scroll_velocity = -dy_scroll * scroll_scale
                    prev_y = y
            else:
                # Apply momentum when fingers not in scrolling position
                scroll_velocity *= momentum_decay

            if abs(scroll_velocity) > 0.5:
                pyautogui.scroll(int(scroll_velocity))

            # --- Thumbs up for double click ---
            thumb_tip_y = hand_landmarks.landmark[4].y
            thumb_base_y = hand_landmarks.landmark[2].y
            fingers_folded = all(f.y > wrist.y for f in [hand_landmarks.landmark[i] for i in [8,12,16,20]])
            if thumb_tip_y < thumb_base_y and fingers_folded:
                pyautogui.doubleClick()

        # --- Show camera feed ---
        cv2.imshow("Air Controller", frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
            break

cap.release()
cv2.destroyAllWindows()
