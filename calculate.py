import ezdxf
from shapely.geometry import Polygon, Point
import math

def parse_and_calculate():
    # 1. 加载 CAD 图纸
    try:
        doc = ezdxf.readfile("test_floor_plan.dxf")
        msp = doc.modelspace()
    except IOError:
        print("❌ 找不到 CAD 文件，请先运行生成脚本！")
        return

    # 2. 提取需要的数据
    floor_polys = [poly for poly in msp.query('LWPOLYLINE[layer=="A-FLOOR"]') if poly.closed]
    texts = [text for text in msp.query('TEXT[layer=="A-ROOM-NAME"]')]
    sockets = [insert for insert in msp.query('INSERT[layer=="E-SOCKET"]')]

    # 3. 耗材计算算法遍历
    for poly in floor_polys:
        # 提取多边形顶点并转换为 Shapely 的 Polygon 对象
        points = [(p[0], p[1]) for p in poly.get_points()]
        polygon = Polygon(points)

        # --- 算法 1: 面积计算 (平方毫米转平方米) ---
        area_m2 = polygon.area / 1_000_000

        # --- 算法 2: 空间归属判断 (文字是否在多边形内) ---
        room_name = "未命名区域"
        for t in texts:
            pos = Point(t.dxf.insert.x, t.dxf.insert.y)
            if polygon.contains(pos):
                room_name = t.dxf.text
                break

        # --- 算法 3: 统计该空间内的图块数量 ---
        socket_count = sum(1 for s in sockets if polygon.contains(Point(s.dxf.insert.x, s.dxf.insert.y)))

        # --- 算法 4: 耗材采购算法 (引入行业标准损耗率) ---
        tile_waste_rate = 1.05  # 瓷砖通常预留 5% 切割损耗
        tile_area_needed = area_m2 * tile_waste_rate
        # 假设使用 600mm x 600mm 瓷砖 (单块面积 0.36 m2)
        tile_600_count = math.ceil(tile_area_needed / 0.36) 

        # 输出报表
        print(f"====== {room_name} 算量清单 ======")
        print(f"净面积:\t\t{area_m2:.2f} m²")
        print(f"插座数量:\t{socket_count} 个")
        print(f"地砖采购面积:\t{tile_area_needed:.2f} m² (含5%损耗)")
        print(f"600x600砖块数:\t{tile_600_count} 块 (向上取整)\n")

if __name__ == "__main__":
    parse_and_calculate()
