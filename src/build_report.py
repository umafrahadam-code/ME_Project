# -*- coding: utf-8 -*-
"""Build the project report (DOCX) in the chapter format of the reference
report: Ch.1 Introduction ... Ch.9 Conclusion, Appendix 1 (source code),
Appendix 2 (screenshots), References.

All numbers are read from the experiment artefacts, not typed by hand.
Usage:  python src/build_report.py   ->  ME_Plant_Disease_Detection_Project_Report_Final.docx
"""
import csv
import json
import os

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "ME_Plant_Disease_Detection_Project_Report_Final.docx")
FIG = os.path.join(ROOT, "figures")
SHOT = os.path.join(ROOT, "artifacts", "screenshots")


def jload(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as fh:
        return json.load(fh)


EV = jload("artifacts", "metrics", "test_evaluation.json")
MET = jload("artifacts", "metrics", "metrics_b40.json")
STAB = jload("artifacts", "metrics", "explanation_stability.json")
DS = jload("dataset", "PlantVillage", "splits", "dataset_summary.json")
AUD = jload("dataset", "PlantVillage", "splits", "dataset_audit.json")
with open(os.path.join(ROOT, "artifacts", "training_log_b40.csv")) as _fh:
    LOG = list(csv.DictReader(_fh))
with open(os.path.join(ROOT, "tests", "test_execution_summary.csv")) as _fh:
    TCS = list(csv.DictReader(_fh))

TITLE = ("A DATA-BUDGET-AWARE AND EXPLANATION-STABLE LIGHTWEIGHT DEEP LEARNING "
         "FRAMEWORK FOR PLANT DISEASE DETECTION")
FONT = "Times New Roman"
BODY = 14


def pct(x, d=2):
    return ("%." + str(d) + "f%%") % (100 * x)


def nice(c):
    crop, _, cond = c.partition("___")
    return "%s – %s" % (crop.replace("_", " ").replace(",", ""), cond.replace("_", " ").strip())


# ======================================================================
doc = Document()
st = doc.styles["Normal"]
st.font.name = FONT
st.font.size = Pt(BODY)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
pf = st.paragraph_format
pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
pf.space_after = Pt(6)
pf.space_before = Pt(0)

for name, size, align in [("Heading 1", 14, WD_ALIGN_PARAGRAPH.CENTER),
                          ("Heading 2", 14, WD_ALIGN_PARAGRAPH.LEFT),
                          ("Heading 3", 14, WD_ALIGN_PARAGRAPH.LEFT)]:
    h = doc.styles[name]
    h.font.name = FONT
    h.font.size = Pt(size)
    h.font.bold = True
    h.font.italic = False
    h.font.color.rgb = RGBColor(0, 0, 0)
    rpr = h.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for att in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf.get(qn(att)) is not None:
            del rf.attrib[qn(att)]
    for att in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(att), FONT)
    h.paragraph_format.alignment = align
    h.paragraph_format.space_before = Pt(12 if name != "Heading 1" else 0)
    h.paragraph_format.space_after = Pt(6 if name != "Heading 1" else 18)
    h.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    h.paragraph_format.keep_with_next = True

from docx.enum.style import WD_STYLE_TYPE  # noqa: E402

for lvl in (1, 2):  # compact table-of-contents entries
    try:
        ts = doc.styles["TOC %d" % lvl]
    except KeyError:
        ts = doc.styles.add_style("TOC %d" % lvl, WD_STYLE_TYPE.PARAGRAPH)
        ts.base_style = doc.styles["Normal"]
    ts.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    ts.paragraph_format.space_after = Pt(5)
    ts.paragraph_format.left_indent = Inches(0.3 * (lvl - 1))
    ts.font.size = Pt(14)

sec = doc.sections[0]
sec.page_height, sec.page_width = Inches(11.69), Inches(8.27)
sec.left_margin, sec.right_margin = Inches(1.0), Inches(1.0)  # same as CAMPUSMIND sample
sec.top_margin, sec.bottom_margin = Inches(1.0), Inches(1.0)


# ------------------------------------------------------------ helpers
def para(text="", bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
         indent=True, size=None, after=None, before=None, keep=False, spacing=None):
    p = _apply_break(doc.add_paragraph())
    p.alignment = align
    if indent and align == WD_ALIGN_PARAGRAPH.JUSTIFY:
        p.paragraph_format.first_line_indent = Inches(0.5)
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    if before is not None:
        p.paragraph_format.space_before = Pt(before)
    if spacing is not None:
        p.paragraph_format.line_spacing_rule = spacing
    if keep:
        p.paragraph_format.keep_with_next = True
    if text:
        add_runs(p, text, bold, italic, size)
    return p


def add_runs(p, text, bold=False, italic=False, size=None):
    """**bold** spans inside text are rendered bold."""
    parts = text.split("**")
    for i, part in enumerate(parts):
        if not part:
            continue
        r = p.add_run(part)
        r.bold = bold or (i % 2 == 1)
        r.italic = italic
        if size:
            r.font.size = Pt(size)
    return p


def bullets(items, style="List Bullet"):
    for it in items:
        p = doc.add_paragraph(style=style)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(2)
        add_runs(p, it)


def numbered(items):
    for i, it in enumerate(items, 1):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.first_line_indent = Inches(-0.3)
        p.paragraph_format.space_after = Pt(2)
        add_runs(p, "%d.  %s" % (i, it))


def label(text):
    """Small bold run-in heading like 'DISADVANTAGES' in the reference."""
    return para(text, bold=True, indent=False, align=WD_ALIGN_PARAGRAPH.LEFT,
                keep=True, after=2, before=6)


def h1(text):
    return _apply_break(doc.add_heading(text, level=1))


def h2(text):
    return doc.add_heading(text, level=2)


def h3(text):
    return doc.add_heading(text, level=3)


_NEXT_BREAK = [False]


def page_break():
    """The next paragraph starts on a new page (no empty break paragraph)."""
    _NEXT_BREAK[0] = True


def _apply_break(p):
    if _NEXT_BREAK[0]:
        p.paragraph_format.page_break_before = True
        _NEXT_BREAK[0] = False
    return p


def chapter(num, title):
    p = para("CHAPTER %d" % num, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
             indent=False, after=0, keep=True, before=24)
    h1(title)


FIGS, TABS = [], []
_bm = [0]


def bookmark(p, name):
    _bm[0] += 1
    s = OxmlElement("w:bookmarkStart")
    s.set(qn("w:id"), str(_bm[0]))
    s.set(qn("w:name"), name)
    e = OxmlElement("w:bookmarkEnd")
    e.set(qn("w:id"), str(_bm[0]))
    p._p.insert(0, s)
    p._p.append(e)


def figure(path, num, caption, width=6.0, max_h=4.3):
    """Insert an image no wider than `width` and no taller than `max_h` inches,
    so figures fit on partly filled pages instead of leaving large gaps."""
    from PIL import Image as _Im
    with _Im.open(path) as _im:
        w_px, h_px = _im.size
    width = min(width, max_h * w_px / h_px)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    p.add_run().add_picture(path, width=Inches(width))
    c = para("Fig %s %s" % (num, caption), bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
             indent=False, size=14, after=12)
    bm = "fig_%s" % num.replace(".", "_")
    bookmark(c, bm)
    FIGS.append((num, caption, bm))


