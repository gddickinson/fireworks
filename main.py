#!/usr/bin/env python3
"""
Fireworks Simulation Application
Main entry point for the fireworks display simulator
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from gui import FireworksApp
from config import DisplayConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_application() -> QApplication:
    """Initialize and configure the QApplication instance"""
    # Create the application
    app = QApplication(sys.argv)

    # Set application-wide attributes
    app.setApplicationName("Fireworks Simulator")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("FireworksApp")

    # High DPI settings are now handled automatically in Qt6
    # But we can still set additional high DPI attributes if needed
    #app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    return app

def main():
    """Main application entry point"""
    try:
        # Initialize the application
        app = setup_application()
        logger.info("Application initialized")

        # Create and show the main window
        window = FireworksApp()
        window.setGeometry(100, 100,
                          DisplayConfig.WINDOW_WIDTH,
                          DisplayConfig.WINDOW_HEIGHT)
        window.show()
        logger.info("Main window displayed")

        # Start the event loop
        sys.exit(app.exec())

    except ImportError as e:
        logger.error(f"Failed to import PyQt6. Install it with: pip install PyQt6\n{e}", exc_info=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Application error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
