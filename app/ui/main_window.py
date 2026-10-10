from __future__ import annotations

import httpx

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from app.config import settings
from app.models.job import SearchResponse
from app.ui.pages import AboutPage, ResultsPage, SearchPage
from app.ui.theme import MAIN_QSS
from app.ui.widgets import NavButton


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JobFinder")
        self.resize(1440, 900)
        self.setMinimumSize(1180, 780)
        self.setStyleSheet(MAIN_QSS)
        self._status_attempts = 0
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self.refresh_status)
        self._build()
        self._status_timer.start(500)

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame(objectName="Sidebar")
        sidebar.setFixedWidth(224)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(16, 20, 16, 16)
        side.setSpacing(6)

        brand_row = QHBoxLayout()
        brand_mark = QLabel("J")
        brand_mark.setObjectName("BrandMark")
        brand = QLabel("JobFinder")
        brand.setObjectName("Brand")
        brand_row.addWidget(brand_mark)
        brand_row.addWidget(brand)
        brand_row.addStretch()
        side.addLayout(brand_row)

        sub = QLabel("JOB RESEARCH DESKTOP")
        sub.setObjectName("BrandSub")
        side.addWidget(sub)
        side.addSpacing(28)

        section = QLabel("WORKSPACE")
        section.setObjectName("SidebarSection")
        side.addWidget(section)

        self.nav_search = NavButton("Search")
        self.nav_results = NavButton("Results")
        self.nav_about = NavButton("About")
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        for button in (self.nav_search, self.nav_results, self.nav_about):
            self._nav_group.addButton(button)
            side.addWidget(button)
        self._nav_group.buttonClicked.connect(self._nav_clicked)

        side.addStretch()
        self.backend_badge = QLabel("Checking local backend…")
        self.backend_badge.setObjectName("SidebarStatus")
        side.addWidget(self.backend_badge)
        root.addWidget(sidebar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        topbar = QFrame(objectName="Topbar")
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(22, 12, 22, 12)
        self.connection = QLabel("Local search")
        self.connection.setObjectName("Pill")
        tb.addWidget(self.connection)
        tb.addStretch()
        self.new_search_button = QPushButton("New search")
        self.new_search_button.setObjectName("Secondary")
        self.new_search_button.clicked.connect(lambda: self.show_page(0))
        tb.addWidget(self.new_search_button)
        content_layout.addWidget(topbar)

        self.stack = QStackedWidget()
        self.search_page = SearchPage(self)
        self.results_page = ResultsPage(self)
        self.about_page = AboutPage()
        for page in (self.search_page, self.results_page, self.about_page):
            self.stack.addWidget(page)
        content_layout.addWidget(self.stack, 1)
        root.addWidget(content, 1)
        self.show_page(0)

    def _nav_clicked(self, btn):
        mapping = {self.nav_search: 0, self.nav_results: 1, self.nav_about: 2}
        self.show_page(mapping[btn])

    def show_page(self, index: int):
        self.stack.setCurrentIndex(index)
        for btn, idx in ((self.nav_search, 0), (self.nav_results, 1), (self.nav_about, 2)):
            btn.setChecked(index == idx)

    def _set_backend_state(self, ready: bool):
        self.backend_badge.setText("Local backend · Ready" if ready else "Local backend · Starting")
        self.backend_badge.setProperty("state", "ok" if ready else "")
        self.backend_badge.style().unpolish(self.backend_badge)
        self.backend_badge.style().polish(self.backend_badge)
        self.connection.setText("Ready to search" if ready else "Starting local service…")

    def refresh_status(self):
        """Poll the backend until it answers; then slow down to a light heartbeat."""
        try:
            response = httpx.get(
                f"http://{settings.backend_host}:{settings.backend_port}/api/status",
                timeout=1.5,
            )
            response.raise_for_status()
            self._set_backend_state(True)
            self._status_timer.setInterval(15000)
        except Exception:
            self._status_attempts += 1
            self._set_backend_state(False)
            if self._status_attempts == 20:
                self.backend_badge.setText("Local backend · Unavailable")
                self.connection.setText("Local service is not responding")
            self._status_timer.setInterval(1000)

    async def api_search(self, spec):
        url = f"http://{settings.backend_host}:{settings.backend_port}/api/search"
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.post(url, json=spec.model_dump(mode="json"))
            response.raise_for_status()
            return SearchResponse.model_validate(response.json())
