/**
 * @file controller.cpp
 * @author William Chong (wmchong@stanford.edu)
 * @brief 
 * @version 0.1
 * @date 2024-06-11
 * 
 * @copyright Copyright (c) 2024
 * 
 */

#include <Sai2Model.h>
#include "Sai2Primitives.h"
#include "redis/RedisClient.h"
#include "timer/LoopTimer.h"

#include <iostream>
#include <string>

using namespace std;
using namespace Eigen;
using namespace Sai2Primitives;

#include <signal.h>
bool runloop = false;
void sighandler(int){runloop = false;}

#include "redis_keys.h"

// States 
enum State {
	POSTURE = 0,
    CALIBRATION, 
	MOTION
};

// const bool flag_simulation = true;
const bool flag_simulation = false;

int main(int argc, char *argv[]) {
	// Location of URDF files specifying world and robot information
	static const string robot_file = "./resources/panda_arm.urdf";

	// redis keys overwrite for real robot 
	if (!flag_simulation) {
		JOINT_ANGLES_KEY = "sai2::FrankaPanda::Juliet::sensors::q";
		JOINT_VELOCITIES_KEY = "sai2::FrankaPanda::Juliet::sensors::dq";
		JOINT_TORQUES_COMMANDED_KEY = "sai2::FrankaPanda::Juliet::actuators::fgc";
		CONTROLLER_RUNNING_KEY = "sai2::FrankaPanda::Juliet::running";
	}

	// initial state 
	int state = POSTURE;
	string controller_status = "1";
	
	// start redis client
	auto redis_client = Sai2Common::RedisClient();
	redis_client.connect();

	// set up signal handler
	signal(SIGABRT, &sighandler);
	signal(SIGTERM, &sighandler);
	signal(SIGINT, &sighandler);

	// load robots, read current state and update the model
	auto robot = std::make_shared<Sai2Model::Sai2Model>(robot_file, false);
	robot->setQ(redis_client.getEigen(JOINT_ANGLES_KEY));
	robot->setDq(redis_client.getEigen(JOINT_VELOCITIES_KEY));
	robot->updateModel();

	// prepare controller
	int dof = robot->dof();
	VectorXd command_torques = VectorXd::Zero(dof);  // panda + gripper torques 
	MatrixXd N_prec = MatrixXd::Identity(dof, dof);

	// arm task
	const string control_link = "link7";
	const Vector3d control_point = Vector3d(0, 0, 0.107 + 0.030 * 0);
	Affine3d compliant_frame = Affine3d::Identity();
	compliant_frame.translation() = control_point;
	auto pose_task = std::make_shared<Sai2Primitives::MotionForceTask>(robot, control_link, compliant_frame);
	pose_task->disableInternalOtg();
	pose_task->setPosControlGains(100, 15, 0);
	pose_task->setOriControlGains(100, 15, 0);
	pose_task->handleAllSingularitiesAsType1(true);
	pose_task->enableVelocitySaturation(0.3, M_PI / 3);

	Vector3d ee_pos;
	Matrix3d ee_ori;
    Vector3d desired_pos;
    Matrix3d desired_ori;

	// joint task
	auto joint_task = std::make_shared<Sai2Primitives::JointTask>(robot);
	joint_task->setGains(200, 15, 0);
	const double QTOL = 5e-2;

	VectorXd q_desired(dof);
	// q_desired.head(7) << -30.0, -15.0, -15.0, -105.0, 0.0, 90.0, 45.0;
	// q_desired.head(7) *= M_PI / 180.0;
	// q_desired << 0, 0, 0, -1.57079, 0, 1.57079, -0.7853;
	// q_desired << -0.012742,-0.185922,0.011882,-2.100614,0.002333,1.914703,-0.001852;
	// q_desired << -0.0732522,-0.729555,0.0545331,-2.28114,0.0462191,1.57187,0.782391;
	// q_desired << -0.0201507,-0.280972,0.015657,-2.09495,0.0345741,1.86694,0.842742;
	q_desired << -0.0975007,0.0812935,-0.275996,-2.13114,0.0854098,2.19845,0.453058;
	joint_task->setGoalPosition(q_desired);

    // motion retargetting 
    const double LINEAR_SF = 1e0;
    const double ANGULAR_SF = 1e0;
    Vector3d robot_pos_center, vr_pos_center;
    Matrix3d robot_ori_center, vr_ori_center;  

    // setup vr 
	// euler frame transformations from vr frame to viewer frame 
	Matrix3d R_vr_to_base;  // default vr: x right, y up, z in
	R_vr_to_base = AngleAxisd(- M_PI / 2, Vector3d(1, 0, 0)).toRotationMatrix();  // x right, y left, z up
	Matrix3d R_base_to_ee = ee_ori.transpose();
	Matrix3d R_base_ori = AngleAxisd(M_PI / 2, Vector3d(0, 0, 1)).toRotationMatrix().transpose();
	Matrix3d R_base_to_user;
	double device_z_rot = - M_PI / 2;  // default 
	if (argc > 1) {
		device_z_rot = std::strtod(argv[1], NULL) * M_PI / 180;
	}
	R_base_to_user = AngleAxisd(device_z_rot, Vector3d(0, 0, 1)).toRotationMatrix();
	// Matrix3d R_vr_to_user = R_base_to_user * R_vr_to_base;
	Matrix3d R_vr_to_user = MatrixXd::Identity(3, 3);

	// Matrix3d R_optitrack_to_sai = AngleAxisd(- M_PI / 2, Vector3d::UnitZ()).toRotationMatrix() * AngleAxisd(M_PI / 2, Vector3d::UnitX()).toRotationMatrix();
	// Matrix3d R_realsense_to_sai = AngleAxisd(- M_PI / 2, Vector3d::UnitZ()).toRotationMatrix() * AngleAxisd(-M_PI / 2, Vector3d::UnitY()).toRotationMatrix(); // Added transformation matrix 
	// Matrix3d R_realsense_to_sai = AngleAxisd(M_PI, Vector3d::UnitX()).toRotationMatrix();

	// initialize keys 
	redis_client.setEigen(DESIRED_POS_KEY, Vector3d::Zero());
	redis_client.setEigen(DESIRED_ORI_KEY, Matrix3d::Identity());
	redis_client.setInt(REPLAY_READY_KEY, 0);

	// create a loop timer
	runloop = true;
	double control_freq = 1000;
	Sai2Common::LoopTimer timer(control_freq, 1e6);

	while (runloop) {
		timer.waitForNextLoop();
		const double time = timer.elapsedSimTime();

		// update robot 
		robot->setQ(redis_client.getEigen(JOINT_ANGLES_KEY));
		robot->setDq(redis_client.getEigen(JOINT_VELOCITIES_KEY));
		robot->updateModel();

		// set current pose 
		redis_client.setEigen(EE_POS_KEY, robot->position(control_link, control_point));
		redis_client.setEigen(EE_ORI_KEY, robot->rotation(control_link));

        // get desired pose input
        Vector3d vr_pos = redis_client.getEigen(DESIRED_POS_KEY);
        Matrix3d vr_ori = redis_client.getEigen(DESIRED_ORI_KEY);
		// std::cout << "Desired position: \n" << desired_pos.transpose() << "\n";
		// std::cout << "Desired orientation: \n" << desired_ori << "\n";
	
		if (state == POSTURE) {

			// integrator
			if (joint_task->goalPositionReached(10 * QTOL)) {
				joint_task->setGains(200, 20, 50);
			}

			// update task model 
			N_prec.setIdentity();
			joint_task->updateTaskModel(N_prec);

			command_torques = joint_task->computeTorques();

			if (joint_task->goalPositionReached(QTOL)) {
				cout << "Posture To Calibration" << endl;
				pose_task->reInitializeTask();
				joint_task->reInitializeTask();
				joint_task->setGains(200, 20, 0);

				ee_pos = robot->position(control_link, control_point);
				ee_ori = robot->rotation(control_link);

				redis_client.setEigen(DESIRED_POS_KEY, ee_pos);
				redis_client.setEigen(DESIRED_ORI_KEY, ee_ori);
				redis_client.setEigen(ROBOT_HOME_POS_KEY, ee_pos);
				redis_client.setEigen(ROBOT_HOME_ORI_KEY, ee_ori);

				std::cout << "Starting Position: \n" << ee_pos.transpose() << "\n";
				std::cout << "Starting Orientation: \n" << ee_ori.transpose() << "\n";

				// // change desired position to home position
				// Vector3d home_position = Vector3d(0.5, 0, 0.5);
				// Matrix3d home_orientation;
				// home_orientation << 1, 0, 0, 0, -1, 0, 0, 0, -1;
				// pose_task->setGoalPosition(home_position);
				// pose_task->setGoalOrientation(home_orientation);

                // record initial position and orientation
                robot_pos_center = ee_pos;
                robot_ori_center = ee_ori;

				// state = MOTION;
                state = CALIBRATION;
			}
		} else if (state == CALIBRATION) {
			if (redis_client.getInt(REPLAY_READY_KEY)) {
            	vr_pos_center = vr_pos;
            	vr_ori_center = vr_ori;

            	state = MOTION;
				std::cout << "Calibration To Motion\n";
				redis_client.setInt(REPLAY_READY_KEY, 0);
			}

			// update task model 
			N_prec.setIdentity();
			joint_task->updateTaskModel(N_prec);

			command_torques = joint_task->computeTorques();

        } else if (state == MOTION) {
			// update goal position and orientation (relative to starting point)
            Vector3d robot_desired_pos = robot_pos_center + LINEAR_SF *  R_vr_to_user * (vr_pos - vr_pos_center);
            Matrix3d delta_rotation_vr = vr_ori.transpose() * vr_ori_center;
            Matrix3d delta_rotation_base = R_vr_to_user * delta_rotation_vr * R_vr_to_user.transpose();  // similarity transform to bring rotation to inertial frame
            Matrix3d robot_desired_ori = delta_rotation_base * robot_ori_center;

            pose_task->setGoalPosition(robot_desired_pos);
            // pose_task->setGoalOrientation(robot_desired_ori);

			// update task model
			N_prec.setIdentity();
			pose_task->updateTaskModel(N_prec);
			joint_task->updateTaskModel(pose_task->getTaskAndPreviousNullspace());

			command_torques = pose_task->computeTorques() + joint_task->computeTorques();
		}

		// execute redis write callback
		redis_client.setEigen(JOINT_TORQUES_COMMANDED_KEY, command_torques);
	}

	timer.stop();
	cout << "\nSimulation loop timer stats:\n";
	timer.printInfoPostRun();
	redis_client.setEigen(JOINT_TORQUES_COMMANDED_KEY, 0 * command_torques);  // back to floating

	return 0;
}