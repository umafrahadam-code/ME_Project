# -*- coding: utf-8 -*-
"""Evaluate the exported model bundle on the fixed test partition.

Writes artifacts/metrics/test_evaluation.json (accuracy, macro P/R/F1,
per-class P/R/F1/support, confusion matrix, CPU latency).

Usage:  python src/evaluate.py
"""
import csv
import json
import os
import time

import torch
from PIL import Image
from torchvision import transforms

from predict import ToTensorNoNumpy, load_bundle

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPLITS = os.path.join(ROOT, "dataset", "PlantVillage", "splits")
RAW = os.path.join(ROOT, "dataset", "PlantVillage", "raw", "color")
OUT = os.path.join(ROOT, "artifacts", "metrics", "test_evaluation.json")


def main():
    torch.set_num_threads(min(12, os.cpu_count() or 4))
    net, classes, cfg = load_bundle()
    idx = {c: i for i, c in enumerate(classes)}
    size = int(cfg["input_size"])
    tf = transforms.Compose([transforms.Resize(int(size * 1.15)),
                             transforms.CenterCrop(size), ToTensorNoNumpy(),
                             transforms.Normalize(cfg["mean"], cfg["std"])])
    with open(os.path.join(SPLITS, "split_manifest.csv"), encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["partition"] == "test"]

    n = len(classes)
    cm = [[0] * n for _ in range(n)]
    batch, xs, ys = 64, [], []

    def flush():
        with torch.no_grad():
            pred = net(torch.stack(xs)).argmax(1).tolist()
        for g, p in zip(ys, pred):
            cm[g][p] += 1
        xs.clear()
        ys.clear()

    for r in rows:
        with Image.open(os.path.join(RAW, r["class_name"], r["file_name"])) as im:
            xs.append(tf(im.convert("RGB")))
        ys.append(idx[r["class_name"]])
        if len(xs) == batch:
            flush()
    if xs:
        flush()

    per = {}
    for i, c in enumerate(classes):
        tp = cm[i][i]
        fp = sum(cm[j][i] for j in range(n)) - tp
        fn = sum(cm[i]) - tp
        p = tp / (tp + fp) if tp + fp else 0.0
        rcl = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * p * rcl / (p + rcl) if p + rcl else 0.0
        per[c] = {"precision": round(p, 4), "recall": round(rcl, 4),
                  "f1": round(f1, 4), "support": sum(cm[i])}

    # single-image CPU latency (warm, 1 thread pool as configured)
    x = xs or [tf(Image.new("RGB", (256, 256), "green"))]
    x1 = x[0].unsqueeze(0)
    with torch.no_grad():
        for _ in range(5):
            net(x1)
        t0 = time.perf_counter()
        for _ in range(50):
            net(x1)
    latency = (time.perf_counter() - t0) / 50 * 1000

    total = sum(map(sum, cm))
    res = {
        "test_images": total,
        "accuracy": round(sum(cm[i][i] for i in range(n)) / total, 4),
        "macro_precision": round(sum(v["precision"] for v in per.values()) / n, 4),
        "macro_recall": round(sum(v["recall"] for v in per.values()) / n, 4),
        "macro_f1": round(sum(v["f1"] for v in per.values()) / n, 4),
        "latency_ms_cpu": round(latency, 2),
        "parameters": sum(p.numel() for p in net.parameters()),
        "per_class": per,
        "classes": classes,
        "confusion_matrix": cm,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print("acc %.4f  P %.4f  R %.4f  F1 %.4f  latency %.1f ms"
          % (res["accuracy"], res["macro_precision"], res["macro_recall"],
             res["macro_f1"], latency))


if __name__ == "__main__":
    main()
