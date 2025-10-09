// Dashboard-specific JavaScript functionality

// Dashboard data refresh intervals
let dashboardRefreshInterval;
let priceUpdateInterval;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

// Initialize dashboard functionality
function initializeDashboard() {
    // Start auto-refresh intervals
    startAutoRefresh();
    
    // Initialize real-time price updates
    startPriceUpdates();
    
    // Load initial data
    loadDashboardMetrics();
}

// Start auto-refresh for dashboard data
function startAutoRefresh() {
    // Refresh every 30 seconds
    dashboardRefreshInterval = setInterval(() => {
        loadDashboardMetrics();
    }, 30000);
}

// Start real-time price updates
function startPriceUpdates() {
    // Update prices every 5 seconds
    priceUpdateInterval = setInterval(() => {
        updateMarketPrices();
    }, 5000);
}

// Load dashboard metrics
async function loadDashboardMetrics() {
    try {
        // Load system status
        await loadSystemStatus();
        
        // Load performance metrics
        await loadPerformanceMetrics();
        
        // Load active positions
        await loadActivePositions();
        
        // Update timestamp
        updateLastRefreshTime();
        
    } catch (error) {
        console.error('Error loading dashboard metrics:', error);
        showAlert('Error updating dashboard data', 'warning');
    }
}

// Load system status
async function loadSystemStatus() {
    try {
        const response = await fetch('/api/v1/monitoring/system-status');
        const data = await response.json();
        
        // Update status cards
        updateElement('active-strategies', data.active_strategies);
        updateElement('open-positions', data.total_open_positions);
        
        // Update MT5 status card
        const mt5StatusCard = document.getElementById('mt5-status');
        if (mt5StatusCard) {
            if (data.mt5_connected) {
                mt5StatusCard.textContent = data.mt5_mock_mode ? 'Mock Mode' : 'Connected';
                mt5StatusCard.parentElement.parentElement.className = 
                    data.mt5_mock_mode ? 'card bg-warning text-white' : 'card bg-success text-white';
            } else {
                mt5StatusCard.textContent = 'Disconnected';
                mt5StatusCard.parentElement.parentElement.className = 'card bg-danger text-white';
            }
        }
        
    } catch (error) {
        console.error('Error loading system status:', error);
    }
}

// Load performance metrics
async function loadPerformanceMetrics() {
    try {
        const response = await fetch('/api/v1/monitoring/performance/overall?days=1');
        const data = await response.json();
        
        // Update daily P&L
        const dailyPnL = document.getElementById('daily-pnl');
        if (dailyPnL) {
            const pnlValue = data.total_profit_loss;
            dailyPnL.textContent = `$${pnlValue.toFixed(2)}`;
            
            // Update card color based on P&L
            const pnlCard = dailyPnL.closest('.card');
            if (pnlValue > 0) {
                pnlCard.className = 'card bg-success text-white';
            } else if (pnlValue < 0) {
                pnlCard.className = 'card bg-danger text-white';
            } else {
                pnlCard.className = 'card bg-warning text-white';
            }
        }
        
        // Update performance chart if it exists
        if (window.performanceChart) {
            await updatePerformanceChart();
        }
        
    } catch (error) {
        console.error('Error loading performance metrics:', error);
    }
}

// Load active positions
async function loadActivePositions() {
    try {
        const response = await fetch('/api/v1/trading/positions');
        const positions = await response.json();
        
        // Update positions count
        updateElement('open-positions', positions.length);
        
        // You could also update a detailed positions table here
        
    } catch (error) {
        console.error('Error loading active positions:', error);
    }
}

// Update performance chart
async function updatePerformanceChart() {
    if (!window.performanceChart) return;
    
    try {
        // Get performance data for the last 30 days
        const response = await fetch('/api/v1/monitoring/performance/overall?days=30');
        const data = await response.json();
        
        // For now, create sample data - you'd implement actual historical data endpoint
        const labels = [];
        const chartData = [];
        let cumulativePnL = 0;
        
        for (let i = 29; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
            
            // Simulate daily P&L changes
            const dailyChange = (Math.random() - 0.5) * 200;
            cumulativePnL += dailyChange;
            chartData.push(cumulativePnL);
        }
        
        window.performanceChart.data.labels = labels;
        window.performanceChart.data.datasets[0].data = chartData;
        
        // Update chart colors based on final P&L
        const color = cumulativePnL >= 0 ? 'rgb(40, 167, 69)' : 'rgb(220, 53, 69)';
        window.performanceChart.data.datasets[0].borderColor = color;
        window.performanceChart.data.datasets[0].backgroundColor = color + '20';
        
        window.performanceChart.update('none'); // No animation for real-time updates
        
    } catch (error) {
        console.error('Error updating performance chart:', error);
    }
}

