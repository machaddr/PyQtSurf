#!/usr/bin/env python3

import sys, os, json
from PyQt6.QtCore import QUrl, Qt , QDateTime
from PyQt6.QtWidgets import QApplication, QMainWindow, QLineEdit, QTabWidget, QToolBar, QMessageBox, QMenu, QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QHBoxLayout
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtNetwork import QNetworkCookie

class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQtSurf")
        self.showMaximized()

        # Paths for the data files
        self.data_dir = os.path.expanduser("~/.pyqtsurf") if os.name != 'nt' else os.path.join(os.getenv("USERPROFILE"), ".pyqtsurf")
        os.makedirs(self.data_dir, exist_ok=True)
        self.bookmarks_file = os.path.join(self.data_dir, "bookmarks.json")
        self.history_file = os.path.join(self.data_dir, "history.json")
        self.cookies_file = os.path.join(self.data_dir, "cookies.json")

        self.bookmarks = self.load_json(self.bookmarks_file)
        self.history = self.load_json(self.history_file)
        self.cookies = self.load_json(self.cookies_file)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBarDoubleClicked.connect(self.tab_open_doubleclick)
        self.tabs.currentChanged.connect(self.current_tab_changed)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)
        self.setCentralWidget(self.tabs)

        self.status = QToolBar()
        self.addToolBar(self.status)

        self.url_bar = QLineEdit()

        self.add_new_tab(QUrl("https://html.duckduckgo.com/html"), "Homepage")
        self.create_menu_bar()
        self.create_shortcuts()

        # Populate history and bookmarks menus
        self.update_history_menu()
        self.update_bookmarks_menu()
        self.update_cookies_menu()  # Update cookies menu
        
        self.load_cookies_to_web_engine()  # Load cookies into the web engine

    def load_json(self, file_path):
        """Load data from a JSON file, or return an empty list if the file doesn't exist."""
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return []

    def save_json(self, file_path, data):
        """Save data to a JSON file."""
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)

    def add_new_tab(self, qurl=None, label="Homepage"):
        if qurl is None:
            qurl = QUrl("https://html.duckduckgo.com/html")

        browser = QWebEngineView()
        browser.setUrl(qurl)

        i = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(i)

        browser.urlChanged.connect(lambda qurl, browser=browser: self.update_urlbar(qurl, browser))
        browser.loadFinished.connect(lambda _, i=i, browser=browser: self.update_title(browser))
        browser.loadFinished.connect(lambda _, i=i, browser=browser: self.tabs.setTabText(i, browser.page().title()))
        browser.loadFinished.connect(lambda: self.add_to_history(qurl, browser.page().title()))  # Add to history
        browser.page().profile().cookieStore().cookieAdded.connect(self.add_cookie)  # Add cookie

    def tab_open_doubleclick(self, i):
        if i == -1:
            self.add_new_tab()

    def current_tab_changed(self, i):
        qurl = self.tabs.currentWidget().url()
        self.update_urlbar(qurl, self.tabs.currentWidget())
        self.update_title(self.tabs.currentWidget())

    def close_current_tab(self, i):
        if self.tabs.count() < 2:
            return

        self.tabs.removeTab(i)

    def update_title(self, browser):
        if browser != self.tabs.currentWidget():
            return

        current_widget = self.tabs.currentWidget()
        if current_widget is not None and current_widget.page() is not None:
            title = current_widget.page().title()
            self.setWindowTitle(f"{title} - PyQtSurf")

    def navigate_home(self):
        self.tabs.currentWidget().setUrl(QUrl("https://html.duckduckgo.com/html"))

    def update_urlbar(self, q, browser=None):
        if browser != self.tabs.currentWidget():
            return

        # Set full URL including the scheme
        self.url_bar.setText(q.toString(QUrl.ComponentFormattingOption.FullyEncoded))
        self.url_bar.setCursorPosition(0)

    def navigate_to_url(self):
        url = self.url_bar.text()
        if not url.startswith("http://") and not url.startswith("https://"):
            if "." in url and " " not in url:
                url = f"https://{url}"
            else:
                url = f"https://html.duckduckgo.com/html?q={url}"
        self.tabs.currentWidget().setUrl(QUrl(url))

    def create_menu_bar(self):
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")
        new_tab_action = QAction("New Tab", self)
        new_tab_action.triggered.connect(lambda _: self.add_new_tab())
        file_menu.addAction(new_tab_action)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menu_bar.addMenu("Edit")
        select_all_action = QAction("Select All", self)
        select_all_action.triggered.connect(self.select_all_text)
        edit_menu.addAction(select_all_action)
        cut_action = QAction("Cut", self)
        cut_action.triggered.connect(self.cut_text)
        edit_menu.addAction(cut_action)
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self.copy_text)
        edit_menu.addAction(copy_action)
        paste_action = QAction("Paste", self)
        paste_action.triggered.connect(self.paste_text)
        edit_menu.addAction(paste_action)

        # History menu (before Bookmarks)
        self.history_menu = menu_bar.addMenu("History")
        self.update_history_menu()

        # Bookmarks menu
        self.bookmarks_menu = menu_bar.addMenu("Bookmarks")
        self.update_bookmarks_menu()

        # Cookies menu
        self.cookies_menu = menu_bar.addMenu("Cookies")
        self.update_cookies_menu()

        # Settings menu
        settings_menu = menu_bar.addMenu("Settings")
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings_dialog)
        settings_menu.addAction(settings_action)

        # Help menu
        help_menu = menu_bar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        # Navigation bar
        navtb = QToolBar("Navigation")
        self.addToolBar(navtb)

        self.back_button = QAction("←", self)
        self.back_button.triggered.connect(lambda: self.tabs.currentWidget().back())
        navtb.addAction(self.back_button)

        self.forward_button = QAction("→", self)
        self.forward_button.triggered.connect(lambda: self.tabs.currentWidget().forward())
        navtb.addAction(self.forward_button)

        self.reload_button = QAction("⟳", self)
        self.reload_button.triggered.connect(lambda: self.tabs.currentWidget().reload())
        navtb.addAction(self.reload_button)

        self.home_button = QAction("Home", self)
        self.home_button.triggered.connect(self.navigate_home)
        navtb.addAction(self.home_button)

        self.url_bar.returnPressed.connect(self.navigate_to_url)
        navtb.addWidget(self.url_bar)

        self.bookmark_button = QAction("☆", self)
        self.bookmark_button.triggered.connect(self.toggle_bookmark)
        navtb.addAction(self.bookmark_button)
        
        self.settings_button = QAction("⚙", self)
        self.settings_button.triggered.connect(self.show_settings_dialog)
        navtb.addAction(self.settings_button)

    def create_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+T"), self).activated.connect(lambda: self.add_new_tab())
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(lambda: self.close_current_tab(self.tabs.currentIndex()))
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(lambda: self.tabs.currentWidget().reload())
        QShortcut(QKeySequence("Alt+Home"), self).activated.connect(self.navigate_home)
        QShortcut(QKeySequence("Alt+Left"), self).activated.connect(lambda: self.tabs.currentWidget().back())
        QShortcut(QKeySequence("Alt+Right"), self).activated.connect(lambda: self.tabs.currentWidget().forward())
        QShortcut(QKeySequence("Ctrl+B"), self).activated.connect(self.toggle_bookmark)

    def toggle_bookmark(self):
        url = self.url_bar.text()
        if url in [bookmark[1] for bookmark in self.bookmarks]:
            self.bookmarks = [bookmark for bookmark in self.bookmarks if bookmark[1] != url]
            for action in self.bookmarks_menu.actions():
                if action.data() == url:
                    self.bookmarks_menu.removeAction(action)
            self.bookmark_button.setIconText("☆")  # Set to unpressed state
        else:
            current_widget = self.tabs.currentWidget()
            if current_widget is not None and current_widget.page() is not None:
                title = current_widget.page().title()
                self.bookmarks.append([title, url])
                bookmark_action = QAction(title, self)
                bookmark_action.setData(url)
                bookmark_action.triggered.connect(lambda _, url=url: self.tabs.currentWidget().setUrl(QUrl(url)))
                self.bookmarks_menu.addAction(bookmark_action)
            self.bookmark_button.setIconText("★")  # Change to pressed state
        self.save_json(self.bookmarks_file, self.bookmarks)  # Save bookmarks

        # Reset the bookmark button state when the URL changes
        self.url_bar.textChanged.connect(self.reset_bookmark_button)

    def reset_bookmark_button(self):
        url = self.url_bar.text()
        if url not in [bookmark[1] for bookmark in self.bookmarks]:
            self.bookmark_button.setIconText("☆")  # Set to unpressed state

    def select_all_text(self):
        widget = self.focusWidget()
        if isinstance(widget, QLineEdit):
            widget.selectAll()
        elif isinstance(self.tabs.currentWidget(), QWebEngineView):
            self.tabs.currentWidget().page().runJavaScript("document.execCommand('selectAll');")

    def cut_text(self):
        widget = self.focusWidget()
        if isinstance(widget, QLineEdit):
            widget.cut()
        elif isinstance(self.tabs.currentWidget(), QWebEngineView):
            self.tabs.currentWidget().page().runJavaScript("document.execCommand('cut');")

    def copy_text(self):
        widget = self.focusWidget()
        if isinstance(widget, QLineEdit):
            widget.copy()
        elif isinstance(self.tabs.currentWidget(), QWebEngineView):
            self.tabs.currentWidget().page().runJavaScript("document.execCommand('copy');")

    def paste_text(self):
        widget = self.focusWidget()
        if isinstance(widget, QLineEdit):
            widget.paste()
        elif isinstance(self.tabs.currentWidget(), QWebEngineView):
            self.tabs.currentWidget().page().runJavaScript("document.execCommand('paste');")
            
    def add_to_history(self, qurl, title):
        """ Add a page to the history """
        url = self.url_bar.text()
        if url != "about:blank":
            self.history.append((title, url))
            self.update_history_menu()
            self.save_json(self.history_file, self.history)  # Save history

    def update_history_menu(self):
        """ Update the History menu with the latest entries """
        self.history_menu.clear()
        for title, url in reversed(self.history[-50:]):  # Limit to the last 50 entries
            history_action = QAction(title, self)
            history_action.triggered.connect(lambda _, url=url: self.tabs.currentWidget().setUrl(QUrl(url)))
            self.history_menu.addAction(history_action)

    def update_bookmarks_menu(self):
        """ Update the Bookmarks menu with the loaded bookmarks """
        self.bookmarks_menu.clear()
        for title, url in self.bookmarks:
            bookmark_action = QAction(title, self)
            bookmark_action.triggered.connect(lambda _, url=url: self.tabs.currentWidget().setUrl(QUrl(url)))
            self.bookmarks_menu.addAction(bookmark_action)

    def update_cookies_menu(self):
        """ Update the Cookies menu with the loaded cookies """
        self.cookies_menu.clear()
        for cookie in self.cookies:
            cookie_action = QAction(f"{cookie['name']} - {cookie['domain']}", self)
            self.cookies_menu.addAction(cookie_action)

    def add_cookie(self, cookie):
        """ Add a cookie to the list and save it """
        self.cookies.append({
            'name': cookie.name().data().decode('utf-8'),
            'value': cookie.value().data().decode('utf-8'),
            'domain': cookie.domain(),
            'path': cookie.path(),
            'expiry': cookie.expirationDate().toString(Qt.DateFormat.ISODate)
        })
        self.save_json(self.cookies_file, self.cookies)
        self.update_cookies_menu()
        
    def load_cookies_to_web_engine(self):
        """ Load cookies into the web engine """
        profile = self.tabs.currentWidget().page().profile()
        cookie_store = profile.cookieStore()
        for cookie in self.cookies:
            qcookie = QNetworkCookie(
                cookie['name'].encode('utf-8'),
                cookie['value'].encode('utf-8')
            )
            qcookie.setDomain(cookie['domain'])
            qcookie.setPath(cookie['path'])
            qcookie.setExpirationDate(QDateTime.fromString(cookie['expiry'], Qt.DateFormat.ISODate))
            cookie_store.setCookie(qcookie)

    def show_settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")

        layout = QVBoxLayout()

        # Bookmarks section
        bookmarks_label = QLabel("Bookmarks:")
        layout.addWidget(bookmarks_label)

        bookmarks_list = QListWidget()
        for title, url in self.bookmarks:
            bookmarks_list.addItem(f"{title} - {url}")
        layout.addWidget(bookmarks_list)

        # Add bookmark section
        add_layout = QHBoxLayout()
        add_title_edit = QLineEdit()
        add_title_edit.setPlaceholderText("Title")
        add_url_edit = QLineEdit()
        add_url_edit.setPlaceholderText("URL")
        add_button = QPushButton("Add")
        add_button.clicked.connect(lambda: self.add_bookmark(add_title_edit.text(), add_url_edit.text(), bookmarks_list))
        add_layout.addWidget(add_title_edit)
        add_layout.addWidget(add_url_edit)
        add_layout.addWidget(add_button)
        layout.addLayout(add_layout)

        # Remove bookmark button
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(lambda: self.remove_selected_bookmark(bookmarks_list))
        layout.addWidget(remove_button)

        # History section
        history_label = QLabel("History:")
        layout.addWidget(history_label)

        history_list = QListWidget()
        for title, url in self.history:
            item = QListWidgetItem(f"{title} - {url}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            history_list.addItem(item)
        layout.addWidget(history_list)

        # Clear all history button
        clear_history_button = QPushButton("Clear All History")
        clear_history_button.clicked.connect(self.clear_all_history)
        layout.addWidget(clear_history_button)

        # Connect to update history when checkbox state changes
        history_list.itemChanged.connect(lambda item: self.update_history_on_uncheck(item, history_list))

        # Cookies section
        cookies_label = QLabel("Cookies:")
        layout.addWidget(cookies_label)

        cookies_list = QListWidget()
        for cookie in self.cookies:
            cookies_list.addItem(f"{cookie['name']} - {cookie['value']}")
        layout.addWidget(cookies_list)

        # Remove all cookies button
        remove_all_cookies_button = QPushButton("Remove All Cookies")
        remove_all_cookies_button.clicked.connect(self.remove_all_cookies)
        layout.addWidget(remove_all_cookies_button)

        dialog.setLayout(layout)
        dialog.exec()

    def add_bookmark(self, title, url, bookmarks_list):
        if title and url:
            self.bookmarks.append([title, url])
            self.save_json(self.bookmarks_file, self.bookmarks)
            bookmarks_list.addItem(f"{title} - {url}")
            self.update_bookmarks_menu()

    def remove_selected_bookmark(self, bookmarks_list):
        selected_items = bookmarks_list.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            item_text = item.text()
            title, url = item_text.split(" - ", 1)
            self.bookmarks = [bookmark for bookmark in self.bookmarks if bookmark[1] != url]
            bookmarks_list.takeItem(bookmarks_list.row(item))
        self.save_json(self.bookmarks_file, self.bookmarks)
        self.update_bookmarks_menu()

    def update_history_on_uncheck(self, item, history_list):
        if item.checkState() == Qt.CheckState.Unchecked:
            item_text = item.text()
            title, url = item_text.split(" - ", 1)
            self.history = [entry for entry in self.history if entry[1] != url]
            history_list.takeItem(history_list.row(item))
            self.save_json(self.history_file, self.history)
            self.update_history_menu()

    def clear_all_history(self):
        self.history = []
        self.save_json(self.history_file, self.history)
        self.update_history_menu()
        
    def remove_all_cookies(self):
        self.cookies = []
        self.save_json(self.cookies_file, self.cookies)
        profile = self.tabs.currentWidget().page().profile()
        cookie_store = profile.cookieStore()
        cookie_store.deleteAllCookies()
        for cookie in self.cookies:
            qcookie = QNetworkCookie(
            cookie['name'].encode('utf-8'),
            cookie['value'].encode('utf-8')
            )
            qcookie.setDomain(cookie['domain'])
            qcookie.setPath(cookie['path'])
            qcookie.setExpirationDate(QDateTime.fromString(cookie['expiry'], Qt.DateFormat.ISODate))
            cookie_store.setCookie(qcookie)
        self.update_cookies_menu()
        
    def show_about_dialog(self):
        license_text = """
        PyQtSurf - A simple web browser built with PyQt6.

        Author: André Machado, 2024
        License: GPL 3.0

        This program is free software; you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation; either version 3 of the License, or
        (at your option) any later version.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.

        You should have received a copy of the GNU General Public License
        along with this program; if not, write to the Free Software
        Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
        """
        QMessageBox.about(self, "About PyQtSurf", license_text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Browser()
    window.show()
    sys.exit(app.exec())
    