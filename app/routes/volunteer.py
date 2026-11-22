from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime
from app.models import db, Shift, Application

volunteer_bp = Blueprint('volunteer', __name__)

@volunteer_bp.route('/dashboard')
@login_required
def dashboard():
    applications = Application.query.filter_by(volunteer_id=current_user.id).order_by(Application.applied_at.desc()).all()
    total_hours = current_user.total_hours
    attended_count = sum(1 for a in applications if a.status == 'attended')
    
    return render_template('volunteer/dashboard.html', 
                           applications=applications,
                           total_hours=total_hours,
                           attended_count=attended_count)

@volunteer_bp.route('/apply/<int:shift_id>', methods=['POST'])
@login_required
def apply_shift(shift_id):
    shift = Shift.query.get_or_404(shift_id)

    # Проверка на повторную подачу
    existing_app = Application.query.filter_by(shift_id=shift.id, volunteer_id=current_user.id).first()
    if existing_app and existing_app.status != 'cancelled':
        flash('Вы уже подали заявку на эту смену!', 'warning')
        return redirect(url_for('main.project_detail', project_id=shift.project_id))

    # Проверка возраста (FR-21)
    # Проверяем, указана ли дата рождения
    if current_user.birth_date is None:
        flash('Для записи на смену сначала укажите дату рождения в профиле.', 'warning')
        return redirect(url_for('main.project_detail', project_id=shift.project_id))

    # Проверяем минимальный возраст
    if current_user.age < shift.min_age:
        flash(
            f'Данный проект рассчитан на участников от {shift.min_age} лет. '
            f'Ваш возраст: {current_user.age}.',
            'danger'
        )
        return redirect(url_for('main.project_detail', project_id=shift.project_id))
    # Для несовершеннолетних (<18) требуется согласие родителей (FR-21)
    parent_consent = request.form.get('parent_consent') == 'on'
    if current_user.is_minor and not parent_consent:
        flash('Для участников младше 18 лет обязательно согласие родителя/законного представителя!', 'danger')
        return redirect(url_for('main.project_detail', project_id=shift.project_id))

    # Проверка свободных мест
    if shift.available_places <= 0:
        flash('К сожалению, на эту смену уже закончились места.', 'warning')
        return redirect(url_for('main.project_detail', project_id=shift.project_id))

    new_app = Application(
        shift_id=shift.id,
        volunteer_id=current_user.id,
        status='pending', # Организатор подтверждает заявку (FR-18)
        parent_consent_given=parent_consent,
        applied_at=datetime.utcnow()
    )
    db.session.add(new_app)
    db.session.commit()

    flash('Заявка на смену успешно отправлена! Организатор рассмотрит ее в ближайшее время.', 'success')
    return redirect(url_for('volunteer.dashboard'))

@volunteer_bp.route('/cancel/<int:app_id>', methods=['POST'])
@login_required
def cancel_application(app_id):
    application = Application.query.get_or_404(app_id)
    if application.volunteer_id != current_user.id:
        flash('Доступ запрещен.', 'danger')
        return redirect(url_for('volunteer.dashboard'))

    application.status = 'cancelled'
    db.session.commit()
    flash('Запись на смену успешно отменена.', 'info')
    return redirect(url_for('volunteer.dashboard'))

@volunteer_bp.route('/certificate')
@login_required
def certificate():
    completed_apps = Application.query.filter_by(
        volunteer_id=current_user.id,
        status='attended'
    ).all()
    
    return render_template('volunteer/certificate.html', 
                           user=current_user,
                           completed_apps=completed_apps,
                           total_hours=current_user.total_hours)
