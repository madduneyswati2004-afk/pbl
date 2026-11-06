"""
Campus Event Management & Feedback Analyzer — Web Interface
Run with: py app.py
Open: http://127.0.0.1:5000
"""

import csv
import os
import io
import base64
from datetime import date, datetime

from flask import (
    Flask, render_template, request, redirect, url_for, flash
)
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from event import Event
from student import Student
from registration import (
    Registration,
    RegistrationError,
    DuplicateRegistrationError,
    EventFullError,
)

app = Flask(__name__)
app.secret_key = "campus-event-secret-key"

DATA_DIR = "data"
FILES = {
    "events": os.path.join(DATA_DIR, "events.csv"),
    "students": os.path.join(DATA_DIR, "students.csv"),
    "registrations": os.path.join(DATA_DIR, "registrations.csv"),
    "feedback": os.path.join(DATA_DIR, "feedback.csv"),
}
HEADERS = {
    "events": ["event_id", "name", "date", "venue", "max_participants"],
    "students": ["student_id", "name", "department", "email"],
    "registrations": ["registration_id", "student_id", "event_id", "date"],
    "feedback": ["event_id", "student_id", "rating", "comment"],
}


# ── helpers ──────────────────────────────────────────────────────────
def initialize_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs("graphs", exist_ok=True)
    for key, filename in FILES.items():
        if not os.path.exists(filename):
            with open(filename, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=HEADERS[key]).writeheader()


