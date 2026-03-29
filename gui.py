#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GLib

import core


CSS = b"""
.store-row {
  border: 2px solid #dcdcdc;
  border-radius: 6px;
  margin: 4px;
  padding: 6px;
}
.store-row.selected {
  border: 2px solid #2ecc71;
}
.add-store {
  background-color: #28aa50;
  color: #ffffff;
  border-radius: 6px;
  padding: 4px 8px;
}
.repo-row {
  border: 2px solid #dcdcdc;
  border-radius: 6px;
  margin: 4px;
  padding: 6px;
}
.repo-row.selected {
  border: 2px solid #2ecc71;
}
"""


class RepoGui:
    """Represents a single repository row in the ListBox with Edit/Delete actions.

    Each instance creates a `ListBoxRow` stored in `self.row`.
    """

    def __init__(self, repo, parent_window, refresh_callback):
        self.repo = repo
        self.parent = parent_window
        self.refresh_callback = refresh_callback

        self.row = gtk.ListBoxRow()

        outer = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=4)
        outer.set_margin_top(4)
        outer.set_margin_bottom(4)
        try:
            outer.get_style_context().add_class("repo-row")
        except Exception:
            pass

        hbox = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=8)
        left_v = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=2)
        prefix = "✅" if getattr(repo, "is_active", True) else "❌"
        name_label = gtk.Label(label=f"{prefix}- {repo.name}", xalign=0)
        path_label = gtk.Label(label=getattr(repo, "path", ""), xalign=0)
        try:
            tip_label = gtk.Label(label=f"Add remote to your project:\ngit remote add local {repo.path}\n", xalign=0)
            tip_label.set_selectable(True)
        except Exception:
            tip_label = None
        name_label.set_xalign(0)
        path_label.set_xalign(0)
        try:
            name_label.set_selectable(True)
            path_label.set_selectable(True)
        except Exception:
            pass
        left_v.pack_start(name_label, False, False, 0)
        left_v.pack_start(path_label, False, False, 0)

        btn_box = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=6)
        edit_btn = gtk.Button(label="Edit")
        del_btn = gtk.Button(label="X")
        try:
            del_btn.get_style_context().add_class("destructive-action")
        except Exception:
            pass
        try:
            # make repo action buttons fixed-size like store buttons
            edit_btn.set_size_request(60, 24)
            del_btn.set_size_request(60, 24)
        except Exception:
            pass
        btn_box.pack_start(edit_btn, False, False, 0)
        btn_box.pack_start(del_btn, False, False, 0)

        hbox.pack_start(left_v, True, True, 0)
        hbox.pack_start(btn_box, False, False, 0)

        outer.pack_start(hbox, False, False, 0)

        # Description line
        desc_text = getattr(repo, 'description', '') or ''
        desc_label = gtk.Label(label=desc_text, xalign=0)
        desc_label.set_xalign(0)
        outer.pack_start(tip_label, False, False, 0)
        outer.pack_start(desc_label, False, False, 0)

        self.row.repo = repo
        self.row.add(outer)

        edit_btn.connect("clicked", self.on_edit_clicked)
        del_btn.connect("clicked", self.on_delete_clicked)

    def on_edit_clicked(self, _btn):
        # Inline dialog to edit repo name and description
        dialog = gtk.Dialog(title=f"Edit Repo {self.repo.name}", parent=self.parent, flags=gtk.DialogFlags.MODAL)
        dialog.add_button("Cancel", gtk.ResponseType.CANCEL)
        dialog.add_button("OK", gtk.ResponseType.OK)
        content = dialog.get_content_area()

        grid = gtk.Grid(column_spacing=6, row_spacing=6, margin=12)
        name_label = gtk.Label(label="Name:", xalign=0)
        name_entry = gtk.Entry()
        name_entry.set_text(self.repo.name)

        desc_label = gtk.Label(label="Description:", xalign=0)
        desc_view = gtk.TextView()
        try:
            buf = desc_view.get_buffer()
            buf.set_text(getattr(self.repo, "description", "") or "")
        except Exception:
            pass
        desc_scrolled = gtk.ScrolledWindow()
        desc_scrolled.set_policy(gtk.PolicyType.AUTOMATIC, gtk.PolicyType.AUTOMATIC)
        desc_scrolled.set_min_content_height(80)
        desc_scrolled.add(desc_view)

        grid.attach(name_label, 0, 0, 1, 1)
        grid.attach(name_entry, 1, 0, 1, 1)
        grid.attach(desc_label, 0, 1, 1, 1)
        grid.attach(desc_scrolled, 1, 1, 1, 1)
        content.add(grid)
        dialog.show_all()
        resp = dialog.run()
        if resp == gtk.ResponseType.OK:
            new_name = name_entry.get_text().strip()
            try:
                buf = desc_view.get_buffer()
                start = buf.get_start_iter()
                end = buf.get_end_iter()
                new_desc = buf.get_text(start, end, True).strip()
            except Exception:
                new_desc = ""

            # Basic uniqueness check within current store
            try:
                cfg = core.get_current_config()
                store_id = getattr(cfg, "current_store_id", None)
                if new_name != self.repo.name and core.Repos.filter(lambda k: k["name"] == new_name and k["store_id"] == store_id):
                    md = gtk.MessageDialog(self.parent, gtk.DialogFlags.MODAL, gtk.MessageType.ERROR, gtk.ButtonsType.OK, f"Repo with name '{new_name}' already exists in this store")
                    md.run()
                    md.destroy()
                    dialog.destroy()
                    return
            except Exception:
                pass

            try:
                self.repo.name = new_name
                self.repo.description = new_desc
                core.Repos.update(self.repo)
            except Exception as e:
                md = gtk.MessageDialog(self.parent, gtk.DialogFlags.MODAL, gtk.MessageType.ERROR, gtk.ButtonsType.OK, f"Error updating repo: {e}")
                md.run()
                md.destroy()
            else:
                try:
                    self.refresh_callback()
                except Exception:
                    pass
        dialog.destroy()

    def on_delete_clicked(self, _btn):
        # Confirm deletion of this repo from the database (do not delete files)
        repo = self.repo
        md = gtk.MessageDialog(self.parent, gtk.DialogFlags.MODAL, gtk.MessageType.QUESTION, gtk.ButtonsType.YES_NO, f"Delete repo '{repo.name}' from database? This will NOT delete files on disk.")
        resp = md.run()
        md.destroy()
        if resp != gtk.ResponseType.YES:
            return

        try:
            # Remove repo record
            core.Repos.delete(repo._id)
            # Remove reference from store
            try:
                store = core._get_store_by_id(getattr(repo, "store_id", None))
                if store and getattr(store, "repos_ids", None) and repo._id in store.repos_ids:
                    store.repos_ids.remove(repo._id)
                    core.Stores.update(store)
            except Exception:
                pass
        except Exception as e:
            err = gtk.MessageDialog(self.parent, gtk.DialogFlags.MODAL, gtk.MessageType.ERROR, gtk.ButtonsType.OK, f"Error deleting repo: {e}")
            err.run()
            err.destroy()
            return

        info = gtk.MessageDialog(self.parent, gtk.DialogFlags.MODAL, gtk.MessageType.INFO, gtk.ButtonsType.OK, f"Repo '{repo.name}' deleted from database")
        info.run()
        info.destroy()
        try:
            self.refresh_callback()
        except Exception:
            pass


