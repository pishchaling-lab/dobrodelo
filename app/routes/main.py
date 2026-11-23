from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import current_user
from app.models import Project, Shift, Organization

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Показываем только проекты подтвержденных организаций и со статусом open
    featured_projects = Project.query.join(Organization).filter(
        Organization.is_verified == True,
        Project.status == 'open'
    ).order_by(Project.created_at.desc()).limit(6).all()

    # Статистика для лендинга
    stats = {
        'projects_count': Project.query.join(Organization).filter(Organization.is_verified == True).count(),
        'orgs_count': Organization.query.filter_by(is_verified=True).count(),
        'shifts_count': Shift.query.join(Project).join(Organization).filter(Organization.is_verified == True).count()
    }
    return render_template('index.html', projects=featured_projects, stats=stats)

@main_bp.route('/catalog')
def catalog():
    query = Project.query.join(Organization).filter(
        Organization.is_verified == True,
        Project.status == 'open'
    )

    category = request.args.get('category')
    city = request.args.get('city')
    search = request.args.get('q')

    if category:
        query = query.filter(Project.category == category)
    if city:
        query = query.filter(Project.city.ilike(f'%{city}%'))
    if search:
        query = query.filter(Project.title.ilike(f'%{search}%') | Project.description.ilike(f'%{search}%'))

    projects = query.order_by(Project.created_at.desc()).all()

    categories = ['Животные', 'Экология', 'Социальное', 'Дети', 'Культура', 'Спорт']
    return render_template('catalog.html', projects=projects, categories=categories,
                           selected_category=category, selected_city=city, search=search)

@main_bp.route('/project/<int:project_id>')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    # Проекты неверифицированных организаций видны только админу и владельцу
    if not project.organization.is_verified:
        is_admin = current_user.is_authenticated and current_user.role == 'admin'
        is_owner = current_user.is_authenticated and project.organization.owner_id == current_user.id
        if not (is_admin or is_owner):
            flash('Проект пока недоступен для просмотра, так как организация не верифицирована.', 'warning')
            return redirect(url_for('main.catalog'))
    return render_template('project_detail.html', project=project)
