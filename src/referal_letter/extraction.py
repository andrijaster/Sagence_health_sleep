import os
import base64
from typing import List, Optional
from pydantic import BaseModel, Field
from pdf2image import convert_from_path
from openai import AsyncOpenAI


class ReferralInfo(BaseModel):
    patient_name: str = Field(description="Full name of the patient.")
    doctor_name: str = Field(description="Referring doctor’s full name.")
    referral_reason: str = Field(description="Reason for the referral in details.")
    referral_date: str = Field(description="Date of the referral, e.g., '12 March 2024'.")
    referred_to: str = Field(description="Specialist, department, or hospital referred to.")


class AsyncReferralLetterExtractor:
    def __init__(self, api_key: str = None):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key must be provided or set in the OPENAI_API_KEY environment variable.")
        self.client = AsyncOpenAI(api_key=api_key)

    @staticmethod
    def convert_pdf_to_images(pdf_path: str) -> List[str]:
        """Convert PDF pages to JPEG images (sync since pdf2image is not async)."""
        images = convert_from_path(pdf_path, dpi=300)
        image_paths = []
        for i, image in enumerate(images):
            temp_path = f"{pdf_path}_page_{i + 1}.jpg"
            image.save(temp_path, "JPEG")
            image_paths.append(temp_path)
        return image_paths

    @staticmethod
    def encode_image_to_base64(image_path: str) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    async def extract_info_from_images(self, base64_images: List[str]) -> Optional[ReferralInfo]:
        """Asynchronously extract info from images using GPT-4o."""
        message_content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64}",
                    "detail": "high"
                }
            }
            for b64 in base64_images
        ]

        try:
            completion = await self.client.chat.completions.parse(
                model="gpt-4o-2024-08-06",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Extract the most important information from this multi-page doctor's referral letter. "
                            "Provide patient name, referring doctor name, referral reason, referral date, and "
                            "specialist or hospital referred to."
                        ),
                    },
                    {
                        "role": "user",
                        "content": message_content,
                    },
                ],
                temperature=0,
                response_format=ReferralInfo,
            )
            return completion.choices[0].message.parsed
        except Exception as e:
            print(f"❌ GPT extraction failed: {e}")
            return None

    async def process_pdf(self, pdf_path: str) -> dict:
        """Process a single PDF file asynchronously."""
        try:
            image_paths = self.convert_pdf_to_images(pdf_path)
            base64_images = [self.encode_image_to_base64(p) for p in image_paths]

            print(f"📄 Processing: {os.path.basename(pdf_path)} ({len(base64_images)} pages)...")

            result = await self.extract_info_from_images(base64_images)
            if result:
                return {
                    "filename": os.path.basename(pdf_path),
                    **result.dict()
                }
            else:
                return {
                    "filename": os.path.basename(pdf_path),
                    "patient_name": "ERROR",
                    "doctor_name": "ERROR",
                    "referral_reason": "ERROR",
                    "referral_date": "ERROR",
                    "referred_to": "ERROR",
                }

        except Exception as e:
            print(f"❌ Error processing {pdf_path}: {e}")
            return {
                "filename": os.path.basename(pdf_path),
                "patient_name": "ERROR",
                "doctor_name": "ERROR",
                "referral_reason": "ERROR",
                "referral_date": "ERROR",
                "referred_to": "ERROR",
            }