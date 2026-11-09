# -*- coding: utf-8 -*-
"""Explanation-stability analysis of Grad-CAM under label-preserving views.

For a stratified sample of test images (N per class) the original image x and a
transformed view T(x) are explained for the class predicted on x. The view's
map is mapped back to the original geometry, then compared with:
  * Pearson correlation of the two 5x5 -> 160x160 maps
  * IoU of the top-20 % most activated pixels
Prediction agreement (same top-1 on x and T(x)) is recorded as well.

Writes artifacts/metrics/explanation_stability.json
Usage:  python src/explanation_stability.py --per-class 10
"""
import argparse
import csv
import json
import os
import random

import torch
import torch.nn.functional as F
from PIL import Image, ImageEnhance
from torchvision import transforms

from gradcam import GradCAM
from predict import ToTensorNoNumpy, load_bundle

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "dataset", "PlantVillage", "raw", "color")
SPLITS = os.path.join(ROOT, "dataset", "PlantVillage", "splits")
OUT = os.path.join(ROOT, "artifacts", "metrics", "explanation_stability.json")

VIEWS = {
    "horizontal_flip": (lambda im: im.transpose(Image.FLIP_LEFT_RIGHT),
                        lambda cam: torch.flip(cam, dims=[1])),
    "brightness_+15%": (lambda im: ImageEnhance.Brightness(im).enhance(1.15),
                        lambda cam: cam),
    "rotation_10deg": (lambda im: im.rotate(10, resample=Image.BILINEAR),
                       None),  # inverse applied on the upsampled map below
}


def up(cam, size):
    return F.interpolate(cam[None, None], size=(size, size), mode="bilinear",
                         align_corners=False)[0, 0]


def pearson(a, b):
    a, b = a.flatten() - a.mean(), b.flatten() - b.mean()
    d = a.norm() * b.norm()
    return float((a @ b) / d) if d > 0 else 0.0


def top_iou(a, b, q=0.8):
    ma, mb = a >= torch.quantile(a, q), b >= torch.quantile(b, q)
    return float((ma & mb).sum()) / max(1, float((ma | mb).sum()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-class", type=int, default=10)
    a = ap.parse_args()
    random.seed(42)
    net, classes, cfg = load_bundle()
    size = int(cfg["input_size"])
    prep = transforms.Compose([transforms.Resize(int(size * 1.15)), transforms.CenterCrop(size)])
    tt = transforms.Compose([ToTensorNoNumpy(), transforms.Normalize(cfg["mean"], cfg["std"])])
    cam = GradCAM(net)

    with open(os.path.join(SPLITS, "split_manifest.csv"), encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["partition"] == "test"]
    by_cls = {}
    for r in rows:
        by_cls.setdefault(r["class_name"], []).append(r)
    sample = []
    for c in sorted(by_cls):
        sample += random.sample(by_cls[c], min(a.per_class, len(by_cls[c])))

    stats = {k: {"pearson": [], "iou": [], "agree": []} for k in VIEWS}
    for r in sample:
        with Image.open(os.path.join(RAW, r["class_name"], r["file_name"])) as im:
            img = prep(im.convert("RGB"))
        c0, p0 = cam(tt(img).unsqueeze(0))
        k = int(p0.argmax())
        m0 = up(c0, size)
        for name, (fwd, inv) in VIEWS.items():
            v = fwd(img)
            c1, p1 = cam(tt(v).unsqueeze(0), class_idx=k)
            m1 = up(c1, size)
            if inv is not None:
                m1 = inv(m1)
            else:  # undo the 10 degree rotation on the map
                pil = Image.fromarray((m1.clamp(0, 1) * 255).byte().numpy())
                m1 = torch.tensor(list(pil.rotate(-10, resample=Image.BILINEAR).getdata()),
                                  dtype=torch.float32).view(size, size) / 255.0
            s = stats[name]
            s["pearson"].append(pearson(m0, m1))
            s["iou"].append(top_iou(m0, m1))
            s["agree"].append(int(int(p1.argmax()) == k))

    res = {"images": len(sample), "per_class": a.per_class, "views": {}}
    for name, s in stats.items():
        n = len(s["agree"])
        res["views"][name] = {
            "prediction_agreement": round(sum(s["agree"]) / n, 4),
            "mean_pearson": round(sum(s["pearson"]) / n, 4),
            "mean_top20_iou": round(sum(s["iou"]) / n, 4),
        }
        print("%-16s agree %.3f  pearson %.3f  IoU %.3f" % (
            name, *res["views"][name].values()))
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)


if __name__ == "__main__":
    main()
