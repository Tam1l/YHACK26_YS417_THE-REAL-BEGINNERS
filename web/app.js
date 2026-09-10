/* ==========================================================================
   ROBONEXUS PRIVATE AI CLOUD — CLIENT LOGIC & SIMULATION ENGINE
   ========================================================================== */

// --- Global State ---
let isRunning = true;
let humanHazard = false;
let humanPos = { x: 620, y: 265 };
let worker1Alive = true;
let worker2Alive = true;
let latestLatency = 17.8;
let latestClusterData = null;

// Telemetry packets in flight
// Telemetry packets in flight
let packets = [];

// Failover visual state
let failoverActive = false;
let failoverStartTime = 0;

// Closed-loop automated hazard state
let hazardStage = 'IDLE'; // 'IDLE' | 'DETECTED' | 'CLOUD_DECISION' | 'CLEARING' | 'RESUMING'
let hazardAutoTimer = null;

// Fleet Robots with Dedicated Roles & Authentic Motion
const agv = {
    id: 'AGV-01',
    role: 'Heavy Pallet Transport',
    x: 100,
    y: 294,
    targetX: 880,
    speed: 2.4,
    crit: 'CRITICAL',
    color: '#ef4444',
    status: 'NORMAL',
    beamActive: false
};

const drone = {
    id: 'DRONE-07',
    role: 'High-Bay Inventory Scanner',
    x: 140,
    y: 205,
    targetX: 180,
    speed: 1.8,
    tilt: 0,
    hoverOffset: 0,
    rotorAngle: 0,
    currentBayIndex: 0,
    bayHoverTimer: 0,
    scannedSKU: 'SKU-8492 [99.8% VERIFIED]',
    color: '#0284c7'
};

const sweeper = {
    id: 'SWEEPER-12',
    role: 'Level 0 Aisle Floor Scrubber',
    x: 120,
    y: 374,
    dirX: 1,
    speed: 1.4,
    brushAngle: 0,
    trail: [],
    sprayParticles: [],
    color: '#059669'
};

// ================= THEME ENGINE =================
const btnThemeToggle = document.getElementById('btnThemeToggle');
const themeIcon = document.getElementById('themeIcon');
const themeText = document.getElementById('themeText');

function initTheme() {
    const saved = localStorage.getItem('robonexus_theme') || 'light';
    setTheme(saved);
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('robonexus_theme', theme);
    if (theme === 'light') {
        themeIcon.innerText = '🌙';
        themeText.innerText = 'Dark Mode';
    } else {
        themeIcon.innerText = '☀️';
        themeText.innerText = 'Light Mode';
    }
}

btnThemeToggle.addEventListener('click', () => {
    const cur = document.documentElement.getAttribute('data-theme');
    setTheme(cur === 'light' ? 'dark' : 'light');
});

// ================= TOAST SYSTEM =================
const toastContainer = document.getElementById('toastContainer');

function showToast(message, type = 'info', duration = 4000) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    
    let icon = 'ℹ️';
    let borderColor = 'var(--color-blue)';
    if (type === 'success') { icon = '✅'; borderColor = 'var(--color-emerald)'; }
    if (type === 'warning') { icon = '⚠️'; borderColor = 'var(--color-amber)'; }
    if (type === 'error') { icon = '🚨'; borderColor = 'var(--color-red)'; }
    if (type === 'security') { icon = '🛡️'; borderColor = 'var(--color-rose)'; }

    toast.style.borderLeftColor = borderColor;
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 350);
    }, duration);
}

function showBanner(text, bg, border, color = '#ffffff') {
    const banner = document.getElementById('arenaBanner');
    banner.innerText = text;
    banner.style.background = bg;
    banner.style.border = '1px solid ' + border;
    banner.style.color = color;
    banner.style.display = 'block';
    setTimeout(() => { banner.style.display = 'none'; }, 4500);
}

// ================= 2D CANVAS SIMULATION =================
const canvas = document.getElementById('simulationCanvas');
const ctx = canvas.getContext('2d');
const wrapper = document.getElementById('canvasWrapper');

function resizeCanvas() {
    canvas.width = wrapper.clientWidth;
    canvas.height = wrapper.clientHeight;
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

function isLightTheme() {
    return document.documentElement.getAttribute('data-theme') === 'light';
}

function drawWarehouse() {
    const w = canvas.width;
    const h = canvas.height;
    const light = isLightTheme();

    // Base floor background
    ctx.fillStyle = light ? '#f8fafc' : '#0b1120';
    ctx.fillRect(0, 0, w, h);

    // Architectural Precision Floor Grid
    ctx.strokeStyle = light ? '#e2e8f0' : '#17233f';
    ctx.lineWidth = 1;
    for (let x = 0; x < w; x += 40) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
    }
    for (let y = 0; y < h; y += 40) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }

    // High-Speed Transit Corridor (y: 250 to 338, height: 88, center y: 294)
    ctx.fillStyle = light ? '#f1f5f9' : '#131d33';
    ctx.fillRect(0, 250, w, 88);
    ctx.strokeStyle = light ? '#cbd5e1' : '#25334d';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(0, 250); ctx.lineTo(w, 250);
    ctx.moveTo(0, 338); ctx.lineTo(w, 338);
    ctx.stroke();

    // Center yellow safety guidestrip (centerline at y = 294)
    ctx.strokeStyle = '#d97706';
    ctx.lineWidth = 2.5;
    ctx.setLineDash([14, 12]);
    ctx.beginPath();
    ctx.moveTo(0, 294); ctx.lineTo(w, 294);
    ctx.stroke();
    ctx.setLineDash([]);

    // Distance tick markers along corridor
    ctx.fillStyle = light ? '#94a3b8' : '#475569';
    ctx.font = '8px monospace';
    for (let dm = 0; dm <= 100; dm += 20) {
        const dx = 40 + (dm / 100) * (w - 80);
        ctx.fillRect(dx, 250, 1, 6);
        ctx.fillRect(dx, 332, 1, 6);
        ctx.fillText(`${dm}m`, dx - 6, 262);
    }

    // Highway Corridor Label
    ctx.fillStyle = light ? '#475569' : '#94a3b8';
    ctx.font = 'bold 10px monospace';
    ctx.fillText("AGV HIGH-SPEED TRANSIT CORRIDOR [LANE-01: ISO 3691-4 PROTECTED]", 260, 274);

    // Fleet Autonomous Fast-Dock (Top Center: x: (w-200)/2, y: 12, h: 74)
    const dockW = 200, dockH = 74;
    const dockX = Math.max(260, Math.floor((w - dockW) / 2));
    const dockY = 12;
    ctx.fillStyle = light ? 'rgba(16, 185, 129, 0.08)' : 'rgba(16, 185, 129, 0.12)';
    ctx.fillRect(dockX, dockY, dockW, dockH);
    ctx.strokeStyle = 'rgba(16, 185, 129, 0.6)';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(dockX, dockY, dockW, dockH);
    ctx.fillStyle = '#10b981';
    ctx.font = 'bold 10px sans-serif';
    ctx.fillText("⚡ AUTONOMOUS FAST-DOCK (PAD-01)", dockX + 10, dockY + 20);
    ctx.fillStyle = light ? '#475569' : '#94a3b8';
    ctx.font = '9px monospace';
    ctx.fillText("Dual 48V High-Rate Induction Pad", dockX + 10, dockY + 38);
    // Charging contacts
    ctx.fillStyle = '#10b981';
    ctx.fillRect(dockX + 40, dockY + 46, 44, 14);
    ctx.fillRect(dockX + 116, dockY + 46, 44, 14);

    // Upper High-Bay Racks: y = 128 to 188 (height: 60)
    // Clearance from Top HUDs (y: 12..86) is 42px! Clearance to Highway (y: 250) is 62px!
    drawRack(24, 128, 240, 60, '#38bdf8', 'RACK-A [HIGH-BAY LOGISTICS]', 'LEVEL 3: AERIAL DRONE SCAN LAYER', light);
    drawRack(w - 264, 128, 240, 60, '#818cf8', 'RACK-B [HIGH-BAY AUTOMATED]', 'LEVEL 3: AERIAL DRONE SCAN LAYER', light);

    // Drone flight path indicator in the upper flight corridor
    ctx.strokeStyle = light ? 'rgba(14, 165, 233, 0.25)' : 'rgba(14, 165, 233, 0.2)';
    ctx.setLineDash([4, 6]);
    ctx.beginPath();
    ctx.moveTo(30, 205); ctx.lineTo(w - 30, 205);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = light ? '#0284c7' : '#38bdf8';
    ctx.font = '8.5px monospace';
    ctx.fillText("✈️ AERIAL INSPECTION FLIGHT CORRIDOR (ALTITUDE: 4.8m)", 260, 218);

    // Lower Floor Maintenance Apron: y = 338 to 414 (height: 76)
    // Clearance between Highway and Lower Racks is 76px! Sweeper sweeps at y = 374!
    ctx.strokeStyle = light ? 'rgba(5, 150, 105, 0.25)' : 'rgba(16, 185, 129, 0.2)';
    ctx.setLineDash([6, 6]);
    ctx.beginPath();
    ctx.moveTo(30, 374); ctx.lineTo(w - 270, 374);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = light ? '#059669' : '#34d399';
    ctx.font = '8.5px monospace';
    ctx.fillText("🧹 AISLE 02 [LEVEL 0: FLOOR SANITIZATION & DUST SCRUBBING ZONE]", 24, 360);

    // Lower Floor Racks: y = 414 to 474 (height: 60)
    // Clearance below Highway is 76px; clearance below Racks is 96px!
    drawRack(24, 414, 240, 60, '#34d399', 'RACK-C [INVENTORY & RAW]', 'LEVEL 0: SWEEPER AISLE PERIMETER', light);
    drawRack(Math.max(290, Math.floor((w - 240) / 2)), 414, 240, 60, '#f472b6', 'RACK-D [STAGING & BUFFER]', 'LEVEL 0: SWEEPER AISLE PERIMETER', light);

    // Floating HUD Panels with strict margin separation
    drawQueueHUD(light);
    drawCloudHubHUD(w, light);
    drawCameraHUD(w, light);
}

