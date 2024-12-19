import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QTabWidget,
    QLineEdit, QTextEdit, QCheckBox, QGroupBox, QScrollArea
)
from PyQt6.QtCore import Qt
from ..core.models import ModProject, FileEntry, Association, Action, EntryPoint
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModToolsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Civilization V Mod Tools")
        self.setMinimumSize(800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create toolbar
        toolbar = QHBoxLayout()
        layout.addLayout(toolbar)

        # Add buttons
        self.load_modinfo_btn = QPushButton("Load .modinfo")
        self.load_modinfo_btn.clicked.connect(self.load_modinfo)
        toolbar.addWidget(self.load_modinfo_btn)

        self.load_civ5proj_btn = QPushButton("Load .civ5proj")
        self.load_civ5proj_btn.clicked.connect(self.load_civ5proj)
        toolbar.addWidget(self.load_civ5proj_btn)

        self.save_modinfo_btn = QPushButton("Save as .modinfo")
        self.save_modinfo_btn.clicked.connect(self.save_modinfo)
        toolbar.addWidget(self.save_modinfo_btn)

        self.save_civ5proj_btn = QPushButton("Save as .civ5proj")
        self.save_civ5proj_btn.clicked.connect(self.save_civ5proj)
        toolbar.addWidget(self.save_civ5proj_btn)

        self.create_solution_cb = QCheckBox("Create/Update Solution")
        self.create_solution_cb.setChecked(True)
        toolbar.addWidget(self.create_solution_cb)

        toolbar.addStretch()

        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Create tabs
        self.create_basic_info_tab()
        self.create_dependencies_tab()
        self.create_files_tab()
        self.create_actions_tab()
        self.create_entry_points_tab()

        # Initialize project
        self.project = ModProject(name="New Mod")
        self.update_ui_from_project()

    def create_basic_info_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        scroll.setWidget(widget)
        self.tabs.addTab(scroll, "Basic Info")

        # Basic info fields
        self.name_edit = self.add_field(layout, "Name:")
        self.mod_guid_edit = self.add_field(layout, "Mod GUID:")
        self.version_edit = self.add_field(layout, "Version:")
        self.teaser_edit = self.add_field(layout, "Teaser:")
        
        self.description_edit = QTextEdit()
        layout.addWidget(QLabel("Description:"))
        layout.addWidget(self.description_edit)
        
        self.authors_edit = self.add_field(layout, "Authors:")
        self.homepage_edit = self.add_field(layout, "Homepage:")

        # Support flags
        flags_group = QGroupBox("Support Flags")
        flags_layout = QVBoxLayout()
        flags_group.setLayout(flags_layout)
        layout.addWidget(flags_group)

        self.affects_saves_cb = QCheckBox("Affects Saved Games")
        flags_layout.addWidget(self.affects_saves_cb)
        
        self.supports_sp_cb = QCheckBox("Supports Single Player")
        flags_layout.addWidget(self.supports_sp_cb)
        
        self.supports_mp_cb = QCheckBox("Supports Multiplayer")
        flags_layout.addWidget(self.supports_mp_cb)
        
        self.supports_hotseat_cb = QCheckBox("Supports Hot Seat")
        flags_layout.addWidget(self.supports_hotseat_cb)
        
        self.supports_mac_cb = QCheckBox("Supports Mac")
        flags_layout.addWidget(self.supports_mac_cb)
        
        self.hide_setup_cb = QCheckBox("Hide in Setup")
        flags_layout.addWidget(self.hide_setup_cb)

        layout.addStretch()

    def create_dependencies_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.tabs.addTab(widget, "Dependencies")

        # Dependencies list
        deps_group = QGroupBox("Dependencies")
        deps_layout = QVBoxLayout()
        deps_group.setLayout(deps_layout)
        layout.addWidget(deps_group)

        # Add dependency button
        add_dep_btn = QPushButton("Add Dependency")
        add_dep_btn.clicked.connect(self.add_dependency)
        deps_layout.addWidget(add_dep_btn)

        # Dependencies list widget
        self.deps_list = QVBoxLayout()
        deps_layout.addLayout(self.deps_list)

        # Blockers
        blocks_group = QGroupBox("Blockers")
        blocks_layout = QVBoxLayout()
        blocks_group.setLayout(blocks_layout)
        layout.addWidget(blocks_group)

        # Add blocker button
        add_block_btn = QPushButton("Add Blocker")
        add_block_btn.clicked.connect(self.add_blocker)
        blocks_layout.addWidget(add_block_btn)

        # Blockers list widget
        self.blocks_list = QVBoxLayout()
        blocks_layout.addLayout(self.blocks_list)

        layout.addStretch()

    def create_files_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.tabs.addTab(widget, "Files")

        # Add file button
        add_file_btn = QPushButton("Add File")
        add_file_btn.clicked.connect(self.add_file)
        layout.addWidget(add_file_btn)

        # Files list
        self.files_list = QVBoxLayout()
        layout.addLayout(self.files_list)
        layout.addStretch()

    def create_actions_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.tabs.addTab(widget, "Actions")

        # Add action button
        add_action_btn = QPushButton("Add Action")
        add_action_btn.clicked.connect(self.add_action)
        layout.addWidget(add_action_btn)

        # Actions list
        self.actions_list = QVBoxLayout()
        layout.addLayout(self.actions_list)
        layout.addStretch()

    def create_entry_points_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.tabs.addTab(widget, "Entry Points")

        # Add entry point button
        add_ep_btn = QPushButton("Add Entry Point")
        add_ep_btn.clicked.connect(self.add_entry_point)
        layout.addWidget(add_ep_btn)

        # Entry points list
        self.entry_points_list = QVBoxLayout()
        layout.addLayout(self.entry_points_list)
        layout.addStretch()

    def add_field(self, layout, label_text):
        label = QLabel(label_text)
        edit = QLineEdit()
        layout.addWidget(label)
        layout.addWidget(edit)
        return edit

    def update_ui_from_project(self):
        # Update basic info
        self.name_edit.setText(self.project.name)
        self.mod_guid_edit.setText(self.project.mod_guid)
        self.version_edit.setText(self.project.version)
        self.teaser_edit.setText(self.project.teaser)
        self.description_edit.setText(self.project.description)
        self.authors_edit.setText(self.project.authors)
        self.homepage_edit.setText(self.project.homepage)

        # Update flags
        self.affects_saves_cb.setChecked(self.project.affects_saves)
        self.supports_sp_cb.setChecked(self.project.supports_singleplayer)
        self.supports_mp_cb.setChecked(self.project.supports_multiplayer)
        self.supports_hotseat_cb.setChecked(self.project.supports_hotseat)
        self.supports_mac_cb.setChecked(self.project.supports_mac)
        self.hide_setup_cb.setChecked(self.project.hide_setup_game)

        # Clear and rebuild lists
        self.clear_layout(self.deps_list)
        self.clear_layout(self.blocks_list)
        self.clear_layout(self.files_list)
        self.clear_layout(self.actions_list)
        self.clear_layout(self.entry_points_list)

        # Rebuild dependencies
        for dep in self.project.dependencies:
            self.add_dependency_widget(dep)

        # Rebuild blockers
        for block in self.project.blockers:
            self.add_blocker_widget(block)

        # Rebuild files
        for file in self.project.files:
            self.add_file_widget(file)

        # Rebuild actions
        for action in self.project.actions:
            self.add_action_widget(action)

        # Rebuild entry points
        for ep in self.project.entry_points:
            self.add_entry_point_widget(ep)

    def update_project_from_ui(self):
        # Update basic info
        self.project.name = self.name_edit.text()
        self.project.mod_guid = self.mod_guid_edit.text()
        self.project.version = self.version_edit.text()
        self.project.teaser = self.teaser_edit.text()
        self.project.description = self.description_edit.toPlainText()
        self.project.authors = self.authors_edit.text()
        self.project.homepage = self.homepage_edit.text()

        # Update flags
        self.project.affects_saves = self.affects_saves_cb.isChecked()
        self.project.supports_singleplayer = self.supports_sp_cb.isChecked()
        self.project.supports_multiplayer = self.supports_mp_cb.isChecked()
        self.project.supports_hotseat = self.supports_hotseat_cb.isChecked()
        self.project.supports_mac = self.supports_mac_cb.isChecked()
        self.project.hide_setup_game = self.hide_setup_cb.isChecked()

    @staticmethod
    def clear_layout(layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def load_modinfo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open .modinfo file", "", "ModInfo Files (*.modinfo)")
        if file_path:
            try:
                self.project = ModProject.from_modinfo(Path(file_path))
                self.update_ui_from_project()
                QMessageBox.information(self, "Success", "ModInfo file loaded successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load ModInfo file: {e}")

    def load_civ5proj(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open .civ5proj file", "", "Civ5Proj Files (*.civ5proj)")
        if file_path:
            try:
                self.project = ModProject.from_civ5proj(Path(file_path))
                self.update_ui_from_project()
                QMessageBox.information(self, "Success", "Civ5Proj file loaded successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load Civ5Proj file: {e}")

    def save_modinfo(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save .modinfo file", "", "ModInfo Files (*.modinfo)")
        if file_path:
            try:
                self.update_project_from_ui()
                self.project.write_modinfo(Path(file_path))
                QMessageBox.information(self, "Success", "ModInfo file saved successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save ModInfo file: {e}")

    def save_civ5proj(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save .civ5proj file", "", "Civ5Proj Files (*.civ5proj)")
        if file_path:
            try:
                self.update_project_from_ui()
                create_solution = self.create_solution_cb.isChecked()
                output_path = Path(file_path)
                self.project.write_civ5proj(output_path, create_solution=create_solution)
                
                msg = "Civ5Proj file saved successfully"
                if create_solution:
                    msg += f"\nSolution file created/updated: {output_path.with_suffix('.civ5sln')}"
                QMessageBox.information(self, "Success", msg)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save Civ5Proj file: {e}")

    def add_dependency(self):
        dep = Association(type="Game")
        self.project.dependencies.append(dep)
        self.add_dependency_widget(dep)

    def add_blocker(self):
        block = Association(type="Mod")
        self.project.blockers.append(block)
        self.add_blocker_widget(block)

    def add_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select file to add")
        if file_path:
            file = FileEntry(path=file_path, import_to_vfs=True)
            self.project.files.append(file)
            self.add_file_widget(file)

    def add_action(self):
        action = Action(action_set="OnModActivated", action_type="UpdateDatabase", filename="")
        self.project.actions.append(action)
        self.add_action_widget(action)

    def add_entry_point(self):
        ep = EntryPoint(type="InGameUIAddin", file="")
        self.project.entry_points.append(ep)
        self.add_entry_point_widget(ep)

    def add_dependency_widget(self, dep):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        type_edit = QLineEdit(dep.type)
        name_edit = QLineEdit(dep.name)
        id_edit = QLineEdit(dep.id)
        min_ver_edit = QLineEdit(dep.min_version)
        max_ver_edit = QLineEdit(dep.max_version)
        
        layout.addWidget(QLabel("Type:"))
        layout.addWidget(type_edit)
        layout.addWidget(QLabel("Name:"))
        layout.addWidget(name_edit)
        layout.addWidget(QLabel("ID:"))
        layout.addWidget(id_edit)
        layout.addWidget(QLabel("Min Ver:"))
        layout.addWidget(min_ver_edit)
        layout.addWidget(QLabel("Max Ver:"))
        layout.addWidget(max_ver_edit)
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.remove_dependency(widget, dep))
        layout.addWidget(remove_btn)
        
        self.deps_list.addWidget(widget)

    def add_blocker_widget(self, block):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        name_edit = QLineEdit(block.name)
        id_edit = QLineEdit(block.id)
        min_ver_edit = QLineEdit(block.min_version)
        max_ver_edit = QLineEdit(block.max_version)
        
        layout.addWidget(QLabel("Name:"))
        layout.addWidget(name_edit)
        layout.addWidget(QLabel("ID:"))
        layout.addWidget(id_edit)
        layout.addWidget(QLabel("Min Ver:"))
        layout.addWidget(min_ver_edit)
        layout.addWidget(QLabel("Max Ver:"))
        layout.addWidget(max_ver_edit)
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.remove_blocker(widget, block))
        layout.addWidget(remove_btn)
        
        self.blocks_list.addWidget(widget)

    def add_file_widget(self, file):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        path_edit = QLineEdit(file.path)
        import_cb = QCheckBox("Import to VFS")
        import_cb.setChecked(file.import_to_vfs)
        
        layout.addWidget(path_edit)
        layout.addWidget(import_cb)
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.remove_file(widget, file))
        layout.addWidget(remove_btn)
        
        self.files_list.addWidget(widget)

    def add_action_widget(self, action):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        set_edit = QLineEdit(action.action_set)
        type_edit = QLineEdit(action.action_type)
        file_edit = QLineEdit(action.filename)
        
        layout.addWidget(QLabel("Set:"))
        layout.addWidget(set_edit)
        layout.addWidget(QLabel("Type:"))
        layout.addWidget(type_edit)
        layout.addWidget(QLabel("File:"))
        layout.addWidget(file_edit)
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.remove_action(widget, action))
        layout.addWidget(remove_btn)
        
        self.actions_list.addWidget(widget)

    def add_entry_point_widget(self, ep):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        type_edit = QLineEdit(ep.type)
        file_edit = QLineEdit(ep.file)
        name_edit = QLineEdit(ep.name)
        desc_edit = QLineEdit(ep.description)
        
        layout.addWidget(QLabel("Type:"))
        layout.addWidget(type_edit)
        layout.addWidget(QLabel("File:"))
        layout.addWidget(file_edit)
        layout.addWidget(QLabel("Name:"))
        layout.addWidget(name_edit)
        layout.addWidget(QLabel("Desc:"))
        layout.addWidget(desc_edit)
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.remove_entry_point(widget, ep))
        layout.addWidget(remove_btn)
        
        self.entry_points_list.addWidget(widget)

    def remove_dependency(self, widget, dep):
        self.project.dependencies.remove(dep)
        widget.deleteLater()

    def remove_blocker(self, widget, block):
        self.project.blockers.remove(block)
        widget.deleteLater()

    def remove_file(self, widget, file):
        self.project.files.remove(file)
        widget.deleteLater()

    def remove_action(self, widget, action):
        self.project.actions.remove(action)
        widget.deleteLater()

    def remove_entry_point(self, widget, ep):
        self.project.entry_points.remove(ep)
        widget.deleteLater()

def main():
    app = QApplication(sys.argv)
    window = ModToolsWindow()
    window.show()
    return app.exec()