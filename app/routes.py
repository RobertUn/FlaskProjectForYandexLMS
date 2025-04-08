from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user

from app.extensions import db
from app.forms import LoginForm, RegistrationForm
from app.models import User

auth_bp = Blueprint('auth', __name__)  # Создаем Blueprint


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():  # Проверка данных формы
        # Проверяем, нет ли уже такого пользователя
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Этот логин уже занят!', 'error')
            return redirect(url_for('register'))

        # Создаем нового пользователя
        user = User(username=form.username.data)
        user.set_password(form.password.data)  # Хешируем пароль
        db.session.add(user)
        db.session.commit()

        flash('Регистрация прошла успешно! Теперь можно войти.', 'success')
        return redirect(url_for('auth.login'))  # Перенаправляем на страницу входа

    return render_template('register.html', form=form)  # Шаблон сделаем позже


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        # Проверяем пароль
        if user and user.check_password(form.password.data):
            login_user(user)  # Создаем сессию пользователя
            flash('Вы успешно вошли!', 'success')
            return redirect(url_for('dashboard'))  # Перенаправляем в личный кабинет
        else:
            flash('Неверный логин или пароль!', 'error')

    return render_template('login.html', form=form)


@auth_bp.route('/')  # Или создайте отдельный Blueprint для главной страницы
def home():
    return "Добро пожаловать! Перейдите на /auth/login или /auth/register"
