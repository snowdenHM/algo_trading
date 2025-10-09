// Main JavaScript functionality for AlgoTrading Platform

// Global variables
let connectionStatus = false;
let performanceChart = null;

// API Base URL
const API_BASE = '/api/v1';

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setInterval(updateConnectionStatus, 10000); // Check connection every 10 seconds
    setInterval(updateDashboardData, 30000); // Update dashboard every 30 seconds
});

// Initialize application
async function initializeApp() {
    showLoading();
    try {
        await updateConnectionStatus();
        await updateDashboardData();
        initializePerformanceChart();
    } catch (error) {
        console.error('Error initializing app:', error);
        showAlert('Error initializing application', 'danger');
    }
    hideLoading();
}

// Update MT5 connection status
async function updateConnectionStatus() {
    try {
        const response = await fetch(`${API_BASE}/trading/connection-status`);
        const data = await response.json();
        
        connectionStatus = data.connected;
        
        // Update navbar indicator
        const statusElement = document.getElementById('connection-status');
        const mt5StatusElement = document.getElementById('mt5-status');
        
        if (data.connected) {
            if (data.mock_mode) {
                statusElement.className = 'badge status-mock';
                statusElement.innerHTML = '<i class="fas fa-circle me-1"></i>Mock Mode';
                if (mt5StatusElement) mt5StatusElement.textContent = 'Mock Mode';
            } else {
                statusElement.className = 'badge status-connected';
                statusElement.innerHTML = '<i class="fas fa-circle me-1"></i>Connected';
                if (mt5StatusElement) mt5StatusElement.textContent = 'Connected';
            }
        } else {
            statusElement.className = 'badge status-disconnected';
            statusElement.innerHTML = '<i class="fas fa-circle me-1"></i>Disconnected';
            if (mt5StatusElement) mt5StatusElement.textContent = 'Disconnected';
        }
    } catch (error) {
        console.error('Error checking connection status:', error);
    }
}

// Update dashboard data
async function updateDashboardData() {
    try {
        // Update system status
        const systemStatus = await fetch(`${API_BASE}/monitoring/system-status`);
        const systemData = await systemStatus.json();
        
        // Update cards
        updateElement('active-strategies', systemData.active_strategies);
        updateElement('open-positions', systemData.total_open_positions);
        
        // Update performance data
        const performance = await fetch(`${API_BASE}/monitoring/performance/overall?days=1`);
        const performanceData = await performance.json();
        
        updateElement('daily-pnl', `$${performanceData.total_profit_loss.toFixed(2)}`);
        
        // Update market prices
        await updateMarketPrices();
        
        // Update recent trades
        await updateRecentTrades();
        
        // Update system logs
        await updateSystemLogs();
        
    } catch (error) {
        console.error('Error updating dashboard:', error);
    }
}

// Update market prices
async function updateMarketPrices() {
    const symbols = ['BTCUSD', 'EURUSD', 'GBPUSD'];
    const pricesContainer = document.getElementById('market-prices');
    
    if (!pricesContainer) return;
    
    let pricesHtml = '';
    
    for (const symbol of symbols) {
        try {
            const response = await fetch(`${API_BASE}/trading/price/${symbol}`);
            if (response.ok) {
                const priceData = await response.json();
                pricesHtml += `
                    <div class="price-display">
                        <div class="price-symbol">${symbol}</div>
                        <div class="d-flex justify-content-between">
                            <span class="price-bid">Bid: ${priceData.bid}</span>
                            <span class="price-ask">Ask: ${priceData.ask}</span>
                        </div>
                        <div class="price-spread text-center">Spread: ${priceData.spread.toFixed(5)}</div>
                    </div>
                `;
            }
        } catch (error) {
            console.error(`Error fetching price for ${symbol}:`, error);
        }
    }
    
    pricesContainer.innerHTML = pricesHtml || '<p class="text-muted">No price data available</p>';
}

// Update recent trades
async function updateRecentTrades() {
    const tradesContainer = document.getElementById('recent-trades');
    if (!tradesContainer) return;
    
    try {
        const response = await fetch(`${API_BASE}/trading/trades?limit=10`);
        const trades = await response.json();
        
        let tradesHtml = '';
        
        trades.forEach(trade => {
            const typeClass = trade.trade_type === 'buy' ? 'trade-buy' : 'trade-sell';
            const statusClass = `trade-${trade.status}`;
            
            tradesHtml += `
                <div class="d-flex justify-content-between align-items-center mb-2 p-2 border-bottom">
                    <div>
                        <span class="${typeClass}">${trade.trade_type.toUpperCase()}</span>
                        <span class="ms-2">${trade.symbol}</span>
                        <br>
                        <small class="text-muted">${new Date(trade.open_time).toLocaleString()}</small>
                    </div>
                    <div class="text-end">
                        <span class="badge ${statusClass}">${trade.status}</span>
                        <br>
                        <small>${trade.volume} lots</small>
                    </div>
                </div>
            `;
        });
        
        tradesContainer.innerHTML = tradesHtml || '<p class="text-muted">No recent trades</p>';
    } catch (error) {
        console.error('Error updating recent trades:', error);
        tradesContainer.innerHTML = '<p class="text-danger">Error loading trades</p>';
    }
}

// Update system logs
async function updateSystemLogs() {
    const logsContainer = document.getElementById('system-logs');
    if (!logsContainer) return;
    
    try {
        const response = await fetch(`${API_BASE}/monitoring/logs?limit=20`);
        const logs = await response.json();
        
        let logsHtml = '';
        
        logs.forEach(log => {
            const levelClass = `log-${log.level.toLowerCase()}`;
            logsHtml += `
                <div class="log-entry ${levelClass}">
                    <div class="log-timestamp">${new Date(log.created_at).toLocaleString()}</div>
                    <div>[${log.level}] ${log.component}: ${log.message}</div>
                </div>
            `;
        });
        
        logsContainer.innerHTML = logsHtml || '<p class="text-muted">No logs available</p>';
    } catch (error) {
        console.error('Error updating system logs:', error);
        logsContainer.innerHTML = '<p class="text-danger">Error loading logs</p>';
    }
}

