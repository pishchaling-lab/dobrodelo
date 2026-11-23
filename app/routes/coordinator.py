from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from datetime import datetime
from app.models import db, Project, Shift, Application, Organization

coordinator_bp = Blueprint('coordinator', __name__)

def check_coordinator():
    if current_user.role not in ['coordinator', 'admin']:
      abort(403)
# Проверка прав на проект (админ или владелец организации)
def check_project_owner(project):  
    if current_user.role != 'admin' and project.organization.owner_id != current_user.id:
        flash('У вас нет прав для управления этим проектом.', 'danger')
        return False
    return True

@coordinator_bp.route('/dashboard')
@login_required
def dashboard():
    check_coordinator()
    org = Organization.query.filter_by(owner_id=current_user.id).first()
    if not org and current_user.role == 'admin':
        org = Organization.query.first()

    projects = Project.query.filter_by(organization_id=org.id).all() if org else []

    # Сбор общей статистики
    total_shifts = sum(len(p.shifts) for p in projects)
    all_shift_ids = [s.id for p in projects for s in p.shifts]
    total_applications = Application.query.filter(Application.shift_id.in_(all_shift_ids)).count() if all_shift_ids else 0
    pending_applications = Application.query.filter(
        Application.shift_id.in_(all_shift_ids),
        Application.status == 'pending'
    ).count() if all_shift_ids else 0

    return render_template('coordinator/dashboard.html',
                           org=org,
                           projects=projects,
                           total_shifts=total_shifts,
                           total_applications=total_applications,
                           pending_applications=pending_applications)

