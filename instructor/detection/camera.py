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
