from flask import Blueprint, jsonify, request, render_template
import cv2
from os import makedirs
from os.path import splitext, basename, join
from io import BytesIO
import requests
import openai
import os
import shutil
import base64
import json
from reazonspeech.nemo.asr import load_model, transcribe, audio_from_path


# OpenAI APIキーの設定
openai.api_key = os.getenv("OPENAI_API_KEY")

video_processing_blueprint = Blueprint("video_processing", __name__)

basedir = os.path.abspath(os.path.dirname(__file__))
model = load_model(device='cpu')

# URLから画像データを取得する関数
def fetch_image_from_url(url: str):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return BytesIO(response.content)
        else:
            print(f"URLから画像を取得できませんでした: {url}")
            return None
    except Exception as e:
        print(f"画像取得エラー ({url}): {e}")
        return None

def transcribe_audio(video_path):
    # 動画の音声を文字起こしする関数
    audio_path = join(basedir, "audio.wav")
    command = f"ffmpeg -i {video_path} -q:a 0 -map a {audio_path}"  # 動画から音声を抽出してWAV形式に保存
    os.system(command)

    audio = audio_from_path(audio_path)
    transcription = transcribe(model, audio)
    
    # transcription オブジェクトからテキストを抽出
    transcription_text = transcription.text  # ここで transcription_text を定義
    print(transcription_text)
    
    os.remove(audio_path)
    return transcription_text

@video_processing_blueprint.route("/process_video", methods=["POST"])
def process_video():
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "ファイルがありません"}), 400

        video_dir = join(basedir, "video")
        os.makedirs(video_dir, exist_ok=True)
        video_path = join(video_dir, file.filename)
        file.save(video_path)
        print(f"動画ファイルを保存しました: {video_path}")

        # フレームを保存
        frame_dir = join(basedir, "frame")
        os.makedirs(frame_dir, exist_ok=True)
        image_paths = save_frames(video_path, frame_dir)

        # 音声を文字起こし
        transcription_text = transcribe_audio(video_path)

        # 画像分析を実行
        analysis_response = requests.post(
            "http://localhost:5000/api/analyze_images",
                 json={
                    "image_paths": image_paths,         # image_paths を追加
                    "transcription": transcription_text
    }
        )

        # 不要なファイルとフォルダを削除
        os.remove(video_path)
        shutil.rmtree(frame_dir)

        if analysis_response.status_code == 200:
            return jsonify(analysis_response.json()), 200
        else:
            return jsonify({"error": "画像分析中にエラーが発生しました"}), 500

    except Exception as e:
        print(f"動画処理中にエラーが発生しました: {e}")
        return jsonify({"error": "動画の処理中にエラーが発生しました"}), 500
def encode_image(image_path):
    "画像をbase64にエンコードする関数"
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_image_with_ollama(image_path):
    # ollamaのllavaを用いて、画像を説明させる関数
    base64_image = encode_image(image_path)

    data = {
        'model': 'llava',
        'prompt': 'List the elements on the screen, paying special attention to those that do not comply with Japanese law and those that pose a risk of flame wars. In short sentences.',
        'images': [base64_image]
    }

    response = requests.post('http://localhost:11434/api/generate',
                            headers={'Content-Type': 'application/json'},
                            json=data,
                            stream=True)

    if response.status_code == 200:
        full_response = ''
        for line in response.iter_lines():
            if line:
                json_response = json.loads(line)
                if 'response' in json_response:
                    full_response += json_response['response']
                    print(json_response['response'], end='', flush=True)
                if json_response.get('done', False):
                    break
        return full_response
    else:
        return f"Error: {response.status_code} - {response.text}"

@video_processing_blueprint.route("/analyze_images", methods=["POST"])
def analyze_images():
    try:
        transcription = request.json.get("transcription", "")
        image_paths = request.json.get("image_paths", [])
        
        if not transcription:
            return jsonify({"error": "文字起こし結果がありません"}), 400
        
        if not image_paths:
            return jsonify({"error": "画像パスがありません"}), 400

        analysis_results = []
        for idx, image_path in enumerate(image_paths):
            if not os.path.exists(image_path):
                continue
            ollama_result = analyze_image_with_ollama(image_path)
            analysis_results.append(f"{idx+1}秒: {ollama_result}")

        if not analysis_results:
            return jsonify({"error": "有効な画像が見つかりません"}), 400

        summary_prompt = (
            f"Ollamaの結果は以下です:\n{chr(10).join(analysis_results)}\n"
            f"音声の文字起こし結果は以下です:\n{transcription}\n"
            "総合的な炎上リスクを評価してください。"
        )
        
        print(openai.api_key)  # APIキーを確認
        openai_response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "炎上リスクを判定してください。"},
                {"role": "user", "content": summary_prompt},
            ],
        )

        result = {
            "analysis_results": analysis_results,
            "openai_risk_assessment": openai_response.choices[0].message['content'].strip()
        }
        print(result)
        return jsonify(result), 200

    except Exception as e:
        print(f"画像分析中にエラーが発生しました: {e}")
        return jsonify({"error": "画像分析中にエラーが発生しました"}), 500
# 動画からフレームを切り出して、Firestorageにアップロードし、URLをFirestoreに保存
def save_frames(video_path: str, frame_dir: str, name="image", ext="jpg"):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_dir = join(frame_dir, splitext(basename(video_path))[0])
    makedirs(frame_dir, exist_ok=True)

    image_paths = []
    idx = 0
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % int(2*fps) == 0:
            filled_idx = str(idx).zfill(4)
            frame_filename = f"{join(frame_dir, name)}_{filled_idx}.{ext}"
            cv2.imwrite(frame_filename, frame)
            image_paths.append(frame_filename)
            idx += 1

        frame_count += 1

    cap.release()
    print("Frames have been saved.")
    return image_paths  # 追加