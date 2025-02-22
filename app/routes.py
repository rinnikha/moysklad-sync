from flask import current_app, Blueprint, flash, jsonify, render_template, redirect, url_for, request
import json
from app import db
from app.models import CounterpartyMapping, SyncLog, SyncLogStatus, User
from app.forms import MappingForm

from flask_login import login_user, logout_user, login_required, current_user

from app.forms import LoginForm

from app.sync.core import retry_order_sync, sync_orders


from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.logs'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect(url_for('main.logs'))
        flash('Invalid username or password')
    return render_template('login.html', form=form)

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main_bp.route('/')
@login_required
def dashboard():
    stats = {
        'total_mappings': CounterpartyMapping.query.count(),
        'successful_syncs': SyncLog.query.filter_by(status=SyncLogStatus.COMPLETED).count(),
        'failed_syncs': SyncLog.query.filter_by(status=SyncLogStatus.FAILED).count()
    }
    return render_template('dashboard.html', stats=stats)

@main_bp.route('/mappings', methods=['GET', 'POST'])
@login_required
def mappings():
    form = MappingForm()
    if form.validate_on_submit():
        try:
            mapping = CounterpartyMapping(
                ms1_cp_name=form.ms1_cp_search.data,
                ms1_cp_id=json.loads(form.ms1_cp_meta.data)['href'].split('/')[-1],
                ms1_cp_meta=json.loads(form.ms1_cp_meta.data),
                ms2_org_name=form.ms2_org_search.data,
                ms2_org_meta=json.loads(form.ms2_org_meta.data),
                group_name=form.group_search.data,
                group_meta=json.loads(form.group_meta.data),
                owner_name=form.owner_search.data,
                owner_meta=json.loads(form.owner_meta.data),
                store_name=form.store_search.data,
                store_meta=json.loads(form.store_meta.data)
            )
            db.session.add(mapping)
            db.session.commit()
            flash('Mapping created successfully!', 'success')
            
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating mapping: {str(e)}', 'danger')

        return redirect(url_for('main.mappings'))
    else:
        if request.method == 'POST':
            print("Form errors:", form.errors)
            print("Request form:", request.form)
    return render_template('mappings.html', form=form, mappings=CounterpartyMapping.query.all(), editing=False)



# @main_bp.route('/mappings', methods=['GET', 'POST'])
# def mappings():
#     form = MappingForm()

#     if form.errors:
#         flash(f'Form errors: {form.errors}', 'danger')
    
#     if form.validate_on_submit():
#         try:
#             mapping = CounterpartyMapping(
#                 ms1_cp_name=json.loads(form.ms1_cp_meta.data)['name'],
#                 ms1_cp_id=json.loads(form.ms1_cp_meta.data)['id'],
#                 ms1_cp_meta=json.loads(form.ms1_cp_meta.data),
#                 ms2_org_name=json.load(form.ms2_org_meta.data)['name'],
#                 ms2_org_meta=json.loads(form.ms2_org_meta.data),
#                 group_name=json.loads(form.group_meta.data)['name'],
#                 group_meta=json.loads(form.group_meta.data),
#                 owner_name=json.loads(form.owner_meta.data)['name'],
#                 owner_meta=json.loads(form.owner_meta.data),
#                 store_name=json.loads(form.store_meta.data)['name'],
#                 store_meta=json.loads(form.store_meta.data)
#             )
#             db.session.add(mapping)
#             db.session.commit()
#             flash('Mapping created successfully!', 'success')
#         except Exception as e:
#             db.session.rollback()
#             flash(f'Error creating mapping: {str(e)}', 'danger')
            
#         return redirect(url_for('main.mappings'))
    
#     return render_template('mappings.html',
#                          form=form,
#                          mappings=CounterpartyMapping.query.all(),
#                          editing=False)

