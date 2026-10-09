from ultralytics import YOLO


class FireDetector:

    def __init__(self, model_path):
        self.model = YOLO(model_path)
        print("MODEL CLASS NAMES:", self.model.names)

    def detect(self, frame):

        results = self.model(
            frame,
            conf=0.10,
            verbose=False
        )

        detections = []

        for result in results:

            if result.boxes is None:
                continue

            for box in result.boxes:

                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0]
                )

                detections.append({
                    "class_id": class_id,
                    "confidence": confidence,
                    "box": (x1, y1, x2, y2)
                })

        return detections
