# -*- coding: utf-8 -*-
"""Draw the system-design figures used in Chapter 5 of the report.

Output: figures/design/*.png
Usage : python src/make_diagrams.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Ellipse, FancyBboxPatch, Polygon  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "figures", "design")
os.makedirs(OUT, exist_ok=True)
plt.rcParams["font.family"] = "Times New Roman"

FILL = "#e8f1e6"
FILL2 = "#fdf3e1"
EDGE = "#1f3d22"


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h), dpi=200)
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, fill=FILL, fs=11, bold=False, r=0.08):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                boxstyle="round,pad=0.02,rounding_size=%s" % r,
                                fc=fill, ec=EDGE, lw=1.3))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs,
            weight="bold" if bold else "normal", wrap=True)


def arrow(ax, x1, y1, x2, y2, text=None, fs=9, off=(0, 0.12), style="-|>", ls="-"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=EDGE, lw=1.2, linestyle=ls,
                                shrinkA=0, shrinkB=0))
    if text:
        ax.text((x1 + x2) / 2 + off[0], (y1 + y2) / 2 + off[1], text,
                ha="center", va="center", fontsize=fs, style="italic",
                bbox=dict(fc="white", ec="none", pad=0.5))


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def actor(ax, x, y, name, s=0.35):
    ax.add_patch(Circle((x, y + 1.1 * s), 0.22 * s * 2, fc="white", ec=EDGE, lw=1.3))
    ax.plot([x, x], [y + 0.65 * s, y - 0.4 * s], color=EDGE, lw=1.3)
    ax.plot([x - 0.55 * s, x + 0.55 * s], [y + 0.35 * s, y + 0.35 * s], color=EDGE, lw=1.3)
    ax.plot([x, x - 0.45 * s], [y - 0.4 * s, y - 1.1 * s], color=EDGE, lw=1.3)
    ax.plot([x, x + 0.45 * s], [y - 0.4 * s, y - 1.1 * s], color=EDGE, lw=1.3)
    ax.text(x, y - 1.45 * s, name, ha="center", va="top", fontsize=11, weight="bold")


# ------------------------------------------------------------ architecture
def architecture():
    fig, ax = canvas(12, 5.6)
    # offline training lane
    ax.add_patch(FancyBboxPatch((0.2, 3.0), 11.6, 2.4, boxstyle="round,pad=0.02",
                                fc="#f7faf6", ec="#9db59a", lw=1, ls="--"))
    ax.text(0.45, 5.12, "Offline training pipeline", fontsize=11, weight="bold", color="#3b5e3e")
    y = 4.0
    xs = [1.35, 3.6, 5.85, 8.1, 10.45]
    labels = ["PlantVillage\ndataset\n(54,305 images)", "Dataset audit &\nleaf-group split\n70 / 15 / 15",
              "Pre-processing &\naugmentation", "MobileNetV3-Small\ntraining\n(weighted CE)",
              "Model bundle\nmodel.pt, classes,\nconfig"]
    for x, t in zip(xs, labels):
        box(ax, x, y, 1.95, 1.3, t, fs=10.5)
    for a, b in zip(xs[:-1], xs[1:]):
        arrow(ax, a + 0.98, y, b - 0.98, y)
    # online lane
    ax.add_patch(FancyBboxPatch((0.2, 0.2), 11.6, 2.6, boxstyle="round,pad=0.02",
                                fc="#fffdf8", ec="#d6b98a", lw=1, ls="--"))
    ax.text(0.45, 2.52, "Web application (Flask)", fontsize=11, weight="bold", color="#7a5a1e")
    y2 = 1.55
    box(ax, 1.35, y2, 1.95, 1.2, "User\n(browser)", fill=FILL2)
    box(ax, 3.6, y2, 1.95, 1.2, "Authentication\n& image upload", fill=FILL2)
    box(ax, 5.85, y2, 1.95, 1.2, "Validation &\nresize / normalise", fill=FILL2)
    box(ax, 8.1, y2, 1.95, 1.2, "Prediction +\nGrad-CAM", fill=FILL2)
    box(ax, 10.45, y2, 1.95, 1.2, "Result, report\n& history", fill=FILL2)
    for a, b in zip([1.35, 3.6, 5.85, 8.1], [3.6, 5.85, 8.1, 10.45]):
        arrow(ax, a + 0.98, y2, b - 0.98, y2)
    arrow(ax, 10.45, 3.35, 8.1, 2.15, "load weights", off=(0.3, 0.05))
    # database
    ax.add_patch(Ellipse((10.45, 0.5), 1.4, 0.32, fc="#e3ecf7", ec=EDGE))
    ax.text(10.45, 0.5, "SQLite DB", ha="center", va="center", fontsize=10)
    arrow(ax, 10.45, 0.95, 10.45, 0.66, style="<|-|>")
    save(fig, "fig_5_1_architecture.png")


# ---------------------------------------------------------------- use case
def use_case():
    fig, ax = canvas(10, 6.4)
    ax.add_patch(FancyBboxPatch((2.6, 0.3), 4.8, 5.8, boxstyle="round,pad=0.02",
                                fc="#fbfdfb", ec=EDGE, lw=1.2))
    ax.text(5.0, 5.85, "Plant Disease Detection System", ha="center", fontsize=12, weight="bold")
    cases = ["Register", "Login", "Upload leaf image", "View prediction & confidence",
             "View Grad-CAM heatmap", "Download / print report", "View history", "Logout"]
    ys = [5.25, 4.6, 3.95, 3.3, 2.65, 2.0, 1.35, 0.75]
    for t, y in zip(cases, ys):
        ax.add_patch(Ellipse((5.0, y), 3.9, 0.52, fc=FILL, ec=EDGE, lw=1.1))
        ax.text(5.0, y, t, ha="center", va="center", fontsize=10.5)
    actor(ax, 1.0, 3.2, "User / Farmer")
    for y in ys:
        ax.plot([1.25, 3.05], [3.35, y], color=EDGE, lw=0.8)
    actor(ax, 9.0, 3.2, "Trained model")
    for y in [3.3, 2.65]:
        ax.plot([7.0, 8.75], [y, 3.35], color=EDGE, lw=0.8)
    save(fig, "fig_5_2_use_case.png")


# ------------------------------------------------------------------- class
def class_box(ax, x, y, w, name, attrs, ops, fs=9.5):
    lh = 0.27
    h1, h2, h3 = 0.42, lh * len(attrs) + 0.12, lh * len(ops) + 0.12
    top = y
    for hh, fill in [(h1, "#cfe3cc"), (h2, "white"), (h3, "white")]:
        ax.add_patch(plt.Rectangle((x, top - hh), w, hh, fc=fill, ec=EDGE, lw=1.2))
        top -= hh
    ax.text(x + w / 2, y - h1 / 2, name, ha="center", va="center", fontsize=10.5, weight="bold")
    for i, a in enumerate(attrs):
        ax.text(x + 0.1, y - h1 - 0.2 - i * lh, a, fontsize=fs, va="center")
    for i, o in enumerate(ops):
        ax.text(x + 0.1, y - h1 - h2 - 0.2 - i * lh, o, fontsize=fs, va="center")
    return y - h1 - h2 - h3


def class_diagram():
    fig, ax = canvas(12, 6.8)
    class_box(ax, 0.2, 6.5, 3.4, "LeafDataset",
              ["- keys : list", "- cls_idx : dict", "- tf : Compose"],
              ["+ __len__() : int", "+ __getitem__(i) : (Tensor, int)"])
    class_box(ax, 4.3, 6.5, 3.4, "MobileNetV3Small",
              ["- features : Sequential", "- avgpool : AdaptiveAvgPool2d",
               "- classifier : Sequential (38)"],
              ["+ forward(x) : Tensor"])
    class_box(ax, 8.4, 6.5, 3.4, "Trainer (train.py)",
              ["- budget : str", "- epochs, lr, batch", "- crit : CrossEntropyLoss(w)"],
              ["+ build_model() : Module", "+ evaluate(loader) : dict", "+ main()"])
    class_box(ax, 0.2, 3.0, 3.4, "GradCAM",
              ["- model : Module", "- layer : features[-1]", "- acts, grads : Tensor"],
              ["+ __call__(x) : (cam, probs)", "+ overlay(img, cam) : Image"])
    class_box(ax, 4.3, 3.0, 3.4, "FlaskApp (app.py)",
              ["- NET, CLASSES, CFG", "- CAM : GradCAM", "- DB_PATH : str"],
              ["+ register() / login()", "+ index() : predict", "+ result() / report()", "+ history()"])
    class_box(ax, 8.4, 3.0, 3.4, "Database (SQLite)",
              ["users(id, name, email,", "      password, created_at)", "predictions(id, user_id, label,",
               "      confidence, top5, ...)"],
              ["+ get_db() : Connection"])
    arrow(ax, 3.6, 5.9, 4.3, 5.9, "feeds", off=(0, 0.15))
    arrow(ax, 8.4, 5.9, 7.7, 5.9, "trains", off=(0, 0.15))
    arrow(ax, 4.3, 2.4, 3.6, 2.4, "uses", off=(0, 0.15))
    arrow(ax, 6.0, 3.0, 6.0, 4.55, "loads", off=(0.35, 0))
    arrow(ax, 7.7, 2.4, 8.4, 2.4, "stores", off=(0, 0.15))
    save(fig, "fig_5_3_class.png")


# ---------------------------------------------------------------- sequence
def sequence():
    fig, ax = canvas(12, 7)
    parts = ["User", "Browser UI", "Flask server", "Model + Grad-CAM", "SQLite DB"]
    xs = [1.0, 3.6, 6.2, 8.8, 11.0]
    for x, p in zip(xs, parts):
        box(ax, x, 6.5, 1.9, 0.6, p, fs=11, bold=True)
        ax.plot([x, x], [6.2, 0.3], color="#7a8a7c", lw=1, ls="--")
    msgs = [(0, 1, "1. open site / login"), (1, 2, "2. POST /login (email, password)"),
            (2, 4, "3. verify hashed password"), (4, 2, "4. user record"),
            (0, 1, "5. choose leaf image"), (1, 2, "6. POST / (multipart image)"),
            (2, 2, "7. validate & resize"), (2, 3, "8. forward pass + backward (CAM)"),
            (3, 2, "9. top-5 probabilities, heatmap"), (2, 4, "10. INSERT prediction"),
            (2, 1, "11. redirect /result/<id>"), (1, 0, "12. show disease, confidence, heatmap")]
    y = 5.8
    for a, b, t in msgs:
        if a == b:
            ax.plot([xs[a], xs[a] + 0.45, xs[a] + 0.45], [y + 0.1, y + 0.1, y - 0.15],
                    color=EDGE, lw=1.1)
            arrow(ax, xs[a] + 0.45, y - 0.15, xs[a], y - 0.15)
            ax.text(xs[a] + 0.6, y - 0.02, t, fontsize=9.5, va="center")
            y -= 0.1
        else:
            arrow(ax, xs[a], y, xs[b], y, style="-|>",
                  ls="--" if b < a else "-")
            ax.text((xs[a] + xs[b]) / 2, y + 0.13, t, ha="center", fontsize=9.5,
                    bbox=dict(fc="white", ec="none", pad=0.3))
        y -= 0.45
    save(fig, "fig_5_4_sequence.png")


# ---------------------------------------------------------------- activity
def activity():
    fig, ax = canvas(7.5, 10.5)
    x = 3.75
    ax.add_patch(Circle((x, 10.1), 0.15, fc=EDGE))
    steps = [(9.35, "Login / Register"), (8.45, "Upload leaf image"), (6.65, "Resize 184 px, centre-crop 160 px,\nnormalise (ImageNet mean/std)"),
             (5.75, "MobileNetV3-Small forward pass"), (4.85, "Softmax: top-5 classes & confidence"),
             (3.95, "Grad-CAM heatmap of top class"), (3.05, "Save prediction to database"),
             (2.15, "Display result, report & history")]
    for yy, t in steps:
        box(ax, x, yy, 4.2, 0.6, t, fs=10.5, r=0.25)
    # decision
    ax.add_patch(Polygon([[x, 7.95], [x + 1.3, 7.55], [x, 7.15], [x - 1.3, 7.55]], fc=FILL2, ec=EDGE))
    ax.text(x, 7.55, "Valid image?", ha="center", va="center", fontsize=10.5)
    arrow(ax, x, 9.95, x, 9.65)
    arrow(ax, x, 9.05, x, 8.75)
    arrow(ax, x, 8.15, x, 7.95)
    arrow(ax, x, 7.15, x, 6.95)
    ax.text(x + 0.15, 7.03, "yes", fontsize=9.5)
    ax.plot([x + 1.3, 6.9, 6.9], [7.55, 7.55, 8.45], color=EDGE, lw=1.2)
    arrow(ax, 6.9, 8.45, x + 2.1, 8.45)
    ax.text(5.75, 7.7, "no: show error", fontsize=9.5, ha="center")
    for a, b in [(6.65, 5.75), (5.75, 4.85), (4.85, 3.95), (3.95, 3.05), (3.05, 2.15)]:
        arrow(ax, x, a - 0.3, x, b + 0.3)
    arrow(ax, x, 1.85, x, 1.35)
    ax.add_patch(Circle((x, 1.2), 0.17, fc="white", ec=EDGE, lw=1.5))
    ax.add_patch(Circle((x, 1.2), 0.1, fc=EDGE))
    save(fig, "fig_5_5_activity.png")


# --------------------------------------------------------------------- DFD
def dfd0():
    fig, ax = canvas(10, 3.2)
    box(ax, 1.3, 1.6, 2.0, 0.9, "User", fill=FILL2, fs=12, bold=True, r=0.02)
    ax.add_patch(Circle((5.0, 1.6), 1.15, fc=FILL, ec=EDGE, lw=1.3))
    ax.text(5.0, 1.6, "0.0\nPlant Disease\nDetection System", ha="center", va="center", fontsize=11)
    box(ax, 8.7, 1.6, 2.0, 0.9, "User", fill=FILL2, fs=12, bold=True, r=0.02)
    arrow(ax, 2.3, 1.6, 3.85, 1.6, "leaf image,\ncredentials", off=(0, 0.42))
    arrow(ax, 6.15, 1.6, 7.7, 1.6, "disease, confidence,\nheatmap, report", off=(0, 0.42))
    save(fig, "fig_5_6_dfd0.png")


def dfd_level(name, procs, stores, flows, w=12, h=5.2):
    fig, ax = canvas(w, h)
    for key, (x, y, t) in procs.items():
        ax.add_patch(Circle((x, y), 0.85, fc=FILL, ec=EDGE, lw=1.3))
        ax.text(x, y, t, ha="center", va="center", fontsize=10)
    for key, (x, y, t) in stores.items():
        ax.plot([x - 1.1, x + 1.1], [y + 0.28, y + 0.28], color=EDGE, lw=1.3)
        ax.plot([x - 1.1, x + 1.1], [y - 0.28, y - 0.28], color=EDGE, lw=1.3)
        ax.plot([x - 1.1, x - 1.1], [y - 0.28, y + 0.28], color=EDGE, lw=1.3)
        ax.text(x, y, t, ha="center", va="center", fontsize=10)
    for (x1, y1, x2, y2, t) in flows:
        arrow(ax, x1, y1, x2, y2, t, off=(0, 0.18))
    save(fig, name)


def dfd1():
    procs = {"p0": (1.0, 2.6, "User"),
             "p1": (3.4, 2.6, "1.0\nAuthenticate"),
             "p2": (6.0, 2.6, "2.0\nUpload &\nvalidate"),
             "p3": (8.6, 2.6, "3.0\nPredict &\nexplain"),
             "p4": (11.0, 2.6, "4.0\nReport &\nhistory")}
    stores = {"d1": (3.4, 0.55, "D1  users"), "d2": (8.6, 0.55, "D2  model bundle"),
              "d3": (9.9, 4.6, "D3  predictions")}
    flows = [(1.85, 2.6, 2.55, 2.6, "login"), (4.25, 2.6, 5.15, 2.6, "session"),
             (6.85, 2.6, 7.75, 2.6, "160x160 tensor"), (9.45, 2.6, 10.15, 2.6, "result"),
             (3.4, 1.75, 3.4, 0.83, ""), (8.6, 0.83, 8.6, 1.75, ""),
             (8.95, 3.38, 9.4, 4.32, "save"), (10.6, 4.32, 10.75, 3.42, "read")]
    fig_w = 12.2
    dfd_level("fig_5_7_dfd1.png", procs, stores, flows, w=fig_w)


def dfd2():
    procs = {"a": (1.1, 3.1, "3.1\nResize &\ncrop"),
             "b": (3.5, 3.1, "3.2\nNormalise"),
             "c": (5.9, 3.1, "3.3\nCNN\nforward"),
             "d": (8.3, 3.1, "3.4\nSoftmax\ntop-5"),
             "e": (5.9, 0.95, "3.5\nGrad-CAM"),
             "f": (10.7, 3.1, "3.6\nStore &\ndisplay")}
    stores = {"s": (5.9, 5.1, "D2  model weights")}
    flows = [(1.95, 3.1, 2.65, 3.1, "image"), (4.35, 3.1, 5.05, 3.1, "tensor"),
             (6.75, 3.1, 7.45, 3.1, "logits"), (9.15, 3.1, 9.85, 3.1, "labels"),
             (5.9, 4.82, 5.9, 3.95, ""), (5.9, 2.25, 5.9, 1.8, ""),
             (6.75, 0.95, 10.2, 2.4, "heatmap")]
    dfd_level("fig_5_8_dfd2.png", procs, stores, flows, w=12, h=5.7)


def testing_flow():
    fig, ax = canvas(11, 2.2)
    xs = [1.2, 3.9, 6.6, 9.4]
    for x, t in zip(xs, ["Unit\ntesting", "Functional\ntesting", "Integration\ntesting",
                         "Acceptance\ntesting"]):
        box(ax, x, 1.1, 2.0, 1.0, t, fs=12)
    for a, b in zip(xs[:-1], xs[1:]):
        arrow(ax, a + 1.0, 1.1, b - 1.0, 1.1)
    save(fig, "fig_8_1_testing_flow.png")


if __name__ == "__main__":
    for f in [architecture, use_case, class_diagram, sequence, activity, dfd0, dfd1,
              dfd2, testing_flow]:
        f()
    print("figures ->", OUT)
