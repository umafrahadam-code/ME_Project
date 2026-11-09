# A Data-Budget-Aware and Explanation-Stable Lightweight Deep Learning Framework for Plant Disease Detection

M.E. project – a Flask web application that detects plant leaf diseases with a
lightweight **MobileNetV3-Small** model and explains every prediction with **Grad-CAM**.

| Item | Value |
|---|---|
| Dataset | PlantVillage – 54,305 images, 38 classes (leaf-group split 38,105 / 8,150 / 8,050) |
| Model | MobileNetV3-Small, 1.56 M parameters, 160 × 160 input, 6.4 MB checkpoint |
| Training budget | 40 % of the training set (15,240 images), 5 epochs, AdamW |
| Test accuracy | **98.30 %** (macro F1 97.74 %) |
| CPU latency | about 22 ms per image |
| Explanation stability | flip 98.4 % (r 0.947), brightness 99.5 % (r 0.993), rotation 10° 91.8 % (r 0.809) |

## Features
- Register / login / logout (salted password hashes, SQLite)
- Upload a leaf image → disease, confidence, top-5 classes and Grad-CAM heat map
- Low-confidence warning, upload validation (type, size, corrupt files)
- Printable per-prediction report and per-user history

## Run on Windows (one command)
Open PowerShell in the project folder and run:

```powershell
.\run_app.bat
```

It finds (or installs) Python 3.10–3.12, creates a virtual environment in
`%USERPROFILE%\.plantapp_venv`, installs the packages (first time only) and opens
<http://127.0.0.1:5000>. See **How_To_Run_The_App.pdf** for the full guide.

### Manual start
```bash
pip install -r requirements.txt
python app.py
```
Set the `PORT` environment variable to use a port other than 5000.

## Project structure
```
app.py                 Flask web application
src/                   training, evaluation, Grad-CAM, prediction, report builders
templates/, static/    web pages and style sheet
model_bundle/          trained model (model.pt), class list, preprocessing config
artifacts/metrics/     evaluation and stability results (JSON)
artifacts/screenshots/ application screenshots
figures/               design diagrams and result charts
tests/                 automated tests (python -m pytest tests -q)
```

## Retraining
Download PlantVillage into `dataset/PlantVillage`, then run the scripts in `src/`
(`train.py`, `evaluate.py`, `explanation_stability.py`).
