"""SNhelper desktop control panel.

Run with::

    python main.py

The default backend URL can be overridden with ``SNHELPER_API_URL``. Network
calls are executed in QThreads so the user interface remains responsive.
"""

from __future__ import annotations

import os
import json
import sys
from datetime import datetime
from typing import Any, Callable

import requests
from PyQt6.QtCore import QSettings, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


API_BASE_URL = os.getenv("SNHELPER_API_URL", "http://127.0.0.1:8000").rstrip("/")
REQUEST_TIMEOUT = 8
WINDOW_ASPECT_RATIO = 16 / 9


class ApiError(RuntimeError):
    """A user-facing error raised for failed API calls."""


class ApiClient:
    """Small requests-based client for the local LangChain Agent API."""

    def __init__(
        self,
        base_url: str = API_BASE_URL,
        api_key: str = "",
        timeout: int = REQUEST_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.timeout = timeout
        self.session = requests.Session()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = dict(kwargs.pop("headers", {}) or {})
        if self.api_key:
            headers.setdefault("Authorization", f"Bearer {self.api_key}")
            headers.setdefault("X-API-Key", self.api_key)
        if headers:
            kwargs["headers"] = headers
        try:
            response = self.session.request(
                method,
                f"{self.base_url}{path}",
                timeout=self.timeout,
                **kwargs,
            )
            response.raise_for_status()
        except requests.Timeout as exc:
            raise ApiError(f"连接超时（{self.base_url}，超过 {self.timeout} 秒）") from exc
        except requests.ConnectionError as exc:
            raise ApiError(f"无法连接服务（请确认地址和服务已启动）：{self.base_url}") from exc
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "未知"
            detail = ""
            if exc.response is not None:
                try:
                    payload = exc.response.json()
                    detail = f"：{payload.get('detail', payload)}" if payload else ""
                except ValueError:
                    detail = f"：{exc.response.text[:160]}" if exc.response.text else ""
            raise ApiError(f"Agent 返回 HTTP {status}{detail}") from exc
        except requests.RequestException as exc:
            raise ApiError(f"请求失败：{exc}") from exc

        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise ApiError("Agent 返回了无法解析的 JSON 数据") from exc

    def capture(self, content: str) -> Any:
        return self._request("POST", "/capture", json={"content": content})

    def get_tasks(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/tasks/today")
        values = payload.get("tasks", []) if isinstance(payload, dict) else payload
        if not isinstance(values, list):
            raise ApiError("任务接口返回格式不正确")
        return [item if isinstance(item, dict) else {"title": str(item)} for item in values]

    def update_task(self, task_id: Any, completed: bool) -> Any:
        return self._request("PATCH", f"/tasks/{task_id}", json={"completed": completed})

    def search(self, query: str) -> list[dict[str, Any]]:
        payload = self._request("GET", "/search", params={"q": query})
        values = payload.get("results", []) if isinstance(payload, dict) else payload
        if not isinstance(values, list):
            raise ApiError("检索接口返回格式不正确")
        return [item if isinstance(item, dict) else {"title": str(item), "content": str(item)} for item in values]

    def health(self) -> dict[str, Any]:
        payload = self._request("GET", "/health")
        return payload if isinstance(payload, dict) else {"status": str(payload)}


class ApiWorker(QThread):
    """Run one blocking API operation outside the Qt GUI thread."""

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, operation: Callable[[], Any]) -> None:
        super().__init__()
        self.operation = operation

    def run(self) -> None:
        try:
            self.succeeded.emit(self.operation())
        except Exception as exc:  # noqa: BLE001 - convert all network errors to UI text
            self.failed.emit(str(exc))


class QuickCapturePanel(QWidget):
    capture_requested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("灵感速记")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        subtitle = QLabel("把刚刚想到的内容先记录下来，稍后由 Agent 归档和整理。")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(subtitle)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText("输入一个想法、知识片段或待处理事项……")
        self.editor.setMinimumHeight(260)
        layout.addWidget(self.editor)

        actions = QHBoxLayout()
        actions.addStretch()
        self.send_button = QPushButton("发送到知识库")
        self.send_button.setObjectName("primaryButton")
        self.send_button.clicked.connect(self._emit_capture)
        actions.addWidget(self.send_button)
        layout.addLayout(actions)

        self.status = QLabel("等待输入")
        self.status.setObjectName("mutedLabel")
        layout.addWidget(self.status)
        layout.addStretch()

    def _emit_capture(self) -> None:
        content = self.editor.toPlainText().strip()
        if not content:
            self.status.setText("请先输入内容")
            return
        self.send_button.setEnabled(False)
        self.status.setText("正在发送……")
        self.capture_requested.emit(content)

    def set_result(self, message: str, clear: bool = False) -> None:
        self.send_button.setEnabled(True)
        if clear:
            self.editor.clear()
        self.status.setText(message)


class TaskPanel(QWidget):
    refresh_requested = pyqtSignal()
    task_toggled = pyqtSignal(object, bool)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel("执行清单")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        header.addWidget(self.refresh_button)
        layout.addLayout(header)

        self.list_widget = QListWidget()
        self.list_widget.setSpacing(4)
        layout.addWidget(self.list_widget)
        self.status = QLabel("点击刷新获取今天的微任务")
        self.status.setObjectName("mutedLabel")
        layout.addWidget(self.status)

    def set_loading(self, loading: bool) -> None:
        self.refresh_button.setEnabled(not loading)
        if loading:
            self.status.setText("正在加载任务……")

    def set_tasks(self, tasks: list[dict[str, Any]]) -> None:
        self.list_widget.clear()
        for index, task in enumerate(tasks):
            task_id = task.get("id", task.get("task_id", index))
            title = str(task.get("title", task.get("content", "未命名任务")))
            completed = bool(task.get("completed", task.get("done", False)))
            item = QListWidgetItem(self.list_widget)
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 4, 8, 4)
            checkbox = QCheckBox()
            checkbox.setChecked(completed)
            checkbox.setToolTip("标记任务完成")
            checkbox.toggled.connect(lambda checked, current_id=task_id: self.task_toggled.emit(current_id, checked))
            row_layout.addWidget(checkbox)
            label = QLabel(title)
            label.setWordWrap(True)
            row_layout.addWidget(label, 1)
            item.setSizeHint(row.sizeHint())
            self.list_widget.setItemWidget(item, row)
        self.status.setText(f"共 {len(tasks)} 项任务")

    def set_error(self, message: str) -> None:
        self.list_widget.clear()
        self.status.setText(message)


