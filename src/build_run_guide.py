# -*- coding: utf-8 -*-
"""Build the step-by-step guide for running the web app on another laptop.

A temporary DOCX is written to the system temp folder, converted to PDF with
MS Word, and then deleted.
Usage:  python src/build_run_guide.py   ->  How_To_Run_The_App.pdf
"""
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
PDF = os.path.join(ROOT, "How_To_Run_The_App.pdf")
TMP = os.path.join(tempfile.gettempdir(), "run_guide_tmp.docx")
SHOTS = os.path.join(ROOT, "artifacts", "screenshots")
TITLE = ("A Data-Budget-Aware and Explanation-Stable Lightweight Deep Learning "
         "Framework for Plant Disease Detection")
GREEN = RGBColor(0x1B, 0x5E, 0x20)
FONT = "Times New Roman"

doc = Document()
s = doc.sections[0]
s.page_height, s.page_width = Inches(11.69), Inches(8.27)
s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Inches(1.0)
st = doc.styles["Normal"]
st.font.name = FONT
st.font.size = Pt(13)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st.paragraph_format.space_after = Pt(4)
st.paragraph_format.line_spacing = 1.15

# footer page number
fp = s.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
for kind, text in (("begin", None), (None, " PAGE "), ("end", None)):
    r = fp.add_run()
    if kind:
        el = OxmlElement("w:fldChar")
        el.set(qn("w:fldCharType"), kind)
    else:
        el = OxmlElement("w:instrText")
        el.set(qn("xml:space"), "preserve")
        el.text = text
    r._r.append(el)


def runs(p, text, size=None, color=None):
    """**bold** and `code` spans."""
    import re
    for part in re.split(r"(\*\*.+?\*\*|`.+?`)", text):
        if not part:
            continue
        if part.startswith("**"):
            r = p.add_run(part[2:-2])
            r.bold = True
        elif part.startswith("`"):
            r = p.add_run(part[1:-1])
            r.font.name = "Consolas"
            r._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), "Consolas")
            r.font.color.rgb = RGBColor(0xB7, 0x1C, 0x1C)
        else:
            r = p.add_run(part)
        if size:
            r.font.size = Pt(size)
        if color is not None:
            r.font.color.rgb = color
    return p


def para(text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, **kw):
    p = doc.add_paragraph()
    p.alignment = align
    return runs(p, text, **kw)


