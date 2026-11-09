# -*- coding: utf-8 -*-
"""Make the 3 front pages (title page, bonafide certificate, acknowledgement)
by editing a copy of the college sample report, so logos, fonts and layout stay
identical. The result (report_assets/front_pages.docx) is inserted at the start
of the project report by src/finalize_report.py.

Usage:  python src/build_front_pages.py
"""
import copy
import os

import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "report_assets", "front_pages_template.docx")
OUT = os.path.join(ROOT, "report_assets", "front_pages.docx")

TITLE = ("A DATA-BUDGET-AWARE AND EXPLANATION-STABLE LIGHTWEIGHT DEEP LEARNING "
         "FRAMEWORK FOR PLANT DISEASE DETECTION")
STUDENT, ROLL = "A. BOWSIYA", "911625405001"
HOD = "T. TAMILILAKKIYA M.E.,"
GUIDE = "Mrs. P. JONE JENIFER M.E.,"
MONTH = "NOVEMBER 2026"

d = docx.Document(SRC)
body = d.element.body
P = d.paragraphs

# ---- keep only the first three pages (paragraphs 0..59) -------------------
inner = None
for el in body:
    sp = el.find(".//" + qn("w:sectPr"))
    if el.tag == qn("w:p") and sp is not None:
        inner = copy.deepcopy(sp)          # first section's page setup
        break
cut = P[60]._p
kids = list(body)
start = kids.index(cut)
for el in kids[start:]:
    body.remove(el)
if inner is not None:
    body.append(inner)


def set_runs(p, parts, size=14):
    """Replace all runs of paragraph p by (text, bold[, size]) parts."""
    for r in p._p.findall(qn("w:r")):
        p._p.remove(r)
    for part in parts:
        text, bold = part[0], part[1]
        sz = part[2] if len(part) > 2 else size
        chunks = text.split("\n")
        r = p.add_run()
        for i, c in enumerate(chunks):
            if i:
                r.add_break()
            if c:
                r.add_text(c)
        r.bold = bold
        r.font.size = Pt(sz)
        r.font.name = "Times New Roman"


# ---- page 1: title page ----------------------------------------------------
set_runs(P[1], [(TITLE, True, 16), ("\n\nA PROJECT REPORT", True, 14)])
set_runs(P[3], [("%s   (%s)" % (STUDENT, ROLL), True, 16)])
P[3].paragraph_format.left_indent = Inches(0)
P[3].paragraph_format.first_line_indent = Inches(0)
for i in (4, 5, 6):
    P[i]._p.getparent().remove(P[i]._p)
set_runs(P[9], [("MASTER OF ENGINEERING", True, 16)])
set_runs(P[16], [(MONTH, True, 14)])

# ---- page 2: bonafide certificate -------------------------------------------
set_runs(P[23], [("Certified that this project report ", False),
                 ("“%s”" % TITLE.title().replace("And", "and").replace("For", "for"), True),
                 (" is the Bonafide work of ", False),
                 ("“%s (%s)”" % (STUDENT, ROLL), True),
                 (" who carried out the project work under my supervision.", False)])
set_runs(P[29], [(HOD, True), ("\t" + GUIDE, True)])
P[29].paragraph_format.tab_stops.add_tab_stop(Inches(3.45))

# Each front page starts on a new page explicitly, and a few blank lines are
# removed from the certificate so it stays on one page inside the report.
P[18].paragraph_format.page_break_before = True
for i in (21, 25, 42, 43):
    assert P[i].text.strip() == "", i
    P[i]._p.getparent().remove(P[i]._p)

# ---- page 3: acknowledgement (single student -> I / me) ---------------------
P[47].paragraph_format.page_break_before = True
IND = "              "
ACK = {
    50: [(IND + "I am much grateful to the management of Mother Terasa College of "
          "Engineering and Technology, Pudukkottai for providing me an opportunity to "
          "undergo this project work.", False)],
    51: [("\n" + IND + "I have immense pleasure and satisfaction in expressing my hearty "
          "thanks to our beloved managing founder ", False), ("Mr. R. CHINNATHAMBI,", True),
         (" who is the source of this great institution.", False)],
    52: [("\n" + IND + "I am very glad to express my hearty thanks to our beloved Chairman",
          False)],
    54: [("\n" + IND + "I would like to express my sincere thanks to our Principal", False)],
    55: [("Dr. M. RAVICHANDRAN,", True),
         (" Principal, MTCET, for the facilities and encouragement given towards the progress "
          "and completion of this project.", False)],
    56: [("\n" + IND + "I am grateful to ", False), (HOD, True),
         (" Head of the Department, Department of Computer Science and Engineering, for the "
          "effective leadership and supportive guidance given to this project.", False)],
    57: [("\n" + IND + "I wish to convey my heartfelt thanks to ", False), (GUIDE, True),
         (" Assistant Professor, Department of Computer Science and Engineering, my project "
          "guide, for not only showing the path but also encouraging me.", False)],
    58: [("\n" + IND + "I wish to extend my sincere thanks to all faculty members of the "
          "Computer Science and Engineering Department for their valuable suggestions and "
          "encouragement towards the successful completion of this project.", False)],
    59: [(IND + "Finally, I express my profound gratitude to the Almighty, who gave me the "
          "bravery, privilege, power and belief to complete this project.", False)],
}
for i, parts in ACK.items():
    set_runs(P[i], parts)

# ---- make spacing explicit so it survives insertion into the report ---------
# The template's defaults (Calibri 11 pt, 8 pt after, 1.08 line spacing) would
# otherwise be replaced by the report's Normal style when Word merges the files.
for p in d.paragraphs:
    pPr = p._p.get_or_add_pPr()
    sp = pPr.find(qn("w:spacing"))
    if sp is None:
        sp = OxmlElement("w:spacing")
        pPr.append(sp)
    if qn("w:after") not in sp.attrib:
        sp.set(qn("w:after"), "160")
    if qn("w:line") not in sp.attrib:
        sp.set(qn("w:line"), "259")
        sp.set(qn("w:lineRule"), "auto")
    if pPr.find(qn("w:ind")) is None:
        ind = OxmlElement("w:ind")
        ind.set(qn("w:firstLine"), "0")
        pPr.append(ind)
    for el in [pPr] + list(p._p.findall(qn("w:r"))):
        rPr = el.find(qn("w:rPr"))
        if rPr is None:
            rPr = OxmlElement("w:rPr")
            if el is pPr:
                pPr.append(rPr)
            else:
                el.insert(0, rPr)
        if rPr.find(qn("w:sz")) is None:
            sz = OxmlElement("w:sz")
            sz.set(qn("w:val"), "22")
            rPr.append(sz)
        if rPr.find(qn("w:rFonts")) is None:
            rf = OxmlElement("w:rFonts")
            rf.set(qn("w:ascii"), "Times New Roman")
            rf.set(qn("w:hAnsi"), "Times New Roman")
            rPr.insert(0, rf)

d.save(OUT)
print("->", OUT)
