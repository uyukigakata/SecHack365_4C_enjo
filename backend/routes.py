from flask import Blueprint, jsonify, request, render_template
import cv2
from os import makedirs
from os.path import splitext, basename, join
from io import BytesIO
from google.cloud import vision
import requests
import openai
import os
import shutil
from .firebase_config import bucket, db
from google.cloud import firestore

# OpenAI APIキーの設定
openai.api_key = os.getenv("OPENAI_API_KEY")

video_processing_blueprint = Blueprint("video_processing", __name__)

# FirestoreとGoogle Cloud Visionクライアントの初期化
firestore_client = firestore.Client()
vision_client = vision.ImageAnnotatorClient()
basedir = os.path.abspath(os.path.dirname(__file__))

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

        collection_name = "frame"  
        doc_id = splitext(basename(video_path))[0]

        frame_dir = join(basedir, "frame")
        os.makedirs(frame_dir, exist_ok=True)
        image_urls = save_frames_and_upload(video_path, frame_dir, collection_name, doc_id)

        os.remove(video_path)
        shutil.rmtree(frame_dir)

        return jsonify({
            "message": "フレームが保存され、Firestorageにアップロードされました",
            "doc_id": doc_id,
            "image_urls": image_urls
        }), 200

    except Exception as e:
        print(f"動画処理中にエラーが発生しました: {e}")
        return jsonify({"error": "動画の処理中にエラーが発生しました"}), 500

@video_processing_blueprint.route("/analyze_images/<doc_id>", methods=["GET"])
def analyze_images(doc_id):
    try:
        data = get_marker_from_firestore("frame", doc_id)
        if not data or "images" not in data:
            return jsonify({"image_urls": [], "high_risk_frames": [], "openai_risk_assessment": ""}), 404

        analysis_results = []
        high_risk_frames = []
        cloudAPI_results = []

        for idx, url in enumerate(data["images"]):
            image_data = fetch_image_from_url(url)
            if image_data:
                image = vision.Image(content=image_data.read())
                response = vision_client.safe_search_detection(image=image)
                safe_search = response.safe_search_annotation

                safe_search_result = {
                    "adult": safe_search.adult,
                    "violence": safe_search.violence,
                    "racy": safe_search.racy
                }
                analysis_results.append(safe_search_result)

                if any(value >= 4 for value in safe_search_result.values()):
                    high_risk_frames.append(f"{idx+1}秒時点のフレーム")
                
                cloudAPI_results.append(f"{idx+1}秒: 成人={safe_search_result['adult']}, 暴力={safe_search_result['violence']}, 卑猥={safe_search_result['racy']}")

        summary_prompt = (
            f"動画の各フレームを解析した結果、高リスクと判断されたフレームは以下の通りです：{', '.join(high_risk_frames)}。"
            f"\nセーフサーチ結果は以下です:\n{chr(10).join(cloudAPI_results)}\n"
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
            "image_urls": data["images"],  # 画像URLリストを追加
            "high_risk_frames": high_risk_frames,
            "openai_risk_assessment": openai_response.choices[0].message['content'].strip()
        }
        return jsonify(result), 200

    except Exception as e:
        print(f"画像分析中にエラーが発生しました: {e}")
        return jsonify({"error": "画像分析中にエラーが発生しました"}), 500

    try:
        data = get_marker_from_firestore("frame", doc_id)
        if not data or "images" not in data:
            return jsonify({"image_urls": []}), 404

        analysis_results = []
        high_risk_frames = []
        cloudAPI_results = []

        for idx, url in enumerate(data["images"]):
            image_data = fetch_image_from_url(url)
            if image_data:
                image = vision.Image(content=image_data.read())
                response = vision_client.safe_search_detection(image=image)
                safe_search = response.safe_search_annotation

                safe_search_result = {
                    "adult": safe_search.adult,
                    "violence": safe_search.violence,
                    "racy": safe_search.racy
                }
                analysis_results.append(safe_search_result)

                if any(value >= 4 for value in safe_search_result.values()):
                    high_risk_frames.append(f"{idx+1}秒時点のフレーム")
                
                # Cloud Visionの結果をリストに追加
                cloudAPI_results.append(f"{idx+1}秒: 成人={safe_search_result['adult']}, 暴力={safe_search_result['violence']}, 卑猥={safe_search_result['racy']}")

        # 解析結果を基にOpenAI APIで総合的な炎上リスクを評価
        summary_prompt = (
            f"動画の各フレームを解析した結果、高リスクと判断されたフレームは以下の通りです：{', '.join(high_risk_frames)}。"
            f"\nセーフサーチ結果は以下です:\n{chr(10).join(cloudAPI_results)}\n"
            "総合的な炎上リスクを評価してください。"
        )
        
        openai_response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "不適切なコンテンツをSNSに投稿すると、学生から大人まで炎上によって誹謗中傷が発生します。"
                        "それを防ぐため、ユーザーがSNSにコンテンツを投稿する際に炎上の可能性があるか判定してください。"
                    )
                },
                {
                    "role": "user", 
                    "content": (
                        f"{summary_prompt}\n"
                        "炎上の基準には、公共の場での不適切な行動や、食に関する無礼な扱い、敬意の欠如が含まれます。"
                        "この画像が炎上する可能性が高いか低いかを判断してください。"
                    )
                },
            ],
            max_tokens=500
        )

        result = {
            "high_risk_frames": high_risk_frames,
            "openai_risk_assessment": openai_response.choices[0].message['content'].strip()
        }
        return jsonify(result), 200

    except Exception as e:
        print(f"画像分析中にエラーが発生しました: {e}")
        return jsonify({"error": "画像分析中にエラーが発生しました"}), 500

# 動画からフレームを切り出して、Firestorageにアップロードし、URLをFirestoreに保存
def save_frames_and_upload(video_path: str, frame_dir: str, collection_name: str, doc_id: str, name="image", ext="jpg"):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_dir = join(frame_dir, splitext(basename(video_path))[0])
    makedirs(frame_dir, exist_ok=True)

    image_urls = []
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

            image_url = upload_image_to_storage(collection_name, frame_filename, f"{splitext(basename(video_path))[0]}_{filled_idx}.{ext}")
            image_urls.append(image_url)
            
            os.remove(frame_filename)
            idx += 1

        frame_count += 1

    cap.release()
    print("Frames have been saved and uploaded to Firestorage.")
    save_urls_to_firestore(collection_name, doc_id, image_urls)
    return image_urls

def upload_image_to_storage(collection_name: str, image_path: str, image_name: str):
    blob = bucket.blob(f"{collection_name}/{image_name}")
    blob.upload_from_filename(image_path)
    blob.make_public()
    print('File uploaded successfully')
    return blob.public_url

def save_urls_to_firestore(collection_name: str, doc_id: str, image_urls: list):
    markers_ref = db.collection(collection_name).document(doc_id)
    markers_ref.set({"images": image_urls})
    print("Image URLs saved to Firestore.")

def get_marker_from_firestore(collection_name: str, doc_id: str):
    doc_ref = db.collection(collection_name).document(doc_id)
    doc = doc_ref.get()
    if doc.exists:
        print(f"Document data: {doc.to_dict()}")
        return doc.to_dict()
    else:
        print("No such document!")
        return None