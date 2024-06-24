import argparse
import cv2
import mediapipe as mp
import numpy as np
import pyrealsense2 as rs
from mediapipe import solutions
from mediapipe.framework.formats import landmark_pb2
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


base_options = python.BaseOptions(model_asset_path='pose_landmarker.task')
options = vision.PoseLandmarkerOptions(
    base_options=base_options,
    output_segmentation_masks=True)
detector = vision.PoseLandmarker.create_from_options(options)


def setup_pipeline():
    # Configure depth and color streams
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    # Start streaming
    pipeline.start(config)
    return pipeline


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

        print(f"LEFT HAND: {left_hand}")
        print(f"RIGHT HAND: {right_hand}")


def detect_keypoints(img):
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    detection_result = detector.detect(image)
    return detection_result


def process_frames(frames):
    depth_frame = frames.get_depth_frame()
    color_frame = frames.get_color_frame()
    if not depth_frame or not color_frame:
        return

    # Convert images to numpy arrays
    depth_image = np.asanyarray(depth_frame.get_data())
    color_image = np.asanyarray(color_frame.get_data())

    # Detect keypoints
    detection_result= detect_keypoints(color_image)
    color_image = draw_landmarks_on_image(color_image, detection_result)
    stream_landmarks(detection_result)

    # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
    depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

    depth_colormap_dim = depth_colormap.shape
    color_colormap_dim = color_image.shape

    # If depth and color resolutions are different, resize color image to match depth image for display
    if depth_colormap_dim != color_colormap_dim:
        resized_color_image = cv2.resize(color_image, dsize=(depth_colormap_dim[1], depth_colormap_dim[0]), interpolation=cv2.INTER_AREA)
        images = np.hstack((resized_color_image, depth_colormap))
    else:
        images = np.hstack((color_image, depth_colormap))

    # Show images
    cv2.namedWindow('RealSense', cv2.WINDOW_AUTOSIZE)
    cv2.imshow('RealSense', images)
    cv2.waitKey(1)


if __name__ == "__main__":
    pipeline = setup_pipeline()
    try:
        while True:
            frames = pipeline.wait_for_frames()
            process_frames(frames)
    finally:
        pipeline.stop()