@coordinator_bp.route('/project/new', methods=['GET', 'POST'])
@login_required
def create_project():
    check_coordinator()
    org = Organization.query.filter_by(owner_id=current_user.id).first()
    if not org:
        flash('Сначала необходимо зарегистрировать профиль организации.', 'warning')
        return redirect(url_for('coordinator.dashboard'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        # Проверяем, что название проекта заполнено
        if not title:
            flash('Название проекта не может быть пустым.', 'danger')
            return redirect(url_for('coordinator.create_project'))
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'Экология')
        city = request.form.get('city', org.city).strip()
        address = request.form.get('address', '').strip()

        project = Project(
            organization_id=org.id,
            title=title,
            description=description,
            category=category,
            city=city,
            address=address,
            status='open'
        )
        db.session.add(project)
        db.session.commit()
        flash(f'Проект «{title}» успешно создан! Теперь добавьте смены.', 'success')
        return redirect(url_for('coordinator.create_shift', project_id=project.id))

    categories = ['Животные', 'Экология', 'Социальное', 'Дети', 'Культура', 'Спорт']
    return render_template('coordinator/project_create.html', org=org, categories=categories)

@coordinator_bp.route('/project/<int:project_id>/shift/new', methods=['GET', 'POST'])
@login_required
def create_shift(project_id):
    check_coordinator()
    project = Project.query.get_or_404(project_id)
    if not check_project_owner(project):
        return redirect(url_for('coordinator.dashboard'))

    if request.method == 'POST':
       date_str = request.form.get('date', '')
        start_time = request.form.get('start_time', '10:00')
        end_time = request.form.get('end_time', '14:00')
        location = request.form.get('location', project.address)

        # Проверяем корректность даты и числовых полей
        try:
            max_volunteers = int(request.form.get('max_volunteers', 10))
            hours = float(request.form.get('hours', 4.0))
            min_age = int(request.form.get('min_age', 14))
            shift_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Проверьте корректность даты и числовых полей (участники, часы, возраст).', 'danger')
            return redirect(url_for('coordinator.create_shift', project_id=project.id))

        shift = Shift(
            project_id=project.id,
            date=shift_date,
            start_time=start_time,
            end_time=end_time,
            location=location,
            max_volunteers=max_volunteers,
            hours=hours,
            min_age=min_age
        )
        db.session.add(shift)
        db.session.commit()
        flash('Смена успешно добавлена!', 'success')
        return redirect(url_for('coordinator.dashboard'))

    return render_template('coordinator/shift_create.html', project=project)

@coordinator_bp.route('/shift/<int:shift_id>/applications')
@login_required
def shift_applications(shift_id):
    check_coordinator()
    shift = Shift.query.get_or_404(shift_id)
    if not check_project_owner(shift.project):
        return redirect(url_for('coordinator.dashboard'))
    applications = Application.query.filter_by(shift_id=shift.id).all()
    return render_template('coordinator/shift_applications.html', shift=shift, applications=applications)

@coordinator_bp.route('/application/<int:app_id>/status/<string:new_status>', methods=['POST'])
@login_required
def update_application_status(app_id, new_status):
    check_coordinator()
    application = Application.query.get_or_404(app_id)
    if not check_project_owner(application.shift.project):
        return redirect(url_for('coordinator.dashboard'))
    if new_status in ['approved', 'rejected', 'cancelled']:
        # При одобрении проверяем, не достигнут ли лимит мест на смене
        if new_status == 'approved' and application.status != 'approved':
            approved_count = Application.query.filter(
                Application.shift_id == application.shift_id,
                Application.status.in_(['approved', 'attended'])
            ).count()
            if approved_count >= application.shift.max_volunteers:
                flash('Лимит волонтёров на эту смену уже достигнут.', 'warning')
                return redirect(url_for('coordinator.shift_applications', shift_id=application.shift_id))
        application.status = new_status
        db.session.commit()
        flash(f'Статус заявки изменен на: {new_status}.', 'info')
    return redirect(url_for('coordinator.shift_applications', shift_id=application.shift_id))

@coordinator_bp.route('/shift/<int:shift_id>/attendance', methods=['GET', 'POST'])
@login_required
def shift_attendance(shift_id):
    """
    Отметка явки (FR-20) и автоматический учет волонтерских часов (FR-28).
    """
    check_coordinator()
    shift = Shift.query.get_or_404(shift_id)
   if not check_project_owner(shift.project):
        return redirect(url_for('coordinator.dashboard'))

    # Показываем только одобренные заявки и заявки с уже отмеченной явкой
    applications = Application.query.filter(
        Application.shift_id == shift.id,
        Application.status.in_(['approved', 'attended', 'no_show'])
    ).all()

    if request.method == 'POST':
        for app in applications:
            attendance_status = request.form.get(f'attendance_{app.id}')
            if attendance_status == 'attended':
                app.status = 'attended'
                app.hours_awarded = shift.hours  # Начисление подтвержденных часов
            elif attendance_status == 'no_show':
                app.status = 'no_show'
                app.hours_awarded = 0.0

        db.session.commit()
        flash('Явка успешно отмечена! Часы автоматически зачислены в профили волонтеров.', 'success')
        return redirect(url_for('coordinator.dashboard'))

    return render_template('coordinator/shift_attendance.html', shift=shift, applications=applications)

@coordinator_bp.route('/reports')
@login_required
def reports():
    """
    Отчет для грантодателей и партнеров за 1 клик (FR-35, BG-4).
    """
    check_coordinator()
    org = Organization.query.filter_by(owner_id=current_user.id).first()
    if not org and current_user.role == 'admin':
        org = Organization.query.first()

    projects = Project.query.filter_by(organization_id=org.id).all() if org else []
    project_ids = [p.id for p in projects]
    shifts = Shift.query.filter(Shift.project_id.in_(project_ids)).all() if project_ids else []
    shift_ids = [s.id for s in shifts]

    all_apps = Application.query.filter(Application.shift_id.in_(shift_ids)).all() if shift_ids else []
    attended_apps = [a for a in all_apps if a.status == 'attended']
    total_hours_granted = sum(a.hours_awarded or 0 for a in attended_apps)
    unique_volunteers = len(set(a.volunteer_id for a in attended_apps))

    turnout_rate = (len(attended_apps) / len(all_apps) * 100) if all_apps else 0

    report_data = {
        'org_name': org.name if org else 'Все организации',
        'projects_count': len(projects),
        'shifts_count': len(shifts),
        'total_applications': len(all_apps),
        'attended_count': len(attended_apps),
        'total_hours': total_hours_granted,
        'unique_volunteers': unique_volunteers,
        'turnout_rate': round(turnout_rate, 1)
    }

    return render_template('coordinator/reports.html', report=report_data, projects=projects)
