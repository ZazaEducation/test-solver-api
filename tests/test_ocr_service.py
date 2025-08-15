"""Test OCR service functionality with PDF processing."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from PIL import Image
import io

from src.ai_test_solver.services.ocr import OCRService
from src.ai_test_solver.core.exceptions import TestSolverException


@pytest.fixture
def ocr_service():
    """Create OCR service instance."""
    return OCRService()


@pytest.fixture
def sample_pdf_bytes():
    """Get sample PDF bytes."""
    pdf_path = Path(__file__).parent / "fixtures" / "sample_test.pdf"
    if pdf_path.exists():
        return pdf_path.read_bytes()
    
    # Fallback minimal PDF
    return b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj
4 0 obj<</Length 80>>stream
BT/F1 12 Tf 50 750 Td(1. What is 2+2?)Tj 0 -20 Td(A) 3 B) 4 C) 5)Tj ET
endstream endobj
xref
0 5
trailer<</Size 5/Root 1 0 R>>
startxref
300
%%EOF"""


@pytest.fixture
def sample_image():
    """Create a sample image for testing."""
    # Create a simple test image
    img = Image.new('RGB', (300, 200), color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer.getvalue()


class TestOCRService:
    """Test OCR service functionality."""
    
    @patch('src.ai_test_solver.services.ocr.vision.ImageAnnotatorClient')
    def test_extract_text_from_image(self, mock_vision_client, ocr_service, sample_image):
        """Test text extraction from image."""
        # Mock Google Vision API response
        mock_client_instance = Mock()
        mock_vision_client.return_value = mock_client_instance
        
        mock_response = Mock()
        mock_response.text_annotations = [
            Mock(description="Sample test question\n1. What is 2+2?\nA) 3\nB) 4\nC) 5")
        ]
        mock_client_instance.text_detection.return_value = mock_response
        
        # Test text extraction
        result = ocr_service.extract_text_from_image(sample_image)
        
        assert "Sample test question" in result
        assert "What is 2+2?" in result
        assert "A) 3" in result
        assert "B) 4" in result
        
        # Verify Vision API was called
        mock_client_instance.text_detection.assert_called_once()
    
    @patch('src.ai_test_solver.services.ocr.vision.ImageAnnotatorClient')
    def test_extract_text_no_text_found(self, mock_vision_client, ocr_service, sample_image):
        """Test handling when no text is found in image."""
        mock_client_instance = Mock()
        mock_vision_client.return_value = mock_client_instance
        
        mock_response = Mock()
        mock_response.text_annotations = []
        mock_client_instance.text_detection.return_value = mock_response
        
        result = ocr_service.extract_text_from_image(sample_image)
        
        assert result == ""
    
    @patch('src.ai_test_solver.services.ocr.vision.ImageAnnotatorClient')
    def test_extract_text_api_error(self, mock_vision_client, ocr_service, sample_image):
        """Test handling of Vision API errors."""
        mock_client_instance = Mock()
        mock_vision_client.return_value = mock_client_instance
        
        # Simulate API error
        mock_client_instance.text_detection.side_effect = Exception("Vision API error")
        
        with pytest.raises(TestSolverException) as exc_info:
            ocr_service.extract_text_from_image(sample_image)
        
        assert "OCR_FAILED" in str(exc_info.value)
        assert "Vision API error" in str(exc_info.value)
    
    @patch('pdf2image.convert_from_bytes')
    @patch('src.ai_test_solver.services.ocr.vision.ImageAnnotatorClient')
    def test_extract_text_from_pdf(self, mock_vision_client, mock_pdf2image, ocr_service, sample_pdf_bytes):
        """Test text extraction from PDF."""
        # Mock pdf2image conversion
        mock_image = Mock()
        mock_pdf2image.return_value = [mock_image]
        
        # Mock image to bytes conversion
        with patch.object(ocr_service, '_image_to_bytes') as mock_image_to_bytes:
            mock_image_to_bytes.return_value = b"fake_image_bytes"
            
            # Mock Vision API
            mock_client_instance = Mock()
            mock_vision_client.return_value = mock_client_instance
            
            mock_response = Mock()
            mock_response.text_annotations = [
                Mock(description="PDF Page Content\n1. Math Question\nA) Answer 1")
            ]
            mock_client_instance.text_detection.return_value = mock_response
            
            # Test PDF text extraction
            result = ocr_service.extract_text_from_pdf(sample_pdf_bytes)
            
            assert "PDF Page Content" in result
            assert "Math Question" in result
            
            # Verify pdf2image was called
            mock_pdf2image.assert_called_once_with(sample_pdf_bytes)
            
            # Verify Vision API was called for each page
            mock_client_instance.text_detection.assert_called()
    
    @patch('pdf2image.convert_from_bytes')
    def test_extract_text_from_pdf_conversion_error(self, mock_pdf2image, ocr_service, sample_pdf_bytes):
        """Test handling of PDF conversion errors."""
        # Simulate pdf2image error
        mock_pdf2image.side_effect = Exception("PDF conversion failed")
        
        with pytest.raises(TestSolverException) as exc_info:
            ocr_service.extract_text_from_pdf(sample_pdf_bytes)
        
        assert "PDF_CONVERSION_FAILED" in str(exc_info.value)
        assert "PDF conversion failed" in str(exc_info.value)
    
    @patch('pdf2image.convert_from_bytes')
    @patch('src.ai_test_solver.services.ocr.vision.ImageAnnotatorClient')
    def test_extract_text_from_multipage_pdf(self, mock_vision_client, mock_pdf2image, ocr_service):
        """Test text extraction from multi-page PDF."""
        # Mock multiple pages
        mock_page1 = Mock()
        mock_page2 = Mock()
        mock_pdf2image.return_value = [mock_page1, mock_page2]
        
        # Mock image conversion
        with patch.object(ocr_service, '_image_to_bytes') as mock_image_to_bytes:
            mock_image_to_bytes.return_value = b"fake_image_bytes"
            
            # Mock Vision API responses for each page
            mock_client_instance = Mock()
            mock_vision_client.return_value = mock_client_instance
            
            mock_responses = [
                Mock(text_annotations=[Mock(description="Page 1 Content\n1. Question 1")]),
                Mock(text_annotations=[Mock(description="Page 2 Content\n2. Question 2")])
            ]
            mock_client_instance.text_detection.side_effect = mock_responses
            
            # Test multi-page extraction
            result = ocr_service.extract_text_from_pdf(b"fake_pdf_bytes")
            
            assert "Page 1 Content" in result
            assert "Page 2 Content" in result
            assert "Question 1" in result
            assert "Question 2" in result
            
            # Verify Vision API was called twice (once per page)
            assert mock_client_instance.text_detection.call_count == 2
    
    def test_image_to_bytes(self, ocr_service):
        """Test PIL Image to bytes conversion."""
        # Create a test image
        test_image = Image.new('RGB', (100, 100), color='red')
        
        # Convert to bytes
        image_bytes = ocr_service._image_to_bytes(test_image)
        
        assert isinstance(image_bytes, bytes)
        assert len(image_bytes) > 0
        
        # Verify it's valid image data by loading it back
        loaded_image = Image.open(io.BytesIO(image_bytes))
        assert loaded_image.size == (100, 100)
        assert loaded_image.mode == 'RGB'
    
    @patch('src.ai_test_solver.services.ocr.vision.ImageAnnotatorClient')
    def test_process_file_pdf(self, mock_vision_client, ocr_service, sample_pdf_bytes):
        """Test processing PDF file through main interface."""
        with patch.object(ocr_service, 'extract_text_from_pdf') as mock_extract_pdf:
            mock_extract_pdf.return_value = "Extracted PDF text"
            
            result = ocr_service.process_file(sample_pdf_bytes, "application/pdf")
            
            assert result == "Extracted PDF text"
            mock_extract_pdf.assert_called_once_with(sample_pdf_bytes)
    
    @patch('src.ai_test_solver.services.ocr.vision.ImageAnnotatorClient')
    def test_process_file_image(self, mock_vision_client, ocr_service, sample_image):
        """Test processing image file through main interface."""
        with patch.object(ocr_service, 'extract_text_from_image') as mock_extract_image:
            mock_extract_image.return_value = "Extracted image text"
            
            result = ocr_service.process_file(sample_image, "image/png")
            
            assert result == "Extracted image text"
            mock_extract_image.assert_called_once_with(sample_image)
    
    def test_process_file_unsupported_type(self, ocr_service):
        """Test handling of unsupported file types."""
        with pytest.raises(TestSolverException) as exc_info:
            ocr_service.process_file(b"some data", "text/plain")
        
        assert "UNSUPPORTED_FILE_TYPE" in str(exc_info.value)
        assert "text/plain" in str(exc_info.value)


@pytest.mark.asyncio
class TestAsyncOCRService:
    """Test async OCR service functionality."""
    
    @patch('src.ai_test_solver.services.ocr.vision.ImageAnnotatorClient')
    async def test_async_extract_text_from_image(self, mock_vision_client, sample_image):
        """Test async text extraction from image."""
        # Create async OCR service
        ocr_service = OCRService()
        
        # Mock Vision API
        mock_client_instance = Mock()
        mock_vision_client.return_value = mock_client_instance
        
        mock_response = Mock()
        mock_response.text_annotations = [
            Mock(description="Async test content\n1. Async question")
        ]
        mock_client_instance.text_detection.return_value = mock_response
        
        # Test async extraction
        with patch.object(ocr_service, 'extract_text_from_image') as mock_extract:
            mock_extract.return_value = "Async extracted text"
            
            result = await ocr_service.extract_text_async(sample_image, "image/png")
            
            assert result == "Async extracted text"
            mock_extract.assert_called_once_with(sample_image)
    
    @patch('src.ai_test_solver.services.ocr.vision.ImageAnnotatorClient')
    async def test_async_extract_text_from_pdf(self, mock_vision_client, sample_pdf_bytes):
        """Test async text extraction from PDF."""
        ocr_service = OCRService()
        
        with patch.object(ocr_service, 'extract_text_from_pdf') as mock_extract:
            mock_extract.return_value = "Async PDF text"
            
            result = await ocr_service.extract_text_async(sample_pdf_bytes, "application/pdf")
            
            assert result == "Async PDF text"
            mock_extract.assert_called_once_with(sample_pdf_bytes)