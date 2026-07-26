import collections
import collections.abc
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

def create_presentation():
    prs = Presentation()
    # Use blank slide layout for all to have full control
    blank_layout = prs.slide_layouts[6] 

    # ----- Slide 1: Title Page -----
    slide1 = prs.slides.add_slide(blank_layout)
    
    # Title
    txBox = slide1.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(1))
    tf = txBox.text_frame
    p = tf.add_paragraph()
    p.text = "@SIH Idea submission- Template\nTITLE PAGE"
    p.font.bold = True
    p.font.size = Pt(28)
    
    # Content
    contentBox = slide1.shapes.add_textbox(Inches(1), Inches(2.5), Inches(8), Inches(4))
    tf2 = contentBox.text_frame
    tf2.word_wrap = True
    points = [
        "• Problem Statement ID: SIH-XXXX",
        "• Problem Statement Title: AI-Powered Behavioral Anomaly Detection for Cybersecurity",
        "• Theme: Cybersecurity & Smart Automation",
        "• PS Category- Software/Hardware: Software",
        "• Student Name (Registered on portal): Atharv Sinha",
        "• Student ID: XXXXXXXXX"
    ]
    for point in points:
        p = tf2.add_paragraph()
        p.text = point
        p.font.size = Pt(20)

    # ----- Slide 2: Proposed Solution -----
    slide2 = prs.slides.add_slide(blank_layout)
    txBox = slide2.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(1))
    tf = txBox.text_frame
    p = tf.add_paragraph()
    p.text = "@SIH Idea submission- Template\nAI-Driven Behavioral Anomaly Detection"
    p.font.bold = True
    p.font.size = Pt(24)

    contentBox = slide2.shapes.add_textbox(Inches(0.5), Inches(1.8), Inches(9), Inches(5))
    tf2 = contentBox.text_frame
    tf2.word_wrap = True
    points = [
        "Proposed Solution (Describe your Idea/Solution/Prototype)",
        "• Detailed explanation of the proposed solution:",
        "  - ML system that learns normal behavior patterns of users, service accounts & IoT devices.",
        "  - Automatically detects 8 attack types including brute force, lateral movement, credential stuffing, etc.",
        "  - Real-time dashboard with live threat feed, risk scoring, and alert queue.",
        "",
        "• How it addresses the problem:",
        "  - Traditional SIEM tools use static rules; our system uses behavioral baselines + ML.",
        "  - Reduces alert fatigue: AI classifies and prioritizes threats by risk score.",
        "",
        "• Innovation and uniqueness of the solution:",
        "  - Dual-model architecture: Isolation Forest (unsupervised) + Random Forest (supervised).",
        "  - Explainability engine: Heuristic feature attribution generates natural-language risk summaries.",
        "  - 97.45% classification accuracy on 8 distinct attack patterns."
    ]
    for i, point in enumerate(points):
        p = tf2.add_paragraph()
        p.text = point
        if i == 0 or point.startswith("•"):
            p.font.bold = True
        p.font.size = Pt(16)


    # ----- Slide 3: Technical Approach -----
    slide3 = prs.slides.add_slide(blank_layout)
    txBox = slide3.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(1))
    tf = txBox.text_frame
    p = tf.add_paragraph()
    p.text = "@SIH Idea submission- Template\nTECHNICAL APPROACH"
    p.font.bold = True
    p.font.size = Pt(24)

    contentBox = slide3.shapes.add_textbox(Inches(0.5), Inches(1.8), Inches(9), Inches(5))
    tf2 = contentBox.text_frame
    tf2.word_wrap = True
    points = [
        "• Technologies to be used (programming languages, frameworks, hardware):",
        "  - Python 3.12, scikit-learn, Pandas, NumPy.",
        "  - UI/Frontend: Plotly, Dash, Flask.",
        "  - ML Models: Isolation Forest (unsupervised baseline), Random Forest (classifier).",
        "  - Hardware: Standard Server / Laptop (MVP runs entirely locally with low footprint).",
        "",
        "• Methodology and process for implementation:",
        "  1. Data Generator: Simulates real-time network access logs (48,700 events).",
        "  2. Baseline Profiler (Isolation Forest): Learns 'normal' entity behavior.",
        "  3. Anomaly Classifier (Random Forest): Identifies and classifies attacks.",
        "  4. Risk Engine: Generates human-readable explainability strings and risk scores.",
        "  5. SOC Dashboard: Visualizes real-time metrics, geographical hotspots, and live alerts."
    ]
    for i, point in enumerate(points):
        p = tf2.add_paragraph()
        p.text = point
        if point.startswith("•"):
            p.font.bold = True
        p.font.size = Pt(16)


    # ----- Slide 4: Feasibility and Viability -----
    slide4 = prs.slides.add_slide(blank_layout)
    txBox = slide4.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(1))
    tf = txBox.text_frame
    p = tf.add_paragraph()
    p.text = "@SIH Idea submission- Template\nFEASIBILITY AND VIABILITY"
    p.font.bold = True
    p.font.size = Pt(24)

    contentBox = slide4.shapes.add_textbox(Inches(0.5), Inches(1.8), Inches(9), Inches(5))
    tf2 = contentBox.text_frame
    tf2.word_wrap = True
    points = [
        "• Analysis of the feasibility of the idea:",
        "  - Built with open-source Python ecosystem — zero licensing costs.",
        "  - Highly scalable: Training pipeline completes in <30 seconds for 48K events.",
        "  - Drop-in architecture allows seamless integration into existing SIEMs via API.",
        "",
        "• Potential challenges and risks:",
        "  - Data drift: Attack patterns evolve, making models stale.",
        "  - False positives: Over-sensitive models can cause alert fatigue in SOCs.",
        "  - Privacy: Processing access logs containing PII (GDPR compliance).",
        "",
        "• Strategies for overcoming these challenges:",
        "  - Continuous retraining schedules to refresh baselines dynamically.",
        "  - Adaptive per-entity risk thresholds to reduce false positives by up to 40%.",
        "  - Data anonymization (hashing PII fields) before ingestion into ML pipeline."
    ]
    for i, point in enumerate(points):
        p = tf2.add_paragraph()
        p.text = point
        if point.startswith("•"):
            p.font.bold = True
        p.font.size = Pt(16)


    # ----- Slide 5: Artifacts -----
    slide5 = prs.slides.add_slide(blank_layout)
    txBox = slide5.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(9), Inches(0.8))
    tf = txBox.text_frame
    p = tf.add_paragraph()
    p.text = "@SIH Idea submission- Template\nARTIFACTS"
    p.font.bold = True
    p.font.size = Pt(24)

    contentBox = slide5.shapes.add_textbox(Inches(0.5), Inches(1.0), Inches(9), Inches(1.5))
    tf2 = contentBox.text_frame
    tf2.word_wrap = True
    points = [
        "• Relevant artifacts:",
        "  - Copy of the Code / GitHub: github.com/AtharvSinha26052005/honeywell_AI_Anomoly_Detection",
        "  - Performance: 48,700 Events Generated, 97.45% Accuracy, 4,508 Anomalies Detected",
        "  - Dashboard snaps (Below): Real-time threat feed, Heatmaps, Entity analytics."
    ]
    for point in points:
        p = tf2.add_paragraph()
        p.text = point
        p.font.size = Pt(14)
        if point.startswith("•"): p.font.bold = True

    # Add images
    try:
        slide5.shapes.add_picture("dashboard_top.png", Inches(0.5), Inches(2.5), height=Inches(2.2))
        slide5.shapes.add_picture("dashboard_middle.png", Inches(5.0), Inches(2.5), height=Inches(2.2))
        slide5.shapes.add_picture("dashboard_bottom.png", Inches(2.5), Inches(4.8), height=Inches(2.2))
    except Exception as e:
        print("Warning: Images not found or error adding images:", e)


    # ----- Slide 6: Research and References -----
    slide6 = prs.slides.add_slide(blank_layout)
    txBox = slide6.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(1))
    tf = txBox.text_frame
    p = tf.add_paragraph()
    p.text = "@SIH Idea submission- Template\nRESEARCH AND REFERENCES"
    p.font.bold = True
    p.font.size = Pt(24)

    contentBox = slide6.shapes.add_textbox(Inches(0.5), Inches(1.8), Inches(9), Inches(5))
    tf2 = contentBox.text_frame
    tf2.word_wrap = True
    points = [
        "• Details / Links of the reference and research work:",
        "  - Liu et al., 2008 — \"Isolation Forest\" — IEEE International Conference on Data Mining.",
        "  - Breiman, 2001 — \"Random Forests\" — Machine Learning, 45(1).",
        "  - MITRE ATT&CK Framework: Used for attack pattern taxonomy mapping.",
        "  - NIST SP 800-53: Security and Privacy Controls for Information Systems.",
        "  - Chandola et al., 2009 — \"Anomaly Detection: A Survey\" — ACM Computing Surveys.",
        "",
        "• Technical Frameworks:",
        "  - scikit-learn (scikit-learn.org) for underlying machine learning logic.",
        "  - Plotly Dash (dash.plotly.com) for real-time dashboard capabilities.",
        "  - Pandas (pandas.pydata.org) for vectorized data transformations.",
        "",
        "Thank you! - AI-Powered Behavioral Anomaly Detection for Cybersecurity"
    ]
    for i, point in enumerate(points):
        p = tf2.add_paragraph()
        p.text = point
        if point.startswith("•"):
            p.font.bold = True
        p.font.size = Pt(16)


    # Save presentation
    prs.save("presentation.pptx")
    print("Successfully generated presentation.pptx")

if __name__ == "__main__":
    create_presentation()
