from flask import Flask,render_template,send_from_directory
from flask_cors import CORS
import os
from .routes import video_processing_blueprint  # 相対インポートに変更

def create_app():
    app = Flask(__name__)
    CORS(app)  # CORSを有効化

    # config.py を直接パスで指定
    app.config.from_pyfile(os.path.join(os.path.dirname(__file__), 'config.py'))
    
    # Blueprintの登録
    app.register_blueprint(video_processing_blueprint, url_prefix="/api")


    # シンプルなテストルートを定義
    @app.route('/')
    def index():
        return render_template("./index.html")
    # assets フォルダの中身を返すルートを定義
    def send_assets(folder, filename, **kwargs):
        return send_from_directory(folder, filename, **kwargs)
    @app.route('/favicon.ico')
    def favicon():
        return send_assets('./', 'favicon.ico')
    @app.route('/test')
    def test_route():
        return "テストページです！"

    return app