@main_bp.route('/mappings/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_mapping(id):
    mapping = CounterpartyMapping.query.get_or_404(id)
    form = MappingForm(obj=mapping)
    if form.validate_on_submit():
        # update mapping fields, commit, flash message, etc.
        db.session.commit()
        flash('Mapping updated successfully!', 'success')
        return redirect(url_for('main.mappings'))
    return render_template('mappings.html',
                           form=form,
                           mapping=mapping,  # Ensure mapping is passed here!
                           mappings=CounterpartyMapping.query.all(),
                           editing=True)



# @main_bp.route('/mappings/edit/<int:id>', methods=['GET', 'POST'])
# def edit_mapping(id):
#     mapping = CounterpartyMapping.query.get_or_404(id)
#     form = MappingForm(obj=mapping)
    
#     if form.validate_on_submit():
#         try:
#             form.populate_obj(mapping)
#             db.session.commit()
#             flash('Mapping updated successfully!', 'success')
#             return redirect(url_for('main.mappings'))
#         except Exception as e:
#             db.session.rollback()
#             flash(f'Error updating mapping: {str(e)}', 'danger')
    
#     # Pre-fill form fields
#     form.ms1_cp_meta.data = json.dumps(mapping.ms1_cp_meta)
#     # Add similar lines for other fields
    
#     return render_template('mappings.html', 
#                          form=form, 
#                          mappings=CounterpartyMapping.query.all(),
#                          editing=True)


@main_bp.route('/mappings/delete/<int:id>', methods=['POST'])
@login_required
def delete_mapping(id):
    mapping = CounterpartyMapping.query.get_or_404(id)
    try:
        db.session.delete(mapping)
        db.session.commit()
        flash('Mapping deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting mapping: {str(e)}', 'danger')
    return redirect(url_for('main.mappings'))


@main_bp.route('/logs')
@login_required
def logs():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status')
    counterparty_id = request.args.get('counterparty')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = SyncLog.query

    # Filters
    if status:
        query = query.filter(SyncLog.status == status)
    if counterparty_id:
        query = query.filter(SyncLog.counterparty_id == counterparty_id)
    if start_date:
        query = query.filter(SyncLog.sync_time >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(SyncLog.sync_time <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))

    logs = query.order_by(SyncLog.sync_time.desc()).paginate(page=page, per_page=20)

    scheduler = current_app.scheduler
    next_run = None
    try:
        job = scheduler.get_job('hourly_sync')
        if job:
            next_run = job.next_run_time.isoformat()
    except AttributeError:

        pass

    return render_template('logs.html',
                         logs=logs,
                         counterparties=CounterpartyMapping.query.all(),
                         next_sync=next_run)

@main_bp.route('/logs/<int:log_id>/retry', methods=['POST'])
@login_required
def retry_sync(log_id):
    log = SyncLog.query.get_or_404(log_id)
    
    try:
        # Your retry logic here
        # Example: 
        success = retry_order_sync(log_id)
        
        if success:
            flash('Sync retried successfully', 'success')
        else:
            flash('Sync retry failed', 'danger')
            
    except Exception as e:
        flash(f'Error retrying sync: {str(e)}', 'danger')
    
    return redirect(url_for('main.logs'))



@main_bp.route('/sync-now', methods=['POST'])
@login_required
def manual_sync():
    try:
        # Run sync
        sync_orders()
        
        return jsonify({
            'status': 'success',
            'message': 'Sync completed successfully'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Manual sync failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500



@main_bp.route('/search/ms1-counterparties')
def search_ms1_counterparties():
    search_term = request.args.get('q', '')
    ms1_client = current_app.ms1_client
    results = ms1_client.search_counterparties(search_term)
    return jsonify([{
        'name': item['name'],
        'meta': item['meta']
    } for item in results])

@main_bp.route('/search/ms2-organizations')
def search_ms2_organizations():
    search_term = request.args.get('q', '')
    ms2_client = current_app.ms2_client
    results = ms2_client.search_organizations(search_term)
    return jsonify([{
        'name': item['name'],
        'meta': item['meta']
    } for item in results])

@main_bp.route('/search/ms2-groups')
def search_ms2_groups():
    search_term = request.args.get('q', '')
    ms2_client = current_app.ms2_client
    results = ms2_client.search_groups(search_term)
    return jsonify([{
        'name': item['name'],
        'meta': item['meta']
    } for item in results])

@main_bp.route('/search/ms2-stores')
def search_ms2_stores():
    search_term = request.args.get('q', '')
    ms2_client = current_app.ms2_client
    results = ms2_client.search_stores(search_term)
    return jsonify([{
        'name': item['name'],
        'meta': item['meta']
    } for item in results])


@main_bp.route('/search/ms2-employees')
def search_ms2_employees():
    search_term = request.args.get('q', '')
    ms2_client = current_app.ms2_client
    results = ms2_client.search_employees(search_term)
    return jsonify([{
        'name': item['name'],
        'meta': item['meta']
    } for item in results])