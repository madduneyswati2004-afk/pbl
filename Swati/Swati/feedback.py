
import os
import pandas as pd
import matplotlib.pyplot as plt


class FeedbackAnalyzer:
    def __init__(self, feedback_file, events, registrations):
        self.feedback_file = feedback_file
        self.events = events
        self.registrations = registrations

    def collect_feedback(self, event_id, student_id):
        if event_id not in self.events:
            raise ValueError("Invalid event ID.")

        if student_id not in {
            reg.student_id for reg in self.registrations.values()
            if reg.event_id == event_id
        }:
            raise ValueError(
                "Only registered students can submit feedback."
            )

        rating_text = input("Enter rating (1-5): ").strip()

        try:
            rating = int(rating_text)
        except ValueError:
            raise ValueError("Rating must be a whole number from 1 to 5.")

        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5.")

        existing = pd.read_csv(self.feedback_file, dtype=str)

        duplicate = (
            (existing["event_id"] == event_id) &
            (existing["student_id"] == student_id)
        )

        if duplicate.any():
            raise ValueError(
                "Feedback has already been submitted for this event."
            )

        comment = input("Enter comment (optional): ").strip()

        new_feedback = pd.DataFrame([{
            "event_id": event_id,
            "student_id": student_id,
            "rating": rating,
            "comment": comment
        }])

        new_feedback.to_csv(
            self.feedback_file,
            mode="a",
            header=False,
            index=False
        )

        print("Feedback submitted successfully!")

    def analyze(self):
        df = pd.read_csv(self.feedback_file)

        if df.empty:
            print("No feedback available.")
            return

        df["rating"] = pd.to_numeric(df["rating"], errors="raise")

        print("\nAVERAGE RATING BY EVENT")
        print(df.groupby("event_id")["rating"].mean().round(2))

        print("\nFEEDBACK RESPONSE COUNT")
        print(df.groupby("event_id")["rating"].count())

        print("\nREGISTERED PARTICIPANTS BY EVENT")
        for event_id, event in self.events.items():
            count = sum(
                1 for reg in self.registrations.values()
                if reg.event_id == event_id
            )
            print(f"{event.name}: {count}")

        print("\nHIGHEST-RATED EVENT")
        averages = df.groupby("event_id")["rating"].mean()
        highest = averages.max()

        for event_id in averages[averages == highest].index:
            name = self.events[event_id].name if event_id in self.events else event_id
            print(f"{name}: {highest:.2f}/5")

        os.makedirs("graphs", exist_ok=True)

        # Graph 1: Average rating by event
        averages = df.groupby("event_id")["rating"].mean()
        labels = [
            self.events[eid].name if eid in self.events else eid
            for eid in averages.index
        ]

        plt.figure(figsize=(8, 5))
        plt.bar(labels, averages.values, color="skyblue")
        plt.title("Average Feedback Rating by Event")
        plt.xlabel("Event")
        plt.ylabel("Average Rating")
        plt.ylim(0, 5)
        plt.xticks(rotation=20, ha="right")
        plt.tight_layout()
        plt.savefig("graphs/average_ratings.png")
        plt.close()

        # Graph 2: Distribution of feedback ratings
        plt.figure(figsize=(8, 5))
        plt.hist(
            df["rating"],
            bins=[0.5, 1.5, 2.5, 3.5, 4.5, 5.5],
            edgecolor="black",
            color="orange"
        )
        plt.xticks([1, 2, 3, 4, 5])
        plt.title("Feedback Rating Distribution")
        plt.xlabel("Rating")
        plt.ylabel("Number of Responses")
        plt.tight_layout()
        plt.savefig("graphs/rating_histogram.png")
        plt.close()

        # Graph 3: Participation by event
        counts = {
            event_id: sum(
                1 for reg in self.registrations.values()
                if reg.event_id == event_id
            )
            for event_id in self.events
        }

        names = [self.events[eid].name for eid in counts]
        values = list(counts.values())

        plt.figure(figsize=(8, 5))
        plt.bar(names, values, color="mediumseagreen")
        plt.title("Event-wise Participation")
        plt.xlabel("Event")
        plt.ylabel("Registered Students")
        plt.xticks(rotation=20, ha="right")
        plt.tight_layout()
        plt.savefig("graphs/event_participation.png")
        plt.close()

        print("\nGraphs saved in the 'graphs' folder.")
