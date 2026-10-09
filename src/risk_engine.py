class RiskEngine:

    def calculate(
        self,
        fire_confidence,
        fire_area,
        growth,
        verified
    ):

        score = 0

        # Fire confidence
        if fire_confidence >= 0.80:
            score += 40

        elif fire_confidence >= 0.60:
            score += 30

        elif fire_confidence >= 0.40:
            score += 15

        # Fire area
        if fire_area >= 50000:
            score += 25

        elif fire_area >= 20000:
            score += 15

        elif fire_area > 0:
            score += 5

        # Fire growth
        if growth > 10000:
            score += 20

        elif growth > 0:
            score += 10

        # Verification
        if verified == "VERIFIED FIRE":
            score += 15

        # Risk level
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