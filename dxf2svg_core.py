# dxf2svg_core.py
import ezdxf
import math
import os
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

class DXFToSVG:
    def __init__(self):
        self.svg_width = 800
        self.svg_height = 600
        self.stroke_width = 1
        self.stroke_color = "#000000"

    def load_dxf(self, dxf_path):
        try:
            doc = ezdxf.readfile(dxf_path)
            return doc
        except Exception as e:
            print(f"載入 DXF 檔案失敗: {e}")
            return None

    def extract_all_lines(self, doc):
        msp = doc.modelspace()
        line_entities = []
        for entity in msp:
            if entity.dxftype() == 'LINE':
                line_entities.append({
                    'type': 'LINE',
                    'start': (entity.dxf.start.x, entity.dxf.start.y),
                    'end': (entity.dxf.end.x, entity.dxf.end.y),
                    'layer': entity.dxf.layer,
                    'color': getattr(entity.dxf, 'color', 7)
                })
            elif entity.dxftype() == 'LWPOLYLINE':
                points = [(point[0], point[1]) for point in entity.get_points()]
                line_entities.append({
                    'type': 'LWPOLYLINE',
                    'points': points,
                    'closed': entity.closed,
                    'layer': entity.dxf.layer,
                    'color': getattr(entity.dxf, 'color', 7)
                })
            elif entity.dxftype() == 'POLYLINE':
                points = [(vertex.dxf.location.x, vertex.dxf.location.y)
                          for vertex in entity.vertices]
                line_entities.append({
                    'type': 'POLYLINE',
                    'points': points,
                    'closed': entity.closed,
                    'layer': entity.dxf.layer,
                    'color': getattr(entity.dxf, 'color', 7)
                })
            elif entity.dxftype() == 'ARC':
                center = entity.dxf.center
                radius = entity.dxf.radius
                start_angle = math.radians(entity.dxf.start_angle)
                end_angle = math.radians(entity.dxf.end_angle)
                if end_angle < start_angle:
                    end_angle += 2 * math.pi
                num_segments = max(8, int((end_angle - start_angle) * radius / 10))
                angle_step = (end_angle - start_angle) / num_segments
                arc_points = []
                for i in range(num_segments + 1):
                    angle = start_angle + i * angle_step
                    x = center.x + radius * math.cos(angle)
                    y = center.y + radius * math.sin(angle)
                    arc_points.append((x, y))
                line_entities.append({
                    'type': 'ARC_SEGMENTS',
                    'points': arc_points,
                    'closed': False,
                    'layer': entity.dxf.layer,
                    'color': getattr(entity.dxf, 'color', 7)
                })
            elif entity.dxftype() == 'CIRCLE':
                center = entity.dxf.center
                radius = entity.dxf.radius
                num_segments = 32
                angle_step = 2 * math.pi / num_segments
                circle_points = []
                for i in range(num_segments + 1):
                    angle = i * angle_step
                    x = center.x + radius * math.cos(angle)
                    y = center.y + radius * math.sin(angle)
                    circle_points.append((x, y))
                line_entities.append({
                    'type': 'CIRCLE_SEGMENTS',
                    'points': circle_points,
                    'closed': True,
                    'layer': entity.dxf.layer,
                    'color': getattr(entity.dxf, 'color', 7)
                })
        return line_entities

    def get_bounding_box(self, entities):
        if not entities:
            return 0, 0, 100, 100
        x_coords = []
        y_coords = []
        for entity in entities:
            if entity['type'] == 'LINE':
                x_coords.extend([entity['start'][0], entity['end'][0]])
                y_coords.extend([entity['start'][1], entity['end'][1]])
            else:
                for point in entity['points']:
                    x_coords.append(point[0])
                    y_coords.append(point[1])
        return min(x_coords), min(y_coords), max(x_coords), max(y_coords)

    def normalize_coordinates(self, entities, target_width=800, target_height=600, margin=50):
        min_x, min_y, max_x, max_y = self.get_bounding_box(entities)
        orig_width = max_x - min_x
        orig_height = max_y - min_y
        available_width = target_width - 2 * margin
        available_height = target_height - 2 * margin
        scale_x = available_width / orig_width if orig_width > 0 else 1
        scale_y = available_height / orig_height if orig_height > 0 else 1
        scale = min(scale_x, scale_y)
        scaled_width = orig_width * scale
        scaled_height = orig_height * scale
        offset_x = margin + (available_width - scaled_width) / 2
        offset_y = margin + (available_height - scaled_height) / 2
        normalized_entities = []
        for entity in entities:
            if entity['type'] == 'LINE':
                new_start = (
                    (entity['start'][0] - min_x) * scale + offset_x,
                    target_height - ((entity['start'][1] - min_y) * scale + offset_y)
                )
                new_end = (
                    (entity['end'][0] - min_x) * scale + offset_x,
                    target_height - ((entity['end'][1] - min_y) * scale + offset_y)
                )
                normalized_entities.append({
                    'type': 'LINE',
                    'start': new_start,
                    'end': new_end,
                    'layer': entity['layer'],
                    'color': entity['color']
                })
            else:
                new_points = []
                for point in entity['points']:
                    new_point = (
                        (point[0] - min_x) * scale + offset_x,
                        target_height - ((point[1] - min_y) * scale + offset_y)
                    )
                    new_points.append(new_point)
                normalized_entities.append({
                    'type': entity['type'],
                    'points': new_points,
                    'closed': entity.get('closed', False),
                    'layer': entity['layer'],
                    'color': entity['color']
                })
        return normalized_entities

    def get_color_by_index(self, color_index):
        color_map = {
            1: "#FF0000", 2: "#FFFF00", 3: "#00FF00", 4: "#00FFFF", 5: "#0000FF", 6: "#FF00FF", 7: "#FFFFFF", 8: "#808080", 9: "#C0C0C0", 10: "#800000", 11: "#808000", 12: "#008000", 13: "#008080", 14: "#000080", 15: "#800080",
        }
        return color_map.get(color_index, "#000000")

    def entities_to_svg_elements(self, entities):
        svg_elements = []
        for entity in entities:
            color = self.get_color_by_index(entity['color'])
            if entity['type'] == 'LINE':
                from xml.etree.ElementTree import Element
                line = Element('line')
                line.set('x1', f"{entity['start'][0]:.2f}")
                line.set('y1', f"{entity['start'][1]:.2f}")
                line.set('x2', f"{entity['end'][0]:.2f}")
                line.set('y2', f"{entity['end'][1]:.2f}")
                line.set('stroke', color)
                line.set('stroke-width', str(self.stroke_width))
                line.set('stroke-linecap', 'round')
                svg_elements.append(line)
            else:
                if not entity['points']:
                    continue
                path = Element('path')
                path_parts = []
                first_point = entity['points'][0]
                path_parts.append(f"M{first_point[0]:.2f},{first_point[1]:.2f}")
                for point in entity['points'][1:]:
                    path_parts.append(f"L{point[0]:.2f},{point[1]:.2f}")
                if entity.get('closed', False):
                    path_parts.append("Z")
                path.set('d', " ".join(path_parts))
                path.set('stroke', color)
                path.set('stroke-width', str(self.stroke_width))
                path.set('stroke-linecap', 'round')
                path.set('stroke-linejoin', 'round')
                path.set('fill', 'none')
                svg_elements.append(path)
        return svg_elements

    def create_svg(self, entities):
        svg = Element('svg')
        svg.set('width', str(self.svg_width))
        svg.set('height', str(self.svg_height))
        svg.set('viewBox', f'0 0 {self.svg_width} {self.svg_height}')
        svg.set('xmlns', 'http://www.w3.org/2000/svg')
        svg_elements = self.entities_to_svg_elements(entities)
        for element in svg_elements:
            svg.append(element)
        return svg

    def convert_dxf_to_svg(self, dxf_path, output_path=None):
        doc = self.load_dxf(dxf_path)
        if not doc:
            return False, "無法載入 DXF 檔案"
        entities = self.extract_all_lines(doc)
        if not entities:
            return False, "DXF 檔案中沒有找到線條"
        normalized_entities = self.normalize_coordinates(entities, self.svg_width, self.svg_height)
        svg = self.create_svg(normalized_entities)
        rough_string = tostring(svg, 'unicode')
        reparsed = parseString(rough_string)
        formatted_svg = reparsed.toprettyxml(indent="  ")
        if output_path is None:
            base_name = os.path.splitext(dxf_path)[0]
            output_path = f"{base_name}.svg"
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(formatted_svg)
            return True, f"成功轉換為 SVG: {output_path}"
        except Exception as e:
            return False, f"儲存 SVG 檔案失敗: {e}" 