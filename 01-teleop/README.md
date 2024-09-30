# 01-teleop

There are two programs: simviz and controller.  Simviz is the simulation and visualization, and the controller controls the robots. To switch to the real robot, change the controller flag 
```
const bool flag_simulation = true;
```
to 
```
const bool flag_simulation = false;
```
in controller.cpp.  The torque driver should be running before execution of the controller.