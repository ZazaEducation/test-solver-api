"""Test PDF upload and processing functionality."""

import io
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.ai_test_solver.main import app
from src.ai_test_solver.models.test import TestStatus


@pytest.fixture
def test_pdf_content():
    """Load test PDF content."""
    pdf_path = Path(__file__).parent / "fixtures" / "sample_test.pdf"
    if pdf_path.exists():
        return pdf_path.read_bytes()
    
    # Fallback: create minimal PDF content
    return b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj
4 0 obj<</Length 44>>stream
BT/F1 12 Tf 50 750 Td(Sample Test Content)Tj ET
endstream endobj
xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000060 00000 n 
0000000120 00000 n 
0000000250 00000 n 
trailer<</Size 5/Root 1 0 R>>
startxref
300
%%EOF"""


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_services():
    """Mock all external services."""
    with patch('src.ai_test_solver.api.tests.get_database_service') as mock_db, \
         patch('src.ai_test_solver.api.tests.get_file_storage_service') as mock_storage, \
         patch('src.ai_test_solver.api.tests.get_test_processing_service') as mock_processor:
        
        # Mock database service
        db_service = AsyncMock()
        db_service.create_test.return_value = Mock(id="test-uuid-123")
        mock_db.return_value = db_service
        
        # Mock file storage service
        storage_service = AsyncMock()
        storage_service.upload_file.return_value = "https://storage.example.com/test.pdf"
        mock_storage.return_value = storage_service
        
        # Mock test processing service
        processing_service = AsyncMock()
        mock_processor.return_value = processing_service
        
        yield {
            'db': db_service,
            'storage': storage_service,
            'processor': processing_service
        }


class TestPDFUpload:
    """Test PDF upload functionality."""
    
    def test_upload_valid_pdf(self, client, test_pdf_content, mock_services):
        """Test uploading a valid PDF file."""
        files = {
            "file": ("test.pdf", io.BytesIO(test_pdf_content), "application/pdf")
        }
        data = {
            "title": "Sample Math Test",
            "created_by": "test@example.com"
        }
        
        response = client.post("/api/v1/tests/upload", files=files, data=data)
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert "test_id" in response_data
        assert "file_url" in response_data
        assert "estimated_time" in response_data
        assert response_data["file_url"] == "https://storage.example.com/test.pdf"
        
        # Verify services were called
        mock_services['storage'].upload_file.assert_called_once()
        mock_services['db'].create_test.assert_called_once()
    
    def test_upload_invalid_file_type(self, client):
        """Test uploading an invalid file type."""
        files = {
            "file": ("test.txt", io.BytesIO(b"This is not a PDF"), "text/plain")
        }
        data = {
            "title": "Invalid Test",
            "created_by": "test@example.com"
        }
        
        response = client.post("/api/v1/tests/upload", files=files, data=data)
        
        assert response.status_code == 422
        assert "not supported" in response.json()["detail"]
    
    def test_upload_missing_title(self, client, test_pdf_content):
        """Test uploading without required title field."""
        files = {
            "file": ("test.pdf", io.BytesIO(test_pdf_content), "application/pdf")
        }
        data = {
            "created_by": "test@example.com"
            # Missing title
        }
        
        response = client.post("/api/v1/tests/upload", files=files, data=data)
        
        assert response.status_code == 422
    
    def test_upload_missing_created_by(self, client, test_pdf_content):
        """Test uploading without required created_by field."""
        files = {
            "file": ("test.pdf", io.BytesIO(test_pdf_content), "application/pdf")
        }
        data = {
            "title": "Test Without Creator"
            # Missing created_by
        }
        
        response = client.post("/api/v1/tests/upload", files=files, data=data)
        
        assert response.status_code == 422
    
    @patch('src.ai_test_solver.core.settings.max_file_size_bytes', 1024)  # 1KB limit
    def test_upload_file_too_large(self, client):
        """Test uploading a file that exceeds size limit."""
        large_content = b"x" * 2048  # 2KB file
        files = {
            "file": ("large.pdf", io.BytesIO(large_content), "application/pdf")
        }
        data = {
            "title": "Large Test",
            "created_by": "test@example.com"
        }
        
        response = client.post("/api/v1/tests/upload", files=files, data=data)
        
        assert response.status_code == 413
        assert "exceeds maximum allowed size" in response.json()["detail"]
    
    def test_upload_storage_failure(self, client, test_pdf_content, mock_services):
        """Test handling storage service failure."""
        # Make storage service fail
        mock_services['storage'].upload_file.side_effect = Exception("Storage failed")
        
        files = {
            "file": ("test.pdf", io.BytesIO(test_pdf_content), "application/pdf")
        }
        data = {
            "title": "Test Storage Failure",
            "created_by": "test@example.com"
        }
        
        response = client.post("/api/v1/tests/upload", files=files, data=data)
        
        assert response.status_code == 500
        assert "Failed to upload and process test file" in response.json()["detail"]
    
    def test_upload_database_failure(self, client, test_pdf_content, mock_services):
        """Test handling database service failure."""
        # Make database service fail
        mock_services['db'].create_test.side_effect = Exception("Database failed")
        
        files = {
            "file": ("test.pdf", io.BytesIO(test_pdf_content), "application/pdf")
        }
        data = {
            "title": "Test Database Failure",
            "created_by": "test@example.com"
        }
        
        response = client.post("/api/v1/tests/upload", files=files, data=data)
        
        assert response.status_code == 500
        assert "Failed to upload and process test file" in response.json()["detail"]


class TestFileValidation:
    """Test file validation logic."""
    
    def test_validate_pdf_extension(self, client, test_pdf_content):
        """Test PDF file extension validation."""
        files = {
            "file": ("document.pdf", io.BytesIO(test_pdf_content), "application/pdf")
        }
        data = {
            "title": "PDF Test",
            "created_by": "test@example.com"
        }
        
        with patch('src.ai_test_solver.api.tests.get_database_service'), \
             patch('src.ai_test_solver.api.tests.get_file_storage_service'), \
             patch('src.ai_test_solver.api.tests.get_test_processing_service'):
            response = client.post("/api/v1/tests/upload", files=files, data=data)
            # Should not fail validation
            assert response.status_code != 422 or "File type not supported" not in response.json().get("detail", "")
    
    def test_validate_image_extensions(self, client):
        """Test image file extension validation."""
        image_content = b"fake image content"
        
        valid_extensions = [
            ("test.png", "image/png"),
            ("test.jpg", "image/jpeg"),
            ("test.jpeg", "image/jpeg"),
            ("test.tiff", "image/tiff"),
            ("test.bmp", "image/bmp"),
        ]
        
        for filename, content_type in valid_extensions:
            files = {
                "file": (filename, io.BytesIO(image_content), content_type)
            }
            data = {
                "title": f"Image Test {filename}",
                "created_by": "test@example.com"
            }
            
            with patch('src.ai_test_solver.api.tests.get_database_service'), \
                 patch('src.ai_test_solver.api.tests.get_file_storage_service'), \
                 patch('src.ai_test_solver.api.tests.get_test_processing_service'):
                response = client.post("/api/v1/tests/upload", files=files, data=data)
                # Should not fail validation for file type
                if response.status_code == 422:
                    assert "File type not supported" not in response.json().get("detail", "")
    
    def test_validate_invalid_extensions(self, client):
        """Test rejection of invalid file extensions."""
        invalid_files = [
            ("test.doc", "application/msword"),
            ("test.txt", "text/plain"),
            ("test.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ("test.mp4", "video/mp4"),
        ]
        
        for filename, content_type in invalid_files:
            files = {
                "file": (filename, io.BytesIO(b"fake content"), content_type)
            }
            data = {
                "title": f"Invalid Test {filename}",
                "created_by": "test@example.com"
            }
            
            response = client.post("/api/v1/tests/upload", files=files, data=data)
            
            assert response.status_code == 422
            assert "not supported" in response.json()["detail"]


@pytest.mark.asyncio
class TestAsyncPDFUpload:
    """Test PDF upload with async client."""
    
    async def test_async_upload_pdf(self, test_pdf_content):
        """Test PDF upload using async client."""
        with patch('src.ai_test_solver.api.tests.get_database_service') as mock_db, \
             patch('src.ai_test_solver.api.tests.get_file_storage_service') as mock_storage, \
             patch('src.ai_test_solver.api.tests.get_test_processing_service') as mock_processor:
            
            # Setup mocks
            db_service = AsyncMock()
            db_service.create_test.return_value = Mock(id="async-test-uuid")
            mock_db.return_value = db_service
            
            storage_service = AsyncMock()
            storage_service.upload_file.return_value = "https://storage.example.com/async-test.pdf"
            mock_storage.return_value = storage_service
            
            mock_processor.return_value = AsyncMock()
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                files = {
                    "file": ("async_test.pdf", test_pdf_content, "application/pdf")
                }
                data = {
                    "title": "Async PDF Test",
                    "created_by": "async@example.com"
                }
                
                response = await client.post("/api/v1/tests/upload", files=files, data=data)
                
                assert response.status_code == 200
                response_data = response.json()
                
                assert "test_id" in response_data
                assert response_data["file_url"] == "https://storage.example.com/async-test.pdf"
                
                # Verify async services were called
                db_service.create_test.assert_called_once()
                storage_service.upload_file.assert_called_once()