// GPS + Leaflet map logic for report.html
let map = null;
let marker = null;

document.addEventListener('DOMContentLoaded', () => {
    const gpsBtn = document.getElementById('gps-btn');
    const locationInput = document.getElementById('location_text');
    const latInput = document.getElementById('latitude');
    const lngInput = document.getElementById('longitude');
    const mapSection = document.getElementById('map-section');
    const mapEl = document.getElementById('leaflet-map');
    const gpsSpinner = document.getElementById('gps-spinner');
    const gpsLabel = document.getElementById('gps-label');

    if (!gpsBtn) return;

    gpsBtn.addEventListener('click', () => {
        if (!navigator.geolocation) {
            alert('Geolocation is not supported by your browser.');
            return;
        }

        // Show loading spinner
        gpsSpinner.classList.remove('hidden');
        gpsLabel.classList.add('hidden');
        gpsBtn.disabled = true;

        navigator.geolocation.getCurrentPosition(
            async (pos) => {
                const lat = pos.coords.latitude;
                const lng = pos.coords.longitude;

                // Fill hidden inputs
                latInput.value = lat;
                lngInput.value = lng;

                // Reverse Geocode
                try {
                    const res = await fetch(`/reverse-geocode?lat=${lat}&lng=${lng}`);
                    const data = await res.json();
                    locationInput.value = data.address || `${lat}, ${lng}`;
                } catch {
                    locationInput.value = `${lat}, ${lng}`;
                }

                // Show map
                mapSection.classList.remove('hidden');
                if (!map) {
                    map = L.map(mapEl).setView([lat, lng], 16);
                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                        attribution: '© OpenStreetMap contributors'
                    }).addTo(map);
                } else {
                    map.setView([lat, lng], 16);
                }

                if (marker) marker.remove();
                marker = L.marker([lat, lng], { draggable: true }).addTo(map)
                    .bindPopup('📍 Drag to adjust the position').openPopup();

                // Update inputs when marker is dragged
                marker.on('dragend', async (e) => {
                    const newPos = e.target.getLatLng();
                    latInput.value = newPos.lat;
                    lngInput.value = newPos.lng;
                    try {
                        const res = await fetch(`/reverse-geocode?lat=${newPos.lat}&lng=${newPos.lng}`);
                        const data = await res.json();
                        locationInput.value = data.address || `${newPos.lat}, ${newPos.lng}`;
                    } catch {
                        locationInput.value = `${newPos.lat}, ${newPos.lng}`;
                    }
                });

                // Reset button
                gpsSpinner.classList.add('hidden');
                gpsLabel.classList.remove('hidden');
                gpsBtn.disabled = false;
                gpsBtn.classList.add('bg-green-600');
                gpsBtn.classList.remove('bg-accent');
            },
            (err) => {
                alert('Could not get your location. Please enter it manually.');
                gpsSpinner.classList.add('hidden');
                gpsLabel.classList.remove('hidden');
                gpsBtn.disabled = false;
            },
            { timeout: 10000 }
        );
    });
});
