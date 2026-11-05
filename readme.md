# ライトローバー Gazeboモデル (ROS 2 Jazzy / Gazebo Harmonic)

ROS 2 と連携し、Gazebo Harmonic で使用できるライトローバーのモデルです。
ライトローバー本体が無くても動作します。

実機と同じトピックでシミュレータを動かせるため、[lightrover_ros2](https://github.com/vstoneofficial/lightrover_ros2) (jazzy ブランチ) の
Nav2 設定をそのまま使って自律走行できます。

詳細は下記のwebdocをご確認ください。
- ライトローバーwebdoc: https://vstoneofficial.github.io/lightrover_webdoc/
- ライトローバー製品ページ: https://www.vstone.co.jp/products/lightrover/index.html

## 動作環境

- Ubuntu 24.04
- ROS 2 Jazzy
- Gazebo Harmonic (gz-sim 8)

## インストール

```bash
sudo apt install ros-jazzy-ros-gz ros-jazzy-gz-ros2-control ros-jazzy-ros2-controllers \
  ros-jazzy-xacro ros-jazzy-joint-state-publisher-gui \
  ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-slam-toolbox \
  ros-jazzy-mouse-teleop ros-jazzy-teleop-twist-keyboard

cd ~/ros2_ws/src
git clone -b jazzy https://github.com/vstoneofficial/lightrover_description.git
# Nav2 で自律走行する場合
git clone -b jazzy https://github.com/vstoneofficial/lightrover_ros2.git

cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

## 使い方

### RViz でモデルを表示する

```bash
ros2 launch lightrover_description lightrover_view.launch.py
```

### Gazebo でシミュレーションする

```bash
ros2 launch lightrover_description gazebo.launch.py
```

| 引数 | 既定値 | 説明 |
|---|---|---|
| `world` | `lightrover_sample` | `empty` / `lightrover_sample` / `lightrover_sample_2` または SDF のパス |
| `gui` | `true` | Gazebo の画面を表示する |
| `rviz` | `false` | RViz2 を起動する (odom 固定でモデル・LiDAR・オドメトリを表示) |
| `x` `y` `yaw` | `0.0` | スポーン位置 |

シミュレータは実機と同じトピックを使います。

| トピック | 型 | 内容 |
|---|---|---|
| `/rover_twist` | `geometry_msgs/Twist` | 速度指令 (実機の pos_controller と同じ) |
| `/rover_twist_stamped` | `geometry_msgs/TwistStamped` | 速度指令 (mouse_teleop など Stamped で出すツール用) |
| `/odom` | `nav_msgs/Odometry` | 車輪オドメトリ (TF `odom -> base_footprint` も出力) |
| `/scan` | `sensor_msgs/LaserScan` | LiDAR (frame `laser_frame`, 360°, 0.1〜8.0 m, 10 Hz) |
| `/clock` | `rosgraph_msgs/Clock` | シミュレーション時刻 (`use_sim_time:=true` で使用) |

### マウス(タッチパッド)で操作する

シミュレータを起動してから、別の端末で起動します。

```bash
ros2 launch lightrover_description mouse_teleop.launch.py
```

表示されたウィンドウ上でドラッグすると走行し、ボタンを離すと停止します。
上下のドラッグで前後進、左右のドラッグで旋回します。
`scale:=0.2` のように、ウィンドウ端までドラッグしたときの速度 (m/s, rad/s) を変えられます (既定 0.3)。

Jazzy の mouse_teleop は `TwistStamped` を出すため、`/rover_twist_stamped` で受けています。

キーボードで走らせる場合:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=rover_twist
```

### SLAM で地図を作る

slam_toolbox で地図を作ります。RViz2 の表示設定は lightrover_ros2 (jazzy) の `lightrover_navigation` と共通です。

```bash
ros2 launch lightrover_description gazebo_slam.launch.py
# 別の端末でロボットを動かす
ros2 launch lightrover_description mouse_teleop.launch.py
```

slam_toolbox の設定は `config/slam_toolbox_sim.yaml` です。
`lightrover_navigation` の実機設定を元に、地図の更新頻度を上げています。

| 項目 | 実機設定 | シミュレータ設定 |
|---|---|---|
| `minimum_travel_distance` | 1.0 m | 0.1 m |
| `minimum_travel_heading` | 1.0 rad (約57°) | 0.1 rad (約6°) |
| `max_laser_range` | 30.0 m | 8.0 m |

slam_toolbox は、ロボットがこの距離か角度だけ動くまで新しいスキャンを地図に反映しません。
実機設定のままだと 1 m 進むか約57°回るまで地図が変わりません。
実機と同じ設定で試す場合は、次のように指定します。

```bash
ros2 launch lightrover_description gazebo_slam.launch.py \
  slam_params_file:=$(ros2 pkg prefix lightrover_navigation)/share/lightrover_navigation/config/mapper_params_online_async.yaml
```

地図ができたら、さらに別の端末で保存します。

```bash
ros2 run nav2_map_server map_saver_cli -f ~/lightrover_map --ros-args -p use_sim_time:=true
```

保存した地図は、Nav2 で使えます。

```bash
ros2 launch lightrover_description gazebo_nav.launch.py map:=$HOME/lightrover_map.yaml
```

### Nav2 で自律走行する

lightrover_ros2 (jazzy) の `lightrover_navigation` を、シミュレータ用の設定
(`use_sim_time:=true`、実機用ノードなし) で起動します。
ワールドに対応した地図 (`maps/`) と初期位置は自動で設定されます。

```bash
ros2 launch lightrover_description gazebo_nav.launch.py
# 迷路のワールド
ros2 launch lightrover_description gazebo_nav.launch.py world:=lightrover_sample_2
```

RViz2 の「Nav2 Goal」でゴールを指定すると走行します。
別の地図や Nav2 パラメータを使う場合は `map:=` `params_file:=` を指定してください。

同梱の地図はワールドの SDF から `scripts/world_to_map.py` で生成したものです。
ワールドを変更した場合は、次のように作り直せます。

```bash
ros2 run lightrover_description world_to_map.py <world.sdf> <出力先/名前>
```

## ROS 1 版・humble ブランチからの変更点

- Gazebo Classic の ROS 1 プラグインを、Gazebo Harmonic 用 (`gz_ros2_control`、`gpu_lidar`) に置き換えた
- 質量を実機に合わせた
  - 車輪: 2.0 kg → 0.0135 kg (×2)
  - 本体 (base_link): 0.002 kg → 0.484 kg
  - キャスター: 0.05 kg → 0.005 kg
  - 合計約 0.516 kg (実機相当)
  - ROS 1 版は Gazebo Classic (ODE) での動作安定化のため、質量と重心を実機から変えていた。Gazebo Harmonic (DART) では実機の質量のまま安定して走行する
- 車輪の慣性テンソルの向きを修正した (回転軸 y に軸方向の値が乗るように)
- 速度制御を `diff_drive_controller` に変更し、`/rover_twist` で受けて `/odom` を出すようにした
- ワールドを SDF 1.9 に変換した。`clearpath_playpen.world` は Gazebo Classic のモデルデータベースに依存するため削除
- RViz 設定を RViz2 形式に作り直した

## 既知の注意点

- その場旋回では、オドメトリの旋回角が実際より 2% 程度小さく出ます。直進ではほぼ一致します
- LiDAR の取り付け位置は URDF (メッシュ) に合わせて base_link から x = -0.07 m です。
  lightrover_ros2 の実機用 launch の static TF (x = -0.042 m) とは異なります
- GPU のない PC では LiDAR の描画が重く、実時間より遅く進むことがあります
