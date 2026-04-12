# SignFlow — System Architecture

## Overview

SignFlow is a real-time pipeline that converts sign language into readable English captions using computer vision and sequence modeling, delivered through a low-latency desktop overlay.

---

## End-to-End Flow

Input (Screen/Webcam)  
→ Landmark Extraction (MediaPipe)  
→ Feature Processing  
→ Model Inference (Local/API)  
→ Token Output  
→ Post-processing (Smoothing)  
→ Overlay Display (PyQt)

---

## Components

### 1. Capture Layer
- Captures frames from a selected screen region or webcam  
- Designed for flexible input sources  
- Optimized for low-latency frame acquisition  

### 2. Landmark Extraction
- Uses MediaPipe to extract 3D hand landmarks  
- Converts frames into structured spatial data  
- Reduces input complexity for the model  

### 3. Feature Processing
- Normalizes landmark coordinates into feature vectors  
- Handles temporal sequencing (frame windows)  
- Prepares input for model inference  

### 4. Model Inference
- Transformer-based sequence model  
- Predicts discrete sign tokens  
- Supports local and API-based inference  

### 5. Post-processing
- Converts tokens into readable English  
- Applies smoothing to reduce jitter  
- Improves caption stability  

### 6. Overlay UI
- PyQt-based desktop overlay  
- Displays captions in real time  
- Non-intrusive and always visible  

---

## Design Principles

- Low latency first (<100ms target)  
- Modular architecture (easy to swap components)  
- API-first evolution (scalable inference layer)  
- Works as a universal overlay (platform-agnostic)  

---

## Current Limitations

- Limited vocabulary (prototype stage)  
- Basic temporal modeling  
- Dependent on clear hand visibility  
- No full contextual understanding yet  

---

## Future Improvements

- Larger vocabulary and dataset  
- Context-aware sequence modeling  
- Camera-based input support  
- Production-grade inference API  
- SDK for external integrations  