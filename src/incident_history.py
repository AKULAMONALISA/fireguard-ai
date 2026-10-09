
import csv
import os
from datetime import datetime

HISTORY_FILE = os.path.join(
    os.path.dirname(__file__), "incident_history.csv"
)

def save_incident(
    status,
    confidence,
    area=0,
    growth=0,
    trend="unknown",
    risk_level="LOW",
    risk_score=0,
    latitude=0.0,
    longitude=0.0,
    frames_processed=0,
):
    file_exists = os.path.isfile(HISTORY_FILE)

    with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp", "status", "confidence", "area",
                "growth", "trend", "risk_level", "risk_score",
                "latitude", "longitude", "frames_processed",
            ],
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "status": status,
            "confidence": confidence,
            "area": area,
            "growth": growth,
            "trend": trend,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "latitude": latitude,
            "longitude": longitude,
            "frames_processed": frames_processed,
        })

def load_incidents():
    if not os.path.isfile(HISTORY_FILE):
        return []

    with open(HISTORY_FILE, "r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))
