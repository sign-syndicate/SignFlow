from __future__ import annotations

import os
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from core.pipeline import VisionPipeline


def main() -> int:
	model_path = PROJECT_ROOT / "models" / "yolov8n.pt"
	model_path.parent.mkdir(parents=True, exist_ok=True)

	print("[INFO] Starting SignFlow headless pipeline...")
	print(f"[INFO] Model path: {model_path}")
	print("[INFO] Press Ctrl+C to stop.")

	pipeline = VisionPipeline(model_path=model_path, monitor_index=1, conf=0.35)

	last_report = time.time()
	frames = 0

	def on_result(boxes):
		nonlocal last_report, frames
		frames += 1
		now = time.time()
		if now - last_report >= 1.0:
			print(f"[INFO] FPS: {frames:>2d} | persons: {len(boxes)}")
			frames = 0
			last_report = now

	try:
		pipeline.run(on_result=on_result, throttle_seconds=0.0)
	except KeyboardInterrupt:
		print("\n[INFO] Stopping pipeline...")
	finally:
		pipeline.stop()

	return 0


if __name__ == "__main__":
	raise SystemExit(main())