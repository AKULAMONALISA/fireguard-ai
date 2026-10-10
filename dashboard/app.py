
import sys
import time
import threading
from pathlib import Path
from datetime import datetime

import av
import cv2
import pandas as pd
import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase

# --------------------------------------------------
# PATHS AND PROJECT IMPORTS
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODEL_PATH = ROOT / "models" / "best.pt"
VIDEO_DIR = ROOT / "videos"
RESULTS_DIR = ROOT / "results"

VIDEO_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

from src.detector import FireDetector
from src.tracker import FireTracker
from src.verifier import FireVerifier
from src.risk_engine import RiskEngine
from src.incident_history import load_incidents, save_incident

try:
    from src.email_alert import send_email_alert
except ImportError:
    send_email_alert = None


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="FireGuard",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# STYLING
# --------------------------------------------------

st.markdown(
    """
    <style>
    .stApp {
        background: #f3f6fb;
        color: #17263c;
    }

    [data-testid="stHeader"] {
        background: #f3f6fb;
    }

    section.main > div.block-container {
        max-width: 1500px;
        padding: 1.5rem 2rem 3rem;
    }

    .hero {
        background: linear-gradient(
            115deg, #14243a, #244b76, #9f2530
        );
        border-radius: 20px;
        padding: 30px 34px;
        margin-bottom: 22px;
        box-shadow: 0 10px 28px rgba(20,36,58,.12);
    }

    .hero * {
        color: white !important;
    }

    .hero .eyebrow {
        color: #fecaca !important;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 3px;
    }

    .hero h1 {
        font-size: 40px !important;
        margin: 10px 0 !important;
    }

    .hero p {
        color: #e1eafa !important;
        font-size: 16px;
    }

    .kicker {
        color: #2457d6;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 1.8px;
        margin: 18px 0 6px;
    }

    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #dce4ee;
        border-radius: 15px;
        padding: 16px;
        box-shadow: 0 3px 12px rgba(20,36,58,.04);
    }

    [data-testid="stSidebar"] {
        background: white;
        border-right: 1px solid #dce4ee;
    }

    div.stButton > button,
    div.stDownloadButton > button {
        border-radius: 10px;
        min-height: 42px;
        font-weight: 700;
    }

    div.stButton > button[kind="primary"] {
        background: #dc2626;
        border-color: #dc2626;
        color: white;
    }

    hr {
        border-color: #dce4ee;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

DEFAULTS = {
    "fg_report": "",
    "fg_photo": None,
    "fg_video": None,
    "fg_original": None,
    "fg_original_name": "",
    "fg_growth": [],
    "fg_email_notice": None,
    "fg_status": "STANDBY",
    "fg_confidence": 0.0,
    "fg_risk_level": "LOW",
    "fg_risk_score": 0,
    "fg_frames": 0,
    "fg_last_video": "",
    "fg_latitude": 13.6288,
    "fg_longitude": 79.4192,
    "fg_live_saved_key": None,
    "fg_live_processor": None,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# --------------------------------------------------
# DETECTOR
# --------------------------------------------------

@st.cache_resource
def get_detector():
    if not MODEL_PATH.exists():
        return None
    return FireDetector(str(MODEL_PATH))


# --------------------------------------------------
# DETECTION HELPERS
# --------------------------------------------------

def get_fire_confidence(detections):
    """Return the highest confidence for class ID 0."""
    values = [
        float(d.get("confidence", 0))
        for d in detections
        if int(d.get("class_id", -1)) == 0
    ]
    return max(values, default=0.0)


def get_fire_area(detections):
    """Estimate total detected fire-box area in pixels."""
    total = 0

    for detection in detections:
        if int(detection.get("class_id", -1)) != 0:
            continue

        box = detection.get("box")
        if box is None:
            continue

        try:
            x1, y1, x2, y2 = map(int, box)
            total += max(0, x2 - x1) * max(0, y2 - y1)
        except (TypeError, ValueError):
            continue

    return total


def draw_detections(frame, detections):
    output = frame.copy()

    for detection in detections:
        try:
            x1, y1, x2, y2 = map(
                int, detection["box"]
            )
            class_id = int(detection.get("class_id", -1))
            confidence = float(
                detection.get("confidence", 0)
            )

            label = (
                "FIRE" if class_id == 0
                else "SMOKE" if class_id == 1
                else f"CLASS {class_id}"
            )

            color = (
                (0, 0, 255) if class_id == 0
                else (0, 165, 255)
            )

            cv2.rectangle(
                output, (x1, y1), (x2, y2),
                color, 2
            )

            cv2.putText(
                output,
                f"{label} {confidence:.0%}",
                (x1, max(25, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                color,
                2,
            )

        except (KeyError, TypeError, ValueError):
            continue

    return output


def calculate_risk(confidence, area, growth, verification):
    engine = RiskEngine()
    return engine.calculate(
        fire_confidence=confidence,
        fire_area=area,
        growth=growth,
        verified=verification,
    )


def draw_location(latitude, longitude):
    st.map(
        pd.DataFrame({
            "latitude": [latitude],
            "longitude": [longitude],
        }),
        latitude="latitude",
        longitude="longitude",
        zoom=10,
    )


# --------------------------------------------------
# EMAIL HELPER
# --------------------------------------------------

def send_notification(
    status,
    confidence,
    risk,
    latitude,
    longitude,
    timestamp,
):
    """
    Uses the project's existing email-alert function.
    Does not print email credentials or secrets.
    """
    if send_email_alert is None:
        return False, (
            "Email module could not be imported. "
            "Check src/email_alert.py."
        )

    try:
        result = send_email_alert(
            status=status,
            confidence=confidence,
            risk_level=risk["level"],
            risk_score=risk["score"],
            latitude=latitude,
            longitude=longitude,
            timestamp=timestamp,
        )

        # Some implementations return None on success.
        if result is False:
            return False, "Email function reported failure."

        return True, "Email alert sent."

    except Exception as exc:
        return False, f"Email failed: {exc}"


# --------------------------------------------------
# INCIDENT HISTORY
# --------------------------------------------------

def show_history():
    records = load_incidents()

    if not records:
        st.info("No incidents have been saved yet.")
        return

    df = pd.DataFrame(records)

    numeric_columns = [
        "confidence", "area", "growth", "risk_score",
        "latitude", "longitude", "frames_processed",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column], errors="coerce"
            )

    st.dataframe(
        df.iloc[::-1],
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download incident history CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="fireguard_incident_history.csv",
        mime="text/csv",
    )


# --------------------------------------------------
# LIVE CAMERA SHARED STATE
# --------------------------------------------------

LIVE_STATE = {
    "lock": threading.Lock(),
    "confidence": 0.0,
    "area": 0,
    "verification": "NO FIRE",
    "risk": {"score": 0, "level": "LOW"},
    "frame": None,
    "frames_processed": 0,
    "last_seen": None,
    "error": None,
}


# --------------------------------------------------
# LIVE CAMERA PROCESSOR
# --------------------------------------------------

class FireCameraProcessor(VideoProcessorBase):
    def __init__(self):
        self.detector = get_detector()
        self.verifier = FireVerifier()
        self.risk_engine = RiskEngine()
        self.frames_processed = 0
        self.previous_area = 0

    def recv(self, frame):
        image = frame.to_ndarray(format="bgr24")

        if self.detector is None:
            with LIVE_STATE["lock"]:
                LIVE_STATE["error"] = (
                    f"Model file not found: {MODEL_PATH}"
                )

            return av.VideoFrame.from_ndarray(
                image, format="bgr24"
            )

        try:
            detections = self.detector.detect(image)

            confidence = get_fire_confidence(detections)
            area = get_fire_area(detections)

            verification = self.verifier.update(
                confidence
            )

            growth = max(0, area - self.previous_area)
            self.previous_area = area

            risk = self.risk_engine.calculate(
                fire_confidence=confidence,
                fire_area=area,
                growth=growth,
                verified=verification,
            )

            annotated = draw_detections(image, detections)

            status_text = (
                "VERIFIED FIRE"
                if verification == "VERIFIED FIRE"
                else "POSSIBLE FIRE"
                if verification == "POSSIBLE FIRE"
                else "NO FIRE"
            )

            cv2.putText(
                annotated,
                f"{status_text} | Risk: {risk['level']}",
                (15, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255)
                if verification == "VERIFIED FIRE"
                else (0, 150, 255),
                2,
            )

            self.frames_processed += 1

            # Share only data. Do not call st.* from this worker.
            with LIVE_STATE["lock"]:
                LIVE_STATE["confidence"] = confidence
                LIVE_STATE["area"] = area
                LIVE_STATE["verification"] = verification
                LIVE_STATE["risk"] = risk
                LIVE_STATE["frame"] = annotated.copy()
                LIVE_STATE["frames_processed"] = (
                    self.frames_processed
                )
                LIVE_STATE["last_seen"] = (
                    datetime.now().isoformat(
                        timespec="seconds"
                    )
                )
                LIVE_STATE["error"] = None

            return av.VideoFrame.from_ndarray(
                annotated, format="bgr24"
            )

        except Exception as exc:
            with LIVE_STATE["lock"]:
                LIVE_STATE["error"] = str(exc)

            return av.VideoFrame.from_ndarray(
                image, format="bgr24"
            )


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown(
    """
    <div class="hero">
        <div class="eyebrow">
            WILDFIRE INTELLIGENCE PLATFORM
        </div>
        <h1>🔥 FireGuard</h1>
        <p>
            Detect early. Verify intelligently.
            Understand risk.
        </p>
        <p>
            AI Vision • Temporal Verification •
            Geospatial Awareness • Evidence Analytics
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.markdown("## 🔥 FireGuard")
    st.caption("AI fire monitoring dashboard")
    st.divider()

    latitude = st.number_input(
        "Latitude",
        value=float(st.session_state.fg_latitude),
        format="%.6f",
    )

    longitude = st.number_input(
        "Longitude",
        value=float(st.session_state.fg_longitude),
        format="%.6f",
    )

    st.session_state.fg_latitude = latitude
    st.session_state.fg_longitude = longitude

    confidence_threshold = st.slider(
        "Fire confidence threshold",
        min_value=0.10,
        max_value=0.90,
        value=0.35,
        step=0.05,
    )

    st.divider()

    uploaded_video = st.file_uploader(
        "Upload video for analysis",
        type=["mp4", "mov", "avi", "mkv"],
    )

    default_video = VIDEO_DIR / "fire.mp4"

    if uploaded_video is not None:
        input_video = RESULTS_DIR / uploaded_video.name

        if st.button(
            "Save uploaded video",
            use_container_width=True,
        ):
            input_video.write_bytes(
                uploaded_video.getvalue()
            )
            st.session_state.fg_last_video = str(
                input_video
            )
            st.success("Video saved.")

    elif st.session_state.fg_last_video:
        input_video = Path(
            st.session_state.fg_last_video
        )

    else:
        input_video = default_video

    page = st.radio(
        "NAVIGATION",
        [
            "Overview",
            "Live Camera",
            "Video Analysis",
            "Incident Report",
            "Evidence",
            "Growth Analytics",
            "Incident History",
        ],
    )

    st.divider()
    st.caption("FireGuard • AI-assisted monitoring")


# --------------------------------------------------
# MODEL AVAILABILITY
# --------------------------------------------------

if not MODEL_PATH.exists():
    st.error(
        f"Model not found: {MODEL_PATH}. "
        "Ensure models/best.pt exists in the project."
    )


# --------------------------------------------------
# LIVE CAMERA PAGE
# --------------------------------------------------

if page == "Live Camera":
    st.markdown(
        '<div class="kicker">REAL-TIME MONITORING</div>',
        unsafe_allow_html=True,
    )
    st.subheader("Live Camera Detection")

    st.write(
        "Allow browser camera access. "
        "Keep the camera running while reviewing detections."
    )

    if not MODEL_PATH.exists():
        st.error("Cannot start camera detection without best.pt.")
    else:
        webrtc_streamer(
            key="fireguard-live-camera",
            video_processor_factory=FireCameraProcessor,
            media_stream_constraints={
                "video": True,
                "audio": False,
            },
            async_processing=True,
        )

    st.divider()
    st.subheader("Latest camera results")

    if st.button("Refresh live results"):
        pass

    with LIVE_STATE["lock"]:
        live_confidence = LIVE_STATE["confidence"]
        live_area = LIVE_STATE["area"]
        live_verification = LIVE_STATE["verification"]
        live_risk = dict(LIVE_STATE["risk"])
        live_frame = (
            LIVE_STATE["frame"].copy()
            if LIVE_STATE["frame"] is not None
            else None
        )
        live_frames = LIVE_STATE["frames_processed"]
        live_seen = LIVE_STATE["last_seen"]
        live_error = LIVE_STATE["error"]

    if live_error:
        st.error(f"Camera processing issue: {live_error}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Fire confidence", f"{live_confidence:.1%}")
    m2.metric("Detected area", f"{live_area:,} px²")
    m3.metric("Risk", live_risk["level"])
    m4.metric("Frames processed", live_frames)

    st.info(f"Verification: {live_verification}")

    if live_seen:
        st.caption(f"Last processed frame: {live_seen}")

    if live_frame is not None:
        st.image(
            cv2.cvtColor(live_frame, cv2.COLOR_BGR2RGB),
            caption="Latest annotated camera frame",
            use_container_width=True,
        )

    st.warning(
        "A model detection is not proof of a real fire. "
        "Verify the scene before contacting emergency services."
    )

    can_save_live = (
        live_verification == "VERIFIED FIRE"
        and live_confidence >= confidence_threshold
    )

    if can_save_live:
        st.success(
            "The current camera result meets the "
            "verification and confidence conditions."
        )
    else:
        st.caption(
            "Saving a confirmed live incident requires "
            "VERIFIED FIRE and confidence above your threshold."
        )

    if st.button(
        "Save verified live incident and send email",
        type="primary",
        disabled=not can_save_live,
        use_container_width=True,
    ):
        incident_key = (
            live_seen,
            round(live_confidence, 3),
            live_area,
        )

        if incident_key == st.session_state.fg_live_saved_key:
            st.info(
                "This live result has already been saved. "
                "Wait for a new result before saving again."
            )
        else:
            timestamp = datetime.now().isoformat(
                timespec="seconds"
            )

            report = (
                "FIREGUARD LIVE CAMERA INCIDENT\n"
                f"Timestamp: {timestamp}\n"
                f"Status: VERIFIED FIRE\n"
                f"Confidence: {live_confidence:.1%}\n"
                f"Area: {live_area}\n"
                f"Risk: {live_risk['level']}\n"
                f"Risk score: {live_risk['score']}\n"
                f"Latitude: {latitude}\n"
                f"Longitude: {longitude}\n"
                f"Frames processed: {live_frames}\n"
            )

            save_incident(
                status="FIRE ALERT",
                confidence=live_confidence,
                area=live_area,
                growth=0,
                trend="live camera",
                risk_level=live_risk["level"],
                risk_score=live_risk["score"],
                latitude=latitude,
                longitude=longitude,
                frames_processed=live_frames,
            )

            if live_frame is not None:
                photo_path = RESULTS_DIR / "live_evidence.jpg"
                cv2.imwrite(str(photo_path), live_frame)
                st.session_state.fg_photo = str(photo_path)

            st.session_state.fg_status = "FIRE ALERT"
            st.session_state.fg_confidence = live_confidence
            st.session_state.fg_risk_level = live_risk["level"]
            st.session_state.fg_risk_score = live_risk["score"]
            st.session_state.fg_frames = live_frames
            st.session_state.fg_report = report
            st.session_state.fg_live_saved_key = incident_key

            success, message = send_notification(
                "FIRE ALERT",
                live_confidence,
                live_risk,
                latitude,
                longitude,
                timestamp,
            )

            st.session_state.fg_email_notice = message

            st.success("Live incident saved to history.")
            if success:
                st.success(message)
            else:
                st.warning(
                    "Incident saved, but email was not confirmed: "
                    + message
                )

    if st.session_state.fg_email_notice:
        st.caption(
            "Most recent email status: "
            + str(st.session_state.fg_email_notice)
        )


# --------------------------------------------------
# VIDEO ANALYSIS PAGE
# --------------------------------------------------

elif page == "Video Analysis":
    st.markdown(
        '<div class="kicker">VIDEO FORENSICS</div>',
        unsafe_allow_html=True,
    )
    st.subheader("Analyze a fire-monitoring video")

    if not input_video.exists():
        st.warning(
            f"Video not found: {input_video}. "
            "Upload a video in the sidebar or add videos/fire.mp4."
        )
    elif not MODEL_PATH.exists():
        st.error("Model file is missing.")
    else:
        st.write(f"Input video: `{input_video.name}`")

        if st.button(
            "START FIRE ANALYSIS",
            type="primary",
            use_container_width=True,
        ):
            cap = cv2.VideoCapture(str(input_video))

            if not cap.isOpened():
                st.error("Could not open the input video.")
            else:
                detector = get_detector()
                tracker = FireTracker()
                verifier = FireVerifier(
                    threshold=confidence_threshold
                )
                risk_engine = RiskEngine()

                fps = cap.get(cv2.CAP_PROP_FPS)
                if not fps or fps <= 0:
                    fps = 20.0

                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                total_frames = int(
                    cap.get(cv2.CAP_PROP_FRAME_COUNT)
                )

                output_path = RESULTS_DIR / (
                    f"fireguard_annotated_"
                    f"{datetime.now():%Y%m%d_%H%M%S}.mp4"
                )

                writer = cv2.VideoWriter(
                    str(output_path),
                    cv2.VideoWriter_fourcc(*"mp4v"),
                    fps,
                    (width, height),
                )

                progress = st.progress(0)
                preview = st.empty()
                status_box = st.empty()
                metrics_box = st.empty()

                best_confidence = 0.0
                best_frame = None
                last_confidence = 0.0
                last_area = 0
                last_growth = 0
                verified_fire_seen = False
                frames_processed = 0
                growth_history = []
                previous_area = 0
                last_risk = {"score": 0, "level": "LOW"}
                last_verification = "NO FIRE"

                while cap.isOpened():
                    ok, frame = cap.read()
                    if not ok:
                        break

                    detections = detector.detect(frame)
                    tracker.update(detections)

                    confidence = get_fire_confidence(detections)
                    area = get_fire_area(detections)
                    growth = max(0, area - previous_area)
                    previous_area = area

                    verification = verifier.update(confidence)

                    if verification == "VERIFIED FIRE":
                        verified_fire_seen = True

                    risk = risk_engine.calculate(
                        fire_confidence=confidence,
                        fire_area=area,
                        growth=growth,
                        verified=verification,
                    )

                    annotated = draw_detections(frame, detections)

                    cv2.putText(
                        annotated,
                        f"Confidence: {confidence:.1%} | "
                        f"Risk: {risk['level']} ({risk['score']})",
                        (15, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.65,
                        (0, 0, 255)
                        if verification == "VERIFIED FIRE"
                        else (0, 165, 255),
                        2,
                    )

                    writer.write(annotated)
                    frames_processed += 1

                    growth_history.append({
                        "frame": frames_processed,
                        "confidence": confidence,
                        "area": area,
                        "growth": growth,
                        "risk_score": risk["score"],
                    })

                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_frame = annotated.copy()

                    last_confidence = confidence
                    last_area = area
                    last_growth = growth
                    last_risk = risk
                    last_verification = verification

                    if total_frames > 0:
                        progress.progress(
                            min(frames_processed / total_frames, 1.0)
                        )

                    preview.image(
                        cv2.cvtColor(
                            annotated, cv2.COLOR_BGR2RGB
                        ),
                        use_container_width=True,
                    )

                    metrics_box.metric(
                        "Current confidence",
                        f"{confidence:.1%}",
                    )
                    status_box.write(
                        f"Verification: **{verification}** · "
                        f"Risk: **{risk['level']}** "
                        f"({risk['score']}/100)"
                    )

                cap.release()
                writer.release()
                progress.progress(1.0)

                if frames_processed == 0:
                    st.error("No frames could be processed.")
                else:
                    confirmed = (
                        verified_fire_seen
                        and best_confidence >= confidence_threshold
                    )

                    if confirmed:
                        final_status = "FIRE ALERT"
                    elif best_confidence >= confidence_threshold:
                        final_status = "POSSIBLE FIRE — REVIEW"
                    else:
                        final_status = "NO FIRE DETECTED"

                    timestamp = datetime.now().isoformat(
                        timespec="seconds"
                    )

                    report = (
                        "FIREGUARD INCIDENT REPORT\n"
                        f"Timestamp: {timestamp}\n"
                        f"Video: {input_video.name}\n"
                        f"Status: {final_status}\n"
                        f"Verification: {last_verification}\n"
                        f"Best confidence: {best_confidence:.1%}\n"
                        f"Last detected area: {last_area}\n"
                        f"Last growth: {last_growth}\n"
                        f"Risk level: {last_risk['level']}\n"
                        f"Risk score: {last_risk['score']}/100\n"
                        f"Frames processed: {frames_processed}\n"
                        f"Latitude: {latitude}\n"
                        f"Longitude: {longitude}\n"
                    )

                    save_incident(
                        status=final_status,
                        confidence=best_confidence,
                        area=last_area,
                        growth=last_growth,
                        trend="increasing"
                        if last_growth > 0 else "stable",
                        risk_level=last_risk["level"],
                        risk_score=last_risk["score"],
                        latitude=latitude,
                        longitude=longitude,
                        frames_processed=frames_processed,
                    )

                    st.session_state.fg_status = final_status
                    st.session_state.fg_confidence = best_confidence
                    st.session_state.fg_risk_level = last_risk["level"]
                    st.session_state.fg_risk_score = last_risk["score"]
                    st.session_state.fg_frames = frames_processed
                    st.session_state.fg_report = report
                    st.session_state.fg_photo = (
                        RESULTS_DIR / "best_fire_frame.jpg"
                    ).as_posix() if best_frame is not None else None
                    st.session_state.fg_video = str(output_path)
                    st.session_state.fg_original = str(input_video)
                    st.session_state.fg_original_name = input_video.name
                    st.session_state.fg_growth = growth_history
                    st.session_state.fg_last_video = str(input_video)

                    if best_frame is not None:
                        cv2.imwrite(
                            str(RESULTS_DIR / "best_fire_frame.jpg"),
                            best_frame,
                        )

                    st.success(f"Analysis complete: {final_status}")
                    st.write(report)

                    if final_status in (
                        "FIRE ALERT",
                        "POSSIBLE FIRE — REVIEW",
                    ):
                        success, message = send_notification(
                            final_status,
                            best_confidence,
                            last_risk,
                            latitude,
                            longitude,
                            timestamp,
                        )
                        st.session_state.fg_email_notice = message

                        if success:
                            st.success(message)
                        else:
                            st.warning(
                                "Incident saved, but email was not confirmed: "
                                + message
                            )
                    else:
                        st.info(
                            "No alert email was sent because the "
                            "analysis did not meet the alert conditions."
                        )


# --------------------------------------------------
# OVERVIEW PAGE
# --------------------------------------------------

elif page == "Overview":
    st.markdown(
        '<div class="kicker">SYSTEM OVERVIEW</div>',
        unsafe_allow_html=True,
    )

    incidents = load_incidents()
    df = pd.DataFrame(incidents)

    total_incidents = len(df)
    fire_alerts = (
        int(df["status"].astype(str).str.contains(
            "FIRE ALERT", case=False
        ).sum())
        if not df.empty and "status" in df.columns
        else 0
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("System status", st.session_state.fg_status)
    c2.metric("Saved incidents", total_incidents)
    c3.metric("Fire alerts", fire_alerts)
    c4.metric(
        "Latest confidence",
        f"{st.session_state.fg_confidence:.1%}",
    )

    st.subheader("Latest analysis")
    left, right = st.columns([1.2, 1])

    with left:
        st.write(
            f"**Status:** {st.session_state.fg_status}"
        )
        st.write(
            f"**Risk level:** {st.session_state.fg_risk_level}"
        )
        st.write(
            f"**Risk score:** {st.session_state.fg_risk_score}/100"
        )
        st.write(
            f"**Frames processed:** {st.session_state.fg_frames}"
        )

        if st.session_state.fg_report:
            st.text(st.session_state.fg_report)

    with right:
        st.subheader("Monitoring location")
        draw_location(latitude, longitude)


# --------------------------------------------------
# INCIDENT REPORT PAGE
# --------------------------------------------------

elif page == "Incident Report":
    st.markdown(
        '<div class="kicker">INCIDENT DOCUMENTATION</div>',
        unsafe_allow_html=True,
    )
    st.subheader("Incident Report")

    if not st.session_state.fg_report:
        st.info("Run video analysis or save a verified live incident first.")
    else:
        st.code(st.session_state.fg_report)

        st.download_button(
            "Download incident report",
            data=st.session_state.fg_report,
            file_name="fireguard_incident_report.txt",
            mime="text/plain",
        )

    if st.session_state.fg_email_notice:
        st.info(
            f"Latest email status: {st.session_state.fg_email_notice}"
        )


# --------------------------------------------------
# EVIDENCE PAGE
# --------------------------------------------------

elif page == "Evidence":
    st.markdown(
        '<div class="kicker">EVIDENCE VAULT</div>',
        unsafe_allow_html=True,
    )
    st.subheader("Captured Evidence")

    photo = st.session_state.fg_photo

    if photo:
        photo_path = Path(photo)
        if photo_path.exists():
            st.image(
                str(photo_path),
                caption="Annotated evidence frame",
                use_container_width=True,
            )
            st.download_button(
                "Download evidence image",
                data=photo_path.read_bytes(),
                file_name=photo_path.name,
                mime="image/jpeg",
            )
        else:
            st.info("The saved evidence image is unavailable.")
    else:
        st.info("No evidence image saved yet.")

    for label, key in [
        ("Annotated video", "fg_video"),
        ("Original video", "fg_original"),
    ]:
        value = st.session_state.get(key)

        if value and Path(value).exists():
            path = Path(value)
            st.write(f"**{label}:** {path.name}")

            mime = (
                "video/mp4"
                if path.suffix.lower() == ".mp4"
                else "application/octet-stream"
            )

            st.download_button(
                f"Download {label.lower()}",
                data=path.read_bytes(),
                file_name=path.name,
                mime=mime,
                key=f"download_{key}",
            )


# --------------------------------------------------
# GROWTH ANALYTICS PAGE
# --------------------------------------------------

elif page == "Growth Analytics":
    st.markdown(
        '<div class="kicker">TEMPORAL ANALYTICS</div>',
        unsafe_allow_html=True,
    )
    st.subheader("Fire Detection and Growth")

    growth_history = st.session_state.fg_growth

    if not growth_history:
        st.info("Run video analysis to generate analytics.")
    else:
        growth_df = pd.DataFrame(growth_history)

        chart_columns = [
            column for column in
            ["confidence", "area", "growth", "risk_score"]
            if column in growth_df.columns
        ]

        selected_metric = st.selectbox(
            "Select metric",
            chart_columns,
        )

        st.line_chart(
            growth_df.set_index("frame")[[selected_metric]]
        )

        st.dataframe(
            growth_df,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download growth analytics CSV",
            data=growth_df.to_csv(index=False).encode("utf-8"),
            file_name="fireguard_growth_analytics.csv",
            mime="text/csv",
        )


# --------------------------------------------------
# INCIDENT HISTORY PAGE
# --------------------------------------------------

elif page == "Incident History":
    st.markdown(
        '<div class="kicker">INCIDENT ARCHIVE</div>',
        unsafe_allow_html=True,
    )
    st.subheader("Incident History")
    show_history()


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()
st.caption(
    "FireGuard is an AI-assisted monitoring prototype. "
    "Detections and risk scores require human verification."
)
