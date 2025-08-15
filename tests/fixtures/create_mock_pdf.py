"""Create mock PDF files for testing."""

import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def create_sample_test_pdf() -> bytes:
    """Create a sample test PDF with multiple choice questions."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    question_style = ParagraphStyle(
        'Question',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    
    choice_style = ParagraphStyle(
        'Choice',
        parent=styles['Normal'],
        fontSize=11,
        leftIndent=20,
        spaceAfter=5
    )
    
    # Content
    story = []
    
    # Title
    story.append(Paragraph("Sample Mathematics Test", title_style))
    story.append(Spacer(1, 12))
    
    # Instructions
    instructions = """
    <b>Instructions:</b><br/>
    • Choose the best answer for each question<br/>
    • Mark only one answer per question<br/>
    • Show your work where applicable
    """
    story.append(Paragraph(instructions, styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Questions
    questions = [
        {
            "question": "1. What is the result of 15 + 27?",
            "choices": ["A) 32", "B) 42", "C) 41", "D) 52"],
            "correct": "B"
        },
        {
            "question": "2. Solve for x: 2x + 5 = 13",
            "choices": ["A) x = 3", "B) x = 4", "C) x = 5", "D) x = 6"],
            "correct": "B"
        },
        {
            "question": "3. What is the area of a circle with radius 5 units? (Use π ≈ 3.14)",
            "choices": ["A) 31.4 square units", "B) 78.5 square units", "C) 15.7 square units", "D) 25 square units"],
            "correct": "B"
        },
        {
            "question": "4. Which of the following is a prime number?",
            "choices": ["A) 15", "B) 21", "C) 17", "D) 25"],
            "correct": "C"
        },
        {
            "question": "5. What is the value of 3² + 4²?",
            "choices": ["A) 14", "B) 25", "C) 49", "D) 7"],
            "correct": "B"
        }
    ]
    
    for q_data in questions:
        # Add question
        story.append(Paragraph(q_data["question"], question_style))
        
        # Add choices
        for choice in q_data["choices"]:
            story.append(Paragraph(choice, choice_style))
        
        story.append(Spacer(1, 15))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def create_complex_test_pdf() -> bytes:
    """Create a more complex test PDF with mixed question types."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    story = []
    
    # Title
    story.append(Paragraph("Advanced Physics and Chemistry Test", title_style))
    story.append(Spacer(1, 20))
    
    # Section A: Multiple Choice
    story.append(Paragraph("<b>Section A: Multiple Choice (40 points)</b>", styles['Heading2']))
    story.append(Spacer(1, 10))
    
    mc_questions = [
        {
            "question": "1. What is the acceleration due to gravity on Earth?",
            "choices": ["A) 9.8 m/s²", "B) 10.2 m/s²", "C) 8.9 m/s²", "D) 9.6 m/s²"]
        },
        {
            "question": "2. Which element has the atomic number 6?",
            "choices": ["A) Oxygen", "B) Carbon", "C) Nitrogen", "D) Boron"]
        },
        {
            "question": "3. What is the formula for calculating kinetic energy?",
            "choices": ["A) KE = mv", "B) KE = ½mv²", "C) KE = m²v", "D) KE = mv²"]
        }
    ]
    
    for q_data in mc_questions:
        story.append(Paragraph(q_data["question"], styles['Normal']))
        for choice in q_data["choices"]:
            story.append(Paragraph(choice, styles['Normal']))
        story.append(Spacer(1, 10))
    
    # Section B: Short Answer
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Section B: Short Answer (30 points)</b>", styles['Heading2']))
    story.append(Spacer(1, 10))
    
    short_questions = [
        "4. Explain Newton's First Law of Motion.",
        "5. Balance the chemical equation: H₂ + O₂ → H₂O",
        "6. Calculate the molarity of a solution containing 5.85g of NaCl in 500mL of water."
    ]
    
    for question in short_questions:
        story.append(Paragraph(question, styles['Normal']))
        story.append(Spacer(1, 30))  # Space for answers
    
    # Section C: Problem Solving
    story.append(Paragraph("<b>Section C: Problem Solving (30 points)</b>", styles['Heading2']))
    story.append(Spacer(1, 10))
    
    problem = """
    7. A car travels at a constant velocity of 25 m/s for 10 seconds, then accelerates 
    at 2 m/s² for 5 seconds. Calculate:
    a) The distance traveled during constant velocity
    b) The final velocity after acceleration
    c) The total distance traveled
    """
    story.append(Paragraph(problem, styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


if __name__ == "__main__":
    # Create sample test PDF
    pdf_content = create_sample_test_pdf()
    with open("sample_test.pdf", "wb") as f:
        f.write(pdf_content)
    print("Created sample_test.pdf")
    
    # Create complex test PDF
    complex_pdf_content = create_complex_test_pdf()
    with open("complex_test.pdf", "wb") as f:
        f.write(complex_pdf_content)
    print("Created complex_test.pdf")