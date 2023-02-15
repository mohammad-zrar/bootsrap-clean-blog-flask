from urllib import request
from functools import wraps
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
# ----- Import Flask ----------
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask import abort
from flask_gravatar import Gravatar
# ----------------------------- #
# ------------ Import SQLAlchemy ----------------- #
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
# -----------------------
import os
# from dotenv import load_dotenv, find_dotenv
#
# load_dotenv(verbose=True)


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
# #CONNECT TO DB
print(os.environ.get("DATABASE_URL"))
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://clean_blog_user:OiSKVzgykBsTcTNAypoFqqqRC3Mzy2sI@dpg-cfme4gda499591e80ufg-a/clean_blog"
# For Internal
# postgresql://clean_blog_user:OiSKVzgykBsTcTNAypoFqqqRC3Mzy2sI@dpg-cfme4gda499591e80ufg-a/clean_blog
# For External
# postgresql://clean_blog_user:OiSKVzgykBsTcTNAypoFqqqRC3Mzy2sI@dpg-cfme4gda499591e80ufg-a.oregon-postgres.render.com/clean_blog
# username:password@location-of-the-database/name-of-database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ----- flask-login ------ #
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ------------------------------ #


# -------------- Gravatar ------------------ #
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='mp',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)
# ------------------------- PPP ------------------ #

# #CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")


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


# -------------- ------------ ------------------------ #
# Create admin-only decorator
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If id is not 1 then return abort with 403 error
        if current_user.id != 1:
            return abort(403)
        # Otherwise continue with the route function
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["POST", "GET"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            flash("You've already signed up with that email, log in instead!")
            return redirect("login")
        else:
            hash_and_salted_password = generate_password_hash(
                form.password.data,
                method='pbkdf2:sha256',
                salt_length=8
            )
            new_user = User(
                email=form.email.data,
                name=form.name.data,
                password=hash_and_salted_password,
            )
            db.session.add(new_user)
            db.session.commit()

            # This line will authenticate the user with Flask-Login
            login_user(new_user)
            return redirect(url_for("get_all_posts"))

    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = request.form.get('email')
        password = request.form.get('password')

        # Find user by email entered.
        user = User.query.filter_by(email=email).first()
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
            print(current_user.name)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    global gravatar
    requested_post = BlogPost.query.get(post_id)
    form = CommentForm()
    # print(requested_post.comments[1].text)
    # print(requested_post.comments[1].comment_author.name)
    if form.validate_on_submit():
        print(requested_post.id)
        new_comment = Comment(
            comment_author=current_user,
            parent_post=requested_post,
            author_id=current_user.id,
            post_id=requested_post.id,
            text=form.comment_text.data
        )
        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html", post=requested_post, form=form)


@app.route("/new-post", methods=["POST", "GET"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        print("Validate OK")
        new_post = BlogPost(
            author_id=current_user.id,
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            date=date.today().strftime("%B %d, %Y")
        )
        print("Object OK")
        db.session.add(new_post)
        db.session.commit()
        print("Session committed")
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["POST", "GET"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
