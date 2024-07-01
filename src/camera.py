import pyrealsense2 as rs


class RealSenseCamera:

    def __init__(self, width=1280, height=720):
        self.pipeline = rs.pipeline()
        config = rs.config()

        pipeline_wrapper = rs.pipeline_wrapper(self.pipeline)
        pipeline_profile = config.resolve(pipeline_wrapper)
        device = pipeline_profile.get_device()
        advanced_mode = rs.rs400_advanced_mode(device)
        advanced_mode.toggle_advanced_mode(True)

        config.enable_stream(rs.stream.depth, width, height, rs.format.z16, 30)
        config.enable_stream(rs.stream.color, width, height, rs.format.bgr8, 30)
        self.pipeline.start(config)

        self.frame_history = []
        self._setup_postprocessing()

    def _setup_postprocessing(self):
        self.align = rs.align(rs.stream.color)

        self.decimation_filter = rs.decimation_filter()
        self.depth_to_disparity = rs.disparity_transform(True)
        self.spatial_filter = rs.spatial_filter()
        self.temporal_filter = rs.temporal_filter()
        self.disparity_to_depth = rs.disparity_transform(False)
        self.hole_filling_filter = rs.hole_filling_filter()

    def get_frames(self):
        """
        Returns depth and color frame.
        """
        frames = self.pipeline.wait_for_frames()
        frames = self.align.process(frames)

        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        if not depth_frame or not color_frame:
            return
        
        self.frame_history.append(depth_frame)
        if len(self.frame_history) > 15:
            self.frame_history.pop(0)
        
        # apply filters according to order in
        # https://dev.intelrealsense.com/docs/post-processing-filters

        for frame in self.frame_history:
            frame = self.decimation_filter.process(frame)
            frame = self.depth_to_disparity.process(frame)
            frame = self.spatial_filter.process(frame)
            frame = self.temporal_filter.process(frame)
            frame = self.disparity_to_depth.process(frame)
            frame = self.hole_filling_filter.process(frame)
        depth_frame = frame

        return depth_frame, color_frame
        
    def __del__(self):
        self.pipeline.stop()


if __name__ == "__main__":
    import numpy as np
    import cv2

    camera = RealSenseCamera()
    while True:
        depth_frame, color_frame = camera.get_frames()

        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
        
        depth_colormap_dim = depth_colormap.shape
        color_colormap_dim = color_image.shape

        if depth_colormap_dim != color_colormap_dim:
            resized_color_image = cv2.resize(color_image, dsize=(depth_colormap_dim[1], depth_colormap_dim[0]), interpolation=cv2.INTER_AREA)
            images = np.hstack((resized_color_image, depth_colormap))
        else:
            images = np.hstack((color_image, depth_colormap))

        cv2.imshow("RealSense", images)
        if cv2.waitKey(1) & 0xFF == ord('q'): 
            break