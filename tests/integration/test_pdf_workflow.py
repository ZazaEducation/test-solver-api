"""Integration tests for complete PDF processing workflow."""

import pytest
import io
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.ai_test_solver.main import app
from src.ai_test_solver.models.test import TestStatus


@pytest.fixture
def test_pdf_content():
    """Load test PDF content."""
    pdf_path = Path(__file__).parent.parent / "fixtures" / "sample_test.pdf"
    if pdf_path.exists():
        return pdf_path.read_bytes()
    
    # Create a more realistic PDF for integration testing
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj

2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj

3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj

4 0 obj
<< /Length 400 >>
stream
BT
/F1 16 Tf
50 750 Td
(Sample Math Test) Tj
0 -40 Td
/F1 12 Tf
(1. What is the result of 15 + 27?) Tj
0 -20 Td
(A) 32) Tj
0 -15 Td
(B) 42) Tj
0 -15 Td
(C) 41) Tj
0 -15 Td
(D) 52) Tj
0 -30 Td
(2. Solve for x: 2x + 5 = 13) Tj
0 -20 Td
(A) x = 3) Tj
0 -15 Td
(B) x = 4) Tj
0 -15 Td
(C) x = 5) Tj
0 -15 Td
(D) x = 6) Tj
0 -30 Td
(3. What is the area of a circle with radius 5 units?) Tj
0 -20 Td
(A) 31.4 square units) Tj
0 -15 Td
(B) 78.5 square units) Tj
0 -15 Td
(C) 15.7 square units) Tj
0 -15 Td
(D) 25 square units) Tj
ET
endstream
endobj

5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj

xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000060 00000 n 
0000000120 00000 n 
0000000250 00000 n 
0000000700 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
770
%%EOF"""


@pytest.fixture
def mock_test_record():
    """Mock test record from database."""
    return Mock(
        id="550e8400-e29b-41d4-a716-446655440000",
        title="Sample Math Test",
        status=TestStatus.COMPLETED,
        file_url="https://storage.example.com/test.pdf",
        original_filename="sample_test.pdf",
        created_by="test@example.com",
        total_questions=3,
        questions=[
            Mock(
                id="q1",
                question_text="What is the result of 15 + 27?",
                choices=["32", "42", "41", "52"],
                correct_answer="42",
                ai_answer="B",
                ai_confidence=0.95,
                ai_explanation="15 + 27 = 42, so the answer is B) 42"
            ),
            Mock(
                id="q2", 
                question_text="Solve for x: 2x + 5 = 13",
                choices=["x = 3", "x = 4", "x = 5", "x = 6"],
                correct_answer="x = 4",
                ai_answer="B",
                ai_confidence=0.92,
                ai_explanation="2x + 5 = 13, so 2x = 8, therefore x = 4"
            ),
            Mock(
                id="q3",
                question_text="What is the area of a circle with radius 5 units?",
                choices=["31.4 square units", "78.5 square units", "15.7 square units", "25 square units"],
                correct_answer="78.5 square units", 
                ai_answer="B",
                ai_confidence=0.88,
                ai_explanation="Area = πr² = π × 5² = 25π ≈ 78.5 square units"
            )
        ]
    )


class TestPDFWorkflowIntegration:
    """Integration tests for complete PDF processing workflow."""
    
    @patch('src.ai_test_solver.api.tests.get_database_service')
    @patch('src.ai_test_solver.api.tests.get_file_storage_service')
    @patch('src.ai_test_solver.api.tests.get_test_processing_service')
    def test_complete_pdf_upload_to_processing_workflow(
        self, 
        mock_processor,
        mock_storage,
        mock_db,
        test_pdf_content
    ):
        """Test complete workflow from PDF upload to processing completion."""
        client = TestClient(app)
        
        # Setup service mocks
        test_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock database service
        db_service = AsyncMock()
        db_service.create_test.return_value = Mock(id=test_id)
        mock_db.return_value = db_service
        
        # Mock file storage service
        storage_service = AsyncMock()
        file_url = "https://storage.example.com/uploaded_test.pdf"
        storage_service.upload_file.return_value = file_url
        mock_storage.return_value = storage_service
        
        # Mock processing service
        processing_service = AsyncMock()
        mock_processor.return_value = processing_service
        
        # Step 1: Upload PDF
        files = {
            "file": ("math_test.pdf", io.BytesIO(test_pdf_content), "application/pdf")
        }
        data = {
            "title": "Integration Test Math Exam",
            "created_by": "integration@test.com"
        }
        
        response = client.post("/api/v1/tests/upload", files=files, data=data)
        
        # Verify upload response
        assert response.status_code == 200
        upload_data = response.json()
        assert upload_data["test_id"] == test_id
        assert upload_data["file_url"] == file_url
        
        # Verify services were called correctly
        storage_service.upload_file.assert_called_once()
        db_service.create_test.assert_called_once()
        
        # Verify test record creation parameters
        create_call_args = db_service.create_test.call_args[0][0]
        assert create_call_args["title"] == "Integration Test Math Exam"
        assert create_call_args["file_url"] == file_url
        assert create_call_args["original_filename"] == "math_test.pdf"
        assert create_call_args["created_by"] == "integration@test.com"
        
        # Verify background processing was initiated
        processing_service.process_test_async.assert_called_once()
        process_call_args = processing_service.process_test_async.call_args
        assert str(process_call_args[0][0]) == test_id  # test_id
        assert process_call_args[0][1] == file_url      # file_url
    
    @patch('src.ai_test_solver.api.tests.get_database_service')
    def test_get_test_status_workflow(self, mock_db, mock_test_record):
        """Test getting test status during processing."""
        client = TestClient(app)
        
        # Mock database service for status checking
        db_service = AsyncMock()
        
        # Test different statuses
        test_statuses = [
            (TestStatus.PENDING, "Test should show pending status"),
            (TestStatus.PROCESSING, "Test should show processing status with progress"),
            (TestStatus.COMPLETED, "Test should show completed status"),
            (TestStatus.FAILED, "Test should show failed status")
        ]
        
        for status, description in test_statuses:
            mock_test_record.status = status
            db_service.get_test.return_value = mock_test_record
            
            # Mock processing jobs for progress tracking
            if status == TestStatus.PROCESSING:
                db_service.get_processing_jobs.return_value = [
                    Mock(status="completed"),
                    Mock(status="completed"),
                    Mock(status="processing"),
                    Mock(status="pending")
                ]
            
            mock_db.return_value = db_service
            
            # Check status
            response = client.get(f"/api/v1/tests/{mock_test_record.id}/status")
            
            assert response.status_code == 200, description
            status_data = response.json()
            
            assert status_data["test_id"] == str(mock_test_record.id)
            assert status_data["status"] == status.value
            
            if status == TestStatus.PROCESSING:
                assert "progress" in status_data
                progress = status_data["progress"]
                assert progress["total_jobs"] == 4
                assert progress["completed_jobs"] == 2
                assert progress["failed_jobs"] == 0
    
    @patch('src.ai_test_solver.api.tests.get_database_service')
    def test_get_completed_test_results(self, mock_db, mock_test_record):
        """Test retrieving completed test results."""
        client = TestClient(app)
        
        # Setup completed test
        mock_test_record.status = TestStatus.COMPLETED
        
        db_service = AsyncMock()
        db_service.get_test_with_questions.return_value = mock_test_record
        mock_db.return_value = db_service
        
        # Get test results
        response = client.get(f"/api/v1/tests/{mock_test_record.id}")
        
        assert response.status_code == 200
        test_data = response.json()
        
        # Verify test metadata
        assert test_data["id"] == str(mock_test_record.id)
        assert test_data["title"] == mock_test_record.title
        assert test_data["status"] == TestStatus.COMPLETED.value
        assert test_data["total_questions"] == 3
        
        # Verify questions were included
        assert "questions" in test_data
        questions = test_data["questions"]
        assert len(questions) == 3
        
        # Verify first question structure
        q1 = questions[0]
        assert q1["question_text"] == "What is the result of 15 + 27?"
        assert q1["choices"] == ["32", "42", "41", "52"]
        assert q1["ai_answer"] == "B"
        assert q1["ai_confidence"] == 0.95
        assert "15 + 27 = 42" in q1["ai_explanation"]
    
    @patch('src.ai_test_solver.api.tests.get_database_service')
    @patch('src.ai_test_solver.api.tests.get_file_storage_service')
    def test_delete_test_workflow(self, mock_storage, mock_db, mock_test_record):
        """Test complete test deletion workflow."""
        client = TestClient(app)
        
        # Setup services
        db_service = AsyncMock()
        db_service.get_test.return_value = mock_test_record
        db_service.delete_test.return_value = None
        mock_db.return_value = db_service
        
        storage_service = AsyncMock()
        storage_service.delete_file.return_value = None
        mock_storage.return_value = storage_service
        
        # Delete test
        response = client.delete(f"/api/v1/tests/{mock_test_record.id}")
        
        assert response.status_code == 200
        delete_data = response.json()
        
        assert delete_data["success"] is True
        assert "deleted successfully" in delete_data["message"]
        
        # Verify file was deleted from storage
        storage_service.delete_file.assert_called_once_with(mock_test_record.file_url)
        
        # Verify test was deleted from database
        db_service.delete_test.assert_called_once_with(mock_test_record.id)
    
    def test_nonexistent_test_handling(self):
        """Test handling of requests for non-existent tests."""
        client = TestClient(app)
        
        nonexistent_id = "00000000-0000-0000-0000-000000000000"
        
        with patch('src.ai_test_solver.api.tests.get_database_service') as mock_db:
            db_service = AsyncMock()
            db_service.get_test.return_value = None
            db_service.get_test_with_questions.return_value = None
            mock_db.return_value = db_service
            
            # Test getting non-existent test
            response = client.get(f"/api/v1/tests/{nonexistent_id}")
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]
            
            # Test getting status of non-existent test
            response = client.get(f"/api/v1/tests/{nonexistent_id}/status")
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]
            
            # Test deleting non-existent test
            response = client.delete(f"/api/v1/tests/{nonexistent_id}")
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
class TestAsyncPDFWorkflow:
    """Test async PDF workflow integration."""
    
    async def test_async_complete_workflow(self, test_pdf_content, mock_test_record):
        """Test complete async workflow."""
        with patch('src.ai_test_solver.api.tests.get_database_service') as mock_db, \
             patch('src.ai_test_solver.api.tests.get_file_storage_service') as mock_storage, \
             patch('src.ai_test_solver.api.tests.get_test_processing_service') as mock_processor:
            
            test_id = "async-workflow-test-id"
            
            # Setup async mocks
            db_service = AsyncMock()
            db_service.create_test.return_value = Mock(id=test_id)
            mock_db.return_value = db_service
            
            storage_service = AsyncMock()
            storage_service.upload_file.return_value = "https://storage.example.com/async_test.pdf"
            mock_storage.return_value = storage_service
            
            processing_service = AsyncMock()
            mock_processor.return_value = processing_service
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Upload PDF
                files = {
                    "file": ("async_test.pdf", test_pdf_content, "application/pdf")
                }
                data = {
                    "title": "Async Workflow Test",
                    "created_by": "async@workflow.test"
                }
                
                response = await client.post("/api/v1/tests/upload", files=files, data=data)
                
                assert response.status_code == 200
                upload_data = response.json()
                assert upload_data["test_id"] == test_id
                
                # Verify async services were called
                db_service.create_test.assert_called_once()
                storage_service.upload_file.assert_called_once()
                processing_service.process_test_async.assert_called_once()
    
    async def test_concurrent_uploads(self, test_pdf_content):
        """Test handling multiple concurrent PDF uploads."""
        import asyncio
        
        with patch('src.ai_test_solver.api.tests.get_database_service') as mock_db, \
             patch('src.ai_test_solver.api.tests.get_file_storage_service') as mock_storage, \
             patch('src.ai_test_solver.api.tests.get_test_processing_service') as mock_processor:
            
            # Setup mocks for concurrent requests
            db_service = AsyncMock()
            storage_service = AsyncMock()
            processing_service = AsyncMock()
            
            # Different responses for each upload
            db_service.create_test.side_effect = [
                Mock(id="concurrent-test-1"),
                Mock(id="concurrent-test-2"),
                Mock(id="concurrent-test-3")
            ]
            storage_service.upload_file.side_effect = [
                "https://storage.example.com/test1.pdf",
                "https://storage.example.com/test2.pdf", 
                "https://storage.example.com/test3.pdf"
            ]
            
            mock_db.return_value = db_service
            mock_storage.return_value = storage_service
            mock_processor.return_value = processing_service
            
            async def upload_test(client, test_num):
                """Upload a test file."""
                files = {
                    "file": (f"test_{test_num}.pdf", test_pdf_content, "application/pdf")
                }
                data = {
                    "title": f"Concurrent Test {test_num}",
                    "created_by": f"concurrent{test_num}@test.com"
                }
                
                response = await client.post("/api/v1/tests/upload", files=files, data=data)
                return response
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Launch concurrent uploads
                tasks = [
                    upload_test(client, 1),
                    upload_test(client, 2),
                    upload_test(client, 3)
                ]
                
                responses = await asyncio.gather(*tasks)
                
                # Verify all uploads succeeded
                for i, response in enumerate(responses, 1):
                    assert response.status_code == 200
                    data = response.json()
                    assert data["test_id"] == f"concurrent-test-{i}"
                
                # Verify all services were called correct number of times
                assert db_service.create_test.call_count == 3
                assert storage_service.upload_file.call_count == 3
                assert processing_service.process_test_async.call_count == 3