import ezdxf

def generate_test_cad():
    # 创建一个新的 DXF 文档
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    # 1. 创建规范的图层
    doc.layers.add("A-FLOOR", color=3)       # 地板层，绿色
    doc.layers.add("A-ROOM-NAME", color=2)   # 房间文字层，黄色
    doc.layers.add("E-SOCKET", color=1)      # 插座图块层，红色

    # 2. 画一个闭合的房间多边形 (单位: mm，4000mm x 5000mm)
    points = [(0, 0), (4000, 0), (4000, 5000), (0, 5000)]
    msp.add_lwpolyline(points, dxfattribs={'layer': 'A-FLOOR', 'closed': True})

    # 3. 添加房间名称文字 (放置在坐标 X:1500, Y:2500 的位置)
    text = msp.add_text("Master Bedroom", dxfattribs={'layer': 'A-ROOM-NAME', 'height': 200})
    text.set_placement((1500, 2500))

    # 4. 定义一个插座图块 (在块里画个圆圈代表插座)
    socket_block = doc.blocks.new(name="SOCKET_86")
    socket_block.add_circle((0, 0), radius=50)

    # 5. 在房间内插入 3 个插座图块
    msp.add_blockref("SOCKET_86", (500, 500), dxfattribs={'layer': 'E-SOCKET'})
    msp.add_blockref("SOCKET_86", (3500, 500), dxfattribs={'layer': 'E-SOCKET'})
    msp.add_blockref("SOCKET_86", (2000, 4800), dxfattribs={'layer': 'E-SOCKET'})

    # 保存文件
    doc.saveas("test_floor_plan.dxf")
    print("✅ 成功生成测试图纸: test_floor_plan.dxf")

if __name__ == "__main__":
    generate_test_cad()
