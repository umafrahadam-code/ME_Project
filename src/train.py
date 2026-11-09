# -*- coding: utf-8 -*-
"""Train the demo classifier used by the inference app.

Follows the experiment protocol declared in the report:
  * fixed leaf-group-aware split from split_manifest.csv (seed 42)
  * per-class budgets sampled from the TRAINING partition only
  * MobileNetV3-Small backbone with a 38-class head
  * class-weighted cross entropy + label-preserving augmentation
  * best checkpoint selected on validation macro-F1, final report on test

Usage:
  python src/train.py --bench                 # 12-iteration speed probe
  python src/train.py --budget B40 --epochs 12
"""
import argparse
import csv
import json
import os
import random
import time
from collections import defaultdict

import torch
import torch.nn as nn
from PIL import Image, ImageEnhance
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPLITS = os.path.join(ROOT, "dataset", "PlantVillage", "splits")
RAW = os.path.join(ROOT, "dataset", "PlantVillage", "raw", "color")
ART = os.path.join(ROOT, "artifacts")
CKPT_DIR = os.path.join(ART, "checkpoints")
METRIC_DIR = os.path.join(ART, "metrics")
BUNDLE = os.path.join(ROOT, "model_bundle")
# Keep the torch hub cache inside the project: the default ~/.cache path is not
# writable in this environment, which made the pretrained download fail early.
os.environ.setdefault("TORCH_HOME", os.path.join(ART, "torch_cache"))
os.makedirs(CKPT_DIR, exist_ok=True)
os.makedirs(METRIC_DIR, exist_ok=True)


# --------------------------------------------------------------------- utils
def seed_everything(s=42):
    random.seed(s)
    torch.manual_seed(s)


