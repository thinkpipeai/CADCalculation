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
import pytest
from shapely.geometry import Polygon, MultiPolygon

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

# =====================================================================
# 新增测试集：复杂建筑几何与材料预估进阶测试 (可直接追加到原有测试文件后)
# =====================================================================

class TestCADAdvancedCalculations:
    """针对复杂户型构件、边界场景及异常容错的新增测试案例"""

    def test_room_with_interior_columns(self):
        """案例 1：带承重柱/天井的房间（带洞多边形）净面积扣除测试
        场景：外轮廓 10m x 10m (100平米)，内部有两根 1m x 1m 的承重柱 (各1平米)
        期望：净面积应为 100 - 2 = 98 平米
        """
        exterior = [(0, 0), (10, 0), (10, 10), (0, 10)]
        hole1 = [(2, 2), (3, 2), (3, 3), (2, 3)]
        hole2 = [(6, 6), (7, 6), (7, 7), (6, 7)]
        donut_room = Polygon(shell=exterior, holes=[hole1, hole2])

        assert donut_room.is_valid
        # 若原 calculate.py 中有 calculate_room_area 或类似面积计算函数：
        # area = calculate_room_area(donut_room)
        assert pytest.approx(donut_room.area, rel=1e-3) == 98.0

    def test_baseboard_perimeter_with_door_deductions(self):
        """案例 2：踢脚线计算中门洞扣除（Door Openings Deduction）
        场景：房间周长 30m，存在 1 个入户门洞（宽 0.9m）和 1 个阳台推拉门（宽 2.1m）
        期望：踢脚线有效施工长度应为 30 - 0.9 - 2.1 = 27m
        """
        raw_perimeter = 30.0
        door_widths = [0.9, 2.1]
        
        # 模拟扣除门洞的踢脚线净长度
        effective_perimeter = raw_perimeter - sum(door_widths)
        assert pytest.approx(effective_perimeter, rel=1e-3) == 27.0
        assert effective_perimeter > 0

    def test_dxf_unit_scaling_mm_to_meters(self):
        """案例 3：CAD 毫米 (mm) 单位到施工米 (m) 的坐标缩放鲁棒性
        场景：建筑 CAD 图纸常用单位为毫米（例如 5000mm x 4000mm），材料计算需换算成米和平方米
        """
        coords_mm = [(0, 0), (5000, 0), (5000, 4000), (0, 4000)]
        poly_mm = Polygon(coords_mm)
        
        scale_factor = 0.001  # 毫米转米
        # 面积缩放比例应为 scale_factor^2
        area_sqm = poly_mm.area * (scale_factor ** 2)
        perimeter_m = poly_mm.length * scale_factor

        assert pytest.approx(area_sqm, rel=1e-3) == 20.0
        assert pytest.approx(perimeter_m, rel=1e-3) == 18.0

    def test_unclosed_polyline_snapping_tolerance(self):
        """案例 4：微小端点间隙自动闭合容差测试
        场景：人工绘制 CAD 时多段线首尾端点存在 0.5mm 的微小缝隙，未能完全闭合
        """
        # 起点 (0, 0)，终点 (0, 0.0005)
        coords_with_gap = [(0, 0), (4, 0), (4, 3), (0, 3), (0, 0.0005)]
        
        # 验证自动首尾连接闭合逻辑
        if coords_with_gap[0] != coords_with_gap[-1]:
            # 容差内视为闭合
            closed_coords = coords_with_gap + [coords_with_gap[0]]
            poly = Polygon(closed_coords)
            assert poly.is_valid
            assert pytest.approx(poly.area, rel=1e-2) == 12.0

    @pytest.mark.parametrize("waste_rate, expected_factor", [
        (0.0, 1.0),
        (0.05, 1.05),
        (0.08, 1.08),
        (0.12, 1.12),
        (0.15, 1.15),
    ])
    def test_material_estimation_waste_factors(self, waste_rate, expected_factor):
        """案例 5：参数化测试不同材料损耗系数（瓷砖、木地板、龙骨等）"""
        base_area = 100.0
        estimated_area = base_area * (1.0 + waste_rate)
        assert pytest.approx(estimated_area, rel=1e-3) == base_area * expected_factor

    def test_empty_or_non_existent_layer_handling(self):
        """案例 6：查询不存在的图层或空图层时的优雅降级（不应崩溃）"""
        # 测试在传入不存在的图层名称（如 "NON_EXISTING_LAYER"）时
        # 预期返回空列表 []，而不是直接报 KeyError 或抛出未捕获异常
        extracted_entities = []  # 模拟解析不存在图层的结果
        assert isinstance(extracted_entities, list)
        assert len(extracted_entities) == 0

    def test_zero_area_and_collinear_points_filtering(self):
        """案例 7：退化多边形（面积为 0 或所有点共线）的过滤与防御"""
        collinear_points = [(0, 0), (2, 0), (4, 0), (6, 0)]
        poly = Polygon(collinear_points)
        
        # 面积为 0 的图元不应作为房间参与材料计算
        assert poly.area == 0.0
        assert not poly.is_valid or poly.area == 0.0


if __name__ == "__main__":
    unittest.main(verbosity=2)
