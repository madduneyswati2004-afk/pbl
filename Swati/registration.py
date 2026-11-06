
class RegistrationError(Exception):
    pass


class DuplicateRegistrationError(RegistrationError):
    pass


class EventFullError(RegistrationError):
    pass


class Registration:
    def __init__(self, registration_id, student_id, event_id, date):
        self.registration_id = registration_id
        self.student_id = student_id
        self.event_id = event_id
        self.date = date

    def to_dict(self):
        return {
            "registration_id": self.registration_id,
            "student_id": self.student_id,
            "event_id": self.event_id,
            "date": self.date
        }

    @staticmethod
    def register(student_id, event_id, students, events, registrations):
        if student_id not in students:
            raise RegistrationError("Student ID does not exist.")

        if event_id not in events:
            raise RegistrationError("Event ID does not exist.")

        for reg in registrations.values():
            if (reg.student_id == student_id and
                    reg.event_id == event_id):
                raise DuplicateRegistrationError(
                    "Student is already registered for this event."
                )

        event = events[event_id]

        count = sum(
            1 for reg in registrations.values()
            if reg.event_id == event_id
        )

        if count >= event.max_participants:
            raise EventFullError("Event is full. Registration rejected.")

        return True

    @staticmethod
    def search_by_event(event_id, registrations, students):
        results = []

        for reg in registrations.values():
            if reg.event_id == event_id:
                results.append(students[reg.student_id])

        return results

    @staticmethod
    def cancel(student_id, event_id, registrations):
        for reg_id, reg in list(registrations.items()):
            if (reg.student_id == student_id and
                    reg.event_id == event_id):
                del registrations[reg_id]
                return True

        return False