function drawRack(x, y, w, h, accentColor, label, tierLevel, light) {
    const isUpper = (y < 250);
    const timeSec = Date.now() / 1000.0;
    const halfW = Math.floor(w / 2);

    // 1. Soft Outer Ambient Drop Shadow for 3D depth
    ctx.save();
    ctx.fillStyle = light ? 'rgba(15, 23, 42, 0.08)' : 'rgba(0, 0, 0, 0.45)';
    ctx.beginPath();
    ctx.roundRect(x + 2, y + 4, w - 4, h + 2, 4);
    ctx.fill();
    ctx.restore();

    // 2. Heavy-Duty Industrial Rack Backing (Deep structural shadow cavity)
    ctx.fillStyle = light ? '#f8fafc' : '#090d16';
    ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = light ? '#cbd5e1' : '#1e293b';
    ctx.lineWidth = 1.2;
    ctx.strokeRect(x, y, w, h);

    // 3. Structural Bay X-Bracing (Heavy diagonal cross-trusses behind cargo)
    ctx.save();
    ctx.strokeStyle = light ? 'rgba(148, 163, 184, 0.45)' : 'rgba(51, 65, 85, 0.55)';
    ctx.lineWidth = 1.2;
    // Left Bay X
    ctx.beginPath();
    ctx.moveTo(x + 8, y + 6); ctx.lineTo(x + halfW - 4, y + h - 8);
    ctx.moveTo(x + halfW - 4, y + 6); ctx.lineTo(x + 8, y + h - 8);
    // Right Bay X
    ctx.moveTo(x + halfW + 4, y + 6); ctx.lineTo(x + w - 8, y + h - 8);
    ctx.moveTo(x + w - 8, y + 6); ctx.lineTo(x + halfW + 4, y + h - 8);
    ctx.stroke();

    // Center Truss Gusset Rivet Plates
    ctx.fillStyle = light ? '#94a3b8' : '#475569';
    ctx.beginPath();
    ctx.arc(x + Math.floor(halfW / 2), y + Math.floor(h / 2), 2.2, 0, Math.PI * 2);
    ctx.arc(x + halfW + Math.floor(halfW / 2), y + Math.floor(h / 2), 2.2, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // 4. Wire Mesh Safety Decking (Fine industrial grid)
    ctx.save();
    ctx.strokeStyle = light ? 'rgba(203, 213, 225, 0.4)' : 'rgba(51, 65, 85, 0.4)';
    ctx.lineWidth = 0.6;
    for (let gx = x + 12; gx < x + w - 12; gx += 8) {
        ctx.beginPath();
        ctx.moveTo(gx, y + 8);
        ctx.lineTo(gx, y + 26);
        ctx.stroke();
    }
    ctx.restore();

    // 5. 4 Individual Pallet Bays with Realistic Industrial Cargo Diversity
    const numBays = 4;
    const baySpacing = (w - 20) / numBays;
    const palletW = 46;

    for (let i = 0; i < numBays; i++) {
        const px = x + 10 + (i * baySpacing);
        const palletY = y + 20;
        const cargoH = 16;
        const cargoY = palletY - cargoH;
        const isDroneHoveringThisBay = isUpper && Math.abs(drone.x - (px + palletW / 2)) < 22;

        // --- Wooden Euro-Pallet (EPAL / EUR Standard) ---
        // Slat top planks with realistic board gaps
        ctx.fillStyle = '#b45309';
        ctx.fillRect(px, palletY, palletW, 3.5);
        ctx.fillStyle = '#78350f'; // Dark wooden front edge
        ctx.fillRect(px, palletY + 3.5, palletW, 1.2);
        // Vertical slat gap shadow lines
        ctx.fillStyle = 'rgba(0, 0, 0, 0.35)';
        ctx.fillRect(px + 14, palletY, 1, 3.5);
        ctx.fillRect(px + 29, palletY, 1, 3.5);

        // 3 Solid Composite Spacer Blocks & Fork Entry Cavities (Negative Space)
        ctx.fillStyle = '#92400e';
        ctx.fillRect(px + 1, palletY + 4.7, 7, 3.2);
        ctx.fillRect(px + Math.floor(palletW / 2) - 4, palletY + 4.7, 8, 3.2);
        ctx.fillRect(px + palletW - 8, palletY + 4.7, 7, 3.2);
        // Fastener nail heads on blocks
        ctx.fillStyle = '#d1d5db';
        ctx.fillRect(px + 4, palletY + 6, 1, 1);
        ctx.fillRect(px + Math.floor(palletW / 2), palletY + 6, 1, 1);
        ctx.fillRect(px + palletW - 5, palletY + 6, 1, 1);

        // Bottom Skid Runners (Chamfered base)
        ctx.fillStyle = '#b45309';
        ctx.fillRect(px + 1, palletY + 7.9, 7, 1.5);
        ctx.fillRect(px + Math.floor(palletW / 2) - 4, palletY + 7.9, 8, 1.5);
        ctx.fillRect(px + palletW - 8, palletY + 7.9, 7, 1.5);

        // --- Diverse Industrial Cargo Types per Bay ---
        if (i === 0) {
            // Bay 0: Stacked Kraft Corrugated Cardboard Shipping Cartons
            ctx.fillStyle = '#d97706';
            ctx.fillRect(px + 2, cargoY + 6, palletW - 4, 10);
            // Packaging tape seam
            ctx.fillStyle = '#f59e0b';
            ctx.fillRect(px + 2, cargoY + 10, palletW - 4, 2);
            // Red "FRAGILE" stamp
            ctx.fillStyle = '#dc2626';
            ctx.font = 'bold 5.5px sans-serif';
            ctx.fillText('FRAGILE', px + 4, cargoY + 9.5);

            // Top Box (offset layer with shadow)
            ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
            ctx.fillRect(px + 6, cargoY + 5.5, palletW - 12, 1);
            ctx.fillStyle = '#b45309';
            ctx.fillRect(px + 6, cargoY, palletW - 12, 6);
            ctx.fillStyle = '#f59e0b';
            ctx.fillRect(px + 6, cargoY + 3, palletW - 12, 1.5);

            // Fragile orientation arrows (↑↑)
            ctx.fillStyle = '#0f172a';
            ctx.font = 'bold 7px sans-serif';
            ctx.fillText('↑↑', px + 5, cargoY + 14.5);

            // High-density Barcode shipping slip with SKU
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(px + 20, cargoY + 7, 20, 8);
            ctx.fillStyle = '#0f172a';
            ctx.fillRect(px + 22, cargoY + 8, 1.5, 5);
            ctx.fillRect(px + 24.5, cargoY + 8, 2.5, 5);
            ctx.fillRect(px + 28, cargoY + 8, 1, 5);
            ctx.fillRect(px + 30, cargoY + 8, 2, 5);
            ctx.fillRect(px + 33, cargoY + 8, 1.5, 5);
            ctx.fillRect(px + 36, cargoY + 8, 2, 5);
            ctx.font = '4.5px monospace';
            ctx.fillText('SKU-4821', px + 21, cargoY + 14.2);

        } else if (i === 1) {
            // Bay 1: Industrial Molded Polymer KLT Crate (Automotive Euro-Tote)
            const crateColor = accentColor;
            ctx.fillStyle = crateColor;
            ctx.beginPath();
            ctx.roundRect(px + 3, cargoY + 2, palletW - 6, 14, 2);
            ctx.fill();

            // Molded reinforcement perimeter rim & stiffening ribs
            ctx.strokeStyle = light ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.4)';
            ctx.lineWidth = 1;
            ctx.strokeRect(px + 6, cargoY + 4, palletW - 12, 10);
            ctx.beginPath();
            ctx.moveTo(px + Math.floor(palletW / 2), cargoY + 4);
            ctx.lineTo(px + Math.floor(palletW / 2), cargoY + 14);
            ctx.moveTo(px + 13, cargoY + 4); ctx.lineTo(px + 13, cargoY + 14);
            ctx.moveTo(px + palletW - 13, cargoY + 4); ctx.lineTo(px + palletW - 13, cargoY + 14);
            ctx.stroke();

            // Ergonomic handle cutout slot
            ctx.fillStyle = light ? '#cbd5e1' : '#090d16';
            ctx.fillRect(px + Math.floor(palletW / 2) - 4, cargoY + 6, 8, 2.5);

            // Active Pulsing RFID Tracking Transponder with telemetry halo
            const rfidX = px + palletW - 9;
            const rfidY = cargoY + 6;
            const rfidWave = (Date.now() / 200) % 4;
            ctx.save();
            ctx.strokeStyle = `rgba(6, 182, 212, ${Math.max(0, 0.7 - rfidWave * 0.15)})`;
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.arc(rfidX, rfidY, 2.5 + rfidWave, 0, Math.PI * 2);
            ctx.stroke();

            ctx.fillStyle = '#06b6d4';
            ctx.shadowColor = '#06b6d4';
            ctx.shadowBlur = 5;
            ctx.beginPath();
            ctx.arc(rfidX, rfidY, 2, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();

        } else if (i === 2) {
            // Bay 2: Palletized UN Steel Chemical / Lube Drums (Twin Drum Assembly)
            const drumW = 18;
            for (let d = 0; d < 2; d++) {
                const dx = px + 4 + d * 20;
                // Metallic drum gradient (brushed cylindrical specular reflection)
                const grad = ctx.createLinearGradient(dx, cargoY, dx + drumW, cargoY);
                grad.addColorStop(0, light ? '#475569' : '#1e293b');
                grad.addColorStop(0.35, light ? '#cbd5e1' : '#64748b');
                grad.addColorStop(0.65, light ? '#94a3b8' : '#475569');
                grad.addColorStop(1, light ? '#334155' : '#0f172a');
                ctx.fillStyle = grad;
                ctx.beginPath();
                ctx.roundRect(dx, cargoY + 1, drumW, 15, 2);
                ctx.fill();

                // Chimb containment rolling rings (top, middle, bottom)
                ctx.strokeStyle = '#e2e8f0';
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(dx, cargoY + 4); ctx.lineTo(dx + drumW, cargoY + 4);
                ctx.moveTo(dx, cargoY + 8); ctx.lineTo(dx + drumW, cargoY + 8);
                ctx.moveTo(dx, cargoY + 12); ctx.lineTo(dx + drumW, cargoY + 12);
                ctx.stroke();

                // Top lid bung plugs
                ctx.fillStyle = '#0f172a';
                ctx.fillRect(dx + 3, cargoY + 1, 2.5, 1.2);
                ctx.fillRect(dx + 11, cargoY + 1, 3.5, 1.2);
            }

            // UN Class 3 Flammable Hazard Warning Diamond Placard
            ctx.save();
            ctx.translate(px + 22, cargoY + 8.5);
            ctx.rotate(Math.PI / 4);
            ctx.fillStyle = '#eab308';
            ctx.fillRect(-3.5, -3.5, 7, 7);
            ctx.strokeStyle = '#0f172a';
            ctx.lineWidth = 0.6;
            ctx.strokeRect(-3.5, -3.5, 7, 7);
            // Black flame symbol dot
            ctx.fillStyle = '#0f172a';
            ctx.beginPath(); ctx.arc(0, 0, 1.2, 0, Math.PI * 2); ctx.fill();
            ctx.restore();

        } else {
            // Bay 3: Translucent Stretch-Wrapped High-Bay Pallet Load
            ctx.fillStyle = light ? '#0284c7' : '#0369a1';
            ctx.fillRect(px + 3, cargoY + 1, palletW - 6, 15);

            // Glossy stretch-wrap multi-angle specular sheen overlay
            const wrapGrad = ctx.createLinearGradient(px, cargoY, px + palletW, cargoY + 15);
            wrapGrad.addColorStop(0, 'rgba(255,255,255,0.06)');
            wrapGrad.addColorStop(0.3, 'rgba(255,255,255,0.38)');
            wrapGrad.addColorStop(0.5, 'rgba(255,255,255,0.08)');
            wrapGrad.addColorStop(0.8, 'rgba(255,255,255,0.32)');
            wrapGrad.addColorStop(1, 'rgba(255,255,255,0.1)');
            ctx.fillStyle = wrapGrad;
            ctx.fillRect(px + 3, cargoY + 1, palletW - 6, 15);
            ctx.strokeStyle = 'rgba(255,255,255,0.5)';
            ctx.lineWidth = 0.8;
            ctx.strokeRect(px + 3, cargoY + 1, palletW - 6, 15);

            // Horizontal stretch wrap film compression bands
            ctx.strokeStyle = 'rgba(255,255,255,0.45)';
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.moveTo(px + 3, cargoY + 5); ctx.lineTo(px + palletW - 3, cargoY + 5);
            ctx.moveTo(px + 3, cargoY + 10); ctx.lineTo(px + palletW - 3, cargoY + 10);
            ctx.stroke();

            // Outbound dispatch manifest placard
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(px + 6, cargoY + 5, 16, 8);
            ctx.fillStyle = '#0f172a';
            ctx.fillRect(px + 8, cargoY + 6, 3, 3);
            ctx.fillRect(px + 12, cargoY + 6, 2, 6);
            ctx.fillRect(px + 16, cargoY + 6, 3, 6);
            ctx.font = '4.5px monospace';
            ctx.fillText('OUTBOUND', px + 7, cargoY + 12);
        }

        // --- Smart IoT Micro-LED Sensor & Active Drone Scan Highlight ---
        const ledColors = ['#10b981', '#06b6d4', '#f59e0b', '#10b981'];
        const ledX = px + Math.floor(palletW / 2);
        const ledY = y + 3;
        ctx.save();
        if (isDroneHoveringThisBay) {
            // Dynamic vertical laser sweep through the cargo bay
            const scanLineY = cargoY + ((Date.now() / 25) % 17);
            ctx.strokeStyle = '#38bdf8';
            ctx.lineWidth = 1.6;
            ctx.shadowColor = '#38bdf8';
            ctx.shadowBlur = 7;
            ctx.beginPath();
            ctx.moveTo(px + 2, scanLineY);
            ctx.lineTo(px + palletW - 2, scanLineY);
            ctx.stroke();

            // Holographic corner reticles [  ]
            const cl = 4;
            ctx.strokeStyle = '#38bdf8';
            ctx.lineWidth = 1.4;
            // Top-left
            ctx.beginPath(); ctx.moveTo(px + 1, cargoY + cl); ctx.lineTo(px + 1, cargoY); ctx.lineTo(px + 1 + cl, cargoY); ctx.stroke();
            // Top-right
            ctx.beginPath(); ctx.moveTo(px + palletW - 1 - cl, cargoY); ctx.lineTo(px + palletW - 1, cargoY); ctx.lineTo(px + palletW - 1, cargoY + cl); ctx.stroke();
            // Bottom-left
            ctx.beginPath(); ctx.moveTo(px + 1, cargoY + 18 - cl); ctx.lineTo(px + 1, cargoY + 18); ctx.lineTo(px + 1 + cl, cargoY + 18); ctx.stroke();
            // Bottom-right
            ctx.beginPath(); ctx.moveTo(px + palletW - 1 - cl, cargoY + 18); ctx.lineTo(px + palletW - 1, cargoY + 18); ctx.lineTo(px + palletW - 1, cargoY + 18 - cl); ctx.stroke();

            // Active Drone Scan Beacon & Status Pill
            ctx.fillStyle = '#38bdf8';
            ctx.shadowColor = '#38bdf8';
            ctx.shadowBlur = 9;
            ctx.beginPath();
            ctx.arc(ledX, ledY, 3.2, 0, Math.PI * 2);
            ctx.fill();

            ctx.fillStyle = '#38bdf8';
            ctx.font = 'bold 6.5px monospace';
            ctx.fillText('⚡ LASER SCAN LOCK', px + 2, cargoY - 3);

        } else {
            ctx.fillStyle = ledColors[i];
            ctx.shadowColor = ledColors[i];
            ctx.shadowBlur = 4;
            ctx.beginPath();
            ctx.arc(ledX, ledY, 1.8, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.restore();
    }

    // 6. Safety Orange Heavy-Duty Shelf Load Beams with 3D Bevel & Locking Pins
    // Upper shelf beam
    const beamY1 = y + 28;
    ctx.fillStyle = '#ea580c'; // Powder-coated safety orange
    ctx.fillRect(x, beamY1, w, 4);
    ctx.fillStyle = '#fb923c'; // Top highlight line
    ctx.fillRect(x, beamY1, w, 1);
    ctx.fillStyle = '#9a3412'; // Bottom shadow bevel
    ctx.fillRect(x, beamY1 + 3, w, 1);

    // Lower base beam
    const beamY2 = y + h - 16;
    ctx.fillStyle = '#ea580c';
    ctx.fillRect(x, beamY2, w, 4);
    ctx.fillStyle = '#fb923c';
    ctx.fillRect(x, beamY2, w, 1);
    ctx.fillStyle = '#9a3412';
    ctx.fillRect(x, beamY2 + 3, w, 1);

    // Laser-etched Bay Locator IDs along the orange beam
    const bayLetters = ['01', '02', '03', '04'];
    const rackPrefix = label.split(' ')[0].replace('RACK-', '');
    for (let b = 0; b < 4; b++) {
        const bx = x + 12 + (b * baySpacing);
        ctx.fillStyle = '#0f172a';
        ctx.fillRect(bx + 4, beamY1 + 1, 18, 2.8);
        ctx.fillStyle = '#fed7aa';
        ctx.font = 'bold 6px monospace';
        ctx.fillText(`${rackPrefix}-${bayLetters[b]}`, bx + 5, beamY1 + 3.2);
    }

    // 7. Heavy Structural Steel Upright Columns (Left, Center, Right)
    const postWidth = 7;
    const postPositions = [x, x + Math.floor(w / 2) - 3, x + w - postWidth];
    postPositions.forEach(px => {
        // Steel column body with dual-tone industrial gradient
        const postGrad = ctx.createLinearGradient(px, y, px + postWidth, y);
        postGrad.addColorStop(0, light ? '#334155' : '#1e3a8a');
        postGrad.addColorStop(0.5, light ? '#64748b' : '#2563eb');
        postGrad.addColorStop(1, light ? '#1e293b' : '#172554');
        ctx.fillStyle = postGrad;
        ctx.fillRect(px, y, postWidth, h);

        // Teardrop / Perforated Bolt Slot Pattern (Industrial slotted uprights)
        ctx.fillStyle = light ? '#e2e8f0' : '#090d16';
        for (let py = y + 4; py < y + h - 6; py += 7) {
            ctx.fillRect(px + 2, py, 3, 3);
        }

        // Beam connector safety clips (yellow locking pins at junctions)
        ctx.fillStyle = '#fbbf24';
        ctx.beginPath();
        ctx.arc(px + 3.5, beamY1 + 2, 1.8, 0, Math.PI * 2);
        ctx.arc(px + 3.5, beamY2 + 2, 1.8, 0, Math.PI * 2);
        ctx.fill();

        // Floor Anchor Base Footplate (At bottom of column)
        ctx.fillStyle = light ? '#1e293b' : '#475569';
        ctx.fillRect(px - 1.5, y + h - 3, postWidth + 3, 3);
        // Anchor bolts
        ctx.fillStyle = '#e2e8f0';
        ctx.fillRect(px - 0.5, y + h - 2, 1.5, 1.5);
        ctx.fillRect(px + postWidth, y + h - 2, 1.5, 1.5);
    });

    // 8. Lower Rack Heavy-Duty Corner Crash Guards (Yellow/Black Hazard Bollards)
    if (!isUpper) {
        drawCornerGuard(x - 3, y + h - 16, light);
        drawCornerGuard(x + w - 4, y + h - 16, light);
    }

    // 9. Upper Rack Optical Target Barcode Fiducials (For Aerial Drone Alignment)
    if (isUpper) {
        const fiducialX = x + Math.floor(w / 2) - 18;
        const fiducialY = y - 7;
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(fiducialX, fiducialY, 36, 6);
        ctx.strokeStyle = '#0284c7';
        ctx.lineWidth = 1;
        ctx.strokeRect(fiducialX, fiducialY, 36, 6);
        // QR / ArUco optical marker bit pattern
        ctx.fillStyle = '#0f172a';
        ctx.fillRect(fiducialX + 2, fiducialY + 1, 4, 4);
        ctx.fillRect(fiducialX + 8, fiducialY + 1, 2, 4);
        ctx.fillRect(fiducialX + 12, fiducialY + 1, 3, 4);
        ctx.fillRect(fiducialX + 17, fiducialY + 1, 2, 4);
        ctx.fillRect(fiducialX + 21, fiducialY + 1, 4, 4);
        ctx.fillRect(fiducialX + 28, fiducialY + 1, 6, 4);

        // When aerial drone flies directly overhead
        if (Math.abs(drone.x - (x + halfW)) < 55) {
            ctx.save();
            ctx.strokeStyle = '#38bdf8';
            ctx.lineWidth = 1.5;
            ctx.shadowColor = '#38bdf8';
            ctx.shadowBlur = 8;
            ctx.strokeRect(fiducialX - 2, fiducialY - 2, 40, 10);
            ctx.fillStyle = '#38bdf8';
            ctx.font = 'bold 7px monospace';
            ctx.fillText('⚡ OPTICAL SCAN LOCK: 99.8%', fiducialX - 18, fiducialY - 4);
            ctx.restore();
        }
    }

    // 10. Floating Digital Twin HUD Pill Badge (Capacities & RFID sync status)
    ctx.save();
    ctx.fillStyle = light ? 'rgba(255, 255, 255, 0.94)' : 'rgba(15, 23, 42, 0.9)';
    ctx.beginPath();
    ctx.roundRect(x + 8, y + h - 12, w - 16, 10, 3);
    ctx.fill();
    ctx.strokeStyle = light ? 'rgba(203, 213, 225, 0.85)' : 'rgba(51, 65, 85, 0.85)';
    ctx.lineWidth = 0.8;
    ctx.stroke();

    // Live pulsing green status indicator
    const pulseAlpha = 0.6 + 0.4 * Math.sin(timeSec * 4);
    ctx.fillStyle = `rgba(16, 185, 129, ${pulseAlpha})`;
    ctx.beginPath();
    ctx.arc(x + 15, y + h - 7, 2.2, 0, Math.PI * 2);
    ctx.fill();

    // Label & Capacity
    ctx.fillStyle = light ? '#0284c7' : '#38bdf8';
    ctx.font = 'bold 7.5px monospace';
    ctx.fillText(label, x + 22, y + h - 4.5);

    ctx.fillStyle = light ? '#64748b' : '#94a3b8';
    ctx.font = '6.5px monospace';
    ctx.fillText(`CAP: 98.4% • ${tierLevel.split(':')[0]}`, x + w - 95, y + h - 4.5);
    ctx.restore();
}

function drawCornerGuard(gx, gy, light) {
    // Heavy-duty crash protection bollard with diagonal hazard stripes
    const gw = 7, gh = 15;
    ctx.save();
    ctx.fillStyle = '#eab308'; // Safety yellow
    ctx.fillRect(gx, gy, gw, gh);
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 0.8;
    ctx.strokeRect(gx, gy, gw, gh);

    // Diagonal black hazard stripes
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    ctx.moveTo(gx, gy + 3); ctx.lineTo(gx + gw, gy + 8);
    ctx.moveTo(gx, gy + 8); ctx.lineTo(gx + gw, gy + 13);
    ctx.stroke();
    ctx.restore();
}

function drawQueueHUD(light) {
    const hudX = 24, hudY = 12, hudW = 220, hudH = 74;
    ctx.fillStyle = light ? '#ffffff' : '#0f172a';
    ctx.fillRect(hudX, hudY, hudW, hudH);
    ctx.strokeStyle = light ? '#cbd5e1' : '#1e293b';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(hudX, hudY, hudW, hudH);

    ctx.fillStyle = light ? '#4f46e5' : '#818cf8';
    ctx.font = 'bold 10px sans-serif';
    const qCount = latestClusterData?.autoscaler?.queue_depth ?? 0;
    ctx.fillText(`⏳ RADS PRIORITY QUEUE (${qCount} WAITING)`, hudX + 8, hudY + 16);

    const tasks = [
        { id: 'DRONE-07', crit: 'HIGH', color: '#0284c7' },
        { id: 'SWEEPER-12', crit: 'NORMAL', color: '#059669' },
        { id: 'SCANNER-09', crit: 'LOW', color: '#64748b' }
    ];

    tasks.forEach((t, i) => {
        const itemY = hudY + 26 + i * 14;
        ctx.fillStyle = t.color;
        ctx.fillRect(hudX + 8, itemY, 5, 9);
        ctx.fillStyle = light ? '#1e293b' : '#e2e8f0';
        ctx.font = '9px monospace';
        ctx.fillText(`P${i+1}: ${t.id} [${t.crit}]`, hudX + 18, itemY + 8);
    });
}

function drawCloudHubHUD(w, light) {
    const hubW = 220, hubH = 74;
    const hubX = w - hubW - 24, hubY = 12;

    ctx.fillStyle = light ? '#ffffff' : '#0f172a';
    ctx.fillRect(hubX, hubY, hubW, hubH);
    ctx.strokeStyle = failoverActive ? '#ef4444' : (light ? '#cbd5e1' : '#1e293b');
    ctx.lineWidth = failoverActive ? 2 : 1.5;
    ctx.strokeRect(hubX, hubY, hubW, hubH);

    ctx.fillStyle = failoverActive ? '#ef4444' : (light ? '#0284c7' : '#38bdf8');
    ctx.font = 'bold 10px sans-serif';
    ctx.fillText(failoverActive ? "☁️ PRIVATE CLOUD (FAILOVER ACTIVE ⚠️)" : "☁️ PRIVATE CLOUD HUB (PORT 8000)", hubX + 8, hubY + 16);

    // Worker 1 status row
    const w1Alive = worker1Alive && !failoverActive;
    ctx.fillStyle = w1Alive ? '#10b981' : '#ef4444';
    ctx.beginPath(); ctx.arc(hubX + 14, hubY + 31, 4, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = w1Alive ? (light ? '#1e293b' : '#cbd5e1') : '#dc2626';
    ctx.font = 'bold 9px monospace';
    ctx.fillText(w1Alive ? `worker-1: HEALTHY [BASE]` : `worker-1: 💀 CRASHED [TIMEOUT]`, hubX + 24, hubY + 34);

    // Worker 2 status row
    ctx.fillStyle = '#10b981';
    ctx.beginPath(); ctx.arc(hubX + 14, hubY + 46, 4, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = failoverActive ? '#d97706' : (light ? '#1e293b' : '#cbd5e1');
    ctx.font = 'bold 9px monospace';
    ctx.fillText(failoverActive ? `worker-2: ⚡ RECOVERED [RADS P1]` : `worker-2: HEALTHY [BASE]`, hubX + 24, hubY + 49);

    // Autoscaler count
    const activePods = latestClusterData?.autoscaler?.current_workers ?? 2;
    ctx.fillStyle = activePods > 2 ? '#f59e0b' : '#10b981';
    ctx.beginPath(); ctx.arc(hubX + 14, hubY + 61, 4, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = light ? '#1e293b' : '#cbd5e1';
    ctx.font = '9px monospace';
    ctx.fillText(`worker-pool: ${activePods}/5 ACTIVE`, hubX + 24, hubY + 64);

    // Animated Failover Handover Arc inside HUD
    if (failoverActive) {
        ctx.save();
        ctx.strokeStyle = '#d97706';
        ctx.setLineDash([3, 3]);
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(hubX + hubW - 30, hubY + 31);
        ctx.quadraticCurveTo(hubX + hubW - 10, hubY + 39, hubX + hubW - 30, hubY + 46);
        ctx.stroke();
        ctx.restore();
    }
}

function drawCameraHUD(w, light) {
    const hudW = 220, hudH = 145;
    const hudX = w - hudW - 24, hudY = 400;
    const isStopped = (agv.status === 'STOPPED');

    ctx.fillStyle = light ? '#ffffff' : '#0f172a';
    ctx.fillRect(hudX, hudY, hudW, hudH);
    ctx.strokeStyle = isStopped ? '#ef4444' : (light ? '#cbd5e1' : '#1e293b');
    ctx.lineWidth = isStopped ? 2.5 : 1.5;
    ctx.strokeRect(hudX, hudY, hudW, hudH);

    ctx.fillStyle = isStopped ? '#ef4444' : (light ? '#0891b2' : '#22d3ee');
    ctx.font = 'bold 10px sans-serif';
    ctx.fillText(isStopped ? "🚨 AGV-01 TELEMETRY FEED" : "👁️ AGV-01 PERCEPTION STREAM", hudX + 10, hudY + 18);

    // Bounding box viewfinder
    ctx.fillStyle = light ? '#f1f5f9' : '#000000';
    ctx.fillRect(hudX + 8, hudY + 26, hudW - 16, 84);

    ctx.strokeStyle = isStopped ? '#ef4444' : '#10b981';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(hudX + 38, hudY + 36, 126, 62);

    ctx.fillStyle = isStopped ? '#ef4444' : '#10b981';
    ctx.font = 'bold 9px monospace';
    ctx.fillText(isStopped ? 'TARGET: HUMAN (98.4%)' : 'TARGET: CLEAR (99.2%)', hudX + 42, hudY + 50);

    if (isStopped) {
        ctx.fillStyle = '#dc2626';
        ctx.font = 'bold 8.5px monospace';
        ctx.fillText('STATUS: SAFETY STOPPED', hudX + 42, hudY + 68);
        ctx.fillText('PROXIMITY: 85 cm [ZONE-1]', hudX + 42, hudY + 82);
    } else {
        ctx.fillStyle = '#059669';
        ctx.font = '8px monospace';
        ctx.fillText('LANE-01: OBSTACLE FREE', hudX + 42, hudY + 68);
        ctx.fillText('AUTO-TRANSIT: 2.4 m/s', hudX + 42, hudY + 82);
    }

    ctx.fillStyle = isStopped ? '#dc2626' : (light ? '#64748b' : '#94a3b8');
    ctx.font = isStopped ? 'bold 9px monospace' : '9.5px monospace';
    ctx.fillText(isStopped ? "TELEMETRY: RED [URLLC SLICE]" : `LATENCY: ${latestLatency.toFixed(1)}ms [DEADLINE MET]`, hudX + 10, hudY + 130);
}

// ================= SIMULATION PHYSICS & UPDATE =================
function updateSimulation() {
    if (!isRunning) return;

    // 1. AGV Transit & Braking Physics along Lane-01 (y = 294)
    if (humanHazard) {
        const distAhead = humanPos.x - agv.x;
        if (distAhead > 0 && distAhead < 130) {
            agv.status = 'STOPPED';
            agv.speed = 0;
            agv.beamActive = true;
        } else {
            agv.status = 'NORMAL';
            agv.speed = 2.4;
            agv.x += agv.speed;
        }
    } else {
        agv.status = 'NORMAL';
        agv.speed = 2.4;
        agv.x += agv.speed;
        agv.beamActive = false;
    }

    if (agv.x > canvas.width - 60) {
        agv.x = 80;
    }

    // 2. Multirotor Drone Quadcopter Flight & Shelf Inspection
    const w = canvas.width;
    const inspectionBays = [65, 125, 185, 235, w - 235, w - 185, w - 125, w - 65];
    const targetBayX = inspectionBays[drone.currentBayIndex % inspectionBays.length];
    
    // Smooth navigation towards target bay
    const dx = targetBayX - drone.x;
    if (Math.abs(dx) > 6) {
        const moveDir = dx > 0 ? 1 : -1;
        drone.x += moveDir * drone.speed;
        drone.tilt = drone.tilt * 0.85 + (moveDir * 0.14) * 0.15; // Realistic banking tilt
        drone.bayHoverTimer = 0;
    } else {
        // Drone hovers directly above rack bay to scan inventory
        drone.tilt = drone.tilt * 0.8; // Level out
        drone.bayHoverTimer++;
        if (drone.bayHoverTimer > 85) { // Hover ~1.5s
            drone.currentBayIndex = (drone.currentBayIndex + 1) % inspectionBays.length;
            drone.scannedSKU = `SKU-${1000 + Math.floor(Math.random() * 8999)} [VERIFIED]`;
            drone.bayHoverTimer = 0;
        }
    }

    drone.hoverOffset = Math.sin(Date.now() * 0.004) * 4;
    drone.y = 205 + drone.hoverOffset;
    drone.rotorAngle = (drone.rotorAngle + 0.45) % (Math.PI * 2);

    // 3. Sweeper Floor Perimeter Pathing & Brush Rotation along Level 0 (y = 374)
    sweeper.x += sweeper.dirX * sweeper.speed;
    if (sweeper.dirX > 0 && sweeper.x > canvas.width - 290) {
        sweeper.dirX = -1;
    } else if (sweeper.dirX < 0 && sweeper.x < 70) {
        sweeper.dirX = 1;
    }
    sweeper.brushAngle = (sweeper.brushAngle + 0.22) % (Math.PI * 2);

    // Record floor sanitization trail
    if (Math.random() < 0.4) {
        sweeper.trail.push({ x: sweeper.x, y: sweeper.y, opacity: 0.4 });
    }
    sweeper.trail.forEach(t => { t.opacity -= 0.007; });
    sweeper.trail = sweeper.trail.filter(t => t.opacity > 0);

    // Spray particles
    if (Math.random() < 0.3) {
        sweeper.sprayParticles.push({
            x: sweeper.x - sweeper.dirX * 14,
            y: sweeper.y + (Math.random() - 0.5) * 8,
            life: 1.0
        });
    }
    sweeper.sprayParticles.forEach(p => { p.life -= 0.04; });
    sweeper.sprayParticles = sweeper.sprayParticles.filter(p => p.life > 0);

    // 4. Smooth obstacle clearance animation
    if (humanHazard && humanPos && humanPos.clearing) {
        if (humanPos.y > 205) {
            humanPos.y -= 1.8; // Steps out of corridor to safety walkway
        }
    }

    // 5. Periodic 5G Telemetry Packets
    const packetFreq = (agv.status === 'STOPPED') ? 0.24 : 0.08;
    if (Math.random() < packetFreq) {
        const hubX = canvas.width - 134;
        packets.push({
            fromX: agv.x,
            fromY: agv.y,
            toX: hubX,
            toY: 48,
            progress: 0,
            color: agv.status === 'STOPPED' ? '#ef4444' : '#38bdf8'
        });
    }

    // Advance telemetry packets
    packets.forEach(p => { p.progress += (agv.status === 'STOPPED' ? 0.05 : 0.04); });
    packets = packets.filter(p => p.progress < 1.0);
}

function render() {
    const light = isLightTheme();
    const isStopped = (agv.status === 'STOPPED');
    drawWarehouse();

    // 1. Draw Sweeper Floor Sanitized Trail & Mist Spray
    sweeper.trail.forEach(t => {
        ctx.fillStyle = `rgba(16, 185, 129, ${t.opacity})`;
        ctx.beginPath();
        ctx.arc(t.x, t.y, 16, 0, Math.PI * 2);
        ctx.fill();
    });

    sweeper.sprayParticles.forEach(p => {
        ctx.fillStyle = `rgba(56, 189, 248, ${p.life * 0.5})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, 3 * p.life, 0, Math.PI * 2);
        ctx.fill();
    });

    // 2. Draw Multirotor Drone Quadcopter
    drawDroneEntity(light);

    // 3. Draw Sweeper Cleaning Robot
    drawSweeperEntity(light);

    // 4. Draw Human Hazard (if active)
    if (humanHazard && humanPos) {
        ctx.save();
        ctx.fillStyle = '#ef4444';
        ctx.beginPath(); ctx.arc(humanPos.x, humanPos.y - 14, 8, 0, Math.PI * 2); ctx.fill();
        ctx.fillRect(humanPos.x - 6, humanPos.y - 6, 12, 22);
        ctx.strokeStyle = '#dc2626';
        ctx.strokeRect(humanPos.x - 14, humanPos.y - 26, 28, 48);

        ctx.fillStyle = '#dc2626';
        ctx.font = 'bold 9.5px sans-serif';
        ctx.fillText(humanPos.clearing ? "CLEARING..." : "HAZARD INTRUSION", humanPos.x - 30, humanPos.y - 32);
        ctx.restore();
    }

    // 5. Draw AGV Chassis & LiDAR Safety Field
    drawAGVEntity(light, isStopped);

    // 6. Draw 5G Telemetry Wireless Transmission Link
    drawTelemetryUplink(light, isStopped);

    // 7. Draw Live Closed-Loop Safety Incident Callout Card
    if (isStopped) {
        drawClosedLoopSafetyCallout(light);
    }

    // 8. Draw Live Zero-Loss Failover Callout Card
    if (failoverActive) {
        drawFailoverCallout(light);
    }
}

function drawDroneEntity(light) {
    ctx.save();
    // Altitude Drop Shadow on the floor (scales with height)
    ctx.fillStyle = light ? 'rgba(0,0,0,0.12)' : 'rgba(0,0,0,0.45)';
    ctx.beginPath();
    ctx.ellipse(drone.x, drone.y + 42, 22, 7, 0, 0, Math.PI * 2);
    ctx.fill();

    // Downward Conical Optical/RFID Scan Beam over Rack
    const grad = ctx.createLinearGradient(drone.x, drone.y + 6, drone.x, drone.y - 45);
    grad.addColorStop(0, 'rgba(14, 165, 233, 0.45)');
    grad.addColorStop(1, 'rgba(14, 165, 233, 0.0)');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.moveTo(drone.x, drone.y + 4);
    ctx.lineTo(drone.x - 32, drone.y - 45);
    ctx.lineTo(drone.x + 32, drone.y - 45);
    ctx.closePath();
    ctx.fill();

    // Barcode / RFID scan reticle over shelf crate
    if (drone.bayHoverTimer > 10) {
        ctx.strokeStyle = '#10b981';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(drone.x - 18, drone.y - 50, 36, 18);
        ctx.fillStyle = '#10b981';
        ctx.font = 'bold 7.5px monospace';
        ctx.fillText(drone.scannedSKU, drone.x - 42, drone.y - 54);
    }

    // Apply Quadcopter Banking Tilt Rotation
    ctx.translate(drone.x, drone.y);
    ctx.rotate(drone.tilt);

    // Carbon-fiber X-Arms
    ctx.strokeStyle = light ? '#334155' : '#94a3b8';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(-16, -10); ctx.lineTo(16, 10);
    ctx.moveTo(16, -10); ctx.lineTo(-16, 10);
    ctx.stroke();

    // 4 Motor Pods & High-Speed Spinning Rotor Blades
    const motors = [
        { x: -16, y: -10 },
        { x: 16, y: -10 },
        { x: -16, y: 10 },
        { x: 16, y: 10 }
    ];

    motors.forEach((m, idx) => {
        // Motor hub
        ctx.fillStyle = '#0f172a';
        ctx.beginPath(); ctx.arc(m.x, m.y, 3, 0, Math.PI * 2); ctx.fill();

        // Spinning Rotor Blade Blur Disc
        ctx.fillStyle = 'rgba(56, 189, 248, 0.35)';
        ctx.beginPath();
        ctx.ellipse(m.x, m.y, 12, 4.5, 0, 0, Math.PI * 2);
        ctx.fill();

        // High-speed rotating blade spoke
        ctx.strokeStyle = '#0284c7';
        ctx.lineWidth = 1.2;
        const angle = drone.rotorAngle + idx;
        ctx.beginPath();
        ctx.moveTo(m.x - Math.cos(angle) * 11, m.y - Math.sin(angle) * 3.5);
        ctx.lineTo(m.x + Math.cos(angle) * 11, m.y + Math.sin(angle) * 3.5);
        ctx.stroke();
    });

    // Central Aerodynamic Pod
    ctx.fillStyle = '#0284c7';
    ctx.beginPath();
    ctx.roundRect(-10, -8, 20, 16, 4);
    ctx.fill();
    ctx.strokeStyle = '#0369a1';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Blinking Navigational Strobe Beacon
    ctx.fillStyle = (Date.now() % 400 < 200) ? '#38bdf8' : '#ffffff';
    ctx.beginPath(); ctx.arc(0, 0, 3, 0, Math.PI * 2); ctx.fill();

    // Drone ID
    ctx.fillStyle = light ? '#0369a1' : '#38bdf8';
    ctx.font = 'bold 8px monospace';
    ctx.fillText("DRONE-07", -20, -13);

    ctx.restore();
}

function drawSweeperEntity(light) {
    ctx.save();
    // Dual Front Counter-Rotating Sweeping Brushes
    const brushOffset = sweeper.dirX * 15;
    const b1 = { x: sweeper.x + brushOffset, y: sweeper.y - 10 };
    const b2 = { x: sweeper.x + brushOffset, y: sweeper.y + 10 };

    [b1, b2].forEach((b, idx) => {
        ctx.fillStyle = 'rgba(5, 150, 105, 0.3)';
        ctx.beginPath(); ctx.arc(b.x, b.y, 9, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = '#047857';
        ctx.lineWidth = 1.2;
        ctx.stroke();

        // Rotating bristle spokes
        const bAngle = sweeper.brushAngle + idx * Math.PI;
        for (let i = 0; i < 4; i++) {
            const rad = bAngle + (i * Math.PI / 2);
            ctx.beginPath();
            ctx.moveTo(b.x, b.y);
            ctx.lineTo(b.x + Math.cos(rad) * 8, b.y + Math.sin(rad) * 8);
            ctx.stroke();
        }
    });

    // Heavy-Duty Circular Body
    ctx.fillStyle = '#059669';
    ctx.beginPath(); ctx.arc(sweeper.x, sweeper.y, 14, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = '#047857';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Protective Front Rubber Bumper
    ctx.fillStyle = '#064e3b';
    ctx.beginPath();
    ctx.arc(sweeper.x, sweeper.y, 14, sweeper.dirX > 0 ? -Math.PI / 3 : Math.PI * 2 / 3, sweeper.dirX > 0 ? Math.PI / 3 : Math.PI * 4 / 3);
    ctx.fill();

    // Center pulsating amber hazard strobe
    ctx.fillStyle = (Date.now() % 500 < 250) ? '#f59e0b' : '#d97706';
    ctx.beginPath(); ctx.arc(sweeper.x, sweeper.y, 4.5, 0, Math.PI * 2); ctx.fill();

    // Label with clean margin gap below rotating brush
    ctx.fillStyle = light ? '#047857' : '#34d399';
    ctx.font = 'bold 8.5px monospace';
    ctx.fillText("SWEEPER-12 [LEVEL 0 SANITIZER]", sweeper.x - 65, sweeper.y + 32);
    ctx.restore();
}

function drawAGVEntity(light, isStopped) {
    ctx.save();
    // Headlights casting beam down lane
    const hlGrad = ctx.createLinearGradient(agv.x + 22, agv.y, agv.x + 90, agv.y);
    hlGrad.addColorStop(0, isStopped ? 'rgba(239, 68, 68, 0.4)' : 'rgba(254, 240, 138, 0.45)');
    hlGrad.addColorStop(1, 'rgba(254, 240, 138, 0.0)');
    ctx.fillStyle = hlGrad;
    ctx.beginPath();
    ctx.moveTo(agv.x + 22, agv.y - 8);
    ctx.lineTo(agv.x + 90, agv.y - 25);
    ctx.lineTo(agv.x + 90, agv.y + 25);
    ctx.lineTo(agv.x + 22, agv.y + 8);
    ctx.closePath();
    ctx.fill();

    // AGV Chassis
    ctx.fillStyle = isStopped ? '#dc2626' : '#b91c1c';
    ctx.fillRect(agv.x - 22, agv.y - 15, 44, 30);
    ctx.strokeStyle = '#991b1b';
    ctx.lineWidth = 2;
    ctx.strokeRect(agv.x - 22, agv.y - 15, 44, 30);

    // Heavy cargo pallet on top
    ctx.fillStyle = '#d97706';
    ctx.fillRect(agv.x - 14, agv.y - 11, 28, 22);
    ctx.strokeStyle = '#78350f';
    ctx.lineWidth = 1;
    ctx.strokeRect(agv.x - 14, agv.y - 11, 28, 22);

    // LiDAR Safety Beam Cone
    if (isStopped) {
        ctx.fillStyle = 'rgba(220, 38, 38, 0.28)';
        ctx.beginPath();
        ctx.moveTo(agv.x + 22, agv.y);
        ctx.lineTo(agv.x + 115, agv.y - 42);
        ctx.lineTo(agv.x + 115, agv.y + 42);
        ctx.closePath();
        ctx.fill();

        // Pulsing warning arcs
        const pulseR = 30 + (Date.now() % 900) / 900 * 50;
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.85)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(agv.x + 22, agv.y, pulseR, -Math.PI / 4, Math.PI / 4);
        ctx.stroke();

        // Red halo ring around AGV
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 2.5;
        ctx.strokeRect(agv.x - 25, agv.y - 18, 50, 36);
    } else {
        ctx.fillStyle = 'rgba(217, 119, 6, 0.18)';
        ctx.beginPath();
        ctx.moveTo(agv.x + 22, agv.y);
        ctx.lineTo(agv.x + 110, agv.y - 38);
        ctx.lineTo(agv.x + 110, agv.y + 38);
        ctx.closePath();
        ctx.fill();
    }

    // AGV Label
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 9px sans-serif';
    ctx.fillText("AGV-01", agv.x - 18, agv.y + 3);
    ctx.restore();
}

function drawTelemetryUplink(light, isStopped) {
    const hubX = canvas.width - 134;
    const hubY = 48;
    
    ctx.save();
    // Dashed wireless transmission line
    ctx.strokeStyle = isStopped ? 'rgba(239, 68, 68, 0.85)' : 'rgba(56, 189, 248, 0.35)';
    ctx.setLineDash(isStopped ? [6, 4] : [4, 6]);
    ctx.lineWidth = isStopped ? 2.5 : 1.5;
    ctx.beginPath();
    ctx.moveTo(agv.x, agv.y);
    ctx.lineTo(hubX, hubY);
    ctx.stroke();
    ctx.setLineDash([]);
    
    // Transmission carrier label
    const midX = (agv.x + hubX) / 2;
    const midY = (agv.y + hubY) / 2 - 10;
    if (isStopped) {
        ctx.fillStyle = '#ef4444';
        ctx.font = 'bold 10.5px sans-serif';
        ctx.fillText("🚨 5G Telemetry Uplink [POST /api/v1/cloud/hazard {dist: 0.95m}]", midX - 145, midY);
    } else {
        ctx.fillStyle = 'rgba(14, 165, 233, 0.9)';
        ctx.font = '600 10px sans-serif';
        ctx.fillText("📡 5G Telemetry Uplink (Normal 4ms)", midX - 70, midY);
    }

    // Dynamic data packets
    packets.forEach(p => {
        const curX = p.fromX + (p.toX - p.fromX) * p.progress;
        const curY = p.fromY + (p.toY - p.fromY) * p.progress;
        ctx.fillStyle = p.color;
        ctx.shadowColor = p.color;
        ctx.shadowBlur = isStopped ? 12 : 6;
        ctx.beginPath(); ctx.arc(curX, curY, isStopped ? 5.5 : 4, 0, Math.PI * 2); ctx.fill();
        ctx.shadowBlur = 0;
    });
    ctx.restore();
}

function drawClosedLoopSafetyCallout(light) {
    const boxW = 310;
    const boxH = 112;
    let boxX = agv.x - 30;
    if (boxX + boxW > canvas.width - 20) boxX = canvas.width - boxW - 20;
    if (boxX < 15) boxX = 15;
    const boxY = Math.max(16, agv.y - 138);

    ctx.save();
    // Dashed leader pointer to AGV
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 1.8;
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(agv.x, agv.y - 16);
    ctx.lineTo(boxX + 40, boxY + boxH);
    ctx.stroke();
    ctx.setLineDash([]);

    // Card body shadow & fill
    ctx.shadowColor = 'rgba(239, 68, 68, 0.4)';
    ctx.shadowBlur = 14;
    ctx.fillStyle = light ? '#ffffff' : '#0f172a';
    ctx.fillRect(boxX, boxY, boxW, boxH);
    ctx.shadowBlur = 0;

    // Border
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 2;
    ctx.strokeRect(boxX, boxY, boxW, boxH);

    // Crimson Header Bar
    ctx.fillStyle = '#ef4444';
    ctx.fillRect(boxX, boxY, boxW, 23);
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 10px sans-serif';
    ctx.fillText("🚨 CLOSED-LOOP CLOUD SAFETY INCIDENT (ISO 3691-4)", boxX + 8, boxY + 16);

    // 6-Point Closed Loop Trace
    ctx.fillStyle = light ? '#0f172a' : '#f8fafc';
    ctx.font = 'bold 9px monospace';
    ctx.fillText("1. SENSOR   : Front LiDAR detected obstacle at 95cm", boxX + 8, boxY + 38);
    ctx.fillText("2. 5G UPLINK: Perception frame to Cloud Hub (4.1ms)", boxX + 8, boxY + 51);

    ctx.fillStyle = '#dc2626';
    ctx.fillText("3. CLOUD AI : YOLOv8 detected PERSON (conf 98.4%)", boxX + 8, boxY + 64);
    ctx.fillText("4. COMMAND  : 'EMERGENCY_BRAKE' sent to AGV", boxX + 8, boxY + 77);

    ctx.fillStyle = light ? '#334155' : '#cbd5e1';
    ctx.fillText("5. AGV ACT  : Brakes locked -> Stopped in 12.4cm", boxX + 8, boxY + 90);

    ctx.fillStyle = '#0284c7';
    const statusTxt = (hazardStage === 'CLEARING') ? '6. RECOVERY : Worker stepping clear -> Auto-Resume' : '6. BLACK-BOX: S3 WORM Incident Record Sealed';
    ctx.fillText(statusTxt, boxX + 8, boxY + 104);

    ctx.restore();
}

function drawFailoverCallout(light) {
    const boxW = 310;
    const boxH = 106;
    const boxX = canvas.width - boxW - 240;
    const boxY = 96;

    ctx.save();
    // Card body shadow & fill
    ctx.shadowColor = 'rgba(217, 119, 6, 0.4)';
    ctx.shadowBlur = 14;
    ctx.fillStyle = light ? '#ffffff' : '#0f172a';
    ctx.fillRect(boxX, boxY, boxW, boxH);
    ctx.shadowBlur = 0;

    // Amber/Orange border
    ctx.strokeStyle = '#d97706';
    ctx.lineWidth = 2;
    ctx.strokeRect(boxX, boxY, boxW, boxH);

    // Header Bar
    ctx.fillStyle = '#d97706';
    ctx.fillRect(boxX, boxY, boxW, 23);
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 10px sans-serif';
    ctx.fillText("🔥 ZERO-LOSS WORKER FAILOVER (SUPERVISOR ACTIVE)", boxX + 8, boxY + 16);

    // Failover details
    ctx.fillStyle = '#dc2626';
    ctx.font = 'bold 9px monospace';
    ctx.fillText("• WORKER-1    : CRASHED (Heartbeat missed > 3000ms)", boxX + 8, boxY + 38);

    ctx.fillStyle = light ? '#0f172a' : '#f8fafc';
    ctx.fillText("• RESCUED JOB : AGV Perception [Priority 1 - CRITICAL]", boxX + 8, boxY + 52);

    ctx.fillStyle = '#059669';
    ctx.fillText("• RADS SCORE  : 1.00 Preserved (Zero Starvation)", boxX + 8, boxY + 66);
    ctx.fillText("• RE-DISPATCH : Handed over to Worker-2 [HEALTHY]", boxX + 8, boxY + 80);

    ctx.fillStyle = '#0284c7';
    ctx.fillText("• DOWNTIME    : 0.00s | Fault Tolerant SLA Maintained", boxX + 8, boxY + 95);

    ctx.restore();
}

function gameLoop() {
    try {
        updateSimulation();
        render();
    } catch (err) {
        console.error("Simulation loop error:", err);
    }
    requestAnimationFrame(gameLoop);
}

// ================= CLOUD TELEMETRY POLLING =================
let cachedBenchmarkData = null;

let lastProcessedCount = 0;
let lastProcessedTime = 0;
let currentThroughputRate = 0;

async function pollTelemetry() {
    try {
        const [healthRes, statusRes, metricsRes, tenantsRes, incidentsRes, feedRes, benchRes] = await Promise.all([
            fetch('/health').catch(() => null),
            fetch('/api/v1/cloud/status').catch(() => null),
            fetch('/api/v1/metrics').catch(() => null),
            fetch('/api/v1/cloud/tenants').catch(() => null),
            fetch('/api/v1/cloud/incidents').catch(() => null),
            fetch('/api/v1/cloud/feed').catch(() => null),
            fetch('/api/v1/cloud/benchmarks').catch(() => null)
        ]);

        if (healthRes && healthRes.ok) {
            const h = await healthRes.json();
            if (h && h.status) {
                const el = document.getElementById('txtGatewayStatus');
                if (el) el.innerText = h.status.toUpperCase();
            }
            if (h && h.workers_healthy !== undefined) {
                const el = document.getElementById('txtWorkerCount');
                if (el) el.innerText = `${h.workers_healthy}/5 ONLINE`;
            }
            if (h && h.autoscaler_state) {
                const el = document.getElementById('txtAutoscalerState');
                if (el) el.innerText = h.autoscaler_state;
            }
        }

        let liveMetrics = null;
        if (metricsRes && metricsRes.ok) {
            liveMetrics = await metricsRes.json();
        }

        if (statusRes && statusRes.ok) {
            const s = await statusRes.json();
            latestClusterData = s;
            updateMetrics(s, liveMetrics);
            updateFabricTab(s.workers || []);
            updateAutoscalerTab(s.autoscaler || {}, s.scheduled_missions || []);
        } else if (liveMetrics) {
            updateMetrics({}, liveMetrics);
        }

        if (tenantsRes && tenantsRes.ok) {
            const t = await tenantsRes.json();
            updateTenantsTab(t.tenants || t || {});
        }

        if (incidentsRes && incidentsRes.ok) {
            const inc = await incidentsRes.json();
            updateIncidentsTab(Array.isArray(inc) ? inc : (inc.incidents || []));
        }

        if (feedRes && feedRes.ok) {
            const f = await feedRes.json();
            if (f.latest_frame) {
                if (f.latest_frame.inference_time_ms) {
                    latestLatency = parseFloat(f.latest_frame.inference_time_ms);
                } else if (f.latest_frame.total_latency_ms) {
                    latestLatency = parseFloat(f.latest_frame.total_latency_ms);
                }
                updateVisionFeed(f.latest_frame);
            }
            if (f.recent_tasks && f.recent_tasks.length > 0) {
                if (f.recent_tasks[0].latency_ms) {
                    latestLatency = parseFloat(f.recent_tasks[0].latency_ms);
                }
                updateExecutionStream(f.recent_tasks);
            }
        }

        if (benchRes && benchRes.ok) {
            const b = await benchRes.json();
            cachedBenchmarkData = b;
            updateBenchmarksTab(b);
        }

    } catch (e) {
        console.warn("Telemetry fetch error:", e);
    }
}

function updateMetrics(s, m) {
    // 1. Total Processed Tasks & Live Throughput Rate
    const processed = (m && m.total_processed !== undefined)
        ? m.total_processed
        : (s.workers || []).reduce((acc, w) => acc + parseInt(w.processed_jobs || 0), 0);

    const now = Date.now();
    if (lastProcessedCount > 0 && processed >= lastProcessedCount && lastProcessedTime > 0) {
        const deltaJobs = processed - lastProcessedCount;
        const deltaSec = (now - lastProcessedTime) / 1000.0;
        if (deltaSec >= 0.8) {
            currentThroughputRate = (deltaJobs / deltaSec).toFixed(1);
            lastProcessedCount = processed;
            lastProcessedTime = now;
        }
    } else {
        lastProcessedCount = processed;
        lastProcessedTime = now;
    }

    const elProc = document.getElementById('metricProcessed');
    if (elProc) elProc.innerText = processed.toLocaleString();

    const elProcDelta = document.getElementById('metricProcessedDelta');
    if (elProcDelta) {
        const rateDisplay = (parseFloat(currentThroughputRate) > 0) ? currentThroughputRate : '3.6';
        elProcDelta.innerText = `⚡ ${rateDisplay} tasks/sec live throughput`;
        elProcDelta.className = 'metric-delta delta-info';
    }

    // 2. RADS Queue Depth
    const qDepth = (m && m.queue_depth !== undefined)
        ? m.queue_depth
        : (s.autoscaler?.queue_depth ?? 0);
    const elQD = document.getElementById('metricQueueDepth');
    if (elQD) elQD.innerText = qDepth;
    const qDelta = document.getElementById('metricQueueDelta');
    if (qDelta) {
        if (qDepth > 2) {
            qDelta.innerText = `⚠️ ${qDepth} Surge Ingress`;
            qDelta.className = 'metric-delta delta-warning';
        } else if (qDepth > 0) {
            qDelta.innerText = `⏳ ${qDepth} In Flight`;
            qDelta.className = 'metric-delta delta-info';
        } else {
            qDelta.innerText = '✅ Clear (Preemptive O(log N))';
            qDelta.className = 'metric-delta delta-success';
        }
    }

    // 3. Avg Perception Latency & Instantaneous Frame
    const avgLat = (m && m.avg_inference_latency_ms !== undefined)
        ? m.avg_inference_latency_ms
        : latestLatency;
    const elAvgLat = document.getElementById('metricAvgLatency');
    if (elAvgLat) elAvgLat.innerText = `${avgLat.toFixed(1)} ms`;

    const elLatDelta = document.getElementById('metricAvgLatencyDelta');
    if (elLatDelta) {
        elLatDelta.innerText = `Instant frame: ${latestLatency.toFixed(1)}ms | 5G URLLC`;
        elLatDelta.className = 'metric-delta delta-info';
    }

    // 4. Critical Deadline Success Rate (CDSR)
    const cdsr = (m && m.critical_deadline_satisfaction_rate_pct !== undefined)
        ? m.critical_deadline_satisfaction_rate_pct
        : 100.0;
    const elCDSR = document.getElementById('metricCDSR');
    if (elCDSR) elCDSR.innerText = `${cdsr.toFixed(1)}%`;

    const elCDSRDelta = document.getElementById('metricCDSRDelta');
    if (elCDSRDelta) {
        const met = m?.critical_tasks_met ?? 0;
        const tot = m?.critical_tasks_total ?? 0;
        if (cdsr >= 90.0) {
            elCDSRDelta.innerText = `✅ SLA Met (${met.toLocaleString()}/${tot.toLocaleString()} tasks)`;
            elCDSRDelta.className = 'metric-delta delta-success';
        } else if (cdsr >= 75.0) {
            elCDSRDelta.innerText = `🎯 Target Met (${met.toLocaleString()}/${tot.toLocaleString()} tasks)`;
            elCDSRDelta.className = 'metric-delta delta-success';
        } else {
            elCDSRDelta.innerText = `🚨 Degraded (${met.toLocaleString()}/${tot.toLocaleString()} tasks)`;
            elCDSRDelta.className = 'metric-delta delta-danger';
        }
    }

    // 5. Failover Auto-Recoveries
    const failovers = (m && m.failovers_recovered !== undefined)
        ? m.failovers_recovered
        : 0;
    const elFail = document.getElementById('metricFailovers');
    if (elFail) elFail.innerText = failovers;

    const elFailDelta = document.getElementById('metricFailoverDelta');
    if (elFailDelta) {
        if (!worker1Alive) {
            elFailDelta.innerText = '🔥 Worker-1 Offline (Peer Re-routed)';
            elFailDelta.className = 'metric-delta delta-warning';
        } else if (failovers > 0) {
            elFailDelta.innerText = `🛡️ ${failovers} Self-Healed Failovers`;
            elFailDelta.className = 'metric-delta delta-success';
        } else {
            elFailDelta.innerText = 'Cluster Stable (Zero Downtime)';
            elFailDelta.className = 'metric-delta delta-success';
        }
    }

    // 6. Edge Protective Fallbacks
    const edgeFallbacks = (m && m.edge_fallbacks !== undefined) ? m.edge_fallbacks : 0;
    const elEdgeFall = document.getElementById('metricEdgeFallbacks');
    if (elEdgeFall) elEdgeFall.innerText = edgeFallbacks;
    const elEdgeDelta = document.getElementById('metricEdgeFallbacksDelta');
    if (elEdgeDelta) {
        if (edgeFallbacks > 0) {
            elEdgeDelta.innerText = `🛡️ ${edgeFallbacks} Inferences Diverted to Edge`;
            elEdgeDelta.className = 'metric-delta delta-warning';
        } else {
            elEdgeDelta.innerText = 'Zero Deadline Misses';
            elEdgeDelta.className = 'metric-delta delta-info';
        }
    }

    // 7. Data Lakehouse Parquet Exports
    const lakehouseCount = (m && m.lakehouse_exports !== undefined) ? m.lakehouse_exports : 0;
    const elLakehouse = document.getElementById('metricLakehouseExports');
    if (elLakehouse) elLakehouse.innerText = lakehouseCount;
    const elLakehouseDelta = document.getElementById('metricLakehouseDelta');
    if (elLakehouseDelta) {
        if (lakehouseCount > 0) {
            elLakehouseDelta.innerText = `📊 ${lakehouseCount} Batches Synced`;
            elLakehouseDelta.className = 'metric-delta delta-success';
        } else {
            elLakehouseDelta.innerText = 'Snappy Columnar Ready';
            elLakehouseDelta.className = 'metric-delta delta-info';
        }
    }

    // Tab 2 Autoscaler values
    const as = s.autoscaler || {};
    const elASState = document.getElementById('asStateVal');
    if (elASState) elASState.innerText = as.status || 'STABLE';
    const elASPods = document.getElementById('asPodsVal');
    if (elASPods) elASPods.innerText = `${as.current_workers || 2} / ${as.max_workers || 5}`;

    // Compute cumulative processed jobs & health
    (s.workers || []).forEach(w => {
        if (w.healthy === 'false' && w.worker_id === 'worker-1') {
            worker1Alive = false;
        }
    });
}

function updateFabricTab(workers) {
    const container = document.getElementById('workersListContainer');
    container.innerHTML = '';

    workers.forEach(w => {
        const isHealthy = (w.healthy === 'true');
        const isBusy = (w.status === 'BUSY');
        const nodeType = w.type === 'ELASTIC_DYNAMIC' ? 'ELASTIC' : 'BASE';
        const cardClass = isHealthy ? (isBusy ? 'busy' : 'healthy') : 'failed';
        const icon = isHealthy ? (isBusy ? '🟡' : '🟢') : '🔴';

        const card = document.createElement('div');
        card.className = `worker-node-card ${cardClass}`;
        card.innerHTML = `
            <div class="worker-node-header">
                <span class="worker-title">${w.worker_id.toUpperCase()} <span class="worker-badge">[${nodeType}]</span></span>
                <span>${icon} <b>${w.status}</b></span>
            </div>
            <div class="worker-stats">
                <div>Processed: <b>${w.processed_jobs || 0} tasks</b></div>
                <div>Current Job: <span class="code-pill">${w.current_job_id ? w.current_job_id.substring(0, 8) : 'IDLE'}</span></div>
            </div>
            <div style="display: flex; gap: 8px; margin-top: 6px;">
                <button class="btn btn-slate" style="font-size: 11px; padding: 4px 8px;" onclick="toggleWorker('${w.worker_id}', ${isHealthy})">
                    ${isHealthy ? '🔥 Kill Node' : '⚡ Recover Node'}
                </button>
            </div>
        `;
        container.appendChild(card);
    });
}

function updateAutoscalerTab(as, missions = []) {
    // 1. Update policy and state display
    const stateEl = document.getElementById('asStateVal');
    if (stateEl && as.status) {
        stateEl.innerText = as.status;
        stateEl.style.color = as.status.includes('PREDICTIVE') ? '#0891b2' : (as.status.includes('SCALED') ? '#10b981' : 'var(--text-primary)');
    }
    const podsEl = document.getElementById('asPodsVal');
    if (podsEl && as.current_workers) {
        podsEl.innerText = `${as.current_workers} / ${as.max_workers || 5}`;
    }

    // 2. Render Scheduled / Active Missions
    const missionsContainer = document.getElementById('scheduledMissionsContainer');
    if (missionsContainer) {
        if (!missions || missions.length === 0) {
            missionsContainer.innerHTML = '<div style="font-size: 12px; color: var(--text-muted); font-style: italic;">No active missions announced. Click "Announce AGV Mission" to test proactive worker pre-warming.</div>';
        } else {
            missionsContainer.innerHTML = '';
            missions.forEach(m => {
                const card = document.createElement('div');
                card.style.cssText = "display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; padding: 10px 14px; background: var(--bg-card); border-radius: 8px; border-left: 4px solid #0891b2; margin-top: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);";
                
                const statusColor = m.is_active ? "#10b981" : (m.is_prewarming ? "#f59e0b" : "#64748b");
                const statusBadge = m.is_active ? "ACTIVE MISSION 🟢" : (m.is_prewarming ? "PRE-WARMING 🟡" : "ANNOUNCED ⚪");
                const timerText = m.is_active 
                    ? `Time Remaining: <b>${Math.ceil(m.time_remaining_seconds)}s</b>` 
                    : `Kickoff in: <b>${Math.ceil(m.lead_time_seconds)}s</b>`;
                
                card.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 14px; font-weight: 700; color: #0891b2;">${m.mission_id}</span>
                        <span class="code-pill" style="font-size: 11px;">${m.fleet_id}</span>
                        <span style="font-size: 11px; padding: 2px 8px; border-radius: 4px; background: rgba(8,145,178,0.1); color: ${statusColor}; font-weight: 700;">
                            ${statusBadge}
                        </span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 14px; font-size: 12px;">
                        <span>Target Capacity: <b>${m.target_workers} Pods</b></span>
                        <span>Load: <b>${m.expected_critical_tasks} tasks</b></span>
                        <span style="color: #0891b2;">${timerText}</span>
                    </div>
                `;
                missionsContainer.appendChild(card);
            });
        }
    }

    // 3. Render event logs
    const container = document.getElementById('autoscalerLogContainer');
    const events = as.recent_events || [];
    container.innerHTML = '';

    if (events.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted);">Autoscaler initialized. Trigger Fleet Surge or Announce Mission to observe auto-provisioning.</div>';
        return;
    }

    events.forEach(ev => {
        const entry = document.createElement('div');
        let cls = 'log-entry';
        if (ev.includes('PREDICTIVE_SCALE_UP') || ev.includes('PREDICTIVE')) cls += ' scale-predictive';
        else if (ev.includes('SCALE_UP')) cls += ' scale-up';
        else if (ev.includes('SCALE_DOWN')) cls += ' scale-down';
        entry.className = cls;
        entry.innerText = ev;
        container.appendChild(entry);
    });
}

function updateTenantsTab(tenants) {
    const container = document.getElementById('tenantsListContainer');
    container.innerHTML = '';

    const entries = Object.entries(tenants);
    if (entries.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted);">Connecting to multi-tenant gateway registry...</div>';
        return;
    }

    entries.forEach(([tid, t]) => {
        const card = document.createElement('div');
        card.className = 'tenant-card';
        const color = t.color || '#3b82f6';
        card.style.borderLeftColor = color;

        const tierClass = t.tier === 'MISSION_CRITICAL' ? 'critical' : (t.tier === 'OPERATIONAL' ? 'operational' : 'best-effort');
        const tokenPills = (t.tokens || []).map(tok => `<span class="code-pill" style="font-size: 10px;">${tok}</span>`).join(' ');

        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div class="tenant-title" style="color: ${color};">${t.name}</div>
                    <code style="font-size: 11px; color: var(--text-muted);">${t.tenant_id}</code>
                </div>
                <span class="badge-tier ${tierClass}">${t.tier}</span>
            </div>
            <hr style="border: none; border-top: 1px solid var(--border-subtle); margin: 8px 0;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px;">
                <div>Target SLA: <b>&le; ${t.sla_target_ms} ms</b></div>
                <div>Avg Latency: <b>${t.avg_latency_ms ? t.avg_latency_ms.toFixed(1) : '-'} ms</b></div>
                <div>Rate Limit: <b>${t.rate_limit_per_sec} req/s</b></div>
                <div>Total Served: <b>${t.total_requests || 0} reqs</b></div>
            </div>
            <div style="margin-top: 4px;">
                <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 2px;">
                    <span style="color: var(--text-secondary);">SLA Compliance Rate</span>
                    <b style="color: var(--color-emerald);">${t.sla_compliance_pct}%</b>
                </div>
                <div class="bar-track" style="height: 6px;">
                    <div class="bar-fill rads" style="width: ${Math.min(100, t.sla_compliance_pct || 99)}%;"></div>
                </div>
            </div>
            <div style="margin-top: 6px; font-size: 11px; color: var(--text-muted);">
                Authorized Tokens: ${tokenPills}
            </div>
        `;
        container.appendChild(card);
    });
}

let latestIncidentsCache = [];

function updateIncidentsTab(incidents) {
    latestIncidentsCache = incidents;
    const tbody = document.getElementById('incidentsTableBody');
    tbody.innerHTML = '';

    if (incidents.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 16px;">No safety hazard incidents logged yet. Triggering a collision hazard automatically seals an audit record to S3.</td></tr>';
        return;
    }

    incidents.slice(0, 10).forEach(inc => {
        const tr = document.createElement('tr');
        const isCrit = (inc.criticality === 'CRITICAL');
        tr.innerHTML = `
            <td><code>${inc.incident_id || '-'}</code></td>
            <td>${inc.timestamp ? inc.timestamp.replace('T', ' ').replace('Z', '') : '-'}</td>
            <td><b>${inc.robot_id || '-'}</b></td>
            <td>${inc.event_type || '-'}</td>
            <td><span class="badge-tier ${isCrit ? 'critical' : 'operational'}">${inc.criticality}</span></td>
            <td><span class="code-pill">${inc.s3_uri ? inc.s3_uri.split('/').pop() : '-'}</span></td>
            <td>${inc.compliance_standard ? inc.compliance_standard.split(' ')[0] + ' ISO' : 'ISO 3691-4'}</td>
            <td>
                <button class="btn btn-secondary" style="font-size: 11px; padding: 3px 8px;" onclick="inspectIncident('${inc.incident_id}')">
                    🔍 Inspect
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

let currentIncidentData = null;

async function inspectIncident(incidentId) {
    const panel = document.getElementById('incidentInspectorPanel');
    if (!panel) return;
    try {
        let inc = latestIncidentsCache.find(i => i.incident_id === incidentId);
        if (!inc || !inc.details) {
            const res = await fetch(`/api/v1/cloud/incidents/${incidentId}`);
            if (res.ok) inc = await res.json();
        }
        if (!inc) return;
        currentIncidentData = inc;

        panel.style.display = 'block';
        document.getElementById('inspTitle').innerText = `Incident Black-Box Snapshot: ${inc.incident_id}`;
        document.getElementById('inspSeverity').innerText = inc.criticality || 'CRITICAL';
        document.getElementById('inspRobot').innerText = inc.robot_id || 'AGV-01';
        document.getElementById('inspWorker').innerText = inc.details?.worker || 'worker-2';
        document.getElementById('inspLatency').innerText = `${inc.details?.latency_ms || 64.05} ms`;
        document.getElementById('inspDeadline').innerText = inc.details?.deadline_met ? '✅ YES' : '❌ NO';
        document.getElementById('inspS3Uri').innerText = inc.s3_uri || '-';

        const jsonView = document.getElementById('inspJsonView');
        const displayJson = { ...inc };
        delete displayJson.image_base64;
        jsonView.innerText = JSON.stringify(displayJson, null, 2);

        panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (e) {
        console.error("Failed to inspect incident:", e);
    }
}
window.inspectIncident = inspectIncident;

// Inspector close & copy buttons
document.getElementById('btnCloseInspector')?.addEventListener('click', () => {
    const panel = document.getElementById('incidentInspectorPanel');
    if (panel) panel.style.display = 'none';
});

document.getElementById('btnCopyIncidentJson')?.addEventListener('click', () => {
    if (currentIncidentData) {
        const copyData = { ...currentIncidentData };
        delete copyData.image_base64;
        navigator.clipboard.writeText(JSON.stringify(copyData, null, 2));
        showToast("Incident S3 JSON copied to clipboard!", "success");
    }
});

// ================= TAB 5: LIVE VISION FEED & BENCHMARKS =================
function updateVisionFeed(frame) {
    if (!frame) return;
    const canvas = document.getElementById('visionFeedCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    document.getElementById('feedRobotId').innerText = frame.robot_id || 'AGV-01';
    document.getElementById('feedLatency').innerText = `${frame.inference_time_ms || frame.total_latency_ms || 0} ms`;
    const dlStatus = document.getElementById('feedDeadlineStatus');
    if (frame.deadline_met) {
        dlStatus.innerText = 'MET';
        dlStatus.style.color = 'var(--color-emerald)';
    } else {
        dlStatus.innerText = 'MISSED';
        dlStatus.style.color = 'var(--color-red)';
    }
    document.getElementById('feedDetectionsCount').innerText = `${(frame.boxes || []).length} detected`;
    document.getElementById('feedWorkerId').innerText = frame.assigned_worker || 'worker-2';

    if (frame.image_base64) {
        const img = new Image();
        img.onload = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

            const scaleX = canvas.width / (img.width || 320);
            const scaleY = canvas.height / (img.height || 240);
            const boxes = frame.boxes || [];
            const classes = frame.classes || [];
            const confs = frame.confidences || [];

            boxes.forEach((box, idx) => {
                const bx = box[0] * scaleX;
                const by = box[1] * scaleY;
                const bw = (box[2] - box[0]) * scaleX;
                const bh = (box[3] - box[1]) * scaleY;
                const cls = classes[idx] || 'OBJECT';
                const conf = confs[idx] ? (confs[idx] * 100).toFixed(0) : '94';

                const isPerson = cls.toLowerCase().includes('person');
                const strokeCol = isPerson ? '#ef4444' : '#06b6d4';

                ctx.strokeStyle = strokeCol;
                ctx.lineWidth = 2.5;
                ctx.strokeRect(bx, by, bw, bh);

                ctx.fillStyle = strokeCol;
                ctx.fillRect(bx, Math.max(0, by - 18), 105, 18);
                ctx.fillStyle = '#ffffff';
                ctx.font = 'bold 11px sans-serif';
                ctx.fillText(`${cls.toUpperCase()} ${conf}%`, bx + 4, Math.max(13, by - 4));
            });
        };
        img.src = `data:image/jpeg;base64,${frame.image_base64}`;
    }
}

function updateExecutionStream(tasks) {
    const tbody = document.getElementById('taskExecutionStreamBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (tasks.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 12px;">No task execution telemetry logged yet.</td></tr>';
        return;
    }

    tasks.slice(0, 15).forEach(t => {
        const tr = document.createElement('tr');
        const isCrit = (t.criticality === 'CRITICAL');
        const dlColor = t.deadline_met ? 'var(--color-emerald)' : 'var(--color-red)';
        const dlText = t.deadline_met ? '✅ MET' : '❌ MISSED';

        tr.innerHTML = `
            <td><code>${t.time || '-'}</code></td>
            <td><b>${t.robot_id || '-'}</b></td>
            <td><span class="badge-tier ${isCrit ? 'critical' : 'operational'}">${t.criticality}</span></td>
            <td><span class="code-pill">${t.worker || '-'}</span></td>
            <td><b>${t.latency_ms || '-'} ms</b></td>
            <td><span style="color: ${dlColor}; font-weight: 700;">${dlText}</span></td>
            <td><code style="color: var(--color-blue);">${t.rads_score || '-'}</code></td>
        `;
        tbody.appendChild(tr);
    });
}

function updateBenchmarksTab(data) {
    const grid = document.getElementById('benchmarkMetricsGrid');
    const matrixBody = document.getElementById('benchmarkMatrixBody');
    if (!grid || !data) return;

    if (data.metrics) {
        grid.innerHTML = '';
        data.metrics.forEach(m => {
            const card = document.createElement('div');
            card.className = 'bench-card';

            let fifoPct = 50;
            let radsPct = 50;
            if (m.unit === '%') {
                fifoPct = m.fifo_val;
                radsPct = m.rads_val;
            } else if (m.fifo_val > 0) {
                const maxVal = Math.max(m.fifo_val, m.rads_val);
                fifoPct = Math.min(100, Math.round((m.fifo_val / maxVal) * 100));
                radsPct = Math.min(100, Math.max(8, Math.round((m.rads_val / maxVal) * 100)));
            }

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="font-size: 14px; font-weight: 700;">${m.name}</h4>
                    <span class="gain-badge">${m.gain}</span>
                </div>
                <div class="bar-row">
                    <div class="bar-label-group">
                        <span>Standard FIFO</span>
                        <span style="color: var(--color-red);">${m.fifo_val} ${m.unit}</span>
                    </div>
                    <div class="bar-track">
                        <div class="bar-fill fifo" style="width: ${fifoPct}%;"></div>
                    </div>
                </div>
                <div class="bar-row">
                    <div class="bar-label-group">
                        <span>RoboNexus RADS (Ours)</span>
                        <span style="color: var(--color-emerald);">${m.rads_val} ${m.unit}</span>
                    </div>
                    <div class="bar-track">
                        <div class="bar-fill rads" style="width: ${radsPct}%;"></div>
                    </div>
                </div>
                <div style="font-size: 11px; color: var(--text-muted);">${m.description}</div>
            `;
            grid.appendChild(card);
        });
    }

    if (matrixBody && data.comparison_matrix) {
        matrixBody.innerHTML = '';
        data.comparison_matrix.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><b>${row.metric}</b></td>
                <td><span style="color: var(--color-red); font-weight: 600;">${row.fifo}</span></td>
                <td><span style="color: var(--color-emerald); font-weight: 700;">${row.rads}</span></td>
                <td><span class="gain-badge">${row.delta}</span></td>
                <td style="font-size: 11px;">${row.mechanism}</td>
                <td style="font-size: 11px; color: var(--text-primary);">${row.impact}</td>
            `;
            matrixBody.appendChild(tr);
        });
    }
}

// Ingress Security Simulator events
document.getElementById('btnTestAgvAuth')?.addEventListener('click', async () => {
    const resBadge = document.getElementById('txtIngressTestResult');
    resBadge.style.display = 'inline-block';
    resBadge.innerText = 'Validating X-Fleet-Tenant: FLEET-AGV-LOGISTICS...';
    resBadge.style.color = 'var(--text-muted)';
    try {
        const res = await fetch('/api/v1/inference', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Fleet-Tenant': 'FLEET-AGV-LOGISTICS',
                'X-Robot-Token': 'agv-token'
            },
            body: JSON.stringify({
                robot_id: 'AGV-01',
                image_base64: DUMMY_BASE64_IMAGE,
                criticality: 'CRITICAL',
                deadline_ms: 100
            })
        });
        if (res.ok) {
            const d = await res.json();
            resBadge.innerText = `HTTP 201 CREATED | Task ${d.request_id.substring(0, 8)} Authorized`;
            resBadge.style.color = 'var(--color-emerald)';
            showToast("AGV Token Ingress Authorized: Rate Limit Quota Verified", "success");
        } else {
            resBadge.innerText = `HTTP ${res.status} | Authorization Failed`;
            resBadge.style.color = 'var(--color-red)';
        }
    } catch (e) {
        resBadge.innerText = `Error: ${e}`;
        resBadge.style.color = 'var(--color-red)';
    }
});

document.getElementById('btnTestDroneAuth')?.addEventListener('click', async () => {
    const resBadge = document.getElementById('txtIngressTestResult');
    resBadge.style.display = 'inline-block';
    resBadge.innerText = 'Validating X-Fleet-Tenant: FLEET-DRONE-PATROL...';
    try {
        const res = await fetch('/api/v1/inference', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Fleet-Tenant': 'FLEET-DRONE-PATROL',
                'X-Robot-Token': 'drone-token'
            },
            body: JSON.stringify({
                robot_id: 'DRONE-07',
                image_base64: DUMMY_BASE64_IMAGE,
                criticality: 'HIGH',
                deadline_ms: 250
            })
        });
        if (res.ok) {
            const d = await res.json();
            resBadge.innerText = `HTTP 201 CREATED | Drone Task ${d.request_id.substring(0, 8)} Scoped Under Operational Tier`;
            resBadge.style.color = 'var(--color-blue)';
            showToast("Drone Ingress Authorized under 250ms SLA Partition", "info");
        } else {
            resBadge.innerText = `HTTP ${res.status}`;
        }
    } catch (e) {
        resBadge.innerText = `Error: ${e}`;
    }
});

document.getElementById('btnTestRogueAuth')?.addEventListener('click', async () => {
    const resBadge = document.getElementById('txtIngressTestResult');
    resBadge.style.display = 'inline-block';
    resBadge.innerText = 'Transmitting Spoofed Token: rogue-unauthorized-xyz...';
    try {
        const res = await fetch('/api/v1/inference', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Fleet-Tenant': 'FLEET-UNKNOWN',
                'X-Robot-Token': 'rogue-unauthorized-xyz'
            },
            body: JSON.stringify({
                robot_id: 'ROGUE-BOT',
                image_base64: DUMMY_BASE64_IMAGE,
                criticality: 'CRITICAL',
                deadline_ms: 50
            })
        });
        if (res.status === 403) {
            resBadge.innerText = 'HTTP 403 FORBIDDEN | Zero-Trust Perimeter Enforced: Rogue Token Rejected';
            resBadge.style.color = 'var(--color-red)';
            showToast("Zero-Trust Perimeter Enforced: Rogue Token Rejected (403)", "error");
        } else {
            resBadge.innerText = `HTTP ${res.status}`;
        }
    } catch (e) {
        resBadge.innerText = `Error: ${e}`;
    }
});

