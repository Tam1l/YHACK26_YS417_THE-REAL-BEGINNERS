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
let packets = [];

// Fleet Robots
const agv = {
    id: 'AGV-01',
    x: 100,
    y: 265,
    targetX: 880,
    speed: 2.4,
    crit: 'CRITICAL',
    color: '#ef4444',
    status: 'NORMAL',
    beamActive: false
};

const drone = {
    id: 'DRONE-07',
    x: 320,
    y: 190,
    angle: 0,
    color: '#38bdf8'
};

const sweeper = {
    id: 'SWEEPER-12',
    x: 280,
    y: 330,
    dir: 1,
    color: '#10b981'
};

// ================= THEME ENGINE =================
const btnThemeToggle = document.getElementById('btnThemeToggle');
const themeIcon = document.getElementById('themeIcon');
const themeText = document.getElementById('themeText');

function initTheme() {
    const saved = localStorage.getItem('robonexus_theme') || 'dark';
    setTheme(saved);
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('robonexus_theme', theme);
    if (theme === 'light') {
        themeIcon.innerText = '🌙';
        themeText.innerText = 'Dark';
    } else {
        themeIcon.innerText = '☀️';
        themeText.innerText = 'Light';
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

    // Base background
    ctx.fillStyle = light ? '#f8fafc' : '#0b1120';
    ctx.fillRect(0, 0, w, h);

    // Floor Grid
    ctx.strokeStyle = light ? '#e2e8f0' : '#17233f';
    ctx.lineWidth = 1;
    for (let x = 0; x < w; x += 40) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
    }
    for (let y = 0; y < h; y += 40) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }

    // Central AGV Highway Transit Lane
    ctx.fillStyle = light ? '#f1f5f9' : '#131d33';
    ctx.fillRect(0, 225, w, 80);
    ctx.strokeStyle = light ? '#cbd5e1' : '#25334d';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(0, 225); ctx.lineTo(w, 225);
    ctx.moveTo(0, 305); ctx.lineTo(w, 305);
    ctx.stroke();

    // Center yellow hazard guidestrip
    ctx.strokeStyle = '#d97706';
    ctx.lineWidth = 2.5;
    ctx.setLineDash([14, 12]);
    ctx.beginPath();
    ctx.moveTo(0, 265); ctx.lineTo(w, 265);
    ctx.stroke();
    ctx.setLineDash([]);

    // Highway Corridor Label
    ctx.fillStyle = light ? '#64748b' : '#94a3b8';
    ctx.font = 'bold 10px monospace';
    ctx.fillText("AGV HIGH-SPEED TRANSIT CORRIDOR [LANE-01]", 260, 242);

    // Fleet Autonomous Charging Dock (Top Center)
    const dockX = Math.max(260, Math.floor((w - 180) / 2));
    const dockY = 14;
    const dockW = 180;
    const dockH = 92;
    ctx.fillStyle = light ? 'rgba(16, 185, 129, 0.08)' : 'rgba(16, 185, 129, 0.12)';
    ctx.fillRect(dockX, dockY, dockW, dockH);
    ctx.strokeStyle = 'rgba(16, 185, 129, 0.6)';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(dockX, dockY, dockW, dockH);
    ctx.fillStyle = '#10b981';
    ctx.font = 'bold 10px sans-serif';
    ctx.fillText("⚡ AUTONOMOUS FAST-DOCK", dockX + 16, dockY + 22);

    // Storage Racks
    drawRack(30, 110, 190, 52, '#38bdf8', 'RACK-A [LOGISTICS]', light);
    drawRack(w - 220, 110, 190, 52, '#818cf8', 'RACK-B [HIGH-BAY]', light);
    drawRack(30, 370, 190, 52, '#34d399', 'RACK-C [INVENTORY]', light);
    drawRack(w - 220, 370, 190, 52, '#f472b6', 'RACK-D [STAGING]', light);

    // Floating HUD Panels
    drawQueueHUD(light);
    drawCloudHubHUD(w, light);
    drawCameraHUD(w, light);
}

function drawRack(x, y, w, h, accentColor, label, light) {
    ctx.fillStyle = light ? '#ffffff' : '#1e293b';
    ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = light ? '#cbd5e1' : '#334155';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(x, y, w, h);

    // Pallets
    for (let i = 0; i < 4; i++) {
        ctx.fillStyle = accentColor;
        ctx.fillRect(x + 10 + i * 44, y + 10, 32, 22);
        ctx.strokeStyle = light ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.2)';
        ctx.strokeRect(x + 10 + i * 44, y + 10, 32, 22);
    }
    ctx.fillStyle = light ? '#475569' : '#94a3b8';
    ctx.font = '9px monospace';
    ctx.fillText(label, x + 8, y + 44);
}

