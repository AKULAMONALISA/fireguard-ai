class FireTracker:

    def __init__(self):
        self.previous_area = 0
        self.current_area = 0

    def calculate_area(self, box):
        x1, y1, x2, y2 = box

        width = x2 - x1
        height = y2 - y1

        area = width * height

        return area

    def update(self, detections):

        total_fire_area = 0

        for detection in detections:

            if detection["class_id"] == 0:
                area = self.calculate_area(
                    detection["box"]
                )

                total_fire_area += area

        self.previous_area = self.current_area
        self.current_area = total_fire_area

        growth = (
            self.current_area - self.previous_area
        )

        if growth > 0:
            trend = "INCREASING"

        elif growth < 0:
            trend = "DECREASING"

        else:
            trend = "STABLE"

        return {
            "area": self.current_area,
            "growth": growth,
            "trend": trend
        }