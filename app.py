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
from flask import Flask, render_template, request, redirect
# SQLite（データベース）を使うために読み込む
import sqlite3
from datetime import datetime
# app.pyを基準にindex.html探してね
app = Flask(__name__)

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
            name TEXT,
            message TEXT
            created_at TEXT
        )
    ''')
    # 変更を確定する
    conn.commit()
    # DB終了（解放）
    conn.close()
# 起動時に1回実行
init_db()

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
# URLと処理を結びつける　
@app.route('/')
# ブラウザでhttp://127.0.0.1:5000/にアクセスしたらdef index()関数を動かす 
def index():
    conn = sqlite3.connect('bbs.db')
    cursor = conn.cursor()
    # DBからデータ取得
    cursor.execute('SELECT * FROM posts ORDER BY id DESC')
    # データベースから投稿データを全部取得する
    raw_posts = cursor.fetchall()
    conn.close()

    # 新しく空のリストを作る
    posts = []
    #  1件ずつ取り出して処理する
    for post in raw_posts:
        # id → 投稿番号　name → 名前　message → メッセージ　created_at → 投稿日時　likes → いいね数
        id, name, message, created_at, likes = post
        # 投稿日を「◯分前」に変換する
        time_text = time_ago(created_at)
        # 加工したデータをリストに追加
        posts.append((id, name, message, time_text, likes))

    # HTMLにデータを渡す
    return render_template('index.html', posts=posts)

# 投稿処理
# /post に送られたデータを処理する
@app.route('/post',methods=['POST'])
def post():
    # HTMLのinputから値を取る
    name =request.form['name']
    message = request.form['message']

    conn = sqlite3.connect('bbs.db')
    cursor = conn.cursor()
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # DBに書き込む　VALUES (?, ?)'SQL側　 (name, message)python側
    
    cursor.execute(
        'INSERT INTO posts (name, message, created_at) VALUES (?, ?, ?)',
        (name, message, created_at)
        )
    conn.commit()
    conn.close()

    return redirect('/')

# 削除処理
@app.route('/delete/<int:post_id>', methods=['POST'])
def delete(post_id):
    conn = sqlite3.connect('bbs.db')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))

    conn.commit()
    conn.close()

    return redirect('/')

# いいね処理
@app.route('/like/<int:post_id>', methods=['POST'])
def like(post_id):
    conn = sqlite3.connect('bbs.db')
    cursor = conn.cursor()

    cursor.execute(
        'UPDATE posts SET likes = likes + 1 WHERE id = ?',
        (post_id,)
    )

    conn.commit()
    conn.close()
    return redirect('/')

# 起動
# このファイルを直接実行したときだけ
if __name__ == '__main__':
    app.run(debug=True)

