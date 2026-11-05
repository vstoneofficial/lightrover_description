"""Gazebo Harmonic 上のライトローバーを Nav2 で自律走行させる launch.

gazebo.launch.py でシミュレータを起動し、lightrover_ros2 (jazzy) の
lightrover_navigation を use_sim_time:=true, launch_base:=false で起動する。
地図はワールドに対応するもの (maps/<world>.yaml) を自動で選ぶ。

例:
  ros2 launch lightrover_description gazebo_nav.launch.py
  ros2 launch lightrover_description gazebo_nav.launch.py world:=lightrover_sample_2
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

    world = arg('world')
    world_name = os.path.splitext(os.path.basename(world))[0]
    map_file = arg('map') or os.path.join(share, 'maps', world_name + '.yaml')
    if not os.path.isfile(map_file):
        raise RuntimeError(f'[{PKG}] 地図が見つかりません: {map_file} (map:=... で指定してください)')

    # include に渡す引数 (rviz:=false など) が呼び出し元に漏れないようスコープを閉じる
    gazebo = GroupAction(scoped=True, forwarding=False, actions=[IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(share, 'launch', 'gazebo.launch.py')),
        launch_arguments={
            'world': world, 'gui': arg('gui'), 'rviz': 'false',
            'x': arg('x'), 'y': arg('y'), 'yaw': arg('yaw'),
        }.items(),
    )])

    navigation = GroupAction(scoped=True, forwarding=False, actions=[IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav_share, 'launch', 'lightrover_navigation.launch.py')),
        launch_arguments={
            'use_sim_time': 'true',
            'launch_base': 'false',          # 実機用ノード(I2C, LiDARドライバ)は起動しない
            'map': map_file,
            'params_file': arg('params_file') or os.path.join(nav_share, 'config', 'nav2_params.yaml'),
            'launch_rviz': arg('rviz'),
            'set_initial_pose': 'true',       # スポーン位置をAMCLの初期位置にする
            'initial_pose_x': arg('x'),
            'initial_pose_y': arg('y'),
            'initial_pose_yaw': arg('yaw'),
            'initial_pose_wait_sec': arg('initial_pose_wait_sec'),
        }.items(),
    )])
    return [gazebo, navigation]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'world', default_value='lightrover_sample',
            description='lightrover_sample / lightrover_sample_2 または SDF のパス'),
        DeclareLaunchArgument('map', default_value='', description='地図yaml (空ならワールドに対応する同梱地図)'),
        DeclareLaunchArgument('params_file', default_value='', description='Nav2パラメータ (空ならlightrover_navigationの既定)'),
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        DeclareLaunchArgument('initial_pose_wait_sec', default_value='10.0'),
        OpaqueFunction(function=_setup),
    ])
