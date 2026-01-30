import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

import time
import tkinter as tk
from tkinter import messagebox

import cv2
import numpy as np
import pygame

SOUND_FILE = "fire_alarm.mp3"

MIN_FIRE_AREA = 600
MIN_FLICKER_CHANGE = 120
CONFIRM_FRAMES_ON = 5
CONFIRM_FRAMES_OFF = 5

MIN_BOX_AREA = 700          
LOG_EVERY_SECONDS = 1.0     


def center_window(root, width=700, height=380):
    root.update_idletasks()
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = (screen_w - width) // 2
    y = (screen_h - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")


def fire_mask_orange_yellow_only(hsv):
    lower = np.array([10, 90, 170])
    upper = np.array([45, 255, 255])
    return cv2.inRange(hsv, lower, upper)


def detect_loop():
    pygame.mixer.init()
    pygame.mixer.music.load(SOUND_FILE)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Camera not found / can't open.")
        return

    prev_mask = None
    fire_on_count = 0
    fire_off_count = 0
    alarm_playing = False

    last_log = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (960, 540))
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        mask = fire_mask_orange_yellow_only(hsv)

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel, iterations=1)

        fire_area = int(cv2.countNonZero(mask))

        flicker_change = 0
        if prev_mask is not None:
            diff = cv2.absdiff(prev_mask, mask)
            flicker_change = int(cv2.countNonZero(diff))
        prev_mask = mask.copy()

        fire_now = (fire_area >= MIN_FIRE_AREA) and (flicker_change >= MIN_FLICKER_CHANGE)

        if fire_now:
            fire_on_count += 1
            fire_off_count = 0
        else:
            fire_off_count += 1
            fire_on_count = 0

        fire_confirmed = fire_on_count >= CONFIRM_FRAMES_ON
        fire_gone = fire_off_count >= CONFIRM_FRAMES_OFF

        if fire_confirmed and not alarm_playing:
            pygame.mixer.music.play(-1)  
            alarm_playing = True

        if fire_gone and alarm_playing:
            pygame.mixer.music.stop()
            alarm_playing = False

        overlay = frame.copy()
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for c in contours:
            area = cv2.contourArea(c)
            if area < MIN_BOX_AREA:
                continue
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(overlay, (x, y), (x + w, y + h), (255, 255, 255), 2)
            cv2.putText(overlay, "", (x, max(20, y - 8)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        status = "ALARM" if alarm_playing else ("CHECKING" if fire_on_count > 0 else "OK")

        if alarm_playing:
            cv2.putText(overlay, "FIRE DETECTED!", (20, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 255), 4)

        cv2.putText(
            overlay,
            f"Area:{fire_area} Flicker:{flicker_change} ON:{fire_on_count} OFF:{fire_off_count}",
            (20, 520),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
        )

        cv2.imshow("Fire Detector (press Q to quit)", overlay)

        now = time.time()
        if now - last_log >= LOG_EVERY_SECONDS:
            print(f"[{status:8}] fire_area={fire_area} flicker={flicker_change} on={fire_on_count} off={fire_off_count}")
            last_log = now

        if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
            break

    pygame.mixer.music.stop()
    cap.release()
    cv2.destroyAllWindows()


def start_app(root):
    if not os.path.exists(SOUND_FILE):
        messagebox.showerror("Error", f"Audio file not found: {SOUND_FILE}")
        return

    root.destroy()   
    detect_loop()    


root = tk.Tk()
root.title("Fire Detector")
root.configure(bg="white")
center_window(root, 700, 380)

tk.Label(root, text="FIRE DETECTOR",
         font=("Arial", 28, "bold"),
         fg="#e74c3c", bg="white").pack(pady=(50, 10))

tk.Label(root, text="by AMIT DAS",
         font=("Arial", 14, "bold"),
         fg="#00a8ff", bg="white").pack(pady=(0, 20))

tk.Label(root, text="Click START to begin monitoring",
         font=("Arial", 11), fg="#666", bg="white").pack()

tk.Label(root, text="The detector will open camera preview and play the alarm on detection",
         font=("Arial", 10), fg="#777", bg="white").pack(pady=(4, 20))

tk.Button(root, text="START",
          font=("Arial", 12, "bold"),
          width=14, height=2,
          bg="#f1f2f6",
          command=lambda: start_app(root)).pack()

root.mainloop()
