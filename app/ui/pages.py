from __future__ import annotations

import asyncio
import re
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QTextBrowser,
    QHeaderView,
)

from app.export import export_csv, export_excel
from app.models.job import SearchResponse
from app.models.search import (
    EmploymentType,
    ExperienceLevel,
    JobPostingAge,
    SalaryRange,
    SearchSpecification,
    WorkMode,
)
from app.ui.widgets import MetricCard, PageHeader


def _md_escape(text: str) -> str:
    """Neutralise Markdown/HTML control characters in text that comes from the web."""
    return re.sub(r"([\\`*_{}\[\]<>#|])", r"\\\1", text)


class AsyncWorker(QObject):
    finished = Signal(object, object)

    def __init__(self, coro_factory):
        super().__init__()
        self.coro_factory = coro_factory

    @Slot()
    def run(self):
        try:
            result = asyncio.run(self.coro_factory())
            self.finished.emit(result, None)
        except Exception as exc:
            self.finished.emit(None, exc)


class SearchPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._thread = None
        self._worker = None
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        hero = QFrame(objectName="Hero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(22, 20, 22, 20)
        hero_layout.setSpacing(4)
        hero_kicker = QLabel("SEARCH")
        hero_kicker.setObjectName("Eyebrow")
        title = QLabel("Find roles that fit.")
        title.setObjectName("HeroTitle")
        subtitle = QLabel("Describe what you are looking for once. JobFinder searches the public web, cleans the results, removes duplicates and gives you the strongest matches.")
        subtitle.setObjectName("HeroSubtitle")
        subtitle.setWordWrap(True)
        hero_layout.addWidget(hero_kicker)
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        outer.addWidget(hero)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 2, 8, 8)
        body_layout.setSpacing(14)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        search_card = self._card("What are you looking for?", "Start with the role and location. The other fields narrow the search.")
        sl = search_card.layout()
        sl.addWidget(self._field("Job title(s)", self._line("AI Engineer, Backend Engineer", "Role names separated by commas")))
        self.titles = sl.itemAt(sl.count() - 1).widget().findChild(QLineEdit)
        sl.addWidget(self._field("Additional roles", self._line("ML Engineer, Python Developer", "Optional alternatives")))
        self.additional = sl.itemAt(sl.count() - 1).widget().findChild(QLineEdit)
        sl.addWidget(self._field("Location", self._line("Cairo, Giza, Remote", "City, country or Remote")))
        self.location = sl.itemAt(sl.count() - 1).widget().findChild(QLineEdit)

        filters = self._card("Filters", "Use only the filters that matter to your search.")
        fl = filters.layout()
        self.age = QComboBox()
        self.age.addItems([x.value for x in JobPostingAge])
        self.age.setCurrentText(JobPostingAge.LAST_7_DAYS.value)
        fl.addWidget(self._field("Posted within", self.age))

        self.experience = QComboBox()
        self.experience.addItems([x.value for x in ExperienceLevel])
        self.experience.setCurrentText(ExperienceLevel.ANY.value)
        fl.addWidget(self._field("Experience", self.experience))

        work_row = QHBoxLayout()
        self.work_remote = QCheckBox("Remote")
        self.work_hybrid = QCheckBox("Hybrid")
        self.work_onsite = QCheckBox("On-site")
        for checkbox in (self.work_remote, self.work_hybrid, self.work_onsite):
            work_row.addWidget(checkbox)
        work_row.addStretch()
        fl.addWidget(self._group("Work mode", work_row))

        type_row = QHBoxLayout()
        self.fulltime = QCheckBox("Full-time")
        self.parttime = QCheckBox("Part-time")
        self.contract = QCheckBox("Contract")
        self.internship = QCheckBox("Internship")
        for checkbox in (self.fulltime, self.parttime, self.contract, self.internship):
            type_row.addWidget(checkbox)
        type_row.addStretch()
        fl.addWidget(self._group("Employment type", type_row))

        grid.addWidget(search_card, 0, 0)
        grid.addWidget(filters, 0, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        body_layout.addLayout(grid)

        details = self._card("More details", "Keywords improve relevance. Excluded keywords remove obvious noise.")
        dl = details.layout()
        details_grid = QGridLayout()
        details_grid.setHorizontalSpacing(14)
        self.keywords = self._line("Python, FastAPI, PostgreSQL", "Optional")
        self.excluded = self._line("Senior, unpaid, sales", "Optional")
        details_grid.addWidget(self._field("Keywords", self.keywords), 0, 0)
        details_grid.addWidget(self._field("Excluded keywords", self.excluded), 0, 1)

        salary_row = QHBoxLayout()
        self.salary_min = QLineEdit(placeholderText="Min")
        self.salary_max = QLineEdit(placeholderText="Max")
        self.currency = QComboBox()
        self.currency.addItems(["USD", "EUR", "GBP", "EGP"])
        for widget in (self.salary_min, self.salary_max, self.currency):
            salary_row.addWidget(widget)
        details_grid.addWidget(self._group("Expected salary", salary_row), 1, 0)

        self.limit = QSpinBox()
        self.limit.setRange(1, 50)
        self.limit.setValue(50)
        details_grid.addWidget(self._field("Results", self.limit), 1, 1)
        details_grid.setColumnStretch(0, 1)
        details_grid.setColumnStretch(1, 1)
        dl.addLayout(details_grid)
        body_layout.addWidget(details)

        action = QFrame(objectName="ActionBar")
        al = QHBoxLayout(action)
        al.setContentsMargins(16, 14, 16, 14)
        note = QLabel("Searches up to the requested limit, then ranks the strongest matches.")
        note.setObjectName("ActionNote")
        al.addWidget(note)
        al.addStretch()
        self.search_button = QPushButton("Search jobs")
        self.search_button.setObjectName("Primary")
        self.search_button.setMinimumWidth(160)
        self.search_button.clicked.connect(self.start_search)
        al.addWidget(self.search_button)
        body_layout.addWidget(action)
        body_layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

    @staticmethod
    def _line(placeholder: str, tooltip: str):
        widget = QLineEdit(placeholderText=placeholder)
        widget.setToolTip(tooltip)
        return widget

    @staticmethod
    def _card(title: str, description: str) -> QFrame:
        card = QFrame(objectName="Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(9)
        heading = QLabel(title)
        heading.setObjectName("SectionTitle")
        desc = QLabel(description)
        desc.setObjectName("CardDescription")
        desc.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(desc)
        return card

    @staticmethod
    def _field(label: str, widget) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        title = QLabel(label)
        title.setObjectName("FieldLabel")
        layout.addWidget(title)
        layout.addWidget(widget)
        return wrap

    @staticmethod
    def _group(label: str, content_layout) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        title = QLabel(label)
        title.setObjectName("FieldLabel")
        layout.addWidget(title)
        layout.addLayout(content_layout)
        return wrap

    def spec(self) -> SearchSpecification:
        salary_min = self._number(self.salary_min.text(), "Minimum salary")
        salary_max = self._number(self.salary_max.text(), "Maximum salary")
        work = []
        if self.work_remote.isChecked():
            work.append(WorkMode.REMOTE)
        if self.work_hybrid.isChecked():
            work.append(WorkMode.HYBRID)
        if self.work_onsite.isChecked():
            work.append(WorkMode.ON_SITE)
        types = []
        if self.fulltime.isChecked():
            types.append(EmploymentType.FULL_TIME)
        if self.parttime.isChecked():
            types.append(EmploymentType.PART_TIME)
        if self.contract.isChecked():
            types.append(EmploymentType.CONTRACT)
        if self.internship.isChecked():
            types.append(EmploymentType.INTERNSHIP)

        if salary_min is not None and salary_max is not None and salary_max < salary_min:
            raise ValueError("Maximum salary must be greater than or equal to minimum salary.")
        salary = (
            SalaryRange(minimum=salary_min, maximum=salary_max, currency=self.currency.currentText())
            if salary_min is not None or salary_max is not None
            else None
        )
        titles = self._split(self.titles.text())
        if not titles:
            raise ValueError("Enter at least one job title.")
        return SearchSpecification(
            job_titles=titles,
            additional_roles=self._split(self.additional.text()),
            location=self.location.text().strip() or None,
            posting_age=JobPostingAge(self.age.currentText()),
            salary=salary,
            experience_level=ExperienceLevel(self.experience.currentText()),
            work_modes=work,
            employment_types=types,
            keywords=self._split(self.keywords.text()),
            excluded_keywords=self._split(self.excluded.text()),
            result_limit=self.limit.value(),
        )

    @staticmethod
    def _split(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @staticmethod
    def _number(value: str, label: str) -> float | None:
        if not value.strip():
            return None
        try:
            number = float(value)
        except ValueError as exc:
            raise ValueError(f"{label} must be a number.") from exc
        if number < 0:
            raise ValueError(f"{label} cannot be negative.")
        return number

    def start_search(self):
        try:
            spec = self.spec()
        except Exception as exc:
            QMessageBox.warning(self, "Check your search", str(exc))
            return
        self.search_button.setEnabled(False)
        self.search_button.setText("Searching…")
        if self._thread is not None:
            return
        self._thread = QThread(self)
        # Keep a reference: a worker held only by a local variable is garbage-collected mid-run.
        self._worker = AsyncWorker(lambda: self.main_window.api_search(spec))
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._finished)
        self._thread.start()

    def _finished(self, result, error):
        self.search_button.setEnabled(True)
        self.search_button.setText("Search jobs")
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread.deleteLater()
            self._thread = None
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
        if error:
            QMessageBox.critical(self, "Search failed", self._describe_error(error))
        else:
            self.main_window.results_page.set_response(result)
            self.main_window.show_page(1)

    @staticmethod
    def _describe_error(error: Exception) -> str:
        name = type(error).__name__
        if "Connect" in name:
            return "Could not reach the local search service. Wait a few seconds and try again."
        if "Timeout" in name:
            return "The search took too long. Try fewer roles or a shorter time window."
        return str(error) or name


class ResultsPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.response: SearchResponse | None = None
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)
        root.addLayout(PageHeader("Your matches", "Cleaned, deduplicated and ranked from the public web."))

        metrics = QHBoxLayout()
        self.m_found = MetricCard("Found")
        self.m_unique = MetricCard("Shortlist")
        self.m_time = MetricCard("Search time")
        self.m_score = MetricCard("Best score")
        for card in (self.m_found, self.m_unique, self.m_time, self.m_score):
            metrics.addWidget(card)
        root.addLayout(metrics)

        work = QHBoxLayout()
        work.setSpacing(14)
        list_card = QFrame(objectName="Card")
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(10, 10, 10, 10)
        toolbar = QHBoxLayout()
        self.status = QLabel("Run a search to see results")
        self.status.setObjectName("Hint")
        toolbar.addWidget(self.status)
        toolbar.addStretch()
        csv_btn = QPushButton("CSV")
        csv_btn.setObjectName("Secondary")
        csv_btn.clicked.connect(self.export_csv)
        xlsx_btn = QPushButton("Excel")
        xlsx_btn.setObjectName("Primary")
        xlsx_btn.clicked.connect(self.export_excel)
        toolbar.addWidget(csv_btn)
        toolbar.addWidget(xlsx_btn)
        list_layout.addLayout(toolbar)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Role", "Company", "Location", "Mode", "Source", "Score"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for column in range(1, 6):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._show_selected)
        list_layout.addWidget(self.table, 1)
        work.addWidget(list_card, 3)

        detail = QFrame(objectName="Card")
        detail.setMinimumWidth(360)
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(18, 16, 18, 16)
        self.detail_title = QLabel("Select a role")
        self.detail_title.setObjectName("SectionTitle")
        self.detail_company = QLabel("—")
        self.detail_company.setObjectName("PageSubtitle")
        self.detail_text = QTextBrowser()
        self.detail_text.setOpenExternalLinks(True)
        self.detail_link = QPushButton("Open job page")
        self.detail_link.setObjectName("Secondary")
        self.detail_link.setEnabled(False)
        self.detail_link.clicked.connect(self._open_link)
        detail_layout.addWidget(self.detail_title)
        detail_layout.addWidget(self.detail_company)
        detail_layout.addWidget(self.detail_text, 1)
        detail_layout.addWidget(self.detail_link)
        work.addWidget(detail, 2)
        root.addLayout(work, 1)

    def set_response(self, response: SearchResponse):
        self.response = response
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for job in response.jobs:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [job.title, job.company, job.location, job.work_mode or "—", job.source, f"{job.score:.1f}"]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.table.blockSignals(False)
        self.m_found.value_label.setText(str(response.total_found))
        self.m_unique.value_label.setText(str(response.total_after_deduplication))
        self.m_time.value_label.setText(f"{response.duration_ms / 1000:.1f}s")
        self.m_score.value_label.setText(f"{response.jobs[0].score:.1f}" if response.jobs else "—")
        self.status.setText(
            f"{len(response.jobs)} matches ready" + (f" · {len(response.warnings)} notes" if response.warnings else "")
        )
        self.status.setToolTip("\n".join(response.warnings))
        if response.jobs:
            self.table.selectRow(0)
        else:
            self.detail_title.setText("No matches")
            self.detail_company.setText("Try a broader query")
            notes = "\n".join(f"• {w}" for w in response.warnings)
            self.detail_text.setPlainText(
                "No public-web results matched the current search." + (f"\n\n{notes}" if notes else "")
            )
            self.detail_link.setProperty("job_url", "")
            self.detail_link.setEnabled(False)

    def _show_selected(self):
        row = self.table.currentRow()
        if not self.response or row < 0 or row >= len(self.response.jobs):
            return
        job = self.response.jobs[row]
        self.detail_title.setText(job.title)
        self.detail_company.setText(f"{job.company}  ·  {job.source}")
        posted = job.posted_at.strftime("%Y-%m-%d") if job.posted_at else "Not verified"
        reasons = "\n".join(f"• {reason}" for reason in job.match_reasons) or "• General relevance match"
        esc = _md_escape
        self.detail_text.setMarkdown(
            f"**Location**  \n{esc(job.location)}\n\n"
            f"**Work mode**  \n{job.work_mode or 'Not specified'}\n\n"
            f"**Employment**  \n{job.employment_type or 'Not specified'}\n\n"
            f"**Experience**  \n{job.experience_level or 'Not specified'}\n\n"
            f"**Salary**  \n{esc(job.salary or 'Not specified')}\n\n"
            f"**Posted**  \n{posted}\n\n"
            f"**Why it matched**  \n{reasons}\n\n"
            f"**Summary**  \n{esc(job.snippet or 'No description was returned.')}"
        )
        self.detail_link.setEnabled(True)
        self.detail_link.setProperty("job_url", job.url)

    def _open_link(self):
        url = str(self.detail_link.property("job_url") or "")
        if url.lower().startswith(("http://", "https://")):
            QDesktopServices.openUrl(QUrl(url))

    def _save(self, exporter, path: str):
        try:
            exporter(self.response.jobs, path)
        except Exception as exc:  # e.g. file is open in Excel, or no write permission
            QMessageBox.critical(self, "Export failed", f"Could not save the file.\n\n{exc}")
            return
        self.status.setText(f"Saved {Path(path).name}")

    def export_csv(self):
        if not self.response:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "jobfinder-results.csv", "CSV files (*.csv)")
        if path:
            self._save(export_csv, path)

    def export_excel(self):
        if not self.response:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Excel", "jobfinder-results.xlsx", "Excel files (*.xlsx)")
        if path:
            self._save(export_excel, path)


class AboutPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)
        root.addLayout(PageHeader("About JobFinder", "A focused Windows desktop tool for finding and comparing recent job openings."))

        card = QFrame(objectName="Card")
        box = QVBoxLayout(card)
        box.setContentsMargins(20, 18, 20, 18)
        box.setSpacing(14)
        for title, body in (
            ("Search", "Build a structured search using roles, location, posting age, salary, work mode and other filters."),
            ("Quality", "JobFinder normalizes results, removes duplicates and ranks the strongest matches before the shortlist is shown."),
            ("Export", "Save the final shortlist directly to CSV or Excel using a standard Windows save dialog."),
            ("Privacy", "There is no application database in this version. Results stay in memory until you export them."),
        ):
            t = QLabel(title)
            t.setObjectName("SectionTitle")
            b = QLabel(body)
            b.setWordWrap(True)
            b.setObjectName("PageSubtitle")
            box.addWidget(t)
            box.addWidget(b)
        root.addWidget(card)
        root.addStretch()
