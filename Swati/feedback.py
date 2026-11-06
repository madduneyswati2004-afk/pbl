
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


# ── Shared professional style ──
BAR_COLOR = "#7C6FF7"
BG_COLOR = "#F0F0F0"

def _apply_style():
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
        df = pd.read_csv(self.feedback_file, dtype=str)

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

        self._generate_graphs(df)

        print("\nGraphs saved in the 'graphs' folder.")

    def _generate_graphs(self, df):
        """Generate all three professional-quality graphs."""
        os.makedirs("graphs", exist_ok=True)
        _apply_style()

        # ── Graph 1: Average Rating by Event (Bar Chart) ──
        averages = df.groupby("event_id")["rating"].mean()
        labels = [
            self.events[eid].name.title() if eid in self.events else eid
            for eid in averages.index
        ]
        n = len(labels)
        bar_w = max(0.35, 0.6 / max(1, n))

        fig1, ax1 = plt.subplots(figsize=(max(7, n * 2), 5))
        x = np.arange(n)
        ax1.bar(x, averages.values, width=bar_w,
                color=BAR_COLOR, edgecolor="none", zorder=3)
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, fontsize=12, fontweight="bold")
        ax1.set_ylim(0, 5.5)
        ax1.set_yticks([0, 1, 2, 3, 4, 5])
        ax1.set_ylabel("Average Rating", fontsize=13, fontweight="bold")
        ax1.set_xlabel("Event", fontsize=13, fontweight="bold")
        ax1.set_title("Average Feedback Rating by Event",
                      fontsize=15, fontweight="bold", pad=12)
        ax1.yaxis.grid(True, linestyle="--", alpha=0.5, color="#cccccc",
                       zorder=0)
        ax1.set_axisbelow(True)
        fig1.tight_layout()
        fig1.savefig("graphs/average_ratings.png", dpi=150,
                     facecolor=BG_COLOR)
        plt.close(fig1)

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
        ax2.yaxis.grid(True, linestyle="--", alpha=0.5, color="#cccccc",
                       zorder=0)
        ax2.set_axisbelow(True)
        fig2.tight_layout()
        fig2.savefig("graphs/rating_histogram.png", dpi=150,
                     facecolor=BG_COLOR)
        plt.close(fig2)

        # ── Graph 3: Event-wise Participation ──
        participation = {
            eid: sum(
                1 for reg in self.registrations.values()
                if reg.event_id == eid
            )
            for eid in self.events
        }
        p_labels = [self.events[eid].name.title() for eid in participation]
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
        ax3.yaxis.grid(True, linestyle="--", alpha=0.5, color="#cccccc",
                       zorder=0)
        ax3.set_axisbelow(True)
        fig3.tight_layout()
        fig3.savefig("graphs/event_participation.png", dpi=150,
                     facecolor=BG_COLOR)
        plt.close(fig3)

        # Reset defaults
        plt.rcdefaults()
