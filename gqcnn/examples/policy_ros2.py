#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright ©2017. The Regents of the University of California (Regents).
All Rights Reserved. Permission to use, copy, modify, and distribute this
software and its documentation for educational, research, and not-for-profit
purposes, without fee and without a signed licensing agreement, is hereby
granted, provided that the above copyright notice, this paragraph and the
following two paragraphs appear in all copies, modifications, and
distributions. Contact The Office of Technology Licensing, UC Berkeley, 2150
Shattuck Avenue, Suite 510, Berkeley, CA 94720-1620, (510) 643-7201,
otl@berkeley.edu,
http://ipira.berkeley.edu/industry-info for commercial licensing opportunities.

IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL,
INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF
THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF REGENTS HAS BEEN
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
PURPOSE. THE SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED
HEREUNDER IS PROVIDED "AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE
MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.

Displays robust grasps planned using a GQ-CNN-based policy on a set of saved
RGB-D images. The default configuration is cfg/examples/policy.yaml.

Author
------
Jeff Mahler
"""
import argparse
import logging
import numpy as np
import os
# import rosgraph.roslogging as rl
# import rospy
import sys
import rclpy
from ament_index_python.packages import get_package_share_directory

from cv_bridge import CvBridge, CvBridgeError

from autolab_core import (Point, Logger, BinaryImage, CameraIntrinsics,
                          ColorImage, DepthImage)
from visualization import Visualizer2D as vis

from gqcnn.grasping import Grasp2D, SuctionPoint2D, GraspAction
from gqcnn_interfaces.msg import GQCNNGrasp
from gqcnn_interfaces.srv import GQCNNGraspPlanner, GQCNNGraspPlannerSegmask

# Set up logger.
logger = Logger.get_logger("examples/policy_ros.py")

def main(args=None):
    # Parse args.
    parser = argparse.ArgumentParser(
        description="Run a grasping policy on an example image")
    parser.add_argument(
        "--depth_image",
        type=str,
        default=None,
        help="path to a test depth image stored as a .npy file")
    parser.add_argument("--segmask",
                        type=str,
                        default=None,
                        help="path to an optional segmask to use")
    parser.add_argument("--camera_intr",
                        type=str,
                        default=None,
                        help="path to the camera intrinsics")
    parser.add_argument("--gripper_width",
                        type=float,
                        default=0.05,
                        help="width of the gripper to plan for")
    parser.add_argument("--namespace",
                        type=str,
                        default="gqcnn",
                        help="namespace of the ROS grasp planning service")
    parser.add_argument("--vis_grasp",
                        type=bool,
                        default=True,
                        help="whether or not to visualize the grasp")
    args = parser.parse_args()
    depth_im_filename = args.depth_image
    segmask_filename = args.segmask
    camera_intr_filename = args.camera_intr
    gripper_width = args.gripper_width
    namespace = args.namespace
    vis_grasp = args.vis_grasp

    # Initialize the ROS node.
    rclpy.init(args=None)
    node = rclpy.create_node('grasp_planning_example')

    # logging.getLogger().addHandler(rl.RosStreamHandler())

    # Setup filenames.

    gqcnn_ros_share_dir = get_package_share_directory('gqcnn')
    if depth_im_filename is None:
        depth_im_filename =  gqcnn_ros_share_dir + "/data/examples/single_object/primesense/depth_9.npy"
    if camera_intr_filename is None:
        camera_intr_filename =  gqcnn_ros_share_dir + "/data/calib/primesense/primesense.intr"


    plan_grasp = node.create_client(GQCNNGraspPlanner, 
                                    "%s/grasp_planner" % (namespace),)
    plan_grasp_segmask = node.create_client(GQCNNGraspPlannerSegmask, 
                                            "%s/grasp_planner_segmask" % (namespace))
    # Wait for grasp planning service and create service proxy.
    plan_grasp.wait_for_service(timeout_sec=1.0)
    plan_grasp_segmask.wait_for_service(timeout_sec=1.0)

    cv_bridge = CvBridge()


    # Set up sensor.
    camera_intr = CameraIntrinsics.load(camera_intr_filename)

    # Read images.
    depth_im = DepthImage.open(depth_im_filename, frame=camera_intr.frame)
    color_im = ColorImage(np.zeros([depth_im.height, depth_im.width,
                                    3]).astype(np.uint8),
                          frame=camera_intr.frame)
    
    a = np.load(depth_im_filename)
    print(a)
    # print(depth_im.data)

    # Read segmask.
    if segmask_filename is not None:
        segmask = BinaryImage.open(segmask_filename, frame=camera_intr.frame)
        # grasp_resp = plan_grasp_segmask(color_im.rosmsg, depth_im.rosmsg,
        #                                 camera_intr.rosmsg, segmask.rosmsg)
        

        request = GQCNNGraspPlannerSegmask.Request()
        request.color_image = color_im.rosmsg
        request.depth_image = depth_im.rosmsg
        request.camera_info = camera_intr.rosmsg
        request.segmask = segmask.rosmsg
        try:
            future = plan_grasp_segmask.call_async(request)
            rclpy.spin_until_future_complete(node, future)
            grasp_resp = future.result()
            print('GQCNNGrasp:', grasp_resp.grasp)
        except rclpy.exceptions.ServiceUnavailableException as e:
            node.get_logger().error('Service unavailable: %s' % e)
        except rclpy.exceptions.ServiceResponseError as e:
            node.get_logger().error('Service response error: %s' % e)
    else:
        # grasp_resp = plan_grasp(color_im.rosmsg, depth_im.rosmsg,
        #                         camera_intr.rosmsg)
        request_ = GQCNNGraspPlanner.Request()
        request_.color_image = color_im.rosmsg
        request_.depth_image = depth_im.rosmsg
        request_.camera_info = camera_intr.rosmsg

        try:
            future = plan_grasp.call_async(request_)
            rclpy.spin_until_future_complete(node, future)
            grasp_resp = future.result()
            print('GQCNNGrasp:', grasp_resp.grasp.center_px)
        except rclpy.exceptions.ServiceUnavailableException as e:
            node.get_logger().error('Service unavailable: %s' % e)
        except rclpy.exceptions.ServiceResponseError as e:
            node.get_logger().error('Service response error: %s' % e)
    grasp = grasp_resp.grasp
    print(grasp.q_value)

    # Convert to a grasp action.
    grasp_type = grasp.grasp_type
    if grasp_type == GQCNNGrasp.PARALLEL_JAW:
        center = Point(np.array([grasp.center_px[0], grasp.center_px[1]]),
                       frame=camera_intr.frame)
        grasp_2d = Grasp2D(center,
                           grasp.angle,
                           grasp.depth,
                           width=gripper_width,
                           camera_intr=camera_intr)
    elif grasp_type == GQCNNGrasp.SUCTION:
        center = Point(np.array([grasp.center_px[0], grasp.center_px[1]]),
                       frame=camera_intr.frame)
        grasp_2d = SuctionPoint2D(center,
                                  np.array([0, 0, 1]),
                                  grasp.depth,
                                  camera_intr=camera_intr)
    else:
        raise ValueError("Grasp type %d not recognized!" % (grasp_type))
    try:
        thumbnail = DepthImage(cv_bridge.imgmsg_to_cv2(
            grasp.thumbnail, desired_encoding="passthrough"),
                               frame=camera_intr.frame)
    except CvBridgeError as e:
        logger.error(e)
        logger.error("Failed to convert image")
        sys.exit(1)
    action = GraspAction(grasp_2d, grasp.q_value, thumbnail)

    # Vis final grasp.
    print("---------------------")
    if vis_grasp:
        vis.figure(size=(10, 10))
        vis.imshow(depth_im, vmin=0.6, vmax=0.9)
        vis.grasp(action.grasp, scale=2.5, show_center=False, show_axis=True)
        vis.title("Planned grasp on depth (Q=%.3f)" % (action.q_value))
        vis.show()
if __name__ == "__main__":
    main()