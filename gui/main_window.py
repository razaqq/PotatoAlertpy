"""
Copyright (c) 2019 razaqq

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from assets.qtmodern import windows
from PyQt5.QtWidgets import (QLabel, QWidget, QTableWidgetItem, QMainWindow,  QMessageBox, QSizePolicy, QHBoxLayout,
                             QVBoxLayout, QTextEdit, QPushButton, QSizeGrip, QDockWidget)
from PyQt5.QtGui import QIcon, QFont, QPixmap, QDesktopServices, QMovie, QTextCursor, QColor
from PyQt5.QtCore import Qt, QUrl, QSize
from gui.stats_table import StatsTable
from gui.label import Label
from gui.team_stats import TeamStats
from gui.menubar import VerticalMenuBar
from gui.settings import SettingsMenu
from gui.about import AboutMenu
from gui.help import HelpMenu
from utils.resource_path import resource_path


# noinspection PyArgumentList
class MainWindow(QMainWindow):
    def __init__(self, config, pa):
        self.pa = pa
        self.config = config
        self.flags = Qt.WindowFlags()
        super().__init__(flags=self.flags)

        self.v_widget = QWidget(self)
        self.v_layout = QVBoxLayout()
        self.h_widget = QWidget(self)
        self.layout = QHBoxLayout()

        self.stats_widget = QWidget(self)
        self.stats_layout = QVBoxLayout()

        self.settings_widget = SettingsMenu(self)
        self.about_widget = AboutMenu(self)
        self.help_widget = HelpMenu(self)

        self.menu_bar = VerticalMenuBar(self)

        self.setup_ui()

        self.status_icon, self.status_text = None, None
        self.update_status(1, 'Ready')

        self.create_table_labels()

        self.left_table, self.right_table = self.create_tables()
        self.team_stats = TeamStats(self.stats_layout, pa)
        self.mw = None
        self.connect_signals()

    def setup_ui(self):
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.stats_layout.setContentsMargins(0, 0, 0, 0)
        self.stats_layout.setSpacing(0)

        self.setMouseTracking(False)
        self.setTabletTracking(False)
        self.setWindowTitle('PotatoAlert')

        icon = QIcon()
        icon.addPixmap(QPixmap(resource_path('./assets/potato.png')), QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)

        size_grip_widget = QWidget(self)
        size_grip_layout = QHBoxLayout()
        size_grip_layout.setContentsMargins(0, 0, 0, 0)
        size_grip_layout.setSpacing(0)
        size_grip_widget.setLayout(size_grip_layout)
        size_grip_layout.addWidget(QSizeGrip(self), alignment=Qt.AlignBottom | Qt.AlignRight)

        self.stats_widget.setLayout(self.stats_layout)
        self.settings_widget.setVisible(False)
        self.about_widget.setVisible(False)
        self.help_widget.setVisible(False)

        self.setCentralWidget(self.v_widget)
        self.v_widget.setLayout(self.v_layout)
        self.v_layout.addWidget(self.h_widget)
        self.v_layout.addWidget(size_grip_widget)
        self.h_widget.setLayout(self.layout)

        dock = QDockWidget()
        dock.setTitleBarWidget(QWidget())
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        dock.setWidget(self.menu_bar)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

        self.layout.addWidget(self.stats_widget)
        self.layout.addWidget(self.settings_widget)
        self.layout.addWidget(self.help_widget)
        self.layout.addWidget(self.about_widget)

    def set_size(self):
        self.mw.move(self.config.getint('DEFAULT', 'windowx'), self.config.getint('DEFAULT', 'windowy'))
        self.mw.resize(self.config.getint('DEFAULT', 'windoww'), self.config.getint('DEFAULT', 'windowh'))

    def create_tables(self):
        table_widget = QWidget(flags=self.flags)
        table_layout = QHBoxLayout()
        table_layout.setContentsMargins(10, 0, 10, 0)
        table_layout.setSpacing(10)
        t1 = StatsTable()
        t2 = StatsTable()
        table_layout.addWidget(t1, alignment=Qt.Alignment(0))
        table_layout.addWidget(t2, alignment=Qt.Alignment(0))
        table_widget.setLayout(table_layout)
        self.stats_layout.addWidget(table_widget, alignment=Qt.Alignment(0))
        t1.doubleClicked.connect(t1.print_click)
        t2.doubleClicked.connect(t2.print_click)
        return t1, t2

    def create_table_labels(self):
        label_widget = QWidget(flags=self.flags)
        label_layout = QHBoxLayout()
        label_layout.setContentsMargins(10, 0, 10, 0)
        label_layout.setSpacing(10)
        label_widget.setLayout(label_layout)

        left_layout = QHBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        left_widget = QWidget(flags=self.flags)
        left_widget.setLayout(left_layout)

        status = QWidget(flags=self.flags)
        status.setFixedWidth(130)
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(0)
        status.setLayout(status_layout)
        status_layout.addWidget(self.status_icon, alignment=Qt.Alignment(0))
        status_layout.addSpacing(5)
        status_layout.addWidget(self.status_text, alignment=Qt.Alignment(0))
        status_layout.addStretch()

        left_layout.addWidget(status, alignment=Qt.Alignment(0))
        left_layout.addStretch()
        left_layout.addWidget(Label(text='My Team'), alignment=Qt.Alignment(0))
        left_layout.addStretch()
        dummy = QWidget(flags=self.flags)
        dummy.setFixedWidth(130)
        left_layout.addWidget(dummy, alignment=Qt.Alignment(0))

        right_layout = QHBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_widget = QWidget(flags=self.flags)
        right_widget.setLayout(right_layout)
        right_layout.addStretch()
        right_layout.addWidget(Label(text='Enemy Team'), alignment=Qt.Alignment(0))
        right_layout.addStretch()

        label_layout.addWidget(left_widget, alignment=Qt.Alignment(0))
        label_layout.addWidget(right_widget, alignment=Qt.Alignment(0))
        self.stats_layout.addWidget(label_widget, alignment=Qt.Alignment(0))

    def update_status(self, status=1, text=''):
        if not self.status_icon or not self.status_text:
            self.status_icon = QLabel()
            self.status_icon.setScaledContents(True)
            self.status_icon.setFixedHeight(20)
            self.status_icon.setFixedWidth(20)
            self.status_text = QLabel('')
            self.status_text.setAlignment(Qt.AlignCenter)
            self.status_text.setStyleSheet('font-size: 10px;')
        if status == 1:  # waiting for start/ready
            pix = QPixmap(resource_path('assets/done.png'))
            self.status_icon.setPixmap(pix)
            self.status_text.setText(text)
        elif status == 2:  # loading
            if not self.status_icon.movie():
                movie = QMovie(resource_path('assets/loading.gif'))
                movie.setSpeed(1000)
                movie.setScaledSize(QSize(20, 20))
                movie.start()
                self.status_icon.setMovie(movie)
            self.status_text.setText(text)
        elif status == 3:  # error
            pix = QPixmap(resource_path('assets/error.png'))
            self.status_icon.setPixmap(pix)
            self.status_text.setText(text)

    def fill_tables(self):
        self.left_table.clearContents()
        self.right_table.clearContents()
        self.left_table.players = self.pa.team1
        self.right_table.players = self.pa.team2

        for team in [self.pa.team1, self.pa.team2]:
            table = self.left_table if team == self.pa.team1 else self.right_table
            for y, player in enumerate(team):
                for x in range(len(player.row)):
                    size = 13 if x < 2 else 16
                    if x == 0 and player.clan_tag:
                        cc = player.clan_color
                        text = f'<span style="color: rgba({cc[0]}, {cc[1]}, {cc[2]});"> [{player.clan_tag}]</span>{player.row[x]}'
                        item = Label(text=text, size=10, bold=False)
                        item.setTextFormat(Qt.RichText)
                        item.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                        item.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
                        item.setContentsMargins(3, 0, 3, 0)

                        if player.background:
                            b = player.background
                            rgba = f"rgba({b[0]}, {b[1]}, {b[2]}, {b[3]})"
                            item.setAutoFillBackground(True)
                            item.setStyleSheet(
                                f'background-color: {rgba};'
                                f'font-size: {size}px;'
                                f'font-family: Segoe UI;'
                            )
                        else:
                            item.setStyleSheet(f'font-size: {size}px; font-family: Segoe UI;')
                        table.setCellWidget(y, x, item)
                        continue

                    font = QFont('Segoe UI', size, QFont.Bold) if x else QFont('Segoe UI', size)
                    font.setPixelSize(size)
                    item = QTableWidgetItem(str(player.row[x]))
                    item.setFont(font)
                    item.setTextAlignment(Qt.AlignVCenter)
                    if player.background:
                        item.setBackground(QColor.fromRgb(*player.background))
                    if player.colors[x]:
                        item.setForeground(QColor.fromRgb(*player.colors[x]))
                    if x > 1:
                        item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
                    table.setItem(y, x, item)

                if player.background:  # Set background for empty columns
                    for x in range(len(player.row), self.left_table.columnCount()):
                        item = QTableWidgetItem('')
                        item.setBackground(QColor.fromRgb(*player.background))
                        table.setItem(y, x, item)

    def closeEvent(self, event):
        # Save current window position and size
        self.config['DEFAULT']['windowx'] = str(self.mw.geometry().x()+7)
        self.config['DEFAULT']['windowy'] = str(self.mw.geometry().y())
        self.config['DEFAULT']['windowh'] = str(self.mw.geometry().height())
        self.config['DEFAULT']['windoww'] = str(self.mw.geometry().width())
        self.config.save()
        super().closeEvent(event)

    def notify_update(self):
        d = windows.ModernDialog(self)
        d.setFixedHeight(70)
        d.setFixedWidth(265)
        d.setWindowTitle('')

        box = QMessageBox(d)
        box.setIcon(QMessageBox.Question)
        box.setText('There is a new version available.\nWould you like to update now?')
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setEscapeButton(QMessageBox.No)
        box.button(QMessageBox.Yes).setDefault(False)
        box.button(QMessageBox.Yes).setAutoDefault(False)
        box.button(QMessageBox.No).setDefault(False)
        box.button(QMessageBox.No).setAutoDefault(False)
        box.setAttribute(Qt.WA_TranslucentBackground)

        layout = QHBoxLayout()
        layout.addWidget(box, alignment=Qt.Alignment(0))
        d.setLayout(layout)
        d.show()

        if box.exec_() == QMessageBox.Yes:
            d.hide()
            return True
        else:
            d.hide()
            return False

    def show_changelog(self, version: str, text: str):
        d = windows.ModernDialog(self)
        d.setMinimumWidth(450)
        d.setFixedHeight(130)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        row_layout = QHBoxLayout()
        row_layout.setSpacing(10)
        row_layout.setContentsMargins(0, 0, 0, 0)

        pix = QPixmap(resource_path('./assets/potato.png'))
        pix = pix.scaled(60, 60)
        img = QLabel()
        img.setPixmap(pix)
        row_layout.addWidget(img, alignment=Qt.Alignment(0))

        changelog_widget = QWidget(flags=self.flags)
        changelog_layout = QVBoxLayout()
        changelog_layout.setSpacing(10)
        changelog_layout.setContentsMargins(0, 0, 0, 0)

        font = QFont()
        font.setPointSize(12)
        text1 = QLabel(f'New in version {version}')
        text1.setFont(font)
        changelog_layout.addWidget(text1, alignment=Qt.Alignment(0))

        changes = QTextEdit()
        changes.insertPlainText(text)
        changes.setReadOnly(True)
        changes.setFixedHeight(100)
        changes.moveCursor(QTextCursor.Start)
        changelog_layout.addWidget(changes, alignment=Qt.Alignment(0))

        changelog_widget.setLayout(changelog_layout)
        row_layout.addWidget(changelog_widget, alignment=Qt.Alignment(0))

        row_widget = QWidget(flags=self.flags)
        row_widget.setLayout(row_layout)
        row_widget.adjustSize()
        main_layout.addWidget(row_widget, alignment=Qt.Alignment(0))

        ok_btn = QPushButton('OK')
        ok_btn.setDefault(False)
        ok_btn.setAutoDefault(False)
        ok_btn.setFixedWidth(100)
        ok_btn.clicked.connect(d.accept)
        main_layout.addWidget(ok_btn, alignment=Qt.AlignCenter)

        d.setLayout(main_layout)
        d.setWindowTitle('')
        d.exec()

    def show_rework(self):
        d = windows.ModernDialog(self)
        d.setMinimumWidth(450)
        d.setFixedHeight(150)
        # d.setStyleSheet('border: 1px solid red')

        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        row_layout = QHBoxLayout()
        row_layout.setSpacing(10)
        row_layout.setContentsMargins(0, 0, 0, 0)

        pix = QPixmap(resource_path('./assets/potato.png'))
        pix = pix.scaled(60, 60)
        img = QLabel()
        img.setPixmap(pix)
        row_layout.addWidget(img, alignment=Qt.AlignCenter)

        changelog_widget = QWidget(flags=self.flags)
        changelog_layout = QVBoxLayout()
        changelog_layout.setSpacing(10)
        changelog_layout.setContentsMargins(0, 0, 0, 0)

        text = """
        THIS VERSION IS END OF LIFE!<br>
        <br>
        There will be no more support or updates.<br>
        Please download the new version from <a href=\"https://github.com/razaqq/PotatoAlertpy/releases/latest/download/PotatoAlert.zip\">HERE</a>.<br>
        <br>
        This message will only be shown once.<br>
        """

        font = QFont()
        font.setPointSize(12)
        text1 = QLabel(text)
        text1.setTextFormat(Qt.RichText)
        text1.setFont(font)
        text1.setAlignment(Qt.AlignCenter)
        text1.setOpenExternalLinks(True)
        changelog_layout.addWidget(text1, alignment=Qt.AlignCenter)

        changelog_widget.setLayout(changelog_layout)
        row_layout.addWidget(changelog_widget, alignment=Qt.AlignCenter)

        row_widget = QWidget(flags=self.flags)
        row_widget.setLayout(row_layout)
        row_widget.adjustSize()
        main_layout.addWidget(row_widget, alignment=Qt.AlignCenter)

        ok_btn = QPushButton('OK')
        ok_btn.setDefault(False)
        ok_btn.setAutoDefault(False)
        ok_btn.setFixedWidth(100)

        def seen():
            self.config['DEFAULT']['seen_rework'] = 'true'
            self.config.save()
            d.accept()
        ok_btn.clicked.connect(seen)
        main_layout.addWidget(ok_btn, alignment=Qt.AlignCenter)

        d.setLayout(main_layout)
        d.setWindowTitle('')
        d.exec()

    def switch_tab(self, new: int):
        old = self.menu_bar.btn_group.checkedId()
        tabs = {
            0: self.stats_widget,
            1: self.settings_widget,
            2: self.help_widget,
            5: self.about_widget
        }
        if not old == new:
            if self.menu_bar.btn_group.buttons()[old].isChecked():
                self.menu_bar.btn_group.buttons()[old].setChecked(False)
            if not self.menu_bar.btn_group.buttons()[new].isChecked():
                self.menu_bar.btn_group.buttons()[new].setChecked(True)

        tabs[new].setVisible(True)
        [tab.setVisible(False) for _id, tab in tabs.items() if _id != new]

    def connect_signals(self):
        self.pa.signals.status.connect(self.update_status)
        self.pa.signals.players.connect(self.fill_tables)
        self.pa.signals.averages.connect(self.team_stats.update_avg)
        self.pa.signals.servers.connect(self.team_stats.update_servers)
        self.pa.signals.clans.connect(self.team_stats.update_clans)

        def button_actions(btn):
            btn_id = self.menu_bar.btn_group.id(btn)
            if btn_id == 4:
                QDesktopServices.openUrl(QUrl('https://github.com/razaqq/PotatoAlert'))
            elif btn_id == 3:
                QDesktopServices.openUrl(QUrl.fromLocalFile(self.config.config_path))
            elif btn_id == 6:
                QDesktopServices.openUrl(QUrl('https://discord.gg/Ut8t8PA'))
            else:
                self.switch_tab(btn_id)

        self.menu_bar.btn_group.buttonClicked.connect(button_actions)
