# 3D Pose Detection with Intel RealSense

Run the following command to create a conda environment with the required packages:
```
conda env create -f environment.yml
```

To run detection, run
```
python run_detection.py
```
Use the `-w` flag to write Redis outputs to a file, and the `-c` flag to specify the length of the capture (in seconds).