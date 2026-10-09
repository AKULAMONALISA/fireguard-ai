
import sys
from pathlib import Path
from datetime import datetime

import cv2
import pandas as pd
import streamlit as st

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
except ImportError as exc:
    send_email_alert = None
    print(f"Email module import failed: {exc}")

MODELS_DIR = ROOT / "models"
VIDEOS_DIR = ROOT / "videos"
RESULTS_DIR = ROOT / "results"
MODEL_PATH = MODELS_DIR / "best.pt"
DEFAULT_VIDEO_PATH = VIDEOS_DIR / "fire.mp4"
ANNOTATED_VIDEO_PATH = RESULTS_DIR / "fireguard_annotated.mp4"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(
    page_title="FIREGUARD AI",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
    "fg_latitude": 13.6288,
    "fg_longitude": 79.4192,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

st.markdown("""
<style>
.stApp {background:#f3f6fb;color:#17263c}
[data-testid="stHeader"] {background:#f3f6fb}
section.main > div.block-container {
    max-width:1500px;
    padding:1.5rem 2rem 3rem
}
.hero {
    background:linear-gradient(115deg,#14243a,#244b76,#9f2530);
    border-radius:20px;
    padding:30px 34px;
    margin-bottom:22px;
    box-shadow:0 10px 28px rgba(20,36,58,.12)
}
.hero * {color:white!important}
.hero .eyebrow {
    color:#fecaca!important;
    font-size:12px;
    font-weight:800;
    letter-spacing:3px
}
.hero h1 {font-size:40px!important;margin:10px 0!important}
.hero p {color:#e1eafa!important;font-size:16px}
.kicker {
    color:#2457d6;
    font-size:12px;
    font-weight:800;
    letter-spacing:1.8px;
    margin:18px 0 6px
}
div[data-testid="stMetric"] {
    background:white;
    border:1px solid #dce4ee;
    border-radius:15px;
    padding:16px;
    box-shadow:0 3px 12px rgba(20,36,58,.04)
}
[data-testid="stSidebar"] {
    background:white;
    border-right:1px solid #dce4ee
}
div.stButton>button,div.stDownloadButton>button {
    border-radius:10px;
    min-height:42px;
    font-weight:700
}
div.stButton>button[kind="primary"] {
    background:#dc2626;
    border-color:#dc2626;
    color:white
}
hr {border-color:#dce4ee}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<div class="eyebrow">WILDFIRE INTELLIGENCE PLATFORM</div>
<h1>🔥 FIREGUARD AI</h1>
<p>Detect early. Verify intelligently. Understand risk.</p>
<p>AI Vision • Temporal Verification • Geospatial Awareness • Evidence Analytics</p>
</div>
""", unsafe_allow_html=True)


# ------------------------------ Sidebar ------------------------------

with st.sidebar:
    st.markdown("## 🚁 Mission Control")
    st.caption("FIREGUARD / FIELD OPERATIONS")
    st.divider()

    st.markdown("### 📍 Incident coordinates")
    latitude = st.number_input(
        "Latitude",
        -90.0,
        90.0,
        value=float(st.session_state.fg_latitude),
        format="%.6f",
        key="fg_latitude",
    )
    longitude = st.number_input(
        "Longitude",
        -180.0,
        180.0,
        value=float(st.session_state.fg_longitude),
        format="%.6f",
        key="fg_longitude",
    )
    st.caption("Example coordinates only. Enter the actual incident location.")

    st.divider()
    st.markdown("### 🎯 Detection settings")
    confidence_threshold = st.slider(
        "Confidence threshold",
        0.10,
        0.90,
        0.35,
        0.05,
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
    st.write("🟢 Model ready" if MODEL_PATH.exists()
             else "🔴 Model file missing")
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


selected_video_name = (
    uploaded_video.name
    if uploaded_video is not None
    else DEFAULT_VIDEO_PATH.name
)

video_path_for_run = None

if uploaded_video is not None:
    suffix = Path(uploaded_video.name).suffix.lower()
    if suffix not in {".mp4", ".avi", ".mov", ".mkv", ".mpeg", ".mpg"}:
        suffix = ".mp4"

    video_path_for_run = RESULTS_DIR / f"uploaded_input{suffix}"

    try:
        video_path_for_run.write_bytes(uploaded_video.getvalue())
    except OSError as exc:
        st.error(f"Could not save uploaded video: {exc}")

elif DEFAULT_VIDEO_PATH.exists():
    video_path_for_run = DEFAULT_VIDEO_PATH


# ------------------------------ Helpers ------------------------------

def get_fire_confidence(detections):
    """Highest confidence among fire detections (class ID 0)."""
    return max(
        (
            float(d.get("confidence", 0.0))
            for d in detections
            if int(d.get("class_id", -1)) == 0
        ),
        default=0.0,
    )


def get_fire_area(detections):
    """Sum of fire bounding-box pixel areas."""
    area = 0.0

    for item in detections:
        if int(item.get("class_id", -1)) != 0:
            continue

        try:
            x1, y1, x2, y2 = map(float, item["box"])
            area += max(0.0, x2 - x1) * max(0.0, y2 - y1)
        except (KeyError, TypeError, ValueError):
            pass

    return area


def draw_detections(frame, detections):
    output = frame.copy()

    for item in detections:
        x1, y1, x2, y2 = map(int, item["box"])
        conf = float(item.get("confidence", 0.0))
        class_id = int(item.get("class_id", -1))

        if class_id == 0:
            label, color = f"FIRE {conf:.2f}", (0, 0, 230)
        elif class_id == 1:
            label, color = f"SMOKE {conf:.2f}", (0, 140, 255)
        else:
            label, color = f"OBJECT {conf:.2f}", (20, 150, 20)

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


def get_risk(engine, confidence, fire_area=0, growth=0, verified=False):
    """Calculate risk using the existing RiskEngine."""
    try:
        result = engine.calculate(
            fire_confidence=float(confidence),
            fire_area=float(fire_area),
            growth=float(growth),
            verified=verified,
        )

        if isinstance(result, dict):
            return {
                "risk_score": result.get(
                    "risk_score", result.get("score", 0)
                ),
                "risk_level": result.get(
                    "risk_level", result.get("level", "LOW")
                ),
            }

    except Exception as exc:
        st.warning(f"Risk calculation error: {exc}")

    return {"risk_score": 0, "risk_level": "LOW"}


def risk_value(data, *keys, default=None):
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


def draw_map(lat, lon):
    st.map(
        pd.DataFrame({
            "latitude": [lat],
            "longitude": [lon],
        }),
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

    for col in [
        "confidence",
        "fire_area_pixels",
        "growth_pixels",
        "risk_score",
        "latitude",
        "longitude",
        "frames_processed",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    st.markdown("### 📋 Previous analysis runs")
    st.dataframe(
        df.iloc[::-1].head(50),
        hide_index=True,
        use_container_width=True,
    )

    if "risk_score" in df.columns:
        chart = df[["risk_score"]].dropna().tail(30)

        if not chart.empty:
            st.markdown("### 📈 Risk score across saved runs")
            st.line_chart(chart, y="risk_score")

    st.download_button(
        "⬇️ DOWNLOAD INCIDENT HISTORY CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="fireguard_incident_history.csv",
        mime="text/csv",
        key="fg_history_download",
    )


# ------------------------------ Video analysis ------------------------------

if start_button:
    cap = writer = None
    frame_number = 0
    fire_frames = 0
    strongest_confidence = 0.0
    best_frame, best_detections = None, []
    growth_data = []
    latest_risk = {"risk_score": 0, "risk_level": "LOW"}
    verification_result = False
    peak_fire_area = previous_area = maximum_growth = 0.0

    try:
        if not MODEL_PATH.exists():
            st.error(f"Model file not found: {MODEL_PATH}")

        elif not video_path_for_run or not Path(video_path_for_run).exists():
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
                    status_slot, confidence_slot = st.empty(), st.empty()
                    risk_slot, telemetry_slot = st.empty(), st.empty()
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
                        fire_area = get_fire_area(detections)
                        growth = max(0.0, fire_area - previous_area)

                        peak_fire_area = max(peak_fire_area, fire_area)
                        maximum_growth = max(maximum_growth, growth)
                        previous_area = fire_area

                        growth_data.append({
                            "frame": frame_number,
                            "confidence": fire_conf,
                            "fire_area_pixels": fire_area,
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
                            fire_area=fire_area,
                            growth=growth,
                            verified=verification_result,
                        )

                        annotated = draw_detections(frame, detections)

                        if writer is not None:
                            writer.write(annotated)

                        if frame_number % 3 == 0 or frame_number == 1:
                            frame_display.image(
                                cv2.cvtColor(
                                    annotated, cv2.COLOR_BGR2RGB
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

                        risk_slot.metric(
                            "RISK LEVEL",
                            str(
                                risk_value(
                                    latest_risk,
                                    "risk_level",
                                    "level",
                                    default="LOW",
                                )
                            ).upper(),
                        )

                        telemetry_slot.caption(
                            f"Frames processed: {frame_number} | "
                            f"Fire detections: {fire_frames} | "
                            f"Current fire-box area: {fire_area:,.0f} pixels"
                        )

                        verification_slot.write(
                            f"Verification result: {verification_result}"
                        )

                    progress.progress(1.0)

                    if writer is not None:
                        writer.release()
                        writer = None

                    cap.release()
                    cap = None

                    photo_bytes = None

                    if best_frame is not None:
                        evidence_frame = draw_detections(
                            best_frame, best_detections
                        )
                        ok_jpg, encoded = cv2.imencode(
                            ".jpg", evidence_frame
                        )

                        if ok_jpg:
                            photo_bytes = encoded.tobytes()

                    risk_level = str(
                        risk_value(
                            latest_risk,
                            "risk_level",
                            "level",
                            default="LOW",
                        )
                    ).upper()

                    try:
                        risk_score = float(
                            risk_value(
                                latest_risk,
                                "risk_score",
                                "score",
                                default=0,
                            )
                        )
                    except (TypeError, ValueError):
                        risk_score = 0.0

                    # Preserve the existing verifier's output rather than
                    # assuming it always returns a particular string.
                    verification_text = str(verification_result).upper()
                    verified_fire = (
                        verification_result is True
                        or verification_text == "VERIFIED FIRE"
                    )

                    fire_confirmed = (
                        strongest_confidence >= confidence_threshold
                        and verified_fire
                    )

                    if (
                        fire_confirmed
                        or risk_level in {"HIGH", "CRITICAL", "SEVERE"}
                    ):
                        final_status = "FIRE ALERT"
                    elif strongest_confidence > 0:
                        final_status = "POSSIBLE FIRE — REVIEW"
                    else:
                        final_status = "NO FIRE DETECTED"

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
Peak fire bounding-box area: {peak_fire_area:.0f} pixels
Maximum frame-to-frame area increase: {maximum_growth:.0f} pixels
Risk level: {risk_level}
Risk score: {risk_score:.2f}
Latitude: {latitude:.6f}
Longitude: {longitude:.6f}

Note: AI-assisted screening only. Bounding-box area is a pixel measurement,
not physical fire size. Review evidence and follow official emergency procedures.
""".strip()

                    st.session_state.fg_report = report

                    try:
                        save_incident(
                            status=final_status,
                            confidence=strongest_confidence,
                            area=peak_fire_area,
                            growth=maximum_growth,
                            trend=(
                                "increasing"
                                if maximum_growth > 0
                                else "stable"
                            ),
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

                    # Send one alert after the video analysis is complete.
                    st.session_state.fg_email_notice = None

                    if final_status == "FIRE ALERT":
                        if send_email_alert is None:
                            st.session_state.fg_email_notice = (
                                "Email module could not be imported. "
                                "Check src/email_alert.py."
                            )
                        else:
                            try:
                                email_result = send_email_alert(
                                    status=final_status,
                                    confidence=strongest_confidence,
                                    risk_level=risk_level,
                                    risk_score=risk_score,
                                    latitude=latitude,
                                    longitude=longitude,
                                    timestamp=datetime.now().strftime(
                                        "%Y-%m-%d %H:%M:%S"
                                    ),
                                )

                                if (
                                    isinstance(email_result, tuple)
                                    and len(email_result) == 2
                                ):
                                    email_success, email_message = email_result
                                else:
                                    email_success = bool(email_result)
                                    email_message = str(email_result)

                                st.session_state.fg_email_notice = (
                                    str(email_message)
                                )

                                if email_success:
                                    st.success(
                                        "Email alert sent successfully."
                                    )
                                else:
                                    st.warning(
                                        f"Email alert not sent: {email_message}"
                                    )

                            except Exception as exc:
                                st.session_state.fg_email_notice = (
                                    "Email alert failed: "
                                    f"{type(exc).__name__}: {exc}"
                                )

                    status_slot.success(
                        f"Analysis finished: {final_status}"
                    )
                    st.success(
                        "Video analysis finished. Open other sections "
                        "using the sidebar."
                    )

    except Exception as exc:
        st.error(f"Analysis could not finish: {exc}")
        st.info(
            "Check that detector, tracker, verifier and risk engine "
            "modules are configured correctly."
        )

    finally:
        if cap is not None:
            cap.release()
        if writer is not None:
            writer.release()


# ------------------------------ Dashboard pages ------------------------------

if page_choice == "Overview":
    st.markdown(
        '<div class="kicker">01 / MISSION OVERVIEW</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("FIRE STATUS", st.session_state.fg_status)
    c2.metric(
        "CONFIDENCE",
        (
            f"{st.session_state.fg_confidence * 100:.1f}%"
            if st.session_state.fg_report
            else "—"
        ),
    )
    c3.metric(
        "FRAMES PROCESSED",
        st.session_state.fg_frames or "—",
    )
    c4.metric(
        "RISK LEVEL",
        st.session_state.fg_risk_level,
        (
            f"Score: {st.session_state.fg_risk_score:.1f}"
            if st.session_state.fg_report
            else None
        ),
    )

    st.divider()
    left, right = st.columns([1.5, 1])

    with left:
        st.markdown("### 🎥 Latest analysis")

        if (
            st.session_state.fg_video
            and Path(st.session_state.fg_video).exists()
        ):
            st.video(st.session_state.fg_video)

        elif (
            st.session_state.fg_original
            and Path(st.session_state.fg_original).exists()
        ):
            st.video(st.session_state.fg_original)

        else:
            st.info("Run an analysis to view the video here.")

    with right:
        st.markdown("### 📡 Incident location")
        st.write(f"Latitude: {latitude:.6f}")
        st.write(f"Longitude: {longitude:.6f}")
        draw_map(latitude, longitude)
        st.caption(
            "Manually entered coordinates; not extracted from the video."
        )

    if st.session_state.fg_email_notice:
        st.info(st.session_state.fg_email_notice)

    st.divider()
    st.markdown("### ⚡ Dashboard sections")
    st.caption(
        "Use the sidebar to open Incident Report, Evidence, "
        "Growth Analytics, or Incident History."
    )


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
                file_name=(
                    st.session_state.fg_original_name
                    or "fireguard_input_video.mp4"
                ),
                mime="video/mp4",
                key="fg_original_download",
            )


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

        st.markdown("### Fire bounding-box area per frame")
        st.line_chart(
            growth_df,
            x="frame",
            y="fire_area_pixels",
            use_container_width=True,
        )

        st.caption(
            "Box area is measured in pixels, not physical fire size."
        )
        st.markdown("### Recent frame results")
        st.dataframe(
            growth_df.tail(20),
            hide_index=True,
            use_container_width=True,
        )

    else:
        st.info("Run an analysis to generate the graph.")


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


st.divider()
st.caption(
    "FIREGUARD AI • AI-assisted fire and smoke monitoring • "
    "Always follow official emergency procedures."
)