def table(header, rows, num=None, caption=None, widths=None, size=14):
    if caption:
        c = para("Table %s %s" % (num, caption), bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
                 indent=False, size=14, after=4, keep=True, before=6)
        bm = "tab_%s" % num.replace(".", "_")
        bookmark(c, bm)
        TABS.append((num, caption, bm))
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        cell = t.rows[0].cells[i]
        cell.text = ""
        r = cell.paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(size)
        shade(cell, "D9E7D6")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(v))
            r.font.size = Pt(size)
    for row in t.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.first_line_indent = Inches(0)
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for ri, row in enumerate(t.rows):
        trPr = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        trPr.append(cs)
        if ri == 0:
            th = OxmlElement("w:tblHeader")
            trPr.append(th)
        if ri < len(t.rows) - 1 and len(t.rows) <= 12:  # keep small tables together
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.keep_with_next = True
    if widths:
        for row in t.rows:
            for cell, w in zip(row.cells, widths):
                cell.width = Inches(w)
    para("", after=4)
    return t


def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def kv_lines(pairs):
    """'System        : PC or Laptop' lines, aligned with a tab stop."""
    for k, v in pairs:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.tab_stops.add_tab_stop(Inches(2.9))
        p.paragraph_format.tab_stops.add_tab_stop(Inches(3.1))
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.first_line_indent = Inches(0)
        p.paragraph_format.left_indent = Inches(3.1)
        p.paragraph_format.first_line_indent = Inches(-2.6)
        p.add_run(k + "\t:\t" + v)


def field(p, instr):
    r = p.add_run()
    b = OxmlElement("w:fldChar")
    b.set(qn("w:fldCharType"), "begin")
    r._r.append(b)
    r2 = p.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = " %s " % instr
    r2._r.append(it)
    r3 = p.add_run()
    s = OxmlElement("w:fldChar")
    s.set(qn("w:fldCharType"), "separate")
    r3._r.append(s)
    p.add_run("1")
    r4 = p.add_run()
    e = OxmlElement("w:fldChar")
    e.set(qn("w:fldCharType"), "end")
    r4._r.append(e)


def footer_page_number(section, fmt, start):
    section.footer.is_linked_to_previous = False
    fp = section.footer.paragraphs[0]
    for r in list(fp.runs):
        r._r.getparent().remove(r._r)
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if fmt:
        field(fp, "PAGE")
    sp = section._sectPr
    for old in sp.findall(qn("w:pgNumType")):
        sp.remove(old)
    pg = OxmlElement("w:pgNumType")
    if fmt:
        pg.set(qn("w:fmt"), fmt)
    pg.set(qn("w:start"), str(start))
    sp.append(pg)


def new_section():
    s = doc.add_section(WD_SECTION.NEW_PAGE)
    return s


def code_block(path, title):
    h2(title)
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        src = fh.read().rstrip("\n").split("\n")
    for line in src:
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(line.replace("\t", "    ") or " ")
        r.font.size = Pt(BODY)  # Times New Roman 14, as in the CAMPUSMIND appendix


# ---------------------------------------------- FRONT MATTER (roman)
# The report starts directly with the Abstract.
footer_page_number(doc.sections[0], "lowerRoman", 1)

para(TITLE, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, size=16, after=18,
     spacing=WD_LINE_SPACING.SINGLE)
h1("ABSTRACT")
para("Plant diseases reduce crop yield, and early recognition depends on scarce experts. "
     "This project develops a lightweight, explainable deep learning system that identifies "
     "plant leaf diseases from a photograph.")
para("The PlantVillage colour dataset (%s images, 38 crop–disease classes covering 14 crops) "
     "was audited for unreadable files and exact duplicates and divided with a leaf-group-aware "
     "split into training (%s), validation (%s) and test (%s) partitions. Controlled training "
     "budgets of 20%%, 40%%, 60%%, 80%% and 100%% were sampled from the training partition only. "
     "A MobileNetV3-Small network pretrained on ImageNet was fine-tuned on the 40%% budget "
     "(%s images) at 160 × 160 pixels, using label-preserving augmentation and class-weighted "
     "cross-entropy to counter class imbalance."
     % ("{:,}".format(DS["total_images"]), "{:,}".format(DS["train"]),
        "{:,}".format(DS["validation"]), "{:,}".format(DS["test"]),
        "{:,}".format(MET["train_images"])))
para("On the held-out test set of %s images the model achieved an accuracy of **%s**, macro "
     "precision of %s, macro recall of %s and macro F1-score of **%s**, with only %.2f million "
     "parameters, a %.1f MB checkpoint and an average CPU inference time of %.0f ms per image. "
     "Grad-CAM heatmaps explain each prediction; under horizontal flips the prediction agreed "
     "in %s of cases with a mean heatmap correlation of %.3f. The model is deployed in a Flask "
     "web application with login, upload, Grad-CAM view, reports and history."
     % ("{:,}".format(EV["test_images"]), pct(EV["accuracy"]), pct(EV["macro_precision"]),
        pct(EV["macro_recall"]), pct(EV["macro_f1"]), EV["parameters"] / 1e6,
        MET["checkpoint_mb"], EV["latency_ms_cpu"],
        pct(STAB["views"]["horizontal_flip"]["prediction_agreement"], 1),
        STAB["views"]["horizontal_flip"]["mean_pearson"]))
para("**Keywords:** Plant disease detection, deep learning, MobileNetV3-Small, transfer "
     "learning, limited data, Grad-CAM, explainable AI, Flask.", indent=False)

page_break()
h1("TABLE OF CONTENTS")
p = doc.add_paragraph()
field(p, 'TOC \\o "1-2" \\h \\z \\u')

LOF_ANCHOR = h1("LIST OF FIGURES")
LOF_PARA = doc.add_paragraph()
LOT_ANCHOR = h1("LIST OF TABLES")
LOT_PARA = doc.add_paragraph()
h1("LIST OF ABBREVIATIONS")
table(["Abbreviation", "Expansion"], [
    ("AI", "Artificial Intelligence"), ("CNN", "Convolutional Neural Network"),
    ("CPU", "Central Processing Unit"), ("CSS", "Cascading Style Sheets"),
    ("DFD", "Data Flow Diagram"), ("F1", "Harmonic mean of precision and recall"),
    ("GPU", "Graphics Processing Unit"),
    ("Grad-CAM", "Gradient-weighted Class Activation Mapping"),
    ("HTML", "HyperText Markup Language"), ("IoU", "Intersection over Union"),
    ("ML", "Machine Learning"), ("ReLU", "Rectified Linear Unit"),
    ("SQL", "Structured Query Language"), ("SVM", "Support Vector Machine"),
    ("UML", "Unified Modeling Language"), ("XAI", "Explainable Artificial Intelligence"),
], widths=[1.6, 4.0])

# ---------------------------------------------- MAIN BODY (arabic)
s3 = new_section()
footer_page_number(s3, "decimal", 1)

# ============================== CHAPTER 1
p = para("CHAPTER 1", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, after=0, keep=True)
h1("INTRODUCTION")
para("Agriculture supports the livelihood of a large part of the population, and plant "
     "diseases are one of the main causes of loss in crop yield and quality. Fungal, bacterial "
     "and viral infections usually appear first on the leaves as spots, lesions, mildew, "
     "blight, mosaic patterns, curling or yellowing. When these symptoms are recognised early, "
     "the farmer can isolate infected plants and seek appropriate advice before the disease "
     "spreads across the field.")
para("The conventional way of identifying a disease is visual inspection by the farmer or by "
     "an agricultural expert. Expert inspection is reliable but is not always available at the "
     "right time, especially in remote villages and during peak seasons when many fields need "
     "attention. Different diseases can also produce visually similar symptoms, so the "
     "decision depends heavily on experience. Laboratory confirmation is accurate but slow and "
     "costly for routine screening.")
para("Advances in computer vision now make it possible to recognise disease symptoms "
     "automatically from a photograph of a leaf. A deep convolutional neural network can learn "
     "the colour, texture and shape patterns of each disease from labelled images and then "
     "classify a new image within a fraction of a second. This project builds such a system "
     "with three practical goals: it must be **lightweight** enough to run on an ordinary "
     "computer, it must remain reliable when the amount of labelled training data is limited, "
     "and it must **explain** its decisions so that users can check whether the model looked "
     "at the diseased region of the leaf.")