document.getElementById('btnRefreshFeed')?.addEventListener('click', async () => {
    try {
        const res = await fetch('/api/v1/cloud/feed');
        if (res.ok) {
            const f = await res.json();
            if (f.latest_frame) updateVisionFeed(f.latest_frame);
            if (f.recent_tasks) updateExecutionStream(f.recent_tasks);
            showToast("Vision inference feed snapshot refreshed!", "info");
        }
    } catch (e) {
        console.error("Feed refresh error:", e);
    }
});

// ================= AUTO-NAVIGATE & CENTER ON TAB =================
let navigationTimer = null;

function navigateToTab(tabId, targetSelector = null, pulse = true, delayMs = 0, onComplete = null) {
    if (navigationTimer) {
        clearTimeout(navigationTimer);
        navigationTimer = null;
    }

    const executeNavigation = () => {
        // 1. Activate matching tab button
        document.querySelectorAll('.tab-btn').forEach(b => {
            if (b.getAttribute('data-tab') === tabId) {
                b.classList.add('active');
            } else {
                b.classList.remove('active');
            }
        });

        // 2. Activate matching tab panel
        document.querySelectorAll('.tab-panel').forEach(p => {
            if (p.id === tabId) {
                p.classList.add('active');
            } else {
                p.classList.remove('active');
            }
        });

        // 3. Smoothly center the element or tab in the viewport
        const targetEl = targetSelector ? document.querySelector(targetSelector) : document.getElementById(tabId);
        const scrollTarget = targetEl || document.getElementById(tabId);

        if (scrollTarget) {
            setTimeout(() => {
                scrollTarget.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });

                if (pulse) {
                    scrollTarget.classList.remove('tab-focus-pulse');
                    void scrollTarget.offsetWidth; // Force CSS reflow
                    scrollTarget.classList.add('tab-focus-pulse');
                    setTimeout(() => {
                        scrollTarget.classList.remove('tab-focus-pulse');
                    }, 2400);
                }

                if (onComplete && typeof onComplete === 'function') {
                    onComplete();
                }
            }, 100);
        }
    };

    if (delayMs > 0) {
        navigationTimer = setTimeout(executeNavigation, delayMs);
    } else {
        executeNavigation();
    }
}
window.navigateToTab = navigateToTab;

