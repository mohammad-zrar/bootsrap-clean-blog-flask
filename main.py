# ---- Flask ---- #
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_bootstrap import Bootstrap
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
# ---- For security ---- #
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
# ---- Others ---- #
from datetime import timedelta, date
from re import match
import os
import secrets

# ------------ Import SQLAlchemy ----------------- #
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship

# ---- Forms ---- #
from forms import RegisterForm, CreatePostForm, CommentForm, EditProfileForm, LoginForm


def generate_unique_secret_key():
    # Generate a random secret key using secrets module
    secret_key = secrets.token_hex(16)  # Generate a 32-character (16 bytes) secret key
    return secret_key


app = Flask(__name__)


app.config['SECRET_KEY'] = generate_unique_secret_key()
# app.permanent_session_lifetime = timedelta(hours=24)
bootstrap = Bootstrap(app)
ckeditor = CKEditor(app)
csrf = CSRFProtect(app)
app.config['WTF_CSRF_ENABLED'] = True
# ----- flask-login ------ #
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    session_cookie_name = 'myapp_session_' + session.get('session_id', '')
    app.config['SESSION_COOKIE_NAME'] = session_cookie_name
    return User.query.get(int(user_id))


gravatar = Gravatar(app,
                    size=24,
                    rating='g',
                    default='mp',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)
# ------------------------------ #


# ---- Building  Database and Tables ---- #
db = SQLAlchemy()
# configure the SQLite database, relative to the app instance folder
# app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///db.sqlite3"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
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
    email = db.Column(db.String(100))
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    bg_color = db.Column(db.String(7))
    bio = db.Column(db.String(250))
    blogs = db.relationship("BlogPost", back_populates="author")
    comments = db.relationship("Comment", back_populates="comment_author")

    favouring = db.relationship(
        'User', secondary=favorites,
        primaryjoin=(favorites.c.favorite_id == id),
        secondaryjoin=(favorites.c.favouring_id == id),
        backref=db.backref('favorites', lazy='dynamic'),
        lazy='dynamic'
    )


# Rest of the code remains the same


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="blogs")

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
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    else:
        session['session_id'] = generate_unique_secret_key()  # Generate a new session ID
        session_cookie_name = 'myapp_session_' + session.get('session_id', '')
        app.config['SESSION_COOKIE_NAME'] = session_cookie_name
        return redirect(url_for('user_blogs', username=current_user.username))


@app.route("/<string:username>/profile", methods=["POST", "GET"])
@login_required
def profile(username):
    if current_user.username != username:
        return redirect(url_for('home'))
    else:
        user = User.query.filter_by(username=username).first()
        edit_form = EditProfileForm(
            email=user.email,
            username=user.username,
            bg_color=user.bg_color,
            bio=user.bio,
        )
        if edit_form.validate_on_submit():
            new_email = edit_form.email.data
            new_username = edit_form.username.data.lower()
            new_bg_color = edit_form.bg_color.data
            new_bio = edit_form.bio.data
            check_user = User.query.filter_by(username=new_username).first()

            if check_user and check_user.username != username:
                flash("This username name already exists try another one!")
                return redirect(url_for('profile', username=current_user.username, form=edit_form))
            elif not match(r'^[a-z][a-z0-9-_]*$', new_username):
                flash("The username must be start with letters and only contains letter or - or _ or [0-9]")
                return redirect(url_for('profile', username=current_user.username, form=edit_form))
            else:
                user.email = new_email
                user.username = new_username
                user.bg_color = new_bg_color
                user.bio = new_bio
                db.session.commit()
                return redirect(url_for('user_blogs', username=current_user.username))
        return render_template('profile.html', username=current_user.username, user=current_user, form=edit_form)