h2("1.1 DEEP LEARNING")
para("Deep learning is a branch of machine learning in which models built from many layers of "
     "artificial neurons learn useful representations directly from raw data. In a "
     "convolutional neural network (CNN), the early layers detect simple patterns such as "
     "edges and colour blobs, the middle layers combine them into textures and lesion shapes, "
     "and the final layers map these features to class scores. Because the features are "
     "learned rather than designed by hand, CNNs adapt well to the large variety of disease "
     "symptoms found on different crops.")
para("Training a deep network from scratch requires a large dataset. **Transfer learning** "
     "reduces this requirement by starting from a network that has already learned general "
     "visual features on the ImageNet dataset and fine-tuning it on the plant-disease images. "
     "**Lightweight architectures** such as MobileNetV3-Small use depthwise separable "
     "convolutions, inverted residual blocks and squeeze-and-excitation attention to keep the "
     "number of parameters and the computation low, which makes them suitable for laptops, "
     "edge devices and web servers without a GPU.")
h2("1.2 IMAGE PROCESSING")
para("Image processing prepares the raw photograph so that the network receives consistent "
     "input. In this project each uploaded image is decoded and converted to the RGB colour "
     "space, resized so that its shorter side is 184 pixels, centre-cropped to 160 × 160 "
     "pixels, converted to a tensor and normalised with the ImageNet channel mean and "
     "standard deviation. The same deterministic pipeline is used during validation, testing "
     "and in the web application, so the model always sees images prepared in the same way.")
para("During training, label-preserving **data augmentation** creates varied views of each "
     "training image: random resized cropping, horizontal flipping and mild changes of "
     "brightness, contrast, saturation and hue. These transformations imitate natural "
     "variation in camera position and lighting without removing the disease symptoms, which "
     "helps the model generalise when the training budget is small.")
h2("1.3 EXPLAINABLE ARTIFICIAL INTELLIGENCE")
para("A prediction is more useful when the user can see why it was made. Gradient-weighted "
     "Class Activation Mapping (Grad-CAM) uses the gradients of the predicted class score with "
     "respect to the last convolutional feature maps to produce a coarse heatmap of the image "
     "regions that most influenced the decision. The heatmap is overlaid on the leaf so that "
     "users can confirm that the model attended to the lesions rather than to the background. "
     "This project also measures how stable these explanations remain when the same leaf is "
     "flipped, brightened or slightly rotated.")
h2("1.4 PROBLEM STATEMENT")
para("Given leaf images belonging to 38 crop–disease classes, the problem is to build a "
     "compact image classifier that (i) achieves high accuracy and balanced performance across "
     "frequent and rare classes when trained on a limited, controlled share of the labelled "
     "data, (ii) provides stable visual explanations of its predictions, and (iii) is "
     "available to end users through a simple, secure web interface.")
h2("1.5 OBJECTIVES")
bullets([
    "To audit the PlantVillage dataset and create a leakage-free, leaf-group-aware "
    "training, validation and test split with controlled training budgets.",
    "To design a preprocessing and augmentation pipeline that preserves disease symptoms.",
    "To fine-tune a lightweight MobileNetV3-Small classifier with class-weighted loss and "
    "evaluate it with accuracy, macro precision, macro recall and macro F1-score.",
    "To generate Grad-CAM explanations and quantify their stability under "
    "label-preserving transformations.",
    "To deploy the model in a Flask web application with authentication, prediction, "
    "explanation, report and history modules.",
])
h2("1.6 ORGANISATION OF THE REPORT")
para("Chapter 2 reviews related work. Chapter 3 studies the existing and proposed systems. "
     "Chapter 4 lists the hardware and software requirements. Chapter 5 presents the system "
     "architecture, UML diagrams and data flow diagrams. Chapter 6 describes the software used. "
     "Chapter 7 explains the implementation modules. Chapter 8 covers testing and results, and "
     "Chapter 9 concludes the report with future enhancements. Appendix 1 contains the source "
     "code and Appendix 2 the screenshots of the application.")

# ============================== CHAPTER 2
chapter(2, "LITERATURE SURVEY")
LIT = [
    ("Hughes, D. P. and Salathé, M. (2015)", "An open access repository of images on plant "
     "health to enable the development of mobile disease diagnostics",
     "The authors released the PlantVillage dataset, containing more than 50,000 expertly "
     "curated images of healthy and infected leaves of 14 crop species across 38 classes. The "
     "images were captured on a uniform background under controlled conditions, and the "
     "dataset was made openly available to encourage research on automatic, smartphone-based "
     "disease diagnosis. PlantVillage has since become the standard benchmark for plant "
     "disease classification and is the dataset used in this project.",
     "Images were taken in controlled settings with plain backgrounds, so models trained only "
     "on this dataset may not transfer directly to cluttered field photographs."),
    ("Mohanty, S. P., Hughes, D. P. and Salathé, M. (2016)", "Using deep learning for "
     "image-based plant disease detection",
     "This study trained AlexNet and GoogLeNet on 54,306 PlantVillage images and compared "
     "training from scratch with transfer learning, as well as colour, grey-scale and "
     "segmented versions of the images. The best configuration, GoogLeNet with transfer "
     "learning, reached 99.35% accuracy on a held-out test set, showing that deep CNNs can "
     "recognise crop–disease pairs very accurately.",
     "When the trained model was tested on images collected from other sources, accuracy "
     "dropped sharply (to about 31%), revealing a strong dependence on the capture conditions "
     "of the training data. The networks used are also large for mobile deployment."),
    ("Sladojevic, S., Arsenovic, M., Anderla, A., Culibrk, D. and Stefanovic, D. (2016)",
     "Deep neural networks based recognition of plant diseases by leaf image classification",
     "The authors collected leaf images from the internet, augmented them, and fine-tuned a "
     "CaffeNet model to recognise 13 types of plant disease plus healthy leaves and "
     "background. The model achieved an average precision of 96.3%, demonstrating that CNNs "
     "trained on augmented web images can distinguish multiple diseases.",
     "The dataset was relatively small and assembled from web searches, the number of classes "
     "was limited, and the model gave no explanation of its decisions."),
    ("Brahimi, M., Boukhalfa, K. and Moussaoui, A. (2017)", "Deep learning for tomato "
     "diseases: classification and symptoms visualization",
     "Using about 14,800 tomato leaf images from PlantVillage covering nine diseases, the "
     "authors fine-tuned AlexNet and GoogLeNet and obtained up to 99.18% accuracy. They also "
     "visualised the regions used by the network, showing that the learned features "
     "correspond to visible symptoms, which increases trust in the model.",
     "The work is restricted to a single crop, and the visualisation was qualitative; the "
     "stability of the visualisations was not measured."),
    ("Ferentinos, K. P. (2018)", "Deep learning models for plant disease detection and "
     "diagnosis",
     "Several CNN architectures were trained on an open database of 87,848 images covering "
     "25 plant species in 58 classes, including images captured in real cultivation "
     "conditions. The VGG model achieved the best success rate of 99.53%, and the study "
     "discussed the potential of such models as early-warning tools.",
     "VGG has well over 100 million parameters, making it heavy for low-cost devices, and "
     "performance was lower when training on laboratory images and testing on field images."),
    ("Barbedo, J. G. A. (2018)", "Impact of dataset size and variety on the effectiveness of "
     "deep learning and transfer learning for plant disease classification",
     "This study analysed how the size and variety of the training data influence CNN "
     "accuracy for plant disease recognition. It showed that small and insufficiently diverse "
     "datasets lead to poor generalisation, and that transfer learning reduces but does not "
     "remove the dependence on data quantity.",
     "The study highlights the problem but does not propose a controlled protocol for "
     "measuring performance at different training budgets, which this project adopts."),
    ("Too, E. C., Yujian, L., Njuki, S. and Yingchun, L. (2019)", "A comparative study of "
     "fine-tuning deep learning models for plant disease identification",
     "VGG-16, Inception-v4, ResNet-50, ResNet-101, ResNet-152 and DenseNet-121 were "
     "fine-tuned on PlantVillage. DenseNet-121 achieved the highest test accuracy of 99.75% "
     "while using fewer parameters than the other deep models and without overfitting.",
     "All compared networks are still considerably larger than mobile architectures, and the "
     "evaluation used the full training set only."),
    ("Howard, A. et al. (2019)", "Searching for MobileNetV3",
     "MobileNetV3 was designed using hardware-aware neural architecture search combined with "
     "the NetAdapt algorithm, inverted residual blocks, squeeze-and-excitation modules and the "
     "hard-swish activation. The Small variant targets low-resource devices and improves "
     "accuracy and latency compared with MobileNetV2 on ImageNet.",
     "The architecture was evaluated on general image classification; its behaviour on "
     "plant-disease data and under limited training data must be measured separately."),
    ("Selvaraju, R. R. et al. (2017)", "Grad-CAM: visual explanations from deep networks via "
     "gradient-based localization",
     "Grad-CAM produces class-discriminative localisation maps for any CNN by weighting the "
     "final convolutional feature maps with the spatially averaged gradients of the target "
     "class score. It requires no change to the network architecture and is widely used to "
     "inspect what image regions drive a prediction.",
     "The maps are coarse (limited by the final feature-map resolution) and do not prove "
     "causality; their consistency under small image changes is not guaranteed."),
    ("Pal, C., Karmakar, S., Mukherjee, I. and Chakrabarti, P. P. (2025)", "A lightweight and "
     "explainable CNN model for empowering plant disease diagnosis",
     "The authors proposed Mob-Res, a parallel network combining a MobileNetV2 feature path "
     "with a residual convolution path, using about 3.51 million parameters. Evaluated on the "
     "Plant Disease Expert and PlantVillage datasets, it reported average accuracies of 97.73% "
     "and 99.47% respectively, and used Grad-CAM, Grad-CAM++ and LIME to explain predictions.",
     "The explanations are presented qualitatively, and model behaviour under reduced "
     "training data is not studied. This project addresses both points with a smaller "
     "backbone (%.2f million parameters)." % (EV["parameters"] / 1e6)),
]
for i, (auth, title, desc, draw) in enumerate(LIT, 1):
    para("[%d] %s – “%s”" % (i, auth, title), bold=True, indent=False,
         align=WD_ALIGN_PARAGRAPH.JUSTIFY, keep=True, before=6, after=2)
    para("**Description:** " + desc, indent=False)
    para("**Drawbacks:** " + draw, indent=False)

