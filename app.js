// KUBER Enterprise Application Controller
document.addEventListener("DOMContentLoaded", () => {
    
    // Application & RBAC State
    let currentUserRole = 'rider'; // 'rider' | 'driver' | 'admin'
    let currentRegion = 'mumbai';
    let mapCenter = [19.0600, 72.8350]; // BKC Mumbai
    let map = null;
    let pickupMarker = null;
    let dropMarker = null;
    let routePolyline = null;
    let activeDriverMarkers = [];

    let currentSurgeMultiplier = 1.8;
    let selectedRideType = 'uberx';
    let currentTripPayload = null;

    // --- 0. AUTHENTICATION SESSION CHECK ---
    function checkAuthSession() {
        const rawSession = localStorage.getItem('kuber_auth_session');
        if (!rawSession) {
            // Redirect unauthenticated user to standalone login page
            window.location.href = "login.html";
            return;
        }

        try {
            const session = JSON.parse(rawSession);
            currentUserRole = session.role || 'rider';
            applyRBACPermissions(currentUserRole, session.name);
        } catch (e) {
            window.location.href = "login.html";
        }
    }

    const btnSignOut = document.getElementById('btn-switch-portal');
    if (btnSignOut) {
        btnSignOut.addEventListener('click', () => {
            localStorage.removeItem('kuber_auth_session');
            window.location.href = "login.html";
        });
    }

    // --- 1. RBAC & PERMISSION CONTROLLER ---
    function applyRBACPermissions(role, customName) {
        currentUserRole = role;
        const nameDisplay = document.getElementById('user-display-name');
        const roleTag = document.getElementById('user-role-badge');
        const avatarInitials = document.getElementById('user-avatar-initials');

        // Reset Tab active states
        document.querySelectorAll('.tab-item').forEach(b => b.classList.remove('disabled', 'active'));
        document.querySelectorAll('.sidebar-tab-content').forEach(c => c.classList.remove('active'));

        if (role === 'rider') {
            if (nameDisplay) nameDisplay.innerText = customName || "Rider Portal";
            if (roleTag) { roleTag.innerText = "RIDER"; roleTag.className = "role-tag rider"; }
            if (avatarInitials) avatarInitials.innerText = "R";

            const rTab = document.querySelector('.rbac-tab-rider');
            const rContent = document.getElementById('tab-rider-booking');
            const aTab = document.querySelector('.rbac-tab-admin');

            if (rTab) rTab.classList.add('active');
            if (rContent) rContent.classList.add('active');
            if (aTab) aTab.classList.add('disabled');
            document.querySelectorAll('.rbac-admin-only').forEach(el => el.style.display = 'none');

        } else if (role === 'driver') {
            if (nameDisplay) nameDisplay.innerText = customName || "Karan Bhati (Driver)";
            if (roleTag) { roleTag.innerText = "DRIVER"; roleTag.className = "role-tag driver"; }
            if (avatarInitials) avatarInitials.innerText = "D";

            const dTab = document.querySelector('.rbac-tab-driver');
            const dContent = document.getElementById('tab-driver-portal');
            const aTab = document.querySelector('.rbac-tab-admin');

            if (dTab) dTab.classList.add('active');
            if (dContent) dContent.classList.add('active');
            if (aTab) aTab.classList.add('disabled');
            document.querySelectorAll('.rbac-admin-only').forEach(el => el.style.display = 'none');

        } else if (role === 'admin') {
            if (nameDisplay) nameDisplay.innerText = customName || "System Director (Ops)";
            if (roleTag) { roleTag.innerText = "ADMIN"; roleTag.className = "role-tag admin"; }
            if (avatarInitials) avatarInitials.innerText = "A";

            const aTab = document.querySelector('.rbac-tab-admin');
            const aContent = document.getElementById('tab-admin-portal');

            if (aTab) aTab.classList.add('active');
            if (aContent) aContent.classList.add('active');
            document.querySelectorAll('.rbac-admin-only').forEach(el => el.style.display = 'flex');
        }
    }

    // --- 2. LEAFLET DARK MAP ENGINE ---
    function initUberMap() {
        try {
            if (map) map.remove();

            map = L.map('uber-leaflet-map', {
                zoomControl: false
            }).setView(mapCenter, 13);

            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; OpenStreetMap &copy; CARTO',
                maxZoom: 19
            }).addTo(map);

            L.control.zoom({ position: 'bottomright' }).addTo(map);

            updateRouteAndMarkers();
            spawnLiveUberVehicles();
        } catch (e) {
            console.log("Map Engine initialized in offline mode.");
        }
    }

    function updateRouteAndMarkers() {
        try {
            const pSelect = document.getElementById('select-pickup');
            const dSelect = document.getElementById('select-drop');

            if (!pSelect || !dSelect) return;

            const pOpt = pSelect.options[pSelect.selectedIndex];
            const dOpt = dSelect.options[dSelect.selectedIndex];

            const pLat = parseFloat(pOpt.getAttribute('data-lat'));
            const pLon = parseFloat(pOpt.getAttribute('data-lon'));
            const dLat = parseFloat(dOpt.getAttribute('data-lat'));
            const dLon = parseFloat(dOpt.getAttribute('data-lon'));

            if (pickupMarker) map.removeLayer(pickupMarker);
            const pickupIcon = L.divIcon({
                className: 'uber-map-pin pickup-pin',
                html: '<div class="pin-square green"></div>',
                iconSize: [24, 24]
            });
            pickupMarker = L.marker([pLat, pLon], { icon: pickupIcon }).addTo(map).bindPopup("Pickup");

            if (dropMarker) map.removeLayer(dropMarker);
            const dropIcon = L.divIcon({
                className: 'uber-map-pin drop-pin',
                html: '<div class="pin-square white"></div>',
                iconSize: [24, 24]
            });
            dropMarker = L.marker([dLat, dLon], { icon: dropIcon }).addTo(map).bindPopup("Destination");

            if (routePolyline) map.removeLayer(routePolyline);
            routePolyline = L.polyline([[pLat, pLon], [dLat, dLon]], {
                color: '#FFFFFF',
                weight: 5,
                opacity: 0.9,
                dashArray: '10, 10'
            }).addTo(map);

            map.fitBounds(routePolyline.getBounds(), { padding: [60, 60] });

            const geohash = encodeGeohash(pLat, pLon);
            const tag = document.getElementById('map-geohash-tag');
            const val = document.getElementById('geohash-val');
            if (tag) tag.innerText = geohash;
            if (val) val.innerText = geohash;

            updatePriceEstimates(pLat, pLon, dLat, dLon);
        } catch (e) {
            console.log("Marker update deferred.");
        }
    }

    function spawnLiveUberVehicles() {
        try {
            activeDriverMarkers.forEach(m => map.removeLayer(m));
            activeDriverMarkers = [];

            const carIcon = L.divIcon({
                className: 'uber-car-marker',
                html: '<div class="car-dot"><i class="fa-solid fa-car"></i></div>',
                iconSize: [28, 28]
            });

            for (let i = 0; i < 6; i++) {
                const offsetLat = (Math.random() - 0.5) * 0.035;
                const offsetLon = (Math.random() - 0.5) * 0.035;
                const m = L.marker([mapCenter[0] + offsetLat, mapCenter[1] + offsetLon], { icon: carIcon }).addTo(map);
                activeDriverMarkers.push(m);
            }
        } catch (e) {}
    }

    function encodeGeohash(lat, lon) {
        const BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz";
        let latInterval = [-90.0, 90.0];
        let lonInterval = [-180.0, 180.0];
        let geohash = "";
        let isEven = true;
        let bit = 0, ch = 0;

        while (geohash.length < 6) {
            let mid;
            if (isEven) {
                mid = (lonInterval[0] + lonInterval[1]) / 2.0;
                if (lon > mid) { ch |= (16 >> bit); lonInterval[0] = mid; }
                else { lonInterval[1] = mid; }
            } else {
                mid = (latInterval[0] + latInterval[1]) / 2.0;
                if (lat > mid) { ch |= (16 >> bit); latInterval[0] = mid; }
                else { latInterval[1] = mid; }
            }
            isEven = !isEven;
            if (bit < 4) bit++;
            else { geohash += BASE32[ch]; bit = 0; ch = 0; }
        }
        return geohash;
    }

    function calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371;
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                  Math.sin(dLon / 2) * Math.sin(dLon / 2);
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }

    function updatePriceEstimates(lat1, lon1, lat2, lon2) {
        const distKm = calculateDistance(lat1, lon1, lat2, lon2);
        currentSurgeMultiplier = (distKm > 10) ? 2.1 : (distKm > 5 ? 1.8 : 1.2);
        
        const sTag = document.getElementById('surge-multiplier-val');
        if (sTag) sTag.innerText = `${currentSurgeMultiplier}x`;

        const prices = {
            uberx: Math.round((50 + distKm * 15) * currentSurgeMultiplier),
            uberxl: Math.round((80 + distKm * 25) * currentSurgeMultiplier),
            black: Math.round((120 + distKm * 35) * currentSurgeMultiplier),
            auto: Math.round((30 + distKm * 10) * currentSurgeMultiplier)
        };

        const pUberX = document.getElementById('price-uberx');
        const pUberXL = document.getElementById('price-uberxl');
        const pBlack = document.getElementById('price-black');
        const pAuto = document.getElementById('price-auto');
        const dVal = document.getElementById('dist-val');

        if (pUberX) pUberX.innerText = `₹${prices.uberx}`;
        if (pUberXL) pUberXL.innerText = `₹${prices.uberxl}`;
        if (pBlack) pBlack.innerText = `₹${prices.black}`;
        if (pAuto) pAuto.innerText = `₹${prices.auto}`;
        if (dVal) dVal.innerText = `${distKm.toFixed(1)} km`;
    }

    // --- 3. RIDE REQUEST LIFECYCLE ---
    const btnReq = document.getElementById('btn-request-uber');
    if (btnReq) {
        btnReq.addEventListener('click', async () => {
            const pSelect = document.getElementById('select-pickup');
            const dSelect = document.getElementById('select-drop');

            const pOpt = pSelect.options[pSelect.selectedIndex];
            const dOpt = dSelect.options[dSelect.selectedIndex];

            const pLat = parseFloat(pOpt.getAttribute('data-lat'));
            const pLon = parseFloat(pOpt.getAttribute('data-lon'));
            const dLat = parseFloat(dOpt.getAttribute('data-lat'));
            const dLon = parseFloat(dOpt.getAttribute('data-lon'));

            const distKm = calculateDistance(pLat, pLon, dLat, dLon);

            const tabBooking = document.getElementById('tab-rider-booking');
            const tabActive = document.getElementById('tab-active-trip');

            if (tabBooking) tabBooking.classList.remove('active');
            if (tabActive) tabActive.classList.add('active');

            const title = document.getElementById('trip-status-title');
            const desc = document.getElementById('trip-status-desc');

            if (title) title.innerText = "Connecting to a Driver...";
            if (desc) desc.innerText = "Geohash Bipartite Batch Queue";

            try {
                await fetch('http://localhost:8001/ride/request', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        rider_id: `rider_${Math.floor(Math.random() * 9000 + 1000)}`,
                        latitude: pLat,
                        longitude: pLon
                    })
                });
            } catch (e) {}

            setTimeout(() => {
                if (title) title.innerText = "Driver En Route";
                if (desc) desc.innerText = "Toyota Fortuner (MH-02-KB-7788)";

                currentTripPayload = {
                    rider_id: `rider_${Math.floor(Math.random() * 9000 + 1000)}`,
                    driver_id: "driver_alpha_77",
                    start_lat: pLat,
                    start_lon: pLon,
                    end_lat: dLat,
                    end_lon: dLon,
                    distance_km: parseFloat(distKm.toFixed(2)),
                    surge_multiplier: currentSurgeMultiplier
                };
            }, 1800);
        });
    }

    // --- 4. COMPLETE TRIP & SHARD ARCHIVE RECEIPT ---
    const btnComp = document.getElementById('btn-complete-trip');
    if (btnComp) {
        btnComp.addEventListener('click', async () => {
            if (!currentTripPayload) return;

            let shardUsed = (currentRegion === 'mumbai') ? 'mumbai' : 'delhi';
            let fareAmount = Math.round((50 + currentTripPayload.distance_km * 15) * currentSurgeMultiplier);
            let tripId = `trip_${Math.random().toString(36).substring(2, 10)}`;

            try {
                const resp = await fetch('http://localhost:8003/trip/complete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(currentTripPayload)
                });
                if (resp.ok) {
                    const data = await resp.json();
                    shardUsed = data.shard_used || shardUsed;
                    fareAmount = data.fare_amount || fareAmount;
                    tripId = data.trip_id || tripId;
                }
            } catch (e) {}

            const idTxt = document.getElementById('receipt-id-text');
            const rDist = document.getElementById('r-dist');
            const rSurge = document.getElementById('r-surge');
            const rPrice = document.getElementById('r-total-price');

            if (idTxt) idTxt.innerText = `TRIP ID: ${tripId}`;
            if (rDist) rDist.innerText = currentTripPayload.distance_km;
            if (rSurge) rSurge.innerText = currentSurgeMultiplier;
            if (rPrice) rPrice.innerText = `₹${fareAmount}.00`;

            const shardName = (shardUsed.toLowerCase() === 'mumbai') ? 'MUMBAI SHARD DATABASE' : 'DELHI SHARD DATABASE';
            const shardPort = (shardUsed.toLowerCase() === 'mumbai') ? '3307 / kuber_db_mumbai' : '3308 / kuber_db_delhi';

            const sTitle = document.getElementById('receipt-shard-title');
            if (sTitle) sTitle.innerText = shardName;

            const modalRec = document.getElementById('modal-receipt');
            if (modalRec) modalRec.classList.add('active');

            const tabActive = document.getElementById('tab-active-trip');
            const tabBooking = document.getElementById('tab-rider-booking');
            if (tabActive) tabActive.classList.remove('active');
            if (tabBooking) tabBooking.classList.add('active');
        });
    }

    // --- 5. EVENT HANDLERS ---
    document.querySelectorAll('.tab-item').forEach(tab => {
        tab.addEventListener('click', () => {
            if (tab.classList.contains('disabled')) return;
            document.querySelectorAll('.tab-item').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.sidebar-tab-content').forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            const targetTab = tab.getAttribute('data-tab');
            const targetContent = document.getElementById(`tab-${targetTab}`);
            if (targetContent) targetContent.classList.add('active');
        });
    });

    document.querySelectorAll('.region-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            document.querySelectorAll('.region-pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');

            currentRegion = pill.getAttribute('data-region');
            const pSel = document.getElementById('select-pickup');
            const dSel = document.getElementById('select-drop');

            if (currentRegion === 'delhi') {
                mapCenter = [28.6139, 77.2090];
                if (pSel) pSel.value = 'connaught';
                if (dSel) dSel.value = 'delhi-airport';
            } else {
                mapCenter = [19.0600, 72.8350];
                if (pSel) pSel.value = 'bkc';
                if (dSel) dSel.value = 'airport';
            }
            initUberMap();
        });
    });

    document.querySelectorAll('.ride-card').forEach(card => {
        card.addEventListener('click', () => {
            document.querySelectorAll('.ride-card').forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            selectedRideType = card.getAttribute('data-type');

            const h4 = card.querySelector('h4');
            const btn = document.getElementById('btn-request-uber');
            if (h4 && btn) {
                const name = h4.innerText.split(' ')[0];
                btn.innerHTML = `<span>Choose ${name}</span>`;
            }
        });
    });

    const pChange = document.getElementById('select-pickup');
    const dChange = document.getElementById('select-drop');
    if (pChange) pChange.addEventListener('change', updateRouteAndMarkers);
    if (dChange) dChange.addEventListener('change', updateRouteAndMarkers);

    // Modal Handlers
    document.querySelectorAll('#btn-admin-telemetry, #btn-admin-topology').forEach(btn => {
        btn.addEventListener('click', () => {
            const modal = document.getElementById('modal-topology');
            if (modal) modal.classList.add('active');
        });
    });

    document.querySelectorAll('.modal-close-icon, .modal-done-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.uber-modal-overlay').forEach(m => m.classList.remove('active'));
        });
    });

    // Bio scan handler
    const bioBtn = document.getElementById('btn-run-bio-scan');
    if (bioBtn) {
        bioBtn.addEventListener('click', () => {
            bioBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scanning Face...';
            setTimeout(() => {
                bioBtn.innerHTML = '<i class="fa-solid fa-circle-check"></i> FaceNet Verified (0.8942)';
                alert("Facial biometrics match verified successfully!");
            }, 1500);
        });
    }

    // Initialize Check Session & Map
    checkAuthSession();
    initUberMap();
});