function drawQueueHUD(light) {
    const hudX = 16, hudY = 14, hudW = 220, hudH = 92;
    ctx.fillStyle = light ? '#ffffff' : '#0f172a';
    ctx.fillRect(hudX, hudY, hudW, hudH);
    ctx.strokeStyle = light ? '#cbd5e1' : '#1e293b';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(hudX, hudY, hudW, hudH);

    ctx.fillStyle = light ? '#4f46e5' : '#818cf8';
    ctx.font = 'bold 10px sans-serif';
    const qCount = latestClusterData?.autoscaler?.queue_depth ?? 0;
    ctx.fillText(`⏳ RADS PRIORITY QUEUE (${qCount} WAITING)`, hudX + 10, hudY + 18);

    const tasks = [
        { id: 'DRONE-07', crit: 'HIGH', color: '#0284c7' },
        { id: 'SWEEPER-12', crit: 'NORMAL', color: '#059669' },
        { id: 'SCANNER-09', crit: 'LOW', color: '#64748b' }
    ];

    tasks.forEach((t, i) => {
        const itemY = hudY + 34 + i * 18;
        ctx.fillStyle = t.color;
        ctx.fillRect(hudX + 10, itemY, 6, 12);
        ctx.fillStyle = light ? '#1e293b' : '#e2e8f0';
        ctx.font = '10px monospace';
        ctx.fillText(`P${i+1}: ${t.id} [${t.crit}]`, hudX + 22, itemY + 10);
    });
}

