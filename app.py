"""
app.pyを実行すると、その中でFlaskアプリが作られ
サーバ(http://127.0.0.1:5000)が起動し、
ブラウザからアクセスできる
"""
"""
Flask → アプリを作る機械
render_template → HTML表示する
request → 入力データを受け取る
redirect → 別ページに移動する
"""
from flask import Flask, render_template, request, redirect, url_for, session
# SQLite（データベース）を使うために読み込む
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash,check_password_hash

# app.pyを基準にindex.html探してね
app = Flask(__name__)
# secret_key 設定する  session機能はこのキーがないと使えない
app.secret_key = 'secret-key'

# データベース初期化
def init_db():
    """
    データベース（bbs.db）を初期化し、posts, users, likesテーブルが存在しない場合は作成する。
    """
    #  データベースファイルに接続　無ければ新しく作る
    conn = sqlite3.connect('bbs.db')
    cursor = conn.cursor()
    # SQL実行
    # 表（テーブル）を作る　すでにあれば作らない
    # id自動で番号振る
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            created_at TEXT,
            likes INTEGER DEFAULT 0
        )
    ''')

    # usersテーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
        ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        post_id INTEGER
    )
    ''')

    # 変更を確定する
    conn.commit()
    # DB終了（解放）
    conn.close()
# 起動時に1回実行
init_db()

# 入力チェック
# 以下の関数は、フォームから送られてきた入力を確かめます。
# 問題があればエラーメッセージを返し、問題なければ None を返します。

def validate_username(username):
    # username に値が入っていない場合
    if username is None:
        return "ユーザー名を入力してください"

    # 前後のスペースを削除して、実際の文字だけを確認します
    username = username.strip()

    # 空文字の場合はエラー
    if username == "":
        return "ユーザー名を入力してください"

    # 文字数が少なすぎる、または多すぎる場合はエラー
    if len(username) < 3 or len(username) > 20:
        return "ユーザー名は3〜20文字で入力してください"

    # ユーザー名にスペースや改行などの空白文字が入っている場合はエラー
    if any(c.isspace() for c in username):
        return "ユーザー名に空白文字は使えません"

    # ここまで問題がなければ、エラーなしとして None を返します
    return None


def validate_password(password):
    # password に値が入っていない場合
    if password is None or password == "":
        return "パスワードを入力してください"

    # パスワードが短すぎる場合はエラー
    if len(password) < 6:
        return "パスワードは6文字以上で入力してください"

    # パスワードが長すぎる場合もエラー
    if len(password) > 64:
        return "パスワードは64文字以下にしてください"

    # OK のときは None を返します
    return None


def validate_message(message):
    # message に値が入っていない場合
    if message is None:
        return "メッセージを入力してください"

    # スペースだけのメッセージも NG
    if message.strip() == "":
        return "メッセージを入力してください"

    # 長すぎるメッセージは NG
    if len(message) > 300:
        return "メッセージは300文字以内で入力してください"

    # 問題がなければ None を返します
    return None

# 投稿日時表示機能
def time_ago(created_at):
    now = datetime.now()
    past = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
    diff = (now - past).total_seconds()

    if diff < 60:
        return"今"
    elif diff < 3600:
        return f"{int(diff // 60)}分前"
    elif diff < 86400:
        return f"{int(diff // 3600)}時間前"
    else:
        return f"{int(diff // 86400)}日前"
    
# トップページ
@app.route('/')
# ブラウザでhttp://127.0.0.1:5000/にアクセスしたらdef index()関数を動かす 
def index():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('bbs.db')
    cursor = conn.cursor()
    # DBからデータ取得
    # cursor.execute('SELECT * FROM posts ORDER BY id DESC')
    cursor.execute('''
        SELECT 
            posts.id,
            posts.user_id,
            posts.message,
            posts.created_at,
            posts.likes,
            users.username,
            CASE 
                WHEN likes.user_id IS NOT NULL THEN 1 
                ELSE 0 
            END AS liked
        FROM posts
        JOIN users ON posts.user_id = users.id
        LEFT JOIN likes 
            ON posts.id = likes.post_id 
            AND likes.user_id = ?
        ORDER BY posts.id DESC
        ''', (session['user_id'],))

    # データベースから投稿データを全部取得する
    raw_posts = cursor.fetchall()
    conn.close()
    error = request.args.get('error')
    # 新しく空のリストを作る
    posts = []
    #  1件ずつ取り出して処理する
    for post in raw_posts:
        # id → 投稿番号　user_id → ユーザid　message → メッセージ　created_at → 投稿日時　likes → いいね数
        id, user_id, message, created_at, likes, username, liked = post
        # 投稿日を「◯分前」に変換する
        time_text = time_ago(created_at)
        # 加工したデータをリストに追加
        posts.append((id, user_id, message, time_text, likes, username,liked))
    # HTMLにデータを渡す
    return render_template('index.html', posts=posts, error=error)

