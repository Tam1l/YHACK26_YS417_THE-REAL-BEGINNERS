import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor

def build_presentation(output_path="RoboNexus_Hackathon_Pitch_Deck.pptx"):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Color Palette
    COLOR_RED_PRIMARY = RGBColor(185, 28, 28)     # Deep Crimson #B91C1C
    COLOR_RED_ACCENT = RGBColor(220, 38, 38)      # Bright Red #DC2626
    COLOR_RED_BG = RGBColor(254, 242, 242)        # Light Red Tint #FEF2F2
    COLOR_BLUE_PRIMARY = RGBColor(29, 78, 216)    # Deep Blue #1D4ED8
    COLOR_BLUE_ACCENT = RGBColor(37, 99, 235)     # Vibrant Blue #2563EB
    COLOR_BLUE_BG = RGBColor(239, 246, 255)       # Light Blue Tint #EFF6FF
    COLOR_DARK_TEXT = RGBColor(15, 23, 42)        # Slate 900 #0F172A
    COLOR_BODY_TEXT = RGBColor(51, 65, 85)        # Slate 700 #334155
    COLOR_MUTED_TEXT = RGBColor(100, 116, 139)    # Slate 500 #64748B
    COLOR_CARD_BG = RGBColor(248, 250, 252)       # Slate 50 #F8FAFC
    COLOR_CARD_BORDER = RGBColor(203, 213, 225)   # Slate 300 #CBD5E1
    COLOR_WHITE = RGBColor(255, 255, 255)
    COLOR_GREEN = RGBColor(22, 101, 52)           # Forest Green
    COLOR_GREEN_BG = RGBColor(240, 253, 244)
    COLOR_AMBER = RGBColor(180, 83, 9)            # Dark Amber
    COLOR_AMBER_BG = RGBColor(254, 252, 232)

    HEADER_PATH = "assets/slides/header_banner.png"
    ROBOT1_PATH = "assets/slides/robot_slide1.png"
    ROBOT10_PATH = "assets/slides/robot_slide10.png"

    def add_common_header(slide):
        if os.path.exists(HEADER_PATH):
            slide.shapes.add_picture(HEADER_PATH, Inches(0), Inches(0), width=Inches(13.333), height=Inches(1.23))

    def add_badge(slide, text, width=3.3):
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(0.6), Inches(1.36), Inches(width), Inches(0.42)
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = COLOR_RED_PRIMARY
        shape.line.color.rgb = COLOR_RED_ACCENT
        shape.line.width = Pt(1)
        tf = shape.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = text.upper()
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE
        p.alignment = PP_ALIGN.CENTER
        return shape

    def add_title(slide, headline, subheadline=None, top=1.85):
        tb = slide.shapes.add_textbox(Inches(0.6), Inches(top), Inches(12.133), Inches(0.8))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = headline
        p.font.size = Pt(20)
        p.font.bold = True
        p.font.color.rgb = COLOR_DARK_TEXT
        
        if subheadline:
            p2 = tf.add_paragraph()
            p2.text = subheadline
            p2.font.size = Pt(13)
            p2.font.color.rgb = COLOR_BODY_TEXT
            p2.space_before = Pt(3)

    def add_bottom_banner(slide, text):
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(0.8), Inches(6.7), Inches(11.733), Inches(0.45)
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = COLOR_RED_PRIMARY
        shape.line.color.rgb = COLOR_RED_ACCENT
        shape.line.width = Pt(1.5)
        tf = shape.text_frame
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.text = text
        p.font.size = Pt(12.5)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE
        p.alignment = PP_ALIGN.CENTER

    # ==========================================
    # SLIDE 1: TITLE SLIDE
    # ==========================================
    s1 = prs.slides.add_slide(blank_layout)
    add_common_header(s1)

    # Robot image on right
    if os.path.exists(ROBOT1_PATH):
        s1.shapes.add_picture(ROBOT1_PATH, Inches(9.8), Inches(1.3), width=Inches(3.3))

    # Left content box
    tb1 = s1.shapes.add_textbox(Inches(0.8), Inches(1.65), Inches(8.8), Inches(5.2))
    tf1 = tb1.text_frame
    tf1.word_wrap = True

    p = tf1.paragraphs[0]
    p.text = "TITLE: Robotics-Aware Private AI Cloud"
    p.font.size = Pt(25)
    p.font.bold = True
    p.font.color.rgb = COLOR_DARK_TEXT

    p_sub = tf1.add_paragraph()
    p_sub.text = "RoboNexus: Low-Latency, Edge-Orchestrated AI Infrastructure for Autonomous Industrial Fleets"
    p_sub.font.size = Pt(13.5)
    p_sub.font.color.rgb = COLOR_RED_PRIMARY
    p_sub.font.bold = True
    p_sub.space_before = Pt(6)
    p_sub.space_after = Pt(20)

    meta_items = [
        ("TEAM NAME:", "The Real Beginners"),
        ("TEAM ID:", "YS417"),
        ("PS ID :", "13"),
        ("DOMAIN :", "Cloud Robotics & Autonomous Systems"),
        ("TEAM LEADER NAME:", "HARISH R"),
        ("MEMBER-1 NAME:", "TAMIL SELVAN P"),
        ("MEMBER-2 NAME:", "SRI KRISHNA R"),
        ("MEMBER-3 NAME:", "SANKAR S R"),
        ("MEMBER-4 NAME:", ""),
        ("MEMBER-5 NAME:", ""),
    ]

    for label, val in meta_items:
        p_m = tf1.add_paragraph()
        run_lbl = p_m.add_run()
        run_lbl.text = f"{label} "
        run_lbl.font.bold = True
        run_lbl.font.size = Pt(13.5)
        run_lbl.font.color.rgb = COLOR_RED_PRIMARY

        run_val = p_m.add_run()
        run_val.text = val
        run_val.font.bold = True
        run_val.font.size = Pt(13.5)
        run_val.font.color.rgb = COLOR_DARK_TEXT
        p_m.space_before = Pt(2)

    # Decorative bottom stripes
    for i in range(4):
        stripe = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5 + i*0.25), Inches(7.1), Inches(0.15), Inches(0.2))
        stripe.fill.solid()
        stripe.fill.fore_color.rgb = COLOR_RED_PRIMARY
        stripe.line.fill.background()

    # ==========================================
    # SLIDE 2: PROBLEM STATEMENT
    # ==========================================
    s2 = prs.slides.add_slide(blank_layout)
    add_common_header(s2)
    add_badge(s2, "PROBLEM STATEMENT", width=3.2)
    add_title(s2, "Industrial robots need cloud-level AI without public-cloud delay or data exposure.")

    # Left Column: 4 Pain Points
    left_tb2 = s2.shapes.add_textbox(Inches(0.6), Inches(2.6), Inches(7.4), Inches(3.8))
    tf2 = left_tb2.text_frame
    tf2.word_wrap = True

    bullets = [
        ("Onboard Compute Bottleneck: ", "Heavy neural networks on robots increase BOM cost ($1,500+/unit), cause thermal throttling, and drain mobile battery 40% faster."),
        ("Public Cloud Infeasibility: ", "Offloading to public cloud adds 120ms+ latency, unpredictable network jitter, internet outage vulnerability, and intellectual property exposure."),
        ("Queue Contention & Starvation: ", "When multiple robots flood compute simultaneously, standard FIFO queues block critical safety tasks behind routine low-priority workloads."),
        ("Safety-Critical Deadlines: ", "Hazard avoidance (e.g., human collision detection) requires guaranteed sub-50ms inference. Missing deadlines violates ISO 3691-4 industrial safety standards.")
    ]

    for i, (title, desc) in enumerate(bullets):
        p = tf2.paragraphs[0] if i == 0 else tf2.add_paragraph()
        run_bullet = p.add_run()
        run_bullet.text = "• "
        run_bullet.font.bold = True
        run_bullet.font.size = Pt(13)
        run_bullet.font.color.rgb = COLOR_RED_PRIMARY

        run_title = p.add_run()
        run_title.text = title
        run_title.font.bold = True
        run_title.font.size = Pt(12.5)
        run_title.font.color.rgb = COLOR_DARK_TEXT

        run_desc = p.add_run()
        run_desc.text = desc
        run_desc.font.size = Pt(12)
        run_desc.font.color.rgb = COLOR_BODY_TEXT
        p.space_after = Pt(10)

    # Right Column: 2 Cards
    # Card 1: Core Challenge
    card1 = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.3), Inches(2.6), Inches(4.4), Inches(1.8))
    card1.fill.solid()
    card1.fill.fore_color.rgb = COLOR_RED_BG
    card1.line.color.rgb = COLOR_RED_ACCENT
    card1.line.width = Pt(1.5)
    tf_c1 = card1.text_frame
    tf_c1.word_wrap = True
    p1 = tf_c1.paragraphs[0]
    p1.text = "Core Challenge"
    p1.font.size = Pt(14)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_RED_PRIMARY
    p1.space_after = Pt(4)
    p2 = tf_c1.add_paragraph()
    p2.text = "Securely process heterogeneous robot AI requests with deterministic sub-50ms latency while guaranteeing zero task drops during worker failures or bandwidth congestion."
    p2.font.size = Pt(11.5)
    p2.font.color.rgb = COLOR_BODY_TEXT

    # Card 2: Target Use Cases
    card2 = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.3), Inches(4.6), Inches(4.4), Inches(1.8))
    card2.fill.solid()
    card2.fill.fore_color.rgb = COLOR_BLUE_BG
    card2.line.color.rgb = COLOR_BLUE_ACCENT
    card2.line.width = Pt(1.5)
    tf_c2 = card2.text_frame
    tf_c2.word_wrap = True
    p1 = tf_c2.paragraphs[0]
    p1.text = "Target Use Cases"
    p1.font.size = Pt(14)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_BLUE_PRIMARY
    p1.space_after = Pt(4)
    p2 = tf_c2.add_paragraph()
    p2.text = "• Smart Warehouses & Automated Guided Vehicles (AGVs)\n• Autonomous Mobile Robots (AMRs) in Shared Spaces\n• Aerial Industrial Inspection Drones & Facility Sweepers\n• High-Precision Manufacturing & Robotic Arm Cells"
    p2.font.size = Pt(11.5)
    p2.font.color.rgb = COLOR_BODY_TEXT

    add_bottom_banner(s2, "Objective: Guarantee safety-critical compute priority with zero cloud egress & deterministic SLA")

    # ==========================================
    # SLIDE 3: PROPOSED SOLUTION
    # ==========================================
    s3 = prs.slides.add_slide(blank_layout)
    add_common_header(s3)
    add_badge(s3, "PROPOSED SOLUTION", width=3.2)
    add_title(s3, "RoboNexus Private AI Cloud", "A private, on-premise AI orchestration platform where heterogeneous robot fleets securely offload vision and inference tasks to local, prioritized edge workers.")

    # 5-Stage Process Flow Diagram
    flow_steps = [
        ("🤖 Robot Fleets", "AGVs • Drones • Sweepers\nReal-time JPEG + Telemetry"),
        ("🛡️ Secure Gateway", "FastAPI Token Auth\nNon-blocking Async Ingress"),
        ("⚡ RADS Scheduler", "Risk-Aware Priority Scoring\nRedis Sorted Sets (ZSET)"),
        ("🧠 Elastic AI Workers", "Ultralytics YOLOv8\nParallel Concurrency Pool"),
        ("📊 Mission Control & S3", "2D Digital Twin Canvas\nISO 3691-4 Black-Box Logs")
    ]

    box_w = 2.2
    gap = 0.22
    start_x = 0.65
    y_pos = 2.85

    for i, (title, sub) in enumerate(flow_steps):
        x = start_x + i * (box_w + gap)
        box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y_pos), Inches(box_w), Inches(1.35))
        box.fill.solid()
        box.fill.fore_color.rgb = COLOR_CARD_BG
        box.line.color.rgb = COLOR_RED_ACCENT if i == 2 else (COLOR_BLUE_ACCENT if i in [0, 1] else COLOR_CARD_BORDER)
        box.line.width = Pt(1.5 if i == 2 else 1)
        tf_b = box.text_frame
        tf_b.word_wrap = True
        p = tf_b.paragraphs[0]
        p.text = title
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = COLOR_RED_PRIMARY if i == 2 else COLOR_DARK_TEXT
        p.alignment = PP_ALIGN.CENTER
        p.space_after = Pt(2)
        p2 = tf_b.add_paragraph()
        p2.text = sub
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = COLOR_BODY_TEXT
        p2.alignment = PP_ALIGN.CENTER

        # Add connecting arrow
        if i < len(flow_steps) - 1:
            arr = s3.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x + box_w + 0.03), Inches(y_pos + 0.5), Inches(0.16), Inches(0.25))
            arr.fill.solid()
            arr.fill.fore_color.rgb = COLOR_RED_PRIMARY
            arr.line.fill.background()

    # 4 Bottom Feature Cards
    features = [
        ("Shared Private AI Compute", "Centralized on-premise GPU/CPU workers slash individual robot hardware costs by 60% and conserve onboard battery."),
        ("RADS Dynamic Pre-emption", "Safety-critical human collision tasks instantly leapfrog low-priority routine frames in the queue."),
        ("Fault-Tolerant Worker Leasing", "Continuous heartbeat monitoring with 5s TTL guarantees orphaned tasks are auto-reassigned without frame loss."),
        ("ISO 3691-4 Archiving", "Full black-box forensic telemetry uploaded to local S3/MinIO for audit trails and safety certification.")
    ]

    for j, (ftitle, fdesc) in enumerate(features):
        col_w = 2.82
        col_x = 0.65 + j * (col_w + 0.22)
        f_card = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(col_x), Inches(4.5), Inches(col_w), Inches(1.9))
        f_card.fill.solid()
        f_card.fill.fore_color.rgb = COLOR_WHITE
        f_card.line.color.rgb = COLOR_CARD_BORDER
        f_card.line.width = Pt(1)
        tf_f = f_card.text_frame
        tf_f.word_wrap = True
        p = tf_f.paragraphs[0]
        p.text = ftitle
        p.font.size = Pt(11.5)
        p.font.bold = True
        p.font.color.rgb = COLOR_RED_PRIMARY
        p.space_after = Pt(3)
        p2 = tf_f.add_paragraph()
        p2.text = fdesc
        p2.font.size = Pt(10)
        p2.font.color.rgb = COLOR_BODY_TEXT

    add_bottom_banner(s3, "Key Outcome: Deterministic sub-50ms safety inference + 100% private on-premise fleet control")

    # ==========================================
    # SLIDE 4: OBJECTIVE
    # ==========================================
    s4 = prs.slides.add_slide(blank_layout)
    add_common_header(s4)
    add_badge(s4, "OBJECTIVE", width=3.2)
    add_title(s4, "Engineering Objectives", "Enable autonomous robot fleets to access AI securely and deterministically via private cloud, maintaining ultra-low latency, priority guarantees, and fault tolerance.")

    pillars = [
        ("Security & Privacy", COLOR_RED_PRIMARY, COLOR_RED_BG, COLOR_RED_ACCENT, [
            ("Zero Cloud Egress", "All video streams & telemetry stay air-gapped on-premise."),
            ("Tokenized Auth", "Per-robot bearer tokens validate every frame at the gateway."),
            ("Tamper-Proof Audit", "Forensic S3 black-box logs comply with ISO 3691-4 safety laws.")
        ]),
        ("Deterministic Latency", COLOR_BLUE_PRIMARY, COLOR_BLUE_BG, COLOR_BLUE_ACCENT, [
            ("Local LAN Routing", "Replaces 120ms internet roundtrip with sub-5ms network ping."),
            ("Pre-warmed AI Models", "Zero cold-start delay for Ultralytics YOLOv8 inference."),
            ("Sub-50ms Total SLA", "Capture-to-actuation cycle meets emergency braking limits.")
        ]),
        ("RADS Scheduling", COLOR_AMBER, COLOR_AMBER_BG, COLOR_AMBER, [
            ("Risk-Driven Priority", "Scores compute based on robot speed, proximity & deadline."),
            ("Leapfrog Dispatch", "Emergency obstacle frames jump ahead of 100+ routine tasks."),
            ("Fleet SLA Tiers", "Guaranteed bandwidth quotas for AGVs vs Drones vs Sweepers.")
        ]),
        ("High Availability", COLOR_GREEN, COLOR_GREEN_BG, COLOR_GREEN, [
            ("Heartbeat Leasing", "Active workers refresh 5s TTL lease; dead nodes detected instantly."),
            ("Zero Frame Drop", "Unacknowledged frames immediately re-enqueued at index 0."),
            ("KEDA Autoscaling", "Dynamically scales worker replicas from queue backlog metrics.")
        ])
    ]

    for k, (p_title, p_color, p_bg, p_border, p_points) in enumerate(pillars):
        px = 0.65 + k * (2.82 + 0.22)
        p_box = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(px), Inches(2.75), Inches(2.82), Inches(3.65))
        p_box.fill.solid()
        p_box.fill.fore_color.rgb = p_bg
        p_box.line.color.rgb = p_border
        p_box.line.width = Pt(1.5)
        tf_p = p_box.text_frame
        tf_p.word_wrap = True
        
        p = tf_p.paragraphs[0]
        p.text = p_title
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = p_color
        p.space_after = Pt(10)

        for pt_title, pt_desc in p_points:
            p_item = tf_p.add_paragraph()
            run_b = p_item.add_run()
            run_b.text = "✓ "
            run_b.font.bold = True
            run_b.font.color.rgb = p_color
            run_b.font.size = Pt(11)

            run_t = p_item.add_run()
            run_t.text = f"{pt_title}: "
            run_t.font.bold = True
            run_t.font.size = Pt(11)
            run_t.font.color.rgb = COLOR_DARK_TEXT

            run_d = p_item.add_run()
            run_d.text = pt_desc
            run_d.font.size = Pt(10.5)
            run_d.font.color.rgb = COLOR_BODY_TEXT
            p_item.space_after = Pt(6)

    add_bottom_banner(s4, "Success Metric: Safety-critical robot requests get compute first under 300% resource congestion")

    # ==========================================
    # SLIDE 5: METHODOLOGY
    # ==========================================
    s5 = prs.slides.add_slide(blank_layout)
    add_common_header(s5)
    add_badge(s5, "METHODOLOGY", width=3.2)
    add_title(s5, "System Methodology & Technical Pipeline", "Five-tier architectural methodology engineered for high-concurrency, low-latency industrial robotic fleets.")

    methods = [
        ("Fleet Simulation & Ingress", "Multi-threaded client generator simulates heterogeneous robots (AGV-01, Drone-02, Sweeper-03) streaming camera frames with dynamic velocity, battery levels, and deadline metadata."),
        ("Secure High-Throughput Gateway", "FastAPI non-blocking asynchronous gateway authenticates robot bearer tokens, unpacks JSON/Protobuf payloads, and ingests tasks into memory in sub-millisecond time."),
        ("RADS Mathematical Scheduling", "Dynamic scoring algorithm evaluates hazard criticality, deadline deficit, queue wait time, and tenant SLA weights, pushing tasks into Redis Sorted Sets (ZSET) with O(log N) efficiency."),
        ("Distributed AI Worker Execution", "Concurrent worker pool leases high-priority tasks, executes pre-warmed YOLOv8 object detection, generates bounding boxes & hazard flags, and publishes results via Redis Pub/Sub."),
        ("Mission Control & S3 Incident Recovery", "Streamlit dashboard displays a 2D Warehouse Digital Twin, live queue latency gauges, and worker kill-switches, while near-miss frames are archived to local S3 for ISO 3691-4 safety audits.")
    ]

    for m_idx, (m_title, m_desc) in enumerate(methods):
        y = 2.75 + m_idx * 0.74
        # Number badge
        num_box = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.65), Inches(y), Inches(0.48), Inches(0.48))
        num_box.fill.solid()
        num_box.fill.fore_color.rgb = COLOR_RED_PRIMARY
        num_box.line.fill.background()
        tf_n = num_box.text_frame
        p_n = tf_n.paragraphs[0]
        p_n.text = str(m_idx + 1)
        p_n.font.size = Pt(14)
        p_n.font.bold = True
        p_n.font.color.rgb = COLOR_WHITE
        p_n.alignment = PP_ALIGN.CENTER

        # Content Card
        row_card = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.3), Inches(y), Inches(11.38), Inches(0.58))
        row_card.fill.solid()
        row_card.fill.fore_color.rgb = COLOR_CARD_BG
        row_card.line.color.rgb = COLOR_CARD_BORDER
        row_card.line.width = Pt(1)
        tf_r = row_card.text_frame
        tf_r.word_wrap = True
        p_r = tf_r.paragraphs[0]
        
        tf_r.margin_left = Inches(0.2)
        tf_r.margin_right = Inches(0.2)
        p_r.alignment = PP_ALIGN.LEFT
        run_t = p_r.add_run()
        run_t.text = f"{m_title}: "
        run_t.font.bold = True
        run_t.font.size = Pt(11.5)
        run_t.font.color.rgb = COLOR_RED_PRIMARY

        run_d = p_r.add_run()
        run_d.text = m_desc
        run_d.font.size = Pt(10.5)
        run_d.font.color.rgb = COLOR_BODY_TEXT

    add_bottom_banner(s5, "Architecture Advantage: Decoupled microservices architecture enables linear scale to 100,000+ robots")

    # ==========================================
    # SLIDE 6: WORKFLOW
    # ==========================================
    s6 = prs.slides.add_slide(blank_layout)
    add_common_header(s6)
    add_badge(s6, "WORKFLOW", width=3.2)
    add_title(s6, "End-to-End Operational Workflow", "Step-by-step frame lifecycle from robotic camera capture to safety actuation and ISO-compliant archiving.")

    # 6 Steps in horizontal flow
    steps6 = [
        ("1. Robot Request", "Camera captures frame;\ntags velocity & deadline"),
        ("2. Gateway Ingress", "Validates bearer token;\nparses payload in <2ms"),
        ("3. RADS Scoring", "Computes risk score;\nevaluates hazard level"),
        ("4. Priority Queue", "Redis ZSET sorts score;\nurgent task jumps index"),
        ("5. Worker Inference", "YOLOv8 detects objects;\nextracts human hazards"),
        ("6. Actuate & Archive", "Returns brake signal;\nlogs audit trail to S3")
    ]

    w6 = 1.8
    gap6 = 0.22
    for s_idx, (stitle, sdesc) in enumerate(steps6):
        sx = 0.65 + s_idx * (w6 + gap6)
        sbox = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(sx), Inches(2.7), Inches(w6), Inches(1.3))
        sbox.fill.solid()
        sbox.fill.fore_color.rgb = COLOR_RED_BG if s_idx in [2, 3] else COLOR_CARD_BG
        sbox.line.color.rgb = COLOR_RED_ACCENT if s_idx in [2, 3] else COLOR_BLUE_ACCENT
        sbox.line.width = Pt(1.5 if s_idx in [2, 3] else 1)
        tf_s = sbox.text_frame
        tf_s.word_wrap = True
        p = tf_s.paragraphs[0]
        p.text = stitle
        p.font.size = Pt(11.5)
        p.font.bold = True
        p.font.color.rgb = COLOR_RED_PRIMARY if s_idx in [2, 3] else COLOR_DARK_TEXT
        p.alignment = PP_ALIGN.CENTER
        p.space_after = Pt(2)
        p2 = tf_s.add_paragraph()
        p2.text = sdesc
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = COLOR_BODY_TEXT
        p2.alignment = PP_ALIGN.CENTER

        if s_idx < len(steps6) - 1:
            arr = s6.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(sx + w6 + 0.04), Inches(2.7 + 0.45), Inches(0.14), Inches(0.22))
            arr.fill.solid()
            arr.fill.fore_color.rgb = COLOR_RED_PRIMARY
            arr.line.fill.background()

    # Demo Highlight Card
    demo_box = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.65), Inches(4.3), Inches(12.03), Inches(2.1))
    demo_box.fill.solid()
    demo_box.fill.fore_color.rgb = COLOR_WHITE
    demo_box.line.color.rgb = COLOR_RED_ACCENT
    demo_box.line.width = Pt(1.5)
    tf_d = demo_box.text_frame
    tf_d.word_wrap = True

    p = tf_d.paragraphs[0]
    p.text = "Live Industrial Edge Scenario: Dynamic Queue Pre-emption"
    p.font.size = Pt(13.5)
    p.font.bold = True
    p.font.color.rgb = COLOR_RED_PRIMARY
    p.space_after = Pt(6)

    demo_bullets = [
        ("Background Congestion: ", "Robots flood queue with 40 low-priority inspection frames (Floor Cleaning Sweeper, Barcode Drones; deadline = 3,000ms, Score = 15-25)."),
        ("Safety-Critical Arrival: ", "Autonomous AGV-01 detects a warehouse worker crossing blind corner at 3.5 m/s (Human Hazard = 1.0, deadline = 120ms)."),
        ("Instant Queue Re-order: ", "RADS engine evaluates parameters in 0.4ms, generates Score = 98.6, and pushes task directly to index #0 ahead of all 40 queued frames."),
        ("Deterministic Safety Response: ", "Worker executes YOLOv8 detection in 22ms, identifies pedestrian with 92% confidence, and returns immediate E-STOP command to AGV.")
    ]

    tf_d.margin_left = Inches(0.3)
    tf_d.margin_right = Inches(0.3)
    for d_title, d_desc in demo_bullets:
        p_d = tf_d.add_paragraph()
        p_d.alignment = PP_ALIGN.LEFT
        run_b = p_d.add_run()
        run_b.text = "⚡ "
        run_b.font.size = Pt(11)
        run_b.font.color.rgb = COLOR_RED_PRIMARY

        run_t = p_d.add_run()
        run_t.text = d_title
        run_t.font.bold = True
        run_t.font.size = Pt(11)
        run_t.font.color.rgb = COLOR_DARK_TEXT

        run_d = p_d.add_run()
        run_d.text = d_desc
        run_d.font.size = Pt(10.5)
        run_d.font.color.rgb = COLOR_BODY_TEXT
        p_d.space_after = Pt(2)

    add_bottom_banner(s6, "Normal Load → Critical Request Arrival → RADS Queue Re-order → Sub-50ms Low-Latency Safety Actuation")

    # ==========================================
    # SLIDE 7: SYSTEM ARCHITECTURE
    # ==========================================
    s7 = prs.slides.add_slide(blank_layout)
    add_common_header(s7)
    add_badge(s7, "SYSTEM ARCHITECTURE", width=3.4)
    add_title(s7, "Decoupled 4-Tier Microservices Architecture", "Zero-dependency on-premise cloud infrastructure designed for horizontal scale and high availability.")

    # 4 Architecture Tier Cards
    tiers = [
        ("Tier 1: Robotic Ingress", COLOR_BLUE_PRIMARY, COLOR_BLUE_BG, [
            "• Heterogeneous fleet: AGVs, Drones, Sweepers",
            "• Multi-tenant protocol: REST & WebSockets",
            "• Protobuf / JSON frame serialization",
            "• Per-robot bearer authentication token"
        ]),
        ("Tier 2: Edge Gateway & RADS", COLOR_RED_PRIMARY, COLOR_RED_BG, [
            "• FastAPI non-blocking async ingress gateway",
            "• RADS Dynamic Priority Evaluation Engine",
            "• Rate-limiting & tenant SLA enforcement",
            "• Prometheus latency & RPS telemetry export"
        ]),
        ("Tier 3: Distributed State & Queue", COLOR_AMBER, COLOR_AMBER_BG, [
            "• Redis 7 in-memory Sorted Sets (ZSET)",
            "• Sub-millisecond atomic queue push & pop",
            "• Worker Heartbeat Registry (5s TTL leases)",
            "• In-flight task lease tracking & dead-letter queue"
        ]),
        ("Tier 4: Compute & Mission Control", COLOR_GREEN, COLOR_GREEN_BG, [
            "• Scalable YOLOv8 object detection worker pool",
            "• KEDA-style queue-lag horizontal autoscaling",
            "• Streamlit 2D Warehouse Digital Twin Dashboard",
            "• Local S3 (MinIO) ISO 3691-4 Black-Box Archiving"
        ])
    ]

    for t_idx, (t_title, t_col, t_bg, t_items) in enumerate(tiers):
        tx = 0.65 + t_idx * (2.82 + 0.22)
        tbox = s7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(tx), Inches(2.75), Inches(2.82), Inches(3.65))
        tbox.fill.solid()
        tbox.fill.fore_color.rgb = t_bg
        tbox.line.color.rgb = t_col
        tbox.line.width = Pt(1.5)
        tf_t = tbox.text_frame
        tf_t.word_wrap = True

        p = tf_t.paragraphs[0]
        p.text = t_title
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = t_col
        p.space_after = Pt(8)

        for item in t_items:
            p_i = tf_t.add_paragraph()
            p_i.text = item
            p_i.font.size = Pt(10.5)
            p_i.font.color.rgb = COLOR_BODY_TEXT
            p_i.space_after = Pt(6)

    add_bottom_banner(s7, "Failure Manager: 5s Heartbeat Miss → Worker Declared Unhealthy → Unfinished Frame Auto-Requeued to Head")

    # ==========================================
    # SLIDE 8: IMPLEMENTATION STACK
    # ==========================================
    s8 = prs.slides.add_slide(blank_layout)
    add_common_header(s8)
    add_badge(s8, "IMPLEMENTATION", width=3.2)
    add_title(s8, "Full-Stack Implementation & Validation Matrix", "Enterprise-grade technology choices validated across edge hardware, network contention, and worker crashes.")

    # Left: Tech Stack Table
    table_shape = s8.shapes.add_table(7, 2, Inches(0.65), Inches(2.7), Inches(6.8), Inches(3.7))
    table = table_shape.table
    table.columns[0].width = Inches(2.2)
    table.columns[1].width = Inches(4.6)

    tech_stack = [
        ("Edge API Gateway", "FastAPI (Asynchronous, Non-blocking REST & WebSockets)"),
        ("In-Memory Queue Fabric", "Redis 7 (Sorted Sets `ZSET` + Atomic Pipelines + PubSub)"),
        ("Computer Vision Core", "Ultralytics YOLOv8 (Pre-warmed PyTorch, TensorRT ready)"),
        ("Priority Scheduling", "RADS Engine (Risk, Deadline, Velocity, SLA Tier Scoring)"),
        ("Mission Control Suite", "Streamlit Real-Time Dashboard + 2D Warehouse Digital Twin"),
        ("Safety Incident Archive", "Local S3 / MinIO (ISO 3691-4 Black-Box Compliance)"),
        ("Deployment & Scaling", "Docker Compose + Kubernetes Manifests + KEDA Autoscaler")
    ]

    for row_idx, (comp, tech) in enumerate(tech_stack):
        cell_comp = table.cell(row_idx, 0)
        cell_comp.fill.solid()
        cell_comp.fill.fore_color.rgb = COLOR_RED_BG if row_idx % 2 == 0 else COLOR_WHITE
        p_c = cell_comp.text_frame.paragraphs[0]
        p_c.text = comp
        p_c.font.bold = True
        p_c.font.size = Pt(11)
        p_c.font.color.rgb = COLOR_RED_PRIMARY

        cell_tech = table.cell(row_idx, 1)
        cell_tech.fill.solid()
        cell_tech.fill.fore_color.rgb = COLOR_CARD_BG if row_idx % 2 == 0 else COLOR_WHITE
        p_t = cell_tech.text_frame.paragraphs[0]
        p_t.text = tech
        p_t.font.size = Pt(10.5)
        p_t.font.color.rgb = COLOR_DARK_TEXT

    # Right: 2 Cards
    # Card 1: Implemented Capabilities
    icard = s8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.75), Inches(2.7), Inches(4.95), Inches(1.8))
    icard.fill.solid()
    icard.fill.fore_color.rgb = COLOR_RED_BG
    icard.line.color.rgb = COLOR_RED_ACCENT
    icard.line.width = Pt(1.5)
    tf_ic = icard.text_frame
    tf_ic.word_wrap = True
    p1 = tf_ic.paragraphs[0]
    p1.text = "Implemented Production Capabilities"
    p1.font.size = Pt(13)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_RED_PRIMARY
    p1.space_after = Pt(3)
    p2 = tf_ic.add_paragraph()
    p2.text = "• Sub-millisecond priority insertion via Redis Sorted Sets\n• Dynamic Multi-Tenant SLA contracts (AGV, Drone, Sweeper)\n• KEDA-style elastic horizontal autoscaling (0 → N workers)\n• Zero frame loss guarantee with automated lease recovery"
    p2.font.size = Pt(10.5)
    p2.font.color.rgb = COLOR_BODY_TEXT

    # Card 2: Live Demo Test Plan
    lcard = s8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.75), Inches(4.6), Inches(4.95), Inches(1.8))
    lcard.fill.solid()
    lcard.fill.fore_color.rgb = COLOR_BLUE_BG
    lcard.line.color.rgb = COLOR_BLUE_ACCENT
    lcard.line.width = Pt(1.5)
    tf_lc = lcard.text_frame
    tf_lc.word_wrap = True
    p1 = tf_lc.paragraphs[0]
    p1.text = "Live Demonstration Scenarios"
    p1.font.size = Pt(13)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_BLUE_PRIMARY
    p1.space_after = Pt(3)
    p2 = tf_lc.add_paragraph()
    p2.text = "1. Multi-Robot Concurrent Stream Storm (50+ RPS Load)\n2. Emergency Human Obstacle Frame Queue Leapfrogging\n3. Worker Crash Kill-Switch & Automatic Task Reassignment\n4. ISO 3691-4 Black-Box Incident Report Export from S3"
    p2.font.size = Pt(10.5)
    p2.font.color.rgb = COLOR_BODY_TEXT

    add_bottom_banner(s8, "Implementation Scope: Fully Decoupled Microservices, Live 2D Digital Twin, Benchmarked under 300% Load")

    # ==========================================
    # SLIDE 9: NOVELTY: RADS SCHEDULER
    # ==========================================
    s9 = prs.slides.add_slide(blank_layout)
    add_common_header(s9)
    add_badge(s9, "IMPLEMENTATION NOVELTY", width=3.8)
    add_title(s9, "Novelty: Robotics-Aware Deadline Scheduler (RADS)", "Traditional FIFO queues treat all frames equally. RADS allocates compute based on physical-world safety consequences.")

    # Mathematical Formula Box
    f_box = s9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.65), Inches(2.7), Inches(12.03), Inches(0.85))
    f_box.fill.solid()
    f_box.fill.fore_color.rgb = COLOR_CARD_BG
    f_box.line.color.rgb = COLOR_RED_PRIMARY
    f_box.line.width = Pt(1.5)
    tf_f = f_box.text_frame
    tf_f.word_wrap = True
    p_f = tf_f.paragraphs[0]
    p_f.text = "Priority Score =  w_c · Hazard_Criticality  +  w_d · (1000 / Deadline_ms)  +  w_w · Wait_Time  +  w_s · Tenant_SLA"
    p_f.font.size = Pt(14)
    p_f.font.bold = True
    p_f.font.color.rgb = COLOR_RED_PRIMARY
    p_f.alignment = PP_ALIGN.CENTER
    p_f2 = tf_f.add_paragraph()
    p_f2.text = "Weights dynamically tuned for industrial robotics: Hazard (45%) • Deadline Urgency (30%) • Wait Time (15%) • Fleet SLA (10%)"
    p_f2.font.size = Pt(10)
    p_f2.font.color.rgb = COLOR_MUTED_TEXT
    p_f2.alignment = PP_ALIGN.CENTER

    # 3 Comparison Columns
    cases = [
        ("Tier 3: Routine Sweeper", COLOR_BLUE_PRIMARY, COLOR_BLUE_BG, COLOR_BLUE_ACCENT, [
            ("Task Type", "Debris & Floor Obstacle Scan"),
            ("Robot Speed", "0.5 m/s (Low Momentum)"),
            ("Deadline Window", "3,500 ms"),
            ("RADS Score", "18.4 (Background Priority)"),
            ("Queue Handling", "Waits for idle compute capacity")
        ]),
        ("Tier 2: Inspection Drone", COLOR_AMBER, COLOR_AMBER_BG, COLOR_AMBER, [
            ("Task Type", "High-Rack Inventory Barcode Scan"),
            ("Robot Speed", "2.0 m/s (Medium Momentum)"),
            ("Deadline Window", "1,000 ms"),
            ("RADS Score", "46.2 (Standard Priority)"),
            ("Queue Handling", "Fair-share round-robin dispatch")
        ]),
        ("Tier 1: Safety-Critical AGV", COLOR_RED_PRIMARY, COLOR_RED_BG, COLOR_RED_ACCENT, [
            ("Task Type", "Pedestrian Collision Risk on Aisle 4"),
            ("Robot Speed", "3.5 m/s (High Momentum AMR)"),
            ("Deadline Window", "120 ms (Braking Threshold)"),
            ("RADS Score", "98.7 (CRITICAL EMERGENCY)"),
            ("Queue Handling", "LEAPFROGS TO INDEX #0 IMMEDIATELY")
        ])
    ]

    for c_idx, (c_title, c_col, c_bg, c_border, c_attrs) in enumerate(cases):
        cx = 0.65 + c_idx * (3.8 + 0.31)
        cbox = s9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(cx), Inches(3.75), Inches(3.8), Inches(2.7))
        cbox.fill.solid()
        cbox.fill.fore_color.rgb = c_bg
        cbox.line.color.rgb = c_border
        cbox.line.width = Pt(2 if c_idx == 2 else 1.2)
        tf_c = cbox.text_frame
        tf_c.word_wrap = True

        p = tf_c.paragraphs[0]
        p.text = c_title
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = c_col
        p.alignment = PP_ALIGN.CENTER
        p.space_after = Pt(6)

        for a_name, a_val in c_attrs:
            p_a = tf_c.add_paragraph()
            run_an = p_a.add_run()
            run_an.text = f"{a_name}: "
            run_an.font.bold = True
            run_an.font.size = Pt(10.5)
            run_an.font.color.rgb = COLOR_DARK_TEXT

            run_av = p_a.add_run()
            run_av.text = a_val
            run_av.font.size = Pt(10.5)
            run_av.font.bold = (c_idx == 2 and a_name == "Queue Handling")
            run_av.font.color.rgb = c_col if (c_idx == 2 and a_name == "Queue Handling") else COLOR_BODY_TEXT
            p_a.space_after = Pt(3)

    add_bottom_banner(s9, "Key Scientific Novelty: AI compute scheduling is directly coupled to physical robot kinetic momentum and collision risk")

    # ==========================================
    # SLIDE 10: EXPECTED DEMO OUTPUT & IMPACT
    # ==========================================
    s10 = prs.slides.add_slide(blank_layout)
    add_common_header(s10)
    add_badge(s10, "LIVE DEMONSTRATION & IMPACT", width=4.2)
    add_title(s10, "Demonstration Output & Judging Strengths", "Live interactive validation of prioritized AI inference, worker failure recovery, and 2D digital twin operations.")

    # Left Robot Image
    if os.path.exists(ROBOT10_PATH):
        s10.shapes.add_picture(ROBOT10_PATH, Inches(0.6), Inches(2.45), width=Inches(2.4))

    # Middle: Demo Verification Bullets
    mid_tb = s10.shapes.add_textbox(Inches(3.2), Inches(2.45), Inches(4.9), Inches(4.0))
    tf_m = mid_tb.text_frame
    tf_m.word_wrap = True

    demo_pts = [
        ("Multi-Robot Concurrent Streams: ", "3+ simulated heterogeneous robots (AGV, Drone, Sweeper) stream frames concurrently without packet drop."),
        ("Instant Queue Leapfrogging: ", "Critical human detection frame visibly jumps to position #1 on live telemetry, bypassing 40+ waiting tasks."),
        ("Live 2D Digital Twin Canvas: ", "Streamlit dashboard displays real-time robot positions, aisle waypoints, and latency radar in real-time."),
        ("Fault-Tolerant Worker Recovery: ", "Simulated worker kill-switch demonstrates instant 5s heartbeat detection and zero-loss frame reassignment."),
        ("ISO 3691-4 S3 Incident Audit: ", "Near-miss event automatically packages telemetry, bounding boxes & JPEG frame into S3 with one-click forensic export.")
    ]

    for i_p, (dtitle, ddesc) in enumerate(demo_pts):
        p = tf_m.paragraphs[0] if i_p == 0 else tf_m.add_paragraph()
        run_b = p.add_run()
        run_b.text = "✓ "
        run_b.font.bold = True
        run_b.font.size = Pt(12)
        run_b.font.color.rgb = COLOR_RED_PRIMARY

        run_t = p.add_run()
        run_t.text = dtitle
        run_t.font.bold = True
        run_t.font.size = Pt(11)
        run_t.font.color.rgb = COLOR_DARK_TEXT

        run_d = p.add_run()
        run_d.text = ddesc
        run_d.font.size = Pt(10.5)
        run_d.font.color.rgb = COLOR_BODY_TEXT
        p.space_after = Pt(6)

    # Right: 2 Strategic Pitch Cards
    # Card 1: Final Pitch Line
    pcard = s10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.3), Inches(2.45), Inches(4.4), Inches(1.85))
    pcard.fill.solid()
    pcard.fill.fore_color.rgb = COLOR_RED_BG
    pcard.line.color.rgb = COLOR_RED_ACCENT
    pcard.line.width = Pt(1.5)
    tf_pc = pcard.text_frame
    tf_pc.word_wrap = True
    p1 = tf_pc.paragraphs[0]
    p1.text = "Final Executive Pitch"
    p1.font.size = Pt(13)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_RED_PRIMARY
    p1.space_after = Pt(3)
    p2 = tf_pc.add_paragraph()
    p2.text = "RoboNexus delivers deterministic, cloud-grade AI compute directly inside industrial facilities—safeguarding human workers, eliminating cloud latency, and cutting robot fleet hardware costs by 60%."
    p2.font.size = Pt(11)
    p2.font.color.rgb = COLOR_BODY_TEXT

    # Card 2: Judging Strengths
    jcard = s10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.3), Inches(4.5), Inches(4.4), Inches(1.95))
    jcard.fill.solid()
    jcard.fill.fore_color.rgb = COLOR_BLUE_BG
    jcard.line.color.rgb = COLOR_BLUE_ACCENT
    jcard.line.width = Pt(1.5)
    tf_jc = jcard.text_frame
    tf_jc.word_wrap = True
    p1 = tf_jc.paragraphs[0]
    p1.text = "Hackathon Judging Strengths"
    p1.font.size = Pt(13)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_BLUE_PRIMARY
    p1.space_after = Pt(3)
    p2 = tf_jc.add_paragraph()
    p2.text = "• Algorithmic Innovation: RADS physical-context scheduler\n• Architectural Rigor: Decoupled 4-tier microservices\n• Industrial Compliance: ISO 3691-4 black-box audit trails\n• Live Production Readiness: 100% functional live test rig"
    p2.font.size = Pt(10.5)
    p2.font.color.rgb = COLOR_BODY_TEXT

    add_bottom_banner(s10, "YHACK'26 Review: Fully Operational Private AI Cloud • Live Demonstration Ready")

    prs.save(output_path)
    print(f"[SUCCESS] Presentation generated and saved to {output_path}")

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "RoboNexus_Hackathon_Pitch_Deck.pptx"
    build_presentation(out)