# ============================== CHAPTER 3
chapter(3, "SYSTEM STUDY")
h2("3.1 EXISTING SYSTEM")
para("In the existing approach, plant diseases are identified mainly by manual visual "
     "inspection carried out by farmers or agricultural extension officers. The farmer "
     "observes symptoms on the leaves and either relies on personal experience or carries "
     "samples to an expert or a laboratory. Laboratory methods such as microscopy, culturing "
     "and molecular tests are accurate but need trained staff, equipment and several days.")
para("Automatic systems reported in the literature mostly train large CNNs such as AlexNet, "
     "VGG or ResNet on the full PlantVillage training set and report a single accuracy value. "
     "Such systems do not show how performance changes when fewer labelled images are "
     "available, often report only overall accuracy (which hides weak minority classes), are "
     "heavy for low-cost hardware, and present a prediction without any explanation that a "
     "user could verify.")
label("DISADVANTAGES")
bullets([
    "Manual inspection is time consuming and depends on the availability and experience of "
    "experts.",
    "Similar-looking symptoms of different diseases lead to misidentification.",
    "Large deep models need high memory and computation, limiting deployment.",
    "Performance under limited labelled data and on rare classes is not measured.",
    "Predictions are given as a black box without visual explanation.",
    "Data leakage between training and test images can inflate reported accuracy.",
])
h2("3.2 PROPOSED SYSTEM")
para("The proposed system is a lightweight, explainable, web-based plant disease detection "
     "system. The dataset is audited and split by leaf groups before any augmentation, so that "
     "near-identical photographs of the same leaf never appear in both training and test "
     "data. Training is performed on a controlled 40% budget of the training partition to "
     "reflect a limited-data setting. A pretrained MobileNetV3-Small network is fine-tuned "
     "with label-preserving augmentation and class-weighted cross-entropy loss, and the best "
     "checkpoint is selected by validation macro F1-score.")
para("The trained model is exported as a versioned bundle and served by a Flask web "
     "application. A registered user uploads a leaf photograph; the system validates the "
     "file, predicts the top-5 classes with confidence, highlights the decisive regions with "
     "Grad-CAM, warns when confidence is low, and stores the result in the user's history "
     "from which a printable report can be produced.")
label("ADVANTAGES")
bullets([
    "Fast prediction (about %.0f ms per image on a CPU) from a single leaf photograph."
    % EV["latency_ms_cpu"],
    "High accuracy (%s) and balanced macro F1-score (%s) on unseen test images."
    % (pct(EV["accuracy"]), pct(EV["macro_f1"])),
    "Lightweight model with %.2f million parameters – no GPU needed for inference."
    % (EV["parameters"] / 1e6),
    "Grad-CAM heatmap shows why a prediction was made; stability is quantified.",
    "Secure user accounts, prediction history and printable reports.",
    "Leakage-free evaluation protocol with fixed seeds for reproducibility.",
])

# ============================== CHAPTER 4
chapter(4, "SYSTEM REQUIREMENTS")
h2("4.1 HARDWARE REQUIREMENTS")
kv_lines([("System", "PC or Laptop"), ("Processor", "Intel Core i5 or higher"),
          ("RAM", "8 GB (16 GB recommended for training)"),
          ("Hard Disk", "20 GB free space"),
          ("GPU", "Optional (the model was trained and runs on CPU)"),
          ("Monitor", "1366 × 768 or higher resolution")])
h2("4.2 SOFTWARE REQUIREMENTS")
kv_lines([("Operating System", "Windows 10 / 11"), ("Front End", "HTML, CSS, Jinja2 templates"),
          ("Back End", "Python 3.12, Flask 3.1"),
          ("Deep Learning", "PyTorch 2.3, torchvision 0.18"),
          ("Libraries", "Pillow, NumPy, Matplotlib"),
          ("Database", "SQLite 3"), ("IDE", "Visual Studio Code"),
          ("Browser", "Google Chrome / Microsoft Edge")])

# ============================== CHAPTER 5
chapter(5, "SYSTEM DESIGN")
h2("5.1 SYSTEM ARCHITECTURE")
para("System architecture describes the high-level structure of the software system, its "
     "components and the way they interact. The proposed system has two parts. The offline "
     "training pipeline audits and splits the dataset, applies preprocessing and "
     "augmentation, trains the MobileNetV3-Small classifier and exports a model bundle "
     "containing the weights, the class list and the preprocessing configuration. The online "
     "Flask web application loads this bundle once at start-up and serves authentication, "
     "image upload, prediction with Grad-CAM, reports and history, storing users and "
     "predictions in an SQLite database.")
figure(os.path.join(FIG, "design", "fig_5_1_architecture.png"), "5.1", "System Architecture", 6.2)
h2("5.2 UML DIAGRAMS")
para("A UML (Unified Modeling Language) diagram visually represents a system together with "
     "its main actors, roles, actions, artefacts and classes, in order to better understand, "
     "alter, maintain or document the system. The following UML diagrams describe the "
     "proposed system:")
