"""history_panel.py — DAG visualization of the processing audit trail.

exports: HistoryPanel
used_by: dig/viz/__init__.py
rules:
  - Read-only visualization of AuditTrail.
"""

import math
from PySide6 import QtCore, QtGui, QtWidgets
from dig.models.audit import AuditTrail, ProcessingStep

class AuditNodeItem(QtWidgets.QGraphicsRectItem):
    """Graphical node representing a single processing step."""
    
    def __init__(self, step: ProcessingStep, parent: QtWidgets.QGraphicsItem | None = None):
        super().__init__(0, 0, 160, 70, parent)
        self.step = step
        
        # Style
        self.setBrush(QtGui.QBrush(QtGui.QColor(40, 44, 52)))
        self.setPen(QtGui.QPen(QtGui.QColor(97, 175, 239), 2))
        
        # Details
        param_str = ", ".join(f"{k}={v}" for k, v in step.parameters.items())
        if len(param_str) > 20:
            param_str = param_str[:17] + "..."
            
        time_str = step.timestamp.strftime('%H:%M:%S')
        text = f"{step.name}\n{time_str}\n{param_str}"
        
        self.text_item = QtWidgets.QGraphicsTextItem(text, self)
        self.text_item.setDefaultTextColor(QtCore.Qt.white)
        self.text_item.setPos(5, 5)
        
        # Make the item selectable
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

class HistoryPanel(QtWidgets.QWidget):
    """Widget displaying the processing audit trail as a DAG (Tree)."""
    
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        
        self.scene = QtWidgets.QGraphicsScene(self)
        self.view = QtWidgets.QGraphicsView(self.scene)
        self.view.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        # Background color
        self.view.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(28, 33, 40)))
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.view)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self._trail: AuditTrail | None = None
        self._nodes: dict[str, AuditNodeItem] = {}
        
    def set_audit_trail(self, trail: AuditTrail) -> None:
        """Set the model and render the DAG."""
        self._trail = trail
        self._rebuild_scene()
        
    def _rebuild_scene(self) -> None:
        self.scene.clear()
        self._nodes.clear()
        
        if not self._trail or not self._trail.steps:
            return
            
        children_map: dict[str, list[ProcessingStep]] = {}
        roots: list[ProcessingStep] = []
        
        for step in self._trail.steps:
            children_map[step.timestamp.isoformat()] = []
            
        for step in self._trail.steps:
            parent_id = step.parent_step
            if parent_id and parent_id in children_map:
                children_map[parent_id].append(step)
            else:
                roots.append(step)
                
        self._draw_tree(roots, 20, 20, children_map)
        
    def _draw_tree(
        self, 
        nodes: list[ProcessingStep], 
        x_start: float, 
        y_start: float, 
        children_map: dict[str, list[ProcessingStep]]
    ) -> float:
        current_y = y_start
        for step in nodes:
            node_id = step.timestamp.isoformat()
            node_item = AuditNodeItem(step)
            node_item.setPos(x_start, current_y)
            self.scene.addItem(node_item)
            self._nodes[node_id] = node_item
            
            node_center_y = current_y + 35
            
            children = children_map.get(node_id, [])
            if children:
                child_x = x_start + 220
                next_y = self._draw_tree(children, child_x, current_y, children_map)
                
                # Draw edges
                for child in children:
                    child_id = child.timestamp.isoformat()
                    child_item = self._nodes[child_id]
                    
                    p1 = QtCore.QPointF(x_start + 160, node_center_y)
                    p2 = QtCore.QPointF(child_x, child_item.pos().y() + 35)
                    
                    path = QtGui.QPainterPath()
                    path.moveTo(p1)
                    # Cubic bezier for smooth routing
                    path.cubicTo(p1.x() + 30, p1.y(), p2.x() - 30, p2.y(), p2.x(), p2.y())
                    
                    edge = QtWidgets.QGraphicsPathItem(path)
                    edge.setPen(QtGui.QPen(QtGui.QColor(150, 150, 150), 2))
                    self.scene.addItem(edge)
                    
                    # Arrow head
                    arrow_size = 6
                    p_prev = path.pointAtPercent(0.95)
                    angle = math.atan2(p2.y() - p_prev.y(), p2.x() - p_prev.x())
                    arrow_p1 = p2 - QtCore.QPointF(
                        math.cos(angle + math.pi/6) * arrow_size,
                        math.sin(angle + math.pi/6) * arrow_size
                    )
                    arrow_p2 = p2 - QtCore.QPointF(
                        math.cos(angle - math.pi/6) * arrow_size,
                        math.sin(angle - math.pi/6) * arrow_size
                    )
                    
                    arrow_poly = QtGui.QPolygonF([p2, arrow_p1, arrow_p2])
                    arrow_item = QtWidgets.QGraphicsPolygonItem(arrow_poly)
                    arrow_item.setBrush(QtGui.QBrush(QtGui.QColor(150, 150, 150)))
                    arrow_item.setPen(QtGui.QPen(QtCore.Qt.PenStyle.NoPen))
                    self.scene.addItem(arrow_item)
                    
                current_y = next_y
            else:
                current_y += 90
                
        return current_y
