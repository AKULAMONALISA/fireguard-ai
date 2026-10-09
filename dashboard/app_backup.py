import sys
from pathlib import Path
from datetime import datetime

import cv2
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.incident_history import load_incidents, save_incident
from src.email_alert import send_email_alert

MODEL_PATH = ROOT / "models" / "best.pt"
VIDEO_PATH = ROOT / "videos" / "fire.mp4"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

ANNOTATED_VIDEO_PATH = RESULTS_DIR / "fireguard_evidence.mp4"

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="FIREGUARD AI | Command Center",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =====================================================
# SESSION STATE
# =====================================================

DEFAULT_STATE = {
    "fireguard_report": "",
    "fireguard_photo": None,
    "fireguard_annotated_video": None,
    "fireguard_original_video": None,
    "fireguard_growth": [],
    "fireguard_email_notice": None,
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value

# =====================================================
# PREMIUM LIGHT THEME
# =====================================================

st.markdown("""
<style>
.stApp {
    background: #f3f6fb;
    color: #17263c;
}
[data-testid="stHeader"] {
    background: #f3f6fb;
}
section.main > div.block-container {
    max-width: 100% !important;
    width: 100% !important;
    padding: 1.5rem 2.2rem 3rem !important;
}
h1, h2, h3, p, label {
    color: #17263c;
}
h1 { font-size: 2.5rem !important; }
h2 { font-size: 1.65rem !important; }
h3 { font-size: 1.2rem !important; }

.hero {
    background: linear-gradient(115deg, #14243a, #244b76, #9f2530);
    border-radius: 20px;
    padding: 30px 34px;
    margin-bottom: 22px;
    box-shadow: 0 10px 28px rgba(20,36,58,.12);
}
.hero * { color: white !important; }
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
    padding: 20px 18px;
    box-shadow: 0 3px 12px rgba(20,36,58,.04);
}
div[data-testid="stMetricLabel"] {
    color: #64748b !important;
    font-size: 14px !important;
}
div[data-testid="stMetricValue"] {
    color: #14243a !important;
    font-size: 28px !important;
    font-weight: 800 !important;
}
[data-testid="stSidebar"] {
    background: white;
    border-right: 1px solid #dce4ee;
}
[data-testid="stSidebar"] * { color: #17263c; }
div.stButton > button,
div.stDownloadButton > button {
    border-radius: 10px;
    min-height: 44px;
    font-weight: 700;
}
div.stButton > button[kind="primary"] {
    background: #dc2626;
    border-color: #dc2626;
    color: white;
}
div.stButton > button[kind="primary"]:hover {
    background: #b91c1c;
    border-color: #b91c1c;
}
hr { border-color: #dce4ee; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# HEADER
# =====================================================

st.markdown("""
<div class="hero">
    <div class="eyebrow">WILDFIRE INTELLIGENCE PLATFORM</div>
    <h1>🔥 FIREGUARD AI</h1>
    <p>Detect early. Verify intelligently. Understand risk.</p>
    <p>AI Vision • Temporal Verification • Geospatial Awareness
    • Evidence Analytics</p>
</div>
""", unsafe_allow_html=True)

# =====================================================
# SIDEBAR
# =====================================================

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
    )

    longitude = st.number_input(
        "Longitude",
        min_value=-180.0,
        max_value=180.0,
        value=79.4192,
        format="%.6f",
    )

    st.caption(
        "Demo coordinates by default. Enter actual incident "
        "coordinates when known."
    )

    st.divider()
    st.markdown("### 🎯 Detection settings")

    confidence_threshold = st.slider(
        "Confidence threshold",
        min_value=0.10,
        max_value=0.90,
        value=0.35,
        step=0.05,
    )

    st.divider()
    st.markdown("### System readiness")

    st.write(
        "🟢 Model ready" if MODEL_PATH.exists()
        else "🔴 Model file missing"
    )
    st.write(
        "🟢 Video ready" if VIDEO_PATH.exists()
        else "🔴 Video file missing"
    )

    start_button = st.button(
        "🚨 START FIRE ANALYSIS",
        type="primary",
        use_container_width=True,
    )

# =====================================================
# METRICS
# =====================================================

st.markdown(
    '<div class="kicker">01 / MISSION OVERVIEW</div>',
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)

status_metric = c1.empty()
confidence_metric = c2.empty()
area_metric = c3.empty()
risk_metric = c4.empty()

status_metric.metric("FIRE STATUS", "STANDBY")
confidence_metric.metric("CONFIDENCE", "—")
area_metric.metric("FIRE AREA", "—")
risk_metric.metric("RISK SCORE", "—")

st.divider()

# =====================================================
# VIDEO AND TELEMETRY
# =====================================================

video_col, data_col = st.columns([1.6, 1])

with video_col:
    st.markdown(
        '<div class="kicker">02 / AI VISION</div>',
        unsafe_allow_html=True,
    )
    st.subheader("🎥 Detection feed")
    video_slot = st.empty()
    progress_slot = st.empty()

with data_col:
    st.markdown(
        '<div class="kicker">03 / LIVE INTELLIGENCE</div>',
        unsafe_allow_html=True,
    )
    st.subheader("📊 Incident telemetry")
    telemetry_slot = st.empty()

    st.subheader("⏱️ Temporal verification")
    verification_slot = st.empty()

    st.subheader("🚨 Emergency response")
    alert_slot = st.empty()

st.divider()

# =====================================================
# GPS MAP
# =====================================================

st.markdown(
    '<div class="kicker">04 / GEOINT</div>',
    unsafe_allow_html=True,
)
st.subheader("🗺️ Incident location & risk map")

map_col, location_col = st.columns([1.7, 1])

with map_col:
    map_slot = st.empty()

with location_col:
    st.markdown("### 📡 Location details")
    st.metric("Latitude", f"{latitude:.6f}")
    st.metric("Longitude", f"{longitude:.6f}")
    st.info(
        "Coordinates are manually entered. They are not "
        "automatically extracted from the video."
    )


def update_map(lat, lon):
    points = pd.DataFrame({
        "latitude": [lat],
        "longitude": [lon],
    })
    map_slot.map(
        points,
        latitude="latitude",
        longitude="longitude",
        size=220,
        color="#dc2626",
        zoom=10,
    )


update_map(latitude, longitude)

st.divider()

# =====================================================
# EMAIL NOTICE — PERSISTS AFTER RERUN
# =====================================================

if st.session_state.fireguard_email_notice:
    notice = st.session_state.fireguard_email_notice

    if notice["kind"] == "success":
        st.success("📧 " + notice["message"])
    elif notice["kind"] == "warning":
        st.warning("📧 " + notice["message"])
    else:
        st.info("📧 " + notice["message"])

# =====================================================
# INCIDENT REPORT AND EVIDENCE
# =====================================================

st.markdown(
    '<div class="kicker">05 / MISSION RECORDS</div>',
    unsafe_allow_html=True,
)
st.subheader("📄 AI incident report")

if st.session_state.fireguard_report:
    st.success("Incident report is ready.")

    with st.expander("👁️ Preview incident report"):
        st.text(st.session_state.fireguard_report)

    st.download_button(
        "⬇️ DOWNLOAD INCIDENT REPORT",
        data=st.session_state.fireguard_report,
        file_name="fireguard_incident_report.txt",
        mime="text/plain",
        key="download_report",
    )

    st.markdown("---")
    st.subheader("🖼️ Incident evidence")

    photo_col, evidence_video_col = st.columns(2)

    with photo_col:
        st.markdown("### 📸 Strongest detection photo")
        photo = st.session_state.fireguard_photo

        if photo:
            st.image(
                photo,
                caption="Strongest AI detection frame",
                use_container_width=True,
            )
            st.download_button(
                "⬇️ DOWNLOAD DETECTION PHOTO",
                data=photo,
                file_name="fireguard_fire_evidence.jpg",
                mime="image/jpeg",
                key="download_fire_photo",
            )
        else:
            st.info("No detection photo was saved.")

    with evidence_video_col:
        st.markdown("### 🎬 Annotated evidence video")
        evidence_video = st.session_state.fireguard_annotated_video

        if evidence_video:
            st.video(evidence_video)
            st.download_button(
                "⬇️ DOWNLOAD ANNOTATED VIDEO",
                data=evidence_video,
                file_name="fireguard_evidence.mp4",
                mime="video/mp4",
                key="download_annotated_video",
            )
        else:
            st.info("No annotated video was saved.")

    original_video = st.session_state.fireguard_original_video
    if original_video:
        st.markdown("### 🎥 Original input video")
        st.download_button(
            "⬇️ DOWNLOAD ORIGINAL VIDEO",
            data=original_video,
            file_name=VIDEO_PATH.name,
            mime="video/mp4",
            key="download_original_video",
        )

st.divider()

# =====================================================
# FIRE GROWTH ANALYTICS
# =====================================================

st.markdown(
    '<div class="kicker">06 / FIRE DYNAMICS</div>',
    unsafe_allow_html=True,
)
st.subheader("📈 Fire Growth Analytics")

saved_growth = st.session_state.fireguard_growth

if saved_growth:
    growth_df = pd.DataFrame(saved_growth)

    st.line_chart(
        growth_df,
        x="Frame",
        y="Fire Area (pixels²)",
        use_container_width=True,
    )
    st.dataframe(
        growth_df.tail(10),
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info("Run the analysis to generate the fire growth graph.")

st.divider()

# =====================================================
# INCIDENT HISTORY
# =====================================================

st.markdown(
    '<div class="kicker">07 / HISTORICAL INTELLIGENCE</div>',
    unsafe_allow_html=True,
)
st.subheader("🗂️ Incident History")
st.caption(
    "Completed analysis runs are stored in results/incident_history.csv. "
    "Coordinates are the values entered in Mission Control."
)

try:
    incident_records = load_incidents()
except Exception as exc:
    incident_records = []
    st.error(f"Could not load incident history: {exc}")

if incident_records:
    incidents_df = pd.DataFrame(incident_records)

    for column in [
        "confidence",
        "fire_area_pixels",
        "growth_pixels",
        "risk_score",
        "latitude",
        "longitude",
        "frames_processed",
    ]:
        if column in incidents_df.columns:
            incidents_df[column] = pd.to_numeric(
                incidents_df[column], errors="coerce"
            )

    st.markdown("### 📋 Previous analysis runs")
    st.dataframe(
        incidents_df.iloc[::-1].head(20),
        hide_index=True,
        use_container_width=True,
    )

    if {"timestamp", "risk_score"}.issubset(incidents_df.columns):
        chart_df = incidents_df[["timestamp", "risk_score"]].copy()
        chart_df = chart_df.dropna(subset=["risk_score"])

        if not chart_df.empty:
            st.markdown("### 📈 Risk score across saved runs")
            chart_df = chart_df.tail(30).set_index("timestamp")
            st.line_chart(
                chart_df,
                y="risk_score",
                use_container_width=True,
            )

    st.download_button(
        "⬇️ DOWNLOAD INCIDENT HISTORY CSV",
        data=incidents_df.to_csv(index=False).encode("utf-8"),
        file_name="fireguard_incident_history.csv",
        mime="text/csv",
        key="download_incident_history",
    )
else:
    st.info(
        "No saved incidents yet. Run an analysis to create the first history record."
    )

# =====================================================
# DETECTION HELPERS
# =====================================================

def get_fire_confidence(detections):
    return max(
        (
            item["confidence"]
            for item in detections
            if item["class_id"] == 0
        ),
        default=0.0,
    )


def draw_detections(frame, detections):
    output = frame.copy()

    for item in detections:
        x1, y1, x2, y2 = item["box"]
        conf = item["confidence"]
        cls = item["class_id"]

        if cls == 0:
            label, color = f"FIRE {conf:.2f}", (0, 0, 230)
        elif cls == 1:
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


# =====================================================
# RUN ANALYSIS
# =====================================================

if start_button:

    if not MODEL_PATH.exists():
        st.error(f"Model not found: {MODEL_PATH}")
        st.stop()

    if not VIDEO_PATH.exists():
        st.error(f"Video not found: {VIDEO_PATH}")
        st.stop()

    try:
        from src.detector import FireDetector
        from src.tracker import FireTracker
        from src.verifier import FireVerifier
        from src.risk_engine import RiskEngine

        detector = FireDetector(str(MODEL_PATH))
        tracker = FireTracker()
        verifier = FireVerifier(
            window_size=10,
            threshold=confidence_threshold,
        )
        risk_engine = RiskEngine()

    except Exception as exc:
        st.error(f"AI initialization failed: {exc}")
        st.stop()

    try:
        original_video_bytes = VIDEO_PATH.read_bytes()
    except OSError as exc:
        st.error(f"Cannot read original video: {exc}")
        st.stop()

    cap = cv2.VideoCapture(str(VIDEO_PATH))

    if not cap.isOpened():
        st.error("Unable to open the video file.")
        st.stop()

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    if not fps or fps <= 0:
        fps = 20.0

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    writer = cv2.VideoWriter(
        str(ANNOTATED_VIDEO_PATH),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    if not writer.isOpened():
        writer.release()
        cap.release()
        st.error(
            "Could not create evidence video. Check the results folder "
            "and available video codecs."
        )
        st.stop()

    progress_bar = st.progress(0)

    frames_processed = 0
    best_conf = 0.0
    best_frame = None
    best_detections = []
    best_area = 0
    best_growth = 0
    best_trend = "STABLE"

    saw_verified = False
    saw_possible = False
    max_risk = 0
    max_risk_level = "LOW"
    growth_history = []
    processing_error = None

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frames_processed += 1
            detections = detector.detect(frame)

            conf = get_fire_confidence(detections)
            status = verifier.update(conf)

            if status == "VERIFIED FIRE":
                saw_verified = True
            elif status == "POSSIBLE FIRE":
                saw_possible = True

            tracking = tracker.update(detections)

            risk = risk_engine.calculate(
                conf,
                tracking["area"],
                tracking["growth"],
                status,
            )

            if risk["score"] > max_risk:
                max_risk = risk["score"]
                max_risk_level = risk["level"]

            growth_history.append({
                "Frame": frames_processed,
                "Fire Area (pixels²)": tracking["area"],
                "Growth": tracking["growth"],
                "Trend": tracking["trend"],
            })

            if conf > best_conf:
                best_conf = conf
                best_frame = frame.copy()
                best_detections = detections.copy()
                best_area = tracking["area"]
                best_growth = tracking["growth"]
                best_trend = tracking["trend"]

            annotated = draw_detections(frame, detections)

            cv2.putText(
                annotated,
                f"STATUS: {status}",
                (18, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 230),
                2,
            )

            writer.write(annotated)

            video_slot.image(
                cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB),
                channels="RGB",
                use_container_width=True,
            )

            status_metric.metric("CURRENT STATUS", status)
            confidence_metric.metric("CONFIDENCE", f"{conf:.2f}")
            area_metric.metric("FIRE AREA", f"{tracking['area']:,} px²")
            risk_metric.metric(
                "RISK",
                f"{risk['level']} · {risk['score']}/100",
            )

            telemetry_slot.dataframe(
                pd.DataFrame([
                    {"Metric": "Fire confidence", "Value": f"{conf:.2f}"},
                    {"Metric": "Fire area (pixels²)", "Value": tracking["area"]},
                    {"Metric": "Area growth", "Value": tracking["growth"]},
                    {"Metric": "Trend", "Value": tracking["trend"]},
                    {"Metric": "Risk level", "Value": risk["level"]},
                    {"Metric": "Risk score", "Value": risk["score"]},
                    {"Metric": "Frames processed", "Value": frames_processed},
                ]),
                hide_index=True,
                use_container_width=True,
            )

            history = list(verifier.history)
            positives = sum(
                value >= confidence_threshold for value in history
            )
            persistence = (
                positives * 100 / len(history) if history else 0
            )

            verification_slot.dataframe(
                pd.DataFrame([
                    {"Metric": "Window frames", "Value": len(history)},
                    {"Metric": "Positive frames", "Value": positives},
                    {"Metric": "Persistence", "Value": f"{persistence:.0f}%"},
                    {"Metric": "Decision", "Value": status},
                ]),
                hide_index=True,
                use_container_width=True,
            )

            progress_bar.progress(
                min(frames_processed / max(total_frames, 1), 1.0)
            )
            progress_slot.caption(
                f"Analyzed {frames_processed} / {total_frames} frames"
            )

    except Exception as exc:
        processing_error = str(exc)

    finally:
        cap.release()
        writer.release()

    if processing_error:
        st.error(f"Video analysis failed: {processing_error}")

    if frames_processed == 0:
        st.error("No frames could be read from the video.")
        st.stop()

    # -------------------------------------------------
    # FINAL DECISION
    # -------------------------------------------------

    if saw_verified:
        final_status = "VERIFIED FIRE"
    elif best_conf >= confidence_threshold or saw_possible:
        final_status = "POSSIBLE FIRE"
    else:
        final_status = "NO FIRE"

    history = list(verifier.history)
    positives = sum(
        value >= confidence_threshold for value in history
    )
    persistence = (
        positives * 100 / len(history) if history else 0
    )

    final_risk = risk_engine.calculate(
        best_conf,
        best_area,
        best_growth,
        final_status,
    )

    status_metric.metric("FINAL STATUS", final_status)
    confidence_metric.metric("MAX CONFIDENCE", f"{best_conf:.2f}")
    area_metric.metric("MAX FIRE AREA", f"{best_area:,} px²")
    risk_metric.metric(
        "FINAL RISK",
        f"{final_risk['level']} · {final_risk['score']}/100",
    )

    photo_bytes = None

    if best_frame is not None:
        strongest = draw_detections(best_frame, best_detections)

        cv2.putText(
            strongest,
            f"FINAL: {final_status}",
            (18, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 230),
            2,
        )

        video_slot.image(
            cv2.cvtColor(strongest, cv2.COLOR_BGR2RGB),
            use_container_width=True,
            caption="Strongest detection frame",
        )

        image_ok, image_buffer = cv2.imencode(".jpg", strongest)
        if image_ok:
            photo_bytes = image_buffer.tobytes()
    else:
        video_slot.info("No detections were recorded.")

    if final_status == "VERIFIED FIRE":
        alert_slot.error(
            "🚨 VERIFIED FIRE — Human review and emergency assessment recommended."
        )
    elif final_status == "POSSIBLE FIRE":
        alert_slot.warning(
            "⚠️ POSSIBLE FIRE — Review footage before confirming an incident."
        )
    else:
        alert_slot.success(
            "✅ NO SIGNIFICANT FIRE CONFIRMED IN THIS VIDEO."
        )

    update_map(latitude, longitude)

    # -------------------------------------------------
    # SAVE EVIDENCE
    # -------------------------------------------------

    st.session_state.fireguard_photo = photo_bytes
    st.session_state.fireguard_original_video = original_video_bytes

    annotated_video_bytes = None

    if (
        ANNOTATED_VIDEO_PATH.exists()
        and ANNOTATED_VIDEO_PATH.stat().st_size > 0
    ):
        annotated_video_bytes = ANNOTATED_VIDEO_PATH.read_bytes()

    st.session_state.fireguard_annotated_video = annotated_video_bytes
    st.session_state.fireguard_growth = growth_history

    # -------------------------------------------------
    # INCIDENT REPORT
    # -------------------------------------------------

    report = f"""
FIREGUARD AI — INCIDENT REPORT
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

FINAL STATUS: {final_status}

Maximum fire confidence: {best_conf:.2f}
Maximum fire area: {best_area} image pixels squared
Area growth: {best_growth}
Area trend: {best_trend}

TEMPORAL VERIFICATION
Positive frames in final window: {positives}
Window size: {len(history)}
Persistence: {persistence:.1f}%

RISK ASSESSMENT
Risk level: {final_risk['level']}
Risk score: {final_risk['score']}/100
Maximum observed risk: {max_risk_level} ({max_risk}/100)

VIDEO ANALYSIS
Input video: {VIDEO_PATH.name}
Frames processed: {frames_processed}
Detection photo available: {"Yes" if photo_bytes else "No"}
Annotated video available: {"Yes" if annotated_video_bytes else "No"}
Original video available: {"Yes" if original_video_bytes else "No"}

GROWTH ANALYTICS
Frames with area measurements: {len(growth_history)}
Final recorded trend: {growth_history[-1]['Trend'] if growth_history else "N/A"}

MAP COORDINATES ENTERED
Latitude: {latitude:.6f}
Longitude: {longitude:.6f}

LIMITATIONS
Coordinates are manually entered, not extracted from video.
Fire area is measured in image pixels, not physical units.
Risk scores are prototype estimates, not official classifications.
AI output requires human review before emergency decisions.

RECOMMENDATION
{"Prompt human review and emergency assessment." if final_status == "VERIFIED FIRE" else "Verify footage before treating this as a confirmed incident." if final_status == "POSSIBLE FIRE" else "No significant fire was confirmed by this prototype."}
"""

    st.session_state.fireguard_report = report

    # -------------------------------------------------
    # SAVE INCIDENT HISTORY
    # -------------------------------------------------

    try:
        save_incident(
            status=final_status,
            confidence=best_conf,
            area=best_area,
            growth=best_growth,
            trend=best_trend,
            risk_level=final_risk["level"],
            risk_score=final_risk["score"],
            latitude=latitude,
            longitude=longitude,
            frames_processed=frames_processed,
        )
    except Exception as exc:
        st.warning(
            f"Analysis finished, but incident history could not be saved: {exc}"
        )

    # -------------------------------------------------
    # EMAIL ALERT — PERSISTENT MESSAGE
    # -------------------------------------------------

    should_send_email = (
        final_status == "VERIFIED FIRE"
        or str(final_risk["level"]).upper() == "HIGH"
    )

    if should_send_email:
        try:
            email_ok, email_message = send_email_alert(
                status=final_status,
                confidence=best_conf,
                risk_level=final_risk["level"],
                risk_score=final_risk["score"],
                latitude=latitude,
                longitude=longitude,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )

            if email_ok:
                st.session_state.fireguard_email_notice = {
                    "kind": "success",
                    "message": email_message,
                }
            else:
                st.session_state.fireguard_email_notice = {
                    "kind": "warning",
                    "message": "Email alert was not sent: " + str(email_message),
                }

        except Exception as exc:
            st.session_state.fireguard_email_notice = {
                "kind": "warning",
                "message": f"Email alert error: {exc}",
            }
    else:
        st.session_state.fireguard_email_notice = {
            "kind": "info",
            "message": (
                "No email sent: this demo result did not meet the "
                "HIGH-risk / VERIFIED FIRE email condition."
            ),
        }

    st.success(
        f"✅ FIREGUARD AI analysis completed — "
        f"{frames_processed} frames processed."
    )

    st.rerun()

# =====================================================
# FOOTER
# =====================================================

st.divider()
st.markdown("""
<div style="text-align:center;color:#64748b;padding:10px">
<b>FIREGUARD AI</b> · Wildfire Intelligence Prototype<br>
For research and demonstration. Not a replacement for official
fire alarms or emergency services.
</div>
""", unsafe_allow_html=True)