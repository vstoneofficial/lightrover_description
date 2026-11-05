"""Gazebo Harmonic 上のライトローバーで SLAM (slam_toolbox) を行う launch.

gazebo.launch.py でシミュレータを起動し、slam_toolbox で地図を作る。
設定は config/slam_toolbox_sim.yaml (lightrover_navigation の実機設定を元に、
0.1 m / 0.1 rad 動くごとに地図を更新するようにしたもの)。
実機と同じ設定で試す場合は slam_params_file:=<lightrover_navigation>/config/mapper_params_online_async.yaml を指定する。
ロボットは mouse_teleop.launch.py などで別に動かす。

例:
  ros2 launch lightrover_description gazebo_slam.launch.py
  ros2 launch lightrover_description gazebo_slam.launch.py world:=lightrover_sample_2

地図の保存 (別の端末で):
  ros2 run nav2_map_server map_saver_cli -f ~/lightrover_map --ros-args -p use_sim_time:=true
"""

import os

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    OpaqueFunction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

PKG = 'lightrover_description'


def _setup(context, *args, **kwargs):
    share = get_package_share_directory(PKG)
    try:
        nav_share = get_package_share_directory('lightrover_navigation')
    except PackageNotFoundError as e:
        raise RuntimeError(
            'lightrover_navigation が見つかりません。'
            'lightrover_ros2 (jazzy ブランチ) をワークスペースに入れてビルドしてください。') from e

    def arg(name):
        return LaunchConfiguration(name).perform(context)

    # include の引数 (rviz:=false) で上書きされる前に判定しておく
    use_rviz = arg('rviz').lower() == 'true'

    # include に渡す引数が呼び出し元に漏れないようスコープを閉じる
    gazebo = GroupAction(scoped=True, forwarding=False, actions=[IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(share, 'launch', 'gazebo.launch.py')),
        launch_arguments={
            'world': arg('world'), 'gui': arg('gui'), 'rviz': 'false',
            'x': arg('x'), 'y': arg('y'), 'yaw': arg('yaw'),
        }.items(),
    )])

    # Jazzy の slam_toolbox はライフサイクルノードなので、configure/activate まで行う
    # slam_toolbox 同梱の launch を使う
    slam = GroupAction(scoped=True, forwarding=False, actions=[IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('slam_toolbox'), 'launch', 'online_async_launch.py')),
        launch_arguments={
            # 既定はシミュレータ用設定 (実機設定より地図の更新頻度を上げたもの)
            'slam_params_file': arg('slam_params_file') or os.path.join(
                share, 'config', 'slam_toolbox_sim.yaml'),
            'use_sim_time': 'true',
            'autostart': 'true',
        }.items(),
    )])

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=['-d', os.path.join(nav_share, 'rviz', 'slam.rviz')],
        parameters=[{'use_sim_time': True}],
    )
    return [gazebo, slam, rviz] if use_rviz else [gazebo, slam]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'world', default_value='lightrover_sample',
            description='empty / lightrover_sample / lightrover_sample_2 または SDF のパス'),
        DeclareLaunchArgument(
            'slam_params_file', default_value='',
            description='slam_toolbox のパラメータ (空なら config/slam_toolbox_sim.yaml)'),
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        OpaqueFunction(function=_setup),
    ])
