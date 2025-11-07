import cv2
import mediapipe as mp
import math
import numpy as np

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)
canvas = None

# Colors
draw_color = (0, 0, 255)  # Red
clear_color = (0, 0, 0)   # Black

with mp_hands.Hands(
    max_num_hands=1,  # We'll use one hand for drawing
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
) as hands:
    prev_x, prev_y = 0, 0  # Previous finger coordinates

    while True:
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        if canvas is None:
            canvas = np.zeros_like(frame)

        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(img_rgb)

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]  # Only one hand
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            h, w, c = frame.shape
            thumb_tip = hand_landmarks.landmark[4]
            index_tip = hand_landmarks.landmark[8]

            x1, y1 = int(thumb_tip.x * w), int(thumb_tip.y * h)
            x2, y2 = int(index_tip.x * w), int(index_tip.y * h)

            # Draw a line between thumb and index
            cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Calculate distance
            distance = math.hypot(x2 - x1, y2 - y1)

            # Pinch to draw
            if distance < 40:
                if prev_x == 0 and prev_y == 0:
                    prev_x, prev_y = x2, y2
                cv2.line(canvas, (prev_x, prev_y), (x2, y2), draw_color, 5)
                prev_x, prev_y = x2, y2
            else:
                prev_x, prev_y = 0, 0

            # Fist to clear screen
            fingertips = [hand_landmarks.landmark[i] for i in [8,12,16,20]]
            wrist = hand_landmarks.landmark[0]
            if all(f.y > wrist.y for f in fingertips):
                canvas[:] = clear_color  # Clear canvas
                cv2.putText(frame, "CLEARED!", (50,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 3)

        # Combine camera and drawing
        frame = cv2.addWeighted(frame, 0.5, canvas, 0.5, 0)
        cv2.imshow("Air Drawing", frame)

        if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
            break

cap.release()
cv2.destroyAllWindows()
