from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QMenuBar,
                            QMenu, QMessageBox, QTabWidget, QDialog)
from PyQt6.QtCore import Qt, QSettings, QPoint, QSize, QEvent
from PyQt6.QtGui import QAction, QKeySequence, QColor, QCloseEvent

from config import DisplayConfig
from gui.canvas import FireworksCanvas
from gui.controls import ControlPanel

class DetachableTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Enable mouse tracking on the tab bar
        self.tabBar().setMouseTracking(True)
        self.tabBar().installEventFilter(self)

        self.tabBar().setMovable(True)
        self.detached_tabs = {}
        self.default_tabs = {}
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.handle_tab_close)

    def eventFilter(self, obj, event):
        """Filter events to catch double clicks on the tab bar"""
        if obj == self.tabBar():
            if event.type() == QEvent.Type.MouseButtonDblClick:
                index = self.tabBar().tabAt(event.pos())
                if index != -1:
                    self.detach_tab(index)
                    return True
        return super().eventFilter(obj, event)

    def detach_tab(self, index):
        """Detach the tab into its own window"""
        if index == -1 or index in self.detached_tabs:
            return

        # Get the tab's data
        tab_name = self.tabText(index)
        tab_content = self.widget(index)

        if tab_content is None:
            return

        # Create and setup the detached window
        detached_window = DetachedTab(tab_name, tab_content, self)
        detached_window.setWindowTitle(tab_name)

        # Position the new window near but not on top of the parent
        parent_pos = self.mapToGlobal(self.pos())
        detached_window.move(parent_pos + QPoint(50, 50))

        # Set a reasonable default size
        detached_window.resize(600, 400)

        # Show the detached window
        detached_window.show()
        detached_window.raise_()
        detached_window.activateWindow()

        # Store reference to detached tab
        self.detached_tabs[index] = detached_window
        self.removeTab(index)

    def handle_tab_close(self, index):
        """Handle tab close button click"""
        if index in self.detached_tabs:
            self.detached_tabs[index].close()
            del self.detached_tabs[index]
        elif index in self.default_tabs:
            widget, label = self.default_tabs[index]
            self.removeTab(index)
            self.addTab(widget, label)
        else:
            self.removeTab(index)

    def addTab(self, widget: QWidget, label: str) -> int:
        """Override addTab to store original tab information"""
        index = super().addTab(widget, label)
        self.default_tabs[index] = (widget, label)
        return index

    def reattach_tab(self, content, name):
        """Reattach a detached tab back to the tab widget"""
        index = self.addTab(content, name)
        if index not in self.default_tabs:
            self.default_tabs[index] = (content, name)
        return index

class DetachedTab(QDialog):
    def __init__(self, name, content, tab_widget):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.name = name
        self.content = content
        self.tab_widget = tab_widget
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins for better appearance
        layout.addWidget(self.content)
        self.setLayout(layout)

    def closeEvent(self, event: QCloseEvent):
        """Handle window close by reattaching the tab"""
        self.tab_widget.reattach_tab(self.content, self.name)
        event.accept()

class FireworksApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings('Fireworks', 'FireworksApp')
        self.init_ui()
        self.load_settings()
        self.apply_controls_to_canvas()

    def init_ui(self):
        """Initialize the main window UI"""
        # Set window properties
        self.setWindowTitle(DisplayConfig.WINDOW_TITLE)
        self.setGeometry(100, 100,
                        DisplayConfig.WINDOW_WIDTH,
                        DisplayConfig.WINDOW_HEIGHT)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create menu bar
        self.create_menu_bar()

        # Create tab widget
        self.tab_widget = DetachableTabWidget()
        layout.addWidget(self.tab_widget)

        # Create and add canvas with a minimum size
        self.canvas = FireworksCanvas()
        self.canvas.setMinimumSize(400, 300)
        self.tab_widget.addTab(self.canvas, "Display")

        # Create and add control panel
        self.controls = ControlPanel()
        self.controls.setMinimumSize(400, 300)
        self.tab_widget.addTab(self.controls, "Controls")

        # Add tab instructions
        self.tab_widget.setTabToolTip(0, "Double-click to detach tab")
        self.tab_widget.setTabToolTip(1, "Double-click to detach tab")

        # Connect control signals
        self.connect_control_signals()

    def create_menu_bar(self):
        """Create the application menu bar"""
        menubar = self.menuBar()

        # Windows menu
        windows_menu = menubar.addMenu('Windows')

        # Attach all windows action
        attach_action = QAction('Attach All Windows', self)
        attach_action.triggered.connect(self.attach_all_windows)
        windows_menu.addAction(attach_action)

        # File menu
        file_menu = menubar.addMenu('File')

        # Save settings action
        save_action = QAction('Save Settings', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_settings)
        file_menu.addAction(save_action)

        # Reset settings action
        reset_action = QAction('Reset to Defaults', self)
        reset_action.setShortcut('Ctrl+R')
        reset_action.triggered.connect(self.reset_to_defaults)
        file_menu.addAction(reset_action)

        file_menu.addSeparator()

        # Exit action
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu('View')

        # Toggle controls action
        toggle_controls = QAction('Toggle Controls', self)
        toggle_controls.setShortcut('Ctrl+T')
        toggle_controls.triggered.connect(self.toggle_controls)
        view_menu.addAction(toggle_controls)

        # Toggle fullscreen action
        toggle_fullscreen = QAction('Toggle Fullscreen', self)
        toggle_fullscreen.setShortcut('F11')
        toggle_fullscreen.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(toggle_fullscreen)

        # Help menu
        help_menu = menubar.addMenu('Help')

        # About action
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def connect_control_signals(self):
        """Connect all control panel signals to their handlers"""
        # Particle controls
        self.controls.particle_count_changed.connect(
            self.canvas.set_particle_count)

        # Color controls
        self.controls.color_changed.connect(
            self.canvas.set_firework_color)
        self.controls.random_colors_toggled.connect(
            self.canvas.set_random_colors)

        # Pattern controls
        self.controls.pattern_changed.connect(
            self.canvas.set_pattern)
        self.controls.pattern_scale_signal.connect(
            self.canvas.set_pattern_scale)
        self.controls.pattern_rotation_signal.connect(
            self.canvas.set_pattern_rotation)
        self.controls.pattern_option_signal.connect(
            lambda opt, val: self.canvas.set_pattern_option(opt, val))
        self.controls.text_pattern_changed.connect(
            self.canvas.set_text_pattern)
        self.controls.pattern_random_toggled.connect(
            self.canvas.set_random_patterns)

        # Background controls
        self.controls.background_changed.connect(
            self.canvas.set_background)
        self.controls.weather_changed.connect(
            self.canvas.set_weather)

        # Physics controls
        self.controls.gravity_changed.connect(
            self.canvas.set_gravity)
        self.controls.launch_speed_changed.connect(
            self.canvas.set_launch_speed)

        # Launch controls
        self.controls.auto_launch_toggled.connect(
            self.canvas.set_auto_launch)
        self.controls.launch_button.clicked.connect(
            self.canvas.manual_launch)



    def apply_controls_to_canvas(self):
        """Give the canvas the values shown in the control panel (signals only fire on changes)"""
        values = self.controls.get_current_values()
        self.canvas.set_particle_count(values['particle_count'])
        self.canvas.set_random_colors(values['random_colors'])
        self.canvas.set_pattern(values['pattern'])
        self.canvas.set_background(values['background'])
        self.canvas.set_weather(values['weather'])
        self.canvas.set_gravity(values['gravity'])
        self.canvas.set_launch_speed(values['launch_speed'])
        self.canvas.set_auto_launch(values['auto_launch'])

    def save_settings(self):
        """Save current settings to QSettings"""
        values = self.controls.get_current_values()
        for key, value in values.items():
            self.settings.setValue(key, value)
        self.settings.sync()

        # Show confirmation
        QMessageBox.information(self, 'Settings Saved',
                              'Your settings have been saved.')

    def load_settings(self):
        """Load settings from QSettings"""
        # Load and apply each setting if it exists
        if self.settings.contains('particle_count'):
            self.controls.particle_slider.setValue(
                self.settings.value('particle_count', type=int))

        if self.settings.contains('pattern'):
            self.controls.pattern_combo.setCurrentText(
                self.settings.value('pattern'))

        if self.settings.contains('background'):
            self.controls.background_combo.setCurrentText(
                self.settings.value('background'))

        if self.settings.contains('weather'):
            self.controls.weather_combo.setCurrentText(
                self.settings.value('weather'))

        if self.settings.contains('gravity'):
            self.controls.gravity_slider.setValue(
                int(float(self.settings.value('gravity')) * 100))

        if self.settings.contains('launch_speed'):
            self.controls.speed_slider.setValue(
                int(float(self.settings.value('launch_speed')) * 10))

        if self.settings.contains('auto_launch'):
            self.controls.auto_launch.setChecked(
                self.settings.value('auto_launch', type=bool))

        if self.settings.contains('random_colors'):
            self.controls.random_color.setChecked(
                self.settings.value('random_colors', type=bool))

    def reset_to_defaults(self):
        """Reset all controls to default values"""
        reply = QMessageBox.question(
            self, 'Reset Settings',
            'Are you sure you want to reset all settings to defaults?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.controls.reset_to_defaults()
            self.canvas.reset_to_defaults()

    def toggle_controls(self):
        """Toggle control panel visibility"""
        self.controls.setVisible(not self.controls.isVisible())

    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            'About Fireworks Simulator',
            '''
            <h3>Fireworks Simulator</h3>
            <p>A PyQt6-based fireworks simulation application.</p>
            <p>Features:</p>
            <ul>
                <li>Realistic particle physics</li>
                <li>Custom patterns and effects</li>
                <li>Various background scenes</li>
                <li>Weather effects</li>
            </ul>
            '''
        )

    def attach_all_windows(self):
        """Reattach all detached tabs"""
        for window in list(self.tab_widget.detached_tabs.values()):
            window.close()

    def closeEvent(self, event):
        """Handle application close event"""
        reply = QMessageBox.question(
            self, 'Exit',
            'Are you sure you want to exit?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Save settings before closing
            self.attach_all_windows()
            self.save_settings()
            event.accept()
        else:
            event.ignore()
