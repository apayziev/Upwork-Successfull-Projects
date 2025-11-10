import sys
import asyncio
import logging

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QGroupBox, QSpinBox,
    QDateEdit, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt6.QtGui import QFont, QTextCursor

from lee_county_permit_scraper import LeeCountyPermitScraper


class ScraperThread(QThread):
    """Thread to run the scraper without blocking the GUI"""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, start_date, end_date, max_concurrent, output_file, user_data_dir, headless):
        super().__init__()
        self.start_date = start_date
        self.end_date = end_date
        self.max_concurrent = max_concurrent
        self.output_file = output_file
        self.user_data_dir = user_data_dir
        self.headless = headless
        self._is_running = True
        self.scraper = None
    
    def run(self):
        """Run the scraper in a separate thread"""
        try:
            # Set up logging to capture messages
            logger = logging.getLogger('main')
            logger.handlers.clear()
            
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            
            # Custom handler to emit signals
            class SignalHandler(logging.Handler):
                def __init__(self, signal):
                    super().__init__()
                    self.signal = signal
                
                def emit(self, record):
                    msg = self.format(record)
                    self.signal.emit(msg)
            
            signal_handler = SignalHandler(self.log_signal)
            signal_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(signal_handler)
            logger.setLevel(logging.INFO)
            
            # Run the scraper
            self.log_signal.emit("Starting scraper...")
            self.scraper = LeeCountyPermitScraper(
                output_file=self.output_file,
                user_data_dir=self.user_data_dir,
                max_concurrent=self.max_concurrent
            )
            
            # Run async code
            asyncio.run(self.scraper.run(self.start_date, self.end_date, extract_details=True, headless=self.headless))
            
            if self._is_running:
                total = len(self.scraper.all_permits)
                message = f"Scraping complete! Total permits: {total}\n\nOutput Folder:\n{self.scraper.output_dir}\n\nFiles:\n  • {self.scraper.output_file.name}\n  • {self.scraper.csv_file.name}"
                self.log_signal.emit("\n" + "="*50)
                self.log_signal.emit(message)
                self.log_signal.emit("="*50 + "\n")
                
                self.finished_signal.emit(True, message)
            else:
                message = f"Scraping stopped by user\n\nPermits collected: {len(self.scraper.all_permits)}\n\nOutput Folder:\n{self.scraper.output_dir}"
                self.log_signal.emit("Scraping stopped by user")
                self.finished_signal.emit(True, message)
        except Exception as e:
            error_msg = f"Error during scraping: {str(e)}"
            self.log_signal.emit(f"ERROR: {error_msg}")
            self.finished_signal.emit(False, error_msg)
    
    def stop(self):
        """Stop the scraper thread"""
        self._is_running = False
        if self.scraper:
            self.scraper.should_stop = True
        # Don't use terminate() as it's too aggressive, let it finish gracefully


class PermitScraperGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.scraper_thread = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Lee County Permit Scraper")
        self.setMinimumSize(900, 700)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("Lee County Permit Scraper")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Configuration Group
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout()
        config_group.setLayout(config_layout)
        
        # Date range selection
        date_layout = QHBoxLayout()
        
        # Start date
        start_label = QLabel("Start Date (mm/dd/yyyy):")
        start_label.setMinimumWidth(150)
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("MM/dd/yyyy")
        self.start_date_edit.setDate(QDate(2025, 10, 1))
        self.start_date_edit.setToolTip("Date format: mm/dd/yyyy")
        
        # End date
        end_label = QLabel("End Date (mm/dd/yyyy):")
        end_label.setMinimumWidth(150)
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat("MM/dd/yyyy")
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setToolTip("Date format: mm/dd/yyyy")
        
        date_layout.addWidget(start_label)
        date_layout.addWidget(self.start_date_edit)
        date_layout.addSpacing(20)
        date_layout.addWidget(end_label)
        date_layout.addWidget(self.end_date_edit)
        date_layout.addStretch()
        
        config_layout.addLayout(date_layout)
        
        # Concurrent tasks
        concurrent_layout = QHBoxLayout()
        concurrent_label = QLabel("Max Concurrent Tasks:")
        concurrent_label.setMinimumWidth(150)
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setMinimum(1)
        self.concurrent_spin.setMaximum(10)
        self.concurrent_spin.setValue(3)
        self.concurrent_spin.setToolTip("Number of permits to process simultaneously (1-10)")
        
        concurrent_layout.addWidget(concurrent_label)
        concurrent_layout.addWidget(self.concurrent_spin)
        concurrent_layout.addStretch()
        
        config_layout.addLayout(concurrent_layout)
        
        # Headless mode checkbox
        headless_layout = QHBoxLayout()
        self.headless_checkbox = QCheckBox("Run in Headless Mode (browser hidden) - Not Recommended")
        self.headless_checkbox.setChecked(False)  # Recommended: False (show browser)
        self.headless_checkbox.setToolTip("⚠️ Headless mode is NOT RECOMMENDED.\n\nWhen unchecked (recommended): Browser window is visible during scraping.\nThis allows you to monitor progress and troubleshoot issues.\n\nWhen checked: Browser runs hidden in the background.\nMay cause issues with some websites that detect headless browsers.")
        
        headless_layout.addWidget(self.headless_checkbox)
        headless_layout.addStretch()
        
        config_layout.addLayout(headless_layout)
        
        main_layout.addWidget(config_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Scraping")
        self.start_button.setFixedSize(120, 32)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.start_button.clicked.connect(self.start_scraping)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.setFixedSize(80, 32)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.stop_button.clicked.connect(self.stop_scraping)
        
        self.clear_button = QPushButton("Clear Logs")
        self.clear_button.setFixedSize(100, 32)
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        self.clear_button.clicked.connect(self.clear_logs)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.clear_button)
        
        main_layout.addLayout(button_layout)
        
        # Logs group
        logs_group = QGroupBox("Logs")
        logs_layout = QVBoxLayout()
        logs_group.setLayout(logs_layout)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #555;
                border-radius: 5px;
            }
        """)
        
        logs_layout.addWidget(self.log_text)
        
        main_layout.addWidget(logs_group)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def start_scraping(self):
        """Start the scraping process"""
        try:
            # Validate dates
            start_date = self.start_date_edit.date().toString("MM/dd/yyyy")
            end_date = self.end_date_edit.date().toString("MM/dd/yyyy")
            
            if self.start_date_edit.date() > self.end_date_edit.date():
                QMessageBox.warning(self, "Invalid Date Range", 
                                  "Start date must be before or equal to end date!")
                return
            
            # Get configuration
            max_concurrent = self.concurrent_spin.value()
            headless = self.headless_checkbox.isChecked()
            output_file = "permits_data.json"
            user_data_dir = "./chrome_profile"
            
            # Disable controls
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.start_date_edit.setEnabled(False)
            self.end_date_edit.setEnabled(False)
            self.concurrent_spin.setEnabled(False)
            self.headless_checkbox.setEnabled(False)
            
            # Clear logs
            self.log_text.clear()
            
            # Update status
            self.statusBar().showMessage("Scraping in progress...")
            self.append_log(f"Configuration:")
            self.append_log(f"  Start Date: {start_date}")
            self.append_log(f"  End Date: {end_date}")
            self.append_log(f"  Max Concurrent: {max_concurrent}")
            self.append_log(f"  Headless Mode: {'Yes' if headless else 'No (browser visible)'}")
            self.append_log("-" * 80)
            
            # Start scraper thread
            self.scraper_thread = ScraperThread(
                start_date=start_date,
                end_date=end_date,
                max_concurrent=max_concurrent,
                output_file=output_file,
                user_data_dir=user_data_dir,
                headless=headless
            )
            self.scraper_thread.log_signal.connect(self.append_log)
            self.scraper_thread.finished_signal.connect(self.scraping_finished)
            self.scraper_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start scraper: {str(e)}")
            self.reset_controls()
    
    def stop_scraping(self):
        """Stop the scraping process and quit the application"""
        if self.scraper_thread and self.scraper_thread.isRunning():
            reply = QMessageBox.question(
                self, "Stop Scraping",
                "Are you sure you want to stop the scraping process?\n\nThe browser will close, current progress will be saved, and the application will quit.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.append_log("\n[USER] Stop requested...")
                self.append_log("[SYSTEM] Closing browser and stopping scraper gracefully...")
                self.stop_button.setEnabled(False)
                self.statusBar().showMessage("Stopping scraper...")
                
                # Signal the scraper to stop
                self.scraper_thread.stop()
                
                # Wait for thread to finish (with timeout)
                if not self.scraper_thread.wait(10000):  # 10 second timeout
                    self.append_log("[WARNING] Scraper did not stop gracefully, forcing termination...")
                    self.scraper_thread.terminate()
                    self.scraper_thread.wait()
                
                self.append_log("[SYSTEM] Scraper stopped by user.")
                self.append_log("[SYSTEM] Quitting application...")
                
                # Quit the application
                QApplication.quit()
    
    def scraping_finished(self, success, message):
        """Handle scraping completion"""
        if success:
            self.statusBar().showMessage("Scraping completed successfully!")
            QMessageBox.information(self, "Success", message)
        else:
            self.statusBar().showMessage("Scraping failed!")
            QMessageBox.critical(self, "Error", message)
        
        self.reset_controls()
    
    def reset_controls(self):
        """Reset UI controls to initial state"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.start_date_edit.setEnabled(True)
        self.end_date_edit.setEnabled(True)
        self.concurrent_spin.setEnabled(True)
        self.headless_checkbox.setEnabled(True)
    
    def append_log(self, message):
        """Append a message to the log display"""
        self.log_text.append(message)
        # Auto-scroll to bottom
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
    
    def clear_logs(self):
        """Clear the log display"""
        self.log_text.clear()
        self.statusBar().showMessage("Logs cleared")
    
    def closeEvent(self, event):
        """Handle window close event"""
        if self.scraper_thread and self.scraper_thread.isRunning():
            reply = QMessageBox.question(
                self, "Close Application",
                "Scraping is in progress. Are you sure you want to close?\n\nThe browser will be closed and progress will be saved.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.append_log("\n[SYSTEM] Closing application, stopping scraper...")
                self.scraper_thread.stop()
                
                # Wait for thread to finish (with timeout)
                if not self.scraper_thread.wait(10000):  # 10 second timeout
                    self.scraper_thread.terminate()
                    self.scraper_thread.wait()
                
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """Main entry point for the GUI application"""
    app = QApplication(sys.argv)
    window = PermitScraperGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