class SearchPanel(QWidget):
    search_requested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("知识检索")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        search_row = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("搜索已归档的想法和知识……")
        self.query.returnPressed.connect(self._emit_search)
        search_row.addWidget(self.query, 1)
        self.search_button = QPushButton("搜索")
        self.search_button.setObjectName("primaryButton")
        self.search_button.clicked.connect(self._emit_search)
        search_row.addWidget(self.search_button)
        layout.addLayout(search_row)

        content = QHBoxLayout()
        self.results = QListWidget()
        self.results.setMinimumWidth(260)
        self.results.itemClicked.connect(self._show_detail)
        content.addWidget(self.results)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setPlaceholderText("点击左侧结果查看详情")
        content.addWidget(self.detail, 1)
        layout.addLayout(content, 1)
        self.status = QLabel("输入关键词开始检索")
        self.status.setObjectName("mutedLabel")
        layout.addWidget(self.status)

    def _emit_search(self) -> None:
        query = self.query.text().strip()
        if not query:
            self.status.setText("请输入搜索关键词")
            return
        self.search_button.setEnabled(False)
        self.status.setText("正在检索……")
        self.search_requested.emit(query)

    def set_results(self, results: list[dict[str, Any]]) -> None:
        self.search_button.setEnabled(True)
        self.results.clear()
        self.detail.clear()
        for result in results:
            title = str(result.get("title", result.get("content", "无标题")))
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, result)
            self.results.addItem(item)
        self.status.setText(f"找到 {len(results)} 条结果")

    def set_error(self, message: str) -> None:
        self.search_button.setEnabled(True)
        self.status.setText(message)

    def _show_detail(self, item: QListWidgetItem) -> None:
        result = item.data(Qt.ItemDataRole.UserRole) or {}
        title = str(result.get("title", "无标题"))
        body = str(result.get("content", result.get("text", "")))
        tags = result.get("tags", [])
        tag_text = f"\n\n标签：{', '.join(map(str, tags))}" if tags else ""
        created = result.get("created_at", result.get("createdAt", ""))
        created_text = f"\n时间：{created}" if created else ""
        self.detail.setPlainText(f"{title}\n{'=' * max(10, len(title))}\n{body}{tag_text}{created_text}")