bullets(["Use Case Diagram", "Class Diagram", "Sequence Diagram", "Activity Diagram"])
h3("5.2.1 Use Case Diagram")
para("A use case diagram shows the interactions between actors and the system. The primary "
     "actor is the user (a farmer, student or agricultural officer) who registers, logs in, "
     "uploads a leaf image, views the prediction, confidence and Grad-CAM heatmap, prints the "
     "report, reviews the history and logs out. The trained model acts as a secondary actor "
     "that supplies the prediction and explanation.")
figure(os.path.join(FIG, "design", "fig_5_2_use_case.png"), "5.2", "Use Case Diagram", 5.6)
h3("5.2.2 Class Diagram")
para("A class diagram is a static structure diagram that describes the classes of a system, "
     "their attributes, operations and relationships.")
bullets([
    "**LeafDataset:** loads images listed in the split manifest and applies the transforms.",
    "**MobileNetV3Small:** the CNN with a 38-way classification head.",
    "**Trainer:** builds the model, runs the training loop with weighted loss and selects "
    "the best checkpoint.",
    "**GradCAM:** hooks the last convolutional block to compute and overlay heatmaps.",
    "**FlaskApp:** handles the web routes for authentication, prediction, reports and "
    "history.",
    "**Database:** the users and predictions tables in SQLite.",
])
figure(os.path.join(FIG, "design", "fig_5_3_class.png"), "5.3", "Class Diagram", 6.2)
h3("5.2.3 Sequence Diagram")
para("A sequence diagram shows object interactions arranged in time order. The user logs in "
     "through the browser, the Flask server verifies the hashed password from the database, "
     "the uploaded image is validated and resized, the model and Grad-CAM produce the "
     "probabilities and heatmap, the prediction is inserted into the database and the result "
     "page is returned to the user.")
figure(os.path.join(FIG, "design", "fig_5_4_sequence.png"), "5.4", "Sequence Diagram", 6.2)
h3("5.2.4 Activity Diagram")
para("An activity diagram represents the flow of control from one activity to another. "
     "Invalid uploads (unsupported type, unreadable or very small images) return the user to "
     "the upload step with an error message; valid images continue through preprocessing, "
     "prediction, explanation and storage.")
figure(os.path.join(FIG, "design", "fig_5_5_activity.png"), "5.5", "Activity Diagram", 4.4)
h2("5.3 DATA FLOW DIAGRAM")
para("A data flow diagram shows how data is processed and transferred in a system. It "
     "identifies the external entities, processes and data stores, and how the inputs are "
     "transformed into outputs. Level 0 shows the whole system as a single process; Level 1 "
     "divides it into its main processes; Level 2 expands the prediction process.")
figure(os.path.join(FIG, "design", "fig_5_6_dfd0.png"), "5.6", "Level 0 Data Flow Diagram", 5.6)
figure(os.path.join(FIG, "design", "fig_5_7_dfd1.png"), "5.7", "Level 1 Data Flow Diagram", 6.2)
figure(os.path.join(FIG, "design", "fig_5_8_dfd2.png"), "5.8",
       "Level 2 Data Flow Diagram (Prediction process)", 6.2)
h2("5.4 DATABASE DESIGN")
para("The application uses an SQLite database with two tables. Passwords are never stored in "
     "plain text; they are hashed with the scrypt algorithm provided by Werkzeug.")
table(["Field", "Type", "Description"], [
    ("id", "INTEGER (PK)", "Auto-increment user identifier"),
    ("name", "TEXT", "Full name"),
    ("email", "TEXT (UNIQUE)", "Login identifier"),
    ("password", "TEXT", "Salted password hash"),
    ("created_at", "TEXT", "Registration timestamp")],
    "5.1", "users table", widths=[1.4, 1.6, 3.0])
table(["Field", "Type", "Description"], [
    ("id", "INTEGER (PK)", "Prediction / report number"),
    ("user_id", "INTEGER (FK)", "Owner of the prediction"),
    ("image_file, cam_file", "TEXT", "Stored input and Grad-CAM image names"),
    ("orig_name", "TEXT", "Original upload file name"),
    ("label", "TEXT", "Top-1 class"),
    ("confidence", "REAL", "Top-1 probability"),
    ("top5", "TEXT", "Top-5 class indices and probabilities"),
    ("latency_ms", "REAL", "Inference + Grad-CAM time"),
    ("created_at", "TEXT", "Prediction timestamp")],
    "5.2", "predictions table", widths=[1.8, 1.4, 2.8])

# ============================== CHAPTER 6
chapter(6, "SOFTWARE DESCRIPTION")
h2("6.1 FRONT END")
h3("6.1.1 HTML")
para("HTML (HyperText Markup Language) is the standard markup language for creating web "
     "pages. It describes the structure of a page using elements such as headings, "
     "paragraphs, forms, images and tables. In this project HTML templates define the login, "
     "registration, upload, result, report and history pages. Form elements collect user "
     "credentials and the leaf image, and the file input restricts uploads to image types.")
h3("6.1.2 CSS")
para("CSS (Cascading Style Sheets) controls the presentation of HTML documents, including "
     "colours, fonts, spacing and layout. A single stylesheet gives the application a "
     "consistent green agricultural theme, a responsive grid layout that adapts to phone "
     "screens, confidence bars for the top-5 predictions and a print style that hides "
     "navigation elements so that the report can be printed or saved as PDF.")
h3("6.1.3 Jinja2 Templates")
para("Jinja2 is the template engine used by Flask. It allows Python values such as the "
     "predicted class, confidence and history records to be inserted into HTML pages, "
     "supports template inheritance through a common base layout, and escapes user-supplied "
     "text automatically, which protects the pages from script injection.")
h2("6.2 BACK END")
h3("6.2.1 Python")
para("Python is a high-level, interpreted, dynamically typed programming language created by "
     "Guido van Rossum and first released in 1991. Its clear syntax, large standard library "
     "and rich ecosystem of scientific packages have made it the most widely used language "
     "for machine learning. In this project Python is used for every stage: dataset auditing, "
     "splitting, training, evaluation, explanation analysis, figure generation and the web "
     "server, which keeps the whole pipeline consistent and reproducible.")
h3("6.2.2 PyTorch and torchvision")
para("PyTorch is an open-source deep learning framework that provides tensors with automatic "
     "differentiation and a flexible, Python-first way of defining neural networks. "
     "torchvision supplies image transforms and pretrained models, including "
     "MobileNetV3-Small with ImageNet weights. PyTorch's forward and backward hooks give "
     "direct access to feature maps and gradients, which are required for Grad-CAM.")
h3("6.2.3 Flask")
para("Flask is a lightweight Python web framework built on the Werkzeug toolkit and the "
     "Jinja2 template engine. It maps URLs to Python functions (routes), handles form and "
     "file uploads, manages signed session cookies for logged-in users and provides "
     "secure password hashing helpers. The trained model is loaded once when the Flask "
     "application starts, so each request only performs inference.")
h3("6.2.4 Supporting Libraries")
para("**Pillow** decodes and validates uploaded images and performs resizing and colour "
     "adjustments. **NumPy** supports numerical operations. **Matplotlib** is used to draw "
     "training curves, confusion matrices, the design diagrams in this report and the colour "
     "map for Grad-CAM overlays.")
h2("6.3 DATABASE – SQLITE")
para("SQLite is a self-contained, serverless, zero-configuration SQL database engine that "
     "stores the whole database in a single file. It is included in the Python standard "
     "library through the sqlite3 module. SQLite is well suited for this application because "
     "it requires no separate database server, supports standard SQL with transactions and "
     "constraints such as UNIQUE and FOREIGN KEY, and can be replaced with MySQL or "
     "PostgreSQL later without changing the application logic.")