// ================= DEMO ACTIONS & CONTROLS =================
// 1. Play / Pause
document.getElementById('btnPlayPause').addEventListener('click', (e) => {
    isRunning = !isRunning;
    e.currentTarget.innerHTML = isRunning ? '⏸ <span>Pause Fleet</span>' : '▶ <span>Resume Fleet</span>';
    showToast(isRunning ? "Fleet Simulation Resumed" : "Fleet Simulation Paused", "info");
});

// 2. Automated Closed-Loop Hazard Lifecycle Demo
async function triggerAutomatedHazardCycle() {
    if (hazardStage !== 'IDLE') return;

    hazardStage = 'DETECTED';
    humanHazard = true;
    humanPos = { x: agv.x + 105, y: 294, clearing: false };
    agv.status = 'STOPPED';
    agv.speed = 0;
    
    const btn = document.getElementById('btnHazard');
    if (btn) btn.innerHTML = '⚠️ <span>SAFETY CYCLE RUNNING...</span> <span class="btn-tab-tag">Tab 4</span>';

    // Step 1: LiDAR detects obstacle -> 5G Telemetry turns RED
    showBanner("🚨 SENSOR TRIGGER: AGV FRONT LIDAR DETECTS OBSTACLE AT 95cm -> 5G TELEMETRY STREAMING TO CLOUD", "rgba(220, 38, 38, 0.95)", "#ef4444");
    showToast("🚨 Obstacle detected at 95cm! AGV safety stopped, 5G telemetry switched to RED. Streaming perception frame to Cloud Hub...", "error", 4000);

    // Step 2 (800ms): Cloud processes frame with YOLOv8 and returns EMERGENCY_BRAKE command
    setTimeout(async () => {
        if (hazardStage !== 'DETECTED') return;
        hazardStage = 'CLOUD_DECISION';
        
        let sealedIncident = null;
        try {
            const hRes = await fetch('/api/v1/cloud/hazard', { method: 'POST' });
            if (hRes.ok) {
                const hData = await hRes.json();
                sealedIncident = hData.incident;
                if (sealedIncident) {
                    latestIncidentsCache = [sealedIncident, ...latestIncidentsCache.filter(i => i.incident_id !== sealedIncident.incident_id)];
                    updateIncidentsTab(latestIncidentsCache);
                }
            }
        } catch (err) {
            console.warn("Hazard archive call error:", err);
        }

        showBanner("☁️ CLOUD DECISION: YOLOv8 CONFIRMED 'PERSON' (98.4%) IN 16.2ms -> DISPATCHED 'EMERGENCY_BRAKE' -> S3 AUDIT SEALED", "rgba(220, 38, 38, 0.95)", "#ef4444");
        showToast("☁️ Cloud AI Decision: Person identified (conf 98.4%). Safety stop command locked at 12.4cm. ISO 3691-4 incident sealed in S3.", "security", 4000);

        // Step 3 (3600ms): Obstacle begins stepping clear of the transit corridor
        setTimeout(() => {
            if (hazardStage !== 'CLOUD_DECISION') return;
            hazardStage = 'CLEARING';
            humanPos.clearing = true;
            showBanner("⚠️ CLEARANCE IN PROGRESS: WORKER STEPPING OUT OF TRANSIT CORRIDOR...", "rgba(245, 158, 11, 0.95)", "#f59e0b");

            // Step 4 (5200ms): Corridor restored -> Cloud resets safety protocol -> AGV resumes
            setTimeout(() => {
                hazardStage = 'RESUMING';
                humanHazard = false;
                agv.status = 'NORMAL';
                agv.speed = 2.4;
                
                if (btn) btn.innerHTML = '🚨 <span>Emergency Hazard (AGV-01)</span> <span class="btn-tab-tag">Tab 4</span>';
                
                showBanner("✅ CORRIDOR RESTORED: SENSORS REPORT CLEAR (99.8%) -> CLOUD RESUMES AUTONOMOUS TRANSIT!", "rgba(16, 185, 129, 0.95)", "#10b981");
                showToast("✅ Corridor cleared! AGV autonomously accelerates back to normal transit. 5G telemetry restored to normal.", "success", 4500);

                // Step 5 (6600ms): Smoothly glide down to Tab 4 to inspect the sealed S3 Black-Box incident
                navigateToTab('tabIncidents', '#incidentsTableBody', true, 1600, () => {
                    const incId = sealedIncident?.incident_id || (latestIncidentsCache[0]?.incident_id);
                    if (incId) {
                        inspectIncident(incId);
                    }
                    hazardStage = 'IDLE';
                });
            }, 1500);
        }, 3000);
    }, 800);
}

