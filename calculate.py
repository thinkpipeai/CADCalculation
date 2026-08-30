import ezdxf
from shapely.geometry import Polygon, Point
import math

INCH_TO_METER = 0.0254
SQ_INCH_TO_SQ_FT = 1 / 144.0
SQ_FT_TO_SQ_M = 0.092903
CEILING_HEIGHT_INCHES = 96  # 8 英尺层高
PAINT_COVERAGE_SQFT_PER_GAL = 350

# 默认窗户规格配置 (单位: 英寸)
DEFAULT_WIN_WIDTH = 36   # 3 英尺宽
DEFAULT_WIN_HEIGHT = 60  # 5 英尺高
WIN_MOLDING_WASTE_RATE = 1.10 # 10% 窗套线切割损耗

def parse_and_calculate():
    try:
        doc = ezdxf.readfile("westwood_proposed_plan.dxf")
        msp = doc.modelspace()
    except IOError:
        print("❌ 找不到 DXF 文件，请先运行生成脚本！")
        return

    layer_mapping = {
        'A-FLOOR-GARAGE': '车库耐磨环氧地面',
        'A-FLOOR-LIVING': '实木地板 / 瓷砖'
    }
    
    room_labels = [t for t in msp.query('TEXT[layer=="A-ROOM-NAME"]')]
    windows = [w for w in msp.query('INSERT[layer=="A-WINDOW"]')]

    print("================ 综合工程量与采购清单 (含窗套线) ================\n")

    total_window_molding_ft = 0.0

    for layer, material_name in layer_mapping.items():
        polys = [p for p in msp.query(f'LWPOLYLINE[layer=="{layer}"]') if p.closed]
        
        for poly in polys:
            points = [(p[0], p[1]) for p in poly.get_points()]
            shape = Polygon(points)
            
            # 使用 12 英寸缓冲区覆盖外墙上的窗户中心点
            buffered_shape = shape.buffer(12.0)

            # 匹配房间名称
            room_name = "未命名区域"
            for t in room_labels:
                if shape.contains(Point(t.dxf.insert.x, t.dxf.insert.y)):
                    room_name = t.dxf.text
                    break

            # 1. 基础尺寸
            area_sqft = shape.area * SQ_INCH_TO_SQ_FT
            perimeter_ft = shape.length / 12.0

            # 2. 踢脚线 (8% 损耗)
            baseboard_ft = math.ceil(perimeter_ft * 1.08)

            # 3. 窗户与窗套线算法 (Window Molding)
            room_windows = [w for w in windows if buffered_shape.contains(Point(w.dxf.insert.x, w.dxf.insert.y))]
            win_count = len(room_windows)
            
            # 单窗周长 (英寸) -> 换算为英尺
            single_win_molding_ft = (2 * (DEFAULT_WIN_WIDTH + DEFAULT_WIN_HEIGHT)) / 12.0
            room_win_molding_ft = win_count * single_win_molding_ft * WIN_MOLDING_WASTE_RATE
            total_window_molding_ft += room_win_molding_ft

            # 输出明细
            print(f"📍【{room_name}】")
            print(f"  ├─ 地面净面积:     {area_sqft:.1f} sq ft")
            print(f"  ├─ 踢脚线需用量:   {baseboard_ft} ft")
            print(f"  ├─ 窗户数量:       {win_count} 扇")
            print(f"  └─ 窗套线采购需求: {math.ceil(room_win_molding_ft)} ft (含10%损耗)\n")

    print("-------------------- 采购总量汇总 --------------------")
    print(f" Total 全屋窗套线条总需求: {math.ceil(total_window_molding_ft)} ft")
    print("==========================================================")

if __name__ == "__main__":
    parse_and_calculate()
