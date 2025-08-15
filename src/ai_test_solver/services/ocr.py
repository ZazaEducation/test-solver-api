"""OCR service using Google Cloud Vision API."""

import io
import os
from typing import List, Optional
from functools import lru_cache

from google.cloud import vision
from PIL import Image
import pdf2image

from ..core import get_logger, settings, OCRError
from ..models.api import ErrorResponse

logger = get_logger(__name__)


class OCRService:
    """Service for extracting text from images and PDFs using Google Cloud Vision."""
    
    def __init__(self):
        """Initialize the OCR service."""
        self._client: Optional[vision.ImageAnnotatorClient] = None
    
    @property
    def client(self) -> vision.ImageAnnotatorClient:
        """Get or create Google Cloud Vision client."""
        if self._client is None:
            try:
                # Set up authentication if credentials file is provided
                if settings.google_application_credentials:
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.google_application_credentials
                
                self._client = vision.ImageAnnotatorClient()
                logger.info("Google Cloud Vision client initialized")
            except Exception as exc:
                logger.error("Failed to initialize Google Cloud Vision client", error=str(exc))
                raise OCRError(f"Failed to initialize OCR service: {str(exc)}") from exc
        
        return self._client
    
    async def extract_text_from_image(self, image_data: bytes) -> str:
        """
        Extract text from an image using Google Cloud Vision.
        
        Args:
            image_data: Image data in bytes
            
        Returns:
            Extracted text content
            
        Raises:
            OCRError: If text extraction fails
        """
        try:
            logger.info("Starting OCR text extraction from image")
            
            # Create Vision API image object
            image = vision.Image(content=image_data)
            
            # Perform text detection
            response = self.client.text_detection(image=image)
            
            # Check for errors
            if response.error.message:
                raise OCRError(f"Google Cloud Vision API error: {response.error.message}")
            
            # Extract text from response
            texts = response.text_annotations
            if not texts:
                logger.warning("No text found in image")
                return ""
            
            # First annotation contains the entire detected text
            extracted_text = texts[0].description
            
            logger.info(
                "OCR text extraction completed",
                text_length=len(extracted_text),
                blocks_detected=len(texts)
            )
            
            return extracted_text
            
        except Exception as exc:
            logger.error("OCR text extraction failed", error=str(exc), exc_info=True)
            raise OCRError(f"Failed to extract text from image: {str(exc)}") from exc
    
    async def extract_text_from_pdf(self, pdf_data: bytes) -> str:
        """
        Extract text from a PDF by converting to images and using OCR.
        
        Args:
            pdf_data: PDF data in bytes
            
        Returns:
            Extracted text content from all pages
            
        Raises:
            OCRError: If text extraction fails
        """
        try:
            logger.info("Starting OCR text extraction from PDF")
            
            # Convert PDF to images
            pdf_file = io.BytesIO(pdf_data)
            images = pdf2image.convert_from_bytes(
                pdf_file.read(),
                dpi=200,  # Good balance between quality and performance
                fmt='PNG'
            )
            
            if not images:
                raise OCRError("No pages found in PDF")
            
            logger.info(f"PDF converted to {len(images)} images")
            
            # Extract text from each page
            all_text_parts = []
            
            for page_num, image in enumerate(images, 1):
                logger.info(f"Processing page {page_num}/{len(images)}")
                
                # Convert PIL image to bytes
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                # Extract text from this page
                page_text = await self.extract_text_from_image(img_byte_arr)
                
                if page_text.strip():
                    all_text_parts.append(f"--- Page {page_num} ---\n{page_text}")
                
            # Combine all pages
            combined_text = "\n\n".join(all_text_parts)
            
            logger.info(
                "PDF OCR extraction completed",
                total_pages=len(images),
                total_text_length=len(combined_text)
            )
            
            return combined_text
            
        except Exception as exc:
            logger.error("PDF OCR extraction failed", error=str(exc), exc_info=True)
            raise OCRError(f"Failed to extract text from PDF: {str(exc)}") from exc
    
    async def extract_text_from_file(self, file_data: bytes, filename: str) -> str:
        """
        Extract text from a file (automatically detects PDF vs image).
        
        Args:
            file_data: File data in bytes
            filename: Original filename for type detection
            
        Returns:
            Extracted text content
            
        Raises:
            OCRError: If text extraction fails or file type is unsupported
        """
        try:
            file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
            
            logger.info(
                "Starting file OCR processing",
                filename=filename,
                file_extension=file_ext,
                file_size=len(file_data)
            )
            
            if file_ext == 'pdf':
                return await self.extract_text_from_pdf(file_data)
            elif file_ext in ['png', 'jpg', 'jpeg', 'tiff', 'bmp']:
                return await self.extract_text_from_image(file_data)
            else:
                raise OCRError(f"Unsupported file type: {file_ext}")
                
        except OCRError:
            raise
        except Exception as exc:
            logger.error("File OCR processing failed", error=str(exc), exc_info=True)
            raise OCRError(f"Failed to process file {filename}: {str(exc)}") from exc
    
    async def preprocess_image(self, image_data: bytes) -> bytes:
        """
        Preprocess image for better OCR results.
        
        Args:
            image_data: Original image data
            
        Returns:
            Preprocessed image data
        """
        try:
            # Open image with PIL
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if image is too large (for better processing speed)
            max_size = 2048
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"Image resized to {new_size}")
            
            # Save processed image to bytes
            output = io.BytesIO()
            image.save(output, format='PNG', optimize=True)
            
            return output.getvalue()
            
        except Exception as exc:
            logger.warning("Image preprocessing failed, using original", error=str(exc))
            return image_data


@lru_cache()
def get_ocr_service() -> OCRService:
    """Get singleton OCR service instance."""
    return OCRService()