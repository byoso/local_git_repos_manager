#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path
import gi
import subprocess

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GLib
from git_parser import list_branches, list_commits

import core
from models import Store, Repo


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
.button {
    margin-left: 10px;
    margin-top: 10px;
    padding: 4px 8px;
    border-radius: 4px;
}
.detail-pane {
    margin: 5px;
}
"""


def add_button_class(btn):
        """Add the 'button' CSS class to a Gtk.Button if possible."""
        try:
                if btn is None:
                        return
                sc = btn.get_style_context()
                sc.add_class("button")
        except Exception:
                pass


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
            tip_title_label = gtk.Label(label="Add remote to your project:", xalign=0)
            tip_label = gtk.Label(label=f"git remote add local {repo.path}", xalign=0)
            tip_label.set_selectable(True)
        except Exception:
            tip_title_label = None
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
        # add_button_class(edit_btn)
        detail_btn = gtk.Button(label="Detail")
        # add_button_class(detail_btn)
        del_btn = gtk.Button(label="X")
        # add_button_class(del_btn)
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
        btn_box.pack_start(detail_btn, False, False, 0)
        btn_box.pack_start(del_btn, False, False, 0)

        hbox.pack_start(left_v, True, True, 0)
        hbox.pack_start(btn_box, False, False, 0)

        outer.pack_start(hbox, False, False, 0)

        # Description line
        desc_text = getattr(repo, 'description', '') or ''
        desc_label = gtk.Label(label=desc_text, xalign=0)
        desc_label.set_xalign(0)
        outer.pack_start(tip_title_label, False, False, 0)
        outer.pack_start(tip_label, False, False, 0)
        outer.pack_start(desc_label, False, False, 0)

        self.row.repo = repo
        self.row.add(outer)

        edit_btn.connect("clicked", self.on_edit_clicked)
        del_btn.connect("clicked", self.on_delete_clicked)
        try:
            detail_btn.connect("clicked", self.on_detail_clicked)
        except Exception:
            pass

    def on_detail_clicked(self, _btn):
        """Show branches for this repo in the main window's right pane."""
        # remember this repo as the last one shown even if it's not a valid git repo
        try:
            self.parent._last_repo_in_detail = self.repo
        except Exception:
            pass
        try:
            self.parent.set_selected_repo(getattr(self.repo, "_id", None))
        except Exception:
            pass

        try:
            branches = list_branches(self.repo.path)
        except Exception as e:
            try:
                # show error in detail pane instead of modal
                self.parent.show_detail_message(f"Error listing branches: {e}")
            except Exception:
                pass
            return
        try:
            # delegate rendering to the main window
            self.parent.show_repo_branches(self.repo, branches)
            try:
                # update visual selection: highlight this repo and clear others
                self.parent.set_selected_repo(getattr(self.repo, "_id", None))
            except Exception:
                pass
        except Exception as e:
            try:
                self.parent.show_detail_message(f"Error showing branch details: {e}")
            except Exception:
                pass

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
                store: Store = core._get_store_by_id(getattr(repo, "store_id", None))  # type: ignore
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
        # Open-folder button (shows store folder in file manager)
        folder_btn = gtk.Button()
        # add_button_class(folder_btn)
        try:
            img = gtk.Image.new_from_icon_name("folder", gtk.IconSize.BUTTON)
            folder_btn.add(img)
        except Exception:
            folder_btn.set_label("Open")
        # disable if store is not active
        try:
            folder_btn.set_sensitive(bool(getattr(store, "is_active", True)))
        except Exception:
            pass

        edit_btn = gtk.Button(label="Edit")
        # add_button_class(edit_btn)
        del_btn = gtk.Button(label="X")
        # add_button_class(del_btn)
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
        btn_box.pack_start(folder_btn, False, False, 0)
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

        try:
            folder_btn.connect("clicked", self.on_open_store_folder_clicked)
        except Exception:
            pass
        edit_btn.connect("clicked", self.on_edit_clicked)
        del_btn.connect("clicked", self.on_delete_clicked)

    def on_open_store_folder_clicked(self, _btn):
        """Open the store folder in the system file manager using xdg-open."""
        try:
            p = Path(self.store.path).expanduser()
            if not p.exists() or not p.is_dir():
                md = gtk.MessageDialog(self.parent, gtk.DialogFlags.MODAL, gtk.MessageType.ERROR, gtk.ButtonsType.OK, f"Path '{p}' is not an existing directory")
                md.run()
                md.destroy()
                return
            # Best-effort: use xdg-open to open folder on Linux
            try:
                subprocess.Popen(["xdg-open", str(p)])
            except Exception as e:
                md = gtk.MessageDialog(self.parent, gtk.DialogFlags.MODAL, gtk.MessageType.ERROR, gtk.ButtonsType.OK, f"Error opening folder: {e}")
                md.run()
                md.destroy()
        except Exception:
            pass

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
        self.set_default_size(800, 600)
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

        # Use a Stack with a StackSwitcher for animated tab transitions
        stack = gtk.Stack()
        stack.set_transition_type(gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        stack.set_transition_duration(250)

        switcher = gtk.StackSwitcher()
        switcher.set_stack(stack)

        container = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=6)
        # center the StackSwitcher by placing flexible spacers on both sides
        switcher_box = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=0)
        left_spacer = gtk.Box()
        left_spacer.set_hexpand(True)
        right_spacer = gtk.Box()
        right_spacer.set_hexpand(True)
        switcher_box.pack_start(left_spacer, True, True, 0)
        switcher_box.pack_start(switcher, False, False, 0)
        switcher_box.pack_start(right_spacer, True, True, 0)
        container.pack_start(switcher_box, False, False, 0)
        container.pack_start(stack, True, True, 0)
        self.add(container)

        # Stores tab
        page1 = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=6)

        header = gtk.Box(orientation=gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_top(8)
        header.set_margin_bottom(8)

        add_btn = gtk.Button(label="+ Add Store")
        add_button_class(add_btn)
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

        stack.add_titled(page1, "stores", "Stores")
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
        add_button_class(self.add_repo_btn)
        add_button_class(self.create_new_btn)
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
        # repos should not be selectable: details are shown via the Detail button
        self.repos_listbox.set_selection_mode(gtk.SelectionMode.NONE)
        repo_scrolled.add(self.repos_listbox)
        # selection of a repo row is not used; details are shown via the 'Detail' button

        # Split the repositories page in two columns using a Paned so the right
        # pane already occupies space even when empty.
        repo_paned = gtk.Paned(orientation=gtk.Orientation.HORIZONTAL)

        # Left: the existing scrollable list of repos
        repo_paned.pack1(repo_scrolled, resize=True, shrink=False)

        # Right: placeholder VBox for future repository details/actions
        self.repos_detail_vbox = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=6)
        self.repos_detail_vbox.set_hexpand(True)
        self.repos_detail_vbox.set_vexpand(True)
        try:
            self.repos_detail_vbox.get_style_context().add_class("detail-pane")
        except Exception:
            pass
        repo_paned.pack2(self.repos_detail_vbox, resize=True, shrink=False)

        # set initial divider position to half of default window width (window default 900)
        try:
            repo_paned.set_position(450)
        except Exception:
            pass

        page2.pack_start(repo_paned, True, True, 0)

        stack.add_titled(page2, "repositories", "Repositories")
        self.repos_page = page2

        # refresh lists when the user switches tabs (Stack uses notify on visible-child)
        def _on_switch(stk, pspec):
            try:
                visible = stk.get_visible_child()
                if visible is self.stores_page:
                    self.populate_stores()
                elif visible is self.repos_page:
                    self.populate_repos()
            except Exception:
                pass

        try:
            stack.connect("notify::visible-child", _on_switch)
        except Exception:
            pass

        # Settings tab removed — not needed

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
            store: Store = core._get_store_by_id(getattr(cfg, "current_store_id", None))  # type: ignore
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
        add_button_class(folder_btn)
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
        # If a repo details pane is currently visible, reapply the
        # selected highlight to keep the previously shown repo green
        # when the user switches tabs and comes back.
        try:
            # details pane has children when details are shown
            children = self.repos_detail_vbox.get_children()
            if hasattr(self, '_last_repo_in_detail') and getattr(self, '_last_repo_in_detail', None) and children:
                try:
                    self.set_selected_repo(getattr(self._last_repo_in_detail, "_id", None))
                except Exception:
                    pass
        except Exception:
            pass

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

    def on_repo_row_selected(self, _lb, row):
        """When a repository row is selected, populate the right pane with branches."""
        if row is None:
            # clear details
            try:
                for child in self.repos_detail_vbox.get_children():
                    self.repos_detail_vbox.remove(child)
            except Exception:
                pass
            return
        repo = getattr(row, "repo", None)
        if repo is None:
            return
        branches = []
        try:
            branches = list_branches(repo.path)
        except Exception as e:
            # show diagnostic error in the detail pane instead of a modal dialog
            try:
                self.show_detail_message(f"Error listing branches: {e}")
            except Exception:
                pass
            return

        # if no branches found, provide diagnostic info to help locate the issue
        if not branches:
            try:
                p = Path(getattr(repo, 'path', ''))
                exists = p.exists()
                dotgit = (p / '.git').exists()
                objects = (p / 'objects').exists()
                info_txt = (
                    f"No branches found for repo '{getattr(repo,'name','')}'\n"
                    f"path: {p}\nexists: {exists}\n.git present: {dotgit}\nobjects present: {objects}"
                )
                # render diagnostic info in the detail pane
                try:
                    self.show_detail_message(info_txt)
                except Exception:
                    pass
                return
            except Exception:
                pass

        self.show_repo_branches(repo, branches)

    def show_repo_branches(self, repo, branches: list) -> None:
        """Render a selectable list of branches for `repo` into the right pane."""
        # clear previous
        for child in self.repos_detail_vbox.get_children():
            self.repos_detail_vbox.remove(child)

        # remember current repo for commits lookup
        self._last_repo_in_detail = repo
        try:
            # visually mark this repo as selected (green border) and clear others
            try:
                self.set_selected_repo(getattr(repo, "_id", None))
            except Exception:
                pass
        except Exception:
            pass

        title = gtk.Label()
        try:
            title.set_markup(f"<b>Branches for {GLib.markup_escape_text(repo.name)}</b>")
        except Exception:
            title.set_text(f"Branches for {getattr(repo, 'name', '')}")
        title.set_xalign(0)
        self.repos_detail_vbox.pack_start(title, False, False, 4)

        # Dropdown for branches
        if not branches:
            lbl = gtk.Label(label="No branches found", xalign=0)
            lbl.set_xalign(0)
            self.repos_detail_vbox.pack_start(lbl, False, False, 2)
            self.repos_detail_vbox.show_all()
            return

        combo = gtk.ComboBoxText()
        # keep the branch objects so we can access sha/ref by index
        self._last_branch_list = list(branches)
        for b in self._last_branch_list:
            name = b.get("name")
            current = b.get("current", False)
            label = f"{name}"
            combo.append_text(label)
        try:
            combo.set_active(0)
        except Exception:
            pass
        try:
            combo.connect("changed", self.on_branch_combo_changed)
        except Exception:
            pass

        self.repos_detail_vbox.pack_start(combo, False, False, 2)

        # selectable label to show the SHA of the selected branch
        sha_label = gtk.Label(label="", xalign=0)
        try:
            sha_label.set_selectable(True)
        except Exception:
            pass
        sha_label.set_xalign(0)
        self.repos_detail_sha_label = sha_label
        self.repos_detail_vbox.pack_start(sha_label, False, False, 2)

        # horizontal separator
        sep = gtk.Separator(orientation=gtk.Orientation.HORIZONTAL)
        self.repos_detail_vbox.pack_start(sep, False, True, 6)

        # commits area (will be populated by update_commits_area)
        self.repos_detail_commits_scrolled = gtk.ScrolledWindow()
        self.repos_detail_commits_scrolled.set_policy(gtk.PolicyType.AUTOMATIC, gtk.PolicyType.AUTOMATIC)
        self.repos_detail_commits_scrolled.set_hexpand(True)
        self.repos_detail_commits_scrolled.set_vexpand(True)
        # placeholder box inside scrolled window
        self._commits_box = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=4)
        self.repos_detail_commits_scrolled.add(self._commits_box)
        self.repos_detail_vbox.pack_start(self.repos_detail_commits_scrolled, True, True, 2)

        # initialize sha label and commits with first branch
        try:
            active = combo.get_active()
            if active is not None and active >= 0:
                b0 = self._last_branch_list[active]
                self.repos_detail_sha_label.set_text(b0.get("sha", ""))
                # show commits for the initial branch
                try:
                    self.update_commits_area(repo, b0.get("ref"))
                except Exception:
                    pass
        except Exception:
            pass
        self.repos_detail_vbox.show_all()

    def show_detail_message(self, text: str) -> None:
        """Render a simple informational message into the right detail pane.

        This replaces any existing details content.
        """
        try:
            for child in self.repos_detail_vbox.get_children():
                self.repos_detail_vbox.remove(child)
        except Exception:
            pass
        try:
            lbl = gtk.Label()
            # use simple markup-safe text
            esc = GLib.markup_escape_text(text)
            lbl.set_markup(f"<span>{esc}</span>")
            lbl.set_xalign(0)
            lbl.set_line_wrap(True)
            self.repos_detail_vbox.pack_start(lbl, False, False, 4)
            self.repos_detail_vbox.show_all()
        except Exception:
            pass

    def on_branch_selected(self, lb, row):
        """Handle branch selection in the right pane. For now, just show basic info below."""
        # remove any existing info box below the list
        try:
            # keep title and scrolled list (first two children), remove others
            children = self.repos_detail_vbox.get_children()
            # if there are more than 2 children, remove from index 2 onwards
            for child in children[2:]:
                self.repos_detail_vbox.remove(child)
        except Exception:
            pass

        if row is None:
            return
        ref = getattr(row, "branch_ref", None)
        name = getattr(row, "branch_name", "")
        info = gtk.Label(label=f"Selected branch: {name}\nRef: {ref}", xalign=0)
        info.set_xalign(0)
        info.set_line_wrap(True)
        self.repos_detail_vbox.pack_start(info, False, False, 4)
        self.repos_detail_vbox.show_all()

    def set_selected_repo(self, repo_id: str | None) -> None:
        """Visually mark the repo with `repo_id` as selected (green border) and clear others.

        This toggles the 'selected' CSS class on the repo rows' outer container.
        """
        try:
            for row in self.repos_listbox.get_children():
                try:
                    r = getattr(row, "repo", None)
                    child = row.get_child()
                    if child is None:
                        continue
                    sc = child.get_style_context()
                    if r is not None and getattr(r, "_id", None) == repo_id:
                        # add selected class
                        sc.add_class("selected")
                    else:
                        # remove selected class if present
                        try:
                            sc.remove_class("selected")
                        except Exception:
                            pass
                except Exception:
                    continue
        except Exception:
            pass

    def on_branch_combo_changed(self, combo):
        """Update SHA label when branch dropdown selection changes."""
        try:
            idx = combo.get_active()
            if idx is None or idx < 0:
                return
            b = self._last_branch_list[idx]
            sha = b.get("sha", "")
            try:
                self.repos_detail_sha_label.set_text(sha)
            except Exception:
                pass
            # update commits area for the selected branch
            try:
                self.update_commits_area(self._last_repo_in_detail, b.get("ref"))
            except Exception:
                try:
                    # fallback: if update_commits_area needs repo, try to read repo from title
                    pass
                except Exception:
                    pass
        except Exception:
            pass

    def update_commits_area(self, repo, branch_ref: str | None) -> None:
        """Populate the commits scrolled area for given branch_ref.

        `repo` may be None if not needed by list_commits (we derive path from stored _last_repo_path).
        """
        try:
            # clear previous commits
            for child in self._commits_box.get_children():
                self._commits_box.remove(child)
        except Exception:
            pass

        if branch_ref is None:
            return

        # determine repo path: try passed repo, else try the last branch list's repo path stored earlier
        repo_path = None
        try:
            if repo is not None:
                repo_path = repo.path
            else:
                # attempt to use the first repo in list if available (best-effort)
                if hasattr(self, '_last_branch_list') and self._last_branch_list:
                    # no repo path available here; caller should pass repo
                    repo_path = None
        except Exception:
            repo_path = None

        if repo_path is None:
            # cannot fetch commits without a repo path
            lbl = gtk.Label(label="Commits unavailable: missing repo path", xalign=0)
            lbl.set_xalign(0)
            self._commits_box.pack_start(lbl, False, False, 2)
            self.repos_detail_vbox.show_all()
            return

        commits = []
        try:
            commits = list_commits(repo_path, branch_ref, max_count=200)
        except Exception:
            commits = []

        if not commits:
            lbl = gtk.Label(label="No commits found", xalign=0)
            lbl.set_xalign(0)
            self._commits_box.pack_start(lbl, False, False, 2)
            self.repos_detail_vbox.show_all()
            return
        label_commit_title = gtk.Label(label="Recent commits:", xalign=0)
        self._commits_box.pack_start(label_commit_title, False, False, 2)
        for c in commits:
            sha = c.get('sha', '')
            author = c.get('author', '')
            date = c.get('date', '')
            subject = c.get('subject', '')
            lbl = gtk.Label(label=f"{sha}\n{author} {date}\n{subject}\n", xalign=0)
            try:
                lbl.set_selectable(True)
            except Exception:
                pass
            lbl.set_xalign(0)
            self._commits_box.pack_start(lbl, False, False, 2)

        self.repos_detail_vbox.show_all()

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
