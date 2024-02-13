from functools import wraps  # decaroter yapmak için lazım
from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
"""Form oluşturur"""
from passlib.hash import sha256_crypt
"""Şifrelemy yarar metni  """
app = Flask(__name__)
app.secret_key = "blog"
# Mygsg bağlamak içi oluşturulan uygulamanın bilgileri config metodu ile girilmeli
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "blog"
# verilerin ne yapıda tutulcağı belirlenir sozluk yapısı ile tutulcak
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)  # Mysql bağlantı kurar

# kullanıcı giriş kontrol decoroteri


def login_required(fonksiyon):
    @wraps(fonksiyon)
    def decore_fonksiyon(*args, **kwargs):
        if "log_in" in session:  # sessionun içinde login varmı kontrol eder
            return fonksiyon(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için giriş yapınız...", "warning")
            return redirect(url_for("login"))
    return decore_fonksiyon


@app.route("/")
def anasayfa():
    return render_template("anasayfa.html")


@app.route("/Hakkimizda")
def hakkimizda():
    return render_template("hakkimizda.html")


# ?Kullanici Kayıt Formu
# form olusturmak için flask ile WTF form kullanılıcak
#! 1 adım kayıt olması için class olusturulur için Form objesi girilmeli


class KayitFormu(Form):
    name = StringField("Ad Soyad", validators=[validators.Length(min=4, max=25), validators.DataRequired(
        "Burayi Mutlaka doldurmalısınız")])  # ilk alan label alanı label ="Ad..." da denebilir
    # ?valitors lar sınırlama getirmeye yarar
    username = StringField("Kullanıcı Adı", validators=[validators.Length(
        min=4, max=25), validators.DataRequired("Burayi Mutlaka doldurmalısınız")])
    # emailmi gerçekte kontrol etmeye yarar
    email = StringField("Email ")
    # fielname girilen eleman kaşılaştırır uyuşmuyorsa message bıtakır
    password = PasswordField("Parola :", validators=[validators.DataRequired(
        message="Lutfen parola belirleyiniz"), validators.EqualTo(fieldname="confirm", message="Parola uyusmuyor...")])
    confirm = PasswordField("Tekrar parola giriniz :", validators=[
                            validators.DataRequired(message="Lutfen parola belirleyiniz")])

#! 2 adım


# Post bir butona basılma gibi eylemlerdir Get ise sayfa açılması yenilenmesi gibi bunlar request türlerindendir Post herhangi formu submit ettiğmizde çalışır
@app.route("/register", methods=["POST", "GET"])
def register():
    # Post veya get olması durumunda form objesi request ile form değişkeni dondurur
    form = KayitFormu(request.form)
    if request.method == "POST" and form.validate():  # form da sorun yoksa valite true doner
        # fonksiyon ismine gore url ye gider
        name = form.name.data  # data içindekiveriyi alır
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(
            form.password.data)  # sha parolayı sifreler
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO users (name,email,username,passaword) VALUES(%s,%s,%s,%s)",
                       (name, email, username, password))
        mysql.connection.commit()
        cursor.close()
        flash("Başarıyla Kayıt olundu...", "success")
        return redirect(url_for("anasayfa"))
        # form objesini gondermeliyiz ona göre elemanlar olusturlur
    else:
        return render_template("register.html", form=form)


class LoginForm(Form):
    username = StringField("Kullanıcı Adı", validators=[validators.Length(min=4, max=25), validators.DataRequired(
        "Burayi Mutlaka doldurmalısınız")])
    password = PasswordField("Parola :", validators=[validators.DataRequired(
        message="Lutfen parola belirleyiniz")])


