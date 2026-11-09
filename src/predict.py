# -*- coding: utf-8 -*-
"""Run a single-image prediction with the exported model bundle.

Usage:
  python src/predict.py path\\to\\leaf.jpg
  python src/predict.py path\\to\\leaf.jpg --topk 5
"""
import argparse
import json
import os

import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLE = os.path.join(ROOT, "model_bundle")


class ToTensorNoNumpy(object):
    """PIL -> float CHW tensor without the NumPy bridge (portable to NumPy 1.x builds)."""

    def __call__(self, img):
        if img.mode != "RGB":
            img = img.convert("RGB")
        buf = torch.frombuffer(bytearray(img.tobytes()), dtype=torch.uint8)
        return (buf.view(img.height, img.width, 3)
                   .permute(2, 0, 1)
                   .float()
                   .div_(255.0))


def load_bundle(path=BUNDLE):
    with open(os.path.join(path, "config.json"), encoding="utf-8") as fh:
        cfg = json.load(fh)
    with open(os.path.join(path, "classes.json"), encoding="utf-8") as fh:
        classes = json.load(fh)

    net = models.mobilenet_v3_small(weights=None)
    net.classifier[3] = nn.Linear(net.classifier[3].in_features, len(classes))
    net.num_classes = len(classes)
    state = torch.load(os.path.join(path, "model.pt"), map_location="cpu",
                       weights_only=True)
    net.load_state_dict(state["state_dict"])
    net.eval()
    return net, classes, cfg


def predict(image_path, topk=5, bundle=BUNDLE):
    net, classes, cfg = load_bundle(bundle)
    size = int(cfg["input_size"])
    tf = transforms.Compose([
        transforms.Resize(int(size * 1.15)),
        transforms.CenterCrop(size),
        ToTensorNoNumpy(),
        transforms.Normalize(cfg["mean"], cfg["std"]),
    ])
    with Image.open(image_path) as im:
        x = tf(im.convert("RGB")).unsqueeze(0)
    with torch.no_grad():
        prob = torch.softmax(net(x), dim=1)[0]
    scores, idx = prob.topk(min(topk, len(classes)))
    return [(classes[i], float(s)) for s, i in zip(scores, idx)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--bundle", default=BUNDLE)
    a = ap.parse_args()

    results = predict(a.image, a.topk, a.bundle)
    print("image :", a.image)
    for rank, (name, score) in enumerate(results, 1):
        print("%d. %-55s %.2f%%" % (rank, name, score * 100.0))


if __name__ == "__main__":
    main()