// Update last refresh time
function updateLastRefreshTime() {
    const refreshIndicator = document.getElementById('last-refresh');
    if (refreshIndicator) {
        refreshIndicator.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
    }
}

// Handle strategy quick actions
async function startStrategy(strategyId) {
    try {
        showLoading();
        const response = await fetch(`/api/v1/strategies/${strategyId}/start`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(result.message, 'success');
            await loadDashboardMetrics();
        } else {
            showAlert(result.detail || 'Failed to start strategy', 'danger');
        }
    } catch (error) {
        console.error('Error starting strategy:', error);
        showAlert('Error starting strategy', 'danger');
    } finally {
        hideLoading();
    }
}

async function stopStrategy(strategyId) {
    try {
        showLoading();
        const response = await fetch(`/api/v1/strategies/${strategyId}/stop`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(result.message, 'success');
            await loadDashboardMetrics();
        } else {
            showAlert(result.detail || 'Failed to stop strategy', 'danger');
        }
    } catch (error) {
        console.error('Error stopping strategy:', error);
        showAlert('Error stopping strategy', 'danger');
    } finally {
        hideLoading();
    }
}

// Enhanced market price updates with animations
async function updateMarketPricesEnhanced() {
    const symbols = ['BTCUSD', 'EURUSD', 'GBPUSD', 'USDJPY'];
    const pricesContainer = document.getElementById('market-prices');
    
    if (!pricesContainer) return;
    
    let pricesHtml = '';
    
    for (const symbol of symbols) {
        try {
            const response = await fetch(`/api/v1/trading/price/${symbol}`);
            if (response.ok) {
                const priceData = await response.json();
                
                // Add trend indicators (simplified)
                const trendIcon = Math.random() > 0.5 ? 
                    '<i class="fas fa-arrow-up text-success"></i>' : 
                    '<i class="fas fa-arrow-down text-danger"></i>';
                
                pricesHtml += `
                    <div class="price-display" data-symbol="${symbol}">
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="price-symbol">${symbol}</span>
                            ${trendIcon}
                        </div>
                        <div class="d-flex justify-content-between mt-2">
                            <div class="text-center">
                                <small class="text-muted">Bid</small><br>
                                <span class="price-bid fw-bold">${priceData.bid.toFixed(5)}</span>
                            </div>
                            <div class="text-center">
                                <small class="text-muted">Ask</small><br>
                                <span class="price-ask fw-bold">${priceData.ask.toFixed(5)}</span>
                            </div>
                        </div>
                        <div class="text-center mt-2">
                            <small class="price-spread">Spread: ${(priceData.spread * 100000).toFixed(1)} pips</small>
                        </div>
                    </div>
                `;
            }
        } catch (error) {
            console.error(`Error fetching price for ${symbol}:`, error);
        }
    }
    
    if (pricesHtml) {
        pricesContainer.innerHTML = pricesHtml;
        
        // Add update animation
        pricesContainer.classList.add('updating');
        setTimeout(() => {
            pricesContainer.classList.remove('updating');
        }, 1000);
    }
}

// Enhanced recent trades with better formatting
async function updateRecentTradesEnhanced() {
    const tradesContainer = document.getElementById('recent-trades');
    if (!tradesContainer) return;
    
    try {
        const response = await fetch('/api/v1/trading/trades?limit=10');
        const trades = await response.json();
        
        if (trades.length === 0) {
            tradesContainer.innerHTML = `
                <div class="text-center text-muted p-4">
                    <i class="fas fa-chart-line fa-3x mb-3 opacity-50"></i>
                    <p>No recent trades</p>
                </div>
            `;
            return;
        }
        
        let tradesHtml = '';
        
        trades.forEach((trade, index) => {
            const typeClass = trade.trade_type === 'buy' ? 'text-success' : 'text-danger';
            const typeIcon = trade.trade_type === 'buy' ? 'fa-arrow-up' : 'fa-arrow-down';
            const statusClass = getStatusBadgeClass(trade.status);
            
            tradesHtml += `
                <div class="trade-item border-bottom py-2 ${index === 0 ? 'latest-trade' : ''}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <div class="d-flex align-items-center mb-1">
                                <i class="fas ${typeIcon} ${typeClass} me-2"></i>
                                <span class="fw-bold ${typeClass}">${trade.trade_type.toUpperCase()}</span>
                                <span class="ms-2 text-dark">${trade.symbol}</span>
                            </div>
                            <div class="d-flex justify-content-between">
                                <small class="text-muted">
                                    ${new Date(trade.open_time).toLocaleDateString()} 
                                    ${new Date(trade.open_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                                </small>
                                <small class="text-muted">${trade.volume} lots</small>
                            </div>
                        </div>
                        <div class="text-end ms-2">
                            <span class="badge ${statusClass} mb-1">${trade.status}</span>
                            ${trade.open_price ? `<br><small class="text-muted">@${trade.open_price}</small>` : ''}
                        </div>
                    </div>
                </div>
            `;
        });
        
        tradesContainer.innerHTML = tradesHtml;
        
    } catch (error) {
        console.error('Error updating recent trades:', error);
        tradesContainer.innerHTML = `
            <div class="text-center text-danger p-4">
                <i class="fas fa-exclamation-triangle fa-2x mb-3"></i>
                <p>Error loading trades</p>
            </div>
        `;
    }
}