# ============================== CHAPTER 7
chapter(7, "SYSTEM IMPLEMENTATION")
h2("7.1 MODULE LIST")
bullets(["Dataset Acquisition and Limited-Data Management module",
         "Preprocessing and Augmentation module",
         "Model Training module",
         "Explainable AI (Grad-CAM) module",
         "User Authentication module",
         "Prediction, Report and History module"])
h2("7.2 MODULE DESCRIPTION")
h3("7.2.1 Dataset Acquisition and Limited-Data Management Module")
para("The PlantVillage colour dataset was downloaded from its public repository. It "
     "contains %s images of 14 crops in 38 classes (26 diseases and 12 healthy classes). "
     "Every file was decoded to check readability: %s files were accepted and %d rejected. "
     "Exact-duplicate detection found %d duplicate groups containing %d files."
     % ("{:,}".format(DS["total_images"]), "{:,}".format(AUD["accepted"]), AUD["rejected"],
        AUD["exact_duplicate_groups"], AUD["files_in_duplicate_groups"]))
para("PlantVillage contains several photographs of the same physical leaf. To avoid data "
     "leakage, images were grouped by leaf (%s groups) and whole groups were assigned to one "
     "partition, giving a 70 / 15 / 15 split with seed 42. Duplicate groups were checked to "
     "ensure that no group crosses partitions. Training budgets were then sampled per class "
     "from the training partition only, while validation and test sets stay fixed."
     % "{:,}".format(DS["group_records"]))
budget_rows = [(b["id"], "%d%%" % int(100 * b["fraction"]), "{:,}".format(b["images"]),
                "{:,}".format(DS["validation"]), "{:,}".format(DS["test"]))
               for b in DS["budgets"]]
table(["Budget", "Fraction", "Training images", "Validation", "Test"], budget_rows,
      "7.1", "Controlled training budgets", widths=[1.0, 1.0, 1.6, 1.2, 1.0])
figure(os.path.join(FIG, "fig_class_distribution.png"), "7.1",
       "Class distribution of the PlantVillage dataset", 6.0)
h3("7.2.2 Preprocessing and Augmentation Module")
para("All images are converted to RGB. For evaluation and inference, each image is resized "
     "to 184 pixels on the shorter side, centre-cropped to 160 × 160 and normalised with the "
     "ImageNet mean (0.485, 0.456, 0.406) and standard deviation (0.229, 0.224, 0.225). For "
     "training, the following label-preserving augmentations are applied on the fly:")
bullets(["Random resized crop to 160 × 160 covering 60–100% of the image area.",
         "Random horizontal flip with probability 0.5.",
         "Colour jitter: brightness, contrast and saturation ±25%, hue ±0.10.",
         "Augmentation is applied to the training partition only."])
para("Class imbalance (the smallest class, %s, has %d images while the largest, %s, has %s) "
     "is handled with class-weighted cross-entropy. Each class weight is proportional to the "
     "inverse square root of its training count and normalised to a mean of one, so rare "
     "classes contribute more to the loss without over-correcting."
     % (nice(DS["min_class"][0]), DS["min_class"][1], nice(DS["max_class"][0]),
        "{:,}".format(DS["max_class"][1])))
h3("7.2.3 Model Training Module")
para("MobileNetV3-Small pretrained on ImageNet is used as the feature extractor. Its final "
     "1000-way linear layer is replaced by a 38-way layer, giving %s trainable parameters "
     "in total. The model was trained on the B40 budget (%s images) with the following "
     "settings:" % ("{:,}".format(EV["parameters"]), "{:,}".format(MET["train_images"])))
table(["Parameter", "Value"], [
    ("Input size", "160 × 160 × 3"), ("Optimiser", "AdamW (weight decay 1e-4)"),
    ("Initial learning rate", "3 × 10⁻⁴ with cosine annealing"),
    ("Batch size", "32"), ("Epochs", "%d" % len(LOG)),
    ("Loss", "Class-weighted cross-entropy"), ("Gradient clipping", "Norm 1.0"),
    ("Checkpoint selection", "Best validation macro F1-score"),
    ("Random seed", "42"), ("Device", "CPU (%.1f minutes total)" % MET["wall_minutes"])],
    "7.2", "Training configuration", widths=[2.4, 3.4])
h3("7.2.4 Explainable AI (Grad-CAM) Module")
para("For an input image, the module records the activations A^k of the last convolutional "
     "block of MobileNetV3-Small (576 feature maps of size 5 × 5 for a 160-pixel input) and "
     "the gradients of the predicted class score y^c with respect to them. The importance of "
     "each feature map is the spatial average of its gradient, α_k^c = (1/Z) Σ_i Σ_j "
     "∂y^c/∂A^k_ij, and the class activation map is L^c = ReLU(Σ_k α_k^c A^k). The map is "
     "normalised to [0, 1], upsampled to the image size, coloured with the jet colour map and "
     "blended with the input image.")
para("To measure explanation stability, %d test images (%d per class) were explained in "
     "their original form and after a label-preserving transformation. The transformed map "
     "was mapped back to the original geometry and compared using the Pearson correlation and "
     "the IoU of the 20%% most activated pixels; prediction agreement was also recorded."
     % (STAB["images"], STAB["per_class"]))
h3("7.2.5 User Authentication Module")
para("New users register with their name, email address and a password of at least six "
     "characters. The password is stored as a salted hash; duplicate email addresses are "
     "rejected by a UNIQUE constraint. During login the hash is verified and the user "
     "identifier is stored in a signed session cookie. All prediction, report and history "
     "pages require login, and every database query is filtered by the logged-in user so that "
     "a user can never open another user's results.")
h3("7.2.6 Prediction, Report and History Module")
para("The uploaded file is checked for an allowed extension (JPG, PNG, BMP, WEBP), a maximum "
     "size of 8 MB, a valid image signature and a minimum size of 32 × 32 pixels. The image "
     "is preprocessed and passed to the model; Grad-CAM is computed in the same pass. The "
     "top-5 classes and probabilities, the heatmap and the processing time are stored with a "
     "server-generated random file name. The result page shows the crop, condition and "
     "confidence, and flags predictions below 50% confidence as uncertain because the model "
     "can only choose among the 38 known classes.")
bullets(["**Result page:** prediction, confidence, input image, Grad-CAM heatmap, top-5 bars.",
         "**Report page:** printable summary that can be saved as PDF from the browser.",
         "**History page:** all previous predictions of the user with date and time."])

# ============================== CHAPTER 8
chapter(8, "SYSTEM TESTING")
h2("8.1 SYSTEM TESTING")
para("Software testing is the process of executing a program with the intent of finding "
     "errors and verifying that it meets its requirements. Testing begins at the level of "
     "individual functions and proceeds to the integrated system. Both the machine-learning "
     "pipeline and the web application were tested.")
label("Testing Objectives")
numbered(["Testing is a process of executing a program with the intent of finding an error.",
          "A good test case has a high probability of finding an undiscovered error.",
          "A successful test is one that uncovers an undiscovered error."])
h3("8.1.1 Unit Testing")
para("Unit testing verifies individual units of code in isolation. Image loading, rejection "
     "of corrupt files, class-label lookup, split overlap checks, budget generation, "
     "augmentation output, model inference shape and Grad-CAM output were each tested "
     "separately (test cases TC-01 to TC-08).")
h3("8.1.2 Functional Testing")
para("Functional testing checks that each feature behaves as specified. The web "
     "application's registration, login, upload validation, prediction, report and history "
     "functions were exercised with valid and invalid inputs (test cases TC-09 to TC-16).")
h3("8.1.3 Integration Testing")
para("Integration testing combines modules and tests them as a group. The complete flow – "
     "registration, login, upload, model inference with Grad-CAM, database insert, result "
     "page, report and history – was executed end-to-end through a real browser using an "
     "automated Playwright script, which also produced the screenshots in Appendix 2.")
