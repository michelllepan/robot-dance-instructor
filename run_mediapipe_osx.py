import argparse
import cv2
import mediapipe as mp
import numpy as np
from mediapipe import solutions
from mediapipe.framework.formats import landmark_pb2
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


base_options = python.BaseOptions(model_asset_path='pose_landmarker.task')
options = vision.PoseLandmarkerOptions(
    base_options=base_options,
    output_segmentation_masks=True)
detector = vision.PoseLandmarker.create_from_options(options)


def draw_landmarks_on_image(rgb_image, detection_result):
    pose_landmarks_list = detection_result.pose_landmarks
    annotated_image = np.copy(rgb_image)

    # Loop through the detected poses to visualize.
    for idx in range(len(pose_landmarks_list)):
        pose_landmarks = pose_landmarks_list[idx]

        # Draw the pose landmarks.
        pose_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
        pose_landmarks_proto.landmark.extend([
            landmark_pb2.NormalizedLandmark(x=landmark.x, y=landmark.y, z=landmark.z) for landmark in pose_landmarks
        ])
        solutions.drawing_utils.draw_landmarks(
            annotated_image,
            pose_landmarks_proto,
            solutions.pose.POSE_CONNECTIONS,
            solutions.drawing_styles.get_default_pose_landmarks_style())
    return annotated_image


def stream_landmarks(detection_result):
    pose_landmarks_list = detection_result.pose_landmarks

    def landmark_to_vec(landmark):
        return np.array([landmark.x, landmark.y, landmark.z])

    for idx in range(len(pose_landmarks_list)):
        pose_landmarks = pose_landmarks_list[idx]

        left_pinky = landmark_to_vec(pose_landmarks[17])
        left_index = landmark_to_vec(pose_landmarks[19])
        left_thumb = landmark_to_vec(pose_landmarks[21])
        left_hand = np.mean((left_pinky, left_index, left_thumb), axis=0)

        right_pinky = landmark_to_vec(pose_landmarks[18])
        right_index = landmark_to_vec(pose_landmarks[20])
        right_thumb = landmark_to_vec(pose_landmarks[22])
        right_hand = np.mean((right_pinky, right_index, right_thumb), axis=0)

        print(f"LEFT HAND:  {left_hand}")
        print(f"RIGHT HAND: {right_hand}")
        print()


def detect_keypoints(img):
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    detection_result = detector.detect(image)
    return detection_result


def process_frames(image):
    detection_result= detect_keypoints(image)
    image = draw_landmarks_on_image(image, detection_result)
    stream_landmarks(detection_result)

    cv2.namedWindow('Capture', cv2.WINDOW_AUTOSIZE)
    cv2.imshow('Capture', image)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera_id", "-c", type=int, default=0, help="camera to read from")
    args = parser.parse_args()

    vid = cv2.VideoCapture(args.camera_id) 
    while True:
        ret, frame = vid.read() 
        if not ret:
            continue

        process_frames(frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): 
            break

    vid.release() 
    cv2.destroyAllWindows() 