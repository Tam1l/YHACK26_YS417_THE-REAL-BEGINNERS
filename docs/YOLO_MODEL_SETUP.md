# YOLOv8 Model Setup

This project runs YOLOv8 Nano on the CPU by default. It needs the Python packages below and the `yolov8n.pt` model-weight file.

## 1. Install the Python packages

From the repository root, run:

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-yolo-cpu.txt
```

`requirements-yolo-cpu.txt` installs CPU-only PyTorch, TorchVision, Ultralytics, OpenCV, Pillow, and NumPy. CPU mode works on laptops without an NVIDIA GPU.

## 2. Download the model weights

The worker loads `yolov8n.pt`. On the first successful YOLO inference, Ultralytics downloads this file automatically if internet access is available. The file is approximately 6.5 MB.

To download it before the demo, run this once from the repository root:

```powershell
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt'); print('YOLOv8 Nano model is ready')"
```

Keep the resulting `yolov8n.pt` file in the repository root (or the worker's working directory). To use another model location, set `YOLO_MODEL_PATH` to its `.pt` file. For an offline demo, copy that file to every laptop or Docker image that will run a worker.

## 3. Verify YOLO locally

With Redis and the workers running, use the included image:

```powershell
python -m pytest -q tests/test_perception_policy.py
```

Then open `http://localhost:8501`, upload `example-yolo-bus.jpg`, and wait for the Vision Feed. You should see labels and boxes, followed by the perception safety action.

## 4. Docker deployment

The Docker worker needs the same dependencies and the `yolov8n.pt` file. Build and start the stack:

```powershell
docker compose up -d --build
docker compose ps
```

If the model was not included while building, the first inference inside the worker downloads it. For a predictable offline or judging demo, pre-download `yolov8n.pt` using step 2 before building the image, and include it in the image or mount it into `/app/yolov8n.pt`.

## 5. GPU option

The checked-in setup is CPU-first. For an NVIDIA GPU, replace the CPU PyTorch lines in `requirements-yolo-cpu.txt` with the PyTorch CUDA wheel versions that match the installed NVIDIA driver and CUDA runtime. Keep `ultralytics`, OpenCV, Pillow, and NumPy unchanged.

## What is downloaded

| Item | Why it is needed | Approximate size |
| --- | --- | --- |
| CPU PyTorch and TorchVision | Runs YOLO inference | Large; typically hundreds of MB |
| Ultralytics | YOLOv8 runtime and model loader | Small Python package |
| OpenCV / Pillow / NumPy | Decode images and draw/process detections | Tens of MB |
| `yolov8n.pt` | Pretrained COCO object detector | About 6.5 MB |

The model detects standard COCO categories such as `person`, `car`, `bus`, `truck`, `bicycle`, and `stop sign`. It does not need you to upload training photos for these built-in categories. Custom warehouse classes require a separately trained YOLO `.pt` model.
