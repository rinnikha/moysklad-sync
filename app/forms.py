from flask_wtf import FlaskForm
from wtforms import StringField, HiddenField, SubmitField, PasswordField, BooleanField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')

class MappingForm(FlaskForm):
    # Visible search inputs with unique IDs (used for display and JS)
    ms1_cp_search = StringField(
        'Поиск контрагента МС1', 
        render_kw={"id": "ms1_cp_search"}
    )
    
    
    # Hidden field with unique ID but same name for Flask form data
    ms1_cp_meta = HiddenField(
        'MS1 Counterparty Meta', 
        validators=[DataRequired()], 
        render_kw={"id": "ms1_cp_meta_hidden"}
    )
    
    ms2_org_search = StringField(
        'Поиск Организации МС2', 
        render_kw={"id": "ms2_org_search"}
    )

    ms2_org_meta = HiddenField(
        'MS2 Organization Meta', 
        validators=[DataRequired()], 
        render_kw={"id": "ms2_org_meta_hidden"}
    )
    
    group_search = StringField(
        'Поиск Отдела МС2', 
        render_kw={"id": "group_search"}
    )

    group_meta = HiddenField(
        'Group Meta', 
        validators=[DataRequired()], 
        render_kw={"id": "group_meta_hidden"}
    )
    
    owner_search = StringField(
        'Поиск Сотрудника МС2', 
        render_kw={"id": "owner_search"}
    )

    owner_meta = HiddenField(
        'Owner Meta', 
        validators=[DataRequired()], 
        render_kw={"id": "owner_meta_hidden"}
    )
    
    store_search = StringField(
        'Поиск Склада', 
        render_kw={"id": "store_search"}
    )

    store_meta = HiddenField(
        'Store Meta', 
        validators=[DataRequired()], 
        render_kw={"id": "store_meta_hidden"}
    )
    
    submit = SubmitField('Сохранить')