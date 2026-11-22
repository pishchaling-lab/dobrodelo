from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='volunteer')  # volunteer, coordinator, admin
    phone = db.Column(db.String(30), nullable=True)
    city = db.Column(db.String(60), nullable=True, default='Москва')
    birth_date = db.Column(db.Date, nullable=True)
    skills = db.Column(db.String(255), nullable=True)
    interests = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    organizations = db.relationship('Organization', backref='coordinator', lazy=True)
    applications = db.relationship('Application', backref='volunteer', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def age(self):
        if not self.birth_date:
            return None

        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) <
            (self.birth_date.month, self.birth_date.day)
        )

    @property
    def is_minor(self):
        return self.age is not None and self.age < 18

    @property
    def total_hours(self):
        # Суммируем часы за подтвержденную явку
        return sum(app.hours_awarded or 0 for app in self.applications if app.status == 'attended')


class Organization(db.Model):
    __tablename__ = 'organizations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(60), nullable=False, default='Москва')
    contact_email = db.Column(db.String(120), nullable=True)
    contact_phone = db.Column(db.String(30), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)  # Подтверждена ли модератором (FR-03, FR-37)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    projects = db.relationship('Project', backref='organization', lazy=True, cascade="all, delete-orphan")


class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(60), nullable=False)  # Животные, Экология, Социальное, Дети, Спорт
    city = db.Column(db.String(60), nullable=False, default='Москва')
    address = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(30), default='open')  # draft, open, closed, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    shifts = db.relationship('Shift', backref='project', lazy=True, cascade="all, delete-orphan")


class Shift(db.Model):
    __tablename__ = 'shifts'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(10), nullable=False, default='10:00')
    end_time = db.Column(db.String(10), nullable=False, default='14:00')
    location = db.Column(db.String(255), nullable=True)
    max_volunteers = db.Column(db.Integer, nullable=False, default=10)
    hours = db.Column(db.Float, nullable=False, default=4.0)  # Количество начисляемых волонтерских часов
    min_age = db.Column(db.Integer, default=14)  # Минимальный возраст
    parent_consent_required = db.Column(db.Boolean, default=True)  # Согласие родителей для несовершеннолетних (FR-21)

    # Relationships
    applications = db.relationship('Application', backref='shift', lazy=True, cascade="all, delete-orphan")

    @property
    def approved_count(self):
        return sum(1 for a in self.applications if a.status in ['approved', 'attended'])

    @property
    def available_places(self):
        return max(0, self.max_volunteers - self.approved_count)


class Application(db.Model):
    __tablename__ = 'applications'

    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(db.Integer, db.ForeignKey('shifts.id'), nullable=False)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(30), default='pending')  # pending, approved, rejected, attended, no_show, cancelled
    parent_consent_given = db.Column(db.Boolean, default=False)  # Подтверждено родителем (FR-21)
    hours_awarded = db.Column(db.Float, default=0.0)  # Автоматический учет часов (FR-28)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.String(255), nullable=True)


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False, default=5)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class VolunteerProfile(db.Model):
    __tablename__ = 'volunteer_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    city = db.Column(db.String(60), nullable=True)
    birth_date = db.Column(db.Date, nullable=True)
    skills = db.Column(db.Text, nullable=True)
    interests = db.Column(db.Text, nullable=True)
    availability = db.Column(db.String(255), nullable=True)
    no_show_count = db.Column(db.Integer, nullable=False, default=0)

    user = db.relationship('User', backref=db.backref('volunteer_profile', uselist=False))
    hours_records = db.relationship(
        'HoursRecord',
        backref='volunteer_profile',
        lazy=True,
        cascade='all, delete-orphan'
    )

    @property
    def age(self):
        if self.birth_date is None:
            return None

        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) <
            (self.birth_date.month, self.birth_date.day)
        )

    @property
    def total_hours(self):
        return sum(float(record.hours) for record in self.hours_records)


class ParentalConsent(db.Model):
    __tablename__ = 'parental_consents'

    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(
        db.Integer,
        db.ForeignKey('volunteer_profiles.id'),
        unique=True,
        nullable=False
    )
    parent_contact = db.Column(db.String(120), nullable=False)
    method = db.Column(db.String(30), nullable=False)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    profile = db.relationship(
        'VolunteerProfile',
        backref=db.backref('parental_consent', uselist=False)
    )


class TeamMember(db.Model):
    __tablename__ = 'team_members'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('organizations.id'),
        nullable=False
    )
    role = db.Column(db.String(50), nullable=False)
    permissions = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'organization_id'),
    )

    user = db.relationship('User', backref='team_memberships')
    organization = db.relationship('Organization', backref='team_members')


class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer,
        db.ForeignKey('organizations.id'),
        nullable=False
    )
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    format = db.Column(db.String(20), nullable=False, default='pdf')
    file_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    organization = db.relationship('Organization', backref='reports')


class Complaint(db.Model):
    __tablename__ = 'complaints'

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    target = db.Column(db.String(255), nullable=False)
    text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default='new')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)

    author = db.relationship('User', backref='complaints')

    def resolve(self):
        self.status = 'resolved'
        self.resolved_at = datetime.utcnow()


class ShiftRole(db.Model):
    __tablename__ = 'shift_roles'

    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(db.Integer, db.ForeignKey('shifts.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    slots = db.Column(db.Integer, nullable=False, default=1)
    required_skills = db.Column(db.Text, nullable=True)


class Attendance(db.Model):
    __tablename__ = 'attendances'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer,
        db.ForeignKey('applications.id'),
        unique=True,
        nullable=False
    )
    status = db.Column(db.String(30), nullable=False, default='pending')
    method = db.Column(db.String(30), nullable=True)
    marked_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    correction_reason = db.Column(db.Text, nullable=True)

    application = db.relationship(
        'Application',
        backref=db.backref('attendance', uselist=False)
    )
    marked_by = db.relationship('User', backref='marked_attendances')

    def confirm(self):
        self.status = 'confirmed'
        self.confirmed_at = datetime.utcnow()

    def correct(self, reason):
        self.correction_reason = reason


class HoursRecord(db.Model):
    __tablename__ = 'hours_records'

    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(
        db.Integer,
        db.ForeignKey('volunteer_profiles.id'),
        nullable=False
    )
    attendance_id = db.Column(
        db.Integer,
        db.ForeignKey('attendances.id'),
        unique=True,
        nullable=True
    )
    hours = db.Column(db.Numeric(8, 2), nullable=False)
    accrued_at = db.Column(db.DateTime, default=datetime.utcnow)

    attendance = db.relationship('Attendance', backref='hours_record')


class Certificate(db.Model):
    __tablename__ = 'certificates'

    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(
        db.Integer,
        db.ForeignKey('volunteer_profiles.id'),
        nullable=False
    )
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    number = db.Column(db.String(100), unique=True, nullable=False)
    file_url = db.Column(db.String(500), nullable=True)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    profile = db.relationship('VolunteerProfile', backref='certificates')
    project = db.relationship('Project', backref='certificates')


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    channel = db.Column(db.String(30), nullable=False, default='in_app')
    scheduled_at = db.Column(db.DateTime, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(30), nullable=False, default='pending')

    recipient = db.relationship('User', backref='notifications')


class AuditLogEntry(db.Model):
    __tablename__ = 'audit_log_entries'

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    target = db.Column(db.String(255), nullable=False)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User', backref='audit_entries')
