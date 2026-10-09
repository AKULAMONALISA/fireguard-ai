from collections import deque


class FireVerifier:

    def __init__(self, window_size=10, threshold=0.35):

        self.window_size = window_size
        self.threshold = threshold

        self.history = deque(
            maxlen=window_size
        )

    def update(self, confidence):

        self.history.append(confidence)

        valid_frames = sum(
            1
            for value in self.history
            if value >= self.threshold
        )

        persistence = (
            valid_frames / len(self.history)
        )

        # Strong and persistent fire detection
        if (
            len(self.history) >= 5
            and persistence >= 0.30
        ):
            return "VERIFIED FIRE"

        # Current frame has a possible fire
        elif confidence >= self.threshold:
            return "POSSIBLE FIRE"

        else:
            return "NO FIRE"

    def get_average_confidence(self):

        if not self.history:
            return 0.0

        return sum(self.history) / len(
            self.history
        )