class RiskEngine:

    def calculate(
        self,
        fire_confidence,
        fire_area=0,
        growth=0,
        verified=False
    ):
        confidence = max(0.0, min(float(fire_confidence), 1.0))

        # Confidence contributes continuously to the score.
        score = round(confidence * 100)

        # Additional evidence increases the score.
        if fire_area >= 50000:
            score += 25
        elif fire_area >= 20000:
            score += 15
        elif fire_area > 0:
            score += 5

        if growth > 10000:
            score += 20
        elif growth > 0:
            score += 10

        if verified == "VERIFIED FIRE" or verified is True:
            score += 15

        score = min(score, 100)

        if score >= 70:
            level = "HIGH"
        elif score >= 40:
            level = "MEDIUM"
        else:
            level = "LOW"

        return {
            "score": score,
            "level": level
        }