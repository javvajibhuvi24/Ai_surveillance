document.addEventListener("DOMContentLoaded", () => {
    // --- TAB SYSTEM ---
    const navItems = document.querySelectorAll(".nav-item");
    const tabContents = document.querySelectorAll(".tab-content");

    navItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const tabId = item.getAttribute("data-tab");

            navItems.forEach(nav => nav.classList.remove("active"));
            tabContents.forEach(content => content.classList.remove("active"));

            item.classList.add("active");
            document.getElementById(tabId).classList.add("active");

            // If entering registry, refresh catalog
            if (tabId === "registry-tab") {
                fetchFacesCatalog();
            }
        });
    });

    // --- TOAST SYSTEM ---
    const toastContainer = document.getElementById("toast-container");
    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        
        let icon = "fa-circle-info";
        if (type === "success") icon = "fa-circle-check";
        if (type === "error") icon = "fa-circle-xmark";
        
        toast.innerHTML = `
            <i class="fa-solid ${icon}"></i>
            <span>${message}</span>
        `;
        
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(20px)";
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // --- CHART INITIALIZATION ---
    const ctx = document.getElementById("complianceChart").getContext("2d");
    const maxDataPoints = 20;
    const chartLabels = Array.from({length: maxDataPoints}, () => "");
    const chartData = Array.from({length: maxDataPoints}, () => 0);

    const complianceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartLabels,
            datasets: [{
                label: 'PPE Compliance %',
                data: chartData,
                borderColor: '#06b6d4',
                backgroundColor: 'rgba(6, 182, 212, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8', font: { family: 'Inter' } }
                },
                x: {
                    grid: { display: false },
                    ticks: { display: false }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });

    function updateChart(score) {
        chartData.push(score);
        chartData.shift();
        complianceChart.update();
    }

    // --- MULTI-CAMERA LOGIC & POLLING ---
    const cameraGrid = document.getElementById("camera-grid");
    let camerasList = [];

    // Global function to submit new camera (since modal button calls it)
    window.submitNewCamera = function() {
        const nameInput = document.getElementById("new-cam-name");
        const urlInput = document.getElementById("new-cam-url");
        const ssidInput = document.getElementById("new-cam-ssid");
        if(!nameInput.value || !urlInput.value) {
            showToast("Please provide both name and URL.", "error");
            return;
        }
        
        fetch("/api/cameras", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: nameInput.value, url: urlInput.value, ssid: ssidInput.value })
        })
        .then(res => res.json())
        .then(data => {
            if(data.success) {
                showToast("Camera added successfully!", "success");
                document.getElementById('add-cam-modal').style.display='none';
                nameInput.value = "";
                urlInput.value = "";
                ssidInput.value = "";
                fetchCameras();
            } else {
                showToast(data.error || "Failed to add camera", "error");
            }
        });
    }

    window.deleteCamera = function(camId) {
        if(!confirm("Remove this camera?")) return;
        fetch(`/api/cameras/${camId}`, { method: "DELETE" })
            .then(res => res.json())
            .then(data => {
                if(data.success) {
                    showToast("Camera removed", "success");
                    fetchCameras();
                }
            });
    }

    function renderCameraGrid() {
        if(camerasList.length === 0) {
            cameraGrid.innerHTML = `<div class="empty-state" style="grid-column: span 2; text-align: center; padding: 60px;"><i class="fa-solid fa-video-slash" style="font-size:30px; margin-bottom:15px; color:var(--muted);"></i><br>No cameras configured. Add one to start monitoring.</div>`;
            return;
        }
        
        cameraGrid.innerHTML = "";
        camerasList.forEach(cam => {
            const isEnabled = cam.enabled !== false;
            const card = document.createElement("div");
            card.className = "card video-card";
            card.id = `card-${cam.id}`;
            card.style.display = "flex";
            card.style.flexDirection = "column";
            card.style.opacity = isEnabled ? "1" : "0.6";
            card.innerHTML = `
                <div class="card-header" style="justify-content: space-between; border-bottom: 1px solid var(--border); padding-bottom: 10px;">
                    <h3 style="font-size: 14px; margin:0;">
                        <i class="fa-solid fa-camera ${isEnabled ? 'text-accent' : ''}" style="${!isEnabled ? 'color:#475569' : ''}"></i>
                        ${cam.name}
                        ${!isEnabled ? '<span style="font-size:10px; color:#475569; margin-left:6px; font-weight:400;">(OFF)</span>' : ''}
                    </h3>
                    <div style="display:flex; gap:8px; align-items:center;">
                        ${cam.ssid ? `<span class="badge" style="font-size:10px; background:var(--surface2); color:var(--muted);"><i class="fa-solid fa-wifi"></i> ${cam.ssid}</span>` : ''}
                        <button class="btn-icon" style="padding:4px 8px; color:#3b82f6; display:flex; align-items:center; gap:5px; font-size:11px;" onclick="takeSnapshot('${cam.id}', this)" title="Take Snapshot">
                            <i class="fa-solid fa-camera-retro"></i> Save Incident
                        </button>
                        <button class="btn-icon" style="padding:4px 8px; color:#f59e0b;" onclick="reconnectCamera('${cam.id}', this)" title="Reconnect / Refresh Stream">
                            <i class="fa-solid fa-rotate-right"></i>
                        </button>
                        <button class="btn-icon cam-toggle-btn" id="toggle-${cam.id}" style="padding:4px 8px; color:${isEnabled ? '#10b981' : '#475569'}; display:flex; align-items:center; gap:5px; font-size:11px;" onclick="toggleCamera('${cam.id}', this)" title="${isEnabled ? 'Turn Camera OFF' : 'Turn Camera ON'}">
                            <i class="fa-solid fa-power-off"></i> ${isEnabled ? 'ON' : 'OFF'}
                        </button>
                        <button class="btn-icon" style="padding: 4px 8px; color:var(--text);" onclick="toggleMaximize(this.closest('.video-card'))" title="Maximize Camera"><i class="fa-solid fa-expand"></i></button>
                        <button class="btn-icon btn-danger" style="padding: 4px 8px;" onclick="deleteCamera('${cam.id}')" title="Remove Camera"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </div>
                <div class="video-wrapper" style="border-radius:0; border-bottom: 1px solid var(--border); cursor:pointer; position:relative;" onclick="toggleMaximize(this.closest('.video-card'))">
                    ${isEnabled
                        ? `<img src="/video_feed/${cam.id}" alt="${cam.name}" style="width:100%; display:block;">`
                        : `<div style="width:100%; aspect-ratio:4/3; background:#0a0f1e; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:10px;">
                               <i class="fa-solid fa-video-slash" style="font-size:32px; color:#334155;"></i>
                               <span style="font-size:12px; color:#475569;">Camera is OFF</span>
                               <button onclick="event.stopPropagation(); toggleCamera('${cam.id}', document.getElementById('toggle-${cam.id}'))" style="background:rgba(16,185,129,0.15); border:1px solid rgba(16,185,129,0.4); color:#10b981; padding:6px 16px; border-radius:6px; font-size:12px; cursor:pointer; margin-top:4px;"><i class="fa-solid fa-power-off"></i> Turn On</button>
                           </div>`
                    }
                </div>
                <div class="kpi-mini-row" style="display:flex; padding: 10px; gap:10px; background: var(--surface2); flex-wrap:wrap;">
                    <div style="flex:1; min-width:100px;">
                        <span style="font-size:10px; color:var(--muted); text-transform:uppercase;">User</span>
                        <div id="person-${cam.id}" style="font-weight:600; font-size:12px; color:#f59e0b;">${isEnabled ? 'SCANNING...' : '—'}</div>
                    </div>
                    <div style="flex:1; min-width:80px;">
                        <span style="font-size:10px; color:var(--muted); text-transform:uppercase;">Compliance</span>
                        <div id="compliance-${cam.id}" style="font-weight:600; font-size:12px;">${isEnabled ? '0%' : '—'}</div>
                    </div>
                    <div style="flex:2; min-width:150px;">
                        <span style="font-size:10px; color:var(--muted); text-transform:uppercase;">Detections</span>
                        <div id="tags-${cam.id}" class="tag-container" style="margin-top:2px; gap:4px;"></div>
                    </div>
                </div>
            `;
            cameraGrid.appendChild(card);
        });
    }

    window.takeSnapshot = function(camId, btn) {
        const icon = btn.querySelector('i');
        icon.classList.remove('fa-camera-retro');
        icon.classList.add('fa-spinner', 'fa-spin');
        btn.disabled = true;
        fetch(`/api/cameras/${camId}/snapshot`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                icon.classList.remove('fa-spinner', 'fa-spin');
                icon.classList.add('fa-camera-retro');
                btn.disabled = false;
                if(data.success) {
                    showToast(data.message, 'success');
                } else {
                    showToast(data.error || 'Snapshot failed', 'error');
                }
            })
            .catch(() => {
                icon.classList.remove('fa-spinner', 'fa-spin');
                icon.classList.add('fa-camera-retro');
                btn.disabled = false;
                showToast('Snapshot failed', 'error');
            });
    }

    window.reconnectCamera = function(camId, btn) {
        const icon = btn.querySelector('i');
        icon.classList.add('fa-spin');
        btn.disabled = true;
        fetch(`/api/cameras/${camId}/restart`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                icon.classList.remove('fa-spin');
                btn.disabled = false;
                if(data.success) {
                    showToast(data.message || 'Camera reconnecting...', 'success');
                    setTimeout(fetchCameras, 1500);
                } else {
                    showToast(data.error || 'Reconnect failed', 'error');
                }
            })
            .catch(() => { icon.classList.remove('fa-spin'); btn.disabled = false; showToast('Reconnect failed', 'error'); });
    }

    window.toggleCamera = function(camId, btn) {
        btn.disabled = true;
        fetch(`/api/cameras/${camId}/toggle`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                btn.disabled = false;
                if(data.success) {
                    showToast(data.message, data.enabled ? 'success' : 'error');
                    // Re-fetch so the card re-renders with correct ON/OFF state
                    camerasList = camerasList.map(c => c.id === camId ? {...c, enabled: data.enabled} : c);
                    renderCameraGrid();
                    fetchCameras();
                } else {
                    showToast(data.error || 'Toggle failed', 'error');
                }
            })
            .catch(() => { btn.disabled = false; showToast('Toggle failed', 'error'); });
    }

    function fetchCameras() {
        fetch("/api/cameras")
            .then(res => res.json())
            .then(data => {
                // If list of IDs changed, re-render the grid
                const oldIds = camerasList.map(c => c.id).join(",");
                const newIds = data.map(c => c.id).join(",");
                camerasList = data;
                if(oldIds !== newIds || !cameraGrid.children.length) {
                    renderCameraGrid();
                }
            });
    }
    
    window.toggleMaximize = function(card) {
        if(card.classList.contains('camera-maximized')) {
            card.classList.remove('camera-maximized');
            card.querySelector('.fa-compress').classList.replace('fa-compress', 'fa-expand');
        } else {
            card.classList.add('camera-maximized');
            card.querySelector('.fa-expand').classList.replace('fa-expand', 'fa-compress');
        }
    }

    function pollStats() {
        if(camerasList.length === 0) return;
        fetch("/api/stats")
            .then(res => res.json())
            .then(data => {
                let totalScore = 0;
                let activeCams = 0;
                
                for(const camId in data) {
                    const stats = data[camId];
                    const pEl = document.getElementById(`person-${camId}`);
                    const cEl = document.getElementById(`compliance-${camId}`);
                    const tEl = document.getElementById(`tags-${camId}`);
                    
                    if(!pEl || !cEl || !tEl) continue; // Grid not rendered yet
                    
                    // Update person
                    pEl.innerText = stats.name;
                    if (stats.name === "UNAUTHORIZED") pEl.style.color = "#ef4444";
                    else if (["NO FACES REGISTERED", "UNKNOWN", "SCANNING..."].includes(stats.name)) pEl.style.color = "#f59e0b";
                    else pEl.style.color = "#10b981";
                    
                    // Update compliance
                    cEl.innerText = `${stats.score}%`;
                    totalScore += stats.score;
                    activeCams++;
                    
                    // Update tags
                    tEl.innerHTML = "";
                    if (stats.labels.length === 0) {
                        tEl.innerHTML = '<span class="tag-empty" style="font-size:10px; padding:2px 4px;">None</span>';
                    } else {
                        stats.labels.forEach(label => {
                            const tag = document.createElement("span");
                            tag.className = "tag";
                            tag.style.fontSize = "10px";
                            tag.style.padding = "2px 4px";
                            if (label.startsWith("NO-")) {
                                tag.style.background = "rgba(239, 68, 68, 0.15)";
                                tag.style.color = "#ef4444";
                                tag.style.borderColor = "rgba(239, 68, 68, 0.35)";
                            } else if (["Hardhat","Safety Vest","Gloves","Goggles","Mask","Safety Shoes"].includes(label)) {
                                tag.style.background = "rgba(16, 185, 129, 0.15)";
                                tag.style.color = "#10b981";
                                tag.style.borderColor = "rgba(16, 185, 129, 0.35)";
                            }
                            tag.innerText = label;
                            tEl.appendChild(tag);
                        });
                    }
                }
                
                if(activeCams > 0) {
                    updateChart(totalScore / activeCams);
                }
            })
            .catch(err => console.error("Error polling stats:", err));
    }

    // Initial fetch of cameras, then poll stats
    fetchCameras();
    setInterval(pollStats, 1000);

    // --- NETWORK & WIFI LOGIC ---
    window.openNetworkModal = function() {
        document.getElementById('wifi-modal').style.display = 'flex';
        fetchWifiNetworks();
    }
    
    window.fetchWifiNetworks = function(btn) {
        const select = document.getElementById("wifi-ssid-select");
        if(btn) {
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scanning...';
            btn.disabled = true;
        }
        
        fetch("/api/wifi/scan")
            .then(res => res.json())
            .then(networks => {
                if(btn) {
                    btn.innerHTML = '<i class="fa-solid fa-rotate-right"></i> Refresh';
                    btn.disabled = false;
                }
                
                select.innerHTML = '<option value="">-- Select a Network --</option>';
                networks.forEach(net => {
                    const opt = document.createElement("option");
                    opt.value = net;
                    opt.innerText = net;
                    select.appendChild(opt);
                });
            })
            .catch(err => {
                if(btn) {
                    btn.innerHTML = '<i class="fa-solid fa-rotate-right"></i> Refresh';
                    btn.disabled = false;
                }
                showToast("Failed to scan Wi-Fi", "error");
            });
    }
    
    window.connectWifi = function(btn) {
        const ssid = document.getElementById("wifi-ssid-select").value;
        const pwd = document.getElementById("wifi-password").value;
        
        if(!ssid || !pwd) {
            showToast("Please select a network and enter a password.", "error");
            return;
        }
        
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Connecting...';
        btn.disabled = true;
        
        fetch("/api/wifi/connect", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ssid, password: pwd })
        })
        .then(res => res.json())
        .then(data => {
            btn.innerHTML = '<i class="fa-solid fa-link"></i> Connect Network';
            btn.disabled = false;
            
            if(data.success) {
                showToast("Wi-Fi connection requested. Check your host network status.", "success");
                document.getElementById('wifi-modal').style.display = 'none';
            } else {
                showToast(data.error || data.message || "Failed to connect", "error");
            }
        });
    }
    
    window.scanNetworkCameras = function(btn) {
        const dropdown = document.getElementById("scan-results-dropdown");
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scanning Port 554...';
        btn.disabled = true;
        dropdown.style.display = "block";
        dropdown.innerHTML = '<div style="padding:10px; color:var(--muted); font-size:12px; text-align:center;">Scanning local subnet for cameras (takes ~15s)...</div>';
        
        fetch("/api/cameras/discover")
            .then(res => res.json())
            .then(ips => {
                btn.innerHTML = '<i class="fa-solid fa-magnifying-glass-location"></i> Scan Network';
                btn.disabled = false;
                
                dropdown.innerHTML = "";
                if(ips.length === 0) {
                    dropdown.innerHTML = '<div style="padding:10px; color:var(--muted); font-size:12px; text-align:center;">No open RTSP ports found on subnet.</div>';
                    setTimeout(() => dropdown.style.display = 'none', 3000);
                    return;
                }
                
                ips.forEach(url => {
                    const item = document.createElement("div");
                    item.style.cssText = "padding:10px 14px; border-bottom:1px solid var(--border); font-size:13px; cursor:pointer;";
                    item.innerHTML = `<i class="fa-solid fa-video text-accent" style="margin-right:8px;"></i> ${url}`;
                    item.onmouseover = () => item.style.background = "var(--surface2)";
                    item.onmouseout = () => item.style.background = "transparent";
                    item.onclick = () => {
                        document.getElementById("new-cam-url").value = url;
                        dropdown.style.display = "none";
                    };
                    dropdown.appendChild(item);
                });
                
                const closeBtn = document.createElement("div");
                closeBtn.style.cssText = "padding:8px; text-align:center; font-size:11px; color:var(--text-muted); cursor:pointer; background:var(--surface2);";
                closeBtn.innerText = "Close";
                closeBtn.onclick = () => dropdown.style.display = "none";
                dropdown.appendChild(closeBtn);
            })
            .catch(err => {
                btn.innerHTML = '<i class="fa-solid fa-magnifying-glass-location"></i> Scan Network';
                btn.disabled = false;
                dropdown.innerHTML = '<div style="padding:10px; color:#ef4444; font-size:12px; text-align:center;">Network scan failed.</div>';
                setTimeout(() => dropdown.style.display = 'none', 3000);
            });
    }

    // --- EMAIL SETTINGS ---
    window.openEmailModal = function() {
        document.getElementById('email-modal').style.display = 'flex';
        fetch('/api/email/settings')
            .then(res => res.json())
            .then(data => {
                const cb = document.getElementById('email-enabled');
                const slider = document.getElementById('email-enabled-slider');
                const knob = document.getElementById('email-toggle-knob');
                cb.checked = data.enabled;
                slider.style.background = data.enabled ? '#00d4ff' : '#334155';
                knob.style.left = data.enabled ? '23px' : '3px';
                document.getElementById('email-sender').value = data.sender || '';
                document.getElementById('email-recipients').value = (data.recipients || []).join(', ');
                document.getElementById('email-password').value = '';
            });
    }

    // Animate toggle knob
    document.getElementById('email-enabled').addEventListener('change', function() {
        const knob = document.getElementById('email-toggle-knob');
        knob.style.left = this.checked ? '23px' : '3px';
    });

    window.saveEmailSettings = function(btn) {
        const sender = document.getElementById('email-sender').value.trim();
        const password = document.getElementById('email-password').value;
        const recipientsRaw = document.getElementById('email-recipients').value;
        const recipients = recipientsRaw.split(',').map(r => r.trim()).filter(r => r);
        const enabled = document.getElementById('email-enabled').checked;

        if(enabled && (!sender || !recipients.length)) {
            showToast('Please fill in sender and at least one recipient.', 'error');
            return;
        }

        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
        btn.disabled = true;

        fetch('/api/email/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled, sender, password, recipients })
        })
        .then(res => res.json())
        .then(data => {
            btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save Settings';
            btn.disabled = false;
            if(data.success) showToast('Email settings saved!', 'success');
            else showToast('Failed to save settings.', 'error');
        });
    }

    window.testEmail = function(btn) {
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...';
        btn.disabled = true;
        fetch('/api/email/test', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                btn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Send Test';
                btn.disabled = false;
                if(data.success) showToast('Test email sent! Check your inbox.', 'success');
                else showToast('Failed to send test email.', 'error');
            });
    }

    // --- ALERTS LOG POLLING ---
    const alertsFeed = document.getElementById("alerts-feed");

    function pollAlerts() {
        fetch("/api/alerts")
            .then(res => res.json())
            .then(data => {
                if (data.length === 0) {
                    alertsFeed.innerHTML = `
                        <div class="alert-empty-state">
                            <i class="fa-solid fa-bell-slash"></i>
                            <p>No safety incidents recorded recently.</p>
                        </div>
                    `;
                    return;
                }

                alertsFeed.innerHTML = "";
                data.forEach(alert => {
                    const item = document.createElement("div");
                    item.className = "alert-item";
                    
                    let timeOnly = alert.timestamp;
                    if (alert.timestamp.includes("_")) {
                        timeOnly = alert.timestamp.split("_")[1].replace(/-/g, ":");
                    }
                    
                    item.innerHTML = `
                        <div class="alert-header">
                            <span class="alert-title">INCIDENT ALERT</span>
                            <span class="alert-time">${timeOnly}</span>
                        </div>
                        <span class="alert-desc">${alert.message}</span>
                    `;
                    alertsFeed.appendChild(item);
                });
            })
            .catch(err => console.error("Error polling alerts:", err));
    }

    // Poll alerts every 2 seconds
    setInterval(pollAlerts, 2000);
    pollAlerts(); // Init run

    // --- FACE REGISTRY MANAGEMENT ---
    const faceListGrid = document.getElementById("face-list-grid");
    const faceCountBadge = document.getElementById("face-count");

    function fetchFacesCatalog() {
        fetch("/api/faces")
            .then(res => res.json())
            .then(data => {
                faceCountBadge.innerText = `${data.length} Members`;
                
                if (data.length === 0) {
                    faceListGrid.innerHTML = `
                        <div style="grid-column: span 12; text-align: center; color: var(--text-muted); padding: 40px 0;">
                            <i class="fa-solid fa-people-group" style="font-size: 32px; margin-bottom: 8px;"></i>
                            <p style="font-size: 13px;">No authorized faces registered yet.</p>
                        </div>
                    `;
                    return;
                }
                
                faceListGrid.innerHTML = "";
                data.forEach(face => {
                    const card = document.createElement("div");
                    card.className = "face-card";
                    
                    card.innerHTML = `
                        <div class="face-thumb-wrapper">
                            <img src="/authorized_faces/${face.filename}" alt="${face.name}">
                        </div>
                        <div class="face-name">${face.name.replace(/_/g, " ")}</div>
                        <button type="button" class="btn-delete-face" data-filename="${face.filename}">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    `;
                    
                    // Attach delete handler
                    card.querySelector(".btn-delete-face").addEventListener("click", () => {
                        deleteFace(face.filename);
                    });
                    
                    faceListGrid.appendChild(card);
                });
            })
            .catch(err => console.error("Error loading faces catalog:", err));
    }

    function deleteFace(filename) {
        if (!confirm(`Are you sure you want to delete this authorized face registration?`)) return;
        
        fetch("/api/delete_face", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ filename })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showToast("Authorized face registration deleted.", "success");
                fetchFacesCatalog();
            } else {
                showToast(data.error || "Failed to delete registration.", "error");
            }
        })
        .catch(err => {
            console.error("Error deleting face:", err);
            showToast("Failed to delete face.", "error");
        });
    }

    // --- UPLOAD REGISTERED FACE FORM ---
    const uploadForm = document.getElementById("upload-face-form");
    const faceInput = document.getElementById("reg-image");
    const fileDropFace = document.getElementById("file-drop-face");
    const facePreviewContainer = document.getElementById("face-preview-container");
    const facePreview = document.getElementById("face-preview");
    const btnRemoveFace = document.getElementById("btn-remove-face");

    // File input change preview
    faceInput.addEventListener("change", (e) => {
        handleFacePreview(e.target.files[0]);
    });

    function handleFacePreview(file) {
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                facePreview.src = e.target.result;
                facePreviewContainer.classList.remove("hidden");
                fileDropFace.classList.add("hidden");
            };
            reader.readAsDataURL(file);
        }
    }

    btnRemoveFace.addEventListener("click", () => {
        faceInput.value = "";
        facePreviewContainer.classList.add("hidden");
        fileDropFace.classList.remove("hidden");
    });

    // Form submit
    uploadForm.addEventListener("submit", (e) => {
        e.preventDefault();
        
        const formData = new FormData(uploadForm);
        
        fetch("/api/upload_face", {
            method: "POST",
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showToast(data.message, "success");
                uploadForm.reset();
                btnRemoveFace.click();
                fetchFacesCatalog();
            } else {
                showToast(data.error || "Failed to register face.", "error");
            }
        })
        .catch(err => {
            console.error("Error uploading face:", err);
            showToast("Failed to connect to server.", "error");
        });
    });

    // --- STATIC IMAGE TEST INFERENCE ---
    const testForm = document.getElementById("test-image-form");
    const testInput = document.getElementById("test-image");
    const fileDropTest = document.getElementById("file-drop-test");
    const testResultsCard = document.getElementById("test-results-card");
    const testResultImg = document.getElementById("test-result-img");
    const testResultScore = document.getElementById("test-result-score");
    const testResultPerson = document.getElementById("test-result-person");
    const testResultTags = document.getElementById("test-result-tags");
    const btnClearTest = document.getElementById("btn-clear-test");
    const btnTestSubmit = document.getElementById("btn-test-submit");
    const testPreviewContainer = document.getElementById("test-preview-container");
    const testPreview = document.getElementById("test-preview");
    const btnRemoveTest = document.getElementById("btn-remove-test");

    // File input change preview
    testInput.addEventListener("change", (e) => {
        handleTestPreview(e.target.files[0]);
    });

    function handleTestPreview(file) {
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                testPreview.src = e.target.result;
                testPreviewContainer.classList.remove("hidden");
                fileDropTest.classList.add("hidden");
            };
            reader.readAsDataURL(file);
            showToast(`Selected test image: ${file.name}`, "info");
        }
    }

    btnRemoveTest.addEventListener("click", () => {
        testInput.value = "";
        testPreviewContainer.classList.add("hidden");
        fileDropTest.classList.remove("hidden");
    });

    // Drag and drop events for dropzones
    const dropZones = [
        { zone: fileDropFace, input: faceInput, preview: handleFacePreview },
        { zone: fileDropTest, input: testInput, preview: handleTestPreview }
    ];

    dropZones.forEach(dz => {
        if (!dz.zone) return;
        
        ["dragenter", "dragover"].forEach(eventName => {
            dz.zone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dz.zone.classList.add("dragover");
            }, false);
        });

        ["dragleave", "drop"].forEach(eventName => {
            dz.zone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dz.zone.classList.remove("dragover");
            }, false);
        });

        dz.zone.addEventListener("drop", (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                dz.input.files = files;
                dz.preview(files[0]);
            }
        }, false);
    });

    // Test form submit
    testForm.addEventListener("submit", (e) => {
        e.preventDefault();
        
        const formData = new FormData(testForm);
        
        btnTestSubmit.disabled = true;
        btnTestSubmit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing Image...';
        showToast("Processing static image through YOLOv8 and DeepFace...", "info");
        
        fetch("/api/test_image", {
            method: "POST",
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            btnTestSubmit.disabled = false;
            btnTestSubmit.innerHTML = '<i class="fa-solid fa-microchip"></i> Run AI Analysis';
            
            if (data.success) {
                showToast("Analysis complete!", "success");
                
                // Render results
                testResultImg.src = data.image;
                testResultScore.innerText = `${data.score}%`;
                testResultPerson.innerText = data.name;
                
                // Color score
                const scoreNum = parseFloat(data.score);
                testResultScore.style.color = scoreNum >= 100 ? "#10b981" : scoreNum >= 60 ? "#f59e0b" : "#ef4444";
                
                // Color identified person
                if (data.name === "UNKNOWN" || data.name === "UNAUTHORIZED") {
                    testResultPerson.style.color = "#ef4444";
                } else {
                    testResultPerson.style.color = "#10b981";
                }
                
                // Render PPE Checklist
                const ppeChecklist = document.getElementById("ppe-checklist");
                const requiredPPE = ["Hardhat", "Safety Vest", "Gloves", "Goggles"];
                const detectedSet = new Set(data.labels.map(l => l.toLowerCase()));
                ppeChecklist.innerHTML = "";
                requiredPPE.forEach(item => {
                    const found = detectedSet.has(item.toLowerCase());
                    const violated = detectedSet.has(("no-" + item).toLowerCase());
                    let status = "missing";
                    let statusText = "MISSING";
                    let icon = "fa-circle-xmark";
                    if (found) { status = "found"; statusText = "DETECTED"; icon = "fa-circle-check"; }
                    else if (violated) { status = "violation"; statusText = "VIOLATION"; icon = "fa-triangle-exclamation"; }
                    const row = document.createElement("div");
                    row.className = `checklist-row ${status}`;
                    row.innerHTML = `
                        <i class="fa-solid ${icon}"></i>
                        <span>${item}</span>
                        <span class="checklist-status">${statusText}</span>
                    `;
                    ppeChecklist.appendChild(row);
                });

                // Render all detected tags
                testResultTags.innerHTML = "";
                if (data.labels.length === 0) {
                    testResultTags.innerHTML = '<span class="tag-empty">None detected</span>';
                } else {
                    data.labels.forEach(label => {
                        const tag = document.createElement("span");
                        tag.className = "tag tag-ppe";
                        tag.innerText = label;
                        testResultTags.appendChild(tag);
                    });
                }
                
                testResultsCard.classList.remove("hidden");
                testResultsCard.scrollIntoView({ behavior: 'smooth' });
            } else {
                showToast(data.error || "Static inference failed.", "error");
            }
        })
        .catch(err => {
            btnTestSubmit.disabled = false;
            btnTestSubmit.innerHTML = '<i class="fa-solid fa-microchip"></i> Run AI Analysis';
            console.error("Error during static test:", err);
            showToast("Failed to connect to server.", "error");
        });
    });

    btnClearTest.addEventListener("click", () => {
        testForm.reset();
        testResultsCard.classList.add("hidden");
        btnRemoveTest.click();
    });
});
