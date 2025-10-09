// Strategies page JavaScript functionality

let strategiesData = [];
let currentPage = 1;
const itemsPerPage = 10;

// Initialize strategies page
document.addEventListener('DOMContentLoaded', function() {
    loadStrategies();
    
    // Auto-refresh every 30 seconds
    setInterval(loadStrategies, 30000);
});

// Load all strategies
async function loadStrategies() {
    try {
        const response = await fetch('/api/v1/strategies/');
        strategiesData = await response.json();
        
        updateStrategyCounts();
        displayStrategies();
        
    } catch (error) {
        console.error('Error loading strategies:', error);
        showAlert('Error loading strategies', 'danger');
    }
}

// Update strategy count cards
function updateStrategyCounts() {
    const total = strategiesData.length;
    const active = strategiesData.filter(s => s.status === 'active').length;
    const paused = strategiesData.filter(s => s.status === 'paused').length;
    const stopped = strategiesData.filter(s => s.status === 'stopped').length;
    
    document.getElementById('total-strategies').textContent = total;
    document.getElementById('active-strategies').textContent = active;
    document.getElementById('paused-strategies').textContent = paused;
    document.getElementById('stopped-strategies').textContent = stopped;
}

// Display strategies in table
function displayStrategies(filteredData = null) {
    const data = filteredData || strategiesData;
    const tableBody = document.getElementById('strategies-table-body');
    
    if (data.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-muted">
                    <i class="fas fa-cog fa-2x mb-3 opacity-50"></i>
                    <p>No strategies found</p>
                </td>
            </tr>
        `;
        return;
    }
    
    let html = '';
    
    data.forEach(strategy => {
        const statusClass = getStatusBadgeClass(strategy.status);
        const statusIcon = getStatusIcon(strategy.status);
        
        html += `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <strong>${strategy.name}</strong>
                        ${strategy.description ? `<small class="text-muted ms-2">${strategy.description.substring(0, 50)}...</small>` : ''}
                    </div>
                </td>
                <td>
                    <span class="badge bg-info">${strategy.strategy_type}</span>
                </td>
                <td>
                    <span class="fw-bold">${strategy.symbol}</span>
                </td>
                <td>
                    <span class="badge ${statusClass}">
                        <i class="${statusIcon} me-1"></i>${strategy.status}
                    </span>
                </td>
                <td>${strategy.initial_lot_size}</td>
                <td>${strategy.recovery_step} pips</td>
                <td>
                    <small>${new Date(strategy.created_at).toLocaleDateString()}</small>
                </td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        ${strategy.status === 'active' ? 
                            `<button class="btn btn-outline-warning" onclick="pauseStrategy(${strategy.id})" title="Pause">
                                <i class="fas fa-pause"></i>
                            </button>
                            <button class="btn btn-outline-danger" onclick="stopStrategy(${strategy.id})" title="Stop">
                                <i class="fas fa-stop"></i>
                            </button>` :
                            `<button class="btn btn-outline-success" onclick="startStrategy(${strategy.id})" title="Start">
                                <i class="fas fa-play"></i>
                            </button>`
                        }
                        <button class="btn btn-outline-primary" onclick="viewStrategyDetails(${strategy.id})" title="Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-outline-secondary" onclick="editStrategy(${strategy.id})" title="Edit" ${strategy.status === 'active' ? 'disabled' : ''}>
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="deleteStrategy(${strategy.id})" title="Delete" ${strategy.status === 'active' ? 'disabled' : ''}>
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    tableBody.innerHTML = html;
}

// Filter strategies
function filterStrategies() {
    const statusFilter = document.getElementById('statusFilter').value;
    const typeFilter = document.getElementById('typeFilter').value;
    
    let filteredData = strategiesData;
    
    if (statusFilter) {
        filteredData = filteredData.filter(s => s.status === statusFilter);
    }
    
    if (typeFilter) {
        filteredData = filteredData.filter(s => s.strategy_type === typeFilter);
    }
    
    displayStrategies(filteredData);
}

// Start strategy
async function startStrategy(strategyId) {
    const sessionName = prompt('Enter session name (optional):') || `Session_${Date.now()}`;
    
    try {
        showLoading();
        const response = await fetch(`/api/v1/strategies/${strategyId}/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ session_name: sessionName })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(result.message, 'success');
            await loadStrategies();
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

// Stop strategy
async function stopStrategy(strategyId) {
    if (!confirm('Are you sure you want to stop this strategy?')) {
        return;
    }
    
    try {
        showLoading();
        const response = await fetch(`/api/v1/strategies/${strategyId}/stop`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(result.message, 'success');
            await loadStrategies();
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

// Pause strategy (placeholder - would need backend implementation)
async function pauseStrategy(strategyId) {
    showAlert('Pause functionality not yet implemented', 'info');
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
        strategy_type: document.getElementById('strategyType').value,
        symbol: document.getElementById('strategySymbol').value,
        description: document.getElementById('description').value,
        initial_lot_size: parseFloat(document.getElementById('initialLotSize').value),
        max_lot_size: parseFloat(document.getElementById('maxLotSize').value),
        recovery_step: parseFloat(document.getElementById('recoveryStep').value),
        max_trades: parseInt(document.getElementById('maxTrades').value),
        take_profit: parseFloat(document.getElementById('takeProfit').value),
        stop_loss: parseFloat(document.getElementById('stopLoss').value),
        max_drawdown: parseFloat(document.getElementById('maxDrawdown').value),
        risk_per_trade: parseFloat(document.getElementById('riskPerTrade').value)
    };
    
    try {
        showLoading();
        const response = await fetch('/api/v1/strategies/', {
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
            await loadStrategies();
        } else {
            showAlert(result.detail || 'Failed to create strategy', 'danger');
        }
    } catch (error) {
        console.error('Error creating strategy:', error);
        showAlert('Error creating strategy', 'danger');
    } finally {
        hideLoading();
    }
}

// Edit strategy
async function editStrategy(strategyId) {
    try {
        const response = await fetch(`/api/v1/strategies/${strategyId}`);
        const strategy = await response.json();
        
        if (response.ok) {
            // Populate edit form
            document.getElementById('editStrategyId').value = strategy.id;
            document.getElementById('editStrategyName').value = strategy.name;
            // Add more fields as needed
            
            const modal = new bootstrap.Modal(document.getElementById('editStrategyModal'));
            modal.show();
        } else {
            showAlert('Failed to load strategy details', 'danger');
        }
    } catch (error) {
        console.error('Error loading strategy for edit:', error);
        showAlert('Error loading strategy', 'danger');
    }
}

// Update strategy
async function updateStrategy() {
    const strategyId = document.getElementById('editStrategyId').value;
    const form = document.getElementById('editStrategyForm');
    
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const updateData = {
        name: document.getElementById('editStrategyName').value
        // Add more fields as needed
    };
    
    try {
        showLoading();
        const response = await fetch(`/api/v1/strategies/${strategyId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updateData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert('Strategy updated successfully!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('editStrategyModal')).hide();
            await loadStrategies();
        } else {
            showAlert(result.detail || 'Failed to update strategy', 'danger');
        }
    } catch (error) {
        console.error('Error updating strategy:', error);
        showAlert('Error updating strategy', 'danger');
    } finally {
        hideLoading();
    }
}

// Delete strategy
async function deleteStrategy(strategyId) {
    const strategy = strategiesData.find(s => s.id === strategyId);
    if (!strategy) return;
    
    if (!confirm(`Are you sure you want to delete strategy "${strategy.name}"? This action cannot be undone.`)) {
        return;
    }
    
    try {
        showLoading();
        const response = await fetch(`/api/v1/strategies/${strategyId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(result.message, 'success');
            await loadStrategies();
        } else {
            showAlert(result.detail || 'Failed to delete strategy', 'danger');
        }
    } catch (error) {
        console.error('Error deleting strategy:', error);
        showAlert('Error deleting strategy', 'danger');
    } finally {
        hideLoading();
    }
}

// View strategy details
async function viewStrategyDetails(strategyId) {
    try {
        showLoading();
        
        // Load strategy details
        const strategyResponse = await fetch(`/api/v1/strategies/${strategyId}`);
        const strategy = await strategyResponse.json();
        
        // Load strategy sessions
        const sessionsResponse = await fetch(`/api/v1/strategies/${strategyId}/sessions`);
        const sessions = await sessionsResponse.json();
        
        if (strategyResponse.ok && sessionsResponse.ok) {
            displayStrategyDetails(strategy, sessions);
            
            const modal = new bootstrap.Modal(document.getElementById('strategyDetailsModal'));
            modal.show();
        } else {
            showAlert('Failed to load strategy details', 'danger');
        }
    } catch (error) {
        console.error('Error loading strategy details:', error);
        showAlert('Error loading strategy details', 'danger');
    } finally {
        hideLoading();
    }
}

// Display strategy details in modal
function displayStrategyDetails(strategy, sessions) {
    document.getElementById('strategyDetailsTitle').textContent = `Strategy: ${strategy.name}`;
    
    const content = `
        <div class="row">
            <div class="col-md-6">
                <h6 class="border-bottom pb-2">Strategy Information</h6>
                <table class="table table-sm">
                    <tr><td><strong>Name:</strong></td><td>${strategy.name}</td></tr>
                    <tr><td><strong>Type:</strong></td><td><span class="badge bg-info">${strategy.strategy_type}</span></td></tr>
                    <tr><td><strong>Symbol:</strong></td><td>${strategy.symbol}</td></tr>
                    <tr><td><strong>Status:</strong></td><td><span class="badge ${getStatusBadgeClass(strategy.status)}">${strategy.status}</span></td></tr>
                    <tr><td><strong>Created:</strong></td><td>${new Date(strategy.created_at).toLocaleString()}</td></tr>
                </table>
                
                <h6 class="border-bottom pb-2 mt-4">Trading Parameters</h6>
                <table class="table table-sm">
                    <tr><td><strong>Initial Lot Size:</strong></td><td>${strategy.initial_lot_size}</td></tr>
                    <tr><td><strong>Max Lot Size:</strong></td><td>${strategy.max_lot_size}</td></tr>
                    <tr><td><strong>Recovery Step:</strong></td><td>${strategy.recovery_step} pips</td></tr>
                    <tr><td><strong>Max Trades:</strong></td><td>${strategy.max_trades}</td></tr>
                    <tr><td><strong>Take Profit:</strong></td><td>${strategy.take_profit} pips</td></tr>
                    <tr><td><strong>Stop Loss:</strong></td><td>${strategy.stop_loss} pips</td></tr>
                    <tr><td><strong>Max Drawdown:</strong></td><td>$${strategy.max_drawdown}</td></tr>
                </table>
            </div>
            
            <div class="col-md-6">
                <h6 class="border-bottom pb-2">Trading Sessions</h6>
                <div style="max-height: 400px; overflow-y: auto;">
                    ${sessions.length === 0 ? 
                        '<p class="text-muted">No trading sessions found</p>' :
                        sessions.map(session => `
                            <div class="border rounded p-3 mb-3">
                                <div class="d-flex justify-content-between align-items-start mb-2">
                                    <h6 class="mb-0">${session.session_name}</h6>
                                    <span class="badge ${session.status === 'active' ? 'bg-success' : 'bg-secondary'}">${session.status}</span>
                                </div>
                                <small class="text-muted">
                                    Started: ${new Date(session.start_time).toLocaleString()}<br>
                                    ${session.end_time ? `Ended: ${new Date(session.end_time).toLocaleString()}` : 'Still running'}
                                </small>
                                <div class="row mt-2">
                                    <div class="col-6"><small>Total Trades: <strong>${session.total_trades}</strong></small></div>
                                    <div class="col-6"><small>Win Rate: <strong>${session.total_trades > 0 ? ((session.winning_trades / session.total_trades) * 100).toFixed(1) : 0}%</strong></small></div>
                                    <div class="col-12"><small>P&L: <strong class="${session.total_profit_loss >= 0 ? 'text-success' : 'text-danger'}">$${session.total_profit_loss.toFixed(2)}</strong></small></div>
                                </div>
                            </div>
                        `).join('')
                    }
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('strategyDetailsContent').innerHTML = content;
}

// Show create strategy modal
function showCreateStrategyModal() {
    const modal = new bootstrap.Modal(document.getElementById('createStrategyModal'));
    modal.show();
}

// Helper functions
function getStatusBadgeClass(status) {
    const classes = {
        'active': 'bg-success',
        'inactive': 'bg-secondary',
        'paused': 'bg-warning',
        'stopped': 'bg-danger'
    };
    return classes[status] || 'bg-secondary';
}

function getStatusIcon(status) {
    const icons = {
        'active': 'fas fa-play',
        'inactive': 'fas fa-pause',
        'paused': 'fas fa-pause-circle',
        'stopped': 'fas fa-stop'
    };
    return icons[status] || 'fas fa-question';
}

// Export functions
window.Strategies = {
    loadStrategies,
    startStrategy,
    stopStrategy,
    createStrategy,
    deleteStrategy,
    viewStrategyDetails
};