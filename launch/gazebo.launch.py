"""ライトローバーを Gazebo Harmonic (gz-sim 8) 上で起動する launch.

実機と同じインターフェースを提供する:
  - 速度指令  : /rover_twist (geometry_msgs/Twist)
  - オドメトリ: /odom (nav_msgs/Odometry), TF odom -> base_footprint
  - LiDAR    : /scan (sensor_msgs/LaserScan, frame: laser_frame)
  - 時刻      : /clock (use_sim_time:=true で使う)

例:
  ros2 launch lightrover_description gazebo.launch.py
  ros2 launch lightrover_description gazebo.launch.py world:=lightrover_sample_2
  ros2 launch lightrover_description gazebo.launch.py world:=empty gui:=false rviz:=true
"""

import os

from ament_index_python.packages import (
    PackageNotFoundError,
    get_package_prefix,
    get_package_share_directory,
)
from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

PKG = 'lightrover_description'


def _resolve_world(world: str, share: str) -> str:
    """名前 (empty / lightrover_sample / lightrover_sample_2) またはパスを SDF のパスにする."""
    if os.path.isfile(world):
        return world
    name = world[:-4] if world.endswith('.sdf') else world
    path = os.path.join(share, 'worlds', name + '.sdf')
    if not os.path.isfile(path):
        raise RuntimeError(f'[{PKG}] world が見つかりません: {world}')
    return path


def _gz_ros2_control_plugin_path() -> str:
    """gz_ros2_control-system プラグインのあるディレクトリを返す.

    通常は gz_ros2_control の環境フックが GZ_SIM_SYSTEM_PLUGIN_PATH を設定するが、
    setup.bash の読み込み漏れなどで設定されていないと Gazebo がプラグインを見つけられず、
    コントローラが起動しない (odom の TF が出ず Nav2 も動かない)。そのため明示的に渡す。
    """
    try:
        prefix = get_package_prefix('gz_ros2_control')
    except PackageNotFoundError as e:
        raise RuntimeError(
            f'[{PKG}] gz_ros2_control が見つかりません。\n'
            '  sudo apt install ros-jazzy-gz-ros2-control\n'
            'を実行し、source /opt/ros/jazzy/setup.bash してから再度起動してください。') from e
    lib_dir = os.path.join(prefix, 'lib')
    if not os.path.isfile(os.path.join(lib_dir, 'libgz_ros2_control-system.so')):
        raise RuntimeError(
            f'[{PKG}] {lib_dir} に libgz_ros2_control-system.so がありません。'
            'ros-jazzy-gz-ros2-control を再インストールしてください。')
    return lib_dir


def _gazebo(context, *args, **kwargs):
    share = get_package_share_directory(PKG)
    world = _resolve_world(LaunchConfiguration('world').perform(context), share)
    gui = LaunchConfiguration('gui').perform(context).lower() == 'true'
    verbose = LaunchConfiguration('gz_verbose').perform(context)

    gz_args = f'-r -v {verbose} '
    if not gui:
        # GUIなしでもLiDAR(gpu_lidar)を動かすため headless rendering を有効にする
        gz_args += '-s --headless-rendering '
    gz_args += world

    return [
        AppendEnvironmentVariable('GZ_SIM_SYSTEM_PLUGIN_PATH', _gz_ros2_control_plugin_path()),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')),
            launch_arguments={'gz_args': gz_args, 'on_exit_shutdown': 'true'}.items(),
        )
    ]


def generate_launch_description():
    share = get_package_share_directory(PKG)
    xacro_file = os.path.join(share, 'urdf', 'lightrover_urdf.xacro')
    use_sim_time = {'use_sim_time': True}

    robot_description = ParameterValue(
        Command([FindExecutable(name='xacro'), ' ', xacro_file]), value_type=str)

    # URDF内の package://lightrover_description/... を Gazebo から解決できるようにする
    resource_path = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.join(get_package_prefix(PKG), 'share'))

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description}, use_sim_time],
    )

    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-world', 'default',
            '-name', 'lightrover',
            '-topic', '/robot_description',
            '-x', LaunchConfiguration('x'),
            '-y', LaunchConfiguration('y'),
            '-z', LaunchConfiguration('z'),
            '-Y', LaunchConfiguration('yaw'),
        ],
    )

    controllers = Node(
        package='controller_manager',
        executable='spawner',
        output='screen',
        arguments=[
            'joint_state_broadcaster', 'diff_drive_controller',
            '--controller-manager-timeout', '120',
        ],
        parameters=[use_sim_time],
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        output='screen',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
        ],
        parameters=[use_sim_time],
    )

    relay = Node(
        package=PKG,
        executable='rover_twist_relay.py',
        output='screen',
        parameters=[use_sim_time],
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=['-d', os.path.join(share, 'rviz', 'gazebo.rviz')],
        parameters=[use_sim_time],
        condition=IfCondition(LaunchConfiguration('rviz')),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'world', default_value='lightrover_sample',
            description='empty / lightrover_sample / lightrover_sample_2 または SDF のパス'),
        DeclareLaunchArgument('gui', default_value='true', description='Gazebo の GUI を表示する'),
        DeclareLaunchArgument('rviz', default_value='false', description='RViz2 を起動する'),
        DeclareLaunchArgument('gz_verbose', default_value='1', description='Gazebo のログレベル (0-4)'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('z', default_value='0.01'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        resource_path,
        OpaqueFunction(function=_gazebo),
        robot_state_publisher,
        spawn,
        bridge,
        controllers,
        relay,
        rviz,
    ])
