"""Editor window for .modinfo / .civ5proj files (Tkinter, part of Python).

Open a .modinfo or .civ5proj, edit it, save it as either format. Files are
hashed in the folder of the file being saved, as ModBuddy does. A .modinfo is
saved in the format it was opened in (File > .modinfo format: VP or ModBuddy;
the line endings of the opened file are kept).
"""
import copy
from pathlib import Path
from typing import Callable, List, Optional, Sequence
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import xml.etree.ElementTree as ET

from ..core.civ5proj import read_civ5proj
from ..core.models import Action, Association, EntryPoint, FileEntry, ModProject, new_mod_guid
from ..core.modinfo import modinfo_format, read_modinfo
from ..core.validate import ACTION_SETS, ACTION_TYPES, ENTRY_POINT_TYPES, validate_path
from ..core.xmltext import md5_of, mod_file_path

APP_TITLE = "Civilization V Mod Tools"
FILETYPES = [("Mod files", "*.modinfo *.civ5proj"), ("ModInfo", "*.modinfo"), ("ModBuddy project", "*.civ5proj")]
FLAGS = [("affects_saves", "Affects saved games"), ("supports_singleplayer", "Supports single player"),
         ("supports_multiplayer", "Supports multiplayer"), ("supports_hotseat", "Supports hot seat"),
         ("supports_mac", "Supports Mac"), ("hide_setup_game", "Hide setup game"),
         ("reload_audio", "Reload audio system"), ("reload_landmark", "Reload landmark system"),
         ("reload_strategic_view", "Reload strategic view system"), ("reload_unit", "Reload unit system")]
TEXTS = [("name", "Name"), ("mod_guid", "Mod id"), ("version", "Version"), ("min_save_version", "Min compatible save version"),
         ("teaser", "Teaser"), ("authors", "Authors"), ("special_thanks", "Special thanks"),
         ("homepage", "Homepage"), ("stability", "Stability")]


def default_import(path: Path) -> bool:
    """import="1" for a new file unless the database loads it: .sql, and .xml
    other than a UI context (<Context>, which the UI loads from the VFS)."""
    suffix = path.suffix.lower()
    if suffix == ".sql":
        return False
    if suffix == ".xml":
        try:
            for _, elem in ET.iterparse(str(path), events=("start",)):
                return elem.tag == "Context"
        except (ET.ParseError, OSError):
            return False
    return True


class Column:
    def __init__(self, key: str, title: str, width: int = 120, choices: Sequence[str] = (), boolean: bool = False):
        self.key, self.title, self.width, self.choices, self.boolean = key, title, width, choices, boolean


class RowDialog(tk.Toplevel):
    """Edit one row: one field per column."""

    def __init__(self, parent, title: str, columns: List[Column], values: dict):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.result: Optional[dict] = None
        self.vars = {}
        for r, col in enumerate(columns):
            ttk.Label(self, text=col.title).grid(row=r, column=0, sticky="w", padx=6, pady=3)
            if col.boolean:
                var = tk.BooleanVar(value=bool(values.get(col.key)))
                ttk.Checkbutton(self, variable=var).grid(row=r, column=1, sticky="w", padx=6)
            else:
                var = tk.StringVar(value=str(values.get(col.key, "")))
                widget = (ttk.Combobox(self, textvariable=var, values=list(col.choices), width=60) if col.choices
                          else ttk.Entry(self, textvariable=var, width=62))
                widget.grid(row=r, column=1, sticky="we", padx=6)
            self.vars[col.key] = var
        self.columnconfigure(1, weight=1)
        buttons = ttk.Frame(self)
        buttons.grid(row=len(columns), column=0, columnspan=2, pady=6)
        ttk.Button(buttons, text="OK", command=self._ok).pack(side="left", padx=4)
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left", padx=4)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())

    def _ok(self):
        self.result = {k: v.get() for k, v in self.vars.items()}
        self.destroy()


