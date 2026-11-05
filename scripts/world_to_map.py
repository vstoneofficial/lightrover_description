#!/usr/bin/env python3
"""ワールドSDFの静的な box / cylinder から Nav2 用の占有格子地図 (pgm + yaml) を作る.

LiDAR の高さ (地面から約0.11 m) を横切る物体だけを障害物として描く。
同梱の maps/*.yaml はこのスクリプトで生成した。

例:
  python3 world_to_map.py worlds/lightrover_sample.sdf maps/lightrover_sample
"""

import argparse
import math
import xml.etree.ElementTree as ET


def pose_of(elem):
    text = elem.findtext('pose') if elem is not None else None
    v = [float(x) for x in (text or '0 0 0 0 0 0').split()]
    return v[0], v[1], v[2], v[5]


def compose(a, b):
    ax, ay, az, ayaw = a
    bx, by, bz, byaw = b
    c, s = math.cos(ayaw), math.sin(ayaw)
    return ax + c * bx - s * by, ay + s * bx + c * by, az + bz, ayaw + byaw


def shapes(sdf_path, scan_z):
    world = ET.parse(sdf_path).getroot().find('world')
    for model in world.findall('model'):
        if model.get('name') == 'ground_plane':
            continue
        mp = pose_of(model)
        for link in model.findall('link'):
            lp = compose(mp, pose_of(link))
            for col in link.findall('collision'):
                x, y, z, yaw = compose(lp, pose_of(col))
                geom = col.find('geometry')
                box, cyl = geom.find('box'), geom.find('cylinder')
                if box is not None:
                    sx, sy, sz = [float(v) for v in box.findtext('size').split()]
                    if abs(scan_z - z) <= sz / 2:
                        yield ('box', x, y, yaw, sx, sy)
                elif cyl is not None:
                    r, length = float(cyl.findtext('radius')), float(cyl.findtext('length'))
                    if abs(scan_z - z) <= length / 2:
                        yield ('cyl', x, y, r)


def occupied(shape, px, py):
    if shape[0] == 'box':
        _, x, y, yaw, sx, sy = shape
        dx, dy = px - x, py - y
        c, s = math.cos(-yaw), math.sin(-yaw)
        lx, ly = c * dx - s * dy, s * dx + c * dy
        return abs(lx) <= sx / 2 and abs(ly) <= sy / 2
    _, x, y, r = shape
    return math.hypot(px - x, py - y) <= r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('world')
    ap.add_argument('out_prefix')
    ap.add_argument('--resolution', type=float, default=0.05)
    ap.add_argument('--margin', type=float, default=2.0)
    ap.add_argument('--scan-z', type=float, default=0.11)
    args = ap.parse_args()

    objs = list(shapes(args.world, args.scan_z))
    # 物体の外接範囲 + 余白を地図にする
    xs, ys = [0.0], [0.0]
    for o in objs:
        if o[0] == 'box':
            _, x, y, yaw, sx, sy = o
            c, s = math.cos(yaw), math.sin(yaw)
            for lx, ly in ((sx / 2, sy / 2), (sx / 2, -sy / 2), (-sx / 2, sy / 2), (-sx / 2, -sy / 2)):
                xs.append(x + c * lx - s * ly)
                ys.append(y + s * lx + c * ly)
        else:
            xs += [o[1] - o[3], o[1] + o[3]]
            ys += [o[2] - o[3], o[2] + o[3]]
    res = args.resolution
    x0 = math.floor((min(xs) - args.margin) / res) * res
    y0 = math.floor((min(ys) - args.margin) / res) * res
    w = int(math.ceil((max(xs) + args.margin - x0) / res))
    h = int(math.ceil((max(ys) + args.margin - y0) / res))

    rows = []
    for j in range(h - 1, -1, -1):  # pgm は上(=+y)の行から
        py = y0 + (j + 0.5) * res
        row = bytearray()
        for i in range(w):
            px = x0 + (i + 0.5) * res
            row.append(0 if any(occupied(o, px, py) for o in objs) else 254)
        rows.append(bytes(row))

    name = args.out_prefix.rsplit('/', 1)[-1]
    with open(args.out_prefix + '.pgm', 'wb') as f:
        f.write(f'P5\n{w} {h}\n255\n'.encode())
        for r in rows:
            f.write(r)
    with open(args.out_prefix + '.yaml', 'w') as f:
        f.write(f'image: {name}.pgm\nmode: trinary\nresolution: {res:.3f}\n'
                f'origin: [{x0:.3f}, {y0:.3f}, 0.0]\nnegate: 0\n'
                f'occupied_thresh: 0.65\nfree_thresh: 0.25\n')
    print(f'{args.out_prefix}: {w}x{h} cells, {len(objs)} obstacles, origin ({x0:.2f}, {y0:.2f})')


if __name__ == '__main__':
    main()