def heading(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(15)
    r.font.color.rgb = GREEN
    return p


def steps(items):
    for i, it in enumerate(items, 1):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Inches(0.4)
        p.paragraph_format.first_line_indent = Inches(-0.3)
        p.paragraph_format.space_after = Pt(3)
        runs(p, "%d.  %s" % (i, it))


def bullets(items):
    for it in items:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Inches(0.4)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        p.paragraph_format.space_after = Pt(2)
        runs(p, "•  " + it)


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def command(lines):
    """Grey box with commands to type."""
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = t.rows[0].cells[0]
    shade(c, "F1F3F4")
    c.paragraphs[0].text = ""
    for i, ln in enumerate(lines):
        p = c.paragraphs[0] if i == 0 else c.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        r = p.add_run(ln)
        r.font.name = "Consolas"
        r._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), "Consolas")
        r.font.size = Pt(11.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def table(header, rows, widths):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold = True
        shade(c, "D9E7D6")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            runs(cells[i].paragraphs[0], v, size=12)
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr()
        trPr.append(OxmlElement("w:cantSplit"))
        for c, w in zip(row.cells, widths):
            c.width = Inches(w)
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def shots(pairs):
    """Screenshots two per row with captions."""
    t = doc.add_table(rows=2, cols=len(pairs))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (fn, cap) in enumerate(pairs):
        p = t.rows[0].cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(os.path.join(SHOTS, fn), width=Inches(2.95))
        q = t.rows[1].cells[i].paragraphs[0]
        q.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = q.add_run(cap)
        r.italic = True
        r.font.size = Pt(11)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


# ======================================================================
p = para("HOW TO RUN THE APPLICATION", align=WD_ALIGN_PARAGRAPH.CENTER, size=18, color=GREEN)
p.runs[0].bold = True
para(TITLE, align=WD_ALIGN_PARAGRAPH.CENTER, size=13).runs[0].italic = True
para("Step-by-step guide for running the Plant Disease Detection web application on any "
     "Windows laptop.", align=WD_ALIGN_PARAGRAPH.CENTER, size=12)

heading("Quick start – one command does everything")
para("Copy `PlantDiseaseApp.zip` into the **Downloads** folder. Open **PowerShell** (press the "
     "Windows key, type `powershell`, press Enter), paste this one line and press **Enter**:")
command(["cd ~\\Downloads; if (!(Test-Path PlantDiseaseApp)) { Expand-Archive PlantDiseaseApp.zip . }; "
         ".\\PlantDiseaseApp\\run_app.bat"])
para("This single command:")
bullets([
    "extracts the zip (only the first time, so your accounts and history are never overwritten);",
    "finds Python 3.10–3.12, and **installs Python 3.12 automatically** with winget if it is "
    "missing;",
    "creates a virtual environment and installs PyTorch, Torchvision, Flask, Pillow and "
    "Matplotlib (first time only, 5–10 minutes, needs internet);",
    "starts the app and opens **http://127.0.0.1:5000** in the browser.",
])
para("Next time, run the **same command** again – it starts in a few seconds without internet. "
     "The sections below explain each step in detail.")

heading("1. What you need")
table(["Item", "Requirement"], [
    ("Computer", "Windows 10 or Windows 11 laptop (no GPU needed)"),
    ("Memory / disk", "4 GB RAM or more, about 1.5 GB free disk space"),
    ("Python", "Python **3.10, 3.11 or 3.12** (3.12 recommended)"),
    ("Internet", "Needed **only for the first run**, to download the packages (~250 MB)"),
    ("Browser", "Google Chrome, Microsoft Edge or Firefox"),
    ("Project file", "`PlantDiseaseApp.zip` (about 6 MB)"),
], widths=[1.6, 4.65])

heading("2. Install Python (one time only)")
para("`run_app.bat` installs Python automatically when it is missing. Install it by hand only "
     "if the automatic installation fails:")
steps([
    "Open **https://www.python.org/downloads/** and download **Python 3.12** for Windows.",
    "Run the installer. On the first screen **tick “Add python.exe to PATH”**, then click "
    "**Install Now**.",
    "To check, open **Command Prompt** (press Windows key, type `cmd`, press Enter) and type "
    "the command below. It should print a version such as Python 3.12.x.",
])
command(["python --version"])

heading("3. Copy and extract the project")
steps([
    "Copy `PlantDiseaseApp.zip` to the laptop (pen drive, Google Drive, e-mail, etc.).",
    "Right-click the zip file → **Extract All…** → **Extract**.",
    "Open the extracted **PlantDiseaseApp** folder. It contains:",
])
table(["File / folder", "Purpose"], [
    ("`run_app.bat`", "One-click setup and start"),
    ("`app.py`", "Flask web application"),
    ("`src`", "Grad-CAM and prediction code"),
    ("`model_bundle`", "Trained MobileNetV3-Small model, class list, settings"),
    ("`templates`, `static`", "Web pages, style sheet, uploaded images"),
    ("`instance`", "SQLite database with user accounts and history"),
    ("`requirements.txt`", "List of Python packages"),
], widths=[2.0, 4.25])

heading("4. Run the application (easy method)")
steps([
    "Double-click **run_app.bat**. A black Command Prompt window opens.",
    "If Windows shows “Windows protected your PC”, click **More info → Run anyway**.",
    "**First run only:** the window shows the steps **[1/3]** to **[3/3]**. It installs Python "
    "if needed, creates a virtual environment in `%USERPROFILE%\\.plantapp_venv` and installs "
    "PyTorch, Torchvision, Flask, Pillow and Matplotlib. This takes about **5–10 minutes**. Keep "
    "the internet on and do not close the window.",
    "When you see **“Running on http://127.0.0.1:5000”**, the browser opens the app "
    "automatically. If the page does not load, wait a few seconds and press **F5**.",
    "**Next runs:** double-click **run_app.bat** again. It starts in a few seconds, "
    "without internet.",
])

heading("5. Run the application (manual method)")
para("Use this if the batch file does not work. Open Command Prompt in the "
     "**PlantDiseaseApp** folder (type `cmd` in the folder’s address bar and press Enter) and "
     "run:")
command(["python -m venv %USERPROFILE%\\.plantapp_venv",
         "%USERPROFILE%\\.plantapp_venv\\Scripts\\activate",
         "pip install -r requirements.txt",
         "python app.py"])
para("Then open **http://127.0.0.1:5000** in the browser. Next time, only the second and the "
     "last command are needed. The virtual environment is kept in a short path because some "
     "PyTorch file names are very long.")

heading("6. Using the application")
steps([
    "**Register** – on the login page click **Create an account**, enter name, e-mail and a "
    "password (at least 6 characters). Accounts created on the original laptop are already "
    "included, so you can also log in with them directly.",
    "**Login** – enter the e-mail and password and click **Login**.",
    "**Upload** – choose a leaf photo (JPG, PNG, BMP or WEBP) and click **Detect disease**.",
    "**Result** – the page shows the crop, the disease, the confidence, the top predictions "
    "and the Grad-CAM heat map. A warning appears when confidence is below 50%.",
    "**Report** – click **View report**, then **Print / Save PDF** to print or save it.",
    "**History** – click **History** at the top to see all previous predictions of the "
    "logged-in user.",
    "**Logout** – click Logout at the top right.",
])
shots([("01_login.png", "Login page"), ("03_upload.png", "Upload a leaf image")])
shots([("04_result_disease.png", "Prediction with Grad-CAM"), ("07_history.png", "History page")])

heading("7. Stopping the application")
para("Press **Ctrl + C** in the black Command Prompt window, or simply close that window. "
     "The browser page stops working after the server is stopped.")

heading("8. Troubleshooting")
table(["Problem", "Solution"], [
    ("“Python could not be installed automatically”",
     "Install 64-bit Python 3.12 by hand (Section 2), tick **Add python.exe to PATH**, and "
     "run the command again."),
    ("Package installation fails",
     "Check the internet connection and run the command again. The script removes the "
     "half-installed environment by itself."),
    ("Upgrade or reinstall all packages",
     "Delete the folder `%USERPROFILE%\\.plantapp_venv` and run the command again."),
    ("“No matching distribution found for torch”",
     "The Python version is too new or 32-bit. Install **64-bit Python 3.12**."),
    ("Browser shows “This site can’t be reached”",
     "The server is still loading – wait a few seconds and press F5. Make sure the black window "
     "is still open."),
    ("“Address already in use” / port 5000 busy",
     "Another copy of the app is running. Close the other black window, or use another port: "
     "in PowerShell run `$env:PORT=5001; .\\PlantDiseaseApp\\run_app.bat` and open "
     "http://127.0.0.1:5001."),
    ("“Invalid email or password”",
     "Check the e-mail and password, or click **Register** to create a new account."),
    ("“Unsupported file type” or “too large”",
     "Use a JPG, PNG, BMP or WEBP image smaller than 8 MB."),
], widths=[2.4, 3.85])

heading("9. Running the tests (optional)")
para("The automated tests are not part of the zip. In the full project folder run:")
command(["pip install pytest", "python -m pytest tests -q"])
para("All 8 tests should pass.")

# ======================================================================
doc.save(TMP)
w = win32com.client.DispatchEx("Word.Application")
w.Visible = False
w.DisplayAlerts = 0
try:
    d = w.Documents.Open(TMP, False, True)
    d.ExportAsFixedFormat(PDF, 17)
    print("pages", d.ComputeStatistics(2))
    d.Close(False)
finally:
    w.Quit()
os.remove(TMP)
print("->", PDF)
