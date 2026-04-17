/**
 * Antigravity — Dashboard Logic
 * Handles API communication with the Spring Boot backend.
 */

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('predictionForm');
    const predictBtn = document.getElementById('predictBtn');
    const loader = document.getElementById('loader');
    const resultContent = document.getElementById('resultContent');

    // UI Elements
    const etaValue = document.getElementById('etaMinutes');
    const adjustedEta = document.getElementById('adjustedEta');
    const bufferFactor = document.getElementById('bufferFactor');
    const disconnectTime = document.getElementById('disconnectTime');
    const statusLabel = document.getElementById('statusLabel');
    const confidenceBadge = document.getElementById('confidenceBadge');
    const historyBody = document.getElementById('historyBody');

    let history = []; // Array to store recent predictions
        e.preventDefault();

        // Prepare data
        const data = {
            stationId: document.getElementById('stationId').value,
            connectorId: 1, // Default for demo
            currentSoc: parseFloat(document.getElementById('currentSoc').value),
            chargerMaxKw: parseFloat(document.getElementById('chargerMaxKw').value),
            batteryCapacityKwh: parseFloat(document.getElementById('batteryCapacityKwh').value),
            ambientTempC: parseFloat(document.getElementById('ambientTempC').value),
            timestamp: new Date().toISOString()
        };

        // Show loading state
        setLoading(true);

        try {
            const response = await fetch('/api/telemetry/heartbeat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.message || 'Failed to get prediction');
            }

            const result = await response.json();
            updateUI(result, data);
            addToHistory(result, data);

        } catch (error) {
            console.error('Error:', error);
            alert('Error connecting to service: ' + error.message);
        } finally {
            setLoading(false);
        }
    });

    function setLoading(isLoading) {
        if (isLoading) {
            loader.style.display = 'block';
            resultContent.style.opacity = '0.3';
            predictBtn.disabled = true;
            predictBtn.textContent = 'Analyzing Patterns...';
        } else {
            loader.style.display = 'none';
            resultContent.style.opacity = '1';
            predictBtn.disabled = false;
            predictBtn.textContent = 'Predict Disconnect ETA';
        }
    }

    function updateUI(data, input) {
        // Animate numbers for extra premium feel
        animateValue(etaValue, 0, data.rawEtaMinutes, 1000);
        
        adjustedEta.textContent = `${data.adjustedEtaMinutes.toFixed(1)} min`;
        bufferFactor.textContent = `${data.bufferFactor.toFixed(2)}x`;
        
        // Format time
        const time = new Date(data.predictedDisconnectTime);
        disconnectTime.textContent = time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        statusLabel.textContent = data.status;
        confidenceBadge.textContent = `${data.confidence} Confidence`;

        // Update colors based on status
        if (data.status === 'NEAR_FULL' || data.status === 'IDLE') {
            etaValue.style.color = '#10b981'; // Green
        } else {
            etaValue.style.color = '#8b5cf6'; // Purple
        }
    }

    function addToHistory(data, input) {
        // Keep only top 5 recent
        history.unshift({ ...data, ...input });
        if (history.length > 5) history.pop();

        renderHistory();
    }

    function renderHistory() {
        historyBody.innerHTML = history.map(item => `
            <tr>
                <td style="font-weight: 600;">${item.stationId}</td>
                <td>${item.currentSoc}%</td>
                <td>${item.rawEtaMinutes.toFixed(1)}m</td>
                <td style="color: var(--accent-secondary); font-weight: 600;">${item.adjustedEtaMinutes.toFixed(1)}m</td>
                <td><span class="confidence-badge" style="font-size: 0.65rem;">${item.confidence}</span></td>
                <td><span style="color: ${item.status === 'CHARGING' ? '#8b5cf6' : '#10b981'}">${item.status}</span></td>
            </tr>
        `).join('');
    }

    function animateValue(obj, start, end, duration) {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            obj.innerHTML = (progress * (end - start) + start).toFixed(1);
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    }
});
