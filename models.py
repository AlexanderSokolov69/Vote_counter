from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy


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
