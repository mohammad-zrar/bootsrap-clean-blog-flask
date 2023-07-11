from flask_wtf import FlaskForm
from wtforms import EmailField, SubmitField, StringField, PasswordField, RadioField, SelectField
from wtforms.validators import DataRequired, Email, Length
from wtforms.widgets import ListWidget, CheckboxInput


class RegisterForm(FlaskForm):
    email = EmailField("Email: ", validators=[DataRequired("Required"), Email("No Valid")],
                       render_kw={"style": "margin-bottom: 10px"})
    username = StringField("Username: ", validators=[DataRequired("Required")],
                           render_kw={"style": "margin-bottom: 10px"})
    password = PasswordField("Password: ", validators=[DataRequired("Required"), Length(min=8)],
                             render_kw={"style": "margin-bottom: 10px"})
    bg_color = SelectField('Choice a background color',
                           choices=[('000000', 'Black'), ('37306B', 'Navy'),
                                    ('862B0D', 'Maroon'), ('454545', 'Dark Gray')],
                           render_kw={"style": "margin-bottom: 10px"}
                           )
    submit = SubmitField("Submit", render_kw={"style": "margin-top: 18px;"})
