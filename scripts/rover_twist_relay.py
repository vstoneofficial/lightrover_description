#!/usr/bin/env python3
"""速度指令を diff_drive_controller に中継する.

  /rover_twist          (geometry_msgs/Twist)        実機と同じ指令 (Nav2, ゲームパッド, キーボード)
  /rover_twist_stamped  (geometry_msgs/TwistStamped) mouse_teleop など Stamped で出すツール用
        ↓
  /cmd_vel_stamped      (geometry_msgs/TwistStamped) diff_drive_controller

Jazzy の diff_drive_controller は TwistStamped しか受け付けないため、
受け取った指令にシミュレーション時刻のタイムスタンプを付けて publish する。
実機の pos_controller は最後に受け取った目標速度を保持し続けるので、
それに合わせて最新の指令を一定周期で送り続ける。
"""

import rclpy
from geometry_msgs.msg import Twist, TwistStamped
from rclpy.node import Node


class RoverTwistRelay(Node):

    def __init__(self):
        super().__init__('rover_twist_relay')
        self.publish_rate = float(self.declare_parameter('publish_rate', 30.0).value)
        self.frame_id = str(self.declare_parameter('frame_id', 'base_footprint').value)
        in_topic = str(self.declare_parameter('input_topic', '/rover_twist').value)
        in_stamped_topic = str(
            self.declare_parameter('input_stamped_topic', '/rover_twist_stamped').value)
        out_topic = str(self.declare_parameter('output_topic', '/cmd_vel_stamped').value)

        self.last_twist = Twist()
        self.pub = self.create_publisher(TwistStamped, out_topic, 10)
        self.sub = self.create_subscription(Twist, in_topic, self.on_twist, 10)
        self.sub_stamped = self.create_subscription(
            TwistStamped, in_stamped_topic, self.on_twist_stamped, 10)
        self.timer = self.create_timer(1.0 / self.publish_rate, self.on_timer)
        self.get_logger().info(
            f'relay {in_topic} (Twist), {in_stamped_topic} (TwistStamped) '
            f'-> {out_topic} (TwistStamped)')

    def on_twist(self, msg: Twist):
        self.last_twist = msg

    def on_twist_stamped(self, msg: TwistStamped):
        self.last_twist = msg.twist

    def on_timer(self):
        out = TwistStamped()
        out.header.stamp = self.get_clock().now().to_msg()
        out.header.frame_id = self.frame_id
        out.twist = self.last_twist
        self.pub.publish(out)


def main():
    rclpy.init()
    node = RoverTwistRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
