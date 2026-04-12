# SignFlow — Real-Time Sign Language to Text

SignFlow converts sign language into English captions in real time using a low-latency pipeline and a lightweight desktop overlay.

---

## How it works

Pipeline:
Capture → Landmarks → Features → Model → Text → Overlay

- MediaPipe for hand landmark extraction  
- Transformer-based model for token prediction  
- Post-processing for smoother captions  
- PyQt overlay for real-time display  

---

## Run locally

```bash
git clone https://github.com/sign-syndicate/signflow.git
cd signflow
pip install -r requirements.txt

python scripts/run_proto.py