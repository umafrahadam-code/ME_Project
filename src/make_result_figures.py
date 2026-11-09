# -*- coding: utf-8 -*-
"""Result figures for Chapter 8 (training curves, per-class F1, confusion
matrix, Grad-CAM samples). Reads the training log and the test evaluation.

Usage:  python src/make_result_figures.py
"""
import csv
import glob
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402
from torchvision import transforms  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gradcam import GradCAM, overlay  # noqa: E402
from predict import ToTensorNoNumpy, load_bundle  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "figures", "results")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 11})
GREEN, ORANGE = "#2e7d32", "#d9822b"


def short(name):
    crop, _, cond = name.partition("___")
    crop = crop.split("_(")[0].replace(",", "").replace("_", " ")
    cond = cond.replace("_", " ").split("(")[0].strip()
    return "%s - %s" % (crop, cond)


def curves():
    with open(os.path.join(ROOT, "artifacts", "training_log_b40.csv")) as fh:
        rows = list(csv.DictReader(fh))
    ep = [int(r["epoch"]) for r in rows]
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.8), dpi=200)
    a.plot(ep, [float(r["train_loss"]) for r in rows], "o-", color=GREEN, label="Training")
    a.plot(ep, [float(r["val_loss"]) for r in rows], "s--", color=ORANGE, label="Validation")
    a.set(title="Loss", xlabel="Epoch", ylabel="Cross-entropy loss", xticks=ep)
    b.plot(ep, [100 * float(r["train_acc"]) for r in rows], "o-", color=GREEN, label="Training accuracy")
    b.plot(ep, [100 * float(r["val_acc"]) for r in rows], "s--", color=ORANGE, label="Validation accuracy")
    b.plot(ep, [100 * float(r["val_macro_f1"]) for r in rows], "^:", color="#555", label="Validation macro-F1")
    b.set(title="Accuracy / F1", xlabel="Epoch", ylabel="%", xticks=ep, ylim=(78, 100))
    for ax in (a, b):
        ax.grid(alpha=.3)
        ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_8_2_training_curves.png"), facecolor="white")
    plt.close(fig)


def per_class(ev):
    items = sorted(ev["per_class"].items(), key=lambda kv: kv[1]["f1"])
    fig, ax = plt.subplots(figsize=(8, 10), dpi=200)
    names = [short(k) for k, _ in items]
    vals = [100 * v["f1"] for _, v in items]
    cols = [ORANGE if v < 95 else GREEN for v in vals]
    ax.barh(names, vals, color=cols)
    for i, v in enumerate(vals):
        ax.text(v + 0.1, i, "%.1f" % v, va="center", fontsize=8)
    ax.set_xlim(80, 101.5)
    ax.set_xlabel("F1-score on test set (%)")
    ax.tick_params(axis="y", labelsize=8.5)
    ax.grid(axis="x", alpha=.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_8_3_per_class_f1.png"), facecolor="white")
    plt.close(fig)


def confusion(ev):
    cm = ev["confusion_matrix"]
    norm = [[c / max(1, sum(r)) for c in r] for r in cm]
    fig, ax = plt.subplots(figsize=(10, 9), dpi=200)
    im = ax.imshow(norm, cmap="Greens", vmin=0, vmax=1)
    n = len(cm)
    labels = [short(c) for c in ev["classes"]]
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=90, fontsize=6.5)
    ax.set_yticklabels(labels, fontsize=6.5)
    ax.set_xlabel("Predicted class")
    ax.set_ylabel("True class")
    fig.colorbar(im, ax=ax, fraction=0.04, label="Row-normalised rate")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_8_4_confusion_matrix.png"), facecolor="white")
    plt.close(fig)


def gradcam_grid():
    net, classes, cfg = load_bundle()
    size = int(cfg["input_size"])
    prep = transforms.Compose([transforms.Resize(int(size * 1.15)), transforms.CenterCrop(size)])
    tt = transforms.Compose([ToTensorNoNumpy(), transforms.Normalize(cfg["mean"], cfg["std"])])
    cam = GradCAM(net)
    with open(os.path.join(ROOT, "dataset", "PlantVillage", "splits", "split_manifest.csv"),
              encoding="utf-8") as fh:
        test = [r for r in csv.DictReader(fh) if r["partition"] == "test"]
    want = ["Tomato___Early_blight", "Apple___Black_rot", "Grape___Esca_(Black_Measles)",
            "Potato___Late_blight", "Corn_(maize)___Common_rust_", "Pepper,_bell___healthy"]
    fig, axes = plt.subplots(2, 6, figsize=(12, 4.6), dpi=200)
    for j, cls in enumerate(want):
        r = next(x for x in test if x["class_name"] == cls)
        img = prep(Image.open(os.path.join(ROOT, "dataset", "PlantVillage", "raw", "color",
                                           cls, r["file_name"])).convert("RGB"))
        c, p = cam(tt(img).unsqueeze(0))
        k = int(p.argmax())
        axes[0, j].imshow(img)
        axes[0, j].set_title(short(cls), fontsize=9)
        axes[1, j].imshow(overlay(img, c))
        axes[1, j].set_title("Pred: %s\n%.1f%%" % (short(classes[k]).split(" - ")[1],
                                                    100 * float(p[k])), fontsize=8.5)
        for ax in (axes[0, j], axes[1, j]):
            ax.axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_8_5_gradcam_samples.png"), facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    with open(os.path.join(ROOT, "artifacts", "metrics", "test_evaluation.json")) as fh:
        ev = json.load(fh)
    curves()
    per_class(ev)
    confusion(ev)
    gradcam_grid()
    print("figures ->", OUT)
