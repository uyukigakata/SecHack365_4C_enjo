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
    "動画の音声を文字起こしする関数"
    audio_path = join(basedir, "audio.wav")
    command = f"ffmpeg -i {video_path} -q:a 0 -map a {audio_path}"
    os.system(command)

    audio = audio_from_path(audio_path)
    transcription =transcribe(model, audio)
    
    os.remove(audio_path)
    return transcription

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

        frame_dir = join(basedir, "frame")
        os.makedirs(frame_dir, exist_ok=True)
        image_paths = save_frames(video_path, frame_dir)

        transcription = transcribe_audio(video_path)

        os.remove(video_path)
        shutil.rmtree(frame_dir)

        return jsonify({
            "message": "フレームと音声の文字起こしが保存されました",
            "image_paths": image_paths,
        }), 200

    except Exception as e:
        print(f"動画処理中にエラーが発生しました: {e}")
        return jsonify({"error": "動画の処理中にエラーが発生しました"}), 500

def encode_image(image_path):
    "画像をbase64にエンコードする関数"
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_image_with_ollama(image_path):
    "ollamaのllavaを用いて、画像を説明させる関数"
    base64_image = encode_image(image_path)

    data = {
        'model': 'llava',
        'prompt': 'Please briefly describe what you see in this image.',
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
        image_paths = request.json.get("image_paths", [])
        transcription = request.json.get("transcription", "")
        if not image_paths:
            return jsonify({"error": "画像パスがありません"}), 400

        analysis_results = []
        for idx, image_path in enumerate(image_paths):
            ollama_result = analyze_image_with_ollama(image_path)
            analysis_results.append(f"{idx+1}秒: {ollama_result}")

        summary_prompt = (
            f"Ollamaの結果は以下です:\n{chr(10).join(analysis_results)}\n"
            f"音声の文字起こし結果は以下です:\n{transcription}\n"
            "総合的な炎上リスクを評価してください。"
        )
        
        openai_response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "炎上リスクを判定してください。"},
                {"role": "user", "content": summary_prompt},
            ],
            max_tokens=500
        )

        result = {
            "analysis_results": analysis_results,
            "openai_risk_assessment": openai_response.choices[0].message['content'].strip()
        }
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

        if frame_count % int(fps) == 0:
            filled_idx = str(idx).zfill(4)
            frame_filename = f"{join(frame_dir, name)}_{filled_idx}.{ext}"
            cv2.imwrite(frame_filename, frame)
            image_paths.append(frame_filename)
            idx += 1

        frame_count += 1

    cap.release()
    print("Frames have been saved.")
    return image_paths