def load_rows():
    with open(os.path.join(SPLITS, "split_manifest.csv"), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def build_class_index(rows):
    classes = sorted({r["class_name"] for r in rows})
    return classes, {c: i for i, c in enumerate(classes)}


def partition_keys(rows, partition, budget=None):
    """Keys for one partition; optionally restricted to a training budget."""
    budget_keys = None
    if budget:
        path = os.path.join(SPLITS, "budgets", "%s_manifest.csv" % budget)
        with open(path, encoding="utf-8") as fh:
            budget_keys = {(r["class_name"], r["file_name"])
                           for r in csv.DictReader(fh)}
    out = []
    for r in rows:
        if r["partition"] != partition:
            continue
        key = (r["class_name"], r["file_name"])
        if budget_keys is not None and key not in budget_keys:
            continue
        out.append(key)
    return out


def class_counts(keys):
    cnt = defaultdict(int)
    for c, _ in keys:
        cnt[c] += 1
    return cnt


def build_model(n_cls, pretrained=True, log=print):
    """MobileNetV3-Small with a fresh 38-way head.

    ``num_classes`` cannot be overridden while requesting pretrained weights
    (torchvision raises ValueError: expected 1000). Build the ImageNet model
    first and then swap the final classifier layer. When the weights cannot be
    downloaded (offline machine), fall back to random initialisation instead of
    crashing the run.
    """
    def _assemble(weights):
        net = models.mobilenet_v3_small(weights=weights)
        in_features = net.classifier[3].in_features
        net.classifier[3] = nn.Linear(in_features, n_cls)
        net.num_classes = n_cls
        return net

    if pretrained:
        try:
            return _assemble(models.MobileNet_V3_Small_Weights.IMAGENET1K_V1), True
        except Exception as exc:  # URLError / HTTPError / socket errors
            log("WARNING: pretrained weights unavailable (%s: %s); "
                "continuing with random initialisation."
                % (type(exc).__name__, exc))
    return _assemble(None), False


# ------------------------------------------------------------------- dataset
class LeafDataset(Dataset):
    def __init__(self, keys, cls_idx, tf):
        self.keys = keys
        self.cls_idx = cls_idx
        self.tf = tf

    def __len__(self):
        return len(self.keys)

    def __getitem__(self, i):
        cls, fn = self.keys[i]
        path = os.path.join(RAW, cls, fn)
        with Image.open(path) as im:
            img = im.convert("RGB")
        return self.tf(img), self.cls_idx[cls]


class ToTensorNoNumpy(object):
    """PIL -> float CHW tensor without going through the NumPy bridge.

    Kept NumPy-free so the pipeline also works on torch builds that were
    compiled against NumPy 1.x (where ``transforms.ToTensor`` can raise
    "Numpy is not available"). The result is identical to ``ToTensor``.
    """

    def __call__(self, img):
        if img.mode != "RGB":
            img = img.convert("RGB")
        buf = torch.frombuffer(bytearray(img.tobytes()), dtype=torch.uint8)
        return (buf.view(img.height, img.width, 3)
                   .permute(2, 0, 1)
                   .float()
                   .div_(255.0))


class RandomColorJitter(object):
    """Brightness/contrast/saturation/hue jitter implemented with PIL only.

    Avoids torchvision's ``np.uint8`` hue arithmetic (which raises
    ``OverflowError`` under NumPy 2.x) and keeps augmentation independent of
    the NumPy ABI. The result is label-preserving, like ``ColorJitter``.
    """

    def __init__(self, brightness=0.25, contrast=0.25, saturation=0.25,
                 hue=0.10):
        self.brightness = brightness
        self.contrast = contrast
        self.saturation = saturation
        self.hue = hue

    @staticmethod
    def _factor(value):
        return random.uniform(max(0.0, 1.0 - value), 1.0 + value)

    @staticmethod
    def _adjust_hue(img, factor):
        if factor == 0.0:
            return img
        hsv = img.convert("HSV")
        h, s, v = hsv.split()
        delta = int(factor * 255)
        lut = [(i + delta) % 256 for i in range(256)]
        return Image.merge("HSV", (h.point(lut), s, v)).convert("RGB")

    def __call__(self, img):
        if self.brightness:
            img = ImageEnhance.Brightness(img).enhance(self._factor(self.brightness))
        if self.contrast:
            img = ImageEnhance.Contrast(img).enhance(self._factor(self.contrast))
        if self.saturation:
            img = ImageEnhance.Color(img).enhance(self._factor(self.saturation))
        if self.hue:
            img = self._adjust_hue(
                img, random.uniform(-self.hue, self.hue))
        return img


def make_transforms(size):
    mean = [0.485, 0.456, 0.406]
    std = [0.229, 0.224, 0.225]
    train_tf = transforms.Compose([
        transforms.RandomResizedCrop(size, scale=(0.6, 1.0)),
        transforms.RandomHorizontalFlip(),
        RandomColorJitter(0.25, 0.25, 0.25, 0.10),
        ToTensorNoNumpy(),
        transforms.Normalize(mean, std),
    ])
    eval_tf = transforms.Compose([
        transforms.Resize(int(size * 1.15)),
        transforms.CenterCrop(size),
        ToTensorNoNumpy(),
        transforms.Normalize(mean, std),
    ])
    return train_tf, eval_tf, mean, std


# ------------------------------------------------------------------- metrics
def macro_f1_and_acc(preds, golds, n_cls):
    tp = [0] * n_cls
    fp = [0] * n_cls
    fn = [0] * n_cls
    correct = 0
    for p, g in zip(preds, golds):
        if p == g:
            tp[p] += 1
            correct += 1
        else:
            fp[p] += 1
            fn[g] += 1
    f1s = []
    for c in range(n_cls):
        prec = tp[c] / (tp[c] + fp[c]) if (tp[c] + fp[c]) else 0.0
        rec = tp[c] / (tp[c] + fn[c]) if (tp[c] + fn[c]) else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if (prec + rec) else 0.0)
    acc = correct / len(golds) if golds else 0.0
    macro = sum(f1s) / n_cls if n_cls else 0.0
    return acc, macro, f1s


@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    preds, golds, losses = [], [], []
    crit = nn.CrossEntropyLoss(reduction="sum")
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        x = x.to(memory_format=torch.channels_last)
        logits = model(x)
        losses.append(float(crit(logits, y)))
        preds.extend(logits.argmax(1).tolist())
        golds.extend(y.tolist())
    n = len(golds)
    acc, macro, f1s = macro_f1_and_acc(preds, golds, model.num_classes)
    loss = sum(losses) / n if n else 0.0
    return {"loss": loss, "acc": acc, "macro_f1": macro, "f1": f1s,
            "preds": preds, "golds": golds}


