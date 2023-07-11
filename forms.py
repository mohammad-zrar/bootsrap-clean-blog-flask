from flask_wtf import FlaskForm
from wtforms import EmailField, SubmitField, StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Email, Length


class RegisterForm(FlaskForm):
    email = EmailField("Email: ", validators=[DataRequired(), Email()])
    username = StringField("Username: ", validators=[DataRequired()])
    password = PasswordField("Password: ", validators=[DataRequired(), Length(min=8)])
    bg_color = SelectField('Choice a background color',
                           choices=[('000000', 'Black'), ('37306B', 'Navy'),
                                    ('862B0D', 'Maroon'), ('454545', 'Dark Gray')]
                           )
    submit = SubmitField("Submit", render_kw={"style": "margin-top: 15px;"})