class StoreGui:
    """Represents a single store row in the ListBox.

    The row contains a horizontal header (name/path + actions) and an optional description below.
    """

    def __init__(self, store, parent_window, refresh_callback):
        self.store = store
        self.parent = parent_window
        self.refresh_callback = refresh_callback

        self.row = gtk.ListBoxRow()

        outer = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=4)
        outer.set_margin_top(4)
        outer.set_margin_bottom(4)
        try:
            outer.get_style_context().add_class("store-row")
        except Exception:
            pass

        # Header: name/path and action buttons
        hbox = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=8)

        left_v = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=2)
        availability = "✅" if getattr(store, "is_active", True) else "❌"
        name_label = gtk.Label(label=f"{availability} {store.name}", xalign=0)
        path_label = gtk.Label(label=store.path or "", xalign=0)
        name_label.set_xalign(0)
        path_label.set_xalign(0)
        left_v.pack_start(name_label, False, False, 0)
        left_v.pack_start(path_label, False, False, 0)

        btn_box = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=6)
        edit_btn = gtk.Button(label="Edit")
        del_btn = gtk.Button(label="X")
        try:
            del_btn.get_style_context().add_class("destructive-action")
        except Exception:
            pass
        try:
            # make store action buttons fixed-size to match repo buttons
            edit_btn.set_size_request(60, 24)
            del_btn.set_size_request(60, 24)
        except Exception:
            pass
        btn_box.pack_start(edit_btn, False, False, 0)
        btn_box.pack_start(del_btn, False, False, 0)

        hbox.pack_start(left_v, True, True, 0)
        hbox.pack_start(btn_box, False, False, 0)

        outer.pack_start(hbox, False, False, 0)

        if getattr(store, "description", None):
            desc_label = gtk.Label(label=store.description, xalign=0)
            desc_label.set_line_wrap(True)
            desc_label.set_xalign(0)
            outer.pack_start(desc_label, False, False, 0)

        try:
            cfg = core.get_current_config()
            if getattr(store, "_id", None) == getattr(cfg, "current_store_id", None):
                outer.get_style_context().add_class("selected")
        except Exception:
            pass

        self.row.store = store
        self.row.add(outer)

        edit_btn.connect("clicked", self.on_edit_clicked)
        del_btn.connect("clicked", self.on_delete_clicked)

    def on_delete_clicked(self, button):
        md = gtk.MessageDialog(self.parent, gtk.DialogFlags.MODAL, gtk.MessageType.QUESTION, gtk.ButtonsType.YES_NO, f"Delete store '{self.store.name}'?")
        resp = md.run()
        md.destroy()
        if resp == gtk.ResponseType.YES:
            res = core.delete_store_by_name(self.store.name)
            info = gtk.MessageDialog(self.parent, gtk.DialogFlags.MODAL, gtk.MessageType.INFO, gtk.ButtonsType.OK, str(res))
            info.run()
            info.destroy()
            try:
                self.refresh_callback()
            except Exception:
                pass

    def on_edit_clicked(self, button):
        initial = {"name": self.store.name, "path": self.store.path, "description": getattr(self.store, "description", "")}
        res = self.parent.open_store_dialog("Edit Store", initial=initial)
        if not res:
            return
        name, path, desc = res

        if name != self.store.name and core.Stores.filter(lambda k: k["name"] == name):
            md = gtk.MessageDialog(self.parent, gtk.DialogFlags.MODAL, gtk.MessageType.ERROR, gtk.ButtonsType.OK, f"Store with name '{name}' already exists")
            md.run()
            md.destroy()
            return

        p = Path(path).expanduser()
        if not p.exists() or not p.is_dir():
            md = gtk.MessageDialog(self.parent, gtk.DialogFlags.MODAL, gtk.MessageType.ERROR, gtk.ButtonsType.OK, f"Path '{path}' is not an existing directory")
            md.run()
            md.destroy()
            return

        try:
            self.store.name = name
            self.store.path = path
            self.store.description = desc
            core.Stores.update(self.store)
        except Exception as e:
            md = gtk.MessageDialog(self.parent, gtk.DialogFlags.MODAL, gtk.MessageType.ERROR, gtk.ButtonsType.OK, f"Error updating store: {e}")
            md.run()
            md.destroy()
            return

        info = gtk.MessageDialog(self.parent, gtk.DialogFlags.MODAL, gtk.MessageType.INFO, gtk.ButtonsType.OK, "Store updated")
        info.run()
        info.destroy()
        try:
            self.refresh_callback()
        except Exception:
            pass


