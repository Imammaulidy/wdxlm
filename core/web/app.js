/**
 * BITGET XLM AUTO WD — DASHBOARD CLIENT APPLICATION
 * Real-time SSE Log Streaming & Interactive ADB Automation Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements - Status Badges
    const deviceBadge = document.getElementById('deviceBadge');
    const deviceText = document.getElementById('deviceText');
    const screenBadge = document.getElementById('screenBadge');
    const screenText = document.getElementById('screenText');
    const botStateBadge = document.getElementById('botStateBadge');
    const botStateText = document.getElementById('botStateText');
    const cloneBadge = document.getElementById('cloneBadge');

    // DOM Elements - Controls
    const btnStartBot = document.getElementById('btnStartBot');
    const btnNextClone = document.getElementById('btnNextClone');
    const btnNextText = document.getElementById('btnNextText');
    const btnPauseBot = document.getElementById('btnPauseBot');
    const btnStopBot = document.getElementById('btnStopBot');
    const checkManualMode = document.getElementById('checkManualMode');

    // DOM Elements - Quick Tools
    const btnLaunchScrcpy = document.getElementById('btnLaunchScrcpy');
    const btnSetScreenBot = document.getElementById('btnSetScreenBot');
    const btnRestoreScreen = document.getElementById('btnRestoreScreen');

    // DOM Elements - Config
    const inputStartIndex = document.getElementById('inputStartIndex');
    const btnDecIndex = document.getElementById('btnDecIndex');
    const btnIncIndex = document.getElementById('btnIncIndex');
    const inputAlamatWd = document.getElementById('inputAlamatWd');
    const inputPin = document.getElementById('inputPin');
    const inputWifiIp = document.getElementById('inputWifiIp');
    const btnSaveConfig = document.getElementById('btnSaveConfig');

    // DOM Elements - Terminal
    const terminalContainer = document.getElementById('terminalContainer');
    const terminalOutput = document.getElementById('terminalOutput');
    const checkAutoScroll = document.getElementById('checkAutoScroll');
    const btnClearLogs = document.getElementById('btnClearLogs');

    // DOM Elements - Steps
    const stepsList = document.getElementById('stepsList');
    const stepsCounter = document.getElementById('stepsCounter');
    const filterStepsInput = document.getElementById('filterStepsInput');
    const btnEnableAllSteps = document.getElementById('btnEnableAllSteps');
    const btnDisableAllSteps = document.getElementById('btnDisableAllSteps');

    // Internal State
    let currentBotState = 'IDLE';
    let nextCloneTarget = null;
    let isConfigLoaded = false;
    let allStepsData = [];

    // =========================================================================
    // 1. TOAST NOTIFICATIONS
    // =========================================================================
    function showToast(message, type = 'success') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        let icon = '✔';
        if (type === 'warning') icon = '⚠';
        if (type === 'error') icon = '✖';
        
        toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    // =========================================================================
    // 2. STATUS POLLER & SYNC
    // =========================================================================
    async function updateStatus() {
        try {
            const res = await fetch('/api/status');
            if (!res.ok) return;
            const data = await res.json();

            // Device status
            const hasDevices = data.devices && data.devices.length > 0;
            if (hasDevices) {
                const target = data.usb_device || data.devices[0];
                deviceBadge.className = 'badge badge-device connected';
                deviceText.textContent = `Terkoneksi: ${target}`;
            } else {
                deviceBadge.className = 'badge badge-device disconnected';
                deviceText.textContent = 'Tidak Ada Perangkat';
            }

            // Screen status
            if (data.screen && data.screen.active_size) {
                const isBot = data.screen.is_bot_format;
                screenText.textContent = `${data.screen.active_size} @ ${data.screen.active_density} DPI ${isBot ? '(Bot)' : '(Asli)'}`;
            }

            // Bot status & clone badge
            currentBotState = data.bot_state;
            botStateText.textContent = currentBotState;
            botStateBadge.className = `badge badge-state state-${currentBotState.toLowerCase()}`;

            if (data.current_clone) {
                cloneBadge.textContent = `Clone: #${data.current_clone}`;
            } else if (data.config && data.config.start_index) {
                cloneBadge.textContent = `Start: #${data.config.start_index}`;
            }

            nextCloneTarget = data.next_clone || ((data.current_clone || data.config.start_index) + 1);

            // Update Control Buttons state
            if (currentBotState === 'IDLE') {
                btnStartBot.disabled = false;
                btnNextClone.disabled = true;
                btnNextClone.classList.remove('highlight-pulse');
                btnNextText.textContent = 'Lanjut Clone Berikutnya (ENTER / CTRL+V)';
                btnPauseBot.disabled = true;
                btnStopBot.disabled = true;
            } else if (currentBotState === 'RUNNING') {
                btnStartBot.disabled = true;
                btnNextClone.disabled = true;
                btnNextClone.classList.remove('highlight-pulse');
                btnNextText.textContent = 'Sedang Memproses...';
                btnPauseBot.disabled = false;
                btnStopBot.disabled = false;
            } else if (currentBotState === 'WAITING_NEXT') {
                btnStartBot.disabled = true;
                btnNextClone.disabled = false;
                btnNextClone.classList.add('highlight-pulse');
                btnNextText.textContent = `Lanjut Clone ke-${nextCloneTarget} (ENTER / CTRL+V)`;
                btnPauseBot.disabled = true;
                btnStopBot.disabled = false;
            }

            // Populate form only on first load so user input is not overwritten
            if (!isConfigLoaded && data.config) {
                inputStartIndex.value = data.config.start_index || 1;
                inputAlamatWd.value = data.config.alamat_wd || '';
                inputPin.value = data.config.pin || '';
                inputWifiIp.value = data.wifi_ip || data.config.last_wifi_ip || '';
                isConfigLoaded = true;
            }
        } catch (err) {
            console.error('Failed to poll status:', err);
        }
    }

    // Poll status every 2.5s
    setInterval(updateStatus, 2500);
    updateStatus();

    // =========================================================================
    // 3. SERVER-SENT EVENTS (SSE) LIVE LOG STREAM
    // =========================================================================
    function initLogStream() {
        terminalOutput.innerHTML = '';
        const evtSource = new EventSource('/api/logs');

        evtSource.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                appendLogLine(data.line);
            } catch (err) {
                appendLogLine(e.data);
            }
        };

        evtSource.onerror = () => {
            // Connection drops, browser will auto reconnect
        };
    }

    function appendLogLine(text) {
        if (!text) return;
        const lineElem = document.createElement('span');
        lineElem.className = 'log-line';

        // Tag styling
        if (text.includes('[V]') || text.includes('BERHASIL') || text.includes('sukses')) {
            lineElem.classList.add('log-success');
        } else if (text.includes('[!]') || text.includes('Peringatan') || text.includes('[STEP-BY-STEP]')) {
            lineElem.classList.add('log-warn');
        } else if (text.includes('[X]') || text.includes('Error') || text.includes('Gagal') || text.includes('DIHENTIKAN')) {
            lineElem.classList.add('log-err');
        } else if (text.startsWith('--->') || text.startsWith('#') || text.startsWith('[ID.')) {
            lineElem.classList.add('log-step');
        } else if (text.startsWith('[SYSTEM]') || text.startsWith('[PROMPT]')) {
            lineElem.classList.add('log-system');
        } else if (text.startsWith('[ACTION]') || text.startsWith('Tapping') || text.startsWith('Swiping')) {
            lineElem.classList.add('log-action');
        }

        lineElem.textContent = text;
        terminalOutput.appendChild(lineElem);

        if (checkAutoScroll.checked) {
            terminalContainer.scrollTop = terminalContainer.scrollHeight;
        }
    }

    btnClearLogs.addEventListener('click', async () => {
        await fetch('/api/logs/clear', { method: 'POST' });
        terminalOutput.innerHTML = '';
        showToast('Log terminal dibersihkan', 'success');
    });

    initLogStream();

    // =========================================================================
    // 4. BOT CONTROLS & ACTIONS
    // =========================================================================
    btnStartBot.addEventListener('click', async () => {
        const startIdx = parseInt(inputStartIndex.value, 10) || 1;
        const manual = checkManualMode.checked;

        btnStartBot.disabled = true;
        try {
            const res = await fetch('/api/bot/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ start_index: startIdx, manual: manual })
            });
            const data = await res.json();
            if (res.ok) {
                showToast(data.message || 'Bot berhasil dijalankan!', 'success');
                updateStatus();
            } else {
                showToast(data.message || 'Gagal memulai bot', 'error');
                btnStartBot.disabled = false;
            }
        } catch (err) {
            showToast('Koneksi ke server gagal', 'error');
            btnStartBot.disabled = false;
        }
    });

    btnNextClone.addEventListener('click', async () => {
        if (currentBotState !== 'WAITING_NEXT') return;
        btnNextClone.disabled = true;
        btnNextClone.classList.remove('highlight-pulse');

        try {
            const res = await fetch('/api/bot/next', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            const data = await res.json();
            if (res.ok) {
                showToast(`Melanjutkan ke Clone #${nextCloneTarget}...`, 'success');
                updateStatus();
            } else {
                showToast(data.message || 'Gagal mengirim sinyal lanjut', 'error');
            }
        } catch (err) {
            showToast('Koneksi ke server gagal', 'error');
        }
    });

    btnPauseBot.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/bot/pause', { method: 'POST' });
            const data = await res.json();
            showToast(data.message || 'Sinyal PAUSE terkirim', 'warning');
            updateStatus();
        } catch (err) {
            showToast('Gagal mengirim sinyal pause', 'error');
        }
    });

    btnStopBot.addEventListener('click', async () => {
        if (!confirm('Yakin ingin menghentikan bot sekarang?')) return;
        try {
            const res = await fetch('/api/bot/stop', { method: 'POST' });
            const data = await res.json();
            showToast(data.message || 'Bot dihentikan', 'warning');
            updateStatus();
        } catch (err) {
            showToast('Gagal menghubungi server', 'error');
        }
    });

    // Global Keyboard Shortcuts
    // - Lanjut: Enter ATAU Ctrl + V
    // - Pause : Tombol 'P' ATAU Ctrl + C
    // - Keluar: Tombol 'Q'
    window.addEventListener('keydown', (e) => {
        const active = document.activeElement;
        const isInput = active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA');
        if (isInput) return; // Jangan mengganggu saat user sedang mengetik di input form

        const isCtrl = e.ctrlKey || e.metaKey;
        const key = e.key.toLowerCase();

        // 1. SHORTCUT LANJUT (ENTER atau CTRL+V)
        if (e.key === 'Enter' || (isCtrl && key === 'v')) {
            if (currentBotState === 'WAITING_NEXT') {
                e.preventDefault();
                btnNextClone.click();
            }
        }

        // 2. SHORTCUT PAUSE (TOMBOL 'P' atau CTRL+C)
        else if ((!isCtrl && key === 'p') || (isCtrl && key === 'c')) {
            if (currentBotState === 'RUNNING') {
                e.preventDefault();
                btnPauseBot.click();
            }
        }

        // 3. SHORTCUT KELUAR (TOMBOL 'Q')
        else if (!isCtrl && key === 'q') {
            if (currentBotState === 'RUNNING' || currentBotState === 'WAITING_NEXT') {
                e.preventDefault();
                btnStopBot.click();
            }
        }
    });

    // =========================================================================
    // 5. QUICK TOOLS (SCRCPY & SCREEN)
    // =========================================================================
    btnLaunchScrcpy.addEventListener('click', async () => {
        showToast('Membuka SCRCPY Mirroring...', 'success');
        try {
            const res = await fetch('/api/scrcpy', { method: 'POST' });
            const data = await res.json();
            if (res.ok) {
                showToast(data.message, 'success');
            } else {
                showToast(data.message, 'error');
            }
        } catch (err) {
            showToast('Gagal memanggil launcher SCRCPY', 'error');
        }
    });

    btnSetScreenBot.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/screen/set', { method: 'POST' });
            const data = await res.json();
            showToast(data.message, data.status);
            updateStatus();
        } catch (err) {
            showToast('Gagal mengatur layar bot', 'error');
        }
    });

    btnRestoreScreen.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/screen/restore', { method: 'POST' });
            const data = await res.json();
            showToast(data.message, data.status);
            updateStatus();
        } catch (err) {
            showToast('Gagal merestore layar HP', 'error');
        }
    });

    // =========================================================================
    // 6. CONFIGURATION FORM
    // =========================================================================
    btnDecIndex.addEventListener('click', () => {
        const val = Math.max(1, (parseInt(inputStartIndex.value, 10) || 1) - 1);
        inputStartIndex.value = val;
    });

    btnIncIndex.addEventListener('click', () => {
        const val = (parseInt(inputStartIndex.value, 10) || 1) + 1;
        inputStartIndex.value = val;
    });

    btnSaveConfig.addEventListener('click', async () => {
        const payload = {
            start_index: parseInt(inputStartIndex.value, 10) || 1,
            alamat_wd: inputAlamatWd.value.trim(),
            pin: inputPin.value.trim(),
            last_wifi_ip: inputWifiIp.value.trim()
        };

        try {
            const res = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok) {
                showToast('Konfigurasi berhasil disimpan!', 'success');
                updateStatus();
            } else {
                showToast('Gagal menyimpan konfigurasi', 'error');
            }
        } catch (err) {
            showToast('Koneksi ke server gagal', 'error');
        }
    });

    // =========================================================================
    // 7. MACRO STEPS MANAGER
    // =========================================================================
    async function loadSteps() {
        try {
            const res = await fetch('/api/steps');
            if (!res.ok) return;
            const data = await res.json();
            allStepsData = data.steps || [];
            renderSteps(allStepsData);
            stepsCounter.textContent = `${allStepsData.length} Steps`;
        } catch (err) {
            stepsList.innerHTML = '<div class="loading-spinner">Gagal memuat langkah-langkah macro.</div>';
        }
    }

    function renderSteps(steps) {
        stepsList.innerHTML = '';
        if (steps.length === 0) {
            stepsList.innerHTML = '<div class="loading-spinner">Tidak ada step yang sesuai filter.</div>';
            return;
        }

        steps.forEach((step) => {
            const card = document.createElement('div');
            card.className = `step-card ${step.enabled ? '' : 'disabled'}`;
            card.id = `step-card-${step.id}`;

            const cmdsPreview = step.commands && step.commands.length > 0 
                ? step.commands.slice(0, 2).join(' | ') 
                : 'Perintah sistem';

            card.innerHTML = `
                <div class="step-info">
                    <div class="step-title-row">
                        <span class="step-id-badge">${step.id}</span>
                        <span class="step-name">${escapeHtml(step.name)}</span>
                    </div>
                    <div class="step-commands" title="${escapeHtml(step.commands.join('\n'))}">${escapeHtml(cmdsPreview)}</div>
                </div>

                <div class="step-controls">
                    <div class="delay-box">
                        <span>Jeda:</span>
                        <input type="number" step="0.1" min="0" value="${step.sleep !== null ? step.sleep : 1.0}" class="input-delay" id="delay-input-${step.id}">
                        <button type="button" class="btn-save-delay" data-id="${step.id}" title="Simpan Jeda Waktu">💾</button>
                    </div>

                    <label class="switch" title="${step.enabled ? 'Nonaktifkan Step' : 'Aktifkan Step'}">
                        <input type="checkbox" ${step.enabled ? 'checked' : ''} data-id="${step.id}" class="step-toggle">
                        <span class="slider"></span>
                    </label>
                </div>
            `;

            stepsList.appendChild(card);
        });

        // Event listener for toggles
        document.querySelectorAll('.step-toggle').forEach((toggle) => {
            toggle.addEventListener('change', async (e) => {
                const stepId = e.target.getAttribute('data-id');
                const isEnabled = e.target.checked;
                const card = document.getElementById(`step-card-${stepId}`);

                if (isEnabled) {
                    card.classList.remove('disabled');
                } else {
                    card.classList.add('disabled');
                }

                try {
                    const res = await fetch('/api/step/toggle', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ step_id: stepId, enabled: isEnabled })
                    });
                    const resData = await res.json();
                    showToast(resData.message, isEnabled ? 'success' : 'warning');
                } catch (err) {
                    showToast('Gagal mengubah status langkah', 'error');
                }
            });
        });

        // Event listener for saving delay
        document.querySelectorAll('.btn-save-delay').forEach((btn) => {
            btn.addEventListener('click', async (e) => {
                const stepId = e.currentTarget.getAttribute('data-id');
                const delayInput = document.getElementById(`delay-input-${stepId}`);
                const delayVal = parseFloat(delayInput.value);

                try {
                    const res = await fetch('/api/step/delay', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ step_id: stepId, delay: delayVal })
                    });
                    const resData = await res.json();
                    showToast(resData.message, 'success');
                } catch (err) {
                    showToast('Gagal mengubah jeda waktu', 'error');
                }
            });
        });
    }

    // Filter Steps Search
    filterStepsInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        if (!query) {
            renderSteps(allStepsData);
            return;
        }

        const filtered = allStepsData.filter((s) => {
            const matchName = (s.name || '').toLowerCase().includes(query);
            const matchId = String(s.id).toLowerCase().includes(query);
            const matchCmds = (s.commands || []).some(cmd => cmd.toLowerCase().includes(query));
            return matchName || matchId || matchCmds;
        });

        renderSteps(filtered);
    });

    // Toggle All Steps
    btnEnableAllSteps.addEventListener('click', async () => {
        try {
            await fetch('/api/step/toggle_all', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: true })
            });
            showToast('Seluruh langkah diaktifkan', 'success');
            loadSteps();
        } catch (err) {
            showToast('Gagal mengaktifkan semua langkah', 'error');
        }
    });

    btnDisableAllSteps.addEventListener('click', async () => {
        try {
            await fetch('/api/step/toggle_all', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: false })
            });
            showToast('Seluruh langkah dinonaktifkan', 'warning');
            loadSteps();
        } catch (err) {
            showToast('Gagal menonaktifkan semua langkah', 'error');
        }
    });

    function escapeHtml(text) {
        if (!text) return '';
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    loadSteps();
});
