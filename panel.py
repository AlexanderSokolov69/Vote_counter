import csv
import decimal
import sys
import time

import pyodbc
import logging
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QMessageBox, QFileDialog
from PyQt6.QtWidgets import QHeaderView, QTableWidget

from Ui_panel import Ui_MainWindow

TIMER_TIK = 500
FONT_MAIN = 13
FONT_ITOG = int(FONT_MAIN * 1.3)
WIDTH_APP = 1200
HEIGHT_APP = 700
WIDTH = 1920
HEIGHT = 1080
SqlNONE = 0
SqlMANY = 1
SqlONE = 2
SqlALL = 3

log_file = f"panel_log_{time.strftime("%Y%m%d%H%M%S", time.localtime())}.log"
logging.basicConfig(
    level=logging.INFO,  # Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s',  # Формат вывода сообщений
    filename=log_file,  # Файл, куда будут записываться логи (если хотите записывать в файл)
    filemode='a'  # Режим записи в файл: 'a' - добавление, 'w' - перезапись
)


# class MyQTableWidget(QTableWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#
#         style_sheet = """
#             QTableWidget::item: hover
#             {
#                 background - color:  # FFE6E6;
#                     color:  # 000000;
#             }
#             QTableWidget::item: selected
#             {
#                 background - color:  # CC0000;
#                     color:  # FFFFFF;
#             }
#         """
#         self.setStyleSheet(style_sheet)
#

class MyWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        logging.info('Программа запущена')
        self.table_refresh = False

        screen_w = self.screen().size().width()
        screen_h = self.screen().size().height()
        app_w, app_h = WIDTH_APP, HEIGHT_APP

        self.setGeometry(screen_w // 2 - app_w // 2,
                         screen_h // 2 - app_h // 2,
                         app_w, app_h)
        self.setWindowTitle('Онлайн голосование')
        self.pix_vote_5555 = QPixmap("static/images/voteflow-5555.png")
        self.pix_title = QPixmap("static/pictures/title_win.png")
        self.pix_vote = QPixmap("static/images/vote.png")
        self.label_9.setPixmap(self.pix_title)
        self.label_17.setPixmap(self.pix_vote_5555)
        self.labelVoting.setPixmap(self.pix_vote)
        self.label_12.setPixmap(self.pix_title)

        # self.con = pyodbc.connect(
        #     'DRIVER={ODBC Driver 17 for SQL Server};'
        #     'SERVER=172.16.1.12,1433;'
        #     'DATABASE=voteflow;'
        #     'UID=sa;'
        #     'PWD=Prestige2011!;'
        #     'TrustServerCertificate=yes')
        self.conn_string = """DRIVER={ODBC Driver 17 for SQL Server};
                        SERVER=172.16.1.12,1433;
                        DATABASE=voteflow;
                        UID=sa;
                        PWD=Prestige2011!;
                        TrustServerCertificate=yes"""

        self.tabWidget.currentChanged.connect(self.tabChanged)
        self.tableWidget.itemChanged.connect(self.t2_edit)
        self.t2AddButton.clicked.connect(self.t2_add_rec)
        self.t2DelButton.clicked.connect(self.t2_del_rec)
        self.t2ClearButton.clicked.connect(self.t2_clear_users)
        self.t2LoadButton.clicked.connect(self.t2_refresh)
        self.t3NextButton.clicked.connect(self.t3_next)
        self.t3PrevButton.clicked.connect(self.t3_prev)
        self.t3StopButton.clicked.connect(self.t3_stop)
        self.t1ClearButton.clicked.connect(self.t1_clear_vote)
        self.t1MaxVote.valueChanged.connect(self.t1on_change_max_vote)
        self.t4PushButton.clicked.connect(self.t4_save_users)
        self.t1ClearWin.clicked.connect(self.t1_clear_win)
        self.t4ResultTable.itemSelectionChanged.connect(self.result_contecst)

        self.t3Users.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.t3Etap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.t3Votes.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.t3Stat.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.vote_numbers = []
        self.current_vote = 0
        self.current_winner = 0

        self.t1_timer = QTimer()
        self.t1_timer.timeout.connect(self.t1_users_timer)
        self.t3_timer = QTimer()
        self.t3_timer.timeout.connect(self.t3_stistica)
        self.t4_timer = QTimer()
        self.t4_timer.timeout.connect(self.t4_itog)
        self.tabWidget.setCurrentIndex(0)
        self.tabWidget.currentChanged.emit(0)

    def get_db_connection(self):
        try:
            engine = pyodbc.connect(self.conn_string, timeout=120)
            return engine
        except pyodbc.OperationalError as e:
            logging.error(f"get_db_connection(): {e}")
            time.sleep(5)  # Подождать 5 секунд
            return self.get_db_connection()  # Попытка повторного подключения

    def db_operate(self, sql, params=None, state=SqlNONE):
        logging.debug(f"SQL команда: {state} : {sql} : {params}")
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cur:
                match state:
                    case 0:
                        if params:
                            ret = cur.execute(sql, params)
                        else:
                            ret = cur.execute(sql)
                    case 1:
                        if params:
                            ret = cur.executemany(sql, params)
                        else:
                            ret = cur.executemany(sql)
                    case 2:
                        if params:
                            ret = cur.execute(sql, params).fetchone()
                        else:
                            ret = cur.execute(sql).fetchone()
                    case 3:
                        if params:
                            ret = cur.execute(sql, params).fetchall()
                        else:
                            ret = cur.execute(sql).fetchall()
            return ret
        except pyodbc.OperationalError as e:
            logging.error(f"db_operate(): {e}")
        except Exception as e:
            logging.error(f'db_operate(): {e}')
        finally:
            conn.close()

    def t1_users_timer(self):
        self.update_tab2_users()

    def t1_clear_win(self):
        self.db_operate('DELETE FROM winners')
        stamp = time.strftime("%Y%m%d%H%M%S", time.localtime())
        self.db_operate(f'UPDATE state SET state={stamp}')
        self.tabWidget.currentChanged.emit(0)

    def t4_save_users(self):
        users = [(user,) for user in
                 set(self.t4UsersTable.item(item.row(), 0).text() for item in self.t4UsersTable.selectedItems())]
        self.db_operate('DELETE FROM winners')
        if users:
            ret = QMessageBox.question(self, 'Оповещение', f"Оповестить {len(users)} участников?")
            if ret == QMessageBox.StandardButton.Yes:
                self.t3StopButton.click()
                sql = """INSERT INTO winners
                         VALUES (?)"""
                self.db_operate(sql, users, SqlMANY)
                self.t4UsersTable.clearSelection()
        stamp = time.strftime("%Y%m%d%H%M%S", time.localtime())
        self.db_operate(f'UPDATE state SET state={stamp}')
        self.t4_itog()

    def resizeEvent(self, event):
        width, height = event.size().width(), event.size().height()
        f_main = int(FONT_MAIN + (width - 1200) * 0.003)
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
            except IndexError as e:
                self.statusbar.showMessage('Достигнут конец списка')
                logging.info(f"t3_next(): {e}")
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
        except IndexError as e:
            logging.info(f"t3_prev(): {e}")
            self.t3_stop()

    def t2_refresh(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Загрузка', '', 'CSV Files (*.csv);;All Files (*)')
        data = []
        logging.info(f"Попытка загрузки файла: {fname}")
        try:
            with open(fname, 'r', encoding='utf-8') as f:
                csv_reader = csv.reader(f, delimiter=';')
                data = sorted([(rec[1].strip(), rec[2].strip(), int(rec[0]))
                               for rec in csv_reader if len(rec) >= 3], key=lambda x: x[0])
            ret = QMessageBox.question(self, 'Загрузка', f'Загрузить {len(data)} записей в базу?',
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ret == QMessageBox.StandardButton.Yes:
                sql = """INSERT INTO film (name, author, number)
                         VALUES (?, ?, ?)"""
                self.db_operate(sql, data, SqlMANY)
        except Exception as e:
            self.statusbar.showMessage('Ошибки загрузки файла..')
            logging.error('t2_refresh(): ' + str(e))
            QMessageBox.about(self, 'Ошибка загрузки!' 'Неправильный формат файла.')
        self.tabChanged(1)

    def t2_clear_users(self):
        ret = QMessageBox.question(self, 'Сброс', f'Очистить список участников голосования?',
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            self.db_operate('DELETE FROM users')
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
                self.current_winner = 0
                self.t4_timer.start(TIMER_TIK * 3)

    def t1_prepare(self):
        self.t3StopButton.click()
        stat = self.db_operate('SELECT COUNT(*) FROM vote', state=SqlONE)[0]
        self.t1Stat.setText(str(stat))
        self.t1Stat.setAlignment(Qt.AlignmentFlag.AlignCenter)
        max_vote = self.db_operate('SELECT maxvote FROM state', state=SqlONE)[0]
        self.t1MaxVote.setValue(max_vote)
        winner = self.db_operate('SELECT COUNT(*) FROM winners', state=SqlONE)[0]
        self.t1CountWin.setText(str(winner))

    def t1on_change_max_vote(self, num):
        sql = f"UPDATE state SET maxvote = {num}"
        self.db_operate(sql)

    def t1_clear_vote(self):
        ret = QMessageBox.question(self, 'Очистка', 'Удалить ВСЕ голоса?',
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            self.db_operate('DELETE FROM vote')
            self.t1_prepare()

    def t3_stistica(self):
        try:
            sql = """SELECT film.number, COUNT(vote.id), film.name
                     FROM vote
                              INNER JOIN film on film.id = vote.film
                     GROUP BY film.name, film.number
                     ORDER BY film.number DESC"""
            count_votes = converter(self.db_operate(sql, state=SqlALL))
            self.t3StatTable.setRowCount(len(count_votes))
            self.t3StatTable.setColumnCount(len(count_votes[0]))
            self.t3StatTable.setHorizontalHeaderLabels(['№ этапа', 'Проголосовало', 'Наименование'])
            self.t3StatTable.verticalHeader().hide()
            self.t3StatTable.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            voting = False
            for row, rec in enumerate(count_votes):
                for col, item in enumerate(rec):
                    self.t3StatTable.setItem(row, col, item)
                    if rec[0].text() and float(rec[0].text()) == float(self.t3LcdCount.value()):
                        self.t3StatTable.item(row, col).setBackground(QColor('#ff0000'))
                        voting = True
            self.labelVoting.setVisible(voting)
            self.t3StatTable.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            for col in range(1, self.t3StatTable.columnCount() - 1):
                self.t3StatTable.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        except Exception as e:
            self.t3StatTable.setRowCount(0)
            self.statusbar.showMessage('Голосов нет.')
            logging.info(f"t3_stistica(): {e}")
        try:
            sql = """SELECT COUNT(*)                                                      as cnt,
                            (SELECT COUNT(*) FROM (SELECT DISTINCT film FROM vote) as et) as etaps,
                            (SELECT COUNT(*) FROM vote)                                   as votes
                     FROM users"""
            stats = self.db_operate(sql, state=SqlONE)
            self.t3Users.setText(str(stats[0]))
            self.t3Etap.setText(str(stats[1]))
            self.t3Votes.setText(str(stats[2]))
            self.t3Stat.setText(f"{stats[2] / stats[1]:.2f}")
            self.statusbar.showMessage('')
        except Exception as e:
            self.t3Users.setText('---')
            self.t3Etap.setText('---')
            self.t3Votes.setText('---')
            self.t3Stat.setText('---')
            self.statusbar.showMessage('Голосов нет.')
            logging.info(f"t3_stistica(): {e}")

    def prepare_voting(self):
        self.vote_numbers = [rec[0] for rec in
                             self.db_operate("SELECT number FROM film ORDER BY number", state=SqlALL)]
        self.t3LcdAll.display(str(len(self.vote_numbers)))
        vote = self.db_operate("SELECT number FROM state", state=SqlONE)[0]
        if not vote:
            vote = 0
        self.set_current_vote(vote)

    def set_current_vote(self, num):
        self.current_vote = num
        self.t3LcdCount.display(str(self.current_vote))
        self.db_operate(f"UPDATE state SET number = {self.current_vote}")

    def update_tab2_users(self):
        data = converter(self.db_operate('select * from users', state=SqlALL))
        if not data:
            data = [[]]
        self.t2Users.setText(str(len(data)))
        self.t2Users.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tableUsers.setRowCount(len(data))
        self.tableUsers.setColumnCount(len(data[0]))
        self.tableUsers.setHorizontalHeaderLabels(['Участник'])
        self.tableUsers.verticalHeader().hide()
        for row, rec in enumerate(data):
            for col, item in enumerate(rec):
                self.tableUsers.setItem(row, col, item)
                self.tableUsers.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

    def t2_edit(self, item):
        if self.table_refresh:
            return
        if self.current_vote:
            QMessageBox.about(self, 'Внимание', 'Идёт голосование. Изменения запрещены!')
        else:
            ret = QMessageBox.question(self, 'Сохранение', 'Сохранить изменение?',
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ret == QMessageBox.StandardButton.Yes:
                try:
                    id_ = self.tableWidget.item(item.row(), 0).text()
                    sql = """SELECT *
                             FROM film
                             WHERE id = ?"""
                    data = list(self.db_operate(sql, params=(id_,), state=SqlONE))
                    headers = ['id', 'name', 'author', 'number']
                    header = headers[item.column()]
                    sql_numbers = self.db_operate("SELECT number FROM film", state=SqlALL)
                    numbers = [num[0] for num in sql_numbers]
                    if item.column() != 3 or int(item.text()) not in numbers:
                        self.db_operate(f"UPDATE film SET {header}=? WHERE id=?", params=(item.text(), id_))
                    else:
                        QMessageBox.about(self, 'Внимание!', 'Не уникальный номер!')
                        self.statusbar.showMessage('Не уникальный номер')
                except Exception as e:
                    logging.error(f"t2_edit(): {e}")
        self.update_tab2()

    def t2_del_rec(self):
        if self.current_vote:
            QMessageBox.about(self, 'Внимание', 'Идёт голосование. Изменения запрещены!')
        else:
            ids = set(self.tableWidget.item(item.row(), 0).text() for item in self.tableWidget.selectedItems())
            ret = QMessageBox.question(self, 'Удаление', f'Удалить {len(ids)} записей?',
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ret == QMessageBox.StandardButton.Yes:
                data = ', '.join([str(id_) for id_ in ids])
                sql = f"""DELETE FROM film WHERE id in ({data})"""
                self.db_operate(sql)
                self.update_tab2()

    def t2_add_rec(self):
        if self.current_vote:
            QMessageBox.about(self, 'Внимание', 'Идёт голосование. Изменения запрещены!')
        else:
            sql = "insert into film  (name, author, number) values ('', '', (SELECT max(number) FROM film ) + 1)"
            self.db_operate(sql)
            self.update_tab2()

    def update_tab2(self):
        try:
            self.table_refresh = True
            result = converter(self.db_operate("SELECT * FROM film ORDER BY number", state=SqlALL))
            self.tableWidget.setRowCount(len(result))
            self.tableWidget.setColumnCount(len(result[0]))
            self.t2Count.setText(str(len(result)))
            self.t2Count.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tableWidget.setHorizontalHeaderLabels(['id', 'Наименование', 'Автор', '№пп'])
            self.tableWidget.verticalHeader().hide()
            for row, rec in enumerate(result):
                for col, item in enumerate(rec):
                    self.tableWidget.setItem(row, col, item)
            self.tableWidget.hideColumn(0)
            for col in range(self.tableWidget.columnCount()):
                self.tableWidget.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
            self.tableWidget.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

            self.statusbar.showMessage('')
            self.table_refresh = False
        except Exception as e:
            logging.error('update_tab2: ' + str(e))

    def result_contecst(self):
        self.current_winner = self.t4ResultTable.selectedItems()[0].row()
        self.t4_itog()

    def t4_itog(self):
        try:
            sql = """SELECT f.id,
                            f.author,
                            f.name,
                            f.number,
                            COUNT(v.id)                     as votes,
                            MAX(v.vote)                     as max,
                            MIN(v.vote)                     as min,
                            SUM(v.vote)                     as summa,
                            SUM(v.vote) * 1.0 / COUNT(v.id) as result
                     FROM vote v
                              LEFT JOIN film f ON f.id = v.film
                     GROUP BY f.id, f.author, f.name, f.number, v.film
                     ORDER BY result DESC"""
            data = converter(self.db_operate(sql, state=SqlALL))
            if not data:
                data = [[]]
            self.t4ResultTable.setRowCount(len(data))
            self.t4ResultTable.setColumnCount(len(data[0]))
            header = ['id', 'Автор', "Наименование работы", "Этап", "Голосов", "Макс.",
                      "Мин.", "Сумма", "Ср.балл"]
            self.t4ResultTable.setHorizontalHeaderLabels(header)
            self.t4ResultTable.verticalHeader().hide()
            self.t4ResultTable.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            for row, rec in enumerate(data):
                for col, item in enumerate(rec):
                    self.t4ResultTable.setItem(row, col, item)
                    color = None
                    match row:
                        case 0:
                            if row == self.current_winner:
                                color = QColor('red')
                            else:
                                color = QColor('#ffcccc')
                        case self.current_winner:
                            color = QColor('#99ff99')
                    if color:
                        self.t4ResultTable.item(row, col).setBackground(color)
            self.t4ResultTable.hideColumn(0)
            for col in range(self.t4ResultTable.columnCount()):
                self.t4ResultTable.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
            self.t4ResultTable.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        except Exception as e:
            self.t4ResultTable.setRowCount(0)
            self.statusbar.showMessage('Результатов нет')
            logging.error('t4_itog(): ' + str(e))
        try:
            best_film_id = data[self.current_winner][0].text()
            sql = f"""SELECT v.users, v.vote, 
                    (SELECT SUM(v2.vote) * 1.0 / (COUNT(v2.vote)) FROM vote v2 WHERE v2.users=v.users) as aver,
                    (SELECT COUNT(*) FROM winners WHERE users=v.users) as win
                    FROM vote v
                    WHERE v.film = {best_film_id}
                    GROUP BY v.users,v.vote
                    ORDER BY vote DESC, aver"""
            users = converter(self.db_operate(sql, state=SqlALL))
            self.t4UsersTable.setRowCount(len(users))
            self.t4UsersTable.setColumnCount(len(users[0]))
            self.t4UsersTable.setHorizontalHeaderLabels(['Участник', 'Балл', 'Ср.балл'])
            self.t4UsersTable.hideColumn(3)
            self.t4UsersTable.verticalHeader().hide()
            self.t4UsersTable.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            for row, user in enumerate(users):
                for col, item in enumerate(user):
                    self.t4UsersTable.setItem(row, col, item)
                    if user[3].text() != '0':
                        self.t4UsersTable.item(row, col).setForeground(QColor('red'))
            self.t4UsersTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            if self.current_vote == 0:
                self.t4_timer.stop()
        except Exception as e:
            self.t4UsersTable.setRowCount(0)
            self.statusBar().showMessage('Итогов нет')
            logging.error('t4_itog(): ' + str(e))


def converter(data):
    out = []
    try:
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
    except TypeError as e:
        logging.error('converter(): ' + str(e))
    return out


def except_hook(exc_type, exc_value, exc_tb):
    logging.error(f'exept_hook: {exc_type}, {exc_value}, {exc_tb}')
    sys.__excepthook__(exc_type, exc_value, exc_tb)


if __name__ == '__main__':
    sys.excepthook = except_hook
    app = QApplication(sys.argv)
    win = MyWindow()
    win.show()
    sys.exit(app.exec())