def load_records(key):
    with open(FILES[key], "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_records(key, records):
    with open(FILES[key], "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS[key])
        writer.writeheader()
        writer.writerows(records)


def load_data():
    events, students, registrations = {}, {}, {}

    for row in load_records("events"):
        e = Event(
            row["event_id"], row["name"], row["date"],
            row["venue"], int(row["max_participants"])
        )
        events[e.event_id] = e

    for row in load_records("students"):
        s = Student(
            row["student_id"], row["name"],
            row["department"], row["email"]
        )
        students[s.student_id] = s

    for row in load_records("registrations"):
        r = Registration(
            row["registration_id"], row["student_id"],
            row["event_id"], row["date"]
        )
        registrations[r.registration_id] = r

    return events, students, registrations


def reg_count(event_id, registrations):
    return sum(1 for r in registrations.values() if r.event_id == event_id)


def is_event_over(event):
    """Check if an event's date has passed."""
    try:
        event_date = datetime.strptime(str(event.date), "%Y-%m-%d").date()
        return event_date < date.today()
    except (ValueError, TypeError):
        return False


def event_status(event):
    """Return status string for an event."""
    return "Completed" if is_event_over(event) else "Upcoming"


def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return b64


# ── routes ───────────────────────────────────────────────────────────
@app.route("/")
def index():
    events, students, registrations = load_data()
    return render_template(
        "index.html",
        events=events,
        students=students,
        registrations=registrations,
        reg_count=reg_count,
        is_event_over=is_event_over,
        event_status=event_status,
        today=str(date.today()),
    )


# ---------- Events ----------
@app.route("/events")
def events_page():
    events, _, registrations = load_data()
    return render_template(
        "events.html", events=events,
        registrations=registrations, reg_count=reg_count,
        is_event_over=is_event_over, event_status=event_status,
        today=str(date.today()),
    )


@app.route("/events/add", methods=["GET", "POST"])
def add_event():
    if request.method == "POST":
        try:
            eid = request.form["event_id"].strip().upper()
            name = request.form["name"].strip()
            event_date = request.form["date"].strip()
            venue = request.form["venue"].strip()
            cap = int(request.form["max_participants"])

            if not eid or not name or not venue:
                raise ValueError("All fields are required.")
            if cap < 1:
                raise ValueError("Capacity must be at least 1.")
            Event.validate_date(event_date)

            # Block past dates
            parsed_date = datetime.strptime(event_date, "%Y-%m-%d").date()
            if parsed_date < date.today():
                raise ValueError(
                    "Cannot create an event in the past. "
                    "Please select today or a future date."
                )

            events, _, _ = load_data()
            if eid in events:
                raise ValueError("Event ID already exists.")

            events[eid] = Event(eid, name, event_date, venue, cap)
            save_records("events", [e.to_dict() for e in events.values()])
            flash("Event created successfully!", "success")
            return redirect(url_for("events_page"))
        except (ValueError, KeyError) as e:
            flash(str(e), "danger")

    return render_template("add_event.html", today=str(date.today()))


@app.route("/events/delete/<event_id>", methods=["POST"])
def delete_event(event_id):
    try:
        events, _, registrations = load_data()
        if event_id not in events:
            raise ValueError("Invalid event ID.")
        if any(r.event_id == event_id for r in registrations.values()):
            raise ValueError(
                "Cancel all registrations before deleting this event."
            )
        del events[event_id]
        save_records("events", [e.to_dict() for e in events.values()])
        flash("Event deleted.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("events_page"))


# ---------- Students ----------
@app.route("/students")
def students_page():
    _, students, _ = load_data()
    return render_template("students.html", students=students)


@app.route("/students/add", methods=["GET", "POST"])
def add_student():
    if request.method == "POST":
        try:
            sid = request.form["student_id"].strip().upper()
            name = request.form["name"].strip()
            dept = request.form["department"].strip()
            email = request.form["email"].strip()

            if not sid or not name or not dept or not email or "@" not in email:
                raise ValueError("All fields are required with a valid email.")

            _, students, _ = load_data()
            if sid in students:
                raise ValueError("Student ID already exists.")

            students[sid] = Student(sid, name, dept, email)
            save_records("students", [s.to_dict() for s in students.values()])
            flash("Student added!", "success")
            return redirect(url_for("students_page"))
        except ValueError as e:
            flash(str(e), "danger")

    return render_template("add_student.html")


# ---------- Registration ----------
@app.route("/register", methods=["GET", "POST"])
def register_page():
    events, students, registrations = load_data()

    if request.method == "POST":
        try:
            sid = request.form["student_id"].strip().upper()
            eid = request.form["event_id"].strip().upper()

            # Block registration for past events
            if eid in events and is_event_over(events[eid]):
                raise ValueError(
                    "This event has already ended. Registration is closed."
                )

            Registration.register(sid, eid, students, events, registrations)

            nums = [
                int(rid[1:]) for rid in registrations
                if rid.startswith("R") and rid[1:].isdigit()
            ]
            new_num = max(nums, default=0) + 1
            reg_id = f"R{new_num:04d}"
            while reg_id in registrations:
                new_num += 1
                reg_id = f"R{new_num:04d}"

            registrations[reg_id] = Registration(
                reg_id, sid, eid, str(date.today())
            )
            save_records(
                "registrations",
                [r.to_dict() for r in registrations.values()],
            )
            flash("Registration successful!", "success")
            return redirect(url_for("register_page"))
        except (RegistrationError, ValueError) as e:
            flash(str(e), "danger")

    reg_list = []
    for r in registrations.values():
        ev_name = events[r.event_id].name if r.event_id in events else r.event_id
        st_name = students[r.student_id].name if r.student_id in students else r.student_id
        reg_list.append({
            "registration_id": r.registration_id,
            "student_name": st_name,
            "student_id": r.student_id,
            "event_name": ev_name,
            "event_id": r.event_id,
            "date": r.date,
        })

    return render_template(
        "register.html",
        events=events, students=students,
        registrations=registrations, reg_list=reg_list,
        reg_count=reg_count, is_event_over=is_event_over,
    )


@app.route("/register/search")
def search_registrations():
    events, students, registrations = load_data()
    search_type = request.args.get("type", "")
    search_id = request.args.get("id", "").strip().upper()
    results = []
    searched = False

    if search_type and search_id:
        searched = True
        if search_type == "event":
            if search_id not in events:
                flash("Invalid event ID.", "danger")
            else:
                for r in registrations.values():
                    if r.event_id == search_id:
                        s = students.get(r.student_id)
                        results.append({
                            "reg_id": r.registration_id,
                            "student_id": r.student_id,
                            "student_name": s.name if s else r.student_id,
                            "department": s.department if s else "—",
                            "event_name": events[search_id].name,
                            "date": r.date,
                        })
        elif search_type == "student":
            if search_id not in students:
                flash("Invalid student ID.", "danger")
            else:
                for r in registrations.values():
                    if r.student_id == search_id:
                        e = events.get(r.event_id)
                        results.append({
                            "reg_id": r.registration_id,
                            "event_id": r.event_id,
                            "event_name": e.name if e else r.event_id,
                            "venue": e.venue if e else "—",
                            "student_name": students[search_id].name,
                            "date": r.date,
                        })

    return render_template(
        "search.html",
        events=events, students=students,
        search_type=search_type, search_id=search_id,
        results=results, searched=searched,
    )


@app.route("/register/cancel", methods=["POST"])
def cancel_registration():
    try:
        sid = request.form["student_id"].strip().upper()
        eid = request.form["event_id"].strip().upper()
        _, _, registrations = load_data()
        if Registration.cancel(sid, eid, registrations):
            save_records(
                "registrations",
                [r.to_dict() for r in registrations.values()],
            )
            flash("Registration cancelled.", "success")
        else:
            flash("Registration not found.", "warning")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for("register_page"))


# ---------- Feedback ----------
@app.route("/feedback", methods=["GET", "POST"])
def feedback_page():
    events, students, registrations = load_data()

    if request.method == "POST":
        try:
            eid = request.form["event_id"].strip().upper()
            sid = request.form["student_id"].strip().upper()
            rating = int(request.form["rating"])
            comment = request.form.get("comment", "").strip()

            if eid not in events:
                raise ValueError("Invalid event ID.")
            if sid not in {
                r.student_id for r in registrations.values()
                if r.event_id == eid
            }:
                raise ValueError(
                    "Only registered students can submit feedback."
                )
            if rating < 1 or rating > 5:
                raise ValueError("Rating must be between 1 and 5.")

            existing = pd.read_csv(FILES["feedback"], dtype=str)
            dup = (existing["event_id"] == eid) & (existing["student_id"] == sid)
            if dup.any():
                raise ValueError("Feedback already submitted for this event.")

            new_row = pd.DataFrame([{
                "event_id": eid, "student_id": sid,
                "rating": rating, "comment": comment,
            }])
            new_row.to_csv(
                FILES["feedback"], mode="a", header=False, index=False
            )
            flash("Feedback submitted!", "success")
            return redirect(url_for("feedback_page"))
        except (ValueError, KeyError) as e:
            flash(str(e), "danger")

    fb_records = load_records("feedback")
    return render_template(
        "feedback.html",
        events=events, students=students,
        registrations=registrations, fb_records=fb_records,
    )


# ---------- Analysis / Graphs ----------
@app.route("/analysis")
def analysis_page():
    events, _, registrations = load_data()

    try:
        df = pd.read_csv(FILES["feedback"], dtype=str)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return render_template(
            "analysis.html", has_data=False,
            events=events, registrations=registrations,
        )

    df["rating"] = pd.to_numeric(df["rating"], errors="raise")

    # Stats
    avg_by_event = df.groupby("event_id")["rating"].mean().round(2)
    count_by_event = df.groupby("event_id")["rating"].count()

    stats = []
    for eid in avg_by_event.index:
        name = events[eid].name if eid in events else eid
        stats.append({
            "event_id": eid,
            "name": name,
            "avg_rating": avg_by_event[eid],
            "feedback_count": int(count_by_event[eid]),
            "participant_count": reg_count(eid, registrations),
        })

    highest_avg = avg_by_event.max()
    best_events = [
        events[eid].name if eid in events else eid
        for eid in avg_by_event[avg_by_event == highest_avg].index
    ]

    # ── Graph style matching reference ──
    BAR_COLOR = "#7C6FF7"
    BG_COLOR = "#F0F0F0"

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 12,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": True,
        "axes.spines.bottom": True,
        "figure.facecolor": BG_COLOR,
        "axes.facecolor": BG_COLOR,
        "axes.edgecolor": "#444444",
    })

    # ── Graph 1: Average rating by event (Bar chart) ──
    labels = [
        events[eid].name.title() if eid in events else eid
        for eid in avg_by_event.index
    ]
    n = len(labels)
    bar_w = max(0.35, 0.6 / max(1, n))

    fig1, ax1 = plt.subplots(figsize=(max(7, n * 2), 5))
    x1 = np.arange(n)
    ax1.bar(x1, avg_by_event.values, width=bar_w,
            color=BAR_COLOR, edgecolor="none", zorder=3)
    ax1.set_xticks(x1)
    ax1.set_xticklabels(labels, fontsize=12, fontweight="bold")
    ax1.set_ylim(0, 5.5)
    ax1.set_yticks([0, 1, 2, 3, 4, 5])
    ax1.set_ylabel("Average Rating", fontsize=13, fontweight="bold")
    ax1.set_xlabel("Event", fontsize=13, fontweight="bold")
    ax1.set_title("Average Feedback Rating by Event",
                  fontsize=15, fontweight="bold", pad=12)
    ax1.yaxis.grid(True, linestyle="--", alpha=0.5, color="#cccccc", zorder=0)
    ax1.set_axisbelow(True)
    fig1.tight_layout()
    fig1.savefig("graphs/average_ratings.png", dpi=150, facecolor=BG_COLOR)
    chart1 = fig_to_base64(fig1)

    # ── Graph 2: Distribution of Feedback Ratings ──
    rating_counts = df["rating"].value_counts().sort_index()
    all_ratings = [1, 2, 3, 4, 5]
    counts_list = [int(rating_counts.get(r, 0)) for r in all_ratings]
    star_labels = ["1 Star", "2 Star", "3 Star", "4 Star", "5 Star"]

    fig2, ax2 = plt.subplots(figsize=(7, 5))
    x2 = np.arange(5)
    ax2.bar(x2, counts_list, width=0.55,
            color=BAR_COLOR, edgecolor="none", zorder=3)
    ax2.set_xticks(x2)
    ax2.set_xticklabels(star_labels, fontsize=12, fontweight="bold")
    max_c = max(counts_list) if counts_list else 1
    ax2.set_ylim(0, max_c + max(1, int(max_c * 0.3)))
    ax2.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax2.set_ylabel("Number of Responses", fontsize=13, fontweight="bold")
    ax2.set_xlabel("Rating", fontsize=13, fontweight="bold")
    ax2.set_title("Distribution of Feedback Ratings",
                  fontsize=15, fontweight="bold", pad=12)
    ax2.yaxis.grid(True, linestyle="--", alpha=0.5, color="#cccccc", zorder=0)
    ax2.set_axisbelow(True)
    fig2.tight_layout()
    fig2.savefig("graphs/rating_histogram.png", dpi=150, facecolor=BG_COLOR)
    chart2 = fig_to_base64(fig2)

    # ── Graph 3: Event-wise participation ──
    participation = {
        eid: reg_count(eid, registrations) for eid in events
    }
    p_labels = [events[eid].name.title() for eid in participation]
    p_values = list(participation.values())
    n3 = len(p_labels)
    bar_w3 = max(0.35, 0.6 / max(1, n3))

    fig3, ax3 = plt.subplots(figsize=(max(7, n3 * 2), 5))
    x3 = np.arange(n3)
    ax3.bar(x3, p_values, width=bar_w3,
            color=BAR_COLOR, edgecolor="none", zorder=3)
    ax3.set_xticks(x3)
    ax3.set_xticklabels(p_labels, fontsize=12, fontweight="bold")
    max_p = max(p_values) if p_values else 1
    ax3.set_ylim(0, max_p + max(1, int(max_p * 0.3)))
    ax3.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax3.set_ylabel("Registered Students", fontsize=13, fontweight="bold")
    ax3.set_xlabel("Event", fontsize=13, fontweight="bold")
    ax3.set_title("Event-wise Participation",
                  fontsize=15, fontweight="bold", pad=12)
    ax3.yaxis.grid(True, linestyle="--", alpha=0.5, color="#cccccc", zorder=0)
    ax3.set_axisbelow(True)
    fig3.tight_layout()
    fig3.savefig("graphs/event_participation.png", dpi=150, facecolor=BG_COLOR)
    chart3 = fig_to_base64(fig3)

    # Reset defaults
    plt.rcdefaults()

    return render_template(
        "analysis.html",
        has_data=True,
        stats=stats,
        best_events=best_events,
        highest_avg=highest_avg,
        chart1=chart1,
        chart2=chart2,
        chart3=chart3,
        events=events,
        registrations=registrations,
    )


# ── entry point ──────────────────────────────────────────────────────
if __name__ == "__main__":
    initialize_files()
    print("Starting Campus Event Management web app …")
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(debug=True, port=5000)

