from flask import Flask, render_template, request
from post import Post
import requests

posts = requests.get("https://api.npoint.io/3fd2ae95189b864f5f49").json()
post_objects = []
for post in posts:
    post_obj = Post(post["id"], post["title"], post["subtitle"], post["supervisor"], post["year"])
    post_objects.append(post_obj)

app = Flask(__name__)


@app.route('/')
def home():
    return render_template("index.html", all_posts=post_objects)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/form-entry', methods=['POST', 'GET'])
def receive_data():
    if request.method == "POST":
        data = request.form
        print(data["name"])
        print(data["email"])
        print(data["phone"])
        print(data["message"])
        return render_template("contact.html", submited=True)
    return render_template("contact.html", submited=False)


@app.route("/post/<int:index>")
def show_post(index):
    requested_post = None
    for blog_post in post_objects:
        if blog_post.id == index:
            requested_post = blog_post
    return render_template("post.html", post=requested_post)


if __name__ == "__main__":
    app.run(debug=True)