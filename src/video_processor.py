import cv2


class VideoProcessor:

    def __init__(self, video_path):

        self.video_path = video_path

        self.cap = cv2.VideoCapture(
            video_path
        )

    def read_frame(self):

        ret, frame = self.cap.read()

        if not ret:
            return None

        return frame

    def release(self):

        self.cap.release()

    def show_frame(
        self,
        frame,
        window_name="FIREGUARD AI"
    ):

        cv2.imshow(
            window_name,
            frame
        )

    def should_stop(self):

        key = cv2.waitKey(1) & 0xFF

        return key == ord("q")

    def close(self):

        cv2.destroyAllWindows()