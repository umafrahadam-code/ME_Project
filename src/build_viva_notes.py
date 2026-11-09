# -*- coding: utf-8 -*-
"""Build the 3-page viva preparation notes as a PDF.

Numbers are read from the experiment artefacts. A temporary DOCX is written to
the system temp folder, converted to PDF with MS Word, and then deleted.
Usage:  python src/build_viva_notes.py   ->  Viva_Preparation_Notes.pdf
"""
import json
import os
import tempfile

import win32com.client
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(ROOT, "Viva_Preparation_Notes.pdf")
TMP = os.path.join(tempfile.gettempdir(), "viva_notes_tmp.docx")


def jload(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as fh:
        return json.load(fh)


EV = jload("artifacts", "metrics", "test_evaluation.json")
MET = jload("artifacts", "metrics", "metrics_b40.json")
ST = jload("artifacts", "metrics", "explanation_stability.json")["views"]
DS = jload("dataset", "PlantVillage", "splits", "dataset_summary.json")


def pct(x, d=2):
    return ("%." + str(d) + "f%%") % (100 * x)


N = lambda v: "{:,}".format(v)  # noqa: E731
GREEN = RGBColor(0x1B, 0x5E, 0x20)
SIZE = float(os.environ.get("VIVA_FONT", "11.6"))

doc = Document()
s = doc.sections[0]
s.page_height, s.page_width = Inches(11.69), Inches(8.27)
s.left_margin = s.right_margin = Inches(0.6)
s.top_margin = s.bottom_margin = Inches(0.5)
st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.font.size = Pt(SIZE)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
st.paragraph_format.space_after = Pt(1.5)
st.paragraph_format.space_before = Pt(0)
st.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE

# page footer "Viva notes - page X"
fp = s.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _fld(p, code):
    for kind, text in (("begin", None), (None, code), ("separate", None), (None, "1"),
                       ("end", None)):
        r = p.add_run()
        r.font.size = Pt(8)
        if kind:
            e = OxmlElement("w:fldChar")
            e.set(qn("w:fldCharType"), kind)
            r._r.append(e)
        elif text == code:
            e = OxmlElement("w:instrText")
            e.set(qn("xml:space"), "preserve")
            e.text = " %s " % code
            r._r.append(e)
        else:
            r.text = text


r = fp.add_run("Viva Preparation Notes  |  Page ")
r.font.size = Pt(8)
_fld(fp, "PAGE")


def runs(p, text, size=SIZE, color=None):
    for i, part in enumerate(text.split("**")):
        if part:
            r = p.add_run(part)
            r.bold = i % 2 == 1
            r.font.size = Pt(size)
            if color and r.bold:
                r.font.color.rgb = color
    return p


def P(text, size=SIZE, align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=1.5):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after = Pt(after)
    return runs(p, text, size)


def H(text, before=5):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    bdr = OxmlElement("w:pBdr")
    b = OxmlElement("w:bottom")
    for k, v in (("w:val", "single"), ("w:sz", "6"), ("w:space", "1"), ("w:color", "1B5E20")):
        b.set(qn(k), v)
    bdr.append(b)
    p._p.get_or_add_pPr().append(bdr)
    r = p.add_run(text.upper())
    r.bold = True
    r.font.size = Pt(11)
    r.font.color.rgb = GREEN
    return p


def B(text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.left_indent = Inches(0.18)
    p.paragraph_format.first_line_indent = Inches(-0.13)
    p.paragraph_format.space_after = Pt(1)
    return runs(p, "• " + text)


def QA(n, q, a):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(2.5)
    p.paragraph_format.keep_together = True
    runs(p, "**Q%d. %s**  " % (n, q), color=GREEN)
    runs(p, a)


def grid(rows, widths, header=True, size=9.5):
    t = doc.add_table(rows=0, cols=len(widths))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for ci, v in enumerate(row):
            cells[ci].width = Inches(widths[ci])
            pp = cells[ci].paragraphs[0]
            pp.paragraph_format.space_after = Pt(0)
            runs(pp, str(v), size)
            if header and ri == 0:
                for r in pp.runs:
                    r.bold = True
                sh = OxmlElement("w:shd")
                sh.set(qn("w:val"), "clear")
                sh.set(qn("w:fill"), "D9E7D6")
                cells[ci]._tc.get_or_add_tcPr().append(sh)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return t


fl, br, ro = ST["horizontal_flip"], ST["brightness_+15%"], ST["rotation_10deg"]
low = sorted(EV["per_class"].items(), key=lambda kv: kv[1]["f1"])[:2]

# ================================================================ PAGE 1
t = doc.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
t.paragraph_format.space_after = Pt(0)
r = t.add_run("VIVA PREPARATION NOTES")
r.bold = True
r.font.size = Pt(15)
r.font.color.rgb = GREEN
P("**A Data-Budget-Aware and Explanation-Stable Lightweight Deep Learning Framework for "
  "Plant Disease Detection**", 11, WD_ALIGN_PARAGRAPH.CENTER, after=4)

H("1. Two-minute project explanation (say this first)", before=2)
P("“Plant diseases reduce crop yield, and farmers cannot always get an expert in time. My "
  "project detects plant leaf diseases from a single photo using a **lightweight deep learning "
  "model** that also **explains** its decision. I used the PlantVillage dataset of **%s images "
  "in 38 classes** covering 14 crops. I first audited the data and split it by **leaf groups**, "
  "so photos of the same leaf never appear in both training and testing – this avoids data "
  "leakage. To study the limited-data situation, I trained on only **40%% of the training data "
  "(%s images)**. I fine-tuned a pretrained **MobileNetV3-Small**, which has only **%.2f million "
  "parameters**, with augmentation and class-weighted loss for imbalance. On %s unseen test "
  "images it reached **%s accuracy** and **%s macro F1-score**, and it predicts in about **%.0f "
  "ms on a normal CPU**. I used **Grad-CAM** to show which leaf regions influenced each "
  "prediction and measured how stable these heatmaps are. Finally, I built a **Flask web app** "
  "with login, image upload, prediction, heatmap, report and history stored in SQLite.”"
  % (N(DS["total_images"]), N(MET["train_images"]), EV["parameters"] / 1e6,
     N(EV["test_images"]), pct(EV["accuracy"]), pct(EV["macro_f1"]), EV["latency_ms_cpu"]))

H("2. Problem, objectives and contribution")
B("**Problem:** manual inspection is slow and expert-dependent; similar symptoms cause "
  "mistakes; large CNNs are heavy; most systems give no explanation and are tested only on "
  "the full dataset with a random split.")
B("**Objectives:** (1) leakage-free split with controlled data budgets, (2) symptom-preserving "
  "preprocessing and augmentation, (3) lightweight classifier with balanced performance, "
  "(4) Grad-CAM explanations with measured stability, (5) usable web application.")
B("**My contribution:** not a new network – a complete, reproducible pipeline that combines "
  "a leaf-group split, data-budget training, class-weighted learning, quantified "
  "explanation stability and a deployed app.")

H("3. Existing vs proposed system")
grid([("Existing system", "Proposed system"),
      ("Manual inspection / lab tests – slow, needs experts", "Photo-based prediction in ~%.0f ms"
       % EV["latency_ms_cpu"]),
      ("Heavy models (VGG, ResNet, >20 M parameters)", "MobileNetV3-Small, %.2f M parameters, "
       "%.1f MB" % (EV["parameters"] / 1e6, MET["checkpoint_mb"])),
      ("Random split – near-duplicate leaves leak into test", "Leaf-group split, 0 overlaps"),
      ("Only overall accuracy reported", "Macro precision / recall / F1, per-class F1, "
       "confusion matrix"),
      ("Black-box prediction", "Grad-CAM heatmap + stability measured"),
      ("No user system", "Login, report, history (Flask + SQLite)")], [3.4, 3.65])

H("4. Key numbers to remember")
grid([("Item", "Value", "Item", "Value"),
      ("Dataset", "PlantVillage, %s images" % N(DS["total_images"]),
       "Accuracy (test)", pct(EV["accuracy"])),
      ("Classes", "38 (14 crops: 26 diseases + 12 healthy)",
       "Macro precision", pct(EV["macro_precision"])),
      ("Split", "70 / 15 / 15 (%s / %s / %s)" % (N(DS["train"]), N(DS["validation"]),
                                                 N(DS["test"])),
       "Macro recall", pct(EV["macro_recall"])),
      ("Budgets", "B20, B40, B60, B80, B100", "Macro F1-score", pct(EV["macro_f1"])),
      ("Trained on", "B40 = %s images" % N(MET["train_images"]),
       "Parameters", N(EV["parameters"])),
      ("Input size", "160 × 160 RGB", "Model file", "%.2f MB" % MET["checkpoint_mb"]),
      ("Epochs / batch", "%d / 32, AdamW, lr 3e-4, cosine" % MET["best_epoch"],
       "CPU speed", "%.1f ms / image" % EV["latency_ms_cpu"]),
      ("Training time", "%.1f min on CPU" % MET["wall_minutes"],
       "Grad-CAM flip agreement", "%s (r = %.3f)" % (pct(fl["prediction_agreement"], 1),
                                                     fl["mean_pearson"])),
      ("Smallest class", "Potato healthy (152)", "Largest class",
       "Orange Citrus greening (5,507)")], [1.15, 2.4, 1.6, 1.9])

# ================================================================ PAGE 2
H("5. Core concepts in simple words")
B("**CNN:** layers of filters that learn image features automatically – early layers find "
  "edges and colours, deeper layers find lesion textures and shapes, the last layer gives "
  "class scores.")
B("**Transfer learning:** start from a model already trained on ImageNet (1.2 M general "
  "images) and fine-tune it on leaves – needs less data and trains faster.")
B("**Why MobileNetV3-Small:** designed for mobile devices – depthwise separable convolutions, "
  "inverted residual blocks, squeeze-and-excitation attention and hard-swish activation. "
  "Very few parameters, fast on CPU, and still accurate.")
B("**Depthwise separable convolution:** splits a normal convolution into a per-channel "
  "(depthwise) filter and a 1×1 (pointwise) mixing step – about 8–9 times less computation.")
B("**Data leakage:** when test images are almost identical to training images, accuracy looks "
  "higher than it really is. PlantVillage has several photos of the same leaf, so I grouped "
  "photos by leaf (%s groups) and kept each group in one partition." % N(DS["group_records"]))
B("**Data budget:** training on a fixed fraction (20–100%) of the training set while keeping "
  "validation and test fixed – shows how the model behaves with limited labelled data.")
B("**Augmentation:** random crop (60–100% area), horizontal flip, colour jitter "
  "(brightness/contrast/saturation ±25%, hue ±0.1) – only on training images, so test data "
  "stays clean.")
B("**Class imbalance and weighted loss:** classes range from 152 to 5,507 images. Each class "
  "weight ∝ 1/√(count), normalised to mean 1, so rare classes count more in the loss without "
  "over-correcting.")
B("**Cross-entropy loss:** −w_y · log p(y|x) – penalises low probability for the true class.")
B("**AdamW + cosine schedule:** Adam optimiser with decoupled weight decay (1e-4); the "
  "learning rate falls smoothly from 3e-4 to 0. Best checkpoint chosen by validation macro F1.")
B("**Accuracy vs macro F1:** accuracy can hide weak small classes. Precision = correct "
  "positives / predicted positives; recall = correct positives / actual positives; F1 = their "
  "harmonic mean; macro = average over all 38 classes equally.")
B("**Grad-CAM:** take the last convolution block (576 maps of 5×5), compute the gradient of "
  "the predicted class score for each map, average it to get a weight, take the weighted sum, "
  "keep positives (ReLU), upsample and overlay as a heatmap. Red = most influential region.")
B("**Explanation stability:** explain the original and a changed view (flip, +15% "
  "brightness, 10° rotation), map back, compare heatmaps with Pearson correlation and top-20% "
  "IoU – stable heatmaps are more trustworthy.")

H("6. Results to explain")
B("Training: loss 0.862 → 0.054, validation accuracy 93.28%% → 98.06%% in %d epochs; "
  "validation loss stayed close to training loss → **no overfitting**." % MET["best_epoch"])
B("Test: **%s accuracy, %s macro F1**; 34 of 38 classes have F1 above 95%%. Accuracy ≈ macro "
  "F1 means performance is balanced, not driven by large classes."
  % (pct(EV["accuracy"]), pct(EV["macro_f1"])))
B("Weakest: **%s (%s)** and **%s (%s)**. Main confusions: Tomato Late blight ↔ Early blight, "
  "Corn Northern Leaf Blight ↔ Gray leaf spot – similar brown lesions."
  % (low[0][0].replace("___", " ").replace("_", " "), pct(low[0][1]["f1"], 1),
     low[1][0].replace("___", " ").replace("_", " ").replace("Corn (maize)", "Corn"),
     pct(low[1][1]["f1"], 1)))
B("Stability (380 test images): brightness – agreement %s, r = %.3f; flip – %s, r = %.3f; "
  "rotation 10° – %s, r = %.3f (weakest, because rotation was not in training augmentation)."
  % (pct(br["prediction_agreement"], 1), br["mean_pearson"], pct(fl["prediction_agreement"], 1),
     fl["mean_pearson"], pct(ro["prediction_agreement"], 1), ro["mean_pearson"]))
B("Comparison: Mohanty 2016 GoogLeNet 99.35%%, Too 2019 DenseNet-121 99.75%%, Pal 2025 Mob-Res "
  "99.47%% (3.51 M params) – all used full training data and their own splits; mine uses 40%% data, "
  "%.2f M params and a leakage-free split, so it is a fairer, harder test." % (EV["parameters"] / 1e6))

H("7. Web application (Flask)")
B("**Flow:** register → login → upload leaf → validate → resize 184, crop 160, normalise → "
  "model + Grad-CAM → save to SQLite → result page → report / history.")
B("**Security:** passwords stored as salted hashes (Werkzeug scrypt), signed session cookies, "
  "random server-side file names, 8 MB limit, file-type and image checks, users can open only "
  "their own results (others get 404), Jinja2 auto-escaping.")
B("**Database:** users(id, name, email, password, created_at); predictions(id, user_id, "
  "image_file, cam_file, label, confidence, top5, latency_ms, created_at).")
B("**Low confidence:** below 50% the app warns the user, because the model must always pick one "
  "of the 38 known classes.")
B("**Testing:** 16 test cases – unit (data loading, corrupt file, split overlap, budgets, "
  "augmentation, inference, Grad-CAM) and functional (login, wrong password, duplicate email, "
  "prediction, invalid files, access control) – all passed.")

# ================================================================ PAGE 3
H("8. Likely viva questions with short answers")
QAS = [
    ("Why did you choose this project?", "Early disease detection helps farmers reduce losses; "
     "experts are not always available, and a phone photo plus a light model can give instant "
     "preliminary screening."),
    ("Why PlantVillage?", "Public, expert-labelled, 38 classes and 54K images, and the standard "
     "benchmark – results can be compared with published work."),
    ("Why not ResNet or VGG?", "They have 11–138 M parameters. MobileNetV3-Small has 1.56 M, runs "
     "in 22 ms on CPU and still gives 98.30% – better suited to low-cost deployment."),
    ("Why only 40% training data?", "To test the limited-data situation that real farms face. "
     "If it works with 40%, it is robust; budgets B20–B100 are prepared for the full study."),
    ("What is the novelty?", "The combination: leaf-group leakage-free split, data-budget "
     "protocol, class-weighted training, quantified Grad-CAM stability and a deployed app – "
     "not just reporting accuracy."),
    ("Why 160 × 160 and not 224?", "Smaller input → about half the computation and faster CPU "
     "training/inference; accuracy stayed above 98%."),
    ("How did you avoid overfitting?", "Pretrained weights, augmentation, weight decay, gradient "
     "clipping, checkpoint selection on validation macro F1; validation loss stayed close to "
     "training loss."),
    ("Why is the test set never used for tuning?", "Using it would leak information and inflate "
     "results; all choices were made on the validation set and the test set was used once."),
    ("Why only 5 epochs?", "CPU-only training (~6 min per epoch); with a pretrained backbone, "
     "validation macro F1 was already 97.50% and still improving slowly – a cosine schedule "
     "finished at epoch 5."),
    ("What does Grad-CAM prove?", "It shows where the model looked, so we can check it focuses on "
     "lesions and not the background. It does not prove biological cause and is coarse (5×5)."),
    ("Why measure explanation stability?", "If a slightly flipped photo gives a totally "
     "different heatmap, the explanation cannot be trusted. Correlation 0.947 under flip shows "
     "stable explanations."),
    ("Will it work on field photos?", "Not verified – PlantVillage has plain backgrounds. Field "
     "testing and background augmentation are the main future work. The app shows a "
     "preliminary result and a low-confidence warning."),
    ("What if the photo is not a leaf?", "The model still chooses one of 38 classes; low "
     "confidence is flagged. An out-of-distribution detector is planned as future work."),
    ("Why macro F1 instead of accuracy?", "Classes are imbalanced (152 to 5,507). Macro F1 "
     "treats every class equally, so a weak small class cannot hide."),
    ("Why does Tomato Early blight score lowest?", "Its brown concentric lesions look like Late "
     "blight and Target Spot; most errors are between these similar diseases."),
    ("How is the class weight calculated?", "w = 1/√(count), normalised to mean 1 – square "
     "root avoids over-correcting very small classes."),
    ("How are passwords stored?", "Never in plain text – salted hash with Werkzeug "
     "(generate_password_hash / check_password_hash)."),
    ("Why Flask and SQLite?", "Flask is light and Python-based, so the PyTorch model loads "
     "directly; SQLite needs no server and can later be replaced with MySQL."),
    ("Why PyTorch?", "Pretrained MobileNetV3 in torchvision and easy forward/backward hooks for "
     "Grad-CAM."),
    ("What are the limitations?", "Lab-style images only, single dataset, one seed and one "
     "budget fully trained, no severity estimation, closed set of 38 classes."),
    ("Future enhancements?", "Field images, rotation/background augmentation, all budgets with "
     "repeated seeds, out-of-distribution rejection, mobile app (TFLite/ONNX), Tamil interface."),
    ("Can this replace an expert?", "No – it is a fast preliminary screening tool; final "
     "diagnosis and treatment must come from an agricultural expert."),
    ("What is data leakage in your dataset?", "Multiple photos of the same leaf; a random split "
     "puts them in both train and test. Leaf-group splitting prevents it – 0 overlaps found."),
    ("How long does prediction take?", "About 22 ms for the model alone and roughly 100 ms "
     "including Grad-CAM on a normal CPU."),
]
for i, (q, a) in enumerate(QAS, 1):
    QA(i, q, a)

H("9. Quick tips for the viva")
B("Start with the 2-minute explanation, then show the app demo (login → upload → result → "
  "heatmap → history).")
B("Always quote numbers exactly: **98.30%** accuracy, **97.74%** macro F1, **1.56 M** "
  "parameters, **22 ms**. If unsure, say “as measured on the 8,050-image test set”.")
B("Admit limitations honestly (field images, single dataset) and link them to future work.")

doc.save(TMP)
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
try:
    d = word.Documents.Open(TMP, False, True)
    pages = d.ComputeStatistics(2)
    d.ExportAsFixedFormat(PDF, 17)
    d.Close(False)
finally:
    word.Quit()
os.remove(TMP)
print("pages=%d -> %s" % (pages, PDF))
