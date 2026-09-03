import ezdxf
from shapely.geometry import Polygon, Point

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
            })
    return rooms


def parse_and_calculate(dxf_path="test_floor_plan.dxf"):
    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
    except IOError:
        print("❌ 找不到 CAD 文件，请先运行 create_cad.py 生成图纸！")
        return

    rooms = _extract_rooms(msp)

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
        print()


if __name__ == "__main__":
    parse_and_calculate()