// Get appropriate badge class for trade status
function getStatusBadgeClass(status) {
    const statusClasses = {
        'open': 'bg-primary',
        'closed': 'bg-secondary',
        'pending': 'bg-warning',
        'cancelled': 'bg-danger'
    };
    return statusClasses[status] || 'bg-secondary';
}

// Clean up intervals when leaving the page
window.addEventListener('beforeunload', function() {
    if (dashboardRefreshInterval) {
        clearInterval(dashboardRefreshInterval);
    }
    if (priceUpdateInterval) {
        clearInterval(priceUpdateInterval);
    }
});

// Override the main.js functions with enhanced versions
if (typeof window.updateMarketPrices !== 'undefined') {
    window.updateMarketPrices = updateMarketPricesEnhanced;
}

if (typeof window.updateRecentTrades !== 'undefined') {
    window.updateRecentTrades = updateRecentTradesEnhanced;
}

// MT5 Connection Management
async function checkMT5Connection() {
    try {
        const response = await fetch('/api/v1/trading/connection-status');
        const status = await response.json();
        
        const alertElement = document.getElementById('connection-alert');
        const messageElement = document.getElementById('connection-message');
        const formElement = document.getElementById('mt5-connection-form');
        
        if (status.connected) {
            alertElement.className = 'alert alert-success';
            if (status.mock_mode) {
                messageElement.textContent = 'Connected in Mock Mode - Using simulated data';
                formElement.style.display = 'block'; // Show form to allow real connection
            } else {
                messageElement.textContent = 'Connected to Real MT5 Account';
                formElement.style.display = 'none';
            }
        } else {
            alertElement.className = 'alert alert-warning';
            messageElement.textContent = 'Not connected to MT5';
            formElement.style.display = 'block';
        }
        
        return status;
    } catch (error) {
        console.error('Error checking MT5 connection:', error);
        const alertElement = document.getElementById('connection-alert');
        const messageElement = document.getElementById('connection-message');
        
        alertElement.className = 'alert alert-danger';
        messageElement.textContent = 'Error checking connection status';
        return null;
    }
}

async function connectMT5() {
    const accountId = document.getElementById('account-id').value;
    const password = document.getElementById('password').value;
    const server = document.getElementById('server').value;
    
    if (!accountId || !password || !server) {
        showAlert('Please fill in all connection fields', 'danger');
        return;
    }
    
    try {
        const response = await fetch('/api/v1/trading/connect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                account_id: parseInt(accountId),
                password: password,
                server: server
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(result.message, 'success');
            // Clear password field for security
            document.getElementById('password').value = '';
            // Refresh connection status
            setTimeout(() => checkMT5Connection(), 1000);
        } else {
            showAlert(result.detail || 'Connection failed', 'danger');
        }
    } catch (error) {
        console.error('Connection error:', error);
        showAlert('Connection error: ' + error.message, 'danger');
    }
}

async function disconnectMT5() {
    try {
        const response = await fetch('/api/v1/trading/disconnect', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(result.message, 'info');
            // Refresh connection status
            setTimeout(() => checkMT5Connection(), 1000);
        } else {
            showAlert(result.detail || 'Disconnection failed', 'danger');
        }
    } catch (error) {
        console.error('Disconnection error:', error);
        showAlert('Disconnection error: ' + error.message, 'danger');
    }
}

function showAlert(message, type) {
    // Create or update a temporary alert
    let alertContainer = document.getElementById('temp-alerts');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.id = 'temp-alerts';
        alertContainer.style.position = 'fixed';
        alertContainer.style.top = '20px';
        alertContainer.style.right = '20px';
        alertContainer.style.zIndex = '9999';
        document.body.appendChild(alertContainer);
    }
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertContainer.appendChild(alertDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.parentNode.removeChild(alertDiv);
        }
    }, 5000);
}

// Update the loadSystemStatus function to include connection check
const originalLoadSystemStatus = loadSystemStatus;
loadSystemStatus = async function() {
    await originalLoadSystemStatus();
    await checkMT5Connection();
};

// Export dashboard-specific functions
window.Dashboard = {
    startStrategy,
    stopStrategy,
    loadDashboardMetrics,
    updatePerformanceChart,
    connectMT5,
    disconnectMT5,
    checkMT5Connection
};