class Table(ttk.Frame):
    """A list of rows (dicts) with Add / Edit / Remove / Up / Down."""

    def __init__(self, parent, columns: List[Column], new_row: Callable[[], dict], extra_buttons=()):
        super().__init__(parent)
        self.columns, self.new_row, self.rows = columns, new_row, []
        self.tree = ttk.Treeview(self, columns=[c.key for c in columns], show="headings", selectmode="extended")
        for c in columns:
            self.tree.heading(c.key, text=c.title)
            self.tree.column(c.key, width=c.width, stretch=True)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        bar = ttk.Frame(self)
        bar.grid(row=1, column=0, columnspan=2, sticky="w", pady=4)
        for text, cmd in [("Add", self.add), ("Edit", self.edit), ("Remove", self.remove),
                          ("Up", lambda: self.move(-1)), ("Down", lambda: self.move(1)), *extra_buttons]:
            ttk.Button(bar, text=text, command=cmd).pack(side="left", padx=2)
        self.tree.bind("<Double-1>", lambda e: self.edit())
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def set_rows(self, rows: List[dict]):
        self.rows = [dict(r) for r in rows]
        self.refresh(select=())

    def refresh(self, select: Optional[Sequence[int]] = None):
        """Redraw the rows; keep the selection, or select the given rows."""
        keep = self._selected() if select is None else list(select)
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(self.rows):
            shown = [("yes" if row.get(c.key) else "") if c.boolean else row.get(c.key, "") for c in self.columns]
            self.tree.insert("", "end", iid=str(i), values=shown)
        keep = [str(i) for i in keep if 0 <= i < len(self.rows)]
        if keep:
            self.tree.selection_set(keep)
            self.tree.see(keep[0])

    def _selected(self) -> List[int]:
        return sorted(int(i) for i in self.tree.selection())

    def _dialog(self, values: dict) -> Optional[dict]:
        d = RowDialog(self, "Edit", self.columns, values)
        try:
            d.grab_set()
        except tk.TclError:  # some X11 window managers: not viewable yet; the dialog still works
            pass
        self.wait_window(d)
        if d.result is None:
            return None
        return {c.key: (d.result[c.key] if not c.boolean else bool(d.result[c.key])) for c in self.columns}

    def add(self):
        row = self._dialog(self.new_row())
        if row is not None:
            self.rows.append(row)
            self.refresh(select=[len(self.rows) - 1])

    def edit(self):
        sel = self._selected()
        if sel:
            row = self._dialog(self.rows[sel[0]])
            if row is not None:
                self.rows[sel[0]].update(row)
                self.refresh(select=[sel[0]])

    def remove(self):
        for i in reversed(self._selected()):
            del self.rows[i]
        self.refresh(select=())

    def move(self, delta: int):
        sel = self._selected()
        if len(sel) == 1 and 0 <= sel[0] + delta < len(self.rows):
            i = sel[0]
            self.rows[i], self.rows[i + delta] = self.rows[i + delta], self.rows[i]
            self.refresh(select=[i + delta])


