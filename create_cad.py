import ezdxf

def generate_westwood_plan():
    # 创建 DXF 文档，设置单位为英寸 (1 = Inches)
    doc = ezdxf.new('R2010')
    doc.header['$INSUNITS'] = 1
    msp = doc.modelspace()

    # 1. 创建符合算量逻辑的规范图层
    doc.layers.add("A-FLOOR-GARAGE", color=1)      # 车库地面 (红色)
    doc.layers.add("A-FLOOR-LIVING", color=3)      # 居住区地面 (绿色)
    doc.layers.add("A-FLOOR-UNFINISHED", color=5)  # 未完工/地下室地面 (蓝色)
    doc.layers.add("A-ROOM-NAME", color=2)         # 房间标注文字 (黄色)
    doc.layers.add("E-EQUIPMENT", color=6)         # 设备/热水器等图块 (粉色)

    # 2. 转换图纸主要区域坐标 (尺寸依据图纸标注: 24'-0"=288", 18'-0"=216", 17'-11"=215" 等)
    
    # 区域 A: 2-Car Garage (24'-0" x 18'-0")
    garage_polygon = [(0, 0), (288, 0), (288, 216), (0, 216)]
    msp.add_lwpolyline(garage_polygon, dxfattribs={'layer': 'A-FLOOR-GARAGE', 'closed': True})

    # 区域 B: Main Living / Kitchen / Dining (上方大跨度区域 approx 40'-0" x 17'-11")
    living_polygon = [(0, 216), (480, 216), (480, 431), (0, 431)]
    msp.add_lwpolyline(living_polygon, dxfattribs={'layer': 'A-FLOOR-LIVING', 'closed': True})

    # 区域 C: Entertainment Room / Basement Space (右下区域)
    ent_polygon = [(288, 0), (480, 0), (480, 216), (288, 216)]
    msp.add_lwpolyline(ent_polygon, dxfattribs={'layer': 'A-FLOOR-LIVING', 'closed': True})

    # 3. 写入房间标识文字 (确保放置在各封闭多边形内部，便于 Shapely 归属计算)
    room_annotations = [
        ("2-CAR GARAGE", (100, 100), "A-ROOM-NAME"),
        ("LIVING / DINING AREA", (80, 320), "A-ROOM-NAME"),
        ("KITCHEN", (350, 320), "A-ROOM-NAME"),
        ("BATH", (430, 250), "A-ROOM-NAME"),
        ("ENTERTAINMENT ROOM", (340, 100), "A-ROOM-NAME"),
        ("BASEMENT", (50, 250), "A-ROOM-NAME"),
    ]

    for name, pos, layer in room_annotations:
        text = msp.add_text(name, dxfattribs={'layer': layer, 'height': 10})
        text.set_placement(pos)

    # 4. 模拟图纸中的关键设备 (如 Water Heater / HVAC)
    heater_block = doc.blocks.new(name="WATER_HEATER")
    heater_block.add_circle((0, 0), radius=12) # 24英寸直径热水器
    
    # 在 Heater Closet 位置放置设备
    msp.add_blockref("WATER_HEATER", (270, 230), dxfattribs={'layer': 'E-EQUIPMENT'})

    doc.saveas("westwood_proposed_plan.dxf")
    print("✅ 已成功按图纸结构生成 DXF: westwood_proposed_plan.dxf")

if __name__ == "__main__":
    generate_westwood_plan()