h3("8.1.4 Acceptance Testing")
para("Acceptance testing determines whether the system satisfies the user requirements. The "
     "application was checked against the objectives in Section 1.5: correct predictions on "
     "unseen test images, a visible explanation for every prediction, clear error messages "
     "and private per-user history.")
figure(os.path.join(FIG, "design", "fig_8_1_testing_flow.png"), "8.1", "Flow of testing", 5.8)
h2("8.2 TEST CASES")
tc_rows = [(r["test_id"], r["test_case"], r["detail"], r["status"]) for r in TCS]
tc_rows += [
    ("TC-09", "Open a page without logging in", "Redirected to the login page", "Pass"),
    ("TC-10", "Login with a wrong password", "“Invalid email or password” shown", "Pass"),
    ("TC-11", "Register an existing email", "“Account already exists” shown", "Pass"),
    ("TC-12", "Upload Tomato Late blight leaf", "Correct class, Grad-CAM, report, history",
     "Pass"),
    ("TC-13", "Upload healthy Apple leaf", "Leaf reported as healthy", "Pass"),
    ("TC-14", "Upload a corrupt .jpg file", "“Not a readable image” shown", "Pass"),
    ("TC-15", "Upload a .txt file", "“Unsupported file type” shown", "Pass"),
    ("TC-16", "Open another user's result URL", "HTTP 404 – access denied", "Pass"),
]
table(["ID", "Test case", "Observed result", "Status"], tc_rows, "8.1",
      "Test case summary", widths=[0.8, 1.9, 2.75, 0.8])

h2("8.3 RESULTS AND DISCUSSION")
h3("8.3.1 Training Behaviour")
last = LOG[-1]
para("Figure 8.2 shows the training and validation curves. Training loss fell from %.3f to "
     "%.3f and validation accuracy rose from %s to %s over %d epochs. The validation loss "
     "remained below or close to the training loss throughout, indicating that the "
     "augmentation and weight decay prevented overfitting. The best checkpoint (epoch %d) "
     "had a validation macro F1-score of %s."
     % (float(LOG[0]["train_loss"]), float(last["train_loss"]), pct(float(LOG[0]["val_acc"])),
        pct(float(last["val_acc"])), len(LOG), MET["best_epoch"], pct(MET["val_macro_f1"])))
figure(os.path.join(FIG, "results", "fig_8_2_training_curves.png"), "8.2",
       "Training and validation curves", 6.2)
h3("8.3.2 Classification Performance")
table(["Metric", "Value"], [
    ("Test images", "{:,}".format(EV["test_images"])), ("Accuracy", pct(EV["accuracy"])),
    ("Macro precision", pct(EV["macro_precision"])), ("Macro recall", pct(EV["macro_recall"])),
    ("Macro F1-score", pct(EV["macro_f1"])),
    ("Parameters", "{:,}".format(EV["parameters"])),
    ("Checkpoint size", "%.2f MB" % MET["checkpoint_mb"]),
    ("CPU inference time", "%.1f ms / image" % EV["latency_ms_cpu"])],
    "8.2", "Test-set performance of the proposed model", widths=[2.6, 2.4])
low = sorted(EV["per_class"].items(), key=lambda kv: kv[1]["f1"])[:4]
para("The model correctly classified %s of the %s held-out test images. Because macro "
     "F1-score (%s) is close to accuracy, performance is balanced across classes rather than "
     "driven by the large classes. Figure 8.3 shows the F1-score of every class: %d of the "
     "38 classes exceed 95%%. The weakest classes are %s."
     % (pct(EV["accuracy"]), "{:,}".format(EV["test_images"]), pct(EV["macro_f1"]),
        sum(1 for v in EV["per_class"].values() if v["f1"] >= 0.95),
        ", ".join("%s (%s)" % (nice(k), pct(v["f1"], 1)) for k, v in low)))
figure(os.path.join(FIG, "results", "fig_8_3_per_class_f1.png"), "8.3",
       "Per-class F1-score on the test set", 5.2)
cm, cl = EV["confusion_matrix"], EV["classes"]
pairs = sorted(((cm[i][j], cl[i], cl[j]) for i in range(38) for j in range(38) if i != j),
               reverse=True)[:3]
para("The confusion matrix in Figure 8.4 is strongly diagonal. The most frequent errors are "
     "between visually similar diseases of the same crop: %s. These diseases produce brown "
     "necrotic lesions that are difficult to separate even for human observers, and the "
     "errors suggest where additional training images would help most."
     % "; ".join("%s predicted as %s (%d images)" % (nice(a), nice(b), n) for n, a, b in pairs))
figure(os.path.join(FIG, "results", "fig_8_4_confusion_matrix.png"), "8.4",
       "Confusion matrix (row-normalised)", 6.0)
h3("8.3.3 Explanation Quality and Stability")
para("Figure 8.5 shows Grad-CAM explanations for test images of six classes. For diseased "
     "leaves, the highest activations lie on the lesions, rust pustules and blighted tissue; "
     "for the healthy leaf the activation spreads over the leaf blade. Table 8.3 reports the "
     "measured stability of these explanations.")
figure(os.path.join(FIG, "results", "fig_8_5_gradcam_samples.png"), "8.5",
       "Grad-CAM explanations for test images", 6.2)
vn = {"horizontal_flip": "Horizontal flip", "brightness_+15%": "Brightness +15%",
      "rotation_10deg": "Rotation 10°"}
table(["View", "Prediction agreement", "Mean Pearson r", "Mean top-20% IoU"],
      [(vn[k], pct(v["prediction_agreement"], 1), "%.3f" % v["mean_pearson"],
        "%.3f" % v["mean_top20_iou"]) for k, v in STAB["views"].items()],
      "8.3", "Explanation stability (%d test images)" % STAB["images"],
      widths=[1.6, 1.6, 1.4, 1.6])
fl, br, ro = (STAB["views"][k] for k in ("horizontal_flip", "brightness_+15%", "rotation_10deg"))
para("The explanations are highly stable under brightness change (r = %.3f) and horizontal "
     "flip (r = %.3f), with prediction agreement of %s and %s respectively. Rotation by 10° "
     "is the hardest view (agreement %s, r = %.3f) because rotation also introduces black "
     "corners and moves the leaf boundary, which the model never saw during training. This "
     "identifies rotation augmentation as a useful future improvement."
     % (br["mean_pearson"], fl["mean_pearson"], pct(br["prediction_agreement"], 1),
        pct(fl["prediction_agreement"], 1), pct(ro["prediction_agreement"], 1),
        ro["mean_pearson"]))
h3("8.3.4 Comparison with Published Work")
para("Table 8.4 places the result beside published PlantVillage studies. The published "
     "values were reported by their authors under their own data splits, so the comparison "
     "is indicative only. The proposed model uses far fewer parameters and only 40% of the "
     "training data, and is evaluated on a leaf-group-aware split that prevents leakage of "
     "near-identical images.")
table(["Study", "Model", "Training data", "Reported accuracy"], [
    ("Mohanty et al. (2016)", "GoogLeNet", "80% of images", "99.35%"),
    ("Too et al. (2019)", "DenseNet-121", "Full training set", "99.75%"),
    ("Pal et al. (2025)", "Mob-Res (3.51 M params)", "Full training set", "99.47%"),
    ("Proposed system", "MobileNetV3-Small (%.2f M)" % (EV["parameters"] / 1e6),
     "40%% budget (%s images)" % "{:,}".format(MET["train_images"]), pct(EV["accuracy"]))],
    "8.4", "Comparison with published PlantVillage results", widths=[1.6, 1.8, 1.6, 1.2])

