from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from urllib.parse import urlparse
from app.models import db, User, Organization

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'coordinator':
            return redirect(url_for('coordinator.dashboard'))
        return redirect(url_for('volunteer.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not email or not password:
            flash('Пожалуйста, заполните email и пароль.', 'danger')
            return render_template('auth/login.html')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f'Добро пожаловать, {user.full_name}!', 'success')
            next_page = request.args.get('next')
            if next_page:
                parsed_next = urlparse(next_page)
                if not parsed_next.netloc and not parsed_next.scheme and parsed_next.path.startswith('/'):
                    return redirect(next_page)
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'coordinator':
                return redirect(url_for('coordinator.dashboard'))
            return redirect(url_for('volunteer.dashboard'))
        else:
            flash('Неверный адрес электронной почты или пароль.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', 'volunteer')
        if not email or not password or not full_name:
            flash('Пожалуйста, заполните все обязательные поля.', 'warning')
            return redirect(url_for('auth.register'))
        if role not in ('volunteer', 'coordinator'):
            flash('Выбрана недопустимая роль.', 'warning')
            return redirect(url_for('auth.register'))
        city = request.form.get('city', 'Москва').strip()
        birth_date_str = request.form.get('birth_date')
        phone = request.form.get('phone', '').strip()

        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует.', 'warning')
            return redirect(url_for('auth.register'))

        birth_date = None
        if birth_date_str:
            try:
                birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        user = User(
            email=email,
            full_name=full_name,
            role=role,
            city=city,
            birth_date=birth_date,
            phone=phone
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Если регистрируется организатор, создаем черновик организации
        if role == 'coordinator':
            org_name = request.form.get('org_name', f'Организация {full_name}').strip()
            org = Organization(
                name=org_name,
                city=city,
                contact_email=email,
                contact_phone=phone,
                owner_id=user.id,
                is_verified=False  # Требует модерации (FR-03)
            )
            db.session.add(org)
            db.session.commit()
            flash('Регистрация успешна! Ваша организация отправлена на проверку модератором.', 'info')
        else:
            flash('Регистрация успешна! Вы вошли в систему.', 'success')

        login_user(user)
        return redirect(url_for('main.index'))

    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы.', 'info')
    return redirect(url_for('main.index'))
