"""マウス(タッチパッド)でシミュレータ上のライトローバーを操作する launch.

gazebo.launch.py / gazebo_slam.launch.py などでシミュレータを起動してから、
別の端末で起動する。表示されたウィンドウ上でドラッグすると走行し、
ボタンを離すと停止する (上下ドラッグ: 前後進, 左右ドラッグ: 旋回)。

例:
  ros2 launch lightrover_description mouse_teleop.launch.py
  ros2 launch lightrover_description mouse_teleop.launch.py scale:=0.2
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'scale', default_value='0.3',
            description='ウィンドウ端までドラッグしたときの速度 (m/s, rad/s)'),
        Node(
            package='mouse_teleop',
            executable='mouse_teleop',
            name='mouse_teleop',
            output='screen',
            parameters=[{
                'scale': ParameterValue(LaunchConfiguration('scale'), value_type=float),
                'holonomic': False,
                'use_sim_time': True,
            }],
            # Jazzy の mouse_teleop は TwistStamped を出すので Stamped 用の入力へ
            remappings=[('mouse_vel', '/rover_twist_stamped')],
        ),
    ])
