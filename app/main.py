import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    # Initialize the underlying Qt application
    app = QApplication(sys.argv)
    
    # Set a base style that looks consistent across Windows/Linux if QSS isn't applied
    app.setStyle("Fusion")
    
    # Create and show our main window
    window = MainWindow()
    window.show()
    
    # Execute the application loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()