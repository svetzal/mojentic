"""
Real-time Tracer Event Viewer with Qt GUI.

This example demonstrates how to use the tracer system with a Qt GUI that displays
tracer events in real-time as they occur. Users can click on events to see detailed
information.

Requirements:
    pip install PyQt6

Usage:
    python tracer_qt_viewer.py
"""
import sys
import uuid
from datetime import datetime
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTableWidget, QTableWidgetItem, QTextEdit, QPushButton, QLabel,
        QHeaderView, QSplitter
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
    from PyQt6.QtGui import QColor, QFont
except ImportError:
    print("Error: PyQt6 is required for this example.")
    print("Install it with: pip install PyQt6")
    sys.exit(1)

from mojentic.tracer import TracerSystem, EventStore
from mojentic.tracer.tracer_events import (
    TracerEvent, LLMCallTracerEvent, LLMResponseTracerEvent,
    ToolCallTracerEvent, AgentInteractionTracerEvent
)
from mojentic.llm import LLMBroker
from mojentic.llm.tools.date_resolver import ResolveDateTool
from mojentic.llm.gateways.models import LLMMessage, MessageRole


class EventSignaler(QObject):
    """Qt signal emitter for tracer events (needed for thread safety)."""
    event_occurred = pyqtSignal(object)


class LLMWorker(QThread):
    """Worker thread for running LLM queries without blocking the UI."""

    finished = pyqtSignal(str)  # Emits response when complete
    error = pyqtSignal(str)  # Emits error message if something goes wrong

    def __init__(self, tracer: TracerSystem):
        super().__init__()
        self.tracer = tracer

    def run(self):
        """Execute the LLM query in a background thread."""
        try:
            # Create LLM broker with our tracer
            llm_broker = LLMBroker(model="qwen3:32b", tracer=self.tracer)

            # Create a date resolver tool
            date_tool = ResolveDateTool(tracer=self.tracer)

            # Generate a correlation ID for this request
            correlation_id = str(uuid.uuid4())

            # Create a test query
            messages = [
                LLMMessage(role=MessageRole.User, content="What is the date next Friday?")
            ]

            # Execute the query (this will generate tracer events)
            response = llm_broker.generate(
                messages,
                tools=[date_tool],
                correlation_id=correlation_id
            )

            self.finished.emit(response)

        except Exception as e:
            self.error.emit(str(e))


