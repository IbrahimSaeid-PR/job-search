from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout


class MetricCard(QFrame):
    def __init__(self, label: str, value: str = "—"):
        super().__init__()
        self.setObjectName("Metric")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(3)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("MetricNumber")
        label_widget = QLabel(label.upper())
        label_widget.setObjectName("MetricLabel")
        layout.addWidget(self.value_label)
        layout.addWidget(label_widget)


class PageHeader(QVBoxLayout):
    def __init__(self, title: str, subtitle: str, eyebrow: str = "JOBFINDER"):
        super().__init__()
        eyebrow_label = QLabel(eyebrow)
        eyebrow_label.setObjectName("Eyebrow")
        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("PageSubtitle")
        self.addWidget(eyebrow_label)
        self.addWidget(title_label)
        self.addWidget(subtitle_label)
        self.setSpacing(3)


class NavButton(QPushButton):
    def __init__(self, text: str):
        super().__init__(text)
        self.setObjectName("Nav")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(42)
