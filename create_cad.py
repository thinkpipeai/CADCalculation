import ezdxf
import math

# 图纸单位：毫米 (mm)，与 calculate.py 算量逻辑一致

WALL_THICK = 200       # 墙体厚度
DOOR_WIDTH = 900       # 门洞宽度
WINDOW_WIDTH = 1500    # 窗洞宽度
WINDOW_SILL = 900      # 窗台高度（示意用）


def _add_layers(doc):
    """创建规范图层"""
    layers = {
        "A-WALL": 7,              # 墙体
        "A-FLOOR": 3,             # 房间地面（算量用）
        "A-FLOOR-SHOWER": 4,    # 淋浴区地面
        "A-FLOOR-BATH-DRY": 5,   # 卫生间干区地面
        "A-ROOM-NAME": 2,        # 房间标注
        "A-DOOR": 1,             # 门
        "A-WINDOW": 6,           # 窗
        "A-CABINET-WALL": 30,    # 吊柜
        "A-CABINET-BASE": 40,    # 地柜
        "E-SOCKET": 8,           # 插座
    }
    for name, color in layers.items():
        doc.layers.add(name, color=color)


def _rect(msp, x0, y0, x1, y1, layer, closed=True):
    """绘制矩形多段线"""
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return msp.add_lwpolyline(pts, dxfattribs={"layer": layer, "closed": closed})


def _wall(msp, x0, y0, x1, y1):
    """绘制墙体线段"""
    msp.add_line((x0, y0), (x1, y1), dxfattribs={"layer": "A-WALL"})


def _wall_rect(msp, x0, y0, x1, y1):
    """绘制矩形外墙（双线效果：外轮廓 + 内轮廓）"""
    t = WALL_THICK
    # 外轮廓
    _rect(msp, x0, y0, x1, y1, "A-WALL")
    # 内轮廓
    _rect(msp, x0 + t, y0 + t, x1 - t, y1 - t, "A-WALL")


def _door(msp, x, y, width, angle=0):
    """
    绘制门（门洞弧线示意）
    angle: 0=门轴在左向右开, 90=门轴在下向上开, 180=门轴在右向左开, 270=门轴在上向下开
    """
    msp.add_arc(
        center=(x, y),
        radius=width,
        start_angle=angle,
        end_angle=angle + 90,
        dxfattribs={"layer": "A-DOOR"},
    )
    # 门扇示意线
    rad = math.radians(angle)
    msp.add_line(
        (x, y),
        (x + width * math.cos(rad), y + width * math.sin(rad)),
        dxfattribs={"layer": "A-DOOR"},
    )


def _window(msp, x0, y0, x1, y1):
    """绘制窗户（双线 + 中线）"""
    msp.add_line((x0, y0), (x1, y1), dxfattribs={"layer": "A-WINDOW"})
    # 窗框平行线
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length == 0:
        return
    nx, ny = -dy / length * 80, dx / length * 80
    msp.add_line((x0 + nx, y0 + ny), (x1 + nx, y1 + ny), dxfattribs={"layer": "A-WINDOW"})
    msp.add_line((x0 - nx, y0 - ny), (x1 - nx, y1 - ny), dxfattribs={"layer": "A-WINDOW"})
    # 玻璃中线
    mx0, my0 = (x0 + x1) / 2, (y0 + y1) / 2
    msp.add_line((mx0 + nx, my0 + ny), (mx0 - nx, my0 - ny), dxfattribs={"layer": "A-WINDOW"})


def _cabinet_base(msp, x0, y0, x1, y1):
    """地柜：贴地矩形 + 台面线"""
    _rect(msp, x0, y0, x1, y1, "A-CABINET-BASE")
    # 台面示意
    msp.add_line((x0, y1), (x1, y1), dxfattribs={"layer": "A-CABINET-BASE"})


def _cabinet_wall(msp, x0, y0, x1, y1):
    """吊柜：贴墙矩形（虚线边框示意）"""
    _rect(msp, x0, y0, x1, y1, "A-CABINET-WALL")
    # 柜门分隔线
    mid_x = (x0 + x1) / 2
    msp.add_line((mid_x, y0), (mid_x, y1), dxfattribs={"layer": "A-CABINET-WALL"})


def _room_label(msp, text, x, y, height=250):
    t = msp.add_text(text, dxfattribs={"layer": "A-ROOM-NAME", "height": height})
    t.set_placement((x, y))


