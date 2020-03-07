#! /usr/bin/env python

import rospy, rospkg

import csv
import time
from math import atan2, degrees
from numpy import genfromtxt

from pure_pursuit import PurePursuit
from pp_viewer import setup_pyplot, draw_pp
from nrc_msgs.msg import LocalizationVector, DriveStatus, motors

command_pub = None
# generated trajectory, pulled in once at start
instructions = None
# pure pursuit path
pp = PurePursuit()
# current position and heading (in degrees)
pos = None
heading = None
# specify whether to show the planned path plot
SHOW_PLOTS = True

# PID variables
integrator = 0
last_error = 0.0
last_time = time.time()

def generate_pure_pursuit_path():
    global pp
    pp = PurePursuit()
    for i in range(len(instructions)):
        # add x,y coords from each point in the generated trajectory as waypoints.
        # this is better than just adding the 5 nodes as waypoints.
        pp.add_point(instructions[i][1], instructions[i][2])
        #interpolate_path(i)

def interpolate_path(i):
    # interpolate straight sections and fill with more points
    # this is useful for debugging and seeing the exact path
    # However, does not work with the extra ramp waypoint
    if i < len(instructions) - 1:
        x_gap = instructions[i][1] - instructions[i+1][1]
        y_gap = instructions[i][2] - instructions[i+1][2]
        density = 20
        # use min_dist to prevent expansion on curves that already have many points
        min_dist = 2 #meters
        if abs(x_gap) > min_dist:
            incr = x_gap / density
            for n in range(density):
                pp.add_point(instructions[i][1] - n*incr, instructions[i][2])
        elif abs(y_gap) > min_dist:
            incr = y_gap / density
            for n in range(density):
                pp.add_point(instructions[i][1], instructions[i][2] - n*incr)

def receive_position(local_pos):
    # triggers when receiving position from David's localization code
    global pos
    pos = (local_pos.x, local_pos.y)

    #TODO print debug code to console
    #print("Position: " + str(local_pos.x) + ", " + str(local_pos.y) + "\n")


def receive_heading(status):
    # triggers when sensors (IMU) publish sensor data, including yaw
    global heading
    heading = 360 - degrees(status.yaw)

def generate_motor_command(timer_event): 
    global integrator, last_time, last_error

    # this function template was taken from igvc_nav_node.py
    if pos is None or heading is None:
        # wait until sensors/localization bring in data to do anything
        return

    # take a snapshot of the current position so it doesn't change while this function is running
    cur_pos = (pos[0], pos[1])

    # declare the look-ahead point
    lookahead = None
    # start with a search radius of 0.4 meters
    radius = 3 #0.4

    # look until finding the path at the increasing radius or hitting 2 meters
    while lookahead is None and radius <= 6: 
        lookahead = pp.get_lookahead_point(cur_pos[0], cur_pos[1], radius)
        radius *= 1.25
    
    # plot the planned path using Noah's IGVC pp code
    if SHOW_PLOTS:
        draw_pp(cur_pos, lookahead, pp.path, xlims=[-15,15], ylims=[-5,30])

    # make sure we actually found the path
    if lookahead is not None:
        heading_to_la = degrees(atan2(lookahead[1] - cur_pos[1], lookahead[0] - cur_pos[0]))
        if heading_to_la <= 0:
            heading_to_la += 360

        #TODO print debug code to console
        #print("Sensed Heading: " + str(heading))
        #print("Desired Heading: " + str(heading_to_la))

        delta = heading_to_la - heading
        delta = (delta + 180) % 360 - 180

        # PID
        error = delta
        time_diff = max(time.time() - last_time, 0.001)
        integrator += error * time_diff
        slope = (error - last_error) / time_diff

        P = 0.001 * error #was 0.002
        max_P = 0.25
        if abs(P) > max_P:
            # cap P and maintain sign
            P *= max_P/P
        I = 0.00001 * integrator
        D = 0.0001 * slope

        drive_power = 1.5
        turn_power = P + I + D

        last_error = error
        last_time = time.time()

        # make the motors command
        motor_msg = motors()
        # convert to angular velocity (needed for simulator v20)
        wheel_radius = 0.0635 # in meters, about 2.5 inches
        motor_msg.left = (drive_power - turn_power) / wheel_radius
        motor_msg.right = (drive_power + turn_power) / wheel_radius
        
        command_pub.publish(motor_msg)

if __name__ == "__main__":
    # initialize with first instruction
    instruction_index = 0

    # get an instance of RosPack with the default search paths
    rospack = rospkg.RosPack()
    filepath = rospack.get_path('nrc_nav') + "/src/"

    # csv is generated with path, based on time passed since start
    # will need to make sure to copy file into this directory after creating it in trajectory_gen
    instructions = genfromtxt(filepath + 'output_traj.csv', delimiter=',', skip_header=1, names="time,x,y,velocity,accel,heading")

    # create the pure pursuit path using the generated trajectory
    generate_pure_pursuit_path()

    # get localization info from David's code
    local_sub = rospy.Subscriber("/nrc/robot_state", LocalizationVector, receive_position, queue_size=1)
    # get heading from a DriveStatus
    status_sub = rospy.Subscriber("/nrc/sensor_data", DriveStatus, receive_heading, queue_size=1)

    # Initialize ROS node
    rospy.init_node("nrc_drive_dr")

    # Set up a publisher for publishing the drive command
    command_pub = rospy.Publisher("/nrc/motors", motors, queue_size=1)

    # Set up a timer to generate new commands at 10 Hz
    update_timer = rospy.Timer(rospy.Duration(secs=0.01), generate_motor_command)

    # setup plotter for the pp path
    if SHOW_PLOTS:
        setup_pyplot()

    # Pump callbacks
    rospy.spin()
