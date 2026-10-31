import ctypes
import cv2
import time
import os
import tkinter as tk
from PIL import Image, ImageTk
import pygame
from datetime import datetime
from pygrabber.dshow_graph import FilterGraph

# --- KONFIGURASI ---
COOLDOWN = 5  # Detik cooldown sebelum alert berikutnya
SCREENSHOT_MAX_AGE_HOURS = 24
CLEANUP_INTERVAL_SECONDS = 3600
WINDOW_WIDTH = 1366
WINDOW_HEIGHT = 768
SCREENSHOT_DIR = "screenshots"
LOG_DIR = "logs"
ALERT_SOUND = "alert.wav"
THRESHOLD_KONFIDENSI = 60  # Semakin rendah semakin ketat. >60 dianggap "Unknown"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# --- LOAD MODEL WAJAH ---
if not os.path.exists("trainer.yml") or not os.path.exists("labels.txt"):
    raise Exception("File 'trainer.yml' atau 'labels.txt' tidak ditemukan. Jalankan 'train.py' terlebih dahulu!")

recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read("trainer.yml")

labels = {}
with open("labels.txt", "r", encoding="utf-8") as f:
    for line in f:
        id_num, name = line.strip().split(":", 1)
        labels[int(id_num)] = name

face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
print(f"✅ Model dimuat. Dikenal: {list(labels.values())}")

# --- FUNGSI KAMERA ---
def get_camera_index_by_name(target_name_part):
    graph = FilterGraph()
    devices = graph.get_input_devices()
    print("=== Daftar Kamera Terdeteksi ===")
    for i, name in enumerate(devices):
        print(f"  [{i}] {name}")
        if target_name_part.lower() in name.lower():
            print(f"✅ Kamera target ditemukan: '{name}' di indeks {i}")
            return i
    return None

TARGET_CAMERA_NAME = "FHD Camera" # Ganti sesuai nama webcam Anda
CAMERA_INDEX = get_camera_index_by_name(TARGET_CAMERA_NAME)
if CAMERA_INDEX is None:
    raise Exception(f"Kamera '{TARGET_CAMERA_NAME}' tidak ditemukan.")

cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
if not cap.isOpened():
    raise Exception("Webcam gagal dibuka.")
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# --- SETUP AUDIO ---
pygame.mixer.init()
alert_sound = pygame.mixer.Sound(ALERT_SOUND) if os.path.exists(ALERT_SOUND) else None

# --- VARIABEL GLOBAL ---
last_alert = 0
DETECTOR_ACTIVE = True
topmost_until = 0

# --- FUNGSI ALERT & LOG ---
def play_alert():
    if alert_sound: alert_sound.play()

def save_screenshot(frame):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(SCREENSHOT_DIR, f"unknown_{timestamp}.jpg")
    cv2.imwrite(filepath, frame)
    return filepath

