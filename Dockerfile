# ベースイメージとしてUbuntuを使用
FROM ubuntu:20.04

# タイムゾーンの設定で対話的な処理を避ける
ENV DEBIAN_FRONTEND=noninteractive

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-opencv \
    curl \
    ffmpeg \
    git \  # gitを追加
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*  # キャッシュを削除してイメージサイズを小さくする

# Ollamaのインストール
RUN curl -fsSL https://ollama.com/install.sh | sh

# 作業ディレクトリを設定
WORKDIR /app

# 必要なファイルをコピー
COPY requirements.txt requirements.txt
COPY . .

# Pythonパッケージをインストール
RUN pip3 install --no-cache-dir -r requirements.txt \
    && git clone https://github.com/reazon-research/ReazonSpeech \
    && pip install Cython \
    && pip install ReazonSpeech/pkg/nemo-asr

# ポートを公開（必要に応じて）
EXPOSE 5000

# FlaskアプリケーションとOllamaを実行
CMD ["sh", "-c", "ollama run llava & python3 server.py"]