@app.route("/<string:username>/blogs")
def user_blogs(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        return "<h1>There is no user with that username</h1>"

    limited_results = db.session.query(BlogPost).filter(BlogPost.author_id == user.id).order_by(BlogPost.date.desc()).limit(4).all()
    return render_template("index.html", option="posts", user=user, blogs=limited_results)


@app.route("/<string:username>/favorites")
@login_required
def favorites(username):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return render_template("index.html", option="fav", user=current_user)


@app.route("/<string:username>/favorite/<string:username_to_favorite>")
@login_required
def favorite(username, username_to_favorite):
    user_to_favorite = User.query.filter_by(username=username_to_favorite).first()

    if user_to_favorite is not None:
        if user_to_favorite not in current_user.favouring:
            current_user.favouring.append(user_to_favorite)
            db.session.commit()
        else:
            current_user.favouring.remove(user_to_favorite)
            db.session.commit()

    return redirect(url_for('user_blogs', username=username_to_favorite))


@app.route('/<string:username>/all-blogs')
def all_blogs(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        return "There is no user with that username"
    blogs = db.session.query(BlogPost).filter(BlogPost.author_id == user.id).order_by(BlogPost.date.desc()).all()
    return render_template("all-blogs.html", all_blogs=blogs, user=user)


@app.route('/<string:username>/blog/<int:blog_id>', methods=["GET", "POST"])
def blog(username, blog_id):
    global gravatar
    user = User.query.filter_by(username=username).first()
    if user is None:
        return "No user with that name"
    blog = db.session.query(BlogPost).filter(BlogPost.author_id == user.id, BlogPost.id == blog_id).first()
    if blog is None:
        return "No post with that id"
    form = CommentForm()
    # print(requested_post.comments[1].text)
    # print(requested_post.comments[1].comment_author.name)
    if form.validate_on_submit() and request.method == "POST":
        print(blog.id)
        new_comment = Comment(
            comment_author=current_user,
            parent_post=blog,
            author_id=current_user.id,
            post_id=blog.id,
            text=form.comment_text.data
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for("blog", username=username, blog_id=blog_id))
    return render_template("blog.html", blog=blog, user=user, form=form)


@app.route("/<string:username>/blog-post", methods=["POST", "GET"])
@login_required
def blog_post(username):
    if current_user.username == username:
        form = CreatePostForm()
        if form.validate_on_submit():
            print("Validate OK")
            new_post = BlogPost(
                author_id=current_user.id,
                title=form.title.data,
                subtitle=form.subtitle.data,
                body=form.body.data,
                img_url="",
                date=date.today().strftime("%B %d, %Y")
            )
            db.session.add(new_post)
            db.session.commit()
            print("Session committed")
            return redirect(url_for("home"))
        return render_template("blog-post.html", form=form, user=current_user)
    else:
        return redirect(url_for('user_blogs', username=username))


@app.route("/<string:username>/edit-blog/<int:blog_id>", methods=["POST", "GET"])
def edit_blog(blog_id, username):
    user = User.query.filter_by(username=username).first()
    blog = db.session.query(BlogPost).filter(BlogPost.author_id == user.id, BlogPost.id == blog_id).first()
    if user is None or blog is None or (username != current_user.username):
        return f"<h3>Not allowed</h3>"
    else:
        edit_form = CreatePostForm(
            title=blog.title,
            subtitle=blog.subtitle,
            author=blog.author,
            body=blog.body
        )
        if edit_form.validate_on_submit():
            blog.title = edit_form.title.data
            blog.subtitle = edit_form.subtitle.data
            blog.body = edit_form.body.data
            db.session.commit()
            return redirect(url_for("blog", blog_id=blog.id, username=username))
        return render_template("edit-blog.html", form=edit_form, blog_id=blog_id, username=username)


@app.route("/<string:username>/delete/<int:blog_id>")
def delete_blog(username, blog_id):
    user = User.query.filter_by(username=username).first()
    blog_to_delete = db.session.query(BlogPost).filter(BlogPost.author_id == user.id, BlogPost.id == blog_id).first()
    if user is None or blog is None or (username != current_user.username):
        return f"<h3>Not allowed</h3>"
    else:
        db.session.delete(blog_to_delete)
        db.session.commit()
    return redirect(url_for('home'))


@app.route("/search", methods=["POST", "GET"])
def search():
    if request.method == "GET":
        return redirect(url_for("user_blogs", username=request.args.get('search')))


# Security Section
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('user_blogs', username=current_user.username))
    else:
        form = LoginForm()
        if form.validate_on_submit():
            username = form.username.data
            password = form.password.data

            # Find user by username entered.
            user = User.query.filter_by(username=username).first()
            if not user:
                flash("That username does not exist, please try again.")
                return redirect(url_for('login'))
            elif not check_password_hash(user.password, password):
                flash('Incorrect password, please try again.')
                return redirect(url_for('login'))
            else:
                login_user(user)
                if current_user.is_authenticated:
                    print(f"{current_user.username} logged in")
                else:
                    print("User failed to log in")
                return redirect(url_for('home'))

        return render_template('login.html', form=form)


@app.route("/register", methods=["POST", "GET"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('user_blogs', username=current_user.username))
    else:
        register_form = RegisterForm()
        if register_form.validate_on_submit():
            email = register_form.email.data
            username = register_form.username.data.lower()
            password = register_form.password.data
            bg_color = register_form.bg_color.data
            bio = register_form.bio.data
            user = User.query.filter_by(username=username).first()
            if user:
                flash("You've already signed up with that email, log in instead!")
                return redirect("login")
            elif not match(r'^[a-z][a-z0-9-_]*$', username):
                flash("The username must be start with letters and only contains letter or - or _ or [0-9]")
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
                    bg_color=bg_color,
                    bio=bio
                )
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
                if current_user.is_authenticated:
                    print(f"{current_user.username} logged in")
                else:
                    print("User Failed to login")
                return redirect(url_for('home'))
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