def _socket_block(doc, msp, x, y):
    if "SOCKET_86" not in doc.blocks:
        blk = doc.blocks.new("SOCKET_86")
        blk.add_circle((0, 0), radius=40)
        blk.add_line((-25, 0), (25, 0))
        blk.add_line((0, -25), (0, 25))
    msp.add_blockref("SOCKET_86", (x, y), dxfattribs={"layer": "E-SOCKET"})


def generate_2b1b_plan():
    """
    生成横平竖直的 2室1厅1卫 (2B1B) 户型平面图

    户型尺寸：9000mm × 7000mm（约 9m × 7m，建筑面积约 63m²）
    布局：
      上层 - 客厅 + 厨房（含吊柜、地柜）
      下层 - 主卧 + 卫生间（淋浴区/干区）+ 次卧
    """
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 4  # 4 = Millimeters
    msp = doc.modelspace()
    _add_layers(doc)

    t = WALL_THICK
    W, H = 9000, 7000          # 外轮廓
    MID_Y = 3500                 # 上下分区
    SPLIT_X_LIVING = 5500        # 客厅/厨房分界
    SPLIT_X_LOWER = 3500         # 主卧/卫生间分界
    SPLIT_X_BATH = 5000          # 卫生间/次卧分界

    # ── 1. 外墙 ──────────────────────────────────────────────
    _wall_rect(msp, 0, 0, W, H)

    # ── 2. 内墙（横平竖直） ──────────────────────────────────
    # 水平隔墙：上下分区
    _wall(msp, t, MID_Y, W - t, MID_Y)
    # 上层垂直隔墙：客厅 | 厨房
    _wall(msp, SPLIT_X_LIVING, MID_Y, SPLIT_X_LIVING, H - t)
    # 下层垂直隔墙：主卧 | 卫生间 | 次卧
    _wall(msp, SPLIT_X_LOWER, t, SPLIT_X_LOWER, MID_Y - t)
    _wall(msp, SPLIT_X_BATH, t, SPLIT_X_BATH, MID_Y - t)
    # 卫生间内部隔墙：淋浴区 | 干区
    SHOWER_W = 1200
    _wall(msp, SPLIT_X_LOWER + SHOWER_W, t, SPLIT_X_LOWER + SHOWER_W, MID_Y - t)

    # ── 3. 房间地面多边形（算量归属用） ─────────────────────
    # 客厅
    _rect(msp, t, MID_Y + t, SPLIT_X_LIVING - t, H - t, "A-FLOOR")
    # 厨房
    _rect(msp, SPLIT_X_LIVING + t, MID_Y + t, W - t, H - t, "A-FLOOR")
    # 主卧
    _rect(msp, t, t, SPLIT_X_LOWER - t, MID_Y - t, "A-FLOOR")
    # 次卧
    _rect(msp, SPLIT_X_BATH + t, t, W - t, MID_Y - t, "A-FLOOR")
    # 卫生间 - 淋浴区
    _rect(msp, SPLIT_X_LOWER + t, t, SPLIT_X_LOWER + SHOWER_W - t, MID_Y - t, "A-FLOOR-SHOWER")
    # 卫生间 - 干区（马桶、洗手台）
    _rect(msp, SPLIT_X_LOWER + SHOWER_W + t, t, SPLIT_X_BATH - t, MID_Y - t, "A-FLOOR-BATH-DRY")

    # ── 4. 厨房橱柜 ──────────────────────────────────────────
    KX0 = SPLIT_X_LIVING + t + 100   # 厨房内缩
    KX1 = W - t - 100
    KY0 = MID_Y + t + 100
    KY1 = H - t - 100
    CAB_H_BASE = 600    # 地柜深度
    CAB_H_WALL = 350    # 吊柜深度
    CAB_H = 700         # 吊柜高度（示意）

    # 地柜：沿厨房南墙（靠客厅侧）+ 西墙
    _cabinet_base(msp, KX0, KY0, KX1, KY0 + CAB_H_BASE)
    _cabinet_base(msp, KX0, KY0, KX0 + CAB_H_BASE, KY1 - CAB_H_WALL - 200)

    # 吊柜：沿厨房北墙 + 东墙
    _cabinet_wall(msp, KX0, KY1 - CAB_H_WALL, KX1, KY1)
    _cabinet_wall(msp, KX1 - CAB_H_BASE, KY0 + CAB_H_BASE + 200, KX1, KY1 - CAB_H_WALL)

    # ── 5. 卫生间设备示意 ────────────────────────────────────
    # 淋浴房挡水条/玻璃隔断
    sx0 = SPLIT_X_LOWER + t + 50
    sx1 = SPLIT_X_LOWER + SHOWER_W - t - 50
    sy0 = t + 50
    sy1 = MID_Y - t - 50
    _rect(msp, sx0, sy0, sx1, sy1, "A-WALL")          # 淋浴房外框
    # 淋浴喷头示意
    msp.add_circle((sx0 + 200, sy1 - 200), radius=80, dxfattribs={"layer": "A-WALL"})
    # 干区：马桶
    toilet_x = SPLIT_X_LOWER + SHOWER_W + 400
    msp.add_circle((toilet_x, t + 600), radius=200, dxfattribs={"layer": "A-WALL"})
    # 干区：洗手台
    vanity_x0 = SPLIT_X_LOWER + SHOWER_W + 200
    vanity_x1 = SPLIT_X_BATH - 200
    _rect(msp, vanity_x0, MID_Y - t - 500, vanity_x1, MID_Y - t - 100, "A-WALL")

    # ── 6. 门窗 ──────────────────────────────────────────────
    DW = DOOR_WIDTH

    # 入户门（南墙，客厅区域）
    entry_x = 2500
    _door(msp, entry_x, t, DW, angle=90)

    # 客厅 → 主卧 门
    _door(msp, 1800, MID_Y, DW, angle=0)

    # 客厅 → 厨房 门（推拉门示意，用双线）
    kit_door_x = SPLIT_X_LIVING
    msp.add_line((kit_door_x, MID_Y + 800), (kit_door_x, MID_Y + 800 + DW), dxfattribs={"layer": "A-DOOR"})
    msp.add_line((kit_door_x + 50, MID_Y + 800), (kit_door_x + 50, MID_Y + 800 + DW), dxfattribs={"layer": "A-DOOR"})

    # 主卧 → 卫生间 门
    _door(msp, SPLIT_X_LOWER, 2200, DW, angle=90)

    # 次卧门
    _door(msp, SPLIT_X_BATH, 2200, DW, angle=90)

    # 外窗
    WW = WINDOW_WIDTH
    # 客厅南窗
    _window(msp, 800, t, 800 + WW, t)
    # 客厅西窗
    _window(msp, t, 4500, t, 4500 + WW)
    # 主卧西窗
    _window(msp, t, 1200, t, 1200 + WW)
    # 次卧东窗
    _window(msp, W - t, 1200, W - t, 1200 + WW)
    # 厨房北窗
    _window(msp, 6500, H - t, 6500 + WW, H - t)

    # ── 7. 房间标注 ──────────────────────────────────────────
    _room_label(msp, "客厅", 2200, 5200)
    _room_label(msp, "厨房", 6800, 5200)
    _room_label(msp, "主卧", 1500, 1800)
    _room_label(msp, "次卧", 6800, 1800)
    _room_label(msp, "淋浴区", SPLIT_X_LOWER + 300, 1200, height=180)
    _room_label(msp, "卫生间干区", SPLIT_X_LOWER + SHOWER_W + 350, 1800, height=180)
    _room_label(msp, "吊柜", KX0 + 400, KY1 - 200, height=150)
    _room_label(msp, "地柜", KX0 + 400, KY0 + 200, height=150)

    # ── 8. 插座（测试算量图块统计） ──────────────────────────
    _socket_block(doc, msp, 2000, 5000)   # 客厅
    _socket_block(doc, msp, 7000, 5000)   # 厨房
    _socket_block(doc, msp, 1500, 1500)   # 主卧
    _socket_block(doc, msp, 7000, 1500)   # 次卧
    _socket_block(doc, msp, SPLIT_X_LOWER + 800, 1500)  # 卫生间

    # ── 9. 尺寸标注文字（户型说明） ──────────────────────────
    title = msp.add_text(
        "2B1B 户型平面图  9000×7000mm",
        dxfattribs={"layer": "A-ROOM-NAME", "height": 300},
    )
    title.set_placement((W / 2 - 2000, H + 500))

    outfile = "test_floor_plan.dxf"
    doc.saveas(outfile)
    print(f"✅ 已生成 2B1B 户型测试图: {outfile}")
    print("   包含：客厅、厨房(吊柜+地柜)、主卧、次卧、卫生间(淋浴区+干区)、门窗")


if __name__ == "__main__":
    generate_2b1b_plan()
