import ezdxf
from shapely.geometry import Polygon, Point
import math

# 常量配置 (美制/公制换算与施工参数)
INCH_TO_METER = 0.0254
SQ_INCH_TO_SQ_FT = 1 / 144.0
SQ_FT_TO_SQ_M = 0.092903
CEILING_HEIGHT_INCHES = 96  # 标准层高 8 英尺 (96 英寸)
PAINT_COVERAGE_SQFT_PER_GAL = 350  # 1 加仑油漆约刷 350 平方英尺墙面

def parse_and_calculate():
    try:
        doc = ezdxf.readfile("westwood_proposed_plan.dxf")
        msp = doc.modelspace()
    except IOError:
        print("❌ 找不到 DXF 文件，请先运行生成脚本！")
        return

    # 1. 提取所有图层要素
    layer_mapping = {
        'A-FLOOR-GARAGE': '车库耐磨环氧地面',
        'A-FLOOR-LIVING': '实木地板 / 瓷砖',
        'A-FLOOR-UNFINISHED': '防潮水泥地面'
    }
    
    room_labels = [t for t in msp.query('TEXT[layer=="A-ROOM-NAME"]')]
    equipments = [e for e in msp.query('INSERT[layer=="E-EQUIPMENT"]')]

    print("================ 综合工程量与采购清单 (BOM) ================\n")

    total_living_sqft = 0.0
    total_paint_sqft = 0.0

    # 2. 遍历所有地面封闭区域
    for layer, material_name in layer_mapping.items():
        polys = [p for p in msp.query(f'LWPOLYLINE[layer=="{layer}"]') if p.closed]
        
        for poly in polys:
            points = [(p[0], p[1]) for p in poly.get_points()]
            shape = Polygon(points)

            # 匹配房间名称
            room_name = "未命名区域"
            for t in room_labels:
                if shape.contains(Point(t.dxf.insert.x, t.dxf.insert.y)):
                    room_name = t.dxf.text
                    break

            # --- 算法 1: 基础几何尺寸 ---
            area_sq_inch = shape.area
            perimeter_inch = shape.length
            
            area_sqft = area_sq_inch * SQ_INCH_TO_SQ_FT
            area_sqm = area_sqft * SQ_FT_TO_SQ_M
            perimeter_ft = perimeter_inch / 12.0
            perimeter_m = perimeter_inch * INCH_TO_METER

            # --- 算法 2: 踢脚线 / 墙角线计算 (考虑 8% 切割损耗) ---
            baseboard_ft = math.ceil(perimeter_ft * 1.08)

            # --- 算法 3: 墙面面积与乳胶漆用量估算 (周长 x 层高) ---
            wall_area_sqft = perimeter_ft * (CEILING_HEIGHT_INCHES / 12.0)
            paint_gallons = math.ceil((wall_area_sqft * 2) / PAINT_COVERAGE_SQFT_PER_GAL) # 默认刷两遍

            # --- 算法 4: 设备/家具计数 ---
            equip_count = sum(1 for e in equipments if shape.contains(Point(e.dxf.insert.x, e.dxf.insert.y)))

            # 汇总数据
            if layer == 'A-FLOOR-LIVING':
                total_living_sqft += area_sqft
            total_paint_sqft += wall_area_sqft

            # 输出单个房间明细
            print(f"📍【{room_name}】(图层: {layer})")
            print(f"  ├─ 地面净面积:   {area_sqft:.1f} sq ft ({area_sqm:.2f} m²)")
            print(f"  ├─ 适用材料:     {material_name} (需备货: {area_sqft * 1.05:.1f} sq ft, 含5%损耗)")
            print(f"  ├─ 周长/踢脚线:  {perimeter_ft:.1f} ft ({perimeter_m:.2f} m) ➔ 建议采购: {baseboard_ft} ft")
            print(f"  ├─ 估算墙面面积: {wall_area_sqft:.1f} sq ft")
            print(f"  ├─ 墙漆需求量:   约 {paint_gallons} 加仑 (两遍底漆+面漆)")
            print(f"  └─ 包含设备数:   {equip_count} 台/件\n")

    # 3. 总体采购汇总
    print("-------------------- 采购总量汇总汇总 --------------------")
    print(f" Total 居住区地板总需求: {math.ceil(total_living_sqft * 1.05)} sq ft (含损耗)")
    print(f" Total 全屋墙漆总桶数:   {math.ceil((total_paint_sqft * 2) / PAINT_COVERAGE_SQFT_PER_GAL)} 加仑")
    print("==========================================================")

if __name__ == "__main__":
    parse_and_calculate()
