import cv2

from src.detector import FireDetector
from src.tracker import FireTracker
from src.verifier import FireVerifier
from src.risk_engine import RiskEngine
from src.video_processor import VideoProcessor


# ==============================
# FIREGUARD AI CONFIGURATION
# ==============================

MODEL_PATH = "models/best.pt"
VIDEO_PATH = "videos/fire.mp4"


# ==============================
# MAIN FUNCTION
# ==============================

def main():

    print("================================")
    print("        FIREGUARD AI")
    print("================================")
    print("Starting system...")

    # --------------------------
    # Initialize components
    # --------------------------

    detector = FireDetector(MODEL_PATH)

    tracker = FireTracker()

    verifier = FireVerifier(
        window_size=10,
        threshold=0.35
    )

    risk_engine = RiskEngine()

    video = VideoProcessor(VIDEO_PATH)

    print("System started successfully.")
    print("Press Q to stop.")
    print("--------------------------------")


    # ==============================
    # PROCESS VIDEO
    # ==============================

    while True:

        # Read frame
        frame = video.read_frame()

        if frame is None:
            print("Video ended.")
            break


        # ==============================
        # AI DETECTION
        # ==============================

        detections = detector.detect(frame)


        # ==============================
        # FIND FIRE CONFIDENCE
        # ==============================

        fire_confidence = 0.0

        for detection in detections:

            if detection["class_id"] == 0:

                fire_confidence = max(
                    fire_confidence,
                    detection["confidence"]
                )


        # ==============================
        # TEMPORAL VERIFICATION
        # ==============================

        status = verifier.update(
            fire_confidence
        )


        # ==============================
        # DEBUG INFORMATION
        # ==============================

        print(
            f"DEBUG -> Confidence: "
            f"{fire_confidence:.2f} | "
            f"Status: {status}"
        )


        # ==============================
        # FIRE GROWTH TRACKING
        # ==============================

        tracking = tracker.update(
            detections
        )


        # ==============================
        # RISK CALCULATION
        # ==============================

        risk = risk_engine.calculate(
            fire_confidence,
            tracking["area"],
            tracking["growth"],
            status
        )


        # ==============================
        # DRAW DETECTION BOXES
        # ==============================

        for detection in detections:

            x1, y1, x2, y2 = detection["box"]

            confidence = detection["confidence"]

            class_id = detection["class_id"]


            # --------------------------
            # Class label
            # --------------------------

            if class_id == 0:

                label = (
                    f"FIRE "
                    f"{confidence:.2f}"
                )

            elif class_id == 1:

                label = (
                    f"SMOKE "
                    f"{confidence:.2f}"
                )

            else:

                label = (
                    f"UNKNOWN "
                    f"{confidence:.2f}"
                )


            # --------------------------
            # Bounding box
            # --------------------------

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 0, 255),
                2
            )


            # --------------------------
            # Detection label
            # --------------------------

            cv2.putText(
                frame,
                label,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )


        # ==============================
        # FIREGUARD INFORMATION
        # ==============================

        cv2.putText(
            frame,
            f"STATUS: {status}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )


        cv2.putText(
            frame,
            f"CONFIDENCE: {fire_confidence:.2f}",
            (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


        cv2.putText(
            frame,
            f"FIRE AREA: {tracking['area']}",
            (20, 105),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


        cv2.putText(
            frame,
            f"GROWTH: {tracking['growth']}",
            (20, 140),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


        cv2.putText(
            frame,
            f"TREND: {tracking['trend']}",
            (20, 175),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


        cv2.putText(
            frame,
            f"RISK: {risk['level']} "
            f"({risk['score']})",
            (20, 210),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )


        # ==============================
        # SYSTEM STATUS
        # ==============================

        print(
            f"Status: {status} | "
            f"Confidence: {fire_confidence:.2f} | "
            f"Area: {tracking['area']} | "
            f"Growth: {tracking['growth']} | "
            f"Trend: {tracking['trend']} | "
            f"Risk: {risk['level']}"
        )


        # ==============================
        # SHOW VIDEO
        # ==============================

        video.show_frame(
            frame,
            "FIREGUARD AI"
        )


        # ==============================
        # PRESS Q TO EXIT
        # ==============================

        if video.should_stop():
            break


    # ==============================
    # CLEANUP
    # ==============================

    video.release()

    video.close()

    print("--------------------------------")
    print("FIREGUARD AI stopped.")


# ==============================
# PROGRAM ENTRY POINT
# ==============================

if __name__ == "__main__":
    main()