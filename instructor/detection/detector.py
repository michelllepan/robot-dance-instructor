import argparse

import cv2
import numpy as np

import mediapipe as mp
from mediapipe import solutions
from mediapipe.framework.formats import landmark_pb2
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class MediaPipeDetector:

    def __init__(self):
        base_options = python.BaseOptions(model_asset_path="assets/pose_landmarker.task")
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            output_segmentation_masks=True)
        self.detector = vision.PoseLandmarker.create_from_options(options)

    def run_detection(self, image):
        image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        detection_result = self.detector.detect(image)
        return detection_result
    
    def draw_landmarks_on_image(self, image, detection_result):
        if not detection_result.pose_landmarks:
            return image

        pose_landmarks = detection_result.pose_landmarks[0]
        annotated_image = np.copy(image)

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
    
    def parse_landmarks(self, detection_result):
        if not detection_result.pose_landmarks:
            return {}
        
        pose_landmarks = detection_result.pose_landmarks[0]

        def landmark_to_vec(landmark):
            return np.array([landmark.x, landmark.y, landmark.z])
        
        nose = landmark_to_vec(pose_landmarks[0])

        # LEFT
        left_pinky = landmark_to_vec(pose_landmarks[17])
        left_index = landmark_to_vec(pose_landmarks[19])
        left_thumb = landmark_to_vec(pose_landmarks[21])
        left_hand = np.mean((left_pinky, left_index, left_thumb), axis=0)

        left_elbow = landmark_to_vec(pose_landmarks[13])
        left_shoulder = landmark_to_vec(pose_landmarks[11])
        left_hip = landmark_to_vec(pose_landmarks[23])

        # RIGHT
        right_pinky = landmark_to_vec(pose_landmarks[18])
        right_index = landmark_to_vec(pose_landmarks[20])
        right_thumb = landmark_to_vec(pose_landmarks[22])
        right_hand = np.mean((right_pinky, right_index, right_thumb), axis=0)

        right_elbow = landmark_to_vec(pose_landmarks[14])
        right_shoulder = landmark_to_vec(pose_landmarks[12])
        right_hip = landmark_to_vec(pose_landmarks[24])

        # CENTER
        center_hips = np.mean((left_hip, right_hip), axis=0)

        return {
            "nose": nose,
            "left_hand": left_hand,
            "left_elbow": left_elbow,
            "left_shoulder": left_shoulder,
            "right_hand": right_hand,
            "right_elbow": right_elbow,
            "right_shoulder": right_shoulder,
            "center_hips": center_hips,
        }