// Initialize performance chart
function initializePerformanceChart() {
    const ctx = document.getElementById('performanceChart');
    if (!ctx) return;
    
    performanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Cumulative P&L',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
    
    // Load initial chart data
    loadPerformanceChartData();
}

// Load performance chart data
async function loadPerformanceChartData() {
    if (!performanceChart) return;
    
    try {
        // This is a placeholder - you would implement actual performance data endpoint
        const labels = [];
        const data = [];
        
        // Generate sample data for now
        for (let i = 0; i < 30; i++) {
            const date = new Date();
            date.setDate(date.getDate() - (29 - i));
            labels.push(date.toLocaleDateString());
            data.push(Math.random() * 1000 - 500); // Random P&L data
        }
        
        performanceChart.data.labels = labels;
        performanceChart.data.datasets[0].data = data;
        performanceChart.update();
    } catch (error) {
        console.error('Error loading chart data:', error);
    }
}

// Connect to MT5
async function connectMT5() {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/trading/connect`, { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            showAlert(data.message, 'success');
            await updateConnectionStatus();
        } else {
            showAlert('Failed to connect to MT5', 'danger');
        }
    } catch (error) {
        console.error('Error connecting to MT5:', error);
        showAlert('Error connecting to MT5', 'danger');
    }
    hideLoading();
}

// Disconnect from MT5
async function disconnectMT5() {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/trading/disconnect`, { method: 'POST' });
        const data = await response.json();
        
        showAlert(data.message, 'info');
        await updateConnectionStatus();
    } catch (error) {
        console.error('Error disconnecting from MT5:', error);
        showAlert('Error disconnecting from MT5', 'danger');
    }
    hideLoading();
}

// Close all positions
async function closeAllPositions() {
    if (!confirm('Are you sure you want to close all open positions?')) {
        return;
    }
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/trading/positions`, { method: 'DELETE' });
        const data = await response.json();
        
        if (response.ok) {
            showAlert(data.message, 'success');
            await updateDashboardData();
        } else {
            showAlert('Failed to close positions', 'danger');
        }
    } catch (error) {
        console.error('Error closing positions:', error);
        showAlert('Error closing positions', 'danger');
    }
    hideLoading();
}

// Show quick trade modal
function showQuickTradeModal() {
    const modal = new bootstrap.Modal(document.getElementById('quickTradeModal'));
    modal.show();
}

// Show create strategy modal
function showCreateStrategyModal() {
    const modal = new bootstrap.Modal(document.getElementById('createStrategyModal'));
    modal.show();
}

// Place quick trade
async function placeQuickTrade() {
    const form = document.getElementById('quickTradeForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const tradeData = {
        symbol: document.getElementById('symbol').value,
        trade_type: document.getElementById('tradeType').value,
        volume: parseFloat(document.getElementById('volume').value),
        stop_loss: document.getElementById('stopLoss').value ? parseFloat(document.getElementById('stopLoss').value) : null,
        take_profit: document.getElementById('takeProfit').value ? parseFloat(document.getElementById('takeProfit').value) : null,
        comment: 'Quick Trade'
    };
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/trading/orders`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(tradeData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert('Trade placed successfully!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('quickTradeModal')).hide();
            form.reset();
            await updateDashboardData();
        } else {
            showAlert(result.detail || 'Failed to place trade', 'danger');
        }
    } catch (error) {
        console.error('Error placing trade:', error);
        showAlert('Error placing trade', 'danger');
    }
    hideLoading();
}

// Create strategy
async function createStrategy() {
    const form = document.getElementById('createStrategyForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const strategyData = {
        name: document.getElementById('strategyName').value,
        symbol: document.getElementById('strategySymbol').value,
        initial_lot_size: parseFloat(document.getElementById('initialLotSize').value),
        recovery_step: parseFloat(document.getElementById('recoveryStep').value),
        take_profit: parseFloat(document.getElementById('strategytakeProfit').value),
        stop_loss: parseFloat(document.getElementById('strategystopLoss').value),
        description: document.getElementById('description').value
    };
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/strategies/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(strategyData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert('Strategy created successfully!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('createStrategyModal')).hide();
            form.reset();
            await updateDashboardData();
        } else {
            showAlert(result.detail || 'Failed to create strategy', 'danger');
        }
    } catch (error) {
        console.error('Error creating strategy:', error);
        showAlert('Error creating strategy', 'danger');
    }
    hideLoading();
}

// Utility functions
function updateElement(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

function showAlert(message, type = 'info') {
    const alertsContainer = document.getElementById('alerts-container');
    const alertId = 'alert_' + Date.now();
    
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" id="${alertId}" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    alertsContainer.insertAdjacentHTML('beforeend', alertHtml);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        const alert = document.getElementById(alertId);
        if (alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }
    }, 5000);
}

function showLoading() {
    const modal = new bootstrap.Modal(document.getElementById('loadingModal'));
    modal.show();
}

function hideLoading() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('loadingModal'));
    if (modal) {
        modal.hide();
    }
}

// Export functions for use in other scripts
window.AlgoTrading = {
    updateConnectionStatus,
    updateDashboardData,
    connectMT5,
    disconnectMT5,
    closeAllPositions,
    showAlert,
    showLoading,
    hideLoading
};