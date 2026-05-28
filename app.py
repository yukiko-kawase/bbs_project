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
    print("session user:", session['user_id'])
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
    return render_template('index.html', posts=posts)

# ログイン機能
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
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
        username = request.form['username']
        print("username:", "[" + username + "]")

        password = request.form['password']

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
    message = request.form['message']

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
                   (post_id,session['user_id']))
    
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

