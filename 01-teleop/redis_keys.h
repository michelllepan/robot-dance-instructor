/**
 * @file redis_keys.h
 * @author William Chong (wmchong@stanford.edu)
 * @brief 
 * @version 0.1
 * @date 2024-06-11
 * 
 * @copyright Copyright (c) 2024
 * 
 */

#pragma once 

// keys for robot information 
std::string JOINT_ANGLES_KEY = "sai2::sim::panda::sensors::q";
std::string JOINT_VELOCITIES_KEY = "sai2::sim::panda::sensors::dq";
std::string JOINT_TORQUES_COMMANDED_KEY = "sai2::sim::panda::actuators::fgc";
std::string CONTROLLER_RUNNING_KEY = "sai2::sim::panda::controller";
std::string ROBOT_HOME_POS_KEY = "sai2::panda::home_position";
std::string ROBOT_HOME_ORI_KEY = "sai2::panda::home_orientation";
std::string GRIPPER_JOINT_ANGLES_KEY = "sai2::sim::panda_gripper::sensors::q";
std::string GRIPPER_JOINT_VELOCITIES_KEY = "sai2::sim::panda_gripper::sensors::dq";
std::string EE_POS_KEY = "sai2::panda::ee_pos";
std::string EE_ORI_KEY = "sai2::panda::ee_ori";

// pose information from user input
std::string DESIRED_POS_KEY = "teleop::desired_pos";  // format of "[x, y, z]"
std::string DESIRED_ORI_KEY = "teleop::desired_ori";  // format of "[[x, y, z], [x, y, z], [x, y, z]]"
std::string REPLAY_READY_KEY = "teleop::replay_ready";