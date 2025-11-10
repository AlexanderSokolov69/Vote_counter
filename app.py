from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
import os

from sqlalchemy import text
from sqlalchemy.exc import NoResultFound

app = Flask(__name__)

# Настройка SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.urandom(24)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Страница для редиректа при неавторизованном доступе


# Модель пользователя
class User(UserMixin, db.Model):
    id = db.Column(db.String, primary_key=True)


class Film(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    author = db.Column(db.String)
    number = db.Column(db.Integer, unique=True)


class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    film = db.Column(db.Integer, db.ForeignKey('film.id'))
    user = db.Column(db.Integer, db.ForeignKey('user.id'))
    vote = db.Column(db.Integer)


class State(db.Model):
    number = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String)


class Winners(db.Model):
    user = db.Column(db.String, primary_key=True)


# Создание базы данных
with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)


@app.route('/')
def index():
    return redirect(url_for('welcome'))


@app.route('/welcome', methods=['GET'])
@login_required
def welcome():
    number = db.session.execute(text('SELECT number FROM state')).one()[0]
    if number > 0:
        film_name = db.session.execute(text(f'SELECT id, name FROM film WHERE number={number}')).one()
        max_vote = db.session.execute(text(f"SELECT maxvote FROM state")).one()[0]
        try:
            old_vote = db.session.execute(text(f"SELECT vote FROM vote WHERE film={film_name[0]} "
                                               f"AND user='{current_user.id}'")).one()[0]
        except NoResultFound:
            old_vote = -1
        return render_template('Welcome.html',
                               number=number, user=current_user.id, film_name=film_name[1],
                               old_vote=old_vote, max_vote=max_vote)
    else:
        winners = [user[0] for user in db.session.execute(text(f'SELECT user FROM winners')).all()]
        alert = current_user.id in winners
        return render_template('Welcome2.html', alert=alert)


@app.route('/welcome', methods=['POST'])
@login_required
def welcome2():
    try:
        number = db.session.execute(text('SELECT number FROM state')).one()[0]
        film_id = db.session.execute(text(f'SELECT id FROM film WHERE number={number}')).one()[0]
        vote = request.form.get('range')
        db.session.execute(text(f"DELETE FROM vote WHERE film={film_id} AND user='{current_user.id}'"))
        new_vote = Vote(film=film_id, vote=vote, user=current_user.id)
        db.session.add(new_vote)
        db.session.commit()
        return redirect(url_for('welcome'))
    except Exception:
        return redirect(url_for('stat'))


@app.route('/stat', methods=['GET', 'POST'])
def stat():
    number = db.session.execute(text('SELECT number FROM state')).one()[0]
    if number == 0:
        return redirect(url_for('welcome'))
    film_id = db.session.execute(text(f'SELECT name FROM film WHERE number={number}')).one()[0]
    count_users = db.session.execute(text('SELECT COUNT(id) FROM user')).one()[0]
    count_votes = db.session.execute(text("""SELECT COUNT(vote.id), film.name FROM vote 
                                LEFT JOIN film on film.id = vote.film
                                GROUP BY film.name
                                ORDER BY film.number""")).fetchall()
    return render_template('stat.html',
                           count_users=count_users, count_votes=count_votes, film_id=film_id,
                           number=number)


@app.route('/login')
def login():
    user_ip = request.remote_addr
    user = db.session.get(User, user_ip)

    if not user:  # Если пользователь еще не зарегистрирован
        # Автоматическая регистрация пользователя по его IP
        new_user = User(id=user_ip)
        db.session.add(new_user)
        db.session.commit()

    # Вход пользователя в систему
    login_user(db.session.get(User, user_ip))  # Входим в систему
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
    user = db.session.get(User, user_ip)

    if not user:
        # Автоматическая регистрация пользователя по его IP
        new_user = User(id=user_ip)
        db.session.add(new_user)
        db.session.commit()

        # Вход пользователя в систему
        login_user(new_user)


if __name__ == '__main__':
    host = '0.0.0.0'
    port = 5555
    app.run(host=host, port=port, debug=True)
