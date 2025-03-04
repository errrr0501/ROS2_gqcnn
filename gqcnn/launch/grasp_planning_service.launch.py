import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
  gqcnn_ros_share_dir = get_package_share_directory('gqcnn')

  ros_param_file = LaunchConfiguration('ros_param_file', default = gqcnn_ros_share_dir + '/config/ros.yaml')
  # print(gqcnn_ros_share_dir)
  
  declare_ros_param_file_cmd = DeclareLaunchArgument(
      'ros_param_file',
      default_value = gqcnn_ros_share_dir + '/config/ros.yaml',
      description = 'Path to file with ROS related config')  



  grasp_planning_service_cmd = Node(
    namespace = 'gqcnn',
    package='gqcnn',
    executable='grasp_planner_node.py',
    name='grasp_planner',
    output='screen',
    parameters=[ros_param_file,
    ])

  ld = LaunchDescription()

  ld.add_action(declare_ros_param_file_cmd)  
  ld.add_action(grasp_planning_service_cmd)

  return ld