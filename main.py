# ---- Flask ---- #
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user

# ---- For security ---- #
from werkzeug.security import generate_password_hash, check_password_hash

# ---- Others ---- #
from datetime import timedelta

# ------------ Import SQLAlchemy ----------------- #
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship

# ---- Forms ---- #
from forms import RegisterForm


app = Flask(__name__)
app.secret_key = "clean-blog1234"
app.permanent_session_lifetime = timedelta(hours=24)
bootstrap = Bootstrap(app)


# ----- flask-login ------ #
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------------------ #


# ---- Building  Database and Tables ---- #
db = SQLAlchemy()
# configure the SQLite database, relative to the app instance folder
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///db.sqlite3"
# initialize the app with the extension
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Intermediate table to store follower-following relationships
favorites = db.Table(
    'favorites',
    db.Column('favorite_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('favouring_id', db.Integer, db.ForeignKey('users.id'))
)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    bg_color = db.Column(db.String(7))
    bio = db.Column(db.String(250))
    posts = db.relationship("BlogPost", back_populates="author")
    comments = db.relationship("Comment", back_populates="comment_author")

    following = db.relationship(
        'User', secondary=favorites,
        primaryjoin=(favorites.c.favorite_id == id),
        secondaryjoin=(favorites.c.favouring_id == id),
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic'
    )

# Rest of the code remains the same


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="posts")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    # ---- User relationship ---- #
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")

    # ***************  Child Relationship  ************* #
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
    text = db.Column(db.Text, nullable=False)


app.app_context().push()
db.create_all()
# ---- ---- ---- ---- #


@app.route("/")
def home():
    # if "user" not in session:
    #     return redirect(url_for("login"))
    return render_template("index.html", option="home")


@app.route("/favorites")
def favorites():
    return render_template("index.html", option="fav")


# Security Section
@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        # Find user by email entered.
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
            # Password incorrect
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
            # Email exists and password correct
        else:
            login_user(user)

            print("Logged in")
            print(current_user.username)
            print(current_user.is_authenticated)
            return redirect(url_for('home'))
    return render_template('login.html')


@app.route("/register", methods=["POST", "GET"])
def register():
    register_form = RegisterForm()
    if register_form.validate_on_submit():
        email = register_form.email.data
        username = register_form.username.data.lower()
        password = register_form.password.data
        bg_color = register_form.bg_color.data
        user = User.query.filter_by(username=username).first()
        if user:
            flash("You've already signed up with that email, log in instead!")
            return redirect("login")
        else:
            hash_and_salted_password = generate_password_hash(
                password,
                method='pbkdf2:sha256',
                salt_length=8
            )
            new_user = User(
                email=email,
                username=username,
                password=hash_and_salted_password,
                bg_color=bg_color
            )
            db.session.add(new_user)
            db.session.commit()
    return render_template("register.html", form=register_form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route("/reset_password")
def reset_password():
    return "Reset password page"


if __name__ == "__main__":
    app.run(debug=True)