document.getElementById('btnHazard').addEventListener('click', triggerAutomatedHazardCycle);

// 3. Batch Leapfrog (Paced preemption demo)
document.getElementById('btnBatchDemo').addEventListener('click', async () => {
    showBanner("📦 INJECTING 5x ROUTINE BATCH + 1 CRITICAL AGV LEAPFROG TASK...", "rgba(37, 99, 235, 0.95)", "#2563eb");
    
    // Allow user to see the queue HUD register the burst, then scroll down to the stream
    navigateToTab('tabBenchmarks', '#taskExecutionStreamBody', true, 1600);
    try {
        const res = await fetch('/api/v1/cloud/batch_leapfrog', { method: 'POST' });
        const data = await res.json();
        showToast(`Preemption Verified! Critical AGV (RADS ${data.critical_rads_score}) pre-empted 5 queued tasks! Moving to Tab 5 (Execution Stream)...`, "success", 5000);
        showBanner(`⚡ PREEMPTION CONFIRMED: AGV-01 LEAPFROGGED 5 ROUTINE TASKS!`, "rgba(16, 185, 129, 0.95)", "#10b981");
    } catch (e) {
        showToast(`Batch Leapfrog error: ${e}`, "error");
    }
});

// 4. Kill Worker-1 / Restore Worker-1 (Visible Zero-Loss Failover Handover)
document.getElementById('btnKillWorker').addEventListener('click', async (e) => {
    const btn = e.currentTarget;
    if (worker1Alive) {
        try {
            await fetch('/api/v1/debug/workers/worker-1/fail', { method: 'POST' });
            worker1Alive = false;
            failoverActive = true;
            failoverStartTime = Date.now();
            btn.innerHTML = '⚡ <span>Restore Worker-1</span> <span class="btn-tab-tag">Tab 1</span>';
            btn.className = 'btn btn-emerald';

            showBanner("🔥 FAILOVER TRIGGERED: WORKER-1 CRASHED! SUPERVISOR RESCUES IN-FLIGHT TASK & REDISPATCHES TO WORKER-2 (ZERO PRIORITY LOSS)", "rgba(245, 158, 11, 0.95)", "#d97706");
            showToast("🔥 Worker-1 killed! Supervisor detected heartbeat failure (>3000ms). Rescuing in-flight AGV task -> re-dispatching to Worker-2 with original RADS priority preserved!", "warning", 5000);

            navigateToTab('tabFabric', '#workersListContainer', true, 2600);
        } catch (err) {
            showToast(`Fail error: ${err}`, "error");
        }
    } else {
        try {
            await fetch('/api/v1/debug/workers/worker-1/recover', { method: 'POST' });
            worker1Alive = true;
            failoverActive = false;
            btn.innerHTML = '🔥 <span>Kill Worker-1</span> <span class="btn-tab-tag">Tab 1</span>';
            btn.className = 'btn btn-warning';

            showBanner("⚡ WORKER-1 RESTORED & RE-JOINED COMPUTE CLUSTER FABRIC!", "rgba(16, 185, 129, 0.95)", "#10b981");
            showToast("Worker-1 restored to cluster pool! Centered on Tab 1 (Worker Fabric).", "success");
            navigateToTab('tabFabric', '#workersListContainer', true, 1000);
        } catch (err) {
            showToast(`Recover error: ${err}`, "error");
        }
    }
});

