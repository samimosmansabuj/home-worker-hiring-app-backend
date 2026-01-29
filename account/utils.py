from rest_framework import serializers
from find_worker_config.model_choice import OTPType
from django.db.models import Q
import random
import string
import secrets
import cv2
import re
import easyocr
from passporteye import read_mrz
from rapidfuzz import fuzz
from dotenv import load_dotenv
import os
import requests
import base64

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



import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class KYCVerificationService:
    MRZ_MATCH_THRESHOLD = 90
    GOOGLE_MATCH_THRESHOLD = 90
    OCR_MATCH_THRESHOLD = 80

    def __init__(self, image_path, user):
        self.image_path = image_path
        self.user = user
        self.reader = easyocr.Reader(['en'], gpu=False)

    def normalize_name(self, name: str) -> str:
        return re.sub(r'[^A-Z ]', '', name.upper()).strip()

    def user_full_name(self):
        return self.normalize_name(
            f"{self.user.first_name} {self.user.last_name}"
        )

    def preprocess_image(self):
        img = cv2.imread(self.image_path)
        if img is None:
            raise Exception("Invalid image path")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        thresh = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        return thresh

    # ---------- MRZ OCR ----------
    def extract_from_mrz(self):
        mrz = read_mrz(self.image_path)
        if not mrz:
            return None
        data = mrz.to_dict()
        full_name = f"{data.get('names', '')} {data.get('surname', '')}"
        print("mrzocr full: ", data)
        return {
            "method": "MRZ",
            "name": self.normalize_name(full_name),
            "raw": data
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
        print("google vision full: ", text)
        return {
            "method": "GOOGLE VISION",
            "name": self.normalize_name(text),
            "raw": text
        }

    # ---------- EASY OCR ----------
    def extract_from_easyocr(self):
        processed = self.preprocess_image()
        results = self.reader.readtext(processed, detail=0)
        full_text = " ".join(results)
        print("easyocr full: ", full_text)
        return {
            "method": "OCR",
            "name": self.normalize_name(full_text),
            "raw": full_text
        }

    # ---------- NAME MATCH ----------
    def calculate_match_score(self, extracted_name):
        return fuzz.token_sort_ratio(
            self.user_full_name(),
            extracted_name
        )

    # ---------- MAIN VERIFICATION ----------
    def verify(self):
        print("user_full_name: ", self.user_full_name())
        print("=================================================")
        print("-------------------MRZ OCR----------------------")
        mrz_data = self.extract_from_mrz()
        if mrz_data:
            score = self.calculate_match_score(mrz_data["name"])
            print("mrz score: ", score)
            if score >= self.MRZ_MATCH_THRESHOLD:
                return self._verified_response(mrz_data, score)
        
        print("-------------------EASY OCR----------------------")
        ocr_data = self.extract_from_easyocr()
        if ocr_data:
            score = self.calculate_match_score(ocr_data["name"])
            print("easyocs score: ", score)
            if score >= self.OCR_MATCH_THRESHOLD:
                return self._verified_response(ocr_data, score)

        print("--------------GOOGLE VISION OCR-----------------")
        google_vision_data = self.extract_google_vision()
        if google_vision_data:
            score = self.calculate_match_score(google_vision_data["name"])
            print("google vision score: ", score)
            if score >= self.GOOGLE_MATCH_THRESHOLD:
                return self._verified_response(ocr_data, score)

        return self._manual_review_response(ocr_data, score)

    # ---------- RESPONSES ----------
    def _verified_response(self, data, score):
        return {
            "verified": True,
            "status": "VERIFIED",
            "method": data["method"],
            "score": score,
            "confidence": "HIGH" if data["method"] == "MRZ" else "MEDIUM",
        }

    def _manual_review_response(self, data, score):
        return {
            "verified": False,
            "status": "MANUAL_REVIEW",
            "method": data["method"],
            "score": score,
            "confidence": "LOW",
        }