@app.route("/login", methods=["POST", "GET"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST" and form.validate():
        username = form.username.data
        password = form.password.data
        cursor = mysql.connection.cursor()
        result = cursor.execute(
            "Select * from  users where username=%s", (username,))
        if result > 0:
            data = cursor.fetchone()
            real_password = data["passaword"]
            if sha256_crypt.verify(password, real_password):  # parola karşılastırır
                flash("Başarıyla giris yaptınız", "success")
                # sessionlar ortak sozluk yapına benzer değişken türüdür her yerde kullanılabilir mesela html da gibi herhangi bir ek birşey göndermemiz gerek yok
                session["username"] = username
                session["log_in"] = True
                return redirect(url_for("anasayfa"))
            else:
                flash("Şifre yanlış ", "danger")
                return redirect(url_for("login"))
        else:
            flash("Kullanıcı bulunmuyor...", "warning")
            return redirect(url_for("login"))
    else:
        return render_template("login.html", form=form)


@app.route("/logout")
def logout():
    session.clear()  # session bosaltır
    return render_template("anasayfa.html")

# Detay Sayfası


@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    result = cursor.execute("SELECT * FROM article WHERE id=%s", (id,))
    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article=article)
    else:
        return render_template("article.html")


@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    result = cursor.execute(
        "SELECT * FROM article where author=%s", (session["username"],))
    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles=articles)
    else:
        return render_template("dashboard.html")


class ArticleForm(Form):
    title = StringField("Makale Başlığı", validators=[
                        validators.Length(min=5, max=25)])
    content = TextAreaField("Makale İçeriği", validators=[
                            validators.Length(min=10)])


@app.route("/addarticle", methods=["POST", "GET"])
@login_required
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
        author = session["username"]
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO article (title, content, author) VALUES(%s,%s,%s)", (title, content, author))
        mysql.connection.commit()
        cursor.close()
        flash("Makale başarıyla eklendi...", "success")
        return redirect(url_for("dashboard"))
    else:
        return render_template("addarticle.html", form=form)


@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    result = cursor.execute("SELECT * FROM article")
    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html", articles=articles)
    else:
        return render_template("articles.html")


@app.route("/delete/<string:id>")
@login_required
def delete_article(id):
    cursor = mysql.connection.cursor()
    result = cursor.execute(
        "SELECT * FROM article where id=%s and author=%s", (id, session["username"]))
    if result > 0:
        cursor.execute(
            "DELETE FROM article WHERE id=%s and author=%s", (id, session["username"]))
        mysql.connection.commit()
        cursor.close()
        flash("Makale başarıyla silindi...", "success")
        return redirect(url_for("dashboard"))
    else:
        flash("Boyle bir makale bulunmuyor", "warning")
        return redirect(url_for("anasayfa"))


@app.route("/edit/<string:id>", methods=["POST", "GET"])
@login_required
def edit(id):
    cursor = mysql.connection.cursor()
    result = cursor.execute(
        "SELECT * FROM article where id=%s and author=%s", (id, session["username"]))
    form = ArticleForm(request.form)
    if result > 0:
        if request.method == "POST" and form.validate():

            title = form.title.data
            content = form.content.data
            cursor.execute("Update article SET title=%s, content=%s where id=%s and author=%s",
                           (title, content, id, session["username"]))
            mysql.connection.commit()
            cursor.close()
            flash("Başarıyla guncellenmiştir", "success")
            return redirect(url_for("dashboard"))
        else:

            article = cursor.fetchone()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("edit.html", form=form)

    else:
        flash("Boyle bir makale bulunmuyor", "warning")
        return redirect(url_for("anasayfa"))


@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "GET":
        # get olmasını istemiyoruz sadece post ta çalışır
        return redirect(url_for("anasayfa"))
    else:
        keyword = request.form.get("keyword")  # değeri almaya yarar name gore
        cursor = mysql.connection.cursor()
        # sql like metodu ile regex mantığı ile arama yapılır
        sorgu = "Select * from article where title LIKE '%"+keyword+"%'"
        result = cursor.execute(sorgu)
        if result > 0:
            articles = cursor.fetchall()
            return render_template("articles.html", articles=articles)
        else:
            return render_template("articles.html")


if __name__ == "__main__":
    app.run(debug=True)