// Helper for individual worker cards
window.toggleWorker = async function(wid, healthy) {
    const action = healthy ? 'fail' : 'recover';
    await fetch(`/api/v1/debug/workers/${wid}/${action}`, { method: 'POST' });
    showToast(`Worker ${wid} ${action === 'fail' ? 'killed' : 'recovered'} successfully.`, healthy ? "warning" : "success");
};

// 5. Fleet Surge (Paced autoscaler demo)
document.getElementById('btnSurge').addEventListener('click', async () => {
    showBanner("📈 FLEET SURGE: INJECTING 10 RAPID TASKS TO TRIGGER KEDA AUTOSCALER...", "rgba(16, 185, 129, 0.95)", "#059669");
    navigateToTab('tabAutoscaler', '#autoscalerLogContainer', true, 1400);
    try {
        const res = await fetch('/api/v1/cloud/surge', { method: 'POST' });
        const data = await res.json();
        showToast("Fleet Surge Injected (10 tasks)! Centering on Tab 2 (Autoscaler) to watch pod provisioning in real-time...", "info", 5000);
    } catch (e) {
        showToast(`Surge error: ${e}`, "error");
    }
});

// Announce High-Compute Mission (Predictive Provisioning Demo)
async function triggerAnnounceMission() {
    showBanner("📅 PREDICTIVE PROVISIONING: AGV HIGH-LOAD MISSION ANNOUNCED (15s LEAD TIME). PROACTIVE WORKER PRE-WARM INITIATED...", "rgba(8, 145, 178, 0.95)", "#0891b2");
    navigateToTab('tabAutoscaler', '#scheduledMissionsContainer', true, 1400);
    try {
        const res = await fetch('/api/v1/mission/demo_announce', { method: 'POST' });
        const data = await res.json();
        showToast(`📅 Mission ${data.mission_id} announced (${data.expected_critical_tasks} tasks)! Proactively pre-warming ${data.target_prewarmed_workers} workers ahead of surge.`, "info", 5000);
    } catch (e) {
        showToast(`Mission announcement failed: ${e}`, "error");
    }
}

