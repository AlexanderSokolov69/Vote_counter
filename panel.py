import decimal
import sys

import pyodbc
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QMessageBox

from Ui_panel import Ui_MainWindow

TIMER_TIK = 500
FONT_MAIN = 13
FONT_ITOG = int(FONT_MAIN * 1.3)
WIDTH_APP = 1200
HEIGHT_APP = 700
WIDTH = 1920
HEIGHT = 1080


class MyWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.table_refresh = False

        screen_w = self.screen().size().width()
        screen_h = self.screen().size().height()
        app_w, app_h = WIDTH_APP, HEIGHT_APP

        self.setGeometry(screen_w // 2 - app_w // 2,
                         screen_h // 2 - app_h // 2,
                         app_w, app_h)
        self.setWindowTitle('Онлайн голосование')
        self.pix_vote_5555 = QPixmap("static/images/voteflow-5555.png")
        self.pix_title = QPixmap("static/images/title.png")
        self.pix_vote = QPixmap("static/images/vote.png")
        self.label_9.setPixmap(self.pix_title)
        self.label_17.setPixmap(self.pix_vote_5555)
        self.labelVoting.setPixmap(self.pix_vote)
        self.label_12.setPixmap(self.pix_title)

        # self.con = sqlite3.connect('instance/users.db')
        # Driver=SQL Server;Server=172.16.1.12,1433;Database=Journal4303;UID=sa;PWD=Prestige2011!;
        self.con = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            'SERVER=172.16.1.12,1433;'
            'DATABASE=voteflow;'
            'UID=sa;'
            'PWD=Prestige2011!;'
            'TrustServerCertificate=yes')

        self.tabWidget.currentChanged.connect(self.tabChanged)
        self.tableWidget.itemChanged.connect(self.t2_edit)
        self.t2AddButton.clicked.connect(self.t2_add_rec)
        self.t2DelButton.clicked.connect(self.t2_del_rec)
        self.t2ClearButton.clicked.connect(self.t2_clear_users)
        self.t2RefreshButton.clicked.connect(self.t2_refresh)
        self.t3NextButton.clicked.connect(self.t3_next)
        self.t3PrevButton.clicked.connect(self.t3_prev)
        self.t3StopButton.clicked.connect(self.t3_stop)
        self.t1ClearButton.clicked.connect(self.t1_clear_vote)
        self.t1MaxVote.valueChanged.connect(self.t1on_change_max_vote)
        self.t4PushButton.clicked.connect(self.t4_save_users)
        self.t1ClearWin.clicked.connect(self.t1_clear_win)

        self.t3Users.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.t3Etap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.t3Votes.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.t3Stat.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.vote_numbers = []
        self.current_vote = 0

        self.t1_timer = QTimer()
        self.t1_timer.timeout.connect(self.t1_users_timer)
        self.t3_timer = QTimer()
        self.t3_timer.timeout.connect(self.t3_stistica)
        self.t4_timer = QTimer()
        self.t4_timer.timeout.connect(self.t4_itog)
        self.tabWidget.setCurrentIndex(0)
        self.tabWidget.currentChanged.emit(0)

    def resource_loader(self):
        ...

    def t1_users_timer(self):
        self.update_tab2_users()

    def t1_clear_win(self):
        with self.con.cursor() as cur:
            cur.execute('DELETE FROM winners')
        self.con.commit()
        self.tabWidget.currentChanged.emit(0)

    def t4_save_users(self):
        users = [(user,) for user in
                 set(self.t4UsersTable.item(item.row(), 0).text() for item in self.t4UsersTable.selectedItems())]
        with self.con.cursor() as cur:
            cur.execute("DELETE FROM winners")
        self.con.commit()
        if users:
            ret = QMessageBox.question(self, 'Оповещение', f"Оповестить {len(users)} участников?")
            if ret == QMessageBox.StandardButton.Yes:
                self.t3StopButton.click()
                sql = """INSERT INTO winners VALUES (?)"""
                with self.con.cursor() as cur:
                    cur.executemany(sql, users)
                self.con.commit()
                self.t4UsersTable.clearSelection()
        self.t4_itog()

    def resizeEvent(self, event):
        width, height = event.size().width(), event.size().height()
        f_main = int(FONT_MAIN + (width - 1200) * 0.005)
        f_itog = int(f_main * 1.3)
        self.setFont(QFont('Arial', f_main))
        self.t4ResultTable.setFont(QFont('Arial', f_itog))
        self.t3StatTable.setFont(QFont('Arial', f_itog))
        self.tabWidget.currentChanged.emit(self.tabWidget.currentIndex())
        return super().resizeEvent(event)

    def t3_stop(self):
        self.current_vote = 0
        self.statusbar.showMessage('Голосование остановлено')
        self.set_current_vote(self.current_vote)

    def t3_next(self):
        self.statusbar.showMessage('')
        if self.current_vote == 0:
            self.current_vote = self.vote_numbers[0]
        else:
            try:
                self.current_vote = self.vote_numbers[self.vote_numbers.index(self.current_vote) + 1]
            except IndexError:
                self.statusbar.showMessage('Достигнут конец списка')
        self.set_current_vote(self.current_vote)

    def t3_prev(self):
        try:
            if self.current_vote == 0:
                raise IndexError()
            else:
                i = self.vote_numbers.index(self.current_vote)
            if i <= 0:
                raise IndexError()
            self.current_vote = self.vote_numbers[i - 1]
            self.set_current_vote(self.current_vote)
            self.statusbar.showMessage('')
        except IndexError:
            self.t3_stop()

    def t2_refresh(self):
        self.tabChanged(1)

    def t2_clear_users(self):
        ret = QMessageBox.question(self, 'Сброс', f'Очистить список участников голосования?',
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            with self.con.cursor() as cur:
                cur.execute('DELETE FROM users')
            self.con.commit()
            self.update_tab2_users()

    def tabChanged(self, a0):
        self.t1_timer.stop()
        self.t3_timer.stop()
        self.t4_timer.stop()
        match a0:
            case 0:
                self.t1_prepare()
                self.t1_timer.start(TIMER_TIK * 2)
            case 1:
                self.update_tab2()
            case 2:
                self.prepare_voting()
                self.t3_timer.start(TIMER_TIK)
            case 3:
                self.t4_timer.start(TIMER_TIK * 3)

    def t1_prepare(self):
        self.t3StopButton.click()
        with self.con.cursor() as cur:
            stat = cur.execute('SELECT COUNT(*) FROM vote').fetchone()[0]
        self.t1Stat.setText(str(stat))
        self.t1Stat.setAlignment(Qt.AlignmentFlag.AlignCenter)
        with self.con.cursor() as cur:
            max_vote = cur.execute('SELECT maxvote FROM state').fetchone()[0]
        self.t1MaxVote.setValue(max_vote)
        with self.con.cursor() as cur:
            winner = cur.execute('SELECT COUNT(*) FROM winners').fetchone()[0]
        self.t1CountWin.setText(str(winner))

    def t1on_change_max_vote(self, num):
        sql = f"UPDATE state SET maxvote = {num}"
        with self.con.cursor() as cur:
            try:
                cur.execute(sql)
                self.con.commit()
            except Exception as e:
                self.statusbar.showMessage(str(e))

    def t1_clear_vote(self):
        ret = QMessageBox.question(self, 'Очистка', 'Удалить ВСЕ голоса?',
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            with self.con.cursor() as cur:
                cur.execute('DELETE FROM vote')
            self.con.commit()
            self.t1_prepare()

    def t3_stistica(self):
        with self.con.cursor() as cur:
            try:
                self.t3StatTable.clear()
                count_votes = converter(cur.execute("""SELECT film.number, COUNT(vote.id), film.name FROM vote 
                                            LEFT JOIN film on film.id = vote.film
                                            GROUP BY film.name, film.number
                                            ORDER BY film.number DESC""").fetchall())
            except Exception as e:
                count_votes = []
                self.statusbar.showMessage('Голосов нет.' + str(e))
        self.t3StatTable.setRowCount(len(count_votes))
        self.t3StatTable.setColumnCount(len(count_votes[0]))
        self.t3StatTable.setHorizontalHeaderLabels(['№ этапа', 'Проголосовало', 'Наименование'])
        voting = False
        for row, rec in enumerate(count_votes):
            for col, item in enumerate(rec):
                self.t3StatTable.setItem(row, col, item)
                # if isinstance(item, int):
                #     self.t3StatTable.item(row, col).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if float(rec[0].text()) == float(self.t3LcdCount.value()):
                    self.t3StatTable.item(row, col).setBackground(QColor('#ff0000'))
                    voting = True
        self.labelVoting.setVisible(voting)
        self.t3StatTable.resizeColumnsToContents()
        sql = """SELECT COUNT(*) as cnt, 
                    (SELECT COUNT(*) FROM (SELECT DISTINCT film FROM vote) as et) as etaps , 
                    (SELECT COUNT(*) FROM vote) as votes
                FROM users"""
        with self.con.cursor() as cur:
            try:
                stats = cur.execute(sql).fetchone()
                self.t3Users.setText(str(stats[0]))
                self.t3Etap.setText(str(stats[1]))
                self.t3Votes.setText(str(stats[2]))
                self.t3Stat.setText(f"{stats[2] / stats[1]:.2f}")
                self.statusbar.showMessage('')
            except Exception as e:
                self.statusbar.showMessage('Голосов нет.' + str(e))

    def prepare_voting(self):
        with self.con.cursor() as cur:
            self.vote_numbers = [rec[0] for rec in cur.execute("SELECT number FROM film ORDER BY number").fetchall()]
            self.t3LcdAll.display(str(len(self.vote_numbers)))
            vote = cur.execute("SELECT number FROM state").fetchone()[0]
        self.set_current_vote(vote)

    def set_current_vote(self, num):
        self.current_vote = num
        with self.con.cursor() as cur:
            self.t3LcdCount.display(str(self.current_vote))
            cur.execute(f"UPDATE state SET number = {self.current_vote}")
        self.con.commit()

    def update_tab2_users(self):
        with self.con.cursor() as cur:
            try:
                data = converter(cur.execute('select * from users').fetchall())
                self.t2Users.setText(str(len(data)))
                self.t2Users.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tableUsers.setRowCount(len(data))
                self.tableUsers.setColumnCount(len(data[0]))
                self.tableUsers.setHorizontalHeaderLabels(['Участник'])
                for row, rec in enumerate(data):
                    for col, item in enumerate(rec):
                        self.tableUsers.setItem(row, col, item)
                self.tableUsers.resizeColumnsToContents()
            except Exception as e:
                self.statusBar().showMessage(str(e))

    def t2_edit(self, item):
        if self.table_refresh:
            return
        ret = QMessageBox.question(self, 'Сохранение', 'Сохранить изменение?',
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            try:
                id_ = self.tableWidget.item(item.row(), 0).text()
                sql = """SELECT * FROM film WHERE id=?"""
                with self.con.cursor() as cur:
                    data = list(cur.execute(sql, (id_,)).fetchone())
                # old_field = data[item.column()]
                data[item.column()] = item.text()
                numbers = [str(num[0]) for num in cur.execute("SELECT number FROM film").fetchall()]
                if item.column() != 4 or str(data[3]) not in numbers:
                    with self.con.cursor() as cur:
                        cur.execute("DELETE FROM film WHERE id=?", (id_,))
                    sql = "INSERT INTO film VALUES(?, ?, ?, ?)"
                    with self.con.cursor() as cur:
                        cur.execute(sql, data)
                    self.con.commit()
                else:
                    self.statusbar.showMessage('Не уникальный номер')
            except Exception as e:
                self.statusBar().showMessage(str(e))
            self.tableWidget.resizeColumnsToContents()

    def t2_del_rec(self):
        ids = set(self.tableWidget.item(item.row(), 0).text() for item in self.tableWidget.selectedItems())
        ret = QMessageBox.question(self, 'Удаление', f'Удалить {len(ids)} записей?',
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            data = ', '.join([str(id_) for id_ in ids])
            sql = f"""DELETE FROM film WHERE id in ({data})"""
            with self.con.cursor() as cur:
                cur.execute(sql)
            self.con.commit()
            self.update_tab2()

    def t2_add_rec(self):
        with self.con.cursor() as cur:
            sql = "insert into film  (name, author, number) values ('', '', (SELECT max(number) FROM film ) + 1)"
            cur.execute(sql)
        self.con.commit()
        self.update_tab2()

    def update_tab2(self):
        try:
            self.table_refresh = True
            with self.con.cursor() as cur:
                result = converter(cur.execute("""SELECT * FROM film ORDER BY number""").fetchall())
            self.tableWidget.setRowCount(len(result))
            self.tableWidget.setColumnCount(len(result[0]))
            self.t2Count.setText(str(len(result)))
            self.t2Count.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tableWidget.setHorizontalHeaderLabels(['id', 'Наименование', 'Автор', '№пп'])
            for row, rec in enumerate(result):
                for col, item in enumerate(rec):
                    self.tableWidget.setItem(row, col, item)
                    # if isinstance(item, int):
                    #     self.tableWidget.item(row, col).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tableWidget.hideColumn(0)
            self.tableWidget.resizeColumnsToContents()
            self.statusbar.showMessage('')
            self.table_refresh = False
        except Exception as e:
            self.statusbar.showMessage(str(e))

    def t4_itog(self):
        sql = """SELECT f.id, f.author, f.name, f.number, COUNT(v.id) as votes, 
                    MAX(v.vote) as max, MIN(v.vote) as min, SUM(v.vote) as summa,
                    SUM(v.vote) * 1.0 / COUNT(v.id) as result
                FROM vote v
                LEFT JOIN film f ON f.id = v.film
                GROUP BY f.id, f.author, f.name, f.number, v.film
                ORDER BY result DESC"""
        try:
            with self.con.cursor() as cur:
                data = converter(cur.execute(sql).fetchall())
            self.t4ResultTable.setRowCount(len(data))
            self.t4ResultTable.setColumnCount(len(data[0]))
            header = ['id', 'Автор', "Наименование работы", "№ этапа", "Голосов", "Макс.балл",
                      "Мин.балл", "Сумма", "Средний балл"]
            self.t4ResultTable.setHorizontalHeaderLabels(header)
            for row, rec in enumerate(data):
                for col, item in enumerate(rec):
                    self.t4ResultTable.setItem(row, col, item)
                    if row == 0:
                        self.t4ResultTable.item(row, col).setBackground(QColor('red'))
                    # if isinstance(item, int | float):
                    #     self.t4ResultTable.item(row, col).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.t4ResultTable.hideColumn(0)
            self.t4ResultTable.resizeColumnsToContents()
            self.statusbar.showMessage('')
            self.t4UsersTable.clear()
            if data:
                best_film_id = data[0][0].text()
            else:
                best_film_id = 0
            sql = f"""SELECT v.users, v.vote, 
                    (SELECT SUM(v2.vote) * 1.0 / (COUNT(v2.vote)) FROM vote v2 WHERE v2.users=v.users) as aver,
                    (SELECT COUNT(*) FROM winners WHERE users=v.users) as win
                    FROM vote v
                    WHERE v.film = {best_film_id}
                    GROUP BY v.users,v.vote
                    ORDER BY vote DESC, aver"""
            with self.con.cursor() as cur:
                users = converter(cur.execute(sql).fetchall())
            self.t4UsersTable.setRowCount(len(users))
            self.t4UsersTable.setColumnCount(len(users[0]))
            self.t4UsersTable.setHorizontalHeaderLabels(['Участник', 'Балл', 'Ср.балл'])
            self.t4UsersTable.hideColumn(3)
            for row, user in enumerate(users):
                for col, item in enumerate(user):
                    self.t4UsersTable.setItem(row, col, item)
                    if user[3].text() != '0':
                        self.t4UsersTable.item(row, col).setForeground(QColor('red'))
            self.t4UsersTable.resizeColumnsToContents()
            if self.current_vote == 0:
                self.t4_timer.stop()
        except Exception as e:
            self.statusBar().showMessage('Итогов нет' + str(e))


def converter(data):
    out = []
    for record in data:
        result = []
        for rec in record:
            if isinstance(rec, str):
                result.append(QTableWidgetItem(rec.strip()))
            elif isinstance(rec, decimal.Decimal):
                result.append(QTableWidgetItem(f"{float(rec):.2f}"))
                result[-1].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                result.append(QTableWidgetItem(str(rec)))
                result[-1].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        out.append(result)
    return out


def except_hook(exc_type, exc_value, exc_tb):
    sys.__excepthook__(exc_type, exc_value, exc_tb)


if __name__ == '__main__':
    sys.excepthook = except_hook
    app = QApplication(sys.argv)
    win = MyWindow()
    win.show()
    sys.exit(app.exec())