# ------------------------------------------------------------------- training
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--budget", default="B40",
                   choices=["B20", "B40", "B60", "B80", "B100", "all"])
    p.add_argument("--epochs", type=int, default=12)
    p.add_argument("--img", type=int, default=160)
    p.add_argument("--batch", type=int, default=32)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--workers", type=int, default=0,
                   help="DataLoader worker processes; 0 is required under "
                        "sandboxed Windows where named pipes are blocked")
    p.add_argument("--patience", type=int, default=4)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--bench", action="store_true")
    p.add_argument("--tag", default="demo")
    return p.parse_args()


def main():
    a = parse_args()
    seed_everything(a.seed)
    device = torch.device("cpu")
    torch.set_num_threads(min(12, os.cpu_count() or 4))

    t0 = time.time()
    rows = load_rows()
    classes, cls_idx = build_class_index(rows)
    n_cls = len(classes)
    budget = None if a.budget == "all" else a.budget

    train_keys = partition_keys(rows, "train", budget)
    val_keys = partition_keys(rows, "validation")
    test_keys = partition_keys(rows, "test")
    print("classes=%d  train=%d  val=%d  test=%d  budget=%s"
          % (n_cls, len(train_keys), len(val_keys), len(test_keys),
             budget or "all"))

    train_tf, eval_tf, mean, std = make_transforms(a.img)
    train_ds = LeafDataset(train_keys, cls_idx, train_tf)
    val_ds = LeafDataset(val_keys, cls_idx, eval_tf)
    test_ds = LeafDataset(test_keys, cls_idx, eval_tf)

    if a.bench:
        loader = DataLoader(train_ds, batch_size=a.batch, shuffle=False,
                            num_workers=0)
        model, pretrained = build_model(n_cls, pretrained=True)
        model = model.to(memory_format=torch.channels_last)
        print("backbone=%s pretrained=%s" % ("MobileNetV3-Small", pretrained))
        model.train()
        opt = torch.optim.AdamW(model.parameters(), lr=a.lr)
        crit = nn.CrossEntropyLoss()
        it = iter(loader)
        n_it = 0
        t1 = time.time()
        while n_it < 12:
            try:
                x, y = next(it)
            except StopIteration:
                it = iter(loader)
                x, y = next(it)
            opt.zero_grad()
            x = x.to(memory_format=torch.channels_last)
            loss = crit(model(x), y)
            loss.backward()
            opt.step()
            n_it += 1
        dt = (time.time() - t1) / n_it
        per_epoch = dt * len(train_ds) / a.batch
        print("BENCH: %.2f s/iter  ->  %.1f min/epoch  ->  %d epochs ~ %.0f min"
              % (dt, per_epoch / 60, a.epochs, per_epoch * a.epochs / 60))
        return

    # class-weighted loss (inverse sqrt frequency, normalised to mean 1)
    cnt = class_counts(train_keys)
    w = [1.0 / (cnt[c] ** 0.5) for c in classes]
    mean_w = sum(w) / len(w)
    weight = torch.tensor([x / mean_w for x in w], dtype=torch.float32)
    crit = nn.CrossEntropyLoss(weight=weight)

    model, pretrained = build_model(n_cls, pretrained=True)
    model = model.to(memory_format=torch.channels_last)
    print("backbone=MobileNetV3-Small  pretrained=%s" % pretrained)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(
        opt, T_max=max(1, a.epochs))

    train_loader = DataLoader(train_ds, batch_size=a.batch, shuffle=True,
                              num_workers=a.workers, drop_last=False)
    val_loader = DataLoader(val_ds, batch_size=a.batch * 2, shuffle=False,
                            num_workers=a.workers)

    log_path = os.path.join(ART, "training_log_%s.csv" % a.tag)
    with open(log_path, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerow(
            ["epoch", "train_loss", "train_acc", "val_loss", "val_acc",
             "val_macro_f1", "lr", "seconds"])

    best = {"macro_f1": -1.0}
    bad = 0
    for ep in range(1, a.epochs + 1):
        t1 = time.time()
        model.train()
        run_loss, run_ok, run_n = 0.0, 0, 0
        for x, y in train_loader:
            opt.zero_grad()
            x = x.to(memory_format=torch.channels_last)
            logits = model(x)
            loss = crit(logits, y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            run_loss += float(loss) * len(y)
            run_ok += int((logits.argmax(1) == y).sum())
            run_n += len(y)
        sched.step()

        val = evaluate(model, val_loader, device)
        secs = time.time() - t1
        tr_loss, tr_acc = run_loss / run_n, run_ok / run_n
        lr_now = opt.param_groups[0]["lr"]
        print("ep %2d/%d  train_loss %.3f acc %.3f | val_loss %.3f "
              "acc %.3f macroF1 %.3f | %.0fs"
              % (ep, a.epochs, tr_loss, tr_acc, val["loss"], val["acc"],
                 val["macro_f1"], secs), flush=True)
        with open(log_path, "a", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(
                [ep, round(tr_loss, 4), round(tr_acc, 4),
                 round(val["loss"], 4), round(val["acc"], 4),
                 round(val["macro_f1"], 4), round(lr_now, 6), int(secs)])

        if val["macro_f1"] > best["macro_f1"] + 1e-4:
            best = {"macro_f1": val["macro_f1"], "acc": val["acc"],
                    "loss": val["loss"], "epoch": ep}
            bad = 0
            torch.save({"state_dict": model.state_dict(), "classes": classes,
                        "img": a.img, "budget": budget or "B100",
                        "seed": a.seed, "epoch": ep, "pretrained": pretrained,
                        "val": {"acc": val["acc"],
                                "macro_f1": val["macro_f1"]}},
                       os.path.join(CKPT_DIR, "model_best.pt"))
        else:
            bad += 1
            if bad >= a.patience:
                print("early stop at epoch %d (best epoch %d)"
                      % (ep, best["epoch"]))
                break

    # ---------------------------------------------------------- final test
    bundle_path = os.path.join(CKPT_DIR, "model_best.pt")
    state = torch.load(bundle_path, map_location="cpu", weights_only=False)
    model.load_state_dict(state["state_dict"])
    test_loader = DataLoader(test_ds, batch_size=a.batch * 2, shuffle=False,
                             num_workers=a.workers)
    test = evaluate(model, test_loader, device)

    n_params = sum(p.numel() for p in model.parameters())
    ckpt_mb = os.path.getsize(bundle_path) / 1e6
    metrics = {
        "budget": budget or "B100",
        "seed": a.seed,
        "input_size": a.img,
        "classes": n_cls,
        "train_images": len(train_keys),
        "val_images": len(val_keys),
        "test_images": len(test_keys),
        "best_epoch": best["epoch"],
        "val_acc": round(best["acc"], 4),
        "val_macro_f1": round(best["macro_f1"], 4),
        "test_acc": round(test["acc"], 4),
        "test_macro_f1": round(test["macro_f1"], 4),
        "per_class_f1": {c: round(v, 4) for c, v in zip(classes, test["f1"])},
        "parameters": n_params,
        "pretrained": pretrained,
        "checkpoint_mb": round(ckpt_mb, 2),
        "wall_minutes": round((time.time() - t0) / 60, 1),
        "device": "cpu",
    }
    with open(os.path.join(METRIC_DIR, "metrics_%s.json" % a.tag), "w",
              encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)

    # ------------------------------------------------------- export bundle
    os.makedirs(BUNDLE, exist_ok=True)
    torch.save({"state_dict": model.state_dict()}, os.path.join(BUNDLE, "model.pt"))
    with open(os.path.join(BUNDLE, "classes.json"), "w", encoding="utf-8") as fh:
        json.dump(classes, fh, indent=2)
    with open(os.path.join(BUNDLE, "config.json"), "w", encoding="utf-8") as fh:
        json.dump({"input_size": a.img, "mean": mean, "std": std,
                   "backbone": "MobileNetV3-Small", "classes": n_cls,
                   "budget": budget or "B100", "seed": a.seed,
                   "pretrained": pretrained,
                   "test_acc": metrics["test_acc"],
                   "test_macro_f1": metrics["test_macro_f1"],
                   "trained_at": time.strftime("%Y-%m-%d %H:%M:%S")}, fh, indent=2)

    print("\nTEST acc %.4f  macro-F1 %.4f  (%.1f min, %.1f MB)"
          % (test["acc"], test["macro_f1"], metrics["wall_minutes"], ckpt_mb))
    print("bundle ->", BUNDLE)


if __name__ == "__main__":
    main()
