import os
import json
import PyPDF2
import requests
from dotenv import load_dotenv
from typing import Dict, List, Optional
import google.generativeai as genai

# Load API keys
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

class EnhancedCourseRecommender:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-1.5-pro")

    def extract_text_from_pdf(self, pdf_file) -> str:
        return ''.join([page.extract_text() for page in PyPDF2.PdfReader(pdf_file).pages])

    def get_resume_text(self, resume_file) -> str:
        if isinstance(resume_file, str) and os.path.exists(resume_file):
            with open(resume_file, 'rb' if resume_file.endswith('.pdf') else 'r', encoding=None if resume_file.endswith('.pdf') else 'utf-8') as f:
                return self.extract_text_from_pdf(f) if resume_file.endswith('.pdf') else f.read()
        raise ValueError("Unsupported or missing resume file")

    def search_youtube_tutorials(self, skill: str, language: Optional[str] = None, max_results: int = 1) -> List[Dict]:
        query = f"{skill} tutorial" + (f" {language}" if language else "")
        lang_map = {"hindi": "hi", "tamil": "ta", "telugu": "te", "kannada": "kn", "marathi": "mr"}

        params = {
            "part": "snippet",
            "q": query,
            "maxResults": max_results,
            "type": "video",
            "videoDefinition": "high",
            "videoDuration": "medium",
            "key": YOUTUBE_API_KEY
        }

        if language and language.lower() in lang_map:
            params["relevanceLanguage"] = lang_map[language.lower()]

        try:
            res = requests.get("https://www.googleapis.com/youtube/v3/search", params=params)
            res.raise_for_status()
            data = res.json()
            return [{
                "title": item['snippet']['title'],
                "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                "thumbnail": item['snippet']['thumbnails']['medium']['url'],
                "description": item['snippet']['description']
            } for item in data.get('items', [])]
        except Exception as e:
            return [{"error": f"Failed to fetch YouTube tutorials: {str(e)}"}]

    def get_course_recommendations(self, resume_path, career_goal: Optional[str] = None,
                                   language: Optional[str] = None, num_courses: int = 10,
                                   num_videos: int = 5) -> List[Dict]:
        resume_text = self.get_resume_text(resume_path)

        # Generate skill list
        skill_prompt = f"You are an expert career advisor. Given resume: {resume_text} Career Goal: {career_goal or 'infer'} Identify 5 key skills as JSON list."
        skill_resp = self.model.generate_content(skill_prompt).text

        if "```json" in skill_resp:
            skill_resp = skill_resp.split("```json")[1].split("```")[0].strip()
        elif "```" in skill_resp:
            skill_resp = skill_resp.split("```")[1].split("```")[0].strip()

        try:
            skills = json.loads(skill_resp)
        except:
            skills = [s.strip(' "\'\n') for s in skill_resp.split(',')]

        # Generate course recommendations
        course_prompt = f"""You are a career advisor. Given resume: {resume_text} Career Goal: {career_goal or "infer"} Recommend {num_courses} real online courses in JSON format:
        [{{
            "title": "", "platform": "", "description": "", "url": "", "skill_category": "", "Price": "", "Time ": ""
        }}]"""

        course_resp = self.model.generate_content(course_prompt).text

        if "```json" in course_resp:
            course_resp = course_resp.split("```json")[1].split("```")[0].strip()
        elif "```" in course_resp:
            course_resp = course_resp.split("```")[1].split("```")[0].strip()

        try:
            courses = json.loads(course_resp)
        except json.JSONDecodeError as e:
            courses = [{"error": f"Invalid course JSON: {str(e)}", "raw_response": course_resp}]

        # Add YouTube videos per skill
        youtube_videos = []
        for skill in skills[:num_videos]:
            videos = self.search_youtube_tutorials(skill, language)
            if videos and isinstance(videos, list):
                v = videos[0]
                youtube_videos.append({
                    "title": v.get("title"),
                    "platform": "YouTube",
                    "description": f"Free tutorial on {skill}",
                    "url": v.get("url"),
                    "skill_category": skill,
                    "is_free": True,
                    "thumbnail": v.get("thumbnail")
                })

        return courses + youtube_videos


# ✅ Function used by Flask to get full result
def get_recommendations_as_json(resume_path, career_goal=None, language="English",
                                 num_courses=10, num_videos=5):
    recommender = EnhancedCourseRecommender()
    recommendations = recommender.get_course_recommendations(
        resume_path, career_goal, language, num_courses, num_videos
    )
    return json.dumps(recommendations, indent=2)
