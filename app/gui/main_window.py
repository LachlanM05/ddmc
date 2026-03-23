import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QMessageBox, 
    QInputDialog, QListWidget, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QAbstractItemView
)
from PyQt6.QtCore import Qt

# Import the backend logic
from core.mod_logic import ProfileManager
from core.paths import PROFILES_DIR, MODS_DIR, ensure_directories
from core.workers import GameMonitorWorker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ensure_directories()
        
        self.setWindowTitle("DDLC Mod Manager")
        self.setMinimumSize(850, 550)
        self.is_dark_mode = True
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        self.setup_ui()
        self.apply_theme()
        self.refresh_all_lists()

    def setup_ui(self):
        """Builds the tabbed interface."""
        
        # --- Header ---
        header_layout = QHBoxLayout()
        title_label = QLabel("DDLC Profile Manager")
        title_label.setObjectName("HeaderTitle")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        self.main_layout.addLayout(header_layout)
        
        # --- Tabs Setup ---
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)
        
        self.setup_profiles_tab()
        self.setup_mods_tab()
        self.setup_settings_tab()

    def setup_profiles_tab(self):
        """Builds the Profiles management tab."""
        self.profiles_tab = QWidget()
        layout = QHBoxLayout(self.profiles_tab)
        
        # --- UPGRADED TO QTREEWIDGET ---
        self.profile_list = QTreeWidget()
        self.profile_list.setHeaderLabels(["Profile Name", "Installed Mod", "Playtime"])
        self.profile_list.setColumnWidth(0, 250)
        self.profile_list.setColumnWidth(1, 200)
        layout.addWidget(self.profile_list, stretch=3)
        
        # Right Side: Constrained Action Buttons
        button_panel = QVBoxLayout()
        
        self.launch_btn = QPushButton("Launch Selected Profile")
        self.launch_btn.setObjectName("PrimaryButton")
        self.launch_btn.clicked.connect(self.handle_launch)
        
        self.create_profile_btn = QPushButton("Create New Profile")
        self.create_profile_btn.clicked.connect(self.handle_create_profile)
        
        self.rename_profile_btn = QPushButton("Rename Profile")
        self.rename_profile_btn.clicked.connect(self.handle_rename_profile)
        
        self.export_profile_btn = QPushButton("Export Profile to Zip")
        self.export_profile_btn.clicked.connect(self.handle_export_profile)
        
        self.delete_profile_btn = QPushButton("Delete Profile")
        self.delete_profile_btn.setObjectName("DangerButton")
        self.delete_profile_btn.clicked.connect(self.handle_delete_profile)
        
        # Add buttons to panel
        button_panel.addWidget(self.launch_btn)
        button_panel.addSpacing(15)
        button_panel.addWidget(self.create_profile_btn)
        button_panel.addWidget(self.rename_profile_btn)
        button_panel.addWidget(self.export_profile_btn)
        button_panel.addStretch()
        button_panel.addWidget(self.delete_profile_btn)
        
        # Wrap panel in a widget to restrict its maximum width for tiling WMs
        panel_widget = QWidget()
        panel_widget.setLayout(button_panel)
        panel_widget.setMaximumWidth(250)
        
        layout.addWidget(panel_widget, stretch=1)
        self.tabs.addTab(self.profiles_tab, "Profiles")

    def setup_mods_tab(self):
        """Builds the Global Mods management tab."""
        self.mods_tab = QWidget()
        layout = QHBoxLayout(self.mods_tab)
        
        self.mod_list = QListWidget()
        layout.addWidget(self.mod_list, stretch=3)
        
        button_panel = QVBoxLayout()
        
        self.import_mod_btn = QPushButton("Import Mod (.zip)")
        self.import_mod_btn.clicked.connect(self.handle_import_mod)
        
        self.rename_mod_btn = QPushButton("Rename Mod")
        self.rename_mod_btn.clicked.connect(self.handle_rename_mod)
        
        self.delete_mod_btn = QPushButton("Delete Mod")
        self.delete_mod_btn.setObjectName("DangerButton")
        self.delete_mod_btn.clicked.connect(self.handle_delete_mod)
        
        button_panel.addWidget(self.import_mod_btn)
        button_panel.addWidget(self.rename_mod_btn)
        button_panel.addStretch()
        button_panel.addWidget(self.delete_mod_btn)
        
        panel_widget = QWidget()
        panel_widget.setLayout(button_panel)
        panel_widget.setMaximumWidth(250)
        
        layout.addWidget(panel_widget, stretch=1)
        self.tabs.addTab(self.mods_tab, "Global Mods")

    def setup_settings_tab(self):
        """Builds the Settings tab."""
        self.settings_tab = QWidget()
        layout = QVBoxLayout(self.settings_tab)
        
        self.import_vanilla_btn = QPushButton("Import / Update Vanilla DDLC")
        self.import_vanilla_btn.setMaximumWidth(300)
        self.import_vanilla_btn.clicked.connect(self.handle_import_vanilla)
        
        self.theme_btn = QPushButton("Toggle Light/Dark Mode")
        self.theme_btn.setMaximumWidth(300)
        self.theme_btn.clicked.connect(self.toggle_theme)
        
        layout.addWidget(self.import_vanilla_btn)
        layout.addWidget(self.theme_btn)
        layout.addStretch()
        
        self.tabs.addTab(self.settings_tab, "Settings")

    # --- Profile Actions ---

    def handle_launch(self):
        selected = self.profile_list.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Warning", "Select a profile to launch.")
            return
            
        # .text(0) ensures we grab the Profile Name from the first column!
        profile_name = selected[0].text(0) 
        
        try:
            # Disable the button so you can't click it twice and spawn two games
            self.launch_btn.setEnabled(False)
            self.launch_btn.setText("Game is Running...")
            
            # Start the game and capture the process object
            game_process = ProfileManager.launch_profile(profile_name)
            
            # Hand the process to our background tracker and start it
            self.monitor = GameMonitorWorker(profile_name, game_process)
            self.monitor.finished_playing.connect(self.on_game_closed)
            self.monitor.start()
            
        except Exception as e:
            self.launch_btn.setEnabled(True)
            self.launch_btn.setText("Launch Selected Profile")
            QMessageBox.critical(self, "Error", str(e))

    def on_game_closed(self, profile_name, session_time):
        """Triggered automatically when the background tracker sees the game die."""
        # Reset the UI button
        self.launch_btn.setEnabled(True)
        self.launch_btn.setText("Launch Selected Profile")
        
        # Save the time to the database and refresh the UI list to show the new time
        ProfileManager.add_playtime(profile_name, session_time)
        self.refresh_all_lists()

    def handle_create_profile(self):
        mods = ProfileManager.get_available_mods()
        if not mods:
            QMessageBox.warning(self, "Warning", "Import a mod globally first!")
            self.tabs.setCurrentIndex(1) # Switch to mods tab
            return

        profile_name, ok = QInputDialog.getText(self, "New Profile", "Enter profile name:")
        if ok and profile_name.strip():
            mod_choice, ok_mod = QInputDialog.getItem(
                self, "Select Mod", "Choose a mod to install:", mods, 0, False
            )
            if ok_mod:
                try:
                    self.setWindowTitle("Extracting, please wait...")
                    
                    # Clean up the name (e.g., "BlueSkies.zip" -> "BlueSkies")
                    clean_mod_name = mod_choice.replace(".zip", "")
                    
                    # Pass the clean name directly into the creation method
                    ProfileManager.create_profile(profile_name, mod_name=clean_mod_name)
                    
                    ProfileManager.install_zipped_mod(profile_name, MODS_DIR / mod_choice)
                    self.setWindowTitle("DDLC Mod Manager")
                    self.refresh_all_lists()
                except Exception as e:
                    self.setWindowTitle("DDLC Mod Manager")
                    QMessageBox.critical(self, "Error", str(e))

    def handle_rename_profile(self):
        selected = self.profile_list.selectedItems()
        if not selected: return
        
        old_name = selected[0].text(0)
        new_name, ok = QInputDialog.getText(self, "Rename", "New name:", text=old_name)
        if ok and new_name.strip() and new_name != old_name:
            try:
                ProfileManager.rename_profile(old_name, new_name.strip())
                self.refresh_all_lists()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def handle_export_profile(self):
        selected = self.profile_list.selectedItems()
        if not selected: return
        
        profile_name = selected[0].text(0)
        save_path, _ = QFileDialog.getSaveFileName(self, "Export Profile", f"{profile_name}.zip", "Zip Files (*.zip)")
        if save_path:
            try:
                self.setWindowTitle("Exporting, please wait...")
                ProfileManager.export_profile(profile_name, save_path)
                self.setWindowTitle("DDLC Mod Manager")
                QMessageBox.information(self, "Success", "Profile exported successfully!")
            except Exception as e:
                self.setWindowTitle("DDLC Mod Manager")
                QMessageBox.critical(self, "Error", str(e))

    def handle_delete_profile(self):
        selected = self.profile_list.selectedItems()
        if not selected: return
        
        profile_name = selected[0].text(0)
        reply = QMessageBox.question(self, "Confirm Delete", 
                                     f"Are you sure you want to delete '{profile_name}'?\nThis will destroy its isolated saves.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            ProfileManager.delete_profile(profile_name)
            self.refresh_all_lists()

    # --- Mod Actions ---

    def handle_import_mod(self):
        zip_path, _ = QFileDialog.getOpenFileName(self, "Select Mod Zip", "", "Zip Files (*.zip)")
        if zip_path:
            try:
                ProfileManager.import_mod_globally(zip_path)
                self.refresh_all_lists()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def handle_rename_mod(self):
        selected = self.mod_list.selectedItems()
        if not selected: return
        
        old_name = selected[0].text()
        new_name, ok = QInputDialog.getText(self, "Rename", "New name (keep .zip):", text=old_name)
        if ok and new_name.strip() and new_name != old_name:
            try:
                ProfileManager.rename_mod(old_name, new_name.strip())
                self.refresh_all_lists()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def handle_delete_mod(self):
        selected = self.mod_list.selectedItems()
        if not selected: return
        
        mod_name = selected[0].text()
        reply = QMessageBox.question(self, "Confirm Delete", f"Delete the global mod '{mod_name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            ProfileManager.delete_mod(mod_name)
            self.refresh_all_lists()

    # --- Utility Methods ---

    def handle_import_vanilla(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Pristine Vanilla DDLC Folder")
        if folder:
            try:
                ProfileManager.import_vanilla(folder)
                QMessageBox.information(self, "Success", "Vanilla DDLC imported!")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def refresh_all_lists(self):
        """Reads the directories and updates the UI lists."""
        self.profile_list.clear()
        if PROFILES_DIR.exists():
            for p in sorted([f.name for f in os.scandir(PROFILES_DIR) if f.is_dir()]):
                # Fetch the tracking data
                settings = ProfileManager.get_profile_settings(p)
                mod_name = settings.get("mod_name", "Unknown")
                seconds = settings.get("playtime_seconds", 0.0)
                
                # Format the time nicely
                if seconds < 60:
                    time_str = f"{int(seconds)} sec"
                elif seconds < 3600:
                    time_str = f"{int(seconds // 60)} min"
                else:
                    time_str = f"{seconds / 3600:.1f} hrs"
                
                # Add it to the multi-column list
                item = QTreeWidgetItem([p, mod_name, time_str])
                self.profile_list.addTopLevelItem(item)
                
        self.mod_list.clear()
        if MODS_DIR.exists():
            for m in sorted([f.name for f in os.scandir(MODS_DIR) if f.name.endswith('.zip')]):
                self.mod_list.addItem(m)

    # --- Theming ---

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()

    def apply_theme(self):
        if self.is_dark_mode:
            bg_color = "#1e1e2e"
            text_color = "#cdd6f4"
            btn_bg = "#313244"
            btn_hover = "#45475a"
            list_bg = "#181825"
            danger_color = "#f38ba8"
            primary_color = "#a6e3a1"
        else:
            bg_color = "#eff1f5"
            text_color = "#4c4f69"
            btn_bg = "#ccd0da"
            btn_hover = "#bcc0cc"
            list_bg = "#e6e9ef"
            danger_color = "#d20f39"
            primary_color = "#40a02b"

        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color: {bg_color}; color: {text_color}; font-family: 'Noto Sans'; font-size: 11pt; }}
            QLabel#HeaderTitle {{ font-size: 16pt; font-weight: bold; margin: 10px; }}
            QTabWidget::pane {{ border: 1px solid {btn_hover}; border-radius: 4px; }}
            QTabBar::tab {{ background: {btn_bg}; padding: 8px 20px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }}
            QTabBar::tab:selected {{ background: {btn_hover}; font-weight: bold; }}
            QPushButton {{ background-color: {btn_bg}; border: 1px solid {btn_hover}; border-radius: 4px; padding: 8px; }}
            QPushButton:hover {{ background-color: {btn_hover}; }}
            QPushButton#DangerButton {{ color: {danger_color}; border: 1px solid {danger_color}; }}
            QPushButton#DangerButton:hover {{ background-color: {danger_color}; color: {bg_color}; }}
            QPushButton#PrimaryButton {{ color: {primary_color}; border: 1px solid {primary_color}; font-weight: bold; }}
            QPushButton#PrimaryButton:hover {{ background-color: {primary_color}; color: {bg_color}; }}
            QTreeWidget, QListWidget {{ background-color: {list_bg}; border: 1px solid {btn_hover}; border-radius: 4px; padding: 4px; }}
            QTreeWidget::item:selected, QListWidget::item:selected {{ background-color: {btn_hover}; }}
            QHeaderView::section {{ background-color: {btn_bg}; color: {text_color}; padding: 4px; border: none; border-right: 1px solid {btn_hover}; }}
            
        """)