class StatusPanel(QWidget):
    refresh_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel("系统状态")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        header.addWidget(self.refresh_button)
        layout.addLayout(header)

        card = QFrame()
        card.setObjectName("statusCard")
        card_layout = QVBoxLayout(card)
        self.service_label = QLabel("服务状态：检查中……")
        self.service_label.setObjectName("statusValue")
        self.communication_label = QLabel("最近通信：暂无")
        self.communication_label.setObjectName("mutedLabel")
        card_layout.addWidget(self.service_label)
        card_layout.addWidget(self.communication_label)
        layout.addWidget(card)
        layout.addStretch()

    def set_loading(self, loading: bool) -> None:
        self.refresh_button.setEnabled(not loading)
        if loading:
            self.service_label.setText("服务状态：检查中……")

    def set_health(self, payload: dict[str, Any]) -> None:
        self.refresh_button.setEnabled(True)
        state = str(payload.get("status", payload.get("state", "online"))).lower()
        online = state in {"ok", "online", "healthy", "up"}
        self.service_label.setText(f"服务状态：{'在线' if online else state}")
        self.service_label.setProperty("online", online)
        self.service_label.style().unpolish(self.service_label)
        self.service_label.style().polish(self.service_label)
        self.communication_label.setText(f"最近通信：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def set_error(self, message: str) -> None:
        self.refresh_button.setEnabled(True)
        self.service_label.setText("服务状态：离线")
        self.communication_label.setText(
            f"最近通信：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}（{message}）"
        )


class RouterSettingsDialog(QDialog):
    """Edit named Router API endpoints and choose the active one."""

    MODULE_LABELS = {
        "capture": "灵感速记",
        "tasks": "执行清单",
        "search": "知识检索",
        "health": "系统状态",
    }

    def __init__(
        self,
        configs: dict[str, str],
        active_name: str,
        module_configs: dict[str, str],
        router_keys: dict[str, str],
        module_keys: dict[str, str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Router / API 设置")
        self.setMinimumSize(760, 520)
        self._result: tuple[dict[str, str], str, dict[str, str], dict[str, str], dict[str, str]] | None = None

        layout = QVBoxLayout(self)
        hint = QLabel("Router 可作为公共连接配置；每个功能模块也可以单独指定 API 地址和可选密钥。")
        hint.setObjectName("mutedLabel")
        layout.addWidget(hint)

        tabs = QTabWidget()
        router_tab = QWidget()
        router_layout = QVBoxLayout(router_tab)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Router 名称", "API 地址", "API Key"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        router_layout.addWidget(self.table, 1)
        for name, url in configs.items():
            self._add_row(name, url, router_keys.get(name, ""))

        row_actions = QHBoxLayout()
        add_button = QPushButton("新增 Router")
        add_button.clicked.connect(self._add_default_row)
        remove_button = QPushButton("删除选中")
        remove_button.clicked.connect(self._remove_selected_row)
        row_actions.addWidget(add_button)
        row_actions.addWidget(remove_button)
        row_actions.addStretch()
        row_actions.addWidget(QLabel("当前 Router"))
        self.active_combo = QComboBox()
        self.active_combo.setMinimumWidth(180)
        row_actions.addWidget(self.active_combo)
        router_layout.addLayout(row_actions)
        tabs.addTab(router_tab, "Router 配置")

        module_tab = QWidget()
        module_layout = QVBoxLayout(module_tab)
        module_hint = QLabel("各模块会直接请求这里填写的地址；密钥会以 Bearer 和 X-API-Key 请求头发送。")
        module_hint.setObjectName("mutedLabel")
        module_layout.addWidget(module_hint)
        self.module_table = QTableWidget(len(self.MODULE_LABELS), 3)
        self.module_table.setHorizontalHeaderLabels(["功能模块", "API 地址", "API Key"])
        self.module_table.horizontalHeader().setStretchLastSection(True)
        self.module_table.setAlternatingRowColors(True)
        for row, (key, label) in enumerate(self.MODULE_LABELS.items()):
            self.module_table.setItem(row, 0, QTableWidgetItem(label))
            self.module_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, key)
            self.module_table.setItem(row, 1, QTableWidgetItem(module_configs.get(key, configs.get(active_name, API_BASE_URL))))
            self.module_table.setItem(row, 2, QTableWidgetItem(module_keys.get(key, "")))
        module_layout.addWidget(self.module_table, 1)
        tabs.addTab(module_tab, "功能模块 API")
        self.tabs = tabs
        layout.addWidget(tabs, 1)

        test_row = QHBoxLayout()
        self.test_button = QPushButton("测试当前选中 API")
        self.test_button.clicked.connect(self._test_selected)
        self.test_status = QLabel("未测试")
        self.test_status.setObjectName("mutedLabel")
        test_row.addWidget(self.test_button)
        test_row.addWidget(self.test_status, 1)
        layout.addLayout(test_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._sync_active_combo(active_name)
        self.table.itemChanged.connect(lambda _item: self._sync_active_combo(self.active_combo.currentText()))

    def _selected_api(self) -> tuple[str, str, str]:
        if self.tabs.currentIndex() == 0:
            row = self.table.currentRow()
            if row < 0:
                row = max(0, self.active_combo.currentIndex())
            if row >= self.table.rowCount():
                return "Router", "", ""
            name = self.table.item(row, 0).text().strip()
            url = self.table.item(row, 1).text().strip().rstrip("/")
            api_key = self.table.item(row, 2).text().strip()
            return name, url, api_key
        row = self.module_table.currentRow()
        if row < 0:
            row = 0
        name = self.module_table.item(row, 0).text().strip()
        url = self.module_table.item(row, 1).text().strip().rstrip("/")
        api_key = self.module_table.item(row, 2).text().strip()
        return name, url, api_key

    def _test_selected(self) -> None:
        name, url, api_key = self._selected_api()
        if not url or not url.startswith(("http://", "https://")):
            self.test_status.setText("地址无效：请输入 http:// 或 https:// 开头的服务根地址")
            return
        self.test_button.setEnabled(False)
        self.test_status.setText(f"正在测试 {name} …")
        worker = ApiWorker(lambda: ApiClient(url, api_key).health())
        self._test_worker = worker
        worker.succeeded.connect(
            lambda payload: self.test_status.setText(
                f"{name} 连接成功：{payload.get('status', 'HTTP 200')}"
                if isinstance(payload, dict)
                else f"{name} 连接成功"
            )
        )
        worker.failed.connect(lambda message: self.test_status.setText(f"{name} 测试失败：{message}"))
        worker.finished.connect(lambda: self.test_button.setEnabled(True))
        worker.start()

    def _add_row(self, name: str, url: str, api_key: str = "") -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(name))
        self.table.setItem(row, 1, QTableWidgetItem(url))
        self.table.setItem(row, 2, QTableWidgetItem(api_key))

    def _add_default_row(self) -> None:
        existing = {self.table.item(row, 0).text() for row in range(self.table.rowCount())}
        index = 1
        name = f"Router {index}"
        while name in existing:
            index += 1
            name = f"Router {index}"
        self._add_row(name, API_BASE_URL, "")
        self.table.selectRow(self.table.rowCount() - 1)
        self._sync_active_combo(name)

    def _remove_selected_row(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self._sync_active_combo(self.active_combo.currentText())

    def _collect(self) -> tuple[dict[str, str], dict[str, str]] | None:
        configs: dict[str, str] = {}
        keys: dict[str, str] = {}
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            url_item = self.table.item(row, 1)
            key_item = self.table.item(row, 2)
            name = name_item.text().strip() if name_item else ""
            url = url_item.text().strip().rstrip("/") if url_item else ""
            api_key = key_item.text().strip() if key_item else ""
            if not name or not url or not url.startswith(("http://", "https://")):
                QMessageBox.warning(self, "配置无效", "Router 名称和 API 地址不能为空，地址必须以 http:// 或 https:// 开头。")
                return None
            if name in configs:
                QMessageBox.warning(self, "配置无效", f"Router 名称重复：{name}")
                return None
            configs[name] = url
            keys[name] = api_key
        if not configs:
            QMessageBox.warning(self, "配置无效", "至少需要保留一个 Router。")
            return None
        return configs, keys

    def _collect_module_configs(self) -> tuple[dict[str, str], dict[str, str]] | None:
        configs: dict[str, str] = {}
        keys: dict[str, str] = {}
        for row, key in enumerate(self.MODULE_LABELS):
            url_item = self.module_table.item(row, 1)
            key_item = self.module_table.item(row, 2)
            url = url_item.text().strip().rstrip("/") if url_item else ""
            api_key = key_item.text().strip() if key_item else ""
            if not url or not url.startswith(("http://", "https://")):
                QMessageBox.warning(
                    self,
                    "配置无效",
                    f"{self.MODULE_LABELS[key]} 的 API 地址不能为空，且必须以 http:// 或 https:// 开头。",
                )
                return None
            configs[key] = url
            keys[key] = api_key
        return configs, keys

    def _sync_active_combo(self, preferred: str) -> None:
        names = [
            self.table.item(row, 0).text().strip()
            for row in range(self.table.rowCount())
            if self.table.item(row, 0) and self.table.item(row, 0).text().strip()
        ]
        self.active_combo.blockSignals(True)
        self.active_combo.clear()
        self.active_combo.addItems(names)
        if preferred in names:
            self.active_combo.setCurrentText(preferred)
        elif names:
            self.active_combo.setCurrentIndex(0)
        self.active_combo.blockSignals(False)

    def _save(self) -> None:
        router_result = self._collect()
        if router_result is None:
            return
        configs, router_keys = router_result
        module_result = self._collect_module_configs()
        if module_result is None:
            return
        module_configs, module_keys = module_result
        active = self.active_combo.currentText()
        if active not in configs:
            active = next(iter(configs))
        self._result = (configs, active, module_configs, router_keys, module_keys)
        self.accept()

    @property
    def result(self) -> tuple[dict[str, str], str, dict[str, str], dict[str, str], dict[str, str]] | None:
        return self._result


class MainWindow(QMainWindow):
    def __init__(self, client: ApiClient | None = None) -> None:
        super().__init__()
        self.settings = QSettings("SNhelper", "Desktop")
        self.router_configs, self.active_router = self._read_router_configs()
        self.module_api_configs = self._read_module_api_configs()
        self.router_api_keys = self._read_api_keys("router_api_keys", self.router_configs)
        self.module_api_keys = self._read_api_keys("module_api_keys", RouterSettingsDialog.MODULE_LABELS)
        self.client = client or ApiClient(
            self.router_configs[self.active_router], self.router_api_keys.get(self.active_router, "")
        )
        self.workers: set[ApiWorker] = set()
        self._ratio_guard = False
        self.setWindowTitle("SNhelper · 第二大脑控制面板")
        self.setMinimumSize(1000, 562)
        self._build_ui()
        self._set_initial_geometry()
        self._load_tasks()
        self._check_health()

    def _read_router_configs(self) -> tuple[dict[str, str], str]:
        default = {"默认 Router": API_BASE_URL}
        raw = self.settings.value("router_configs", "")
        if raw:
            try:
                parsed = json.loads(str(raw))
                if isinstance(parsed, dict):
                    configs = {
                        str(name): str(url).rstrip("/")
                        for name, url in parsed.items()
                        if str(name).strip() and str(url).startswith(("http://", "https://"))
                    }
                    if configs:
                        active = str(self.settings.value("active_router", next(iter(configs))))
                        return configs, active if active in configs else next(iter(configs))
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        return default, "默认 Router"

    def _persist_router_configs(self) -> None:
        self.settings.setValue("router_configs", json.dumps(self.router_configs, ensure_ascii=False))
        self.settings.setValue("active_router", self.active_router)
        self.settings.setValue("module_api_configs", json.dumps(self.module_api_configs, ensure_ascii=False))
        self.settings.setValue("router_api_keys", json.dumps(self.router_api_keys, ensure_ascii=False))
        self.settings.setValue("module_api_keys", json.dumps(self.module_api_keys, ensure_ascii=False))

    def _read_api_keys(self, settings_key: str, names: dict[str, Any]) -> dict[str, str]:
        raw = self.settings.value(settings_key, "")
        if not raw:
            return {str(name): "" for name in names}
        try:
            parsed = json.loads(str(raw))
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed = {}
        if not isinstance(parsed, dict):
            parsed = {}
        return {str(name): str(parsed.get(name, "")).strip() for name in names}

    def _read_module_api_configs(self) -> dict[str, str]:
        fallback = {
            key: self.router_configs[self.active_router]
            for key in RouterSettingsDialog.MODULE_LABELS
        }
        raw = self.settings.value("module_api_configs", "")
        if not raw:
            return fallback
        try:
            parsed = json.loads(str(raw))
        except (TypeError, ValueError, json.JSONDecodeError):
            return fallback
        if not isinstance(parsed, dict):
            return fallback
        result: dict[str, str] = {}
        for key in RouterSettingsDialog.MODULE_LABELS:
            value = str(parsed.get(key, "")).strip().rstrip("/")
            result[key] = value if value.startswith(("http://", "https://")) else fallback[key]
        return result

    def _set_initial_geometry(self) -> None:
        """Start with a centered 16:9 window sized for the current screen."""
        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(1280, 720)
            return
        available = screen.availableGeometry()
        max_width = int(available.width() * 0.90)
        max_height = int(available.height() * 0.90)
        width = min(1280, max_width)
        height = round(width / WINDOW_ASPECT_RATIO)
        if height > max_height:
            height = max_height
            width = round(height * WINDOW_ASPECT_RATIO)
        width = max(800, width)
        height = max(500, height)
        self.resize(width, height)
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def _build_ui(self) -> None:
        root = QWidget()
        root.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(root)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)
        brand = QLabel("SNhelper")
        brand.setObjectName("brand")
        sidebar_layout.addWidget(brand)
        caption = QLabel("个人行动控制面板")
        caption.setObjectName("sidebarCaption")
        sidebar_layout.addWidget(caption)
        sidebar_layout.addSpacing(24)

        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.capture_panel = QuickCapturePanel()
        self.task_panel = TaskPanel()
        self.search_panel = SearchPanel()
        self.status_panel = StatusPanel()
        panels = [self.capture_panel, self.task_panel, self.search_panel, self.status_panel]
        labels = ["灵感速记", "执行清单", "知识检索", "系统状态"]
        self.nav_buttons: list[QPushButton] = []
        for index, (label, panel) in enumerate(zip(labels, panels)):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.clicked.connect(lambda _checked, current=index: self.stack.setCurrentIndex(current))
            sidebar_layout.addWidget(button)
            self.nav_buttons.append(button)
            self.stack.addWidget(panel)
        self.nav_buttons[0].setChecked(True)
        router_label = QLabel("当前 Router")
        router_label.setObjectName("sidebarCaption")
        sidebar_layout.addSpacing(18)
        sidebar_layout.addWidget(router_label)
        self.router_combo = QComboBox()
        self.router_combo.addItems(list(self.router_configs))
        self.router_combo.setCurrentText(self.active_router)
        self.router_combo.currentTextChanged.connect(self._switch_router)
        sidebar_layout.addWidget(self.router_combo)
        settings_button = QPushButton("Router / API 设置")
        settings_button.clicked.connect(self._open_router_settings)
        sidebar_layout.addWidget(settings_button)
        sidebar_layout.addStretch()
        self.endpoint_label = QLabel()
        self.endpoint_label.setObjectName("endpointLabel")
        self.endpoint_label.setWordWrap(True)
        sidebar_layout.addWidget(self.endpoint_label)
        self._update_endpoint_label()

        root_layout.addWidget(sidebar)
        content_frame = QFrame()
        content_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(28, 24, 28, 20)
        content_layout.addWidget(self.stack)
        root_layout.addWidget(content_frame, 1)

        self.capture_panel.capture_requested.connect(self._capture)
        self.task_panel.refresh_requested.connect(self._load_tasks)
        self.task_panel.task_toggled.connect(self._update_task)
        self.search_panel.search_requested.connect(self._search)
        self.status_panel.refresh_requested.connect(self._check_health)
        self.statusBar().showMessage("就绪")

    def _update_endpoint_label(self) -> None:
        self.endpoint_label.setText(f"当前 API\n{self.active_router}\n{self.client.base_url}")

    def _client_for(self, module: str) -> ApiClient:
        """Return the API client assigned to one feature module."""
        base_url = self.module_api_configs.get(module, self.client.base_url)
        api_key = self.module_api_keys.get(module, "")
        if base_url == self.client.base_url and api_key == self.client.api_key:
            return self.client
        return ApiClient(base_url, api_key)

    def _switch_router(self, name: str) -> None:
        if name not in self.router_configs or name == self.active_router:
            return
        previous_url = self.client.base_url
        previous_key = self.client.api_key
        self.active_router = name
        self.client = ApiClient(self.router_configs[name], self.router_api_keys.get(name, ""))
        # Modules still pointing at the previous Router follow the profile;
        # explicitly customized module URLs are preserved.
        previous_modules = dict(self.module_api_configs)
        previous_module_keys = dict(self.module_api_keys)
        self.module_api_configs = {
            key: self.client.base_url if value == previous_url else value
            for key, value in self.module_api_configs.items()
        }
        for key in self.module_api_keys:
            if previous_modules.get(key) == previous_url and previous_module_keys.get(key, "") == previous_key:
                self.module_api_keys[key] = self.client.api_key
        self._persist_router_configs()
        self._update_endpoint_label()
        self.statusBar().showMessage(f"已切换到 {name}", 3000)
        self._load_tasks()
        self._check_health()

    def _open_router_settings(self) -> None:
        previous_url = self.client.base_url
        previous_key = self.client.api_key
        previous_modules = dict(self.module_api_configs)
        previous_module_keys = dict(self.module_api_keys)
        dialog = RouterSettingsDialog(
            self.router_configs,
            self.active_router,
            self.module_api_configs,
            self.router_api_keys,
            self.module_api_keys,
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.result is None:
            return
        (
            self.router_configs,
            active,
            self.module_api_configs,
            self.router_api_keys,
            self.module_api_keys,
        ) = dialog.result
        self.active_router = active
        new_active_url = self.router_configs[active]
        new_active_key = self.router_api_keys.get(active, "")
        self.module_api_configs = {
            key: new_active_url
            if previous_modules.get(key) == previous_url and value == previous_url
            else value
            for key, value in self.module_api_configs.items()
        }
        self.module_api_keys = {
            key: new_active_key
            if previous_modules.get(key) == previous_url
            and previous_module_keys.get(key, "") == previous_key
            and value == previous_key
            else value
            for key, value in self.module_api_keys.items()
        }
        self.router_combo.blockSignals(True)
        self.router_combo.clear()
        self.router_combo.addItems(list(self.router_configs))
        self.router_combo.setCurrentText(active)
        self.router_combo.blockSignals(False)
        self.client = ApiClient(self.router_configs[active], self.router_api_keys.get(active, ""))
        self._persist_router_configs()
        self._update_endpoint_label()
        self.statusBar().showMessage(f"已保存并切换到 {active}", 3000)
        self._load_tasks()
        self._check_health()

    def _start(self, operation: Callable[[], Any], on_success: Callable[[Any], None], on_error: Callable[[str], None]) -> None:
        worker = ApiWorker(operation)
        self.workers.add(worker)
        worker.succeeded.connect(on_success)
        worker.failed.connect(on_error)
        worker.finished.connect(lambda current=worker: self.workers.discard(current))
        worker.start()

    def _capture(self, content: str) -> None:
        client = self._client_for("capture")
        self._start(
            lambda: client.capture(content),
            lambda _payload: self.capture_panel.set_result("已发送到知识库", clear=True),
            lambda message: self.capture_panel.set_result(message),
        )

    def _load_tasks(self) -> None:
        self.task_panel.set_loading(True)
        client = self._client_for("tasks")
        self._start(client.get_tasks, self.task_panel.set_tasks, self.task_panel.set_error)

    def _update_task(self, task_id: Any, completed: bool) -> None:
        self.statusBar().showMessage("正在保存任务状态……")
        client = self._client_for("tasks")
        self._start(
            lambda: client.update_task(task_id, completed),
            lambda _payload: self.statusBar().showMessage("任务状态已保存", 3000),
            lambda message: self.statusBar().showMessage(message, 5000),
        )

    def _search(self, query: str) -> None:
        client = self._client_for("search")
        self._start(lambda: client.search(query), self.search_panel.set_results, self.search_panel.set_error)

    def _check_health(self) -> None:
        self.status_panel.set_loading(True)
        client = self._client_for("health")
        self._start(client.health, self.status_panel.set_health, self.status_panel.set_error)

    def resizeEvent(self, event: Any) -> None:  # noqa: N802 - Qt API name
        super().resizeEvent(event)
        if self.isMaximized() or self.isFullScreen() or self._ratio_guard:
            return
        target_height = round(self.width() / WINDOW_ASPECT_RATIO)
        if abs(target_height - self.height()) <= 2:
            return
        self._ratio_guard = True
        try:
            self.resize(self.width(), target_height)
        finally:
            self._ratio_guard = False

    def closeEvent(self, event: Any) -> None:  # noqa: N802 - Qt API name
        for worker in list(self.workers):
            worker.quit()
            worker.wait(1000)
        event.accept()


def apply_style(app: QApplication) -> None:
    app.setStyleSheet(
        """
        QWidget { font-family: "Microsoft YaHei", "Segoe UI"; font-size: 14px; color: #1f2937; }
        QMainWindow { background: #f4f6f8; }
        #sidebar { background: #17212b; }
        #brand { color: #ffffff; font-size: 24px; font-weight: 700; }
        #sidebarCaption, #endpointLabel { color: #9fb0bf; }
        #sidebar QPushButton { color: #d8e1e8; background: transparent; border: 0; border-radius: 6px; text-align: left; padding: 12px 14px; }
        #sidebar QPushButton:hover { background: #243444; }
        #sidebar QPushButton:checked { background: #2d8cff; color: #ffffff; font-weight: 600; }
        #pageTitle { font-size: 26px; font-weight: 700; color: #111827; }
        #pageSubtitle, #mutedLabel { color: #6b7280; }
        QDialog { background: #f4f6f8; color: #111827; }
        QDialog QLabel { color: #1f2937; }
        QTabWidget::pane { background: #ffffff; border: 1px solid #c8d1da; }
        QTabBar::tab { background: #e5ebf0; color: #334155; padding: 9px 18px; border: 1px solid #c8d1da; }
        QTabBar::tab:selected { background: #ffffff; color: #111827; font-weight: 600; }
        QTableWidget { background: #ffffff; alternate-background-color: #f5f8fb; color: #111827; gridline-color: #d5dbe1; }
        QTableWidget::item:selected { background: #2d8cff; color: #ffffff; }
        QHeaderView::section { background: #e8edf2; color: #1f2937; padding: 7px; border: 0; border-bottom: 1px solid #c8d1da; }
        QComboBox { background: #ffffff; color: #111827; border: 1px solid #c8d1da; border-radius: 5px; padding: 7px 9px; }
        QComboBox QAbstractItemView { background: #ffffff; color: #111827; selection-background-color: #2d8cff; selection-color: #ffffff; }
        QTextEdit, QLineEdit, QListWidget { background: #ffffff; border: 1px solid #d5dbe1; border-radius: 6px; padding: 8px; }
        QTextEdit:focus, QLineEdit:focus, QListWidget:focus { border: 1px solid #2d8cff; }
        QPushButton { background: #e8edf2; border: 0; border-radius: 6px; padding: 9px 16px; }
        QPushButton:hover { background: #dce5ed; }
        #primaryButton { background: #2d8cff; color: white; font-weight: 600; }
        #primaryButton:hover { background: #1478e3; }
        #statusCard { background: #ffffff; border: 1px solid #d5dbe1; border-radius: 8px; }
        #statusValue { font-size: 20px; font-weight: 600; }
        #statusValue[online="true"] { color: #16803c; }
        #statusValue[online="false"] { color: #c0392b; }
        QStatusBar { color: #5b6570; }
        """
    )


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("SNhelper")
    app.setFont(QFont("Microsoft YaHei", 10))
    apply_style(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
