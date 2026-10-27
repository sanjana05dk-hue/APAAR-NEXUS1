from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import json
import os
from difflib import SequenceMatcher
import re

app = Flask(__name__)
# NEXUS Investigation Case Storage
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CASE_FILE = os.path.join(BASE_DIR, "database", "cases.json")


def load_cases():
    """Load saved investigation cases."""
    try:
        with open(CASE_FILE, "r", encoding="utf-8") as file:
            cases = json.load(file)
            return cases if isinstance(cases, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_cases(cases):
    """Save investigation cases to the JSON file."""
    os.makedirs(os.path.dirname(CASE_FILE), exist_ok=True)

    with open(CASE_FILE, "w", encoding="utf-8") as file:
        json.dump(cases, file, indent=4, ensure_ascii=False)


def create_case(alert):
    """Create a review case from a potential identity match."""
    cases = load_cases()

    case_id = f"NEXUS-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    new_case = {
        "case_id": case_id,
        "student_1": alert.get("student_1", ""),
        "student_1_id": alert.get("student_1_id", ""),
        "student_2": alert.get("student_2", ""),
        "student_2_id": alert.get("student_2_id", ""),
        "name_similarity": alert.get("name_similarity", 0),
        "reasons": alert.get("reasons", []),
        "status": "Open",
        "decision": "Pending Review",
        "notes": "",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "history": [
            {
                "action": "Case created",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        ]
    }

    cases.append(new_case)
    save_cases(cases)

    return new_case
def normalize_text(value):
    """Standardize text before comparing records."""
    value = str(value or "").lower().strip()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return " ".join(value.split())


def similarity(first, second):
    """Calculate name similarity as a percentage."""
    first = normalize_text(first)
    second = normalize_text(second)

    if not first or not second:
        return 0

    return round(
        SequenceMatcher(None, first, second).ratio() * 100,
        2
    )



def analyze_identity_records(students):
    """Identify potentially similar records for human verification."""
    alerts = []

    for i in range(len(students)):
        for j in range(i + 1, len(students)):
            first = students[i]
            second = students[j]

            score = similarity(
                first.get("name", ""),
                second.get("name", "")
            )

            institution1 = normalize_text(
                first.get("institution", "")
            )
            institution2 = normalize_text(
                second.get("institution", "")
            )

            same_institution = (
                bool(institution1)
                and institution1 == institution2
            )

            # Explainable reasons for flagging a pair
            reasons = []

            if score >= 70:
                reasons.append(
                    f"Name similarity: {score}%"
                )

            if same_institution:
                reasons.append("Same institution")

            # Ignore pairs without sufficient initial similarity
            if score < 70:
                continue

            # Assign review priority
            if score >= 85 and same_institution:
                priority = "High"
                priority_reason = (
                    "High name similarity and same institution"
                )
            elif score >= 85 or same_institution:
                priority = "Medium"
                priority_reason = (
                    "Additional human verification recommended"
                )
            else:
                priority = "Low"
                priority_reason = (
                    "Name similarity warrants a preliminary review"
                )

            alerts.append({
                "student_1": first.get("name", "Unknown"),
                "student_1_id": first.get("id", "Unknown"),
                "student_2": second.get("name", "Unknown"),
                "student_2_id": second.get("id", "Unknown"),
                "name_similarity": score,
                "same_institution": same_institution,
                "priority": priority,
                "priority_reason": priority_reason,
                "reasons": reasons,
                "message": (
                    "Potential match only. "
                    "Human verification is required."
                )
            })

    return alerts



# APAAR NEXUS — Demonstration prototype.
# These are fictional records, not official APAAR data.

STUDENTS = [
    {
        "id": "STU1001",
        "name": "Aarav Sharma",
        "institution": "National Engineering College",
        "course": "Computer Science",
        "year": "2025",
        "status": "Verified"
    },
    {
        "id": "STU1002",
        "name": "Ananya Rao",
        "institution": "City Institute of Technology",
        "course": "Data Science",
        "year": "2025",
        "status": "Pending Review"
    },
    {
        "id": "STU1003",
        "name": "Rahul Kumar",
        "institution": "National Engineering College",
        "course": "Information Science",
        "year": "2024",
        "status": "Verified"
    },
    {
        "id": "TEST1004",
        "name": "Aarav Sharma",
        "institution": "National Engineering College",
        "course": "Computer Science",
        "year": "2025",
        "status": "Synthetic Test Record"
    }
]


@app.route("/")
def dashboard():
    return render_template(
        "index.html",
        total=len(STUDENTS),
        verified=sum(
            s["status"] == "Verified" for s in STUDENTS
        ),
        pending=sum(
            s["status"] == "Pending Review" for s in STUDENTS
        ),
        students=STUDENTS
    )



@app.route("/detective", methods=["GET", "POST"])
def detective():
    results = []
    query = ""

    if request.method == "POST":
        query = request.form.get("query", "").strip().lower()

        if query:
            results = [
                student for student in STUDENTS
                if query in student["name"].lower()
                or query in student["id"].lower()
                or query in student["institution"].lower()
                or query in student["course"].lower()
            ]

    identity_alerts = analyze_identity_records(STUDENTS)

    return render_template(
        "workspace.html",
        page="detective",
        title="Identity Detective",
        subtitle="Search records and examine potential inconsistencies.",
        students=STUDENTS,
        results=results,
        query=query,
        identity_alerts=identity_alerts
    )

@app.route("/journey")
def journey():
    journey_records = []

    for student in STUDENTS:
        journey_records.append({
            "id": student["id"],
            "name": student["name"],
            "institution": student["institution"],
            "course": student["course"],
            "year": student["year"],
            "status": student["status"]
        })

    return render_template(
        "workspace.html",
        page="journey",
        title="Academic Journey",
        subtitle="Explore student academic records and track their educational progress.",
        students=journey_records
    )



@app.route("/trustgraph")
def trustgraph():
    verified_count = sum(
        student["status"] == "Verified"
        for student in STUDENTS
    )

    pending_count = sum(
        student["status"] == "Pending Review"
        for student in STUDENTS
    )

    return render_template(
        "workspace.html",
        page="trustgraph",
        title="TrustGraph",
        subtitle="Explore relationships and verification status across demonstration student records.",
        students=STUDENTS,
        verified=verified_count,
        pending=pending_count
    )
@app.route("/investigations")
def investigations():
    flagged = [
        student for student in STUDENTS
        if student["status"] == "Pending Review"
    ]

    cases = load_cases()

    total_cases = len(cases)
    open_cases = sum(1 for case in cases if case.get("status") == "Open")
    under_review_cases = sum(1 for case in cases if case.get("status") == "Under Review")
    closed_cases = sum(1 for case in cases if case.get("status") == "Closed")

    verification_required = sum(
        1 for case in cases
        if case.get("decision") == "Potential Match - Further Verification"
    )

    return render_template("workspace.html",
    page="investigations",
    title="Investigation Centre",
    subtitle="Review flagged records and manage investigation cases.",
    students=STUDENTS,
    flagged=flagged,
    cases=cases,
    total_cases=total_cases,
    open_cases=open_cases,
    under_review_cases=under_review_cases,
    closed_cases=closed_cases,
    verification_required=verification_required
)

@app.route("/create_case", methods=["POST"])
def create_case_route():
    identity_alerts = analyze_identity_records(STUDENTS)
    alert_index = request.form.get("alert_index", "").strip()

    try:
        index = int(alert_index)
    except (ValueError, TypeError):
        return redirect(url_for("detective"))

    if index < 0 or index >= len(identity_alerts):
        return redirect(url_for("detective"))

    alert = identity_alerts[index]
    cases = load_cases()

    for case in cases:
        same_pair = (
            case.get("student_1_id") == alert.get("student_1_id")
            and case.get("student_2_id") == alert.get("student_2_id")
        )

        if same_pair and case.get("status") != "Closed":
            return redirect(url_for("investigations"))

    create_case(alert)
    return redirect(url_for("investigations"))

@app.route("/update_case", methods=["POST"])
def update_case():
    case_id = request.form.get("case_id", "").strip()
    new_status = request.form.get("status", "").strip()
    new_decision = request.form.get("decision", "").strip()
    new_notes = request.form.get("notes", "").strip()

    allowed_statuses = ["Open", "Under Review", "Closed"]

    allowed_decisions = [
        "Pending Review",
        "Potential Match - Further Verification",
        "No Match",
        "More Information Required"
    ]

    if new_status not in allowed_statuses:
        return redirect(url_for("investigations"))

    if new_decision not in allowed_decisions:
        return redirect(url_for("investigations"))

    cases = load_cases()

    for case in cases:
        if case.get("case_id") != case_id:
            continue

        # Do not modify a closed case.
        if case.get("status") == "Closed":
            break

        old_status = case.get("status", "Open")
        old_decision = case.get("decision", "Pending Review")
        old_notes = case.get("notes", "")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history = case.setdefault("history", [])

        if old_status != new_status:
            history.append({
                "action": f"Status changed: {old_status} → {new_status}",
                "timestamp": timestamp,
                "notes": new_notes
            })

        if old_decision != new_decision:
            history.append({
                "action": f"Decision changed: {old_decision} → {new_decision}",
                "timestamp": timestamp,
                "notes": new_notes
            })

        if old_notes != new_notes:
            history.append({
                "action": "Investigation notes updated",
                "timestamp": timestamp,
                "notes": new_notes,
                "previous_notes": old_notes
            })

     

        case["status"] = new_status
        case["decision"] = new_decision
        case["notes"] = new_notes

        save_cases(cases)
        break

    return redirect(url_for("investigations"))

   
if __name__ == "__main__":
    app.run(debug=True)