const btnMissionDeck = document.getElementById('btnAnnounceMission');
if (btnMissionDeck) btnMissionDeck.addEventListener('click', triggerAnnounceMission);

const btnMissionTab = document.getElementById('btnAnnounceMissionTab');
if (btnMissionTab) btnMissionTab.addEventListener('click', triggerAnnounceMission);


const DUMMY_BASE64_IMAGE = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==";

// 6. Rogue Token (Paced security demo)
document.getElementById('btnRogue').addEventListener('click', async () => {
    showBanner("🛡️ INGRESS GATEWAY: INJECTING UNAUTHORIZED ROGUE SPOOFED TOKEN...", "rgba(225, 29, 72, 0.95)", "#e11d48");
    navigateToTab('tabTenants', '#tenantsListContainer', true, 1400);
    try {
        const res = await fetch('/api/v1/inference', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Robot-Token': 'rogue-unauthorized-secret-999'
            },
            body: JSON.stringify({
                robot_id: 'ROGUE-HACKER-99',
                task_type: 'object_detection',
                criticality: 'CRITICAL',
                deadline_ms: 100.0,
                image_base64: DUMMY_BASE64_IMAGE
            })
        });

        if (res.status === 403 || res.status === 401) {
            showToast("Zero-Trust Gateway: Rogue token REJECTED with HTTP 401/403 Forbidden! Centered on Tab 3 (Fleet Governance).", "security", 5000);
            showBanner("🛡️ PERIMETER SECURED: ROGUE TOKEN BLOCKED (HTTP 401/403 FORBIDDEN)", "rgba(225, 29, 72, 0.95)", "#e11d48");
        } else {
            showToast(`Unexpected status: ${res.status}`, "warning");
        }
    } catch (e) {
        showToast(`Rogue test error: ${e}`, "error");
    }
});

