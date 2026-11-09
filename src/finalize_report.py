# -*- coding: utf-8 -*-
"""Insert the front pages, update TOC / PAGEREF fields with MS Word and export
the report to PDF.
Usage:  python src/finalize_report.py
"""
import os
import sys
import time

import win32com.client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCX = os.path.join(ROOT, "ME_Plant_Disease_Detection_Project_Report_Final.docx")
PDF = DOCX[:-5] + ".pdf"
FRONT = os.path.join(ROOT, "report_assets", "front_pages.docx")


def insert_front_pages(doc):
    """Put the title page, certificate and acknowledgement in an unnumbered
    first section; the Abstract section keeps its own roman numbering (i...)."""
    if not os.path.exists(FRONT) or doc.Bookmarks.Exists("front_pages"):
        return False
    doc.Range(0, 0).InsertBreak(2)                    # wdSectionBreakNextPage
    for i in (1, 2, 3):                               # primary, first page, even
        doc.Sections(2).Footers(i).LinkToPrevious = False
        doc.Sections(2).Headers(i).LinkToPrevious = False
    for i in (1, 2, 3):
        doc.Sections(1).Footers(i).Range.Text = ""
        doc.Sections(1).Headers(i).Range.Text = ""
    ps = doc.Sections(1).PageSetup
    ps.LeftMargin = ps.RightMargin = ps.TopMargin = ps.BottomMargin = 72  # 1 inch
    doc.Range(0, 0).InsertFile(FRONT)
    # drop the empty paragraph left before the section break
    last = doc.Sections(1).Range.Paragraphs.Last
    prev = last.Previous()
    if prev is not None and prev.Range.Text.strip() == "":
        prev.Range.Delete()
    doc.Bookmarks.Add("front_pages", doc.Range(0, 0))
    return True


def log(msg, t0=[time.time()]):
    print("[%5.1fs] %s" % (time.time() - t0[0], msg), flush=True)


word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
try:
    log("word started")
    doc = word.Documents.Open(DOCX, False, False, False)
    log("opened")
    if insert_front_pages(doc):
        log("front pages inserted")
    for sid in (-20, -21):  # wdStyleTOC1, wdStyleTOC2: compact single-spaced entries
        stl = doc.Styles(sid)
        stl.Font.Name = "Times New Roman"
        stl.Font.Size = 14
        stl.ParagraphFormat.LineSpacingRule = 0
        stl.ParagraphFormat.SpaceAfter = 5
    for _ in range(2):
        doc.TablesOfContents(1).Update()
        log("toc updated")
        doc.Fields.Update()
        log("fields updated")
    doc.Save()
    log("saved")
    doc.ExportAsFixedFormat(PDF, 17)
    log("pdf exported, pages=%d" % doc.ComputeStatistics(2))
    doc.Close(False)
finally:
    word.Quit()
    log("quit")
sys.exit(0)