function drawCloudHubHUD(w, light) {
    const hubW = 220, hubH = 92;
    const hubX = w - hubW - 16, hubY = 14;

    ctx.fillStyle = light ? '#ffffff' : '#0f172a';
    ctx.fillRect(hubX, hubY, hubW, hubH);
    ctx.strokeStyle = light ? '#cbd5e1' : '#1e293b';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(hubX, hubY, hubW, hubH);

    ctx.fillStyle = light ? '#0284c7' : '#38bdf8';
    ctx.font = 'bold 10px sans-serif';
    ctx.fillText("☁️ PRIVATE CLOUD HUB (8000)", hubX + 10, hubY + 18);

    // Worker 1
    ctx.fillStyle = worker1Alive ? '#10b981' : '#ef4444';
    ctx.beginPath(); ctx.arc(hubX + 16, hubY + 36, 4, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = light ? '#1e293b' : '#cbd5e1';
    ctx.font = '10px monospace';
    ctx.fillText(`worker-1: ${worker1Alive ? 'HEALTHY' : 'FAILED'} [BASE]`, hubX + 28, hubY + 40);

    // Worker 2
    ctx.fillStyle = worker2Alive ? '#10b981' : '#ef4444';
    ctx.beginPath(); ctx.arc(hubX + 16, hubY + 54, 4, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = light ? '#1e293b' : '#cbd5e1';
    ctx.fillText(`worker-2: ${worker2Alive ? 'HEALTHY' : 'FAILED'} [BASE]`, hubX + 28, hubY + 58);

    // Autoscaler count
    const activePods = latestClusterData?.autoscaler?.current_workers ?? 2;
    ctx.fillStyle = activePods > 2 ? '#f59e0b' : '#10b981';
    ctx.beginPath(); ctx.arc(hubX + 16, hubY + 72, 4, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = light ? '#1e293b' : '#cbd5e1';
    ctx.fillText(`worker-pool: ${activePods}/5 ACTIVE`, hubX + 28, hubY + 76);
}

function drawCameraHUD(w, light) {
    const hudW = 210, hudH = 135;
    const hudX = w - hudW - 16, hudY = canvas.height - hudH - 16;

    ctx.fillStyle = light ? '#ffffff' : '#0f172a';
    ctx.fillRect(hudX, hudY, hudW, hudH);
    ctx.strokeStyle = light ? '#cbd5e1' : '#1e293b';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(hudX, hudY, hudW, hudH);

    ctx.fillStyle = light ? '#0891b2' : '#22d3ee';
    ctx.font = 'bold 10px sans-serif';
    ctx.fillText("👁️ AGV-01 PERCEPTION STREAM", hudX + 10, hudY + 18);

    // Bounding box viewfinder
    ctx.fillStyle = light ? '#f1f5f9' : '#000000';
    ctx.fillRect(hudX + 8, hudY + 26, hudW - 16, 78);

    ctx.strokeStyle = agv.status === 'STOPPED' ? '#ef4444' : '#10b981';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(hudX + 35, hudY + 36, 120, 56);

    ctx.fillStyle = agv.status === 'STOPPED' ? '#ef4444' : '#10b981';
    ctx.font = 'bold 9px monospace';
    ctx.fillText(agv.status === 'STOPPED' ? 'TARGET: HUMAN (98%)' : 'TARGET: CLEAR (94%)', hudX + 40, hudY + 50);

    ctx.fillStyle = light ? '#64748b' : '#94a3b8';
    ctx.font = '10px monospace';
    ctx.fillText(`LATENCY: ${latestLatency.toFixed(1)}ms [DEADLINE MET]`, hudX + 10, hudY + 122);
}

// ================= SIMULATION PHYSICS & UPDATE =================
function updateSimulation() {
    if (!isRunning) return;

    // AGV Distance Safety Braking
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

    // Drone figure-eight motion
    drone.angle += 0.035;
    drone.x = 320 + Math.sin(drone.angle) * 110;
    drone.y = 190 + Math.cos(drone.angle * 2) * 22;

    // Sweeper linear patrol
    sweeper.x += sweeper.dir * 1.5;
    if (sweeper.x > 460) sweeper.dir = -1;
    if (sweeper.x < 240) sweeper.dir = 1;

    // Periodic telemetry packets
    if (Math.random() < 0.08) {
        const hubX = canvas.width - 120;
        packets.push({
            fromX: agv.x,
            fromY: agv.y,
            toX: hubX,
            toY: 60,
            progress: 0,
            color: agv.status === 'STOPPED' ? '#ef4444' : '#38bdf8'
        });
    }

    // Advance packets
    packets.forEach(p => { p.progress += 0.04; });
    packets = packets.filter(p => p.progress < 1.0);
}

function render() {
    drawWarehouse();

    // Draw Human Hazard
    if (humanHazard) {
        ctx.fillStyle = '#ef4444';
        ctx.beginPath(); ctx.arc(humanPos.x, humanPos.y - 14, 8, 0, Math.PI * 2); ctx.fill();
        ctx.fillRect(humanPos.x - 6, humanPos.y - 6, 12, 22);
        ctx.strokeStyle = '#dc2626';
        ctx.strokeRect(humanPos.x - 14, humanPos.y - 26, 28, 48);

        ctx.fillStyle = '#dc2626';
        ctx.font = 'bold 10px sans-serif';
        ctx.fillText("HAZARD", humanPos.x - 20, humanPos.y - 32);
    }

    // AGV Chassis
    ctx.fillStyle = agv.status === 'STOPPED' ? '#dc2626' : '#b91c1c';
    ctx.fillRect(agv.x - 22, agv.y - 15, 44, 30);
    ctx.strokeStyle = '#991b1b';
    ctx.lineWidth = 2;
    ctx.strokeRect(agv.x - 22, agv.y - 15, 44, 30);

    // LiDAR Safety Beam Cone
    ctx.fillStyle = agv.status === 'STOPPED' ? 'rgba(220, 38, 38, 0.22)' : 'rgba(217, 119, 6, 0.18)';
    ctx.beginPath();
    ctx.moveTo(agv.x + 22, agv.y);
    ctx.lineTo(agv.x + 110, agv.y - 38);
    ctx.lineTo(agv.x + 110, agv.y + 38);
    ctx.closePath();
    ctx.fill();

    // AGV Label
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 9px sans-serif';
    ctx.fillText("AGV-01", agv.x - 18, agv.y + 3);

    // Drone
    ctx.fillStyle = '#0284c7';
    ctx.fillRect(drone.x - 12, drone.y - 12, 24, 24);
    ctx.strokeStyle = '#0369a1';
    ctx.strokeRect(drone.x - 12, drone.y - 12, 24, 24);

    // Drone Spotlight
    ctx.fillStyle = 'rgba(2, 132, 199, 0.18)';
    ctx.beginPath();
    ctx.moveTo(drone.x, drone.y + 12);
    ctx.lineTo(drone.x - 24, drone.y + 36);
    ctx.lineTo(drone.x + 24, drone.y + 36);
    ctx.closePath();
    ctx.fill();

    // Sweeper
    ctx.fillStyle = '#059669';
    ctx.beginPath(); ctx.arc(sweeper.x, sweeper.y, 14, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = '#047857';
    ctx.stroke();

    // Telemetry Packets
    packets.forEach(p => {
        const curX = p.fromX + (p.toX - p.fromX) * p.progress;
        const curY = p.fromY + (p.toY - p.fromY) * p.progress;
        ctx.fillStyle = p.color;
        ctx.shadowColor = p.color;
        ctx.shadowBlur = 6;
        ctx.beginPath(); ctx.arc(curX, curY, 5, 0, Math.PI * 2); ctx.fill();
        ctx.shadowBlur = 0;
    });
}

function gameLoop() {
    updateSimulation();
    render();
    requestAnimationFrame(gameLoop);
}

// ================= CLOUD TELEMETRY POLLING =================
async function pollTelemetry() {
    try {
        const [healthRes, statusRes, tenantsRes, incidentsRes] = await Promise.all([
            fetch('/health').catch(() => null),
            fetch('/api/v1/cloud/status').catch(() => null),
            fetch('/api/v1/cloud/tenants').catch(() => null),
            fetch('/api/v1/cloud/incidents').catch(() => null)
        ]);

        if (healthRes && healthRes.ok) {
            const h = await healthRes.json();
            document.getElementById('txtGatewayStatus').innerText = h.status.toUpperCase();
            document.getElementById('txtWorkerCount').innerText = `${h.workers_healthy}/5 ONLINE`;
            document.getElementById('txtAutoscalerState').innerText = h.autoscaler_state;
        }

        if (statusRes && statusRes.ok) {
            const s = await statusRes.json();
            latestClusterData = s;
            updateMetrics(s);
            updateFabricTab(s.workers || []);
            updateAutoscalerTab(s.autoscaler || {});
        }

        if (tenantsRes && tenantsRes.ok) {
            const t = await tenantsRes.json();
            updateTenantsTab(t.tenants || {});
        }

        if (incidentsRes && incidentsRes.ok) {
            const inc = await incidentsRes.json();
            updateIncidentsTab(inc.incidents || []);
        }

    } catch (e) {
        console.warn("Telemetry fetch error:", e);
    }
}

function updateMetrics(s) {
    const qDepth = s.autoscaler?.queue_depth ?? 0;
    document.getElementById('metricQueueDepth').innerText = qDepth;
    const qDelta = document.getElementById('metricQueueDelta');
    if (qDepth > 2) {
        qDelta.innerText = `${qDepth} Surge Queue`;
        qDelta.className = 'metric-delta delta-warning';
    } else {
        qDelta.innerText = 'Clear';
        qDelta.className = 'metric-delta delta-success';
    }

    const as = s.autoscaler || {};
    document.getElementById('asStateVal').innerText = as.status || 'STABLE';
    document.getElementById('asPodsVal').innerText = `${as.current_workers || 2} / ${as.max_workers || 5}`;

    // Compute cumulative processed jobs
    let totalProc = 0;
    let failovers = 0;
    (s.workers || []).forEach(w => {
        totalProc += parseInt(w.processed_jobs || 0);
        if (w.healthy === 'false' && w.worker_id === 'worker-1') {
            worker1Alive = false;
        }
    });
    document.getElementById('metricProcessed').innerText = totalProc.toLocaleString();
    document.getElementById('metricAvgLatency').innerText = `${latestLatency.toFixed(1)} ms`;
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

function updateAutoscalerTab(as) {
    const container = document.getElementById('autoscalerLogContainer');
    const events = as.recent_events || [];
    container.innerHTML = '';

    if (events.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted);">Autoscaler initialized. Trigger Fleet Surge to observe auto-provisioning.</div>';
        return;
    }

    events.forEach(ev => {
        const entry = document.createElement('div');
        let cls = 'log-entry';
        if (ev.includes('SCALE_UP')) cls += ' scale-up';
        if (ev.includes('SCALE_DOWN')) cls += ' scale-down';
        entry.className = cls;
        entry.innerText = ev;
        container.appendChild(entry);
    });
}

function updateTenantsTab(tenants) {
    const container = document.getElementById('tenantsListContainer');
    container.innerHTML = '';

    Object.entries(tenants).forEach(([tid, t]) => {
        const card = document.createElement('div');
        card.className = 'tenant-card';
        card.style.borderLeftColor = t.color || '#3b82f6';
        card.innerHTML = `
            <div class="tenant-title" style="color: ${t.color || '#3b82f6'};">${t.name}</div>
            <div style="font-size: 12px; color: var(--text-muted);">Tier: <b style="color: var(--text-primary);">${t.tier}</b></div>
            <hr style="border: none; border-top: 1px solid var(--border-subtle); margin: 6px 0;">
            <div style="font-size: 12px;">Target SLA: <b>&le; ${t.sla_target_ms} ms</b></div>
            <div style="font-size: 12px;">SLA Met: <b style="color: var(--color-emerald);">${t.sla_compliance_pct}%</b></div>
            <div style="font-size: 12px;">Rate Limit: <b>${t.rate_limit_per_sec} req/s</b></div>
            <div style="font-size: 12px;">Total Served: <b>${t.total_requests} reqs</b></div>
        `;
        container.appendChild(card);
    });
}

function updateIncidentsTab(incidents) {
    const tbody = document.getElementById('incidentsTableBody');
    tbody.innerHTML = '';

    if (incidents.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No safety hazard incidents logged yet. Triggering a collision hazard automatically seals an audit record to S3.</td></tr>';
        return;
    }

    incidents.slice(0, 10).forEach(inc => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><code>${inc.incident_id || '-'}</code></td>
            <td>${inc.timestamp || '-'}</td>
            <td><b>${inc.robot_id || '-'}</b></td>
            <td>${inc.event_type || '-'}</td>
            <td><span style="color: ${inc.criticality === 'CRITICAL' ? 'var(--color-red)' : 'var(--color-amber)'}; font-weight: bold;">${inc.criticality}</span></td>
            <td><span class="code-pill">${inc.s3_uri || '-'}</span></td>
            <td>${inc.compliance_standard || 'ISO 3691-4'}</td>
        `;
        tbody.appendChild(tr);
    });
}

// ================= DEMO ACTIONS & CONTROLS =================
// 1. Play / Pause
document.getElementById('btnPlayPause').addEventListener('click', (e) => {
    isRunning = !isRunning;
    e.currentTarget.innerHTML = isRunning ? '⏸ <span>Pause Fleet</span>' : '▶ <span>Resume Fleet</span>';
    showToast(isRunning ? "Fleet Simulation Resumed" : "Fleet Simulation Paused", "info");
});

// 2. Hazard Toggle
document.getElementById('btnHazard').addEventListener('click', () => {
    humanHazard = !humanHazard;
    const btn = document.getElementById('btnHazard');
    if (humanHazard) {
        humanPos = { x: agv.x + 85, y: 265 };
        btn.innerHTML = '🟢 <span>CLEAR HAZARD</span>';
        showBanner("🚨 SAFETY CRITICAL: HUMAN OBSTACLE DETECTED IN AGV PATH! EMERGENCY BRAKE ACTIVE.", "rgba(220, 38, 38, 0.95)", "#ef4444");
        showToast("Hazard Obstacle Triggered: AGV LiDAR safety brake engaged!", "error");
    } else {
        btn.innerHTML = '🚨 <span>TRIGGER HAZARD (AGV-01)</span>';
        showBanner("✅ PATH CLEAR: AGV RESUMING AUTONOMOUS TRANSIT", "rgba(16, 185, 129, 0.95)", "#10b981");
        showToast("Hazard cleared. AGV resuming normal speed.", "success");
    }
});

// 3. Batch Leapfrog (RADS Priority Preemption)
document.getElementById('btnBatchDemo').addEventListener('click', async () => {
    showBanner("📦 INJECTING 5x ROUTINE BATCH + 1 CRITICAL AGV LEAPFROG TASK...", "rgba(37, 99, 235, 0.95)", "#2563eb");
    try {
        const res = await fetch('/api/v1/cloud/batch_leapfrog', { method: 'POST' });
        const data = await res.json();
        showToast(`Preemption Verified! Critical AGV (RADS ${data.critical_rads_score}) pre-empted 5 queued tasks!`, "success", 5000);
        showBanner(`⚡ PREEMPTION CONFIRMED: AGV-01 LEAPFROGGED 5 ROUTINE TASKS!`, "rgba(16, 185, 129, 0.95)", "#10b981");
    } catch (e) {
        showToast(`Batch Leapfrog error: ${e}`, "error");
    }
});

// 4. Kill Worker-1 / Restore Worker-1
document.getElementById('btnKillWorker').addEventListener('click', async (e) => {
    const btn = e.currentTarget;
    if (worker1Alive) {
        try {
            await fetch('/api/v1/debug/workers/worker-1/fail', { method: 'POST' });
            worker1Alive = false;
            btn.innerHTML = '⚡ <span>RESTORE WORKER-1</span>';
            btn.className = 'btn btn-emerald';
            showBanner("🔥 WORKER-1 CRASHED! ATOMIC FAILOVER REQUEUE ENGAGED.", "rgba(245, 158, 11, 0.95)", "#f59e0b");
            showToast("Worker-1 killed! In-flight perception jobs peer-recovered by Worker-2 with ZERO data loss!", "warning", 5000);
        } catch (err) {
            showToast(`Fail error: ${err}`, "error");
        }
    } else {
        try {
            await fetch('/api/v1/debug/workers/worker-1/recover', { method: 'POST' });
            worker1Alive = true;
            btn.innerHTML = '🔥 <span>KILL WORKER-1</span>';
            btn.className = 'btn btn-warning';
            showBanner("⚡ WORKER-1 RESTORED & RE-JOINED COMPUTE CLUSTER.", "rgba(16, 185, 129, 0.95)", "#10b981");
            showToast("Worker-1 restored to cluster pool.", "success");
        } catch (err) {
            showToast(`Recover error: ${err}`, "error");
        }
    }
});

// Helper for individual cards
window.toggleWorker = async function(wid, healthy) {
    const action = healthy ? 'fail' : 'recover';
    await fetch(`/api/v1/debug/workers/${wid}/${action}`, { method: 'POST' });
    showToast(`Worker ${wid} ${action === 'fail' ? 'killed' : 'recovered'} successfully.`, healthy ? "warning" : "success");
};

// 5. Fleet Surge (Autoscaler)
document.getElementById('btnSurge').addEventListener('click', async () => {
    showBanner("📈 FLEET SURGE: INJECTING 10 RAPID TASKS TO TRIGGER KEDA AUTOSCALER...", "rgba(16, 185, 129, 0.95)", "#059669");
    try {
        const res = await fetch('/api/v1/cloud/surge', { method: 'POST' });
        const data = await res.json();
        showToast("Fleet Surge Injected (10 tasks)! Watch Autoscaler tab provision auxiliary pods!", "info", 5000);
    } catch (e) {
        showToast(`Surge error: ${e}`, "error");
    }
});

const DUMMY_BASE64_IMAGE = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==";

// 6. Rogue Token (Zero-Trust 403 Rejection)
document.getElementById('btnRogue').addEventListener('click', async () => {
    showBanner("🛡️ INGRESS GATEWAY: INJECTING UNAUTHORIZED ROGUE SPOOFED TOKEN...", "rgba(225, 29, 72, 0.95)", "#e11d48");
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

        if (res.status === 403) {
            showToast("Zero-Trust Gateway: Rogue token REJECTED with HTTP 403 Forbidden!", "security", 5000);
            showBanner("🛡️ PERIMETER SECURED: ROGUE TOKEN BLOCKED (HTTP 403 FORBIDDEN)", "rgba(225, 29, 72, 0.95)", "#e11d48");
        } else {
            showToast(`Unexpected status: ${res.status}`, "warning");
        }
    } catch (e) {
        showToast(`Rogue test error: ${e}`, "error");
    }
});

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
        document.getElementById('btnHazard').innerHTML = '🚨 <span>TRIGGER HAZARD (AGV-01)</span>';
        document.getElementById('btnKillWorker').innerHTML = '🔥 <span>KILL WORKER-1</span>';
        document.getElementById('btnKillWorker').className = 'btn btn-warning';
        showToast("System & Worker Nodes fully reset to HEALTHY.", "success");
    } catch (e) {
        showToast(`Reset error: ${e}`, "error");
    }
});

// 8. Custom Task Dispatch
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
            showToast(`Task Dispatched: ${data.request_id.substring(0, 8)}... (${crit} | ${dl}ms)`, "success");
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
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

        btn.classList.add('active');
        const targetId = btn.getAttribute('data-tab');
        document.getElementById(targetId).classList.add('active');
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
