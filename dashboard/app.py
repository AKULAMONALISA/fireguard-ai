
import sys
from pathlib import Path
from datetime import datetime

import cv2
import pandas as pd
import streamlit as st

# ============================================================
# FIREGUARD AI - COMPLETE DASHBOARD
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.incident_history import load_incidents, save_incident
from src.detector import FireDetector
from src.tracker import FireTracker
from src.verifier import FireVerifier
from src.risk_engine import RiskEngine

try:
    from src.email_alert import send_email_alert
except ImportError:
    send_email_alert = None

MODELS_DIR = ROOT / "models"
VIDEOS_DIR = ROOT / "videos"
RESULTS_DIR = ROOT / "results"

MODEL_PATH = MODELS_DIR / "best.pt"
DEFAULT_VIDEO_PATH = VIDEOS_DIR / "fire.mp4"
ANNOTATED_VIDEO_PATH = RESULTS_DIR / "fireguard_annotated.mp4"
HISTORY_PATH = RESULTS_DIR / "incident_history.csv"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="FIREGUARD AI",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# SESSION STATE
# ============================================================

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
    "fg_risk_level": "—",
    "fg_risk_score": 0.0,
    "fg_frames": 0,
    "fg_last_video": "",
    "fg_page": "Overview",
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ============================================================
# STYLING
# ============================================================

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
        background: linear-gradient(115deg, #14243a, #244b76, #9f2530);
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

# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="hero">
        <div class="eyebrow">WILDFIRE INTELLIGENCE PLATFORM</div>
        <h1>🔥 FIREGUARD AI</h1>
        <p>Detect early. Verify intelligently. Understand risk.</p>
        <p>AI Vision • Temporal Verification • Geospatial Awareness
        • Evidence Analytics</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# SIDEBAR CONTROLS
# ============================================================

with st.sidebar:
    st.markdown("## 🚁 Mission Control")
    st.caption("FIREGUARD / FIELD OPERATIONS")
    st.divider()

    st.markdown("### 📍 Incident coordinates")

    latitude = st.number_input(
        "Latitude",
        min_value=-90.0,
        max_value=90.0,
        value=13.6288,
        format="%.6f",
        key="fg_latitude",
    )

    longitude = st.number_input(
        "Longitude",
        min_value=-180.0,
        max_value=180.0,
        value=79.4192,
        format="%.6f",
        key="fg_longitude",
    )

    st.caption(
        "Example coordinates only. Enter the actual incident location."
    )

    st.divider()
    st.markdown("### 🎯 Detection settings")

    confidence_threshold = st.slider(
        "Confidence threshold",
        min_value=0.10,
        max_value=0.90,
        value=0.35,
        step=0.05,
        key="fg_threshold",
    )

    st.divider()
    st.markdown("### 🎞️ Video input")

    uploaded_video = st.file_uploader(
        "Upload fire/smoke video",
        type=["mp4", "avi", "mov", "mkv", "mpeg", "mpg"],
        key="fg_uploader",
    )

    if uploaded_video is not None:
        st.success(f"Selected: {uploaded_video.name}")
    elif DEFAULT_VIDEO_PATH.exists():
        st.info(f"Default video: {DEFAULT_VIDEO_PATH.name}")
    else:
        st.warning("Upload a video to begin.")

    st.divider()
    st.markdown("### System readiness")

    st.write(
        "🟢 Model ready"
        if MODEL_PATH.exists()
        else "🔴 Model file missing"
    )

    st.write(
        "🟢 Video available"
        if uploaded_video is not None or DEFAULT_VIDEO_PATH.exists()
        else "🔴 No video selected"
    )

    start_button = st.button(
        "🚨 START FIRE ANALYSIS",
        type="primary",
        use_container_width=True,
    )

    st.divider()
    st.markdown("### 🧭 Quick navigation")

    page_choice = st.radio(
        "Open dashboard section",
        [
            "Overview",
            "Incident Report",
            "Evidence",
            "Growth Analytics",
            "Incident History",
        ],
        key="fg_navigation",
        label_visibility="collapsed",
    )

# ============================================================
# VIDEO INPUT PREPARATION
# ============================================================

selected_video_name = (
    uploaded_video.name
    if uploaded_video is not None
    else DEFAULT_VIDEO_PATH.name
)

video_path_for_run = None

if uploaded_video is not None:
    suffix = Path(uploaded_video.name).suffix.lower()

    if suffix not in {
        ".mp4", ".avi", ".mov", ".mkv", ".mpeg", ".mpg"
    }:
        suffix = ".mp4"

    video_path_for_run = RESULTS_DIR / f"uploaded_input{suffix}"

    try:
        video_path_for_run.write_bytes(uploaded_video.getvalue())
    except OSError as exc:
        st.error(f"Could not save uploaded video: {exc}")

elif DEFAULT_VIDEO_PATH.exists():
    video_path_for_run = DEFAULT_VIDEO_PATH

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_fire_confidence(detections):
    """Return the highest confidence for class ID 0."""
    return max(
        (
            float(item["confidence"])
            for item in detections
            if int(item["class_id"]) == 0
        ),
        default=0.0,
    )


def draw_detections(frame, detections):
    output = frame.copy()

    for item in detections:
        x1, y1, x2, y2 = map(int, item["box"])
        confidence = float(item["confidence"])
        class_id = int(item["class_id"])

        if class_id == 0:
            label = f"FIRE {confidence:.2f}"
            color = (0, 0, 230)
        elif class_id == 1:
            label = f"SMOKE {confidence:.2f}"
            color = (0, 140, 255)
        else:
            label = f"OBJECT {confidence:.2f}"
            color = (20, 150, 20)

        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)

        cv2.putText(
            output,
            label,
            (x1, max(y1 - 8, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            color,
            2,
        )

    return output


def get_risk(engine, confidence, frame_number):
    try:
        result = engine.calculate(confidence, frame_number)
    except TypeError:
        try:
            result = engine.calculate(confidence)
        except Exception:
            result = {}
    except Exception:
        result = {}

    return result if isinstance(result, dict) else {}


def risk_value(data, *keys, default=None):
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


def draw_map(lat, lon):
    st.map(
        pd.DataFrame(
            {"latitude": [lat], "longitude": [lon]}
        ),
        latitude="latitude",
        longitude="longitude",
        size=200,
    )


def show_history():
    try:
        records = load_incidents()
    except Exception as exc:
        st.error(f"Could not load incident history: {exc}")
        return

    if not records:
        st.info("No saved incidents yet.")
        return

    df = pd.DataFrame(records)

    numeric_columns = [
        "confidence",
        "fire_area_pixels",
        "growth_pixels",
        "risk_score",
        "latitude",
        "longitude",
        "frames_processed",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    st.markdown("### 📋 Previous analysis runs")

    st.dataframe(
        df.iloc[::-1].head(50),
        hide_index=True,
        use_container_width=True,
    )

    if "risk_score" in df.columns:
        chart_df = df[["risk_score"]].dropna().tail(30)

        if not chart_df.empty:
            st.markdown("### 📈 Risk score across saved runs")
            st.line_chart(chart_df, y="risk_score")

    st.download_button(
        "⬇️ DOWNLOAD INCIDENT HISTORY CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="fireguard_incident_history.csv",
        mime="text/csv",
        key="fg_history_download",
    )


# ============================================================
# VIDEO ANALYSIS
# ============================================================

if start_button:
    cap = None
    writer = None

    frame_number = 0
    fire_frames = 0
    strongest_confidence = 0.0
    best_frame = None
    best_detections = []
    growth_data = []
    verification_result = False
    latest_risk = {}

    try:
        if not MODEL_PATH.exists():
            st.error(f"Model file not found: {MODEL_PATH}")

        elif (
            not video_path_for_run
            or not Path(video_path_for_run).exists()
        ):
            st.error("Please select a valid video file.")

        else:
            detector = FireDetector(str(MODEL_PATH))
            tracker = FireTracker()
            verifier = FireVerifier()
            risk_engine = RiskEngine()

            cap = cv2.VideoCapture(str(video_path_for_run))

            if not cap.isOpened():
                st.error("Could not open the selected video.")

            else:
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                if width <= 0 or height <= 0:
                    st.error("The video has invalid dimensions.")

                else:
                    writer = cv2.VideoWriter(
                        str(ANNOTATED_VIDEO_PATH),
                        cv2.VideoWriter_fourcc(*"mp4v"),
                        fps,
                        (width, height),
                    )

                    if not writer.isOpened():
                        writer.release()
                        writer = None

                    st.info(f"Analyzing video: {selected_video_name}")

                    progress = st.progress(0)
                    frame_display = st.empty()

                    status_slot = st.empty()
                    confidence_slot = st.empty()
                    risk_slot = st.empty()
                    telemetry_slot = st.empty()
                    verification_slot = st.empty()

                    status_slot.info("AI analysis is running...")

                    while True:
                        ok, frame = cap.read()

                        if not ok:
                            break

                        frame_number += 1

                        detections = detector.detect(frame)
                        tracker.update(detections)

                        fire_conf = get_fire_confidence(detections)

                        growth_data.append({
                            "frame": frame_number,
                            "confidence": fire_conf,
                        })

                        if fire_conf > 0:
                            fire_frames += 1

                        if fire_conf > strongest_confidence:
                            strongest_confidence = fire_conf
                            best_frame = frame.copy()
                            best_detections = list(detections)

                        try:
                            verification_result = verifier.update(fire_conf)
                        except Exception:
                            verification_result = (
                                fire_conf >= confidence_threshold
                            )

                        latest_risk = get_risk(
                            risk_engine,
                            fire_conf,
                            frame_number,
                        )

                        annotated = draw_detections(frame, detections)

                        if writer is not None:
                            writer.write(annotated)

                        if frame_number % 3 == 0 or frame_number == 1:
                            frame_display.image(
                                cv2.cvtColor(
                                    annotated,
                                    cv2.COLOR_BGR2RGB,
                                ),
                                caption=f"Processed frame {frame_number}",
                                use_container_width=True,
                            )

                        if total_frames > 0:
                            progress.progress(
                                min(frame_number / total_frames, 1.0)
                            )

                        confidence_slot.metric(
                            "CURRENT FIRE CONFIDENCE",
                            f"{fire_conf * 100:.1f}%",
                        )

                        current_risk = str(
                            risk_value(
                                latest_risk,
                                "risk_level",
                                "level",
                                default="MONITORING",
                            )
                        )

                        risk_slot.metric("RISK LEVEL", current_risk.upper())

                        telemetry_slot.caption(
                            f"Frames processed: {frame_number} | "
                            f"Frames with fire detections: {fire_frames}"
                        )

                        verification_slot.write(
                            "Detection verified by temporal module"
                            if verification_result
                            else "Monitoring detections..."
                        )

                    progress.progress(1.0)

                    if writer is not None:
                        writer.release()
                        writer = None

                    cap.release()
                    cap = None

                    # Save best evidence frame.
                    photo_bytes = None

                    if best_frame is not None:
                        evidence_frame = draw_detections(
                            best_frame,
                            best_detections,
                        )

                        encoded_ok, encoded = cv2.imencode(
                            ".jpg",
                            evidence_frame,
                        )

                        if encoded_ok:
                            photo_bytes = encoded.tobytes()

                    # Final risk information.
                    risk_level = str(
                        risk_value(
                            latest_risk,
                            "risk_level",
                            "level",
                            default="LOW",
                        )
                    ).upper()

                    risk_score = risk_value(
                        latest_risk,
                        "risk_score",
                        "score",
                        default=0,
                    )

                    try:
                        risk_score = float(risk_score)
                    except (TypeError, ValueError):
                        risk_score = 0.0

                    fire_confirmed = (
                        strongest_confidence >= confidence_threshold
                        and bool(verification_result)
                    )

                    if fire_confirmed or risk_level in {
                        "HIGH", "CRITICAL", "SEVERE"
                    }:
                        final_status = "FIRE ALERT"
                    elif strongest_confidence > 0:
                        final_status = "POSSIBLE FIRE — REVIEW"
                    else:
                        final_status = "NO FIRE DETECTED"

                    # Persist dashboard results across reruns.
                    st.session_state.fg_growth = growth_data
                    st.session_state.fg_photo = photo_bytes
                    st.session_state.fg_video = (
                        str(ANNOTATED_VIDEO_PATH)
                        if ANNOTATED_VIDEO_PATH.exists()
                        and ANNOTATED_VIDEO_PATH.stat().st_size > 0
                        else None
                    )
                    st.session_state.fg_original = str(video_path_for_run)
                    st.session_state.fg_original_name = selected_video_name
                    st.session_state.fg_last_video = selected_video_name
                    st.session_state.fg_status = final_status
                    st.session_state.fg_confidence = strongest_confidence
                    st.session_state.fg_risk_level = risk_level
                    st.session_state.fg_risk_score = risk_score
                    st.session_state.fg_frames = frame_number

                    report = f"""
FIREGUARD AI — INCIDENT REPORT
================================
Analysis time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Input video: {selected_video_name}
Final status: {final_status}
Frames processed: {frame_number}
Frames with fire detections: {fire_frames}
Highest fire confidence: {strongest_confidence * 100:.2f}%
Risk level: {risk_level}
Risk score: {risk_score:.2f}
Latitude: {latitude:.6f}
Longitude: {longitude:.6f}

Note:
This is an AI-assisted screening result. Review the evidence
and follow your site's emergency procedures when needed.
""".strip()

                    st.session_state.fg_report = report

                    # Save incident history using the existing API.
                    try:
                        save_incident(
                            status=final_status,
                            confidence=strongest_confidence,
                            area=0,
                            growth=0,
                            trend="unknown",
                            risk_level=risk_level,
                            risk_score=risk_score,
                            latitude=latitude,
                            longitude=longitude,
                            frames_processed=frame_number,
                        )
                    except Exception as exc:
                        st.warning(
                            "Analysis completed, but history could not "
                            f"be saved: {exc}"
                        )

                    # Send alert email when appropriate.
                    st.session_state.fg_email_notice = None

                    if final_status == "FIRE ALERT":
                        if send_email_alert is None:
                            st.session_state.fg_email_notice = (
                                "Email module could not be imported."
                            )
                        else:
                            try:
                                result = send_email_alert(
                                    status=final_status,
                                    confidence=strongest_confidence,
                                    risk_level=risk_level,
                                    video_name=selected_video_name,
                                )
                                st.session_state.fg_email_notice = (
                                    f"Email alert function result: {result}"
                                )
                            except Exception as exc:
                                st.session_state.fg_email_notice = (
                                    f"Email alert failed: {exc}"
                                )

                    status_slot.success(f"Analysis finished: {final_status}")

                    st.success(
                        "Video analysis finished. Use the sidebar navigation "
                        "to open the report, evidence, graph, or history."
                    )

    except Exception as exc:
        st.error(f"Analysis could not finish: {exc}")
        st.info(
            "Check that the detector, tracker, verifier and risk engine "
            "modules are configured correctly."
        )

    finally:
        if cap is not None:
            cap.release()

        if writer is not None:
            writer.release()

# ============================================================
# OVERVIEW
# ============================================================

if page_choice == "Overview":
    st.markdown(
        '<div class="kicker">01 / MISSION OVERVIEW</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("FIRE STATUS", st.session_state.fg_status)
    c2.metric(
        "CONFIDENCE",
        f"{st.session_state.fg_confidence * 100:.1f}%"
        if st.session_state.fg_report else "—",
    )
    c3.metric("FRAMES PROCESSED", st.session_state.fg_frames or "—")
    c4.metric(
        "RISK LEVEL",
        st.session_state.fg_risk_level,
        f"Score: {st.session_state.fg_risk_score:.1f}"
        if st.session_state.fg_report else None,
    )

    st.divider()

    left, right = st.columns([1.5, 1])

    with left:
        st.markdown("### 🎥 Latest analysis")
        if st.session_state.fg_video and Path(
            st.session_state.fg_video
        ).exists():
            st.video(st.session_state.fg_video)
        elif st.session_state.fg_original and Path(
            st.session_state.fg_original
        ).exists():
            st.video(st.session_state.fg_original)
        else:
            st.info("Run an analysis to view the video here.")

    with right:
        st.markdown("### 📡 Incident location")
        st.write(f"Latitude: {latitude:.6f}")
        st.write(f"Longitude: {longitude:.6f}")
        draw_map(latitude, longitude)
        st.caption(
            "Map uses manually entered coordinates, not coordinates "
            "automatically extracted from the video."
        )

    if st.session_state.fg_email_notice:
        st.info(st.session_state.fg_email_notice)

    st.divider()
    st.markdown("### ⚡ Jump to a section")

    jump1, jump2, jump3, jump4 = st.columns(4)

    with jump1:
        st.button(
            "📄 Report",
            on_click=lambda: st.session_state.update(
                fg_navigation="Incident Report"
            ),
            use_container_width=True,
        )

    with jump2:
        st.button(
            "🖼️ Evidence",
            on_click=lambda: st.session_state.update(
                fg_navigation="Evidence"
            ),
            use_container_width=True,
        )

    with jump3:
        st.button(
            "📈 Growth graph",
            on_click=lambda: st.session_state.update(
                fg_navigation="Growth Analytics"
            ),
            use_container_width=True,
        )

    with jump4:
        st.button(
            "🗂️ History",
            on_click=lambda: st.session_state.update(
                fg_navigation="Incident History"
            ),
            use_container_width=True,
        )

# ============================================================
# REPORT PAGE
# ============================================================

elif page_choice == "Incident Report":
    st.markdown(
        '<div class="kicker">02 / INCIDENT REPORT</div>',
        unsafe_allow_html=True,
    )
    st.title("📄 AI Incident Report")

    report = st.session_state.fg_report

    if report:
        st.success("Incident report is ready.")
        st.text_area(
            "Report contents",
            value=report,
            height=360,
            disabled=True,
        )

        st.download_button(
            "⬇️ DOWNLOAD INCIDENT REPORT",
            data=report,
            file_name="fireguard_incident_report.txt",
            mime="text/plain",
            key="fg_report_download",
        )
    else:
        st.info("No report yet. Run the video analysis first.")

# ============================================================
# EVIDENCE PAGE
# ============================================================

elif page_choice == "Evidence":
    st.markdown(
        '<div class="kicker">03 / EVIDENCE</div>',
        unsafe_allow_html=True,
    )
    st.title("🖼️ Incident Evidence")

    if not st.session_state.fg_report:
        st.info("Run an analysis first to generate evidence.")
    else:
        photo = st.session_state.fg_photo
        video = st.session_state.fg_video
        original = st.session_state.fg_original

        photo_col, video_col = st.columns(2)

        with photo_col:
            st.markdown("### 📸 Strongest detection photo")

            if photo:
                st.image(
                    photo,
                    caption="Strongest detected frame",
                    use_container_width=True,
                )
                st.download_button(
                    "⬇️ DOWNLOAD DETECTION PHOTO",
                    data=photo,
                    file_name="fireguard_fire_evidence.jpg",
                    mime="image/jpeg",
                    key="fg_photo_download",
                )
            else:
                st.info("No detection photo was saved.")

        with video_col:
            st.markdown("### 🎬 Annotated evidence video")

            if video and Path(video).exists():
                st.video(video)
                st.download_button(
                    "⬇️ DOWNLOAD ANNOTATED VIDEO",
                    data=Path(video).read_bytes(),
                    file_name="fireguard_evidence.mp4",
                    mime="video/mp4",
                    key="fg_annotated_download",
                )
            else:
                st.info("No annotated video is available.")

        if original and Path(original).exists():
            st.markdown("### 🎥 Original input video")
            st.video(original)
            st.download_button(
                "⬇️ DOWNLOAD ORIGINAL VIDEO",
                data=Path(original).read_bytes(),
                file_name=st.session_state.fg_original_name
                or "fireguard_input_video.mp4",
                mime="video/mp4",
                key="fg_original_download",
            )

# ============================================================
# GROWTH ANALYTICS PAGE
# ============================================================

elif page_choice == "Growth Analytics":
    st.markdown(
        '<div class="kicker">04 / FIRE DYNAMICS</div>',
        unsafe_allow_html=True,
    )
    st.title("📈 Growth Analytics")

    growth = st.session_state.fg_growth

    if growth:
        growth_df = pd.DataFrame(growth)

        st.markdown("### Fire confidence per frame")
        st.line_chart(
            growth_df,
            x="frame",
            y="confidence",
            use_container_width=True,
        )
        st.caption(
            "This graph shows model confidence by frame. It does not "
            "directly measure physical fire size or fire growth."
        )

        st.markdown("### Recent frame results")
        st.dataframe(
            growth_df.tail(20),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("Run an analysis to generate the graph.")

# ============================================================
# INCIDENT HISTORY PAGE
# ============================================================

elif page_choice == "Incident History":
    st.markdown(
        '<div class="kicker">05 / HISTORICAL INTELLIGENCE</div>',
        unsafe_allow_html=True,
    )
    st.title("🗂️ Incident History")

    st.caption(
        "Saved analysis records are loaded from the existing history module."
    )

    show_history()

# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "FIREGUARD AI • AI-assisted fire and smoke monitoring • "
    "Always follow official emergency procedures."
)