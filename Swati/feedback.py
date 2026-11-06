
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


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

        # ── Colour palette ──
        COLORS = [
            "#4F46E5", "#06B6D4", "#10B981", "#F59E0B",
            "#EF4444", "#8B5CF6", "#EC4899", "#14B8A6",
        ]
        STAR_COLORS = [
            "#EF4444", "#F97316", "#FBBF24", "#34D399", "#10B981"
        ]

        # Apply clean style
        plt.rcParams.update({
            "font.family": "sans-serif",
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        })

        # ── Graph 1: Average Rating by Event (Bar Chart) ──
        averages = df.groupby("event_id")["rating"].mean()
        labels = [
            self.events[eid].name.title() if eid in self.events else eid
            for eid in averages.index
        ]
        n = len(labels)
        bar_w = min(0.5, 0.5 / max(1, 4 - n))
        colors = COLORS[:n]

        fig1, ax1 = plt.subplots(figsize=(max(6, n * 2.2), 5))
        x = np.arange(n)
        bars1 = ax1.bar(x, averages.values, width=bar_w,
                        color=colors, edgecolor="white", linewidth=1.2,
                        zorder=3)
        for bar, val in zip(bars1, averages.values):
            ax1.text(bar.get_x() + bar.get_width() / 2,
                     bar.get_height() + 0.12,
                     f"{val:.2f}", ha="center", va="bottom",
                     fontsize=13, fontweight="bold", color="#1e293b")
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, fontsize=12, fontweight="600")
        ax1.set_ylim(0, 5.8)
        ax1.set_yticks([0, 1, 2, 3, 4, 5])
        ax1.set_ylabel("Average Rating", fontsize=12, fontweight="600")
        ax1.set_xlabel("Event", fontsize=12, fontweight="600")
        ax1.set_title("Average Feedback Rating by Event",
                      fontsize=15, fontweight="bold", pad=15)
        ax1.yaxis.grid(True, linestyle="--", alpha=0.4, zorder=0)
        ax1.set_axisbelow(True)
        fig1.tight_layout()
        fig1.savefig("graphs/average_ratings.png", dpi=150)
        plt.close(fig1)

        # ── Graph 2: Rating Distribution (Bar-style Histogram) ──
        rating_counts = df["rating"].value_counts().sort_index()
        all_ratings = [1, 2, 3, 4, 5]
        counts_list = [int(rating_counts.get(r, 0)) for r in all_ratings]

        fig2, ax2 = plt.subplots(figsize=(7, 5))
        x2 = np.arange(5)
        bars2 = ax2.bar(x2, counts_list, width=0.5,
                        color=STAR_COLORS, edgecolor="white",
                        linewidth=1.2, zorder=3)
        for bar, val in zip(bars2, counts_list):
            if val > 0:
                ax2.text(bar.get_x() + bar.get_width() / 2,
                         bar.get_height() + 0.08,
                         str(val), ha="center", va="bottom",
                         fontsize=13, fontweight="bold", color="#1e293b")
        ax2.set_xticks(x2)
        ax2.set_xticklabels(
            ["\u2605 1\nVery Poor", "\u2605 2\nPoor", "\u2605 3\nAverage",
             "\u2605 4\nGood", "\u2605 5\nExcellent"],
            fontsize=9, fontweight="600"
        )
        max_c = max(counts_list) if counts_list else 1
        ax2.set_ylim(0, max_c + max(1, int(max_c * 0.35)))
        ax2.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax2.set_ylabel("Number of Responses", fontsize=12, fontweight="600")
        ax2.set_xlabel("Rating", fontsize=12, fontweight="600")
        ax2.set_title("Feedback Rating Distribution",
                      fontsize=15, fontweight="bold", pad=15)
        ax2.yaxis.grid(True, linestyle="--", alpha=0.4, zorder=0)
        ax2.set_axisbelow(True)
        fig2.tight_layout()
        fig2.savefig("graphs/rating_histogram.png", dpi=150)
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
        bar_w3 = min(0.5, 0.5 / max(1, 4 - n3))
        colors3 = COLORS[:n3]

        fig3, ax3 = plt.subplots(figsize=(max(6, n3 * 2.2), 5))
        x3 = np.arange(n3)
        bars3 = ax3.bar(x3, p_values, width=bar_w3,
                        color=colors3, edgecolor="white",
                        linewidth=1.2, zorder=3)
        for bar, val in zip(bars3, p_values):
            ax3.text(bar.get_x() + bar.get_width() / 2,
                     bar.get_height() + 0.08,
                     str(val), ha="center", va="bottom",
                     fontsize=13, fontweight="bold", color="#1e293b")
        ax3.set_xticks(x3)
        ax3.set_xticklabels(p_labels, fontsize=12, fontweight="600")
        max_p = max(p_values) if p_values else 1
        ax3.set_ylim(0, max_p + max(1, int(max_p * 0.35)))
        ax3.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax3.set_ylabel("Registered Students", fontsize=12, fontweight="600")
        ax3.set_xlabel("Event", fontsize=12, fontweight="600")
        ax3.set_title("Event-wise Participation",
                      fontsize=15, fontweight="bold", pad=15)
        ax3.yaxis.grid(True, linestyle="--", alpha=0.4, zorder=0)
        ax3.set_axisbelow(True)
        fig3.tight_layout()
        fig3.savefig("graphs/event_participation.png", dpi=150)
        plt.close(fig3)

        # Reset defaults
        plt.rcdefaults()
