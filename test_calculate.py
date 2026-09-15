"""
Day 5 — CAD 算量模块测试用例

运行方式（在项目根目录）：
  python test_calculate.py
  或
  python -m unittest test_calculate -v
"""

import os
import tempfile
import unittest

import ezdxf

from calculate import (
    _mm2m,
    _mm2m2,
    _rect_from_polygon,
    analyze_floor_plan,
)
from shapely.geometry import Polygon


DXF_PATH = os.path.join(os.path.dirname(__file__), "test_floor_plan.dxf")


def _room_by_name(result, name):
    for room in result["rooms"]:
        if room["name"] == name:
            return room
    raise AssertionError(f"未找到房间: {name}")


class TestUnitHelpers(unittest.TestCase):
    """单位换算与几何辅助函数"""

    def test_mm_to_m(self):
        self.assertEqual(_mm2m(1000), 1.0)
        self.assertEqual(_mm2m(900), 0.9)

    def test_mm2_to_m2(self):
        # 3000mm × 2000mm = 6_000_000 mm² = 6 m²
        self.assertAlmostEqual(_mm2m2(6_000_000), 6.0)

    def test_rect_from_polygon(self):
        poly = Polygon([(0, 0), (3100, 0), (3100, 3100), (0, 3100)])
        width, depth = _rect_from_polygon(poly)
        self.assertEqual(width, 3100)
        self.assertEqual(depth, 3100)


@unittest.skipUnless(os.path.exists(DXF_PATH), "缺少 test_floor_plan.dxf，请先运行 create_cad.py")
class TestFloorPlanIntegration(unittest.TestCase):
    """基于 2B1B 测试图纸的端到端算量校验"""

    @classmethod
    def setUpClass(cls):
        cls.result = analyze_floor_plan(DXF_PATH)

    def test_room_count(self):
        self.assertEqual(len(self.result["rooms"]), 6)

    def test_room_names(self):
        names = {r["name"] for r in self.result["rooms"]}
        expected = {"客厅", "厨房", "主卧", "次卧", "淋浴区", "卫生间干区"}
        self.assertTrue(expected.issubset(names), f"实际房间: {names}")

    def test_living_room_area(self):
        living = _room_by_name(self.result, "客厅")
        self.assertAlmostEqual(living["area_m2"], 15.81, places=2)

    def test_kitchen_area(self):
        kitchen = _room_by_name(self.result, "厨房")
        self.assertAlmostEqual(kitchen["area_m2"], 9.61, places=2)

    def test_master_bedroom_size(self):
        master = _room_by_name(self.result, "主卧")
        self.assertAlmostEqual(master["width_m"], 3.10, places=2)
        self.assertAlmostEqual(master["depth_m"], 3.10, places=2)

    def test_door_count_and_width(self):
        self.assertEqual(len(self.result["doors"]), 5)
        for door in self.result["doors"]:
            self.assertAlmostEqual(door["width_mm"], 900, delta=1)

    def test_window_count_and_width(self):
        self.assertEqual(len(self.result["windows"]), 5)
        for win in self.result["windows"]:
            self.assertAlmostEqual(win["width_mm"], 1500, delta=1)

    def test_kitchen_cabinets(self):
        kitchen = _room_by_name(self.result, "厨房")
        self.assertEqual(len(kitchen["cabinets"]), 4)
        types = {c["type"] for c in kitchen["cabinets"]}
        self.assertEqual(types, {"地柜", "吊柜"})
        for cab in kitchen["cabinets"]:
            self.assertGreater(cab["width_mm"], 0)
            self.assertGreater(cab["depth_mm"], 0)
            self.assertGreater(cab["area_m2"], 0)

    def test_total_area(self):
        self.assertAlmostEqual(self.result["total_area_m2"], 48.98, places=2)

    def test_socket_in_main_rooms(self):
        for name in ("客厅", "厨房", "主卧", "次卧"):
            room = _room_by_name(self.result, name)
            self.assertGreaterEqual(room["socket_count"], 1, f"{name} 应至少有 1 个插座")


class TestMissingFile(unittest.TestCase):
    """异常路径"""

    def test_missing_dxf_raises(self):
        with self.assertRaises(IOError):
            analyze_floor_plan("not_exists_floor_plan.dxf")


class TestMinimalSyntheticDxf(unittest.TestCase):
    """用内存生成的最小 DXF 验证解析链路"""

    def setUp(self):
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()
        for layer in ("A-FLOOR", "A-ROOM-NAME", "A-DOOR", "A-WINDOW"):
            if layer not in doc.layers:
                doc.layers.add(layer)

        # 4m × 3m 房间
        msp.add_lwpolyline(
            [(0, 0), (4000, 0), (4000, 3000), (0, 3000)],
            dxfattribs={"layer": "A-FLOOR", "closed": True},
        )
        text = msp.add_text("测试房", dxfattribs={"layer": "A-ROOM-NAME", "height": 200})
        text.set_placement((1500, 1500))
        # 900mm 平开门
        msp.add_arc(center=(0, 1000), radius=900, start_angle=0, end_angle=90,
                    dxfattribs={"layer": "A-DOOR"})
        # 1500mm 窗线
        msp.add_line((1000, 3000), (2500, 3000), dxfattribs={"layer": "A-WINDOW"})

        fd, self.path = tempfile.mkstemp(suffix=".dxf")
        os.close(fd)
        doc.saveas(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_synthetic_room_area_and_opening(self):
        result = analyze_floor_plan(self.path)
        self.assertEqual(len(result["rooms"]), 1)
        room = result["rooms"][0]
        self.assertEqual(room["name"], "测试房")
        self.assertAlmostEqual(room["area_m2"], 12.0, places=2)
        self.assertEqual(len(result["doors"]), 1)
        self.assertAlmostEqual(result["doors"][0]["width_mm"], 900, delta=1)
        self.assertEqual(len(result["windows"]), 1)
        self.assertAlmostEqual(result["windows"][0]["width_mm"], 1500, delta=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
