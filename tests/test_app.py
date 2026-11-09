# -*- coding: utf-8 -*-
"""Functional tests for the Flask web application.

Run:  python -m pytest tests/test_app.py -q      (or)  python tests/test_app.py
"""
import glob
import io
import os
import sys
import uuid

import atexit
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
# Use a throw-away database so tests never touch the real user data.
_TMP_DB = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["PLANT_DB"] = _TMP_DB
_UPLOADS = os.path.join(ROOT, "static", "uploads")
_BEFORE = set(os.listdir(_UPLOADS)) if os.path.isdir(_UPLOADS) else set()
import app as webapp  # noqa: E402


@atexit.register
def _cleanup_uploads():
    for f in set(os.listdir(_UPLOADS)) - _BEFORE:
        os.remove(os.path.join(_UPLOADS, f))

RAW = os.path.join(ROOT, "dataset", "PlantVillage", "raw", "color")


def sample(cls):
    return sorted(glob.glob(os.path.join(RAW, cls, "*")))[0]


def client_logged_in():
    c = webapp.app.test_client()
    email = "tester_%s@example.test" % uuid.uuid4().hex[:8]
    r = c.post("/register", data={"name": "Test User", "email": email,
                                  "password": "secret123", "confirm": "secret123"})
    assert r.status_code == 302 and "/login" in r.headers["Location"]
    r = c.post("/login", data={"email": email, "password": "secret123"})
    assert r.status_code == 302
    return c


def upload(c, path, name=None):
    with open(path, "rb") as fh:
        data = {"leaf": (io.BytesIO(fh.read()), name or os.path.basename(path))}
    return c.post("/", data=data, content_type="multipart/form-data")


def test_requires_login():
    r = webapp.app.test_client().get("/")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_wrong_password_rejected():
    c = webapp.app.test_client()
    r = c.post("/login", data={"email": "nobody@example.test", "password": "x"})
    assert b"Invalid email or password" in r.data


def test_duplicate_email_rejected():
    c = webapp.app.test_client()
    email = "dup_%s@example.test" % uuid.uuid4().hex[:8]
    form = {"name": "A", "email": email, "password": "secret123", "confirm": "secret123"}
    c.post("/register", data=form)
    r = c.post("/register", data=form)
    assert b"already exists" in r.data


def test_predict_late_blight():
    c = client_logged_in()
    r = upload(c, sample("Tomato___Late_blight"))
    assert r.status_code == 302 and "/result/" in r.headers["Location"]
    page = c.get(r.headers["Location"]).data.decode()
    assert "Tomato" in page and "Late blight" in page and "Grad-CAM" in page
    pid = r.headers["Location"].rsplit("/", 1)[-1]
    assert c.get("/report/" + pid).status_code == 200
    assert "Late blight" in c.get("/history").data.decode()


def test_predict_healthy():
    c = client_logged_in()
    r = upload(c, sample("Apple___healthy"))
    page = c.get(r.headers["Location"]).data.decode()
    assert "appears <strong>healthy</strong>" in page


def test_corrupt_file_rejected():
    c = client_logged_in()
    r = c.post("/", data={"leaf": (io.BytesIO(b"not an image" * 20), "bad.jpg")},
               content_type="multipart/form-data", follow_redirects=True)
    assert b"not a readable image" in r.data


def test_wrong_extension_rejected():
    c = client_logged_in()
    r = c.post("/", data={"leaf": (io.BytesIO(b"hello"), "notes.txt")},
               content_type="multipart/form-data", follow_redirects=True)
    assert b"Unsupported file type" in r.data


def test_other_user_cannot_open_result():
    a = client_logged_in()
    r = upload(a, sample("Potato___Early_blight"))
    loc = r.headers["Location"]
    b = client_logged_in()
    assert b.get(loc).status_code == 404


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
    print("%d tests passed" % len(tests))