class MainWindow(gtk.Window):
    def __init__(self):
        super().__init__()
        self.set_title("Local Git Manager")
        self.set_default_size(900, 600)
        try:
            self.set_default_icon_from_file("icon_git.png")
        except Exception:
            pass

        # Apply CSS
        try:
            provider = gtk.CssProvider()
            provider.load_from_data(CSS)
            screen = gdk.Screen.get_default()
            gtk.StyleContext.add_provider_for_screen(screen, provider, gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        except Exception:
            pass

        notebook = gtk.Notebook()
        self.add(notebook)

        # Stores tab
        page1 = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=6)

        header = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_top(8)
        header.set_margin_bottom(8)

        add_btn = gtk.Button(label="+ Add Store")
        try:
            add_btn.get_style_context().add_class("add-store")
        except Exception:
            pass
        header.pack_start(add_btn, False, False, 0)

        self.selected_store_label = gtk.Label()
        self.selected_store_label.set_markup('<b>No store selected</b>')
        header.pack_start(self.selected_store_label, False, False, 0)

        page1.pack_start(header, False, False, 0)

        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.PolicyType.AUTOMATIC, gtk.PolicyType.AUTOMATIC)
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)

        self.stores_listbox = gtk.ListBox()
        self.stores_listbox.set_selection_mode(gtk.SelectionMode.SINGLE)
        scrolled.add(self.stores_listbox)
        page1.pack_start(scrolled, True, True, 0)

        notebook.append_page(page1, gtk.Label(label="Stores"))
        # keep references to pages so we can refresh when the user switches tabs
        self.stores_page = page1

        # Repositories tab
        page2 = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=6)
        # Header for repositories: Add buttons
        repo_header = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=8)
        repo_header.set_margin_top(8)
        repo_header.set_margin_bottom(8)

        self.add_repo_btn = gtk.Button(label="+ Add Repo")
        self.create_new_btn = gtk.Button(label="+ Create New Repo")
        try:
            self.add_repo_btn.get_style_context().add_class("add-store")
            self.create_new_btn.get_style_context().add_class("add-store")
        except Exception:
            pass
        repo_header.pack_start(self.add_repo_btn, False, False, 0)
        repo_header.pack_start(self.create_new_btn, False, False, 0)
        page2.pack_start(repo_header, False, False, 0)

        repo_scrolled = gtk.ScrolledWindow()
        repo_scrolled.set_policy(gtk.PolicyType.AUTOMATIC, gtk.PolicyType.AUTOMATIC)
        repo_scrolled.set_hexpand(True)
        repo_scrolled.set_vexpand(True)

        self.repos_listbox = gtk.ListBox()
        self.repos_listbox.set_selection_mode(gtk.SelectionMode.NONE)
        repo_scrolled.add(self.repos_listbox)
        page2.pack_start(repo_scrolled, True, True, 0)

        notebook.append_page(page2, gtk.Label(label="Repositories"))
        self.repos_page = page2

        # refresh lists when the user switches tabs
        def _on_switch(nb, page, page_num):
            try:
                if page is self.stores_page:
                    self.populate_stores()
                elif page is self.repos_page:
                    self.populate_repos()
            except Exception:
                pass

        try:
            notebook.connect("switch-page", _on_switch)
        except Exception:
            pass

        # Settings tab (placeholder)
        page3 = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=6)
        label3 = gtk.Label(label="Contenu de l'onglet 3")
        page3.pack_start(label3, True, True, 0)
        notebook.append_page(page3, gtk.Label(label="Settings"))

        # Signals
        add_btn.connect("clicked", self.on_add_store_clicked)
        self.stores_listbox.connect("row-selected", self.on_row_selected)
        # repo signals
        try:
            self.add_repo_btn.connect("clicked", self.on_add_repo_clicked)
            self.create_new_btn.connect("clicked", self.on_create_new_repo_clicked)
        except Exception:
            pass

        # expose helper
        self.open_store_dialog = self._open_store_dialog

        # initial population
        self.populate_stores()
        self.populate_repos()
        # ensure repo action buttons reflect current selection
        try:
            self._update_repo_buttons_state()
        except Exception:
            pass

    def _update_repo_buttons_state(self):
        """Enable or disable repository action buttons depending on active store."""
        try:
            cfg = core.get_current_config()
            store = core._get_store_by_id(getattr(cfg, "current_store_id", None))
            enabled = bool(store and getattr(store, "is_active", True))
        except Exception:
            enabled = False
        try:
            self.add_repo_btn.set_sensitive(enabled)
        except Exception:
            pass
        try:
            self.create_new_btn.set_sensitive(enabled)
        except Exception:
            pass

    # Dialog to add/edit stores
    def _open_store_dialog(self, title: str, initial: dict | None = None) -> tuple | None:
        dialog = gtk.Dialog(title=title, parent=self, flags=gtk.DialogFlags.MODAL)
        dialog.add_button("Cancel", gtk.ResponseType.CANCEL)
        dialog.add_button("OK", gtk.ResponseType.OK)
        content = dialog.get_content_area()

        grid = gtk.Grid(column_spacing=6, row_spacing=6, margin=12)

        name_label = gtk.Label(label="Name:", xalign=0)
        name_entry = gtk.Entry()

        path_label = gtk.Label(label="Path:", xalign=0)
        path_entry = gtk.Entry()
        folder_btn = gtk.Button()
        try:
            img = gtk.Image.new_from_icon_name("folder", gtk.IconSize.BUTTON)
            folder_btn.add(img)
        except Exception:
            folder_btn.set_label("…")

        path_box = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=6)
        path_box.pack_start(path_entry, True, True, 0)
        path_box.pack_start(folder_btn, False, False, 0)

        desc_label = gtk.Label(label="Description:", xalign=0)
        desc_view = gtk.TextView()
        desc_view.set_wrap_mode(gtk.WrapMode.WORD)
        desc_scrolled = gtk.ScrolledWindow()
        desc_scrolled.set_policy(gtk.PolicyType.AUTOMATIC, gtk.PolicyType.AUTOMATIC)
        desc_scrolled.set_min_content_height(100)
        desc_scrolled.add(desc_view)

        if initial:
            name_entry.set_text(initial.get("name", ""))
            path_entry.set_text(initial.get("path", ""))
            try:
                buf = desc_view.get_buffer()
                buf.set_text(initial.get("description", "") or "")
            except Exception:
                pass

        grid.attach(name_label, 0, 0, 1, 1)
        grid.attach(name_entry, 1, 0, 1, 1)
        grid.attach(path_label, 0, 1, 1, 1)
        grid.attach(path_box, 1, 1, 1, 1)
        grid.attach(desc_label, 0, 2, 1, 1)
        grid.attach(desc_scrolled, 1, 2, 1, 1)

        def on_folder_clicked(_btn):
            chooser = gtk.FileChooserDialog(title="Select Folder", parent=dialog, action=gtk.FileChooserAction.SELECT_FOLDER)
            chooser.add_buttons(gtk.STOCK_CANCEL, gtk.ResponseType.CANCEL, gtk.STOCK_OPEN, gtk.ResponseType.OK)
            start = os.getcwd()
            try:
                chooser.set_current_folder(start)
            except Exception:
                pass
            resp = chooser.run()
            if resp == gtk.ResponseType.OK:
                filename = chooser.get_filename()
                if filename:
                    path_entry.set_text(filename)
            chooser.destroy()

        folder_btn.connect("clicked", on_folder_clicked)

        content.add(grid)
        dialog.show_all()
        resp = dialog.run()
        result = None
        if resp == gtk.ResponseType.OK:
            name = name_entry.get_text().strip()
            path = path_entry.get_text().strip()
            try:
                buf = desc_view.get_buffer()
                start = buf.get_start_iter()
                end = buf.get_end_iter()
                desc = buf.get_text(start, end, True).strip()
            except Exception:
                desc = ""
            result = (name, path, desc)
        dialog.destroy()
        return result

    def _open_repo_dialog(self, title: str, initial: dict | None = None) -> tuple | None:
        """Dialog to add or edit a repository (name + description)."""
        dialog = gtk.Dialog(title=title, parent=self, flags=gtk.DialogFlags.MODAL)
        dialog.add_button("Cancel", gtk.ResponseType.CANCEL)
        dialog.add_button("OK", gtk.ResponseType.OK)
        content = dialog.get_content_area()

        grid = gtk.Grid(column_spacing=6, row_spacing=6, margin=12)
        name_label = gtk.Label(label="Name:", xalign=0)
        name_entry = gtk.Entry()

        desc_label = gtk.Label(label="Description:", xalign=0)
        desc_view = gtk.TextView()
        desc_view.set_wrap_mode(gtk.WrapMode.WORD)
        desc_scrolled = gtk.ScrolledWindow()
        desc_scrolled.set_policy(gtk.PolicyType.AUTOMATIC, gtk.PolicyType.AUTOMATIC)
        desc_scrolled.set_min_content_height(80)
        desc_scrolled.add(desc_view)

        if initial:
            name_entry.set_text(initial.get("name", ""))
            try:
                buf = desc_view.get_buffer()
                buf.set_text(initial.get("description", "") or "")
            except Exception:
                pass

        grid.attach(name_label, 0, 0, 1, 1)
        grid.attach(name_entry, 1, 0, 1, 1)
        grid.attach(desc_label, 0, 1, 1, 1)
        grid.attach(desc_scrolled, 1, 1, 1, 1)

        content.add(grid)
        dialog.show_all()
        resp = dialog.run()
        result = None
        if resp == gtk.ResponseType.OK:
            name = name_entry.get_text().strip()
            try:
                buf = desc_view.get_buffer()
                start = buf.get_start_iter()
                end = buf.get_end_iter()
                desc = buf.get_text(start, end, True).strip()
            except Exception:
                desc = ""
            result = (name, desc)
        dialog.destroy()
        return result

    def populate_stores(self) -> None:
        # clear existing store rows
        for child in self.stores_listbox.get_children():
            self.stores_listbox.remove(child)

        stores = core.list_stores()
        cfg = core.get_current_config()
        for store in stores:
            sg = StoreGui(store, self, self.populate_stores)
            self.stores_listbox.add(sg.row)

        # update selected label
        sel_name = None
        try:
            cur_id = getattr(cfg, "current_store_id", None)
            for s in stores:
                if getattr(s, "_id", None) == cur_id:
                    sel_name = s.name
                    break
        except Exception:
            sel_name = None

        try:
            if sel_name:
                esc = GLib.markup_escape_text(sel_name)
                self.selected_store_label.set_markup(f"<b>{esc}</b>")
            else:
                self.selected_store_label.set_markup('<b>No store selected</b>')
        except Exception:
            if sel_name:
                self.selected_store_label.set_text(sel_name)
            else:
                self.selected_store_label.set_text('No store selected')

        self.stores_listbox.show_all()
        try:
            self._update_repo_buttons_state()
        except Exception:
            pass

    def populate_repos(self) -> None:
        # clear existing repo rows
        for child in self.repos_listbox.get_children():
            self.repos_listbox.remove(child)

        repos = core.list_repos_in_current_store()
        if not repos:
            row = gtk.ListBoxRow()
            lbl = gtk.Label(label="No repos found in the current store", xalign=0)
            lbl.set_xalign(0)
            row.add(lbl)
            self.repos_listbox.add(row)
            self.repos_listbox.show_all()
            return

        for repo in repos:
            try:
                rg = RepoGui(repo, self, self.populate_repos)
                self.repos_listbox.add(rg.row)
            except Exception:
                prefix = "✅" if getattr(repo, 'is_active', True) else "❌"
                text = f"{prefix}- {repo.name}: {getattr(repo, 'path', '')} ({getattr(repo, '_id', '')})"
                row = gtk.ListBoxRow()
                lbl = gtk.Label(label=text, xalign=0)
                lbl.set_xalign(0)
                row.add(lbl)
                self.repos_listbox.add(row)

        self.repos_listbox.show_all()

    def on_add_store_clicked(self, _button):
        res = self.open_store_dialog("Add Store")
        if not res:
            return
        name, path, desc = res
        r = core.add_store(name, path, desc)
        if isinstance(r, str):
            md = gtk.MessageDialog(self, gtk.DialogFlags.MODAL, gtk.MessageType.ERROR, gtk.ButtonsType.OK, r)
            md.run()
            md.destroy()
        else:
            md = gtk.MessageDialog(self, gtk.DialogFlags.MODAL, gtk.MessageType.INFO, gtk.ButtonsType.OK, "Store added")
            md.run()
            md.destroy()
            self.populate_stores()

    def on_row_selected(self, _lb, row):
        if row is None:
            return
        store = getattr(row, "store", None)
        if store is None:
            return
        core.select_store_by_name(store.name)
        self.populate_stores()
        # refresh repos when the selected store changes
        try:
            self.populate_repos()
        except Exception:
            pass
        try:
            self._update_repo_buttons_state()
        except Exception:
            pass

    def on_add_repo_clicked(self, _button):
        # Present a dialog showing direct subfolders of the active store for selection
        try:
            cfg = core.get_current_config()
            store = core._get_store_by_id(getattr(cfg, "current_store_id", None))  # type: ignore
        except Exception:
            store = None

        if not store:
            md = gtk.MessageDialog(self, gtk.DialogFlags.MODAL, gtk.MessageType.ERROR, gtk.ButtonsType.OK, "No active store selected")
            md.run()
            md.destroy()
            return

        store_path = Path(store.path).expanduser()
        try:
            # exclude directories that already have a repo entry for this store
            try:
                existing_repos = core.Repos.filter(lambda k: k["store_id"] == store._id)
                existing_names = {getattr(r, "name", r.get("name") if isinstance(r, dict) else None) for r in existing_repos}
            except Exception:
                existing_names = set()
            subdirs = [p for p in store_path.iterdir() if p.is_dir() and p.name not in existing_names]
        except Exception:
            subdirs = []

        if not subdirs:
            md = gtk.MessageDialog(self, gtk.DialogFlags.MODAL, gtk.MessageType.INFO, gtk.ButtonsType.OK, "No subfolders found in the current store")
            md.run()
            md.destroy()
            return

        dialog = gtk.Dialog(title="Add Repo", parent=self, flags=gtk.DialogFlags.MODAL)
        dialog.add_button("Cancel", gtk.ResponseType.CANCEL)
        dialog.add_button("OK", gtk.ResponseType.OK)
        content = dialog.get_content_area()

        grid = gtk.Grid(column_spacing=6, row_spacing=6, margin=12)

        sel_label = gtk.Label(label="Select folder:", xalign=0)
        combo = gtk.ComboBoxText()
        # sort names for deterministic order
        for p in sorted(subdirs, key=lambda x: x.name.lower()):
            combo.append_text(p.name)
        combo.set_active(0)

        desc_label = gtk.Label(label="Description:", xalign=0)
        desc_view = gtk.TextView()
        desc_view.set_wrap_mode(gtk.WrapMode.WORD)
        desc_scrolled = gtk.ScrolledWindow()
        desc_scrolled.set_policy(gtk.PolicyType.AUTOMATIC, gtk.PolicyType.AUTOMATIC)
        desc_scrolled.set_min_content_height(80)
        desc_scrolled.add(desc_view)

        grid.attach(sel_label, 0, 0, 1, 1)
        grid.attach(combo, 1, 0, 1, 1)
        grid.attach(desc_label, 0, 1, 1, 1)
        grid.attach(desc_scrolled, 1, 1, 1, 1)

        content.add(grid)
        dialog.show_all()
        resp = dialog.run()
        if resp == gtk.ResponseType.OK:
            name = combo.get_active_text()
            try:
                buf = desc_view.get_buffer()
                start = buf.get_start_iter()
                end = buf.get_end_iter()
                desc = buf.get_text(start, end, True).strip()
            except Exception:
                desc = ""

            if not name:
                dialog.destroy()
                return

            repo_path = store_path / name
            if not repo_path.exists() or not repo_path.is_dir() or not (repo_path.joinpath('.git').exists() or repo_path.joinpath('objects').exists()):
                md = gtk.MessageDialog(self, gtk.DialogFlags.MODAL, gtk.MessageType.ERROR, gtk.ButtonsType.OK, "No git repository found in the selected folder")
                md.run()
                md.destroy()
                dialog.destroy()
                return

            try:
                if core.Repos.filter(lambda k: k["name"] == name and k["store_id"] == store._id):
                    md = gtk.MessageDialog(self, gtk.DialogFlags.MODAL, gtk.MessageType.ERROR, gtk.ButtonsType.OK, f"Repo '{name}' already exists in this store")
                    md.run()
                    md.destroy()
                    dialog.destroy()
                    return
            except Exception:
                pass

            r = core.add_repo_to_store(name, desc)
            if isinstance(r, str):
                low = r.lower()
                if low.startswith("error") or "already exists" in low or "no active store" in low:
                    md = gtk.MessageDialog(self, gtk.DialogFlags.MODAL, gtk.MessageType.ERROR, gtk.ButtonsType.OK, r)
                    md.run()
                    md.destroy()
                else:
                    md = gtk.MessageDialog(self, gtk.DialogFlags.MODAL, gtk.MessageType.INFO, gtk.ButtonsType.OK, r)
                    md.run()
                    md.destroy()
                    try:
                        self.populate_repos()
                    except Exception:
                        pass
            else:
                md = gtk.MessageDialog(self, gtk.DialogFlags.MODAL, gtk.MessageType.INFO, gtk.ButtonsType.OK, "Repo added")
                md.run()
                md.destroy()
                try:
                    self.populate_repos()
                except Exception:
                    pass

        dialog.destroy()

    def on_create_new_repo_clicked(self, _button):
        # Create repo and initialize on disk using core.add_and_create_repo
        res = self._open_repo_dialog("Create New Repo")
        if not res:
            return
        name, desc = res
        r = core.add_and_create_repo(name, desc)
        if isinstance(r, str):
            md = gtk.MessageDialog(self, gtk.DialogFlags.MODAL, gtk.MessageType.ERROR, gtk.ButtonsType.OK, r)
            md.run()
            md.destroy()
        else:
            md = gtk.MessageDialog(self, gtk.DialogFlags.MODAL, gtk.MessageType.INFO, gtk.ButtonsType.OK, "Repo created on disk")
            md.run()
            md.destroy()
            try:
                self.populate_repos()
            except Exception:
                pass
        try:
            self.populate_repos()
        except Exception:
            pass


if __name__ == "__main__":
    window = MainWindow()
    window.show_all()
    window.connect("delete-event", gtk.main_quit)
    gtk.main()
