import os
import time
import pyodbc
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy

from sqlalchemy import text, QueuePool
from sqlalchemy.exc import NoResultFound
from flask_apscheduler import APScheduler

os.environ['DATABASE_URL'] = """mssql+pyodbc://sa:Prestige2011!@172.16.1.12,1433/voteflow?driver=ODBC+Driver+17+for+SQL+Server"""

app = Flask(__name__)
last_change = [None]
old_state = [None]

# Настройка SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
# app.config['SQLALCHEMY_DATABASE_URI'] = (
#     'mssql+pyodbc://'
#     'sa:Prestige2011!@'
#     '172.16.1.12,1433/voteflow?'
#     'driver=ODBC+Driver+17+for+SQL+Server'
# )
# Driver=SQL Server;Server=172.16.1.12,1433;Database=Journal4303;UID=sa;PWD=Prestige2011!;
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'poolclass': QueuePool,
    'pool_recycle': 600,
    'pool_pre_ping': True,
    'pool_size': 10,
    'max_overflow': 20
}
app.secret_key = os.urandom(24)

app.config['SCHEDULER_API_ENABLED'] = True
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Страница для редиректа при неавторизованном доступе


# Модель пользователя
class Users(UserMixin, db.Model):
    id = db.Column(db.String(20), primary_key=True)


class Film(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100))
    author = db.Column(db.String(100))
    number = db.Column(db.Integer, unique=True)


class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    film = db.Column(db.Integer, db.ForeignKey('film.id'))
    users = db.Column(db.String(20), db.ForeignKey('users.id'))
    vote = db.Column(db.Integer)


class State(db.Model):
    number = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(40))


class Winners(db.Model):
    users = db.Column(db.String(20), primary_key=True)


# Создание базы данных
with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Users, user_id)


@app.route('/')
def index():
    return redirect(url_for('welcome'))


@app.route('/welcome', methods=['GET'])
@login_required
def welcome():
    try:
        number = db.session.execute(text('SELECT number FROM state')).fetchone()[0]
    except NoResultFound:
        number = 0
    if number > 0:
        try:
            film_name = db.session.execute(text(f'SELECT id, name FROM film WHERE number={number}')).fetchone()
            max_vote = db.session.execute(text(f"SELECT maxvote FROM state")).fetchone()[0]
        except NoResultFound:
            film_name = (0, '_')
            max_vote = 10
        try:
            sql =f"SELECT vote FROM vote WHERE film={film_name[0]} AND users='{current_user.id.strip()}'"
            old_vote = db.session.execute(text(sql)).one()[0]
        except NoResultFound:
            old_vote = -1
        return render_template('Welcome.html',
                               number=number, user=current_user.id, film_name=film_name[1],
                               old_vote=old_vote, max_vote=max_vote)
    else:
        winners = [user[0] for user in db.session.execute(text(f'SELECT users FROM winners')).all()]
        alert = current_user.id in winners
        return render_template('Welcome2.html', alert=alert)


@app.route('/welcome', methods=['POST'])
@login_required
def welcome2():
    try:
        number = db.session.execute(text('SELECT number FROM state')).fetchone()[0]
        film_id = db.session.execute(text(f'SELECT id FROM film WHERE number={number}')).fetchone()[0]
        vote = request.form.get('range')
        db.session.execute(text(f"DELETE FROM vote WHERE film={film_id} AND users='{current_user.id}'"))
        new_vote = Vote(film=film_id, vote=vote, users=current_user.id)
        db.session.add(new_vote)
        db.session.commit()
        return redirect(url_for('welcome'))

    except Exception:
        return redirect(url_for('stat'))


@app.route('/stat', methods=['GET', 'POST'])
def stat():
    try:
        number = db.session.execute(text('SELECT number FROM state')).fetchone()[0]
    except NoResultFound:
        number = 0
    if number == 0:
        return redirect(url_for('welcome'))
    film_id = 0
    count_users = 0
    count_votes = 0
    try:
        film_id = db.session.execute(text(f'SELECT name FROM film WHERE number={number}')).fetchone()[0]
        count_users = db.session.execute(text('SELECT COUNT(id) FROM users')).fetchone()[0]
        count_votes = db.session.execute(text("""SELECT COUNT(vote.id), film.name FROM vote 
                                    LEFT JOIN film on film.id = vote.film
                                    GROUP BY film.name, film.number
                                    ORDER BY film.number""")).fetchall()
    except NoResultFound:
        pass
    return render_template('stat.html',
                           count_users=count_users, count_votes=count_votes, film_id=film_id,
                           number=number)


@app.route('/login')
def login():
    user_ip = request.remote_addr
    user = db.session.get(Users, user_ip)

    if not user:  # Если пользователь еще не зарегистрирован
        # Автоматическая регистрация пользователя по его IP
        new_user = Users(id=user_ip)
        db.session.add(new_user)
        db.session.commit()

    # Вход пользователя в систему
    login_user(db.session.get(Users, user_ip))  # Входим в систему
    return redirect(url_for('welcome'))


# @app.route('/logout')
# @login_required
# def logout():
#     logout_user()
#     return redirect(url_for('index'))
#
#
@app.before_request
def auto_register_user():
    user_ip = request.remote_addr
    user = db.session.get(Users, user_ip)

    if not user:
        # Автоматическая регистрация пользователя по его IP
        new_user = Users(id=user_ip)
        db.session.add(new_user)
        db.session.commit()

        # Вход пользователя в систему
        login_user(new_user)

@scheduler.task('interval', id='my_job', seconds=3)
def my_job():
    with app.app_context():
        try:
            new_state = db.session.execute(text('SELECT * FROM state')).fetchone()
            if old_state[0] != new_state:
                old_state[0] = new_state
                last_change[0] = True
        except Exception as e:
            print('error:', str(e))

@app.route('/updates')
def updates():
    """SSE endpoint: держит соединение и шлёт обновления при изменении last_change"""
    def generate():
        while True:
            time.sleep(1)
            if old_state:
                number = old_state[0][0]
            else:
                number = 0
            yield f"data: {number}\n\n"

    return app.response_class(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )

if __name__ == '__main__':
    host = '0.0.0.0'
    port = 5555
    app.run(host=host, port=port, debug=True)