class TracerViewer(QMainWindow):
    """Qt window that displays tracer events in real-time."""
    
    def __init__(self):
        super().__init__()
        self.events = []
        self.event_signaler = EventSignaler()
        self.event_signaler.event_occurred.connect(self.add_event_to_table)
        self.worker = None  # Track the worker thread

        self.setWindowTitle("Mojentic Tracer - Real-time Event Viewer")
        self.setGeometry(100, 100, 1200, 700)

        self._setup_ui()
        self._setup_tracer()
        
    def _setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Title and controls
        header_layout = QHBoxLayout()
        title_label = QLabel("Real-time Tracer Events")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.clear_button = QPushButton("Clear Events")
        self.clear_button.clicked.connect(self.clear_events)
        header_layout.addWidget(self.clear_button)
        
        self.test_button = QPushButton("Run Test Query")
        self.test_button.clicked.connect(self.run_test_query)
        header_layout.addWidget(self.test_button)
        
        main_layout.addLayout(header_layout)
        
        # Event counter
        self.event_count_label = QLabel("Events: 0")
        main_layout.addWidget(self.event_count_label)
        
        # Splitter for table and details
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Events table
        self.events_table = QTableWidget()
        self.events_table.setColumnCount(5)
        self.events_table.setHorizontalHeaderLabels([
            "Time", "Type", "Correlation ID", "Summary", "Duration (ms)"
        ])
        self.events_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self.events_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.events_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.events_table.itemSelectionChanged.connect(self.show_event_details)
        splitter.addWidget(self.events_table)
        
        # Event details panel
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_label = QLabel("Event Details (click an event to see details)")
        details_label.setFont(QFont("", 10, QFont.Weight.Bold))
        details_layout.addWidget(details_label)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Courier", 9))
        details_layout.addWidget(self.details_text)
        
        splitter.addWidget(details_widget)
        splitter.setSizes([400, 300])
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.statusBar().showMessage("Ready. Waiting for tracer events...")
        
    def _setup_tracer(self):
        """Setup the tracer system with callback."""
        def on_event_stored(event):
            """Callback when an event is stored."""
            if isinstance(event, TracerEvent):
                self.event_signaler.event_occurred.emit(event)
        
        event_store = EventStore(on_store_callback=on_event_stored)
        self.tracer = TracerSystem(event_store=event_store)
        
    def add_event_to_table(self, event: TracerEvent):
        """Add a new event to the table."""
        self.events.append(event)
        
        row = self.events_table.rowCount()
        self.events_table.insertRow(row)
        
        # Time
        time_str = datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S.%f")[:-3]
        time_item = QTableWidgetItem(time_str)
        self.events_table.setItem(row, 0, time_item)
        
        # Type
        event_type = type(event).__name__.replace("TracerEvent", "")
        type_item = QTableWidgetItem(event_type)
        
        # Color code by type
        if isinstance(event, LLMCallTracerEvent):
            type_item.setBackground(QColor(107, 182, 96, 50))  # Mojility green
        elif isinstance(event, LLMResponseTracerEvent):
            type_item.setBackground(QColor(107, 182, 96, 100))
        elif isinstance(event, ToolCallTracerEvent):
            type_item.setBackground(QColor(102, 103, 103, 50))  # Mojility grey
        elif isinstance(event, AgentInteractionTracerEvent):
            type_item.setBackground(QColor(100, 149, 237, 50))  # Blue
        
        self.events_table.setItem(row, 1, type_item)
        
        # Correlation ID (shortened)
        corr_id_short = event.correlation_id[:8] if event.correlation_id else "N/A"
        corr_item = QTableWidgetItem(corr_id_short)
        corr_item.setToolTip(event.correlation_id)
        self.events_table.setItem(row, 2, corr_item)
        
        # Summary
        summary = self._get_event_summary(event)
        summary_item = QTableWidgetItem(summary)
        self.events_table.setItem(row, 3, summary_item)
        
        # Duration
        duration = ""
        if isinstance(event, (LLMResponseTracerEvent, ToolCallTracerEvent)) and event.call_duration_ms:
            duration = f"{event.call_duration_ms:.0f}"
        duration_item = QTableWidgetItem(duration)
        self.events_table.setItem(row, 4, duration_item)
        
        # Scroll to bottom and update counter
        self.events_table.scrollToBottom()
        self.event_count_label.setText(f"Events: {len(self.events)}")
        self.statusBar().showMessage(f"New event: {event_type}")
        
    def _get_event_summary(self, event: TracerEvent) -> str:
        """Get a brief summary of the event."""
        if isinstance(event, LLMCallTracerEvent):
            return f"Model: {event.model}, Messages: {len(event.messages)}"
        elif isinstance(event, LLMResponseTracerEvent):
            content_preview = event.content[:50] + "..." if len(event.content) > 50 else event.content
            return f"Model: {event.model}, Response: {content_preview}"
        elif isinstance(event, ToolCallTracerEvent):
            return f"Tool: {event.tool_name}, Caller: {event.caller or 'N/A'}"
        elif isinstance(event, AgentInteractionTracerEvent):
            return f"From: {event.from_agent} → To: {event.to_agent}"
        return "Unknown event type"
    
    def show_event_details(self):
        """Show detailed information about the selected event."""
        selected_rows = self.events_table.selectedIndexes()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        if row >= len(self.events):
            return
        
        event = self.events[row]
        details = self._format_event_details(event)
        self.details_text.setPlainText(details)
        
    def _format_event_details(self, event: TracerEvent) -> str:
        """Format detailed event information."""
        details = []
        details.append(f"Event Type: {type(event).__name__}")
        details.append(f"Timestamp: {datetime.fromtimestamp(event.timestamp)}")
        details.append(f"Correlation ID: {event.correlation_id}")
        details.append(f"Source: {event.source}")
        details.append("")
        
        if isinstance(event, LLMCallTracerEvent):
            details.append("=== LLM Call Details ===")
            details.append(f"Model: {event.model}")
            details.append(f"Temperature: {event.temperature}")
            details.append(f"Number of Messages: {len(event.messages)}")
            details.append("")
            details.append("Messages:")
            for i, msg in enumerate(event.messages, 1):
                details.append(f"  {i}. Role: {msg.get('role', 'N/A')}")
                content = msg.get('content', 'N/A')
                if len(str(content)) > 200:
                    content = str(content)[:200] + "..."
                details.append(f"     Content: {content}")
            if event.tools:
                details.append("")
                details.append(f"Available Tools: {[t.get('name') for t in event.tools]}")
        
        elif isinstance(event, LLMResponseTracerEvent):
            details.append("=== LLM Response Details ===")
            details.append(f"Model: {event.model}")
            details.append(f"Call Duration: {event.call_duration_ms:.2f} ms" if event.call_duration_ms else "N/A")
            details.append("")
            details.append("Response Content:")
            details.append(event.content)
            if event.tool_calls:
                details.append("")
                details.append(f"Tool Calls Made: {len(event.tool_calls)}")
                for i, tc in enumerate(event.tool_calls, 1):
                    details.append(f"  {i}. {tc}")
        
        elif isinstance(event, ToolCallTracerEvent):
            details.append("=== Tool Call Details ===")
            details.append(f"Tool Name: {event.tool_name}")
            details.append(f"Caller: {event.caller or 'N/A'}")
            details.append(f"Call Duration: {event.call_duration_ms:.2f} ms" if event.call_duration_ms else "Duration: N/A")
            details.append("")
            details.append("Arguments:")
            details.append(f"  {event.arguments}")
            details.append("")
            details.append("Result:")
            details.append(f"  {event.result}")
        
        elif isinstance(event, AgentInteractionTracerEvent):
            details.append("=== Agent Interaction Details ===")
            details.append(f"From Agent: {event.from_agent}")
            details.append(f"To Agent: {event.to_agent}")
            details.append(f"Event Type: {event.event_type}")
            if event.event_id:
                details.append(f"Event ID: {event.event_id}")
        
        return "\n".join(details)
    
    def clear_events(self):
        """Clear all events from the display."""
        self.events.clear()
        self.events_table.setRowCount(0)
        self.details_text.clear()
        self.event_count_label.setText("Events: 0")
        self.tracer.clear()
        self.statusBar().showMessage("Events cleared")
    
    def run_test_query(self):
        """Run a test query to demonstrate the tracer."""
        # Don't start a new query if one is already running
        if self.worker and self.worker.isRunning():
            self.statusBar().showMessage("Query already running, please wait...")
            return

        self.statusBar().showMessage("Running test query in background...")
        self.test_button.setEnabled(False)

        # Create and configure worker thread
        self.worker = LLMWorker(self.tracer)
        self.worker.finished.connect(self._on_query_finished)
        self.worker.error.connect(self._on_query_error)

        # Start the worker thread
        self.worker.start()

    def _on_query_finished(self, response: str):
        """Handle successful query completion."""
        self.statusBar().showMessage(f"Test query completed. Response: {response[:50]}...")
        self.test_button.setEnabled(True)

    def _on_query_error(self, error_msg: str):
        """Handle query error."""
        self.statusBar().showMessage(f"Error during test query: {error_msg}")
        self.test_button.setEnabled(True)

    def closeEvent(self, event):
        """Clean up worker thread when window closes."""
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait()
        event.accept()


def main():
    """Main entry point for the tracer viewer application."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = TracerViewer()
    window.show()
    
    print("\n" + "="*80)
    print("Mojentic Tracer - Real-time Event Viewer")
    print("="*80)
    print("\nThe Qt window is now open. You can:")
    print("  1. Click 'Run Test Query' to generate sample tracer events")
    print("  2. Click on any event row to see detailed information")
    print("  3. Click 'Clear Events' to reset the display")
    print("\nThe viewer will show events in real-time as they occur.")
    print("Close the window to exit.")
    print("="*80 + "\n")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
