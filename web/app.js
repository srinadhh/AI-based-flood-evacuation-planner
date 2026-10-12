// Adyar Flood Evacuation AI - Web Application Logic

let map;
let originMarker;
let shelterMarkers = [];
let floodedLayerGroup;
let routePolyline;

// App State
const state = {
  mode: 'driving',
  origin: { lat: 13.0185, lon: 80.2410 }, // Kotturpuram
  departureMinutes: 0,
  shelters: [],
};

document.addEventListener('DOMContentLoaded', () => {
  initMap();
  loadShelters();
  loadFloodedSegments();
  setupEventListeners();
  requestRoute();
});

// 1. Initialize Map
function initMap() {
  map = L.map('map', {
    zoomControl: false,
  }).setView([state.origin.lat, state.origin.lon], 14);

  L.control.zoom({ position: 'bottomright' }).addTo(map);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  floodedLayerGroup = L.layerGroup().addTo(map);

  // Custom Origin Marker Icon
  const originIcon = L.divIcon({
    className: 'custom-origin-icon',
    html: `<div style="background:#10b981;width:18px;height:18px;border-radius:50%;border:3px solid #ffffff;box-shadow:0 0 10px rgba(16,185,129,0.7);"></div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });

  originMarker = L.marker([state.origin.lat, state.origin.lon], {
    icon: originIcon,
    draggable: true,
  }).addTo(map);

  originMarker.bindTooltip('Evacuation Origin (Drag or click map to move)', { permanent: false, direction: 'top' });

  originMarker.on('dragend', (e) => {
    const latlng = e.target.getLatLng();
    state.origin.lat = latlng.lat;
    state.origin.lon = latlng.lng;
    requestRoute();
  });

  // Map click to reposition origin
  map.on('click', (e) => {
    state.origin.lat = e.latlng.lat;
    state.origin.lon = e.latlng.lng;
    originMarker.setLatLng(e.latlng);
    requestRoute();
  });
}

// 2. Load Shelters
async function loadShelters() {
  try {
    const res = await fetch('/api/shelters');
    state.shelters = await res.json();

    const shelterIcon = L.divIcon({
      className: 'custom-shelter-icon',
      html: `<div style="background:#2563eb;color:#ffffff;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid #ffffff;font-size:11px;font-weight:bold;box-shadow:0 2px 8px rgba(37,99,235,0.5);">S</div>`,
      iconSize: [28, 28],
      iconAnchor: [14, 14],
    });

    state.shelters.forEach(s => {
      const marker = L.marker([s.lat, s.lon], { icon: shelterIcon }).addTo(map);
      marker.bindPopup(`<strong>${s.name}</strong><br>Designated Relief Facility`);
      marker.bindTooltip(s.name, { direction: 'top', offset: [0, -10] });
      shelterMarkers.push(marker);
    });
  } catch (err) {
    console.error('Failed to load shelters:', err);
  }
}

// 3. Load Flooded Road Segments
async function loadFloodedSegments() {
  try {
    const res = await fetch('/api/flooded_segments');
    const segments = await res.json();
    floodedLayerGroup.clearLayers();

    segments.forEach(seg => {
      const line = L.polyline([seg.p1, seg.p2], {
        color: '#ef4444',
        weight: 5,
        opacity: 0.85,
        dashArray: '4, 6',
      });
      line.bindTooltip(`⚠️ Flooded Segment: ${seg.depth_m.toFixed(2)}m Peak Depth`, { direction: 'top' });
      floodedLayerGroup.addLayer(line);
    });
  } catch (err) {
    console.error('Failed to load flooded segments:', err);
  }
}

// 4. Request Route Calculation
async function requestRoute() {
  const statusEl = document.getElementById('resStatus');
  const distEl = document.getElementById('resDist');
  const timeEl = document.getElementById('resTime');
  const shelterEl = document.getElementById('resShelter');

  statusEl.textContent = 'ROUTING...';
  statusEl.className = 'metric-value';

  try {
    const res = await fetch('/api/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mode: state.mode,
        origin_lat: state.origin.lat,
        origin_lon: state.origin.lon,
        departure_time_seconds: state.departureMinutes * 60,
      }),
    });

    const data = await res.json();

    if (data.status === 'SUCCESS') {
      statusEl.textContent = 'SAFE PASSAGE';
      statusEl.className = 'metric-value badge-safe';
      distEl.textContent = `${(data.total_distance_meters / 1000).toFixed(2)} km`;
      timeEl.textContent = `${data.total_time_minutes.toFixed(1)} min`;
      shelterEl.textContent = data.destination_name;

      // Draw Path
      if (routePolyline) map.removeLayer(routePolyline);

      routePolyline = L.polyline(data.path_coords, {
        color: state.mode === 'walking' ? '#06b6d4' : '#2563eb',
        weight: 6,
        opacity: 0.9,
      }).addTo(map);

      map.fitBounds(routePolyline.getBounds(), { padding: [40, 40] });
    } else {
      statusEl.textContent = 'NO SAFE ROUTE';
      statusEl.className = 'metric-value badge-danger';
      distEl.textContent = '—';
      timeEl.textContent = '—';
      shelterEl.textContent = 'Cut Off by Flood';
      if (routePolyline) map.removeLayer(routePolyline);

      appendAssistantMessage(
        `⚠️ **Evacuation Warning**: No safe route found from the selected point at t = ${state.departureMinutes} min.\n` +
        `All accessible corridors exceed the ${state.mode === 'walking' ? '0.15m walking' : '0.20m vehicle'} safe depth threshold.`
      );
    }
  } catch (err) {
    console.error('Route calculation error:', err);
    statusEl.textContent = 'ERROR';
  }
}

// 5. Setup User Event Handlers
function setupEventListeners() {
  // Mode selection buttons
  const btnDriving = document.getElementById('btnDriving');
  const btnWalking = document.getElementById('btnWalking');

  btnDriving.addEventListener('click', () => {
    state.mode = 'driving';
    btnDriving.classList.add('active');
    btnWalking.classList.remove('active');
    requestRoute();
  });

  btnWalking.addEventListener('click', () => {
    state.mode = 'walking';
    btnWalking.classList.add('active');
    btnDriving.classList.remove('active');
    requestRoute();
  });

  // Departure Time Slider
  const timeSlider = document.getElementById('timeSlider');
  const timeDisplay = document.getElementById('timeDisplay');
  timeSlider.addEventListener('input', (e) => {
    state.departureMinutes = parseInt(e.target.value, 10);
    timeDisplay.textContent = `t = ${state.departureMinutes} min`;
  });
  timeSlider.addEventListener('change', () => {
    requestRoute();
  });

  // Replan Button
  document.getElementById('btnReplan').addEventListener('click', () => {
    requestRoute();
  });

  // Chat Form Submission
  const chatForm = document.getElementById('chatForm');
  const chatInput = document.getElementById('chatInput');

  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = chatInput.value.trim();
    if (!query) return;

    appendUserMessage(query);
    chatInput.value = '';

    await handleChatQuery(query);
  });

  // Suggestion Chips
  document.querySelectorAll('.chip-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const prompt = btn.dataset.prompt;
      appendUserMessage(prompt);
      handleChatQuery(prompt);
    });
  });
}

// 6. Handle Chat with Backend
async function handleChatQuery(message) {
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();

    appendAssistantMessage(data.reply);

    if (data.action) {
      if (data.action.type === 'plan_route') {
        if (data.action.mode) {
          state.mode = data.action.mode;
          document.getElementById('btnDriving').classList.toggle('active', state.mode === 'driving');
          document.getElementById('btnWalking').classList.toggle('active', state.mode === 'walking');
        }
        requestRoute();
      }
    }
  } catch (err) {
    console.error('Chat error:', err);
    appendAssistantMessage('Sorry, I encountered an error communicating with the evacuation backend.');
  }
}

// 7. Message Appenders
function appendUserMessage(text) {
  const messagesContainer = document.getElementById('chatMessages');
  const row = document.createElement('div');
  row.className = 'message-row user-row';
  row.innerHTML = `<div class="user-bubble">${escapeHtml(text)}</div>`;
  messagesContainer.appendChild(row);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function appendAssistantMessage(text) {
  const messagesContainer = document.getElementById('chatMessages');
  const row = document.createElement('div');
  row.className = 'message-row assistant-row';

  // Format simple markdown into HTML
  let formatted = text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code style="background:#cbd5e1;padding:2px 6px;border-radius:4px;font-family:monospace;font-size:12px;">$1</code>')
    .replace(/\n- /g, '<br>• ')
    .replace(/\n\n/g, '<br><br>')
    .replace(/\n/g, '<br>');

  row.innerHTML = `<div class="message-bubble assistant-bubble">${formatted}</div>`;
  messagesContainer.appendChild(row);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
