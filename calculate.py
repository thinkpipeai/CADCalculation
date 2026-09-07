import ezdxf
from shapely.geometry import Polygon, Point, LineString

FLOOR_LAYERS = ("A-FLOOR", "A-FLOOR-SHOWER", "A-FLOOR-BATH-DRY")


def _polyline_to_polygon(poly):
    points = [(p[0], p[1]) for p in poly.get_points()]
    return Polygon(points)


def _mm2m(value_mm):
    return value_mm / 1000


def _mm2m2(area_mm2):
    return area_mm2 / 1_000_000


def _rect_from_polygon(polygon):
    minx, miny, maxx, maxy = polygon.bounds
    return maxx - minx, maxy - miny


def _resolve_room_name(polygon, texts):
    for text in texts:
        label = text.dxf.text.strip()
        if "户型平面图" in label or label in ("吊柜", "地柜"):
            continue
        pos = Point(text.dxf.insert.x, text.dxf.insert.y)
        if polygon.contains(pos):
            return label
    return "未命名区域"


def _extract_rooms(msp):
    texts = list(msp.query('TEXT[layer=="A-ROOM-NAME"]'))
    rooms = []
    for layer in FLOOR_LAYERS:
        for poly in msp.query(f'LWPOLYLINE[layer=="{layer}"]'):
            if not poly.closed:
                continue
            polygon = _polyline_to_polygon(poly)
            rooms.append({
                "name": _resolve_room_name(polygon, texts),
                "layer": layer,
                "polygon": polygon,
                "doors": [],
                "windows": [],
            })
    return rooms


def _extract_doors(msp):
    """提取门：弧线门（半径=门宽）+ 推拉门（双线间距）"""
    doors = []

    for arc in msp.query('ARC[layer=="A-DOOR"]'):
        cx, cy = arc.dxf.center.x, arc.dxf.center.y
        doors.append({
            "type": "平开门",
            "width_mm": arc.dxf.radius,
            "position": (cx, cy),
        })

    lines = [
        LineString([(ln.dxf.start.x, ln.dxf.start.y), (ln.dxf.end.x, ln.dxf.end.y)])
        for ln in msp.query('LINE[layer=="A-DOOR"]')
    ]
    used = set()
    for i, line_a in enumerate(lines):
        if i in used:
            continue
        for j, line_b in enumerate(lines[i + 1:], start=i + 1):
            if j in used:
                continue
            if line_a.distance(line_b) > 100:
                continue
            length_a, length_b = line_a.length, line_b.length
            if abs(length_a - length_b) > 50:
                continue
            mid = line_a.interpolate(0.5, normalized=True)
            doors.append({
                "type": "推拉门",
                "width_mm": max(length_a, length_b),
                "position": (mid.x, mid.y),
            })
            used.update({i, j})
            break

    return doors


def _extract_windows(msp):
    """提取窗洞：聚类 A-WINDOW 线段，取最长边为洞口宽度"""
    window_lines = []
    for ln in msp.query('LINE[layer=="A-WINDOW"]'):
        line = LineString([
            (ln.dxf.start.x, ln.dxf.start.y),
            (ln.dxf.end.x, ln.dxf.end.y),
        ])
        if line.length >= 800:
            window_lines.append(line)

    windows = []
    used = set()
    for i, line_a in enumerate(window_lines):
        if i in used:
            continue
        group = [line_a]
        mid_a = line_a.interpolate(0.5, normalized=True)
        for j, line_b in enumerate(window_lines):
            if j == i or j in used:
                continue
            mid_b = line_b.interpolate(0.5, normalized=True)
            if mid_a.distance(Point(mid_b.x, mid_b.y)) > 200:
                continue
            group.append(line_b)
            used.add(j)
        used.add(i)
        width_mm = max(seg.length for seg in group)
        mid = line_a.interpolate(0.5, normalized=True)
        windows.append({
            "width_mm": width_mm,
            "position": (mid.x, mid.y),
        })

    return windows


def _assign_entities(rooms, entities, attr):
    for entity in entities:
        pt = Point(entity["position"])
        for room in rooms:
            if room["polygon"].contains(pt):
                room[attr].append(entity)
                break


def parse_and_calculate(dxf_path="test_floor_plan.dxf"):
    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
    except IOError:
        print("❌ 找不到 CAD 文件，请先运行 create_cad.py 生成图纸！")
        return

    rooms = _extract_rooms(msp)
    doors = _extract_doors(msp)
    windows = _extract_windows(msp)

    _assign_entities(rooms, doors, "doors")
    _assign_entities(rooms, windows, "windows")

    print(f"📐 图纸解析完成: {dxf_path}")
    print(f"   共识别 {len(rooms)} 个房间区域\n")

    for room in sorted(rooms, key=lambda r: r["name"]):
        polygon = room["polygon"]
        width_mm, depth_mm = _rect_from_polygon(polygon)
        print(f"====== {room['name']} ======")
        print(f"图层:\t\t{room['layer']}")
        print(f"净面积:\t\t{_mm2m2(polygon.area):.2f} m²")
        print(f"周长:\t\t{_mm2m(polygon.length):.2f} m")
        print(f"包络尺寸:\t{_mm2m(width_mm):.2f} m × {_mm2m(depth_mm):.2f} m (宽×深)")

        if room["doors"]:
            print(f"门 ({len(room['doors'])} 樘):")
            for i, door in enumerate(room["doors"], 1):
                print(f"  [{i}] {door['type']}  宽度 {_mm2m(door['width_mm']):.2f} m")

        if room["windows"]:
            print(f"窗 ({len(room['windows'])} 扇):")
            for i, win in enumerate(room["windows"], 1):
                print(f"  [{i}] 洞口宽度 {_mm2m(win['width_mm']):.2f} m")

        print()


if __name__ == "__main__":
    parse_and_calculate()
