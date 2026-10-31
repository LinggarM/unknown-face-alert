import cv2
import os
import numpy as np
import urllib.request

DATASET_DIR = "dataset"
CASCADE_FILE = "haarcascade_frontalface_default.xml"
CASCADE_URL = "https://raw.githubusercontent.com/opencv/opencv/4.x/data/haarcascades/haarcascade_frontalface_default.xml"

# Download otomatis jika file belum ada di folder project
if not os.path.exists(CASCADE_FILE):
    print(f"File {CASCADE_FILE} tidak ditemukan. Mengunduh dari GitHub...")
    try:
        urllib.request.urlretrieve(CASCADE_URL, CASCADE_FILE)
        print("✅ Download selesai.")
    except Exception as e:
        print(f"❌ Gagal mengunduh: {e}")
        exit(1)

cascade_path = os.path.abspath(CASCADE_FILE)
face_cascade = cv2.CascadeClassifier(cascade_path)

if face_cascade.empty():
    raise Exception(f"Gagal memuat Haar Cascade dari: {cascade_path}")

faces = []
ids = []
labels = {}
current_id = 0

print("Memulai proses training dari dataset...")
for person_name in os.listdir(DATASET_DIR):
    person_dir = os.path.join(DATASET_DIR, person_name)
    if os.path.isdir(person_dir):
        labels[current_id] = person_name
        for image_file in os.listdir(person_dir):
            image_path = os.path.join(person_dir, image_file)
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                print(f"  ⚠️ Gagal membaca gambar: {image_path}")
                continue
            
            detected = face_cascade.detectMultiScale(img, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            if len(detected) == 0:
                print(f"  ⚠️ Tidak ada wajah terdeteksi di: {image_path}")
                continue
                
            for (x, y, w, h) in detected:
                roi = img[y:y+h, x:x+w]
                roi = cv2.resize(roi, (150, 150))
                faces.append(roi)
                ids.append(current_id)
        current_id += 1

if len(faces) > 0:
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(ids))
    recognizer.write("trainer.yml")
    
    with open("labels.txt", "w", encoding="utf-8") as f:
        for id_num, name in labels.items():
            f.write(f"{id_num}:{name}\n")
            
    print(f"\n✅ Training selesai! {len(faces)} wajah berhasil diproses.")
    print("File 'trainer.yml' dan 'labels.txt' telah dibuat.")
else:
    print("\n❌ Gagal: Tidak ada wajah yang terdeteksi di folder dataset.")
    print("Pastikan foto wajah jelas, tidak terlalu gelap, dan menghadap depan.")