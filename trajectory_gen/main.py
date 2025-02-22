
import json
import matplotlib.pyplot as plt
import numpy as np

from math import cos, sin, radians, sqrt, pi, floor
from scipy.interpolate import splprep, splev

from segment import Segment
from trajectory_point import TrajectoryPoint


HEADER = "time, x, y, velocity, accel, heading\n"

course_x = [0]
course_y = [0]
course_segs = []
traj_pts = []
wpt_x = []
wpt_y = []
wpt_u = []
wpt_v = []

def plot_course(course_info):
    xt = 0
    yt = 0
    course_x = [0]
    course_y = [0]

    # Run through all the segments
    for i in range(len(course_info['segments'])):
        # Get settings
        hdg = course_info['segments'][i]['heading']
        length = course_info['segments'][i]['length']

        # Set the segment start point and other info
        seg = Segment()
        seg.set_start(xt, yt)
        seg.set_hdg(hdg)

        # Update the current endpoint based on the settings
        xt = xt + length * cos(radians(hdg))
        yt = yt + length * sin(radians(hdg))

        # Set the segment endpoint
        seg.set_end(xt, yt)

        # Add segment to the course
        course_segs.append(seg)

        # Append endpoint to the list
        course_x.append(xt)
        course_y.append(yt)

    # Plot the course
    plt.plot(course_x, course_y, 'r')


def plot_waypoints(waypoints):
    # Reset the waypoints
    wpt_x = []
    wpt_y = []
    wpt_u = []
    wpt_v = []

    # Loop through the waypoints
    for i in range(len(waypoints)):
        # Get waypoint info
        hdg = waypoints[i]['heading']
        x = waypoints[i]['x']
        y = waypoints[i]['y']

        # Update display lists
        wpt_x.append(x)
        wpt_y.append(y)
        wpt_u.append(cos(radians(hdg)))
        wpt_v.append(sin(radians(hdg)))

    # Show waypoints as vector field
    plt.quiver(wpt_x, wpt_y, wpt_u, wpt_v)


def spline_fit():
    pass
    #pts = np.array(list(zip(wpt_x, wpt_y)))
    #tck, u = splprep(pts.T, u=None, s=0.0, per=1)
    #u_new = np.linspace(u.min(), u.max(), 1000)
    #x_new, y_new = splev(u_new, tck, der=0)
#
    #plt.plot(x_new, y_new)


def is_straight_line(cur_type, next_type):
    if cur_type == 'turn_end' or next_type == 'end_pt':
        return True
    return False


def create_straight_line(config, cur_wpt, next_wpt):
    # robot settings
    robot = config['robot']
    max_speed = float(robot['max_speed'])
    max_accel = float(robot['max_accel'])

    # coordinates for the start point
    if cur_wpt['type'] == "turn_end":
        x1 = traj_pts[-1].x
        y1 = traj_pts[-1].y
    else:
        x1 = float(cur_wpt['x'])
        y1 = float(cur_wpt['y'])

    # coordinates for the end point
    x2 = float(next_wpt['x'])
    y2 = float(next_wpt['y'])
    hdg = float(cur_wpt['heading'])

    # Distance between waypoints
    dist = sqrt((x1-x2)**2 + (y1-y2)**2)

    # Velocities
    cur_vel = float(min(cur_wpt['speed'], max_speed))
    next_vel = float(min(next_wpt['speed'], max_speed))

    # Find duration needed to achieve cruise velocity
    if len(traj_pts) == 0:
        t0 = 0.0
    else:
        t0 = float(traj_pts[-1].t)
    t_cruise = (next_vel - cur_vel) / max_accel

    # Find how much distance remains once cruise velocity is achieved
    dist_at_cruise = cur_vel*t_cruise + 0.5*max_accel*t_cruise**2
    dist_remain_cruise = dist - dist_at_cruise

    # If the acceleration is too great, cancel the trajectory with an error message
    if dist_remain_cruise < 0:
        print("ERROR: Unreachable waypoint. Going from WPT #" + str(cur_wpt['id']) + " to WPT #" + str(next_wpt['id'])
            + " with current parameters results in overshoot.\nCancelling trajectory generation.")
        return -1

    # Calculate cruise coords
    x_cruise = x1 + dist_at_cruise * cos(radians(hdg))
    y_cruise = y1 + dist_at_cruise * sin(radians(hdg))

    # Find time at next_wpt
    tf = dist_remain_cruise / next_vel

    # Create trajectory points
    # Accelerate to the cruise velocity
    accel_start_pt = TrajectoryPoint(t0, x1, y1, cur_vel, max_accel, hdg)
    traj_pts.append(accel_start_pt)

    # Once at cruise velocity, stop accelerating
    accel_end_pt = TrajectoryPoint(t0 + t_cruise, x_cruise, y_cruise, next_vel, 0, hdg)
    traj_pts.append(accel_end_pt)

    # Reach the goal waypoint
    wpt_traj_pt = TrajectoryPoint(t0+tf, x2, y2, next_vel, 0, hdg)
    traj_pts.append(wpt_traj_pt)

    return 0


def create_turn(params, cur_wpt, next_wpt):
    # HACK: this circle heuristic is a total hack. Using splines or actual physics would be better.

    # general settings
    settings = params['settings']
    hdg_eps = float(settings['hdg_eps'])

    # robot settings
    robot = params['robot']
    max_speed = float(robot['max_speed'])

    # Coordinates
    x1 = float(cur_wpt['x'])
    y1 = float(cur_wpt['y'])
    x2 = float(next_wpt['x'])
    y2 = float(next_wpt['y'])
    hdg1 = float(cur_wpt['heading'])
    hdg2 = float(next_wpt['heading'])

    # Distance between waypoints
    dist = sqrt((x1-x2)**2 + (y1-y2)**2)

    # Assume the waypoints are always on the same diameter
    radius = dist / 2

    # Velocities
    cur_vel = float(min(cur_wpt['speed'], max_speed))
    next_vel = float(min(next_wpt['speed'], max_speed))
    avg_vel = (cur_vel + next_vel) / 2

    # Calculate degrees the circle will rotate
    hdg_diff = hdg2 - hdg1

    # Calculate how long this turn will take
    t0 = 0.0 if len(traj_pts) == 0 else float(traj_pts[-1].t)
    tf = (2 * pi * radius / avg_vel) * (abs(hdg_diff) / 360) + t0
    arc_len = (tf-t0) * avg_vel

    # Go around the circle until the course change has been made
    if hdg_diff < 0:
        hdg_eps = -hdg_eps

    # track the sweep
    num_segs = int(floor(hdg_diff / hdg_eps)) + 1
    seg_len = arc_len / num_segs

    # Initialize turn vars
    x = x1
    y = y1
    hdg = hdg1

    for i in range(num_segs):
        t = (i+1) * (tf - t0) / num_segs + t0
        hdg = hdg + hdg_eps
        x_new = x + seg_len * cos(radians(hdg))
        y_new = y + seg_len * sin(radians(hdg))
        x = x_new
        y = y_new
        traj_pt = TrajectoryPoint(t, x_new, y_new, avg_vel, 0, hdg)
        traj_pts.append(traj_pt)

    return 0


def simple_trajectory_generation(params):
    # Parameter aliases
    waypoints = params['waypoints']

    # Track waypoint types
    last_type = None
    cur_type = None
    next_type = None

    # Stitch together the waypoints
    for i in range(len(waypoints)):
        # Get waypoint types
        cur_type = waypoints[i]['type']
        next_type = None if i == (len(waypoints) - 1) else waypoints[i + 1]['type']

        # End the generation if we have found the last waypoint
        if next_type is None:
            break

        # Get waypoints
        cur_wpt = waypoints[i]
        next_wpt = waypoints[i + 1]

        # If this is the start, then it's always a straight drive from here to the next point
        # Also, if it is a straight line we should make a straight line
        if last_type is None or is_straight_line(cur_type, next_type):
            result = create_straight_line(params, cur_wpt, next_wpt)
        # Otherwise, turn starting from the current waypoint and ending at the next waypoint
        else:
            result = create_turn(params, cur_wpt, next_wpt)

        # if there are errors, cancel the trajectory generation
        if result < 0:
            return

        # Pass the types to the next step
        last_type = cur_type


def plot_traj_points():
    x = []
    y = []

    for traj_pt in traj_pts:
        x.append(traj_pt.x)
        y.append(traj_pt.y)

    plt.plot(x, y, marker='x', color='g')



# Main function
if __name__ == "__main__":
    # Open the configuration parameters file
    config_file = open("config.json", 'r')

    # Parse the configuration as JSON
    params = json.load(config_file)

    # Prepare the course plot
    plot_course(params['course'])

    # Prepare the trajectory by adding waypoints
    plot_waypoints(params['waypoints'])

    # Perform a spline fit to create the trajectory points
    # spline_fit()    # TODO: implement spline trajectory generation

    # Perform simple trajectory generation to make the trajectory points
    simple_trajectory_generation(params)

    # Plot the trajectory points
    plot_traj_points()

    # Export data to CSV
    csv_out = open("../nrc_ws/src/nrc_nav/src/output_traj.csv", "w")
    csv_out.write(HEADER)
    for traj_point in traj_pts:
        csv_out.write(traj_point.export_csv_string())

    # Close file I/O
    csv_out.close()
    config_file.close()

    # Display plot of trajectory and course
    plt.show()