# ============================== CHAPTER 9
chapter(9, "CONCLUSION AND FUTURE ENHANCEMENT")
h2("9.1 CONCLUSION")
para("This project developed a lightweight, explainable and web-deployed system for plant "
     "disease detection from leaf images. The PlantVillage dataset was audited and split by "
     "leaf groups to prevent leakage, and a controlled 40%% training budget was used to "
     "reflect limited labelled data. A MobileNetV3-Small network with %.2f million parameters, "
     "trained with label-preserving augmentation and class-weighted loss on a CPU, achieved "
     "%s accuracy and %s macro F1-score on %s unseen test images, with an inference time of "
     "about %.0f ms per image."
     % (EV["parameters"] / 1e6, pct(EV["accuracy"]), pct(EV["macro_f1"]),
        "{:,}".format(EV["test_images"]), EV["latency_ms_cpu"]))
para("Grad-CAM explanations highlight the diseased regions and were shown to be stable under "
     "flipping and brightness changes. The Flask application makes the model usable by "
     "non-experts through secure accounts, validated uploads, visual explanations, printable "
     "reports and stored history. The system provides fast preliminary screening that can "
     "help farmers seek expert advice earlier; it does not replace confirmation by a plant "
     "pathologist.")
h2("9.2 FUTURE ENHANCEMENT")
bullets([
    "Collect and test on field photographs with complex backgrounds to measure real-world "
    "generalisation, and add background-robust augmentation.",
    "Add rotation and perspective augmentation to improve stability under rotated views.",
    "Complete the full data-budget study (B20–B100) with repeated seeds and report mean and "
    "standard deviation.",
    "Add an out-of-distribution detector to reject images that are not one of the supported "
    "leaves.",
    "Export the model to ONNX / TensorFlow Lite and build an offline Android application.",
    "Provide multilingual (Tamil and English) results and link predictions to verified "
    "advisory information from agricultural departments.",
])

# ============================== APPENDIX 1
p = para("APPENDIX 1", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, after=0,
         keep=True, before=24)
h1("SOURCE CODE")
code_block("app.py", "A1.1 APP.PY (Flask web application)")
code_block("src/predict.py", "A1.2 PREDICT.PY (model bundle loader)")
code_block("src/gradcam.py", "A1.3 GRADCAM.PY (explanation module)")
code_block("src/train.py", "A1.4 TRAIN.PY (training pipeline)")
code_block("templates/result.html", "A1.5 RESULT.HTML (result page template)")

# ============================== APPENDIX 2
p = para("APPENDIX 2", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, after=0,
         keep=True, before=24)
h1("SCREENSHOTS")
for i, (f, cap) in enumerate([
        ("01_login.png", "Login page"), ("02_register.png", "Registration page"),
        ("08_login_error.png", "Login with invalid credentials"),
        ("03_upload.png", "Leaf image upload page"),
        ("04_result_disease.png", "Prediction result – Tomato Late blight with Grad-CAM"),
        ("05_result_healthy.png", "Prediction result – healthy Apple leaf"),
        ("06_report.png", "Printable prediction report"),
        ("07_history.png", "Prediction history")], 1):
    figure(os.path.join(SHOT, f), "A2.%d" % i, cap, 6.0)

# ============================== REFERENCES
h1("REFERENCES")
REFS = [
    "Hughes, D. P. and Salathé, M. (2015), ‘An open access repository of images on plant "
    "health to enable the development of mobile disease diagnostics’, arXiv:1511.08060.",
    "Mohanty, S. P., Hughes, D. P. and Salathé, M. (2016), ‘Using deep learning for "
    "image-based plant disease detection’, Frontiers in Plant Science, Vol. 7, Article 1419.",
    "Sladojevic, S., Arsenovic, M., Anderla, A., Culibrk, D. and Stefanovic, D. (2016), "
    "‘Deep neural networks based recognition of plant diseases by leaf image classification’, "
    "Computational Intelligence and Neuroscience, Vol. 2016, Article 3289801.",
    "Brahimi, M., Boukhalfa, K. and Moussaoui, A. (2017), ‘Deep learning for tomato "
    "diseases: classification and symptoms visualization’, Applied Artificial Intelligence, "
    "Vol. 31, No. 4, pp. 299–315.",
    "Ferentinos, K. P. (2018), ‘Deep learning models for plant disease detection and "
    "diagnosis’, Computers and Electronics in Agriculture, Vol. 145, pp. 311–318.",
    "Barbedo, J. G. A. (2018), ‘Impact of dataset size and variety on the effectiveness of "
    "deep learning and transfer learning for plant disease classification’, Computers and "
    "Electronics in Agriculture, Vol. 153, pp. 46–53.",
    "Too, E. C., Yujian, L., Njuki, S. and Yingchun, L. (2019), ‘A comparative study of "
    "fine-tuning deep learning models for plant disease identification’, Computers and "
    "Electronics in Agriculture, Vol. 161, pp. 272–279.",
    "Howard, A., Sandler, M., Chu, G., Chen, L.-C., Chen, B., Tan, M., Wang, W., Zhu, Y., "
    "Pang, R., Vasudevan, V., Le, Q. V. and Adam, H. (2019), ‘Searching for MobileNetV3’, "
    "Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV), "
    "pp. 1314–1324.",
    "Selvaraju, R. R., Cogswell, M., Das, A., Vedantam, R., Parikh, D. and Batra, D. (2017), "
    "‘Grad-CAM: visual explanations from deep networks via gradient-based localization’, "
    "Proceedings of the IEEE International Conference on Computer Vision (ICCV), pp. 618–626.",
    "Pal, C., Karmakar, S., Mukherjee, I. and Chakrabarti, P. P. (2025), ‘A lightweight and "
    "explainable CNN model for empowering plant disease diagnosis’, Scientific Reports, "
    "Vol. 15, Article 30720, doi:10.1038/s41598-025-94083-1.",
    "Sandler, M., Howard, A., Zhu, M., Zhmoginov, A. and Chen, L.-C. (2018), ‘MobileNetV2: "
    "inverted residuals and linear bottlenecks’, Proceedings of the IEEE Conference on "
    "Computer Vision and Pattern Recognition (CVPR), pp. 4510–4520.",
    "He, K., Zhang, X., Ren, S. and Sun, J. (2016), ‘Deep residual learning for image "
    "recognition’, Proceedings of the IEEE Conference on Computer Vision and Pattern "
    "Recognition (CVPR), pp. 770–778.",
    "Paszke, A. et al. (2019), ‘PyTorch: an imperative style, high-performance deep learning "
    "library’, Advances in Neural Information Processing Systems 32, pp. 8024–8035.",
    "Pallets Projects (2025), ‘Flask documentation’, https://flask.palletsprojects.com/.",
]
for i, r in enumerate(REFS, 1):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.left_indent = Inches(0.5)
    p.paragraph_format.first_line_indent = Inches(-0.5)
    p.add_run("[%d]\t%s" % (i, r))


# ------------------------------------------- list of figures / tables
def fill_list(anchor_para, items, prefix):
    host = anchor_para
    for num, cap, bm in items:
        p = OxmlElement("w:p")
        host._p.addnext(p)
        from docx.text.paragraph import Paragraph
        para_obj = Paragraph(p, host._parent)
        para_obj.paragraph_format.tab_stops.add_tab_stop(Inches(5.7), alignment=2, leader=1)
        para_obj.paragraph_format.space_after = Pt(2)
        para_obj.paragraph_format.left_indent = Inches(1.2)
        para_obj.paragraph_format.first_line_indent = Inches(-1.2)
        para_obj.add_run("%s %s\t%s\t" % (prefix, num, cap))
        field(para_obj, "PAGEREF %s \\h" % bm)
        host = para_obj


fill_list(LOF_PARA, FIGS, "Fig.No")
fill_list(LOT_PARA, TABS, "Table")

doc.save(OUT)
print("saved", OUT, "| figures:", len(FIGS), "tables:", len(TABS))
