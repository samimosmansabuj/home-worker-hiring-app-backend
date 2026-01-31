from rest_framework import serializers
from find_worker_config.model_choice import OTPType, DocumentStatus
from django.db.models import Q
import string
import secrets
import cv2
import re
from passporteye import read_mrz
from rapidfuzz import fuzz
from dotenv import load_dotenv
import os
import requests
import base64
from difflib import SequenceMatcher
from .regressions import DataRegressionFromPassportImage
from django.core.files.storage import default_storage

def generate_otp(length=6):
    if length <= 0:
        raise ValueError("OTP length must be greater than 0")
    digits = string.digits
    otp = ''.join(secrets.choice(digits) for _ in range(length))
    return otp

def get_otp_object(data, type):
    from account.models import OTP
    otp = data.get("otp")
    email = data.get("email")
    phone = data.get("phone")
    query = Q(code=otp, is_used=False, purpose=type)
    if phone:
        query &= Q(phone=phone)
    if email:
        query &= Q(email=email)
    otp_object = OTP.objects.filter(query).last()
    if not otp_object:
        raise Exception("Invalid OTP")
    if otp_object.is_expired():
        raise Exception("OTP expired")
    otp_object.is_used = True
    otp_object.save(update_fields=["is_used"])
    return otp_object

def image_delete_os(picture):
    if picture and default_storage.exists(picture.name):
        default_storage.delete(picture.name)
        return True

def previous_image_delete_os(oldpicture, newpicture):
    if oldpicture and oldpicture != newpicture and default_storage.exists(oldpicture.name):
        default_storage.delete(oldpicture.name)
        return True

import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class KYCVerificationService:
    MRZ_MATCH_THRESHOLD = 90
    GOOGLE_MATCH_THRESHOLD = 90

    def __init__(self, image_path, user):
        self.image_path = image_path
        self.user = user
    
    def normalize_name(self, name: str) -> str:
        return re.sub(r'[^A-Z ]', '', name.upper()).strip()

    def normalize_ocr_chars(self, text: str) -> str:
        replacements = {
            '0': 'O',
            '1': 'I',
            '5': 'S',
            '8': 'B',
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text

    def normalize_person_name(self, raw_name: str) -> str:
        if not raw_name:
            return ""
        name = self.normalize_ocr_chars(raw_name.upper().strip())
        name = re.sub(r'^(K\s*G\s*)', '', name).strip() # Remove KG prefix
        name = re.sub(r'[^A-Z ]', '', name).strip() # Remove special characters
        name = re.sub(r'\s+', ' ', name).strip() # Normalize spaces
        return name.strip()
    
    def user_full_name(self) -> string:
        first_name = self.user.first_name.upper()
        last_name = self.user.last_name.upper()
        return f"{first_name} {last_name}"

    # ---------- MRZ OCR ----------
    def extract_from_mrz(self) -> dict:
        mrz = read_mrz(self.image_path)
        if not mrz:
            return None
        data = mrz.to_dict()
        names = self.normalize_person_name(data.get('names', '').strip("K"))
        surname = self.normalize_person_name(data.get('surname', ''))
        full_name = f"{names} {surname}"
        return {
            "name": full_name
        }

    # ---------- GOOGLE VISSION OCR ----------
    def extract_google_vision(self):
        load_dotenv()
        API_KEY = os.getenv("API_KEY")
        with open(self.image_path, "rb") as f:
            content = f.read()
        image_base64 = base64.b64encode(content).decode()
        url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
        body = {
            "requests": [
                {
                    "image": {"content": image_base64},
                    "features": [{"type": "TEXT_DETECTION"}]
                }
            ]
        }
        response = requests.post(url, json=body)
        result = response.json()
        if "error" in result:
            raise Exception(result["error"]["message"])
        text = result["responses"][0].get("fullTextAnnotation", {}).get("text", "")
        extraction_object = DataRegressionFromPassportImage(text)
        extract_data = extraction_object.extract()

        return {
            "name": extract_data["name"],
            "dob": extract_data["dob"]
        }

    # ---------- NAME MATCH ----------
    def calculate_match_score_partial_ratio(self, extracted_name):
        return fuzz.partial_ratio(
            self.user_full_name(),
            extracted_name
        )

    def name_match_score(self, extracted_name):
        return SequenceMatcher(None, self.user_full_name(), extracted_name).ratio() * 100
    
    def get_best_score(self, score_fuzz, score_diff):
        return max(score_fuzz, score_diff)
        
    # ---------- MAIN VERIFICATION ----------
    def verify(self):
        # -------------------MRZ OCR----------------------
        mrz_data = self.extract_from_mrz()
        if mrz_data:
            mrz_score_fuzz = self.calculate_match_score_partial_ratio(mrz_data["name"])
            mrz_score_diff = self.name_match_score(mrz_data["name"])
            mrz_score = self.get_best_score(mrz_score_fuzz, mrz_score_diff)
            if mrz_score >= self.MRZ_MATCH_THRESHOLD:
                return self._verified_response(mrz_score, "MRZ")
        
        # --------------GOOGLE VISION OCR-----------------
        google_vision_data = self.extract_google_vision()
        if google_vision_data:
            google_score_fuzz = self.calculate_match_score_partial_ratio(google_vision_data["name"])
            google_score_diff = self.name_match_score(google_vision_data["name"])
            google_score = self.get_best_score(google_score_fuzz, google_score_diff)
            if google_score >= self.GOOGLE_MATCH_THRESHOLD:
                return self._verified_response(google_score, "GOOGLE VISION")
        
        highest_score = max(google_score, mrz_score)
        if 90 > highest_score > 70:
            status = DocumentStatus.REVIEW
        else:
            status = DocumentStatus.FAILED
        return self._manual_review_response(highest_score,  status)

    # ---------- RESPONSES ----------
    def _verified_response(self, score, method):
        return {
            "verified": True,
            "score": score,
            "method": method
        }

    def _manual_review_response(self, score, status):
        return {
            "verified": False,
            "status": status
        }
