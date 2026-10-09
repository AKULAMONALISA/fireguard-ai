```python
# Save incident history
try:
    save_incident(
        status=final_status,
        confidence=strongest_confidence,
        area=0,
        growth=0,
        trend="unknown",
        risk_level=risk_level,
        risk_score=risk_score,
        latitude=0.0,
        longitude=0.0,
        frames_processed=frame_number,
    )
except Exception as exc:
    st.warning(
        f"Analysis finished, but incident history could not be saved: {exc}"
    )
```