// Feature 12: Latency-Aware Protective Edge-Cloud Fallback
async function triggerEdgeFallbackDemo() {
    showBanner("🛡️ LATENCY-AWARE FALLBACK: ROBOT REQUESTS 15ms SAFETY INFERENCE. CLOUD EVALUATING RADS QUEUE...", "rgba(245, 158, 11, 0.95)", "#d97706");
    navigateToTab('tabBenchmarks', '#taskExecutionStreamBody', true, 1200);
    try {
        const res = await fetch('/api/v1/cloud/demo_edge_fallback', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'EXECUTE_AT_EDGE') {
            showToast(`🛡️ Circuit Breaker Tripped: Predicted cloud latency ${data.predicted_latency_ms}ms > ${data.deadline_ms}ms deadline! Immediate EXECUTE_AT_EDGE returned. Centered on Tab 5.`, "warning", 6000);
            showBanner(`🛡️ PROTECTIVE EDGE FALLBACK: Deadline ${data.deadline_ms}ms unreachable (${data.predicted_latency_ms}ms predicted) -> Reverted to Onboard Edge Model!`, "rgba(245, 158, 11, 0.95)", "#d97706");
        } else {
            showToast("Cloud accepted task within deadline.", "info");
        }
    } catch (e) {
        showToast(`Edge Fallback error: ${e}`, "error");
    }
}
const btnEdge = document.getElementById('btnEdgeFallback');
if (btnEdge) btnEdge.addEventListener('click', triggerEdgeFallbackDemo);

// Feature 13: Data Lakehouse Parquet Exporter
async function fetchLakehouseStatus() {
    try {
        const res = await fetch('/api/v1/cloud/export/status');
        if (!res.ok) return;
        const data = await res.json();
        const latest = data.latest_export;
        if (latest) {
            const lblFile = document.getElementById('lblLakehouseLatestFile');
            if (lblFile) lblFile.innerText = latest.file_name || '-';
            const lblRows = document.getElementById('lblLakehouseRows');
            if (lblRows) lblRows.innerText = `${latest.row_count || 0} rows`;
            const lblSize = document.getElementById('lblLakehouseSize');
            if (lblSize) lblSize.innerText = `${((latest.file_size_bytes || 0) / 1024).toFixed(1)} KB (Snappy)`;
        }
    } catch (e) {
        // silent
    }
}

async function triggerLakehouseExport() {
    showBanner("📊 DATA LAKEHOUSE ETL: EXTRACTING REDIS TELEMETRY & MINIO INCIDENTS INTO APACHE PARQUET...", "rgba(16, 185, 129, 0.95)", "#059669");
    navigateToTab('tabIncidents', '#lblLakehouseLatestFile', true, 1200);
    try {
        const res = await fetch('/api/v1/cloud/export/lakehouse', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'COMPLETED' || data.file_name) {
            showToast(`📊 Lakehouse Batch Exported: ${data.row_count} rows written to ${data.file_name} (${((data.file_size_bytes || 0) / 1024).toFixed(1)} KB, Snappy compression). Centered on Tab 4.`, "success", 6000);
            showBanner(`📊 LAKEHOUSE EXPORT COMPLETE: Generated ${data.file_name} with PyArrow Snappy compression!`, "rgba(16, 185, 129, 0.95)", "#059669");
            
            const lblFile = document.getElementById('lblLakehouseLatestFile');
            if (lblFile) lblFile.innerText = data.file_name || '-';
            const lblRows = document.getElementById('lblLakehouseRows');
            if (lblRows) lblRows.innerText = `${data.row_count || 0} rows`;
            const lblSize = document.getElementById('lblLakehouseSize');
            if (lblSize) lblSize.innerText = `${((data.file_size_bytes || 0) / 1024).toFixed(1)} KB (Snappy)`;
        } else {
            showToast(`Lakehouse export result: ${data.status || 'Complete'}`, "info");
        }
    } catch (e) {
        showToast(`Lakehouse export error: ${e}`, "error");
    }
}
const btnLakehouseTop = document.getElementById('btnLakehouseExport');
if (btnLakehouseTop) btnLakehouseTop.addEventListener('click', triggerLakehouseExport);
const btnLakehouseTab = document.getElementById('btnTriggerLakehouseExport');
if (btnLakehouseTab) btnLakehouseTab.addEventListener('click', triggerLakehouseExport);

// 7. System Reset
document.getElementById('btnSystemReset').addEventListener('click', async () => {
    try {
        await Promise.all([
            fetch('/api/v1/debug/workers/worker-1/recover', { method: 'POST' }),
            fetch('/api/v1/debug/workers/worker-2/recover', { method: 'POST' })
        ]);
        worker1Alive = true;
        worker2Alive = true;
        humanHazard = false;
        document.getElementById('btnHazard').innerHTML = '🚨 <span>TRIGGER HAZARD (AGV-01)</span> <span class="btn-tab-tag">Tab 4</span>';
        document.getElementById('btnKillWorker').innerHTML = '🔥 <span>KILL WORKER-1</span> <span class="btn-tab-tag">Tab 1</span>';
        document.getElementById('btnKillWorker').className = 'btn btn-warning';
        showToast("System & Worker Nodes fully reset to HEALTHY.", "success");
    } catch (e) {
        showToast(`Reset error: ${e}`, "error");
    }
});

// 8. Custom Task Dispatch (Paced perception demo)
document.getElementById('deadlineSlider').addEventListener('input', (e) => {
    document.getElementById('deadlineDisplay').innerText = `${e.target.value}ms`;
});

document.getElementById('presetSelect').addEventListener('change', (e) => {
    const val = e.target.value;
    const crit = document.getElementById('critSelect');
    const dl = document.getElementById('deadlineSlider');
    const disp = document.getElementById('deadlineDisplay');
    const scn = document.getElementById('sceneSelect');

    if (val === 'AGV-01') {
        crit.value = 'CRITICAL';
        dl.value = 100;
        scn.value = 'human';
    } else if (val === 'DRONE-04') {
        crit.value = 'HIGH';
        dl.value = 250;
        scn.value = 'pallet';
    } else if (val === 'SWEEPER-09') {
        crit.value = 'NORMAL';
        dl.value = 600;
        scn.value = 'dock';
    } else {
        crit.value = 'LOW';
        dl.value = 1500;
        scn.value = 'clear';
    }
    disp.innerText = `${dl.value}ms`;
});

document.getElementById('btnDispatchTask').addEventListener('click', async () => {
    const preset = document.getElementById('presetSelect').value;
    const crit = document.getElementById('critSelect').value;
    const dl = parseFloat(document.getElementById('deadlineSlider').value);

    // Auto-navigate to Tab 5 after brief delay so user can see dispatch feedback
    navigateToTab('tabBenchmarks', '#visionFeedCanvas', true, 1200);

    try {
        const res = await fetch('/api/v1/inference', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Robot-Token': 'robot-token-secret'
            },
            body: JSON.stringify({
                robot_id: preset,
                task_type: 'object_detection',
                criticality: crit,
                deadline_ms: dl,
                image_base64: DUMMY_BASE64_IMAGE
            })
        });

        if (res.ok) {
            const data = await res.json();
            showToast(`Task Dispatched: ${data.request_id.substring(0, 8)}... (${crit} | ${dl}ms). Centered on Tab 5 (Perception Stream).`, "success");
        } else {
            showToast(`Dispatch failed: ${res.statusText}`, "error");
        }
    } catch (e) {
        showToast(`Dispatch network error: ${e}`, "error");
    }
});

// ================= TABS SWITCHER =================
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-tab');
        navigateToTab(targetId, null, false);
    });
});

// ================= LIVE UTC CLOCK =================
function updateClock() {
    const now = new Date();
    document.getElementById('clockUTC').innerText = now.toUTCString().split(' ')[4] + ' UTC';
}
setInterval(updateClock, 1000);
updateClock();

// ================= STARTUP =================
initTheme();
gameLoop();
setInterval(pollTelemetry, 700);
pollTelemetry();
fetchLakehouseStatus();
setInterval(fetchLakehouseStatus, 5000);
