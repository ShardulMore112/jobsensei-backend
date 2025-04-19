from flask import Flask, request, jsonify
import os
import json

# Import your service functions
from services.job_fetch import fetch_jobs_for_skill
from services.course_fetch import get_recommendations_as_json
from services.roadmap import setup_career_advisor, get_roadmap_json
from services.yt_model import search_youtube_tutorials

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Career Assistant Flask API is running!"

@app.route('/fetch_jobs', methods=['POST'])
def fetch_jobs():
    data = request.get_json()
    skill = data.get('skill')
    if not skill:
        return jsonify({"error": "Skill is required"}), 400

    results = fetch_jobs_for_skill(skill)
    return jsonify(results)

@app.route('/fetch_courses', methods=['POST'])
def fetch_courses():
    data = request.get_json()
    resume_path = data.get('resume_path')
    career_goal = data.get('career_goal')
    language = data.get('language', "English")

    if not resume_path or not os.path.exists(resume_path):
        return jsonify({"error": "Valid resume path is required"}), 400

    try:
        result = get_recommendations_as_json(resume_path, career_goal, language)
        return jsonify(json.loads(result))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/generate_roadmap', methods=['POST'])
def generate_roadmap():
    data = request.get_json()
    resume_path = data.get('resume_path')
    career_goal = data.get('career_goal', "AI Engineer")

    if not resume_path or not os.path.exists(resume_path):
        return jsonify({"error": "Valid resume path is required"}), 400

    try:
        rag_chain = setup_career_advisor(resume_path)
        roadmap = get_roadmap_json(rag_chain, career_goal)
        return jsonify(roadmap)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/youtube_tutorials', methods=['POST'])
def youtube_tutorials():
    data = request.get_json()
    skill = data.get('skill')
    language = data.get('language', None)

    if not skill:
        return jsonify({"error": "Skill is required"}), 400

    try:
        results = search_youtube_tutorials(skill, language)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
