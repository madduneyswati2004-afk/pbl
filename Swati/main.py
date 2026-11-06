
import csv
import os
from datetime import date

from event import Event
from student import Student
from registration import (
    Registration,
    RegistrationError,
    DuplicateRegistrationError,
    EventFullError
)
from feedback import FeedbackAnalyzer


DATA_DIR = "data"

FILES = {
    "events": os.path.join(DATA_DIR, "events.csv"),
    "students": os.path.join(DATA_DIR, "students.csv"),
    "registrations": os.path.join(DATA_DIR, "registrations.csv"),
    "feedback": os.path.join(DATA_DIR, "feedback.csv")
}

HEADERS = {
    "events": [
        "event_id", "name", "date", "venue", "max_participants"
    ],
    "students": [
        "student_id", "name", "department", "email"
    ],
    "registrations": [
        "registration_id", "student_id", "event_id", "date"
    ],
    "feedback": [
        "event_id", "student_id", "rating", "comment"
    ]
}


def initialize_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs("graphs", exist_ok=True)

    for key, filename in FILES.items():
        if not os.path.exists(filename):
            with open(filename, "w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=HEADERS[key])
                writer.writeheader()


def load_records(key):
    with open(FILES[key], "r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def save_records(key, records):
    with open(FILES[key], "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=HEADERS[key])
        writer.writeheader()
        writer.writerows(records)


def load_data():
    events = {}
    students = {}
    registrations = {}

    for row in load_records("events"):
        event = Event(
            row["event_id"],
            row["name"],
            row["date"],
            row["venue"],
            int(row["max_participants"])
        )
        if event.event_id in events:
            raise ValueError("Duplicate event ID in events.csv.")
        if event.max_participants < 1:
            raise ValueError("Event capacity must be positive.")
        events[event.event_id] = event

    for row in load_records("students"):
        student = Student(
            row["student_id"],
            row["name"],
            row["department"],
            row["email"]
        )
        if student.student_id in students:
            raise ValueError("Duplicate student ID in students.csv.")
        students[student.student_id] = student

    for row in load_records("registrations"):
        reg = Registration(
            row["registration_id"],
            row["student_id"],
            row["event_id"],
            row["date"]
        )
        if reg.registration_id in registrations:
            raise ValueError("Duplicate registration ID in registrations.csv.")
        if reg.student_id not in students or reg.event_id not in events:
            raise ValueError("Registration refers to a missing student or event.")
        if any(
            old.student_id == reg.student_id and old.event_id == reg.event_id
            for old in registrations.values()
        ):
            raise ValueError("Duplicate student/event registration in CSV.")
        registrations[reg.registration_id] = reg

    for event_id, event in events.items():
        count = sum(
            1 for reg in registrations.values()
            if reg.event_id == event_id
        )
        if count > event.max_participants:
            raise ValueError(f"Event {event_id} exceeds its capacity.")

    return events, students, registrations


def add_event(events):
    event_id = input("Event ID: ").strip().upper()

    if not event_id:
        raise ValueError("Event ID cannot be empty.")
    if event_id in events:
        raise ValueError("Event ID already exists.")

    name = input("Event name: ").strip()
    event_date = Event.validate_date(input("Date (YYYY-MM-DD): ").strip())
    venue = input("Venue: ").strip()
    capacity = int(input("Maximum participants: "))

    if not name or not venue:
        raise ValueError("Event name and venue cannot be empty.")
    if capacity < 1:
        raise ValueError("Capacity must be at least 1.")

    from datetime import datetime as dt
    if dt.strptime(event_date, "%Y-%m-%d").date() < date.today():
        raise ValueError("Cannot create an event in the past.")

    events[event_id] = Event(
        event_id, name, event_date, venue, capacity
    )
    save_records("events", [e.to_dict() for e in events.values()])
    print("Event created successfully!")


def view_events(events, registrations):
    if not events:
        print("No events available.")
        return

    for event in events.values():
        count = sum(
            1 for reg in registrations.values()
            if reg.event_id == event.event_id
        )
        event.display(count)


def update_event(events, registrations):
    event_id = input("Enter event ID to update: ").strip().upper()

    if event_id not in events:
        raise ValueError("Invalid event ID.")

    event = events[event_id]
    count = sum(
        1 for reg in registrations.values()
        if reg.event_id == event_id
    )

    name = input(f"Event name [{event.name}]: ").strip() or event.name
    raw_date = input(f"Date [{event.date}]: ").strip()
    venue = input(f"Venue [{event.venue}]: ").strip() or event.venue
    raw_capacity = input(
        f"Maximum participants [{event.max_participants}]: "
    ).strip()

    event_date = (
        Event.validate_date(raw_date) if raw_date else event.date
    )
    capacity = int(raw_capacity) if raw_capacity else event.max_participants

    if capacity < 1 or capacity < count:
        raise ValueError(
            "Capacity must be positive and cannot be less than registrations."
        )

    event.name = name
    event.date = event_date
    event.venue = venue
    event.max_participants = capacity

    save_records("events", [e.to_dict() for e in events.values()])
    print("Event updated successfully!")


def delete_event(events, registrations):
    event_id = input("Enter event ID to delete: ").strip().upper()

    if event_id not in events:
        raise ValueError("Invalid event ID.")

    if any(reg.event_id == event_id for reg in registrations.values()):
        raise ValueError(
            "Cancel all registrations before deleting this event."
        )

    del events[event_id]
    save_records("events", [e.to_dict() for e in events.values()])
    print("Event deleted successfully!")


def add_student(students):
    student_id = input("Student ID: ").strip().upper()

    if not student_id:
        raise ValueError("Student ID cannot be empty.")
    if student_id in students:
        raise ValueError("Student ID already exists.")

    name = input("Student name: ").strip()
    department = input("Department: ").strip()
    email = input("Email: ").strip()

    if not name or not department or not email or "@" not in email:
        raise ValueError("Enter valid student details and email.")

    students[student_id] = Student(
        student_id, name, department, email
    )
    save_records("students", [s.to_dict() for s in students.values()])
    print("Student added successfully!")


def view_students(students):
    if not students:
        print("No students available.")
        return

    for student in students.values():
        student.display()


def register_student(events, students, registrations):
    student_id = input("Student ID: ").strip().upper()
    event_id = input("Event ID: ").strip().upper()

    Registration.register(
        student_id, event_id, students, events, registrations
    )

    existing_numbers = []
    for reg_id in registrations:
        if reg_id.startswith("R") and reg_id[1:].isdigit():
            existing_numbers.append(int(reg_id[1:]))

    new_number = max(existing_numbers, default=0) + 1
    registration_id = f"R{new_number:04d}"

    while registration_id in registrations:
        new_number += 1
        registration_id = f"R{new_number:04d}"

    reg = Registration(
        registration_id, student_id, event_id, str(date.today())
    )
    registrations[registration_id] = reg

    save_records(
        "registrations",
        [r.to_dict() for r in registrations.values()]
    )
    print("Registration successful!")


def search_registrations(events, students, registrations):
    print("1. Search by event ID")
    print("2. Search by student ID")
    choice = input("Choose: ").strip()

    if choice == "1":
        event_id = input("Event ID: ").strip().upper()
        if event_id not in events:
            raise ValueError("Invalid event ID.")

        results = Registration.search_by_event(
            event_id, registrations, students
        )
        if not results:
            print("No registered students for this event.")
        else:
            for student in results:
                student.display()

    elif choice == "2":
        student_id = input("Student ID: ").strip().upper()
        if student_id not in students:
            raise ValueError("Invalid student ID.")

        found = [
            reg for reg in registrations.values()
            if reg.student_id == student_id
        ]
        for reg in found:
            print(f"{reg.event_id} - {events[reg.event_id].name}")

        if not found:
            print("This student has no registrations.")

    else:
        print("Invalid choice.")


def cancel_registration(registrations):
    student_id = input("Student ID: ").strip().upper()
    event_id = input("Event ID: ").strip().upper()

    if Registration.cancel(student_id, event_id, registrations):
        save_records(
            "registrations",
            [r.to_dict() for r in registrations.values()]
        )
        print("Registration cancelled successfully!")
    else:
        print("Registration not found.")


def main():
    initialize_files()

    try:
        events, students, registrations = load_data()
    except (ValueError, KeyError, csv.Error) as error:
        print(f"Unable to load data: {error}")
        print("Correct the relevant CSV file before restarting.")
        return

    analyzer = FeedbackAnalyzer(
        FILES["feedback"], events, registrations
    )

    while True:
        print("\n========== CAMPUS EVENT MANAGEMENT ==========")
        print("1. Create Event")
        print("2. View Events")
        print("3. Update Event")
        print("4. Delete Event")
        print("5. Add Student")
        print("6. View Students")
        print("7. Register Student")
        print("8. Search Registrations")
        print("9. Cancel Registration")
        print("10. Collect Feedback")
        print("11. Analyze Feedback and Generate Graphs")
        print("0. Exit")

        choice = input("Enter your choice: ").strip()

        try:
            if choice == "1":
                add_event(events)

            elif choice == "2":
                view_events(events, registrations)

            elif choice == "3":
                update_event(events, registrations)

            elif choice == "4":
                delete_event(events, registrations)

            elif choice == "5":
                add_student(students)

            elif choice == "6":
                view_students(students)

            elif choice == "7":
                register_student(events, students, registrations)

            elif choice == "8":
                search_registrations(events, students, registrations)

            elif choice == "9":
                cancel_registration(registrations)

            elif choice == "10":
                event_id = input("Event ID: ").strip().upper()
                student_id = input("Student ID: ").strip().upper()
                analyzer.collect_feedback(event_id, student_id)

            elif choice == "11":
                analyzer.analyze()

            elif choice == "0":
                print("Thank you for using Campus Event Management!")
                break

            else:
                print("Invalid choice. Please try again.")

        except (
            RegistrationError,
            ValueError,
            KeyError,
            OSError,
            csv.Error
        ) as error:
            print(f"Error: {error}")

        except Exception as error:
            print(f"Unexpected error: {error}")


if __name__ == "__main__":
    main()