def write_log(screenshot_path=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_filepath = os.path.join(LOG_DIR, f"detector_log_{datetime.now().strftime('%Y%m%d')}.txt")
    log_entry = f"[{timestamp}] Wajah tidak dikenal terdeteksi!"
    if screenshot_path: log_entry += f" | Screenshot: {screenshot_path}"
    with open(log_filepath, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

def cleanup_old_screenshots():
    now = time.time()
    max_age_seconds = SCREENSHOT_MAX_AGE_HOURS * 3600
    deleted = 0
    for fname in os.listdir(SCREENSHOT_DIR):
        fpath = os.path.join(SCREENSHOT_DIR, fname)
        if os.path.isfile(fpath) and (now - os.path.getmtime(fpath) > max_age_seconds):
            try: os.remove(fpath); deleted += 1
            except: pass
    if deleted > 0: print(f"[Cleanup] {deleted} screenshot lama dihapus.")

def schedule_cleanup():
    cleanup_old_screenshots()
    root.after(CLEANUP_INTERVAL_SECONDS * 1000, schedule_cleanup)

# --- SETUP TKINTER ---
root = tk.Tk()
root.title("Unknown Face Alert")
root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
label = tk.Label(root)
label.pack()

BTN_X1, BTN_Y1 = WINDOW_WIDTH - 160, 20
BTN_X2, BTN_Y2 = WINDOW_WIDTH - 20, 70

def bring_to_front():
    global topmost_until
    root.lift()
    root.attributes('-topmost', True)
    try:
        hwnd = ctypes.windll.user32.FindWindowW(None, "Unknown Face Alert")
        if hwnd:
            user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
            fg_hwnd = user32.GetForegroundWindow()
            fg_tid = user32.GetWindowThreadProcessId(fg_hwnd, None)
            cur_tid = kernel32.GetCurrentThreadId()
            if fg_tid != cur_tid:
                user32.AttachThreadInput(cur_tid, fg_tid, True)
                user32.BringWindowToTop(hwnd); user32.SetForegroundWindow(hwnd)
                user32.SetActiveWindow(hwnd); user32.AttachThreadInput(cur_tid, fg_tid, False)
            else:
                user32.SetForegroundWindow(hwnd)
            user32.ShowWindow(hwnd, 9)
    except: root.focus_force()
    topmost_until = time.time() + 2

def toggle_detector():
    global DETECTOR_ACTIVE
    DETECTOR_ACTIVE = not DETECTOR_ACTIVE
    print(f">>> Detector {'ON' if DETECTOR_ACTIVE else 'OFF'} <<<")

def on_label_click(event):
    if BTN_X1 <= event.x <= BTN_X2 and BTN_Y1 <= event.y <= BTN_Y2: toggle_detector()

def on_key_press(event):
    if event.keysym.lower() == 'p': toggle_detector()

label.bind('<Button-1>', on_label_click)
root.bind('<Key>', on_key_press)
print("Sistem aktif. Tekan 'P' atau klik tombol ON/OFF di pojok kanan atas.\n")

# --- MAIN LOOP ---
def process_frame():
    global last_alert
    ret, frame = cap.read()
    if not ret:
        root.after(30, process_frame)
        return

    current_time = time.time()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Deteksi wajah
    faces_detected = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
    
    unknown_detected = False

    for (x, y, w, h) in faces_detected:
        roi_gray = gray[y:y+h, x:x+w]
        roi_gray = cv2.resize(roi_gray, (150, 150)) # Harus sama dengan ukuran saat training
        
        # Prediksi wajah
        id_pred, confidence = recognizer.predict(roi_gray)
        
        # LBPH: Confidence 0 = perfect match. Semakin tinggi semakin tidak mirip.
        if confidence < THRESHOLD_KONFIDENSI and id_pred in labels:
            name = labels[id_pred]
            color = (0, 255, 0) # Hijau untuk dikenal
        else:
            name = "Wajah Tidak Diketahui"
            color = (0, 0, 255) # Merah untuk tidak dikenal
            unknown_detected = True

        # Gambar kotak dan label
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        cv2.rectangle(frame, (x, y+h-35), (x+w, y+h), color, cv2.FILLED)
        cv2.putText(frame, name, (x+6, y+h-10), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)
        # Opsional: tampilkan angka confidence untuk debugging
        # cv2.putText(frame, f"Conf: {int(confidence)}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    # Trigger alert jika ada wajah tidak dikenal
    if unknown_detected and DETECTOR_ACTIVE:
        if current_time - last_alert > COOLDOWN:
            bring_to_front()
            screenshot_path = save_screenshot(frame)
            write_log(screenshot_path)
            print(f">>> PERINGATAN: Wajah tidak dikenal terdeteksi! <<<")
            play_alert()
            last_alert = current_time
        
        # Border merah kedip di seluruh frame
        cv2.rectangle(frame, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 255), 10)
        cv2.putText(frame, "UNKNOWN FACE DETECTED!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4)

    # Overlay jika OFF
    if not DETECTOR_ACTIVE:
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
        cv2.putText(frame, "DETECTOR OFF", (frame.shape[1] // 2 - 250, frame.shape[1] // 2), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 0, 255), 6)

    # Resize & render ke Tkinter
    frame_resized = cv2.resize(frame, (WINDOW_WIDTH, WINDOW_HEIGHT))
    frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)

    btn_color = (0, 180, 0) if DETECTOR_ACTIVE else (0, 0, 200)
    cv2.rectangle(frame_rgb, (BTN_X1, BTN_Y1), (BTN_X2, BTN_Y2), btn_color, -1)
    cv2.rectangle(frame_rgb, (BTN_X1, BTN_Y1), (BTN_X2, BTN_Y2), (255, 255, 255), 2)
    cv2.putText(frame_rgb, "ON" if DETECTOR_ACTIVE else "OFF", (BTN_X1 + 45, BTN_Y1 + 35), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)

    imgtk = ImageTk.PhotoImage(image=Image.fromarray(frame_rgb))
    label.imgtk = imgtk
    label.configure(image=imgtk)
    root.after(30, process_frame)

# Jalankan
cleanup_old_screenshots()
schedule_cleanup()
process_frame()
root.mainloop()
cap.release()