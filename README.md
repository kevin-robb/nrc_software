# Simulator Demo

This is a stable build of the NRC robot software to be run in simulation for demonstration purposes.
This code is verified to work in the SCR Simulator v.18 with ROS Melodic in Ubuntu 18.04 (and using WSL 1).

## To run this code:
 - Clone the repository and switch to the demo_sim branch by running `git checkout demo_sim`.
 - If using WSL, [install VcXsrv](https://sourceforge.net/projects/vcxsrv/) and run it as specified [here](https://janbernloehr.de/2017/06/10/ros-windows#install-vcxsrv).
 - Download [Version 18 of the SCR Simulator](https://github.com/SoonerRobotics/scr_simulator/releases/tag/v18) and unzip it.
    - For WSL, run the scr_simulator.exe file.
    - On linux, run `chmod +x scr_simulator.x86_64`, `cd ~`, and `./SIMULATOR_DIRECTORY/scr_simulator_v18_linux/scr_simulator.x86_64`.
 - Start the NRC code.
    
    cd ~/nrc_software/nrc_ws
    catkin_make
    source devel/setup.bash
    roslaunch nrc_nav drive_pp_sim.launch

 - Ensure the options for NRC are selected in the simulator. After the console shows rosbridge has connected to port 9090, click "Run" in the simulator to connect the client. You may need to wait a few seconds for VcXsrv to connect and for the code to start up. If it does not connect the client, press Escape and click "Restart" in the simulator to attempt a reconnect.

## How the robot's trajectory is created:

The course is specified by the file `config.json` in the `trajectory_gen` folder. This file specifies the _course_ (the first half of the file) and the _waypoints_ (the second half of the file). Course points represent physical nodes such as cones or buckets that the robot needs to go around but not hit. Waypoints are imaginary points that are used to generate the path. Course points are included purely for display purposes, while waypoints are used to generate the trajectory that the robot will follow. The robot is likely to pass through waypoints, so they should be placed a small distance away from the course points to prevent collisions.

## To change the robot's trajectory:
 - Make sure you are in the trajectory_gen folder by running `cd trajectory_gen` from the main directory.
 - Open the config.json file to edit its contents. This can be done by running `nano config.json`, `code config.json`, or whatever editor you prefer. 
 - Modify, add, or remove _waypoints_ to change the path the robot will follow. To ensure an accurate depiction of your setup, you may wish to alter the _course_ points as well so they will be displayed appropriately.
 - Exit the editor and save your changes. 
 - Now that we have a new course, we need to create a new trajectory. Execute `python main.py` to generate a new trajectory. This will replace the file `output_traj.csv` with the new trajectory.
 - The last step is to make the code use this new trajectory rather than the old one. Run `cp output_traj.csv ../nrc_ws/src/nrc_nav/src` to replace the old trajectory with this new one.
 - The next time the code is run, it will generate a path using this new trajectory, and the VcXsrv display should reflect this.

---

# Physical Robot Software
Software for the NRC AVC 2019/20 robot

## Setup

This setup assumes and has only been tested on a Raspberry Pi 3 running Ubuntu 18.04.3 with [ROS Melodic](http://wiki.ros.org/melodic) installed.

**You must clone this repo into /home/nrc/ for the setup to work. The scripts assume that /home/nrc/nrc_software exists. This will (hopefully but probably not) be improved in the future.**

## Run on boot

To setup running on boot, run `sudo ./setup` from within the `setup` directory. This will copy `setup/systemd/nrc.service` into the `/etc/systemd/system/` directory to create the `nrc` service. It will also run `systemctl enable nrc` which enables the `nrc` service to run on startup.

## Configuring startup

On boot, `setup/systemd/nrc_start.sh` will be run. Modify this as needed.

## The `nrc` service

The `nrc` service is a [systemd](https://www.freedesktop.org/software/systemd/man/systemd.service.html) service unit so it can controlled using `service` or `systemctl`.

Common use cases:
 - `sudo service nrc start` to start the service.
 - `sudo service nrc stop` to stop the service.
 - `sudo service nrc restart` to restart the service.
 - `sudo service nrc status` to view the active status of the service.
 - `sudo systemctl enable nrc` to enable the service running on startup.
 - `sudo systemctl disable nrc` to disable the service running on startup.
 - `sudo journalctl -e -t nrc_logs` to view logs.