ASSOC_COLUMNS = [Column("type", "Type", 70, ("Game", "Dlc", "Mod")), Column("name", "Name", 260),
                 Column("id", "Id", 280), Column("min_version", "Min", 70), Column("max_version", "Max", 70)]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1000x680")
        self.path: Optional[Path] = None
        self.project = ModProject(name="New Mod")
        self.saved = copy.deepcopy(self.project)  # what was last opened or saved, to spot unsaved changes
        self.style_var = tk.StringVar(value="vp")
        self.opened_format: Optional[tuple] = None  # (style, newline) of the opened .modinfo
        self._menu()
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=6, pady=6)
        nb.add(self._properties_tab(nb), text="Properties")
        nb.add(self._associations_tab(nb), text="Dependencies")
        self.files = Table(nb, [Column("path", "Path", 520), Column("import_to_vfs", "Import", 60, boolean=True),
                                Column("subtype", "SubType", 80), Column("md5", "MD5", 260)],
                           lambda: {"path": "", "import_to_vfs": False, "subtype": "Lua", "md5": ""},
                           [("Add files...", self.add_files), ("Refresh MD5s", self.refresh_md5)])
        nb.add(self.files, text="Files")
        self.actions = Table(nb, [Column("action_set", "Set", 160, ACTION_SETS),
                                  Column("action_type", "Type", 140, ACTION_TYPES), Column("filename", "File", 560)],
                             lambda: {"action_set": "OnModActivated", "action_type": "UpdateDatabase", "filename": ""})
        nb.add(self.actions, text="Actions")
        self.entries = Table(nb, [Column("type", "Type", 130, ENTRY_POINT_TYPES), Column("name", "Name", 200),
                                  Column("description", "Description", 260), Column("file", "File", 340)],
                             lambda: {"type": "InGameUIAddin", "name": "", "description": "", "file": ""})
        nb.add(self.entries, text="Entry points")
        self.status = tk.StringVar(value="New mod")
        ttk.Label(self, textvariable=self.status, anchor="w").pack(fill="x", padx=6, pady=(0, 4))
        self.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.load_project(self.project)

    # layout ------------------------------------------------------------------

    def _menu(self):
        bar = tk.Menu(self)
        m = tk.Menu(bar, tearoff=False)
        m.add_command(label="New", command=self.new, accelerator="Ctrl+N")
        m.add_command(label="Open...", command=self.open_dialog, accelerator="Ctrl+O")
        m.add_command(label="Save", command=self.save, accelerator="Ctrl+S")
        m.add_command(label="Save as .modinfo...", command=lambda: self.save_as(".modinfo"))
        m.add_command(label="Save as .civ5proj...", command=lambda: self.save_as(".civ5proj"))
        fmt = tk.Menu(m, tearoff=False)
        fmt.add_radiobutton(label="VP (LF, like generate_modinfo.py)", value="vp", variable=self.style_var)
        fmt.add_radiobutton(label="ModBuddy (CRLF)", value="modbuddy", variable=self.style_var)
        m.add_cascade(label=".modinfo format", menu=fmt)
        m.add_separator()
        m.add_command(label="Validate", command=self.validate)
        m.add_separator()
        m.add_command(label="Quit", command=self.quit_app)
        bar.add_cascade(label="File", menu=m)
        self.config(menu=bar)
        self.bind_all("<Control-n>", lambda e: self.new())
        self.bind_all("<Control-o>", lambda e: self.open_dialog())
        self.bind_all("<Control-s>", lambda e: self.save())

    def _properties_tab(self, parent):
        f = ttk.Frame(parent, padding=8)
        self.text_vars = {}
        for r, (key, label) in enumerate(TEXTS):
            ttk.Label(f, text=label).grid(row=r, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            ttk.Entry(f, textvariable=var, width=80).grid(row=r, column=1, sticky="we", pady=2)
            self.text_vars[key] = var
        ttk.Button(f, text="New id", command=lambda: self.text_vars["mod_guid"].set(new_mod_guid())).grid(row=1, column=2, padx=4)
        r = len(TEXTS)
        ttk.Label(f, text="Description").grid(row=r, column=0, sticky="nw", pady=2)
        self.description = tk.Text(f, height=8, width=80, wrap="word")
        self.description.grid(row=r, column=1, sticky="nsew", pady=2)
        flags = ttk.LabelFrame(f, text="Flags", padding=6)
        flags.grid(row=r + 1, column=0, columnspan=3, sticky="we", pady=6)
        self.flag_vars = {}
        for i, (key, label) in enumerate(FLAGS):
            var = tk.BooleanVar()
            ttk.Checkbutton(flags, text=label, variable=var).grid(row=i // 3, column=i % 3, sticky="w", padx=6)
            self.flag_vars[key] = var
        f.columnconfigure(1, weight=1)
        f.rowconfigure(r, weight=1)
        return f

    def _associations_tab(self, parent):
        f = ttk.Frame(parent, padding=4)
        self.assoc = {}
        for i, (key, title) in enumerate([("dependencies", "Dependencies"), ("references", "References"),
                                          ("blockers", "Blocks")]):
            box = ttk.LabelFrame(f, text=title, padding=4)
            box.grid(row=i, column=0, sticky="nsew", pady=3)
            t = Table(box, ASSOC_COLUMNS, lambda: {"type": "Mod", "name": "", "id": "", "min_version": "0",
                                                   "max_version": "999"})
            t.pack(fill="both", expand=True)
            self.assoc[key] = t
            f.rowconfigure(i, weight=1)
        f.columnconfigure(0, weight=1)
        return f

    # model <-> widgets -----------------------------------------------------

    def load_project(self, p: ModProject):
        self.project = p
        for key, var in self.text_vars.items():
            var.set(getattr(p, key))
        self.description.delete("1.0", "end")
        self.description.insert("1.0", p.description)
        for key, var in self.flag_vars.items():
            var.set(getattr(p, key))
        for key, table in self.assoc.items():
            table.set_rows([vars(a) for a in getattr(p, key)])
        self.files.set_rows([vars(f) for f in p.files])
        self.actions.set_rows([vars(a) for a in p.actions])
        self.entries.set_rows([vars(e) for e in p.entry_points])
        self.saved = copy.deepcopy(self.collect())

    def collect(self) -> ModProject:
        """The project as currently shown; fields the window does not show
        (ProjectGuid, folders, AssemblyName, ...) are kept from the loaded file.
        Text is taken as typed: the writers trim what the game trims."""
        p = self.project
        for key, var in self.text_vars.items():
            setattr(p, key, var.get())
        p.description = self.description.get("1.0", "end-1c")
        for key, var in self.flag_vars.items():
            setattr(p, key, bool(var.get()))
        for key, table in self.assoc.items():
            setattr(p, key, [Association(**r) for r in table.rows])
        p.files = [FileEntry(**r) for r in self.files.rows]
        p.actions = [Action(**r) for r in self.actions.rows]
        p.entry_points = [EntryPoint(**r) for r in self.entries.rows]
        return p

    def dirty(self) -> bool:
        """True if the window shows changes that were not saved."""
        return self.collect() != self.saved

    def confirm_discard(self) -> bool:
        """Before the shown mod is replaced or the window closes: offer to save
        unsaved changes. False if the user cancels (or the save fails)."""
        if not self.dirty():
            return True
        name = self.path.name if self.path else "the new mod"
        answer = messagebox.askyesnocancel("Unsaved changes", f"Save changes to {name}?", parent=self)
        if answer is None:
            return False
        return self.save() if answer else True

    # commands ----------------------------------------------------------------

    def mod_dir(self) -> Optional[Path]:
        return self.path.parent if self.path else None

    def _set_path(self, path: Optional[Path]):
        self.path = path
        self.title(f"{path.name} - {APP_TITLE}" if path else APP_TITLE)

    def quit_app(self):
        if self.confirm_discard():
            self.destroy()

    def new(self):
        if not self.confirm_discard():
            return
        self._set_path(None)
        self.style_var.set("vp")
        self.opened_format = None
        self.load_project(ModProject(name="New Mod"))
        self.status.set("New mod")

    def open_dialog(self):
        if not self.confirm_discard():
            return
        name = filedialog.askopenfilename(filetypes=FILETYPES)
        if name:
            self.open(Path(name))

    def open(self, path: Path):
        try:
            if path.suffix.lower() == ".civ5proj":
                p, fmt = read_civ5proj(path), None
            else:
                p, fmt = read_modinfo(path), modinfo_format(path)
        except Exception as e:  # noqa: BLE001 - shown to the user
            messagebox.showerror("Open", f"{path.name}: {e}")
            return
        self.opened_format = fmt
        if fmt:
            self.style_var.set(fmt[0])
        self._set_path(path)
        self.load_project(p)
        self.status.set(f"{path}: {len(p.files)} files, {len(p.actions)} actions, {len(p.entry_points)} entry points")

    def save(self) -> bool:
        if self.path is None:
            return self.save_as(".modinfo")
        return self.write(self.path)

    def save_as(self, suffix: str) -> bool:
        p = self.collect()
        default = p.modinfo_filename() if suffix == ".modinfo" else f"{p.base_name}.civ5proj"
        name = filedialog.asksaveasfilename(defaultextension=suffix, initialfile=default,
                                            initialdir=str(self.mod_dir() or Path.cwd()),
                                            filetypes=[(suffix, f"*{suffix}")])
        return self.write(Path(name)) if name else False

    def write(self, path: Path) -> bool:
        p = self.collect()
        try:
            if path.suffix.lower() == ".civ5proj":
                p.write_civ5proj(path, create_solution=True)
                note = f"also wrote {path.with_suffix('.civ5sln').name}"
            else:
                style = self.style_var.get()
                # the opened file's line ending, unless the user picked another format
                fmt = self.opened_format
                newline = fmt[1] if fmt and fmt[0] == style else None
                missing = p.write_modinfo(path, style=style, newline=newline)
                note = (f"{style} format; " +
                        (f"{len(missing)} listed files not found next to it" if missing else "all files hashed"))
        except Exception as e:  # noqa: BLE001 - shown to the user
            messagebox.showerror("Save", f"{path.name}: {e}")
            return False
        self._set_path(path)
        self.saved = copy.deepcopy(p)
        self.status.set(f"saved {path} ({note})")
        return True

    def add_files(self):
        base = self.mod_dir()
        if base is None:
            messagebox.showinfo("Add files", "Save or open the mod first: paths are relative to its folder.")
            return
        added = []
        for name in filedialog.askopenfilenames(initialdir=str(base)):
            try:
                rel = Path(name).resolve().relative_to(base.resolve())
            except ValueError:
                messagebox.showwarning("Add files", f"{name} is outside the mod folder {base}")
                continue
            path = str(rel).replace("/", "\\")
            if all(r["path"].lower() != path.lower() for r in self.files.rows):
                self.files.rows.append({"path": path, "import_to_vfs": default_import(Path(name)),
                                        "subtype": "Lua", "md5": md5_of(Path(name))})
                added.append(len(self.files.rows) - 1)
        self.files.refresh(select=added or None)

    def refresh_md5(self):
        base = self.mod_dir()
        if base is None:
            return
        missing = 0
        for r in self.files.rows:
            disk = mod_file_path(base, r["path"])
            if disk.is_file():
                r["md5"] = md5_of(disk)
            else:
                missing += 1
        self.files.refresh()
        self.status.set(f"MD5s refreshed; {missing} files not found")

    def validate(self):
        """Validate the file on disk; with unsaved changes, offer to save first."""
        note = ""
        if self.path is None or self.dirty():
            answer = messagebox.askyesnocancel("Validate", "Validate checks the saved file. Save the changes first?",
                                               parent=self)
            if answer is None or (answer and not self.save()) or self.path is None:
                return
            if not answer:
                note = "(unsaved changes are not included)\n\n"
        issues = validate_path(self.path)
        text = note + ("\n".join(str(i) for i in issues) or "No problems found.")
        win = tk.Toplevel(self)
        win.title(f"Validate {self.path.name}")
        box = tk.Text(win, width=110, height=30, wrap="none")
        box.insert("1.0", text)
        box.configure(state="disabled")
        box.pack(fill="both", expand=True)


def main(path: Optional[str] = None) -> int:
    app = App()
    if path:
        app.open(Path(path))
    app.mainloop()
    return 0


if __name__ == "__main__":
    main()
