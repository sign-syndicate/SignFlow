import argparse
import sys
import time
from pathlib import Path

import cv2
import torch
from ultralytics import YOLO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "yolov8n.pt"

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Robust YOLOv8 camera test (download + live inference)."
    )
    parser.add_argument(
        "--model",
        type=str,
        default=str(DEFAULT_MODEL_PATH),
        help="YOLO model path (default: models/yolov8n.pt).",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Camera index (default: 0).",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1280,
        help="Requested camera width.",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=720,
        help="Requested camera height.",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.35,
        help="Confidence threshold for detections.",
    )
    parser.add_argument(
        "--retry",
        type=int,
        default=3,
        help="How many camera open retries before failing.",
    )
    return parser.parse_args()


def open_camera_with_retries(index: int, width: int, height: int, retries: int) -> cv2.VideoCapture:
    last_error = ""
    for attempt in range(1, retries + 1):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return cap

        cap.release()
        last_error = f"Camera index {index} did not open (attempt {attempt}/{retries})."
        time.sleep(0.8)

    raise RuntimeError(last_error)


def main() -> int:
    args = parse_args()
    model_path = Path(args.model).expanduser().resolve()
    model_path.parent.mkdir(parents=True, exist_ok=True)

    # Force deterministic inference target to avoid unexpected CUDA issues.
    device = "cpu"

    print("[INFO] Python:", sys.version.split()[0])
    print("[INFO] Torch:", torch.__version__)
    print("[INFO] Loading model:", model_path)

    try:
        model = YOLO(str(model_path))
    except Exception as exc:
        print(f"[ERROR] Failed to load YOLO model '{model_path}': {exc}")
        return 1

    try:
        cap = open_camera_with_retries(args.camera, args.width, args.height, args.retry)
    except Exception as exc:
        print(f"[ERROR] Failed to open camera: {exc}")
        return 1

    print("[INFO] Camera opened. Press 'q' to exit.")

    prev_time = time.time()
    fps = 0.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                print("[WARN] Empty frame received; retrying.")
                time.sleep(0.02)
                continue

            results = model.predict(
                source=frame,
                conf=args.conf,
                verbose=False,
                device=device,
            )

            rendered = results[0].plot()

            now = time.time()
            dt = now - prev_time
            if dt > 0:
                fps = 1.0 / dt
            prev_time = now

            cv2.putText(
                rendered,
                f"YOLOv8 Test | FPS: {fps:.1f}",
                (15, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow("SignFlow YOLO Camera Test", rendered)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user.")
    except Exception as exc:
        print(f"[ERROR] Runtime failure: {exc}")
        return 1
    finally:
        cap.release()
        cv2.destroyAllWindows()

    print("[INFO] Test completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