# ログイン機能
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # ログイン時は username と password がどちらも必要
        if not username or not password:
            return render_template('login.html', error="ユーザー名とパスワードを入力してください")

        conn = sqlite3.connect('bbs.db')
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM users WHERE username=?',
            (username,)
        )
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect('/')
        else:
            return render_template('login.html', error="ログイン失敗")
    return render_template('login.html')

# 新規登録機能
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = ""

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # 登録時はユーザー名とパスワードを検証
        error = validate_username(username)
        if error is None:
            error = validate_password(password)

        if error is not None:
            return render_template('register.html', error=error)

        # パスワードをハッシュ化
        hashed = generate_password_hash(password)

        conn = sqlite3.connect('bbs.db')
        cursor = conn.cursor()

        try:
            cursor.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, hashed)
            )

            conn.commit()
            conn.close()

            return redirect('/login')
        except sqlite3.IntegrityError:
            error = "そのユーザ名はすでに使われています"
    return render_template('register.html', error=error)


# 投稿処理
# /post に送られたデータを処理する
@app.route('/post',methods=['POST'])
def post():
    # ログインしていない場合
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    # HTMLのinputから値を取る
    message = request.form.get('message', '')

    # 投稿内容の検証: 空白のみや長すぎるメッセージを禁止
    error = validate_message(message)
    if error is not None:
        return redirect(url_for('index', error=error))

    conn = sqlite3.connect('bbs.db')
    cursor = conn.cursor()

    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # DBに書き込む　VALUES (?, ?)'SQL側　 (user_id, message)python側
    cursor.execute(
        'INSERT INTO posts (user_id, message, created_at) VALUES (?, ?, ?)',
        (user_id, message, created_at)
        )
    
    conn.commit()
    conn.close()

    return redirect('/')

# 投稿編集処理
# ここは、投稿を編集するためのページを表示したり、編集内容を保存したりする場所です。
@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
def edit(post_id):
    # まずログインしているか確認します。ログインしていないならログインページへ戻します。
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('bbs.db')
    cursor = conn.cursor()

    # フォームの送信(method=POST)で編集内容を保存します。
    if request.method == 'POST':
        # フォームから投稿内容を取得します。
        message = request.form.get('message', '')

        # 投稿の内容が正しいか確認します。
        error = validate_message(message)
        if error is not None:
            # エラーがあれば、元の投稿内容をもう一度DBから読み込みます。
            cursor.execute(
                'SELECT * FROM posts WHERE id = ? AND user_id = ?',
                (post_id, session['user_id'])
            )
            post = cursor.fetchone()
            conn.close()

            # 投稿が見つからない場合はトップに戻します。
            if post is None:
                return redirect('/')

            # エラーメッセージを編集ページに表示します。
            return render_template('edit.html', post=post, error=error)

        # エラーがなければ、投稿内容を更新します。
        cursor.execute(
            'UPDATE posts SET message = ? WHERE id = ? AND user_id = ?',
            (message, post_id, session['user_id'])
        )
        conn.commit()
        conn.close()

        # 更新後はトップページに戻します。
        return redirect('/')

    # GET の場合は編集ページを表示します。
    cursor.execute(
        'SELECT * FROM posts WHERE id = ? AND user_id = ?',
        (post_id, session['user_id'])
    )
    post = cursor.fetchone()
    conn.close()

    # 自分の投稿が見つからなければトップに戻します。
    if post is None:
        return redirect('/')

    # 編集ページに投稿内容を渡します。
    return render_template('edit.html', post=post, error=None)

# 削除処理
@app.route('/delete/<int:post_id>', methods=['POST'])
def delete(post_id):

    # ログインしてない人はNG
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('bbs.db')
    cursor = conn.cursor()

    # 自分の投稿だけ削除
    cursor.execute('DELETE FROM posts WHERE id = ? AND user_id = ?',
                   (post_id, session['user_id']))
    
    conn.commit()
    conn.close()

    return redirect('/')

# いいね処理
@app.route('/like/<int:post_id>', methods=['POST'])
def like(post_id):
    user_id = session['user_id']
    conn = sqlite3.connect('bbs.db')
    cursor = conn.cursor()

    # すでにいいねしてるか確認
    cursor.execute(
        "SELECT 1 FROM likes WHERE user_id=? AND post_id=?",
        (user_id, post_id)
    )
    already = cursor.fetchone()

    if already:
        # いいね取り消し（ここがマイナス）
        cursor.execute(
            "DELETE FROM likes WHERE user_id=? AND post_id=?",
            (user_id, post_id)
        )
    else:
        # いいね追加（ここがプラス）
        cursor.execute(
            "INSERT INTO likes (user_id, post_id) VALUES (?, ?)",
            (user_id, post_id)
        )

    # 正しい数を再計算
    cursor.execute(
        "SELECT COUNT(*) FROM likes WHERE post_id=?",
        (post_id,)
    )
    count = cursor.fetchone()[0]

    cursor.execute(
        "UPDATE posts SET likes=? WHERE id=?",
        (count, post_id)
    )
    conn.commit()
    conn.close()
    return redirect('/')

# ログアウト機能
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect('/login')

# 起動
# このファイルを直接実行したときだけ
if __name__ == '__main__':
    app.run(debug=True)

