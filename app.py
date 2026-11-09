# -*- coding: utf-8 -*-
"""Plant Disease Detection - Flask web application.

Modules served by this file:
  * User Authentication  - register / login / logout (hashed passwords, SQLite)
  * Image Upload         - validated leaf image upload
  * Prediction           - MobileNetV3-Small inference, top-5 classes
  * Explanation          - Grad-CAM heatmap of the predicted class
  * Report & History     - per-user prediction history and printable report

Run:
  python app.py            ->  http://127.0.0.1:5000
"""
import os
import sqlite3
import sys
import time
import uuid
from functools import wraps

import torch
from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from PIL import Image, UnidentifiedImageError
from torchvision import transforms
from werkzeug.security import check_password_hash, generate_password_hash

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))
from gradcam import GradCAM, overlay  # noqa: E402
from predict import ToTensorNoNumpy, load_bundle  # noqa: E402

INSTANCE = os.path.join(ROOT, "instance")
UPLOADS = os.path.join(ROOT, "static", "uploads")
DB_PATH = os.environ.get("PLANT_DB", os.path.join(INSTANCE, "plant_disease.db"))
ALLOWED = {"jpg", "jpeg", "png", "bmp", "webp"}
LOW_CONFIDENCE = 0.50
os.makedirs(INSTANCE, exist_ok=True)
os.makedirs(UPLOADS, exist_ok=True)


def _secret_key():
    path = os.path.join(INSTANCE, "secret_key")
    if not os.path.exists(path):
        with open(path, "wb") as fh:
            fh.write(os.urandom(32))
    with open(path, "rb") as fh:
        return fh.read()


app = Flask(__name__)
app.config.update(SECRET_KEY=_secret_key(),
                  MAX_CONTENT_LENGTH=8 * 1024 * 1024)

# ------------------------------------------------------------------ model
NET, CLASSES, CFG = load_bundle()
SIZE = int(CFG["input_size"])
PREPROCESS = transforms.Compose([
    transforms.Resize(int(SIZE * 1.15)),
    transforms.CenterCrop(SIZE),
])
TO_TENSOR = transforms.Compose([
    ToTensorNoNumpy(),
    transforms.Normalize(CFG["mean"], CFG["std"]),
])
CAM = GradCAM(NET)


def split_label(name):
    """'Tomato___Late_blight' -> ('Tomato', 'Late blight')."""
    crop, _, cond = name.partition("___")
    crop = crop.replace("_", " ").replace(",", "")
    cond = cond.replace("_", " ").strip()
    return crop, cond


def is_healthy(name):
    return name.endswith("___healthy")


# --------------------------------------------------------------- database
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL UNIQUE,
    password   TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS predictions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    image_file  TEXT NOT NULL,
    cam_file    TEXT NOT NULL,
    orig_name   TEXT NOT NULL,
    label       TEXT NOT NULL,
    confidence  REAL NOT NULL,
    top5        TEXT NOT NULL,
    latency_ms  REAL NOT NULL,
    created_at  TEXT NOT NULL
);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


with sqlite3.connect(DB_PATH) as _con:
    _con.executescript(SCHEMA)


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_globals():
    return {"user_name": session.get("user_name"), "cfg": CFG,
            "n_classes": len(CLASSES)}


# ------------------------------------------------------- authentication
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        pw = request.form.get("password", "")
        pw2 = request.form.get("confirm", "")
        if not name or "@" not in email:
            flash("Enter your name and a valid email address.", "danger")
        elif len(pw) < 6:
            flash("Password must be at least 6 characters.", "danger")
        elif pw != pw2:
            flash("Passwords do not match.", "danger")
        else:
            db = get_db()
            try:
                db.execute("INSERT INTO users (name, email, password, created_at)"
                           " VALUES (?, ?, ?, ?)",
                           (name, email, generate_password_hash(pw), now()))
                db.commit()
            except sqlite3.IntegrityError:
                flash("An account with this email already exists.", "danger")
            else:
                flash("Registration successful. Please log in.", "success")
                return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        pw = request.form.get("password", "")
        row = get_db().execute("SELECT * FROM users WHERE email = ?",
                               (email,)).fetchone()
        if row is None or not check_password_hash(row["password"], pw):
            flash("Invalid email or password.", "danger")
        else:
            session.clear()
            session["user_id"] = row["id"]
            session["user_name"] = row["name"]
            return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ------------------------------------------------- upload + prediction
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        file = request.files.get("leaf")
        if file is None or file.filename == "":
            flash("Choose a leaf image to upload.", "warning")
            return redirect(url_for("index"))
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in ALLOWED:
            flash("Unsupported file type. Use JPG, PNG, BMP or WEBP.", "danger")
            return redirect(url_for("index"))
        try:
            img = Image.open(file.stream)
            img.verify()
            file.stream.seek(0)
            img = Image.open(file.stream).convert("RGB")
        except (UnidentifiedImageError, OSError, SyntaxError):
            flash("The uploaded file is not a readable image.", "danger")
            return redirect(url_for("index"))
        if min(img.size) < 32:
            flash("Image is too small (minimum 32 x 32 pixels).", "danger")
            return redirect(url_for("index"))

        rid = uuid.uuid4().hex
        view = PREPROCESS(img)
        t0 = time.perf_counter()
        cam, probs = CAM(TO_TENSOR(view).unsqueeze(0))
        latency = (time.perf_counter() - t0) * 1000.0
        scores, idx = torch.topk(probs, 5)
        top5 = ";".join("%d:%.6f" % (i, s) for s, i in
                        zip(scores.tolist(), idx.tolist()))

        img_file, cam_file = rid + ".jpg", rid + "_cam.jpg"
        view.save(os.path.join(UPLOADS, img_file), quality=92)
        overlay(view, cam).save(os.path.join(UPLOADS, cam_file), quality=92)

        db = get_db()
        cur = db.execute(
            "INSERT INTO predictions (user_id, image_file, cam_file, orig_name,"
            " label, confidence, top5, latency_ms, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (session["user_id"], img_file, cam_file, file.filename[:120],
             CLASSES[int(idx[0])], float(scores[0]), top5, latency, now()))
        db.commit()
        return redirect(url_for("result", pid=cur.lastrowid))
    return render_template("index.html")


def load_prediction(pid):
    row = get_db().execute("SELECT * FROM predictions WHERE id = ? AND user_id = ?",
                           (pid, session["user_id"])).fetchone()
    if row is None:
        abort(404)
    top = []
    for item in row["top5"].split(";"):
        i, s = item.split(":")
        crop, cond = split_label(CLASSES[int(i)])
        top.append({"crop": crop, "cond": cond, "score": float(s)})
    crop, cond = split_label(row["label"])
    return {"row": row, "top": top, "crop": crop, "cond": cond,
            "healthy": is_healthy(row["label"]),
            "low": row["confidence"] < LOW_CONFIDENCE}


@app.route("/result/<int:pid>")
@login_required
def result(pid):
    return render_template("result.html", **load_prediction(pid))


@app.route("/report/<int:pid>")
@login_required
def report(pid):
    return render_template("report.html", **load_prediction(pid))


@app.route("/history")
@login_required
def history():
    rows = get_db().execute(
        "SELECT * FROM predictions WHERE user_id = ? ORDER BY id DESC",
        (session["user_id"],)).fetchall()
    items = []
    for r in rows:
        crop, cond = split_label(r["label"])
        items.append({"row": r, "crop": crop, "cond": cond,
                      "healthy": is_healthy(r["label"])})
    return render_template("history.html", items=items)


@app.errorhandler(413)
def too_large(_e):
    flash("File is larger than 8 MB.", "danger")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
