/**
 * BITGET WALLET CONTROL CENTER — TOPNOD MULTI-DEVICE CLIENT (PORT 2000)
 * Dual-Mode Engine: Manual Step Execution & Full Auto Sequence
 * Multi-Device Side-by-Side PADs with Hardware Screen-Off Background Mode
 */

window.onerror = function(msg, url, line, col, error) {
    console.error("Global JS Error:", msg, "at line", line);
    var cont = document.getElementById('devicesGridContainer');
    if (cont && cont.querySelector('.device-card-loading')) {
        var p = cont.querySelector('p');
        if (p) p.textContent = "Error memuat antarmuka: " + msg + " (Baris " + line + ")";
    }
};

document.addEventListener('DOMContentLoaded', () => {
    // State Store
    let currentMode = 'wd_baru'; // 'wd_baru' (Mode Baru) | 'wd_old' | 'create_account' | 'qris_morph'
    let currentStep2Mode = localStorage.getItem('bitget_step2_mode') || 'dompet';
    let cachedSteps = [];
    let connectedDevices = [];
    let availableWallets = [];
    let batchAutoState = true;
    let serverConfig = {};
    let isScreenOffMaster = false;
    let logEventSource = null;
    let autoScroll = true;

    // Ambil mode step 2 tersimpan dari server
    fetch('/api/step/step2_mode')
        .then(r => r.json())
        .then(d => {
            if (d && d.step2_mode) {
                currentStep2Mode = d.step2_mode;
                localStorage.setItem('bitget_step2_mode', d.step2_mode);
            }
        }).catch(() => {});

    // DOM Elements - Top Bar
    const switchMasterScreenOff = document.getElementById('switchMasterScreenOff');
    const screenOffStatusBadge = document.getElementById('screenOffStatusBadge');
    const switchBatchAuto = document.getElementById('switchBatchAuto');
    const batchAutoStatusBadge = document.getElementById('batchAutoStatusBadge');
    const tabBtns = document.querySelectorAll('.mode-tab-btn');
    const btnSetScreenBot = document.getElementById('btnSetScreenBot');
    const btnRestoreScreen = document.getElementById('btnRestoreScreen');
    const btnLaunchScrcpy = document.getElementById('btnLaunchScrcpy');
    const selectMirrorFps = document.getElementById('selectMirrorFps');
    const btnStartAllDevices = document.getElementById('btnStartAllDevices');
    const btnNextAllDevices = document.getElementById('btnNextAllDevices');
    const btnStopAllDevices = document.getElementById('btnStopAllDevices');
    const btnLayoutSplit = document.getElementById('btnLayoutSplit');
    const btnLayoutHorizontal = document.getElementById('btnLayoutHorizontal');

    // DOM Elements - Summary Bar
    const connectedDevicesCountBadge = document.getElementById('connectedDevicesCountBadge');
    const connectedDeviceNamesText = document.getElementById('connectedDeviceNamesText');
    const summaryMasterRef = document.getElementById('summaryMasterRef');
    const summaryEmailsCount = document.getElementById('summaryEmailsCount');
    const summaryLanIp = document.getElementById('summaryLanIp');

    // DOM Elements - PADs Grid & Terminal
    const devicesGridContainer = document.getElementById('devicesGridContainer');
    const terminalContainer = document.getElementById('terminalContainer');
    const terminalOutput = document.getElementById('terminalOutput');
    const selectLogDeviceFilter = document.getElementById('selectLogDeviceFilter');
    const checkAutoScroll = document.getElementById('checkAutoScroll');
    const btnClearLogs = document.getElementById('btnClearLogs');
    const btnRestartTerminal = document.getElementById('btnRestartTerminal');

    // =========================================================================
    // 1. TOAST NOTIFICATIONS
    // =========================================================================
    function showToast(message, type = 'success') {
        const container = document.getElementById('toastContainer');
        if (!container) return;
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
        }, 3200);
    }

    // =========================================================================
    // 2. MODE SWITCHER TABS
    // =========================================================================
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const newMode = btn.getAttribute('data-mode');
            if (newMode !== currentMode) {
                currentMode = newMode;
                loadMacroSteps(currentMode).then(() => {
                    renderDevicePads(connectedDevices);
                });
            }
        });
    });

    // =========================================================================
    // 3. STEP & WALLET LOADER
    // =========================================================================
    async function loadMacroSteps(mode) {
        try {
            const res = await fetch(`/api/steps?mode=${encodeURIComponent(mode)}`);
            if (res.ok) {
                const data = await res.json();
                cachedSteps = data.steps || [];
            }
        } catch (e) {
            console.error("Gagal memuat langkah macro:", e);
        }
    }

    async function loadWallets() {
        try {
            const res = await fetch('/api/wallets');
            if (res.ok) {
                const data = await res.json();
                availableWallets = data.wallets || [];
            }
        } catch (e) {
            console.error("Gagal memuat daftar wallet:", e);
        }
    }

    // =========================================================================
    // 4. SCREEN OFF & BATCH AUTO CONTROLLERS
    // =========================================================================
    if (switchMasterScreenOff) {
        switchMasterScreenOff.addEventListener('change', async (e) => {
            const enabled = e.target.checked;
            try {
                const res = await fetch('/api/screen/mode_screen_off', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ device: 'all', enabled: enabled })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    updateScreenOffBadge(enabled);
                    showToast(enabled ? "Mode Screen Off DIAKTIFKAN pada semua HP (Layar Gelap Total)" : "Mode Screen Off DINONAKTIFKAN (Layar Nyala)", enabled ? "warning" : "success");
                    // Sync checkbox di tiap card
                    document.querySelectorAll('.pad-screen-off-check').forEach(cb => {
                        cb.checked = enabled;
                    });
                }
            } catch (err) {
                showToast("Gagal mengubah mode screen off: " + err.message, "error");
            }
        });
    }

    if (switchBatchAuto) {
        switchBatchAuto.addEventListener('change', (e) => {
            const enabled = e.target.checked;
            batchAutoState = enabled;
            if (batchAutoStatusBadge) {
                batchAutoStatusBadge.className = `badge-screen-status ${enabled ? 'status-on' : 'status-off'}`;
                batchAutoStatusBadge.textContent = enabled ? 'BATCH ON' : 'BATCH OFF';
            }
            document.querySelectorAll('.pad-auto-toggle-check').forEach(cb => {
                cb.checked = enabled;
            });
            showToast(`Mode Batch Sync ${enabled ? 'DIAKTIFKAN (Semua PAD Otomatis Sinkron)' : 'DINONAKTIFKAN (PAD Berjalan Mandiri)'}`, enabled ? 'success' : 'warning');
        });
    }

    // =========================================================================
    // 4.1. PAD LAYOUT MODE CONTROLLER (SPLIT 2-KOLOM VS HORIZONTAL SWIPE)
    // =========================================================================
    function setPadLayout(layout) {
        if (!devicesGridContainer) return;
        devicesGridContainer.classList.remove('layout-split', 'layout-horizontal');
        if (layout === 'horizontal') {
            devicesGridContainer.classList.add('layout-horizontal');
            if (btnLayoutHorizontal) btnLayoutHorizontal.classList.add('active');
            if (btnLayoutSplit) btnLayoutSplit.classList.remove('active');
        } else {
            devicesGridContainer.classList.add('layout-split');
            if (btnLayoutSplit) btnLayoutSplit.classList.add('active');
            if (btnLayoutHorizontal) btnLayoutHorizontal.classList.remove('active');
        }
        localStorage.setItem('topnod_pad_layout', layout);
    }

    if (btnLayoutSplit) {
        btnLayoutSplit.addEventListener('click', () => {
            setPadLayout('split');
            showToast("Mode Tampilan: 2-PAD Split (2 Kolom Berdampingan)", "success");
        });
    }

    if (btnLayoutHorizontal) {
        btnLayoutHorizontal.addEventListener('click', () => {
            setPadLayout('horizontal');
            showToast("Mode Tampilan: Horizontal Scroll (Geser / Swipe Samping)", "success");
        });
    }

    // Load layout tersimpan atau default ke 'split' (2-PAD split berdampingan)
    const savedLayout = localStorage.getItem('topnod_pad_layout') || 'split';
    setPadLayout(savedLayout);

    function updateScreenOffBadge(enabled) {
        isScreenOffMaster = enabled;
        if (switchMasterScreenOff) switchMasterScreenOff.checked = enabled;
        if (screenOffStatusBadge) {
            if (enabled) {
                screenOffStatusBadge.className = 'badge-screen-status status-on';
                screenOffStatusBadge.textContent = 'ON (Layar Mati)';
            } else {
                screenOffStatusBadge.className = 'badge-screen-status status-off';
                screenOffStatusBadge.textContent = 'OFF (Layar Nyala)';
            }
        }
    }

    async function toggleDeviceScreenOff(serial, enabled) {
        try {
            const res = await fetch('/api/screen/mode_screen_off', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ device: serial, enabled: enabled })
            });
            const data = await res.json();
            if (data.status === 'success') {
                showToast(`Screen Off ${serial}: ${enabled ? 'AKTIF (Layar Mati)' : 'NONAKTIF (Layar Nyala)'}`, "success");
            }
        } catch (e) {
            showToast("Gagal toggle screen off: " + e.message, "error");
        }
    }

    // =========================================================================
    // 5. QUICK ACTIONS & TOOLS
    // =========================================================================
    if (btnSetScreenBot) {
        btnSetScreenBot.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/screen/set', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ device: 'all' })
                });
                const data = await res.json();
                showToast("Format Layar Bot (1080x2400 @ 352 DPI + Font 0.81) sukses diterapkan ke SEMUA HP!", "success");
            } catch (e) {
                showToast("Gagal set layar: " + e.message, "error");
            }
        });
    }

    if (btnRestoreScreen) {
        btnRestoreScreen.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/screen/restore', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ device: 'all' })
                });
                const data = await res.json();
                showToast(data.message, "success");
            } catch (e) {
                showToast("Gagal restore layar: " + e.message, "error");
            }
        });
    }

    if (btnLaunchScrcpy) {
        btnLaunchScrcpy.addEventListener('click', async () => {
            const fps = selectMirrorFps ? parseInt(selectMirrorFps.value) || 120 : 120;
            btnLaunchScrcpy.disabled = true;
            try {
                const res = await fetch('/api/scrcpy', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ device: 'all', fps: fps })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    showToast(data.message || `Mirror SCRCPY (${fps} FPS) untuk semua HP diluncurkan!`, "success");
                } else {
                    showToast(data.message || "Gagal membuka SCRCPY", "error");
                }
            } catch (e) {
                showToast("Gagal membuka SCRCPY: " + e.message, "error");
            } finally {
                btnLaunchScrcpy.disabled = false;
            }
        });
    }

    if (btnRestartTerminal) {
        btnRestartTerminal.addEventListener('click', async () => {
            btnRestartTerminal.disabled = true;
            btnRestartTerminal.textContent = '🔄 Restarting...';
            showToast("Merestart ADB Server & me-refresh perangkat...", "warning");
            try {
                const res = await fetch('/api/terminal/restart', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'success') {
                    showToast("ADB Server berhasil di-restart!", "success");
                    if (terminalOutput) terminalOutput.innerHTML = '';
                    updateStatus();
                } else {
                    showToast("Gagal restart ADB: " + data.message, "error");
                }
            } catch (e) {
                showToast("Error restart ADB: " + e.message, "error");
            } finally {
                btnRestartTerminal.disabled = false;
                btnRestartTerminal.textContent = '🔄 Restart Terminal';
            }
        });
    }

    if (btnStartAllDevices) {
        btnStartAllDevices.addEventListener('click', async () => {
            try {
                // Jalankan pada semua PAD yang checkbox ADB On-nya aktif
                let startedCount = 0;
                for (const d of connectedDevices) {
                    const card = document.getElementById(`padCard_${d.serial}`);
                    const adbOnCheck = card ? card.querySelector('.pad-auto-toggle-check') : null;
                    if (!adbOnCheck || adbOnCheck.checked) {
                        const cloneEl = card ? card.querySelector('.pad-clone-input') : null;
                        const accountNum = parseInt((cloneEl ? cloneEl.value : '') || 1) || 1;
                        const refEl = card ? card.querySelector('.pad-reff-input') : null;
                        const refCode = (refEl && refEl.value ? refEl.value.trim() : '') || null;
                        const addrEl = card ? card.querySelector('.pad-address-input') : null;
                        const addrWd = (addrEl && addrEl.value ? addrEl.value.trim() : '') || null;
                        const walletEl = card ? card.querySelector('.pad-wallet-select') : null;
                        const walletFile = (walletEl ? walletEl.value : '') || null;
                        await fetch('/api/bot/start', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                device: d.serial,
                                mode: currentMode,
                                start_index: accountNum,
                                master_referral: refCode,
                                alamat_wd: addrWd,
                                wallet_file: walletFile
                            })
                        });
                        startedCount++;
                    }
                }
                showToast(`Full Auto dijalankan pada ${startedCount} PAD aktif!`, "success");
            } catch (e) {
                showToast("Gagal start semua: " + e.message, "error");
            }
        });
    }

    if (btnNextAllDevices) {
        btnNextAllDevices.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/bot/next', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ device: 'all' })
                });
                const data = await res.json();
                showToast(data.message, "success");
            } catch (e) {
                showToast("Gagal next: " + e.message, "error");
            }
        });
    }

    if (btnStopAllDevices) {
        btnStopAllDevices.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/bot/stop', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ device: 'all' })
                });
                const data = await res.json();
                showToast(data.message, "success");
            } catch (e) {
                showToast("Gagal stop: " + e.message, "error");
            }
        });
    }

    // =========================================================================
    // 6. DYNAMIC TOPNOD PAD CARDS RENDERER
    // =========================================================================
    function renderDevicePads(devices) {
        if (!devicesGridContainer) return;

        if (!devices || devices.length === 0) {
            devicesGridContainer.innerHTML = `
                <div class="device-empty-state">
                    <div class="empty-state-icon">📱🔌</div>
                    <h3 class="empty-state-title">Tidak Ada HP Terdeteksi via ADB</h3>
                    <p class="empty-state-desc">Komputer belum mendeteksi HP Android Anda. Silakan periksa hal berikut:</p>
                    <ul class="empty-state-steps">
                        <li><strong>1.</strong> Pastikan opsi <strong>Debugging USB</strong> aktif di HP (Pengaturan → Opsi Pengembang).</li>
                        <li><strong>2.</strong> Buka layar HP dan klik <strong>"Izinkan" / "OK"</strong> jika muncul notifikasi pop-up USB Debugging.</li>
                        <li><strong>3.</strong> Pastikan mode USB di HP diatur ke <strong>File Transfer (MTP)</strong>, bukan hanya isi daya.</li>
                        <li><strong>4.</strong> Coba cabut dan colokkan kembali kabel USB ke port PC / HP.</li>
                    </ul>
                    <button type="button" class="btn-refresh-adb" id="btnEmptyRefreshAdb">
                        <span>🔄</span> Deteksi Ulang Perangkat (Restart ADB)
                    </button>
                </div>
            `;
            const btnEmptyRefresh = document.getElementById('btnEmptyRefreshAdb');
            if (btnEmptyRefresh) {
                btnEmptyRefresh.addEventListener('click', async () => {
                    btnEmptyRefresh.disabled = true;
                    btnEmptyRefresh.innerHTML = '<span>⏳</span> Memeriksa ADB...';
                    try {
                        const res = await fetch('/api/terminal/restart', { method: 'POST' });
                        const d = await res.json();
                        showToast(d.message || "ADB berhasil di-restart!", "success");
                        setTimeout(pollStatus, 800);
                    } catch (e) {
                        showToast("Gagal restart ADB: " + e.message, "error");
                    } finally {
                        setTimeout(() => {
                            btnEmptyRefresh.disabled = false;
                            btnEmptyRefresh.innerHTML = '<span>🔄</span> Deteksi Ulang Perangkat (Restart ADB)';
                        }, 1200);
                    }
                });
            }
            return;
        }

        // Simpan input value yang sedang diketik user agar tidak ter-reset saat re-render
        const savedInputs = {};
        devices.forEach(d => {
            const card = document.getElementById(`padCard_${d.serial}`);
            if (card) {
                const reffInp = card.querySelector('.pad-reff-input');
                const addrInp = card.querySelector('.pad-address-input');
                const adbInp = card.querySelector('.input-manual-adb');
                const cloneInp = card.querySelector('.pad-clone-input');
                const walletSel = card.querySelector('.pad-wallet-select');
                const adbOnCb = card.querySelector('.pad-auto-toggle-check');
                savedInputs[d.serial] = {
                    reff: reffInp ? reffInp.value : null,
                    address: addrInp ? addrInp.value : null,
                    adb: adbInp ? adbInp.value : null,
                    clone: cloneInp ? cloneInp.value : null,
                    wallet: walletSel ? walletSel.value : null,
                    adbOn: adbOnCb ? adbOnCb.checked : null
                };
            }
        });

        devicesGridContainer.innerHTML = '';

        devices.forEach((dev, index) => {
            const padNum = index + 1;
            const serial = dev.serial;
            const phoneName = dev.model || dev.raw_model || 'Android';
            const fullTitle = dev.full_model || phoneName;
            const botState = dev.bot_state || 'IDLE';
            const isWaiting = (botState === 'WAITING_NEXT');
            const isRunning = (botState === 'RUNNING');
            const isScreenOff = Boolean(dev.is_screen_off);
            const currentClone = dev.current_clone || serverConfig.start_index || 1;
            const nextClone = dev.next_clone || (currentClone + 1);
            const defaultRef = serverConfig.current_referral_code || serverConfig.master_referral_code || "srTwuLUy";
            const defaultAddress = serverConfig.alamat_wd || "GAEL2XQRRNPV2TCCFJFHHP277MN3MXUU2EZMRXRQBDVIUZLLODVH2SS5";
            const isWdMode = (currentMode === 'wd_baru' || currentMode === 'wd_old');
            const serialInputs = savedInputs[serial] || {};
            const currentWalletFile = serialInputs.wallet || dev.wallet_file || (availableWallets.length > 0 ? availableWallets[0] : "");
            const isAdbOn = (serialInputs.adbOn !== null && serialInputs.adbOn !== undefined) 
                ? serialInputs.adbOn 
                : batchAutoState;

            const card = document.createElement('div');
            card.id = `padCard_${serial}`;
            card.className = `device-pad-card ${isRunning ? 'pad-running' : ''} ${isWaiting ? 'pad-waiting' : ''}`;

            card.innerHTML = `
                <!-- PAD HEADER (TOPNOD COMPACT 2-ROW) -->
                <div class="pad-header">
                    <div class="pad-header-top-row">
                        <div class="pad-id-label">
                            <span class="pad-num-tag">PAD ${padNum}:</span>
                            <span class="pad-phone-name" title="${fullTitle}">${phoneName}</span>
                            <span class="pad-signal-icon">📶</span>
                        </div>
                        <label class="checkbox-container pad-adb-on-label" title="Status ADB On / Auto Loop untuk PAD ini">
                            <input type="checkbox" class="pad-auto-toggle-check" data-serial="${serial}" ${isAdbOn ? 'checked' : ''}>
                            <span class="checkmark"></span>
                            <span class="label-text">ADB On</span>
                        </label>
                    </div>
                    <div class="pad-header-bottom-row">
                        <div class="pad-serial-badge">${serial}</div>
                        <div class="pad-state-badge pad-state-${botState.toLowerCase()}">
                            ● ${botState}
                        </div>
                        <button type="button" class="btn-pad-mini-mirror" data-serial="${serial}" title="Buka Mirror SCRCPY untuk HP ini">🖥️ Mirror</button>
                        <label class="checkbox-container pad-screen-off-label" title="Matikan layar fisik HP ini">
                            <input type="checkbox" class="pad-screen-off-check" data-serial="${serial}" ${isScreenOff ? 'checked' : ''}>
                            <span class="checkmark"></span>
                            <span class="label-text" style="color:#7dd3fc; font-weight:700;">🌙</span>
                        </label>
                    </div>
                </div>

                <!-- PER-PAD WALLET SELECTOR (IMPORT MANDIRI) -->
                <div class="pad-wallet-group" title="File wallet (.txt) mandiri untuk PAD ini">
                    <select class="pad-wallet-select" data-serial="${serial}">
                        ${(availableWallets.length > 0 ? availableWallets : (currentWalletFile ? [currentWalletFile] : [])).map(w => `<option value="${w}" ${w === currentWalletFile ? 'selected' : ''}>📁 ${w}</option>`).join('')}
                    </select>
                </div>

                <!-- PAD CONFIG (ADDRESS UNTUK MODE WD XLM / REFF UNTUK MODE BUAT AKUN) -->
                <div class="pad-config-row ${isWdMode ? 'pad-config-wd' : ''}">
                    ${isWdMode ? `
                    <div class="pad-input-group pad-address-group">
                        <span class="pad-input-label" title="Alamat Stellar Tujuan Penarikan XLM">Alamat Stellar:</span>
                        <div class="pad-reff-row">
                            <input type="text" class="pad-input-text pad-address-input" data-serial="${serial}" value="${serialInputs.address || defaultAddress}" placeholder="Alamat Stellar (GAEL...)" title="Alamat Stellar Tujuan (GAEL...)">
                            <button type="button" class="btn-pad-mini btn-save-address" data-serial="${serial}" title="Simpan Alamat Stellar">💾</button>
                        </div>
                    </div>
                    ` : `
                    <div class="pad-input-group">
                        <span class="pad-input-label">Kode Reff Relay:</span>
                        <div class="pad-reff-row">
                            <input type="text" class="pad-input-text pad-reff-input" data-serial="${serial}" value="${serialInputs.reff || defaultRef}" placeholder="Kode Reff" maxlength="24">
                            <button type="button" class="btn-pad-mini btn-save-reff" data-serial="${serial}" title="Simpan Kode Reff">💾</button>
                        </div>
                    </div>
                    `}
                    <div class="pad-input-group">
                        <span class="pad-input-label">Clone:</span>
                        <div class="input-stepper">
                            <button type="button" class="btn-step btn-step-dec" data-serial="${serial}">-</button>
                            <input type="number" class="pad-clone-input" data-serial="${serial}" min="1" max="999" value="${serialInputs.clone || currentClone}">
                            <button type="button" class="btn-step btn-step-inc" data-serial="${serial}">+</button>
                        </div>
                    </div>
                </div>

                <!-- QUICK NAVIGATION KEYS & MANUAL ADB COMMAND -->
                <div class="pad-nav-and-adb-box">
                    <div class="nav-keys-row">
                        <button type="button" class="btn-nav-key btn-key-back" data-serial="${serial}" title="Kirim tombol Back (keyevent 4)">
                            <span>◁</span> <span class="nav-key-label">Back</span>
                        </button>
                        <button type="button" class="btn-nav-key btn-key-home" data-serial="${serial}" title="Kirim tombol Home (keyevent 3)">
                            <span>⌂</span> <span class="nav-key-label">Home</span>
                        </button>
                        <button type="button" class="btn-nav-key btn-key-recents" data-serial="${serial}" title="Kirim tombol Recents (keyevent 187)">
                            <span>▢</span> <span class="nav-key-label">Recents</span>
                        </button>
                    </div>
                    <div class="manual-adb-row">
                        <input type="text" class="input-manual-adb" data-serial="${serial}" value="${serialInputs.adb || ''}" placeholder="Manual ADB...">
                        <button type="button" class="btn-manual-adb-send" data-serial="${serial}" title="Kirim perintah ADB langsung">❯</button>
                    </div>
                </div>

                <!-- PAD MAIN ACTIONS (RUN AUTO & TERMINATE DI ATAS LANGKAH FLOW) -->
                <div class="pad-footer-actions pad-actions-top">
                    ${isWaiting ? `
                        <button type="button" class="btn-pad-next active-prompt" data-serial="${serial}">
                            <span>⏩</span> Lanjut #${nextClone} (Enter)
                        </button>
                    ` : ''}
                    <button type="button" class="btn-pad-run" data-serial="${serial}" ${isRunning ? 'disabled' : ''}>
                        <span>⚡</span> <span class="pad-btn-label">Run Auto</span>
                    </button>
                    <button type="button" class="btn-pad-stop" data-serial="${serial}">
                        <span>⏹</span> <span class="pad-btn-label">Terminate</span>
                    </button>
                </div>

                <!-- TOPNOD STEP LIST (FULL FLOW TANPA SCROLL) -->
                <div class="pad-steps-box">
                    <div class="pad-steps-header">
                        <span class="pad-steps-title">Langkah Macro:</span>
                        <div class="pad-steps-actions">
                            <button type="button" class="btn-link-action btn-check-all-steps" data-serial="${serial}">Semua</button>
                            <span style="color:#475569;">|</span>
                            <button type="button" class="btn-link-action btn-uncheck-all-steps" data-serial="${serial}">Batal</button>
                            ${currentMode === 'qris_morph' ? `
                            <span style="color:#475569;">|</span>
                            <button type="button" class="btn-link-action btn-toggle-gaid-steps" data-serial="${serial}" title="Tampilkan / Sembunyikan 7 Langkah Detail GAID (0.1 - 0.7)">⚙️ GAID (0.1-0.7)</button>
                            ` : ''}
                        </div>
                    </div>
                    ${currentMode === 'qris_morph' ? `
                    <div class="qris-subcommands-toolbar">
                        <div class="qris-sub-title">⚡ SUB-COMMAND &amp; SUB-TAP (QRIS MORPH)</div>
                        <div class="qris-sub-grid">
                            <button type="button" class="btn-qris-sub btn-sub-cache" data-serial="${serial}" data-action="clear_cache" title="Paksa Berhenti Clone, Hapus Cache & Mode Pesawat 3s (Reset Atomik)">
                                <span>🧹 [X] Clear Cache Clone</span>
                            </button>
                            <button type="button" class="btn-qris-sub btn-sub-qris" data-serial="${serial}" data-action="generate_qris" title="Buat QRIS Dinamis Baru & Push ke Galeri HP (/sdcard/Download/)">
                                <span>🖼️ [Q] Generate QRIS</span>
                            </button>
                            <button type="button" class="btn-qris-sub btn-sub-tebar" data-serial="${serial}" data-action="auto_tebar" title="Kirim Saldo USDC On-Chain ke Address Tuyul (Baca Layar & Transfer)">
                                <span>⚡ [D] Auto-Tebar USDC</span>
                            </button>
                            <button type="button" class="btn-qris-sub btn-sub-gaid" data-serial="${serial}" data-action="reset_gaid" title="Jalankan Alur Lengkap Reset Google Advertising ID (Step 0.1 s/d 0.7)">
                                <span>🔄 [I] Reset GAID (0.1 - 0.7)</span>
                            </button>
                            <button type="button" class="btn-qris-sub btn-sub-tap" data-serial="${serial}" data-action="tap_add_token" title="Klik Tombol Cyan Tambahkan Token USDC (787, 2189)">
                                <span>➕ [Y] 4.1: Tambah Token</span>
                            </button>
                            <button type="button" class="btn-qris-sub btn-sub-tap" data-serial="${serial}" data-action="tap_amount" title="Klik Kolom Jumlah Pembayaran Saja (916, 1594)">
                                <span>🖱️ [E] 9.1: Jumlah</span>
                            </button>
                            <button type="button" class="btn-qris-sub btn-sub-tap" data-serial="${serial}" data-action="tap_token" title="Pilih Token USDC Paling Atas Saja (517, 1536)">
                                <span>🪙 [F] 9.2: Token USDC</span>
                            </button>
                            <button type="button" class="btn-qris-sub btn-sub-tap" data-serial="${serial}" data-action="tap_confirm" title="Klik Tombol Konfirmasi Pembayaran Saja (540, 2193)">
                                <span>💳 [G] 9.3: Konfirmasi</span>
                            </button>
                            <button type="button" class="btn-qris-sub btn-sub-tap" data-serial="${serial}" data-action="type_pin" title="Ketik Sandi PIN Transaksi">
                                <span>🔢 [P] PIN Transaksi</span>
                            </button>
                        </div>
                    </div>
                    ` : ''}
                    <div class="pad-steps-list" id="padStepsList_${serial}">
                        <!-- Rendered steps -->
                    </div>
                </div>
            `;

            devicesGridContainer.appendChild(card);

            // Render Macro Steps ke dalam kartu PAD ini
            const stepsListEl = document.getElementById(`padStepsList_${serial}`);
            if (stepsListEl && cachedSteps.length > 0) {
                const isQrisMorph = (currentMode === 'qris_morph');
                let gaidGroupEl = null;
                if (isQrisMorph) {
                    gaidGroupEl = document.createElement('div');
                    gaidGroupEl.className = 'gaid-steps-group';
                    gaidGroupEl.id = `gaidStepsGroup_${serial}`;
                    gaidGroupEl.style.display = 'none';
                    const gaidGroupHeader = document.createElement('div');
                    gaidGroupHeader.className = 'gaid-steps-group-title';
                    gaidGroupHeader.innerHTML = '<span>⚙️ Detail Langkah Reset GAID (0.1 - 0.7) [Disembunyikan]</span>';
                    gaidGroupEl.appendChild(gaidGroupHeader);
                }

                cachedSteps.forEach(step => {
                    const sid = String(step.id);
                    const isGaidStep = isQrisMorph && (['0.1', '0.2', '0.3', '0.4', '0.5', '0.6', '0.7'].indexOf(sid) !== -1);

                    // 0. Sisipkan Tombol Cepat Reset Atomik / Clear Cache di awal Step 0.0
                    if (isQrisMorph && (sid === '0.0' || sid === '0')) {
                        const cacheRow = document.createElement('div');
                        cacheRow.className = 'topnod-step-item step-item-cache-quick';
                        cacheRow.innerHTML = `
                            <button type="button" class="btn-step-action btn-quick-cache" data-serial="${serial}" data-action="clear_cache" title="Paksa Berhenti Clone, Hapus Cache & Mode Pesawat 3s (Reset Atomik)">
                                <span class="step-btn-text">🧹 [X] Sub-Tap: Reset Atomik Clone (Force Stop + Clear Cache + Mode Pesawat 3s)</span>
                            </button>
                        `;
                        stepsListEl.appendChild(cacheRow);
                    }

                    // 1.5 Sisipkan Tombol Cepat Generate QRIS di awal Step 0.8
                    if (isQrisMorph && (sid === '0.8' || sid === 'qris')) {
                        if (gaidGroupEl && !gaidGroupEl.parentNode) {
                            stepsListEl.appendChild(gaidGroupEl);
                        }
                        const qrisRow = document.createElement('div');
                        qrisRow.className = 'topnod-step-item step-item-qris-quick';
                        qrisRow.innerHTML = `
                            <button type="button" class="btn-step-action btn-quick-qris" data-serial="${serial}" data-action="generate_qris" title="Buat QRIS GoBiz Dinamis & Push Langsung ke Galeri HP">
                                <span class="step-btn-text">🖼️ [Q] Sub-Tap: Generate QRIS GoBiz Dinamis &amp; Push ke Galeri HP</span>
                            </button>
                        `;
                        stepsListEl.appendChild(qrisRow);
                    }

                    // 2. Sisipkan Tombol Auto-Tebar On-Chain antara Step 8 dan Step 9
                    if (isQrisMorph && String(step.id) === '9') {
                        const tebarRow = document.createElement('div');
                        tebarRow.className = 'topnod-step-item step-item-auto-tebar';
                        tebarRow.innerHTML = `
                            <button type="button" class="btn-step-action btn-auto-tebar" data-serial="${serial}" data-action="auto_tebar" title="Kirim Saldo USDC On-Chain ke Tuyul (Baca Layar & Transfer)">
                                <span class="step-btn-text">⚡ [D] Auto-Tebar: Kirim Saldo USDC (Baca Layar &amp; Transfer On-Chain)</span>
                            </button>
                        `;
                        stepsListEl.appendChild(tebarRow);
                    }

                    const stepRow = document.createElement('div');
                    stepRow.className = 'topnod-step-item';
                    const isChecked = step.enabled !== false && !step.is_off;
                    const sleepVal = (step.sleep !== null && step.sleep !== undefined) ? step.sleep : 1.0;

                    const isStep2Wd = (String(step.id) === '2' && (currentMode.includes('wd') || currentMode.includes('baru')));
                    if (isStep2Wd) {
                        const curStep2 = currentStep2Mode || 'dompet';
                        stepRow.innerHTML = `
                            <input type="checkbox" class="step-auto-checkbox" data-serial="${serial}" data-step-id="${step.id}" ${isChecked ? 'checked' : ''} title="Centang untuk Full Auto sequence">
                            <div class="step-split-btns" data-step-id="${step.id}">
                                <button type="button" class="btn-step-manual btn-step-sub ${curStep2 === 'profil' ? 'active-sub' : 'inactive-sub'}" data-serial="${serial}" data-step-id="${step.id}" data-action="profil" title="Klik Profil / Avatar (78, 119) [Perlu Step 3 Beralih]">
                                    <span class="step-btn-text">👤 2. Profil</span>
                                </button>
                                <button type="button" class="btn-step-manual btn-step-sub ${curStep2 === 'dompet' ? 'active-sub' : 'inactive-sub'}" data-serial="${serial}" data-step-id="${step.id}" data-action="dompet" title="Klik Dompet Saya (197, 284) [Langsung Ganti Dompet]">
                                    <span class="step-btn-text">👛 Dompet Saya</span>
                                </button>
                            </div>
                            <div class="step-sleep-box" title="Jeda sleep detik (Ketik angka atau klik panah untuk ±0.5s)">
                                <input type="number" class="step-sleep-input" data-serial="${serial}" data-step-id="${step.id}" step="0.5" min="0" max="60" value="${sleepVal}">
                                <span class="sleep-s-label">s</span>
                                <div class="sleep-arrows-group">
                                    <button type="button" class="btn-spin-arrow btn-spin-up" data-serial="${serial}" data-step-id="${step.id}" title="Tambah 0.5 detik">▲</button>
                                    <button type="button" class="btn-spin-arrow btn-spin-down" data-serial="${serial}" data-step-id="${step.id}" title="Kurangi 0.5 detik">▼</button>
                                </div>
                            </div>
                        `;
                    } else if (isQrisMorph && String(step.id) === '9') {
                        stepRow.className = 'topnod-step-item step-item-with-subtaps';
                        stepRow.innerHTML = `
                            <input type="checkbox" class="step-auto-checkbox" data-serial="${serial}" data-step-id="${step.id}" ${isChecked ? 'checked' : ''} title="Centang untuk Full Auto sequence">
                            <div class="step-with-subtaps-col">
                                <button type="button" class="btn-step-manual" data-serial="${serial}" data-step-id="${step.id}" title="Klik untuk eksekusi langkah 9 lengkap di HP">
                                    <span class="step-btn-text">${step.full_title || (step.id + '. ' + step.name)}</span>
                                </button>
                                <div class="step-subtaps-row">
                                    <button type="button" class="btn-qris-sub-mini" data-serial="${serial}" data-action="tap_amount" title="Hanya Klik Kolom Jumlah (916 1594)">[E] 9.1 Jumlah</button>
                                    <button type="button" class="btn-qris-sub-mini" data-serial="${serial}" data-action="tap_token" title="Hanya Pilih Token USDC (517 1536)">[F] 9.2 USDC</button>
                                    <button type="button" class="btn-qris-sub-mini" data-serial="${serial}" data-action="tap_confirm" title="Hanya Klik Konfirmasi (540 2193)">[G] 9.3 Konfirmasi</button>
                                </div>
                            </div>
                            <div class="step-sleep-box" title="Jeda sleep detik (Ketik angka atau klik panah untuk ±0.5s)">
                                <input type="number" class="step-sleep-input" data-serial="${serial}" data-step-id="${step.id}" step="0.5" min="0" max="60" value="${sleepVal}">
                                <span class="sleep-s-label">s</span>
                                <div class="sleep-arrows-group">
                                    <button type="button" class="btn-spin-arrow btn-spin-up" data-serial="${serial}" data-step-id="${step.id}" title="Tambah 0.5 detik">▲</button>
                                    <button type="button" class="btn-spin-arrow btn-spin-down" data-serial="${serial}" data-step-id="${step.id}" title="Kurangi 0.5 detik">▼</button>
                                </div>
                            </div>
                        `;
                    } else {
                        stepRow.innerHTML = `
                            <input type="checkbox" class="step-auto-checkbox" data-serial="${serial}" data-step-id="${step.id}" ${isChecked ? 'checked' : ''} title="Centang untuk Full Auto sequence">
                            <button type="button" class="btn-step-manual" data-serial="${serial}" data-step-id="${step.id}" title="Klik untuk eksekusi langkah ini langsung di HP">
                                <span class="step-btn-text">${step.full_title || (step.id + '. ' + step.name)}</span>
                            </button>
                            <div class="step-sleep-box" title="Jeda sleep detik (Ketik angka atau klik panah untuk ±0.5s)">
                                <input type="number" class="step-sleep-input" data-serial="${serial}" data-step-id="${step.id}" step="0.5" min="0" max="60" value="${sleepVal}">
                                <span class="sleep-s-label">s</span>
                                <div class="sleep-arrows-group">
                                    <button type="button" class="btn-spin-arrow btn-spin-up" data-serial="${serial}" data-step-id="${step.id}" title="Tambah 0.5 detik">▲</button>
                                    <button type="button" class="btn-spin-arrow btn-spin-down" data-serial="${serial}" data-step-id="${step.id}" title="Kurangi 0.5 detik">▼</button>
                                </div>
                            </div>
                        `;
                    }
                    if (isGaidStep && gaidGroupEl) {
                        gaidGroupEl.appendChild(stepRow);
                    } else {
                        stepsListEl.appendChild(stepRow);
                    }
                });

                if (gaidGroupEl && !gaidGroupEl.parentNode) {
                    stepsListEl.appendChild(gaidGroupEl);
                }
            } else if (stepsListEl) {
                stepsListEl.innerHTML = '<div style="font-size:11px; color:#94a3b8; text-align:center; padding:10px;">Tidak ada langkah untuk mode ini</div>';
            }

            // Wire Card Events
            wirePadCardEvents(card, serial);
        });
    }

    // =========================================================================
    // 7. WIRE PER-CARD INTERACTION EVENTS
    // =========================================================================
    // Helper: Mengambil seluruh target PAD yang aktif untuk sinkronisasi batch
    function getActivePadTargets(sourceSerial) {
        if (!batchAutoState) {
            const card = document.getElementById(`padCard_${sourceSerial}`);
            const cloneInput = card ? card.querySelector('.pad-clone-input') : null;
            const cloneNum = parseInt(cloneInput ? cloneInput.value : 1) || 1;
            return [{ serial: sourceSerial, card, cloneNum }];
        }
        
        const targets = [];
        document.querySelectorAll('.device-pad-card').forEach(c => {
            const cb = c.querySelector('.pad-auto-toggle-check');
            const s = (cb ? cb.getAttribute('data-serial') : null) || c.id.replace('padCard_', '');
            if (s && (!cb || cb.checked)) {
                const cloneInput = c.querySelector('.pad-clone-input');
                const cloneNum = parseInt(cloneInput ? cloneInput.value : 1) || 1;
                targets.push({ serial: s, card: c, cloneNum });
            }
        });

        // Fallback jika tidak ada yang tercentang: gunakan sourceSerial
        if (targets.length === 0) {
            const card = document.getElementById(`padCard_${sourceSerial}`);
            const cloneInput = card ? card.querySelector('.pad-clone-input') : null;
            const cloneNum = parseInt(cloneInput ? cloneInput.value : 1) || 1;
            targets.push({ serial: sourceSerial, card, cloneNum });
        }
        return targets;
    }

    // =========================================================================
    // 7. WIRE PER-CARD INTERACTION EVENTS (BIDIRECTIONAL BATCH SYNC SUPPORT)
    // =========================================================================
    function wirePadCardEvents(card, serial) {
        // 1. Screen Off Checkbox
        const screenOffCheck = card.querySelector('.pad-screen-off-check');
        if (screenOffCheck) {
            screenOffCheck.addEventListener('change', (e) => {
                toggleDeviceScreenOff(serial, e.target.checked);
            });
        }

        // 1.0. Per-PAD Mirror SCRCPY
        const padMirrorBtn = card.querySelector('.btn-pad-mini-mirror');
        if (padMirrorBtn) {
            padMirrorBtn.addEventListener('click', async () => {
                const fps = selectMirrorFps ? parseInt(selectMirrorFps.value) || 120 : 120;
                padMirrorBtn.disabled = true;
                const oldText = padMirrorBtn.innerHTML;
                padMirrorBtn.innerHTML = '⏳ ...';
                try {
                    const res = await fetch('/api/scrcpy', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ device: serial, fps: fps })
                    });
                    const d = await res.json();
                    if (d.status === 'success') {
                        showToast(d.message || `Mirror (${fps} FPS) diluncurkan!`, "success");
                    } else {
                        showToast(d.message || "Gagal membuka Mirror", "error");
                    }
                } catch (err) {
                    showToast("Gagal membuka Mirror: " + err.message, "error");
                } finally {
                    padMirrorBtn.disabled = false;
                    padMirrorBtn.innerHTML = oldText;
                }
            });
        }

        // 1.1. Per-PAD Wallet Select
        const walletSelect = card.querySelector('.pad-wallet-select');
        if (walletSelect) {
            walletSelect.addEventListener('change', async (e) => {
                const chosenFile = e.target.value;
                try {
                    const res = await fetch('/api/device/wallet_file', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ device: serial, wallet_file: chosenFile })
                    });
                    const d = await res.json();
                    showToast(d.message, "success");
                } catch (err) {
                    showToast("Gagal update wallet file: " + err.message, "error");
                }
            });
        }

        // 1.2. ADB On / Auto Toggle Checkbox
        const adbOnCheck = card.querySelector('.pad-auto-toggle-check');
        if (adbOnCheck) {
            adbOnCheck.addEventListener('change', (e) => {
                showToast(`PAD ${serial}: ADB Auto ${e.target.checked ? 'AKTIF' : 'NONAKTIF'}`, e.target.checked ? "success" : "warning");
            });
        }

        // 2. Save Referral Button — SINKRONISASI BATCH
        const btnSaveReff = card.querySelector('.btn-save-reff');
        const reffInput = card.querySelector('.pad-reff-input');
        if (btnSaveReff && reffInput) {
            const doSaveReff = async () => {
                const code = reffInput.value.trim();
                if (!code) {
                    showToast("Kode referral tidak boleh kosong", "error");
                    return;
                }
                try {
                    const res = await fetch('/api/create_account/referral/update', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ referral_code: code, master_referral: code })
                    });
                    const d = await res.json();
                    showToast(d.message, "success");
                    if (summaryMasterRef) summaryMasterRef.textContent = code;
                    if (batchAutoState) {
                        document.querySelectorAll('.pad-reff-input').forEach(inp => {
                            inp.value = code;
                        });
                    }
                } catch (e) {
                    showToast("Gagal menyimpan referral: " + e.message, "error");
                }
            };
            btnSaveReff.addEventListener('click', doSaveReff);
            reffInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') doSaveReff();
            });
        }

        // 2.1. Save Stellar Target Address Button (Mode WD XLM) — SINKRONISASI BATCH
        const btnSaveAddress = card.querySelector('.btn-save-address');
        const addressInput = card.querySelector('.pad-address-input');
        if (btnSaveAddress && addressInput) {
            const doSaveAddress = async () => {
                const addr = addressInput.value.trim();
                if (!addr) {
                    showToast("Alamat Stellar tidak boleh kosong", "error");
                    return;
                }
                try {
                    const res = await fetch('/api/config', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ alamat_wd: addr })
                    });
                    const d = await res.json();
                    if (d.status === 'success') {
                        serverConfig.alamat_wd = addr;
                        showToast(`Alamat Stellar tujuan disimpan: ${addr.substring(0, 10)}...`, "success");
                        if (summaryMasterRef && (currentMode === 'wd_baru' || currentMode === 'wd_old')) {
                            summaryMasterRef.textContent = addr.substring(0, 5) + '...' + addr.slice(-4);
                            summaryMasterRef.title = `Alamat Stellar Tujuan: ${addr}`;
                        }
                        if (batchAutoState) {
                            document.querySelectorAll('.pad-address-input').forEach(inp => {
                                inp.value = addr;
                            });
                        }
                    } else {
                        showToast(d.message || "Gagal menyimpan alamat", "error");
                    }
                } catch (e) {
                    showToast("Gagal menyimpan alamat Stellar: " + e.message, "error");
                }
            };
            btnSaveAddress.addEventListener('click', doSaveAddress);
            addressInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') doSaveAddress();
            });
        }

        // 3. Clone Stepper
        const cloneInput = card.querySelector('.pad-clone-input');
        const btnDec = card.querySelector('.btn-step-dec');
        const btnInc = card.querySelector('.btn-step-inc');
        if (cloneInput && btnDec && btnInc) {
            btnDec.addEventListener('click', () => {
                const v = Math.max(1, (parseInt(cloneInput.value) || 1) - 1);
                cloneInput.value = v;
            });
            btnInc.addEventListener('click', () => {
                const v = Math.min(999, (parseInt(cloneInput.value) || 1) + 1);
                cloneInput.value = v;
            });
        }

        // 4. Quick Nav Keys (<, ^, []) — SINKRONISASI BATCH
        const btnBack = card.querySelector('.btn-key-back');
        const btnHome = card.querySelector('.btn-key-home');
        const btnRecents = card.querySelector('.btn-key-recents');
        
        const triggerNavKey = (cmd, keyName) => {
            const targets = getActivePadTargets(serial);
            targets.forEach(t => {
                const navBtn = t.card ? t.card.querySelector(`.btn-key-${keyName}`) : null;
                if (navBtn) {
                    navBtn.style.borderColor = '#00ffa3';
                    setTimeout(() => { if (navBtn) navBtn.style.borderColor = ''; }, 300);
                }
            });
            if (batchAutoState && targets.length > 1) {
                targets.forEach(t => sendAdbCommand(t.serial, cmd, false));
                showToast(`[BATCH SYNC] ${keyName.toUpperCase()} dikirim ke ${targets.length} HP`, "success");
            } else {
                sendAdbCommand(serial, cmd, true);
            }
        };

        if (btnBack) btnBack.addEventListener('click', () => triggerNavKey('keyevent 4', 'back'));
        if (btnHome) btnHome.addEventListener('click', () => triggerNavKey('keyevent 3', 'home'));
        if (btnRecents) btnRecents.addEventListener('click', () => triggerNavKey('keyevent 187', 'recents'));

        // 5. Manual ADB Input Box — SINKRONISASI BATCH
        const manualAdbInput = card.querySelector('.input-manual-adb');
        const btnManualAdbSend = card.querySelector('.btn-manual-adb-send');
        if (manualAdbInput && btnManualAdbSend) {
            const executeManualAdb = () => {
                const cmd = manualAdbInput.value.trim();
                if (!cmd) return;
                const targets = getActivePadTargets(serial);
                if (batchAutoState && targets.length > 1) {
                    targets.forEach(t => {
                        const inp = t.card ? t.card.querySelector('.input-manual-adb') : null;
                        if (inp) inp.value = cmd;
                        sendAdbCommand(t.serial, cmd, false);
                    });
                    showToast(`[BATCH SYNC] ADB "${cmd}" dikirim ke ${targets.length} HP`, "success");
                } else {
                    sendAdbCommand(serial, cmd, true);
                }
            };
            btnManualAdbSend.addEventListener('click', executeManualAdb);
            manualAdbInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    executeManualAdb();
                }
            });
        }

        // 6. Check All / Uncheck All Steps — SINKRONISASI BATCH
        const btnCheckAll = card.querySelector('.btn-check-all-steps');
        const btnUncheckAll = card.querySelector('.btn-uncheck-all-steps');
        if (btnCheckAll) {
            btnCheckAll.addEventListener('click', async () => {
                if (batchAutoState) {
                    document.querySelectorAll('.step-auto-checkbox').forEach(cb => cb.checked = true);
                } else {
                    card.querySelectorAll('.step-auto-checkbox').forEach(cb => cb.checked = true);
                }
                await fetch('/api/step/toggle_all', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ enabled: true, mode: currentMode })
                });
                showToast("Semua langkah dicentang (Aktif)", "success");
            });
        }
        if (btnUncheckAll) {
            btnUncheckAll.addEventListener('click', async () => {
                if (batchAutoState) {
                    document.querySelectorAll('.step-auto-checkbox').forEach(cb => cb.checked = false);
                } else {
                    card.querySelectorAll('.step-auto-checkbox').forEach(cb => cb.checked = false);
                }
                await fetch('/api/step/toggle_all', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ enabled: false, mode: currentMode })
                });
                showToast("Semua langkah dinonaktifkan", "warning");
            });
        }

        const btnToggleGaid = card.querySelector('.btn-toggle-gaid-steps');
        if (btnToggleGaid) {
            btnToggleGaid.addEventListener('click', () => {
                const grp = card.querySelector(`#gaidStepsGroup_${serial}`);
                if (grp) {
                    const isHidden = (grp.style.display === 'none' || grp.style.display === '');
                    grp.style.display = isHidden ? 'block' : 'none';
                    btnToggleGaid.textContent = isHidden ? '👁️ Tutup GAID' : '⚙️ GAID (0.1-0.7)';
                    btnToggleGaid.style.color = isHidden ? '#f59e0b' : '#38bdf8';
                }
            });
        }

        // 7. Checkbox Step Toggle (Auto sequence) — SINKRONISASI BATCH
        card.querySelectorAll('.step-auto-checkbox').forEach(cb => {
            cb.addEventListener('change', async (e) => {
                const stepId = e.target.getAttribute('data-step-id');
                const enabled = e.target.checked;
                if (batchAutoState) {
                    document.querySelectorAll(`.step-auto-checkbox[data-step-id="${stepId}"]`).forEach(c => {
                        c.checked = enabled;
                    });
                }
                try {
                    await fetch('/api/step/toggle', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ step_id: stepId, enabled: enabled, mode: currentMode })
                    });
                } catch (err) {
                    console.error("Gagal toggle step:", err);
                }
            });
        });

        // 8. Manual Step Execution (BUTTON CLICK = INSTANT EXECUTION DENGAN SINKRONISASI BATCH)
        card.querySelectorAll('.btn-step-manual').forEach(btn => {
            btn.addEventListener('click', async () => {
                const stepId = btn.getAttribute('data-step-id');
                if (!stepId) return; // Abaikan tombol yang bukan macro step ber-ID
                const subAction = btn.getAttribute('data-action'); // 'profil' | 'dompet'
                const targets = getActivePadTargets(serial);

                // Khusus Step 2 dengan sub-action: update active state UI dan sinkronkan Step 3
                if (subAction) {
                    currentStep2Mode = subAction;
                    localStorage.setItem('bitget_step2_mode', subAction);
                    document.querySelectorAll('.btn-step-sub').forEach(b => {
                        const act = b.getAttribute('data-action');
                        if (act === subAction) {
                            b.classList.add('active-sub');
                            b.classList.remove('inactive-sub');
                        } else {
                            b.classList.remove('active-sub');
                            b.classList.add('inactive-sub');
                        }
                    });

                    // Sinkronkan checkbox Step 3 di UI
                    const shouldStep3BeActive = (subAction === 'profil');
                    document.querySelectorAll(`.step-auto-checkbox[data-step-id="3"]`).forEach(c => {
                        c.checked = shouldStep3BeActive;
                    });
                }

                // Tambahkan animasi .executing pada tombol langkah di SEMUA PAD target secara serentak
                const animatedButtons = [];
                targets.forEach(t => {
                    let targetBtn = null;
                    if (t.card) {
                        if (subAction) {
                            targetBtn = t.card.querySelector(`.btn-step-manual[data-step-id="${stepId}"][data-action="${subAction}"]`);
                        }
                        if (!targetBtn) {
                            targetBtn = t.card.querySelector(`.btn-step-manual[data-step-id="${stepId}"]`);
                        }
                    }
                    if (targetBtn) {
                        targetBtn.classList.add('executing');
                        animatedButtons.push(targetBtn);
                    }
                });

                try {
                    // Jalankan eksekusi secara paralel di semua perangkat target
                    const promises = targets.map(t => {
                        const payload = {
                            device: t.serial,
                            step_id: stepId,
                            mode: currentMode,
                            account_num: t.cloneNum
                        };
                        const addrEl = t.card ? t.card.querySelector('.pad-address-input') : null;
                        const addrWd = (addrEl && addrEl.value ? addrEl.value.trim() : '');
                        if (addrWd) {
                            payload.alamat_wd = addrWd;
                        }
                        if (subAction) {
                            payload.action = subAction;
                        }
                        return fetch('/api/step/execute', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify(payload)
                        }).then(r => r.json());
                    });

                    const results = await Promise.all(promises);
                    const allSuccess = results.every(r => r.status === 'success');
                    
                    const stepLabel = subAction ? (subAction === 'profil' ? 'Step 2 (Profil 78, 119)' : 'Step 2 (Dompet Saya 197, 284)') : `Step ${stepId}`;

                    if (targets.length > 1) {
                        showToast(`[BATCH SYNC] ${stepLabel} dieksekusi serentak pada ${targets.length} HP!`, allSuccess ? "success" : "warning");
                    } else {
                        const d = results[0];
                        if (d && d.status === 'success') {
                            showToast(`${stepLabel} dijalankan manual di ${serial}`, "success");
                        } else {
                            showToast((d && d.message) ? d.message : "Gagal eksekusi step", "error");
                        }
                    }
                } catch (e) {
                    showToast("Error eksekusi step: " + e.message, "error");
                } finally {
                    setTimeout(() => {
                        animatedButtons.forEach(b => b.classList.remove('executing'));
                    }, 1200);
                }
            });
        });

        // 8b. QRIS Sub-Command & Sub-Tap Execution (Batch Synced)
        card.querySelectorAll('.btn-qris-sub, .btn-qris-sub-mini, .btn-auto-tebar, .btn-quick-gaid, .btn-quick-cache, .btn-quick-qris').forEach(btn => {
            btn.addEventListener('click', async () => {
                const action = btn.getAttribute('data-action');
                const targets = getActivePadTargets(serial);
                
                const animatedButtons = [];
                targets.forEach(t => {
                    const b = t.card ? t.card.querySelector(`[data-action="${action}"]`) : null;
                    if (b) {
                        b.classList.add('executing');
                        animatedButtons.push(b);
                    }
                });
                if (animatedButtons.length === 0) {
                    btn.classList.add('executing');
                    animatedButtons.push(btn);
                }
                
                try {
                    const promises = targets.map(t => {
                        return fetch('/api/qris/sub_command', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                device: t.serial,
                                action: action
                            })
                        }).then(r => r.json());
                    });
                    
                    const results = await Promise.all(promises);
                    const allSuccess = results.every(r => r.status === 'success');
                    const d = results[0];
                    if (targets.length > 1) {
                        showToast(`[BATCH SYNC] Sub-command ${action} terkirim ke ${targets.length} HP`, allSuccess ? "success" : "warning");
                    } else {
                        showToast((d && d.message) ? d.message : `Sub-command ${action} dieksekusi`, allSuccess ? "success" : "error");
                    }
                } catch (e) {
                    showToast(`Error sub-command: ${e.message}`, "error");
                } finally {
                    setTimeout(() => {
                        animatedButtons.forEach(b => b.classList.remove('executing'));
                    }, 1200);
                }
            });
        });

        // 9. Run Full Auto — SINKRONISASI BATCH
        const btnRun = card.querySelector('.btn-pad-run');
        if (btnRun) {
            btnRun.addEventListener('click', async () => {
                const targets = getActivePadTargets(serial);
                try {
                    const promises = targets.map(t => {
                        const refEl = t.card ? t.card.querySelector('.pad-reff-input') : null;
                        const refCode = (refEl && refEl.value ? refEl.value.trim() : '') || null;
                        const addrEl = t.card ? t.card.querySelector('.pad-address-input') : null;
                        const addrWd = (addrEl && addrEl.value ? addrEl.value.trim() : '') || null;
                        const walletEl = t.card ? t.card.querySelector('.pad-wallet-select') : null;
                        const chosenWallet = (walletEl && walletEl.value ? walletEl.value : '') || null;
                        return fetch('/api/bot/start', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                device: t.serial,
                                mode: currentMode,
                                start_index: t.cloneNum,
                                master_referral: refCode,
                                alamat_wd: addrWd,
                                wallet_file: chosenWallet
                            })
                        }).then(r => r.json());
                    });
                    const results = await Promise.all(promises);
                    if (targets.length > 1) {
                        showToast(`[BATCH SYNC] Menjalankan bot pada ${targets.length} HP serentak`, "success");
                    } else {
                        const d = results[0];
                        showToast(d.message, d.status === 'success' ? 'success' : 'error');
                    }
                } catch (e) {
                    showToast("Error start bot: " + e.message, "error");
                }
            });
        }

        // 10. Next Clone — SINKRONISASI BATCH
        const btnNext = card.querySelector('.btn-pad-next');
        if (btnNext) {
            btnNext.addEventListener('click', async () => {
                const targets = getActivePadTargets(serial);
                try {
                    const promises = targets.map(t => {
                        return fetch('/api/bot/next', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ device: t.serial })
                        }).then(r => r.json());
                    });
                    await Promise.all(promises);
                    if (targets.length > 1) {
                        showToast(`[BATCH SYNC] Sinyal lanjut terkirim ke ${targets.length} HP`, "success");
                    } else {
                        showToast("Sinyal lanjut terkirim", "success");
                    }
                } catch (e) {
                    showToast("Error next: " + e.message, "error");
                }
            });
        }

        // 11. Stop / Terminate — SINKRONISASI BATCH
        const btnStop = card.querySelector('.btn-pad-stop');
        if (btnStop) {
            btnStop.addEventListener('click', async () => {
                const targets = getActivePadTargets(serial);
                try {
                    const promises = targets.map(t => {
                        return fetch('/api/bot/stop', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ device: t.serial })
                        }).then(r => r.json());
                    });
                    await Promise.all(promises);
                    if (targets.length > 1) {
                        showToast(`[BATCH SYNC] Seluruh ${targets.length} HP berhasil dihentikan`, "success");
                    } else {
                        showToast(`Bot pada ${serial} dihentikan`, "success");
                    }
                } catch (e) {
                    showToast("Error stop bot: " + e.message, "error");
                }
            });
        }

        // 12. Sleep Delay Input & Spin Arrows (±0.5s per klik)
        card.querySelectorAll('.step-sleep-input').forEach(inp => {
            const handleDelayChange = async (val) => {
                const stepId = inp.getAttribute('data-step-id');
                const numVal = Math.max(0, Math.round(parseFloat(val) * 10) / 10);
                inp.value = numVal;
                
                // Jika Batch Mode ON: sinkronkan nilai input delay ke seluruh kartu PAD
                if (batchAutoState) {
                    document.querySelectorAll(`.step-sleep-input[data-step-id="${stepId}"]`).forEach(el => {
                        el.value = numVal;
                    });
                }

                try {
                    await fetch('/api/step/delay', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ step_id: stepId, delay: numVal, mode: currentMode })
                    });
                    showToast(`Delay Step ${stepId} diubah ke ${numVal}s`, "success");
                } catch (e) {
                    console.error("Gagal update delay:", e);
                }
            };

            inp.addEventListener('change', (e) => {
                handleDelayChange(e.target.value);
            });
            inp.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    inp.blur();
                }
            });
        });

        card.querySelectorAll('.btn-spin-up').forEach(btn => {
            btn.addEventListener('click', () => {
                const stepId = btn.getAttribute('data-step-id');
                const inp = card.querySelector(`.step-sleep-input[data-step-id="${stepId}"]`);
                if (inp) {
                    const cur = parseFloat(inp.value) || 0;
                    const next = Math.round((cur + 0.5) * 10) / 10;
                    inp.value = next;
                    inp.dispatchEvent(new Event('change'));
                }
            });
        });

        card.querySelectorAll('.btn-spin-down').forEach(btn => {
            btn.addEventListener('click', () => {
                const stepId = btn.getAttribute('data-step-id');
                const inp = card.querySelector(`.step-sleep-input[data-step-id="${stepId}"]`);
                if (inp) {
                    const cur = parseFloat(inp.value) || 0;
                    const next = Math.max(0, Math.round((cur - 0.5) * 10) / 10);
                    inp.value = next;
                    inp.dispatchEvent(new Event('change'));
                }
            });
        });
    }

    // Helper: Send ADB Command
    async function sendAdbCommand(serial, command, showNotification = true) {
        try {
            const res = await fetch('/api/device/adb_command', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ device: serial, command: command })
            });
            const d = await res.json();
            if (showNotification) {
                if (d.status === 'success') {
                    showToast(`ADB (${serial}): ${command}`, "success");
                } else {
                    showToast(d.message || "ADB gagal", "error");
                }
            }
        } catch (e) {
            if (showNotification) showToast("Error ADB: " + e.message, "error");
        }
    }

    // =========================================================================
    // 8. STATUS POLLER & SYNC
    // =========================================================================
    async function updateStatus() {
        try {
            const res = await fetch('/api/status');
            if (!res.ok) return;
            const data = await res.json();

            serverConfig = data.config || {};
            if (data.wallets && Array.isArray(data.wallets) && data.wallets.length > 0) {
                availableWallets = data.wallets;
            }
            const uniqueList = data.unique_devices || data.devices || [];
            
            // Check if device list changed
            const currentSerials = uniqueList.map(d => d.serial).join(',');
            const prevSerials = connectedDevices.map(d => d.serial).join(',');
            const devChanged = (currentSerials !== prevSerials);

            connectedDevices = uniqueList;

            // Update Summary Bar
            if (connectedDevicesCountBadge) {
                connectedDevicesCountBadge.textContent = `${uniqueList.length} HP`;
            }
            if (connectedDeviceNamesText) {
                if (uniqueList.length > 0) {
                    connectedDeviceNamesText.textContent = uniqueList.map(d => `${d.model || d.serial} (${d.serial})`).join(', ');
                } else {
                    connectedDeviceNamesText.textContent = 'Tidak Ada Perangkat';
                }
            }
            if (summaryMasterRef) {
                const isWd = (currentMode === 'wd_baru' || currentMode === 'wd_old');
                if (isWd) {
                    const wdAddr = (data.config && data.config.alamat_wd) ? data.config.alamat_wd : (serverConfig.alamat_wd || '');
                    summaryMasterRef.textContent = wdAddr ? (wdAddr.substring(0, 5) + '...' + wdAddr.slice(-4)) : '-';
                    summaryMasterRef.title = `Alamat Stellar Tujuan: ${wdAddr}`;
                    if (summaryMasterRef.previousElementSibling) {
                        summaryMasterRef.previousElementSibling.textContent = '🚀 Stellar:';
                    }
                } else {
                    const refVal = (data.referral && data.referral.master_code) ? data.referral.master_code : ((data.config && data.config.master_referral_code) ? data.config.master_referral_code : 'srTwuLUy');
                    summaryMasterRef.textContent = refVal;
                    summaryMasterRef.title = 'Master Referral Code Relay';
                    if (summaryMasterRef.previousElementSibling) {
                        summaryMasterRef.previousElementSibling.textContent = '🔗 Reff:';
                    }
                }
            }
            if (summaryEmailsCount) {
                summaryEmailsCount.textContent = `${(data.emails && data.emails.total_available) ? data.emails.total_available : 0} Akun`;
            }
            if (summaryLanIp) {
                summaryLanIp.textContent = `http://${data.local_machine_ip || '192.168.1.13'}:${data.server_port || 2000}`;
            }
            const summaryDomainLink = document.getElementById('summaryDomainLink');
            if (summaryDomainLink) {
                const isOnline = Boolean(data.tunnel && data.tunnel.is_online);
                summaryDomainLink.textContent = isOnline ? 'topnodtools.web.id [Online]' : 'topnodtools.web.id';
                summaryDomainLink.style.color = isOnline ? '#00ffa3' : '#38bdf8';
            }

            // Sync Master Screen Off state
            if (data.screen_off_all !== undefined && data.screen_off_all !== isScreenOffMaster) {
                updateScreenOffBadge(data.screen_off_all);
            }

            // Update log filter options
            if (selectLogDeviceFilter) {
                const currentFilter = selectLogDeviceFilter.value;
                const filterOptions = Array.from(selectLogDeviceFilter.options).map(o => o.value);
                const expectedOptions = ['all', ...uniqueList.map(d => d.serial)];
                if (filterOptions.join(',') !== expectedOptions.join(',')) {
                    selectLogDeviceFilter.innerHTML = '<option value="all">Semua Perangkat</option>';
                    uniqueList.forEach(d => {
                        const opt = document.createElement('option');
                        opt.value = d.serial;
                        opt.textContent = `${d.model || d.serial} (${d.serial})`;
                        selectLogDeviceFilter.appendChild(opt);
                    });
                    if (currentFilter && expectedOptions.includes(currentFilter)) {
                        selectLogDeviceFilter.value = currentFilter;
                    }
                }
            }

            // Re-render PADs if devices changed or update live state badges in-place
            if (devChanged) {
                renderDevicePads(connectedDevices);
            } else {
                // In-place status update to preserve UI focus
                uniqueList.forEach(d => {
                    const card = document.getElementById(`padCard_${d.serial}`);
                    if (card) {
                        const stateBadge = card.querySelector('.pad-state-badge');
                        const botState = d.bot_state || 'IDLE';
                        if (stateBadge) {
                            stateBadge.className = `pad-state-badge pad-state-${botState.toLowerCase()}`;
                            stateBadge.textContent = `● ${botState}`;
                        }
                        if (botState === 'RUNNING') {
                            card.classList.add('pad-running');
                            card.classList.remove('pad-waiting');
                        } else if (botState === 'WAITING_NEXT') {
                            card.classList.add('pad-waiting');
                            card.classList.remove('pad-running');
                        } else {
                            card.classList.remove('pad-running', 'pad-waiting');
                        }

                        // Sync run button state
                        const runBtn = card.querySelector('.btn-pad-run');
                        if (runBtn) runBtn.disabled = (botState === 'RUNNING');

                        // Show / hide Next button
                        const footer = card.querySelector('.pad-footer-actions');
                        let nextBtn = card.querySelector('.btn-pad-next');
                        if (botState === 'WAITING_NEXT') {
                            if (!nextBtn && footer) {
                                nextBtn = document.createElement('button');
                                nextBtn.type = 'button';
                                nextBtn.className = 'btn-pad-next active-prompt';
                                nextBtn.setAttribute('data-serial', d.serial);
                                nextBtn.innerHTML = `<span>⏩</span> Lanjut Clone #${d.next_clone || '?'} (Enter)`;
                                nextBtn.addEventListener('click', async () => {
                                    await fetch('/api/bot/next', {
                                        method: 'POST',
                                        headers: {'Content-Type': 'application/json'},
                                        body: JSON.stringify({ device: d.serial })
                                    });
                                });
                                footer.insertBefore(nextBtn, footer.querySelector('.btn-pad-stop'));
                            }
                        } else if (nextBtn) {
                            nextBtn.remove();
                        }
                    }
                });
            }

        } catch (e) {
            console.error("Status poller error:", e);
        }
    }

    // =========================================================================
    // 9. SSE REAL-TIME TERMINAL LOGGING
    let logScrollPending = false;
    let sseReconnectTimer = null;

    function connectSseLogs() {
        if (logEventSource) {
            logEventSource.close();
            logEventSource = null;
        }
        if (sseReconnectTimer) {
            clearTimeout(sseReconnectTimer);
            sseReconnectTimer = null;
        }

        const filterVal = selectLogDeviceFilter ? selectLogDeviceFilter.value : 'all';
        const url = `/api/logs?device=${encodeURIComponent(filterVal)}`;
        logEventSource = new EventSource(url);

        logEventSource.onmessage = (event) => {
            try {
                const item = JSON.parse(event.data);
                appendLogLine(item);
            } catch (err) {
                appendLogLine({ line: event.data });
            }
        };

        logEventSource.onerror = () => {
            if (logEventSource) {
                logEventSource.close();
                logEventSource = null;
            }
            if (!sseReconnectTimer) {
                sseReconnectTimer = setTimeout(() => {
                    sseReconnectTimer = null;
                    connectSseLogs();
                }, 5000);
            }
        };
    }

    function appendLogLine(item) {
        if (!terminalOutput) return;
        const line = item.line || '';

        // Hilangkan pesan awal
        const sysLog = terminalOutput.querySelector('.log-system');
        if (sysLog && sysLog.textContent && sysLog.textContent.indexOf('Menghubungkan ke server') !== -1) {
            terminalOutput.innerHTML = '';
        }

        const span = document.createElement('span');
        span.className = 'log-line';

        // Styling warna berdasarkan konten log
        if (line.includes('[SCREEN OFF]') || line.includes('[SCREEN ON]')) {
            span.style.color = '#38bdf8';
            span.style.fontWeight = '700';
        } else if (line.includes('[MANUAL STEP]') || line.includes('[ACTION]')) {
            span.style.color = '#00ffa3';
            span.style.fontWeight = '700';
        } else if (line.includes('[PROMPT]') || line.includes('WAITING_NEXT') || line.includes('DIPAUSE')) {
            span.style.color = '#fbbf24';
            span.style.fontWeight = '700';
        } else if (line.includes('[ERROR]') || line.includes('Gagal') || line.includes('Exit Code')) {
            span.style.color = '#f43f5e';
            span.style.fontWeight = '700';
        } else if (line.includes('[IMAP SUCCESS]') || line.includes('[REFERRAL]')) {
            span.style.color = '#a855f7';
            span.style.fontWeight = '700';
        } else if (line.includes('MEMPROSES')) {
            span.style.color = '#38bdf8';
            span.style.fontWeight = '800';
        }

        span.textContent = line + '\n';
        terminalOutput.appendChild(span);

        // Batasi baris terminal maks 200 agar performa browser sangat ringan di PC RAM 4GB
        while (terminalOutput.childNodes.length > 200) {
            terminalOutput.removeChild(terminalOutput.firstChild);
        }

        // Throttle scrolling via requestAnimationFrame agar tidak menyebabkan DOM reflow thrashing
        if (autoScroll && terminalContainer && !logScrollPending) {
            logScrollPending = true;
            requestAnimationFrame(() => {
                terminalContainer.scrollTop = terminalContainer.scrollHeight;
                logScrollPending = false;
            });
        }
    }

    if (selectLogDeviceFilter) {
        selectLogDeviceFilter.addEventListener('change', () => {
            if (terminalOutput) terminalOutput.innerHTML = '';
            connectSseLogs();
        });
    }

    if (checkAutoScroll) {
        checkAutoScroll.addEventListener('change', (e) => {
            autoScroll = e.target.checked;
        });
    }

    if (btnClearLogs) {
        btnClearLogs.addEventListener('click', async () => {
            if (terminalOutput) terminalOutput.innerHTML = '';
            await fetch('/api/logs/clear', { method: 'POST' });
            showToast("Log terminal dibersihkan", "success");
        });
    }

    // =========================================================================
    // 10. GLOBAL KEYBOARD SHORTCUTS (ENTER, P, Q)
    // =========================================================================
    document.addEventListener('keydown', (e) => {
        // Jangan tangkap shortcut jika user sedang mengetik di input text
        const tag = (e.target.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

        if (e.key === 'Enter') {
            e.preventDefault();
            if (btnNextAllDevices) btnNextAllDevices.click();
        } else if (e.key === 'p' || e.key === 'P') {
            fetch('/api/bot/pause', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ device: 'all' })
            });
            showToast("Sinyal PAUSE dikirim", "warning");
        } else if (e.key === 'q' || e.key === 'Q') {
            if (btnStopAllDevices) btnStopAllDevices.click();
        }
    });

    // =========================================================================
    // 11. INITIALIZATION & INTERVAL
    // =========================================================================
    Promise.all([loadMacroSteps(currentMode), loadWallets()]).then(() => {
        updateStatus();
    });

    connectSseLogs();
    setInterval(updateStatus, 1500);
});
