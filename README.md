# AlgoTrading FastAPI Platform

A cross-platform algorithmic trading application built with FastAPI, featuring a web interface for managing MetaTrader 5 trading strategies.

## Features

- **Cross-Platform Support**: Works on Windows, macOS, and Linux with MT5 mock mode for non-Windows systems
- **Web Interface**: Modern HTML/CSS/JS dashboard for strategy management and monitoring
- **RESTful API**: Complete API for trading operations, strategy management, and performance monitoring
- **Database Integration**: SQLite database for storing trades, strategies, and session data
- **Martingale Strategy**: Built-in implementation of the Martingale trading strategy
- **Real-time Monitoring**: Live updates of positions, P&L, and system status
- **Risk Management**: Configurable stop-loss, take-profit, and drawdown limits

## Project Structure

```
algo_trading/
├── app/
│   ├── core/
│   │   └── config.py          # Configuration management
│   ├── database/
│   │   └── database.py        # Database setup and session management
│   ├── models/
│   │   └── models.py          # SQLAlchemy database models
│   ├── routers/
│   │   ├── trading.py         # Trading API endpoints
│   │   ├── strategies.py      # Strategy management endpoints
│   │   └── monitoring.py      # Monitoring and analytics endpoints
│   └── services/
│       ├── mt5_interface.py   # Cross-platform MT5 interface
│       └── martingale_service.py  # Martingale strategy implementation
├── static/
│   ├── css/
│   │   └── style.css          # Custom CSS styles
│   └── js/
│       ├── main.js            # Core JavaScript functionality
│       ├── dashboard.js       # Dashboard-specific JavaScript
│       └── strategies.js      # Strategy management JavaScript
├── templates/
│   ├── base.html              # Base template
│   ├── dashboard.html         # Main dashboard
│   ├── strategies.html        # Strategy management page
│   ├── trades.html            # Trade management page
│   └── monitoring.html        # Performance monitoring page
├── main.py                    # FastAPI application entry point
├── requirements.txt           # Python dependencies
└── .env.example              # Environment configuration example
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd algo_trading
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment** (optional):
   ```bash
   cp .env.example .env
   # Edit .env file with your MT5 credentials if available
   ```

## Running the Application

1. **Start the FastAPI server**:
   ```bash
   python main.py
   ```

2. **Access the application**:
   - Web Interface: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Alternative API Docs: http://localhost:8000/redoc

## API Endpoints

### Trading Operations
- `POST /api/v1/trading/connect` - Connect to MT5
- `POST /api/v1/trading/disconnect` - Disconnect from MT5
- `GET /api/v1/trading/connection-status` - Check connection status
- `GET /api/v1/trading/price/{symbol}` - Get current price
- `POST /api/v1/trading/orders` - Place market order
- `GET /api/v1/trading/positions` - Get open positions
- `DELETE /api/v1/trading/positions/{ticket}` - Close specific position
- `DELETE /api/v1/trading/positions` - Close all positions
- `GET /api/v1/trading/trades` - Get trade history

### Strategy Management
- `POST /api/v1/strategies/` - Create new strategy
- `GET /api/v1/strategies/` - Get all strategies
- `GET /api/v1/strategies/{id}` - Get strategy by ID
- `PUT /api/v1/strategies/{id}` - Update strategy
- `DELETE /api/v1/strategies/{id}` - Delete strategy
- `POST /api/v1/strategies/{id}/start` - Start strategy
- `POST /api/v1/strategies/{id}/stop` - Stop strategy
- `GET /api/v1/strategies/{id}/sessions` - Get strategy sessions

### Monitoring & Analytics
- `GET /api/v1/monitoring/system-status` - Get system status
- `GET /api/v1/monitoring/performance/overall` - Get overall performance
- `GET /api/v1/monitoring/performance/by-symbol` - Get performance by symbol
- `GET /api/v1/monitoring/sessions/{id}/performance` - Get session performance
- `GET /api/v1/monitoring/logs` - Get system logs
- `GET /api/v1/monitoring/market-data/{symbol}` - Get market data
- `GET /api/v1/monitoring/active-trades` - Get active trades

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Environment
ENVIRONMENT=development

# Database
DATABASE_URL=sqlite:///./algotrading.db

# MetaTrader 5 (Optional)
MT5_ACCOUNT_ID=your_account_id
MT5_PASSWORD=your_password
MT5_SERVER=your_server

# Trading
DEFAULT_SYMBOL=BTCUSD
DEFAULT_LOT_SIZE=0.01
MAX_CONCURRENT_TRADES=10

# Risk Management
MAX_DRAWDOWN_PERCENT=10.0
MAX_RISK_PER_TRADE=2.0
```

## Cross-Platform Compatibility

The application automatically detects the operating system:

- **Windows**: Uses full MT5 integration when MetaTrader5 package is available
- **macOS/Linux**: Falls back to mock mode for testing and development
- **Mock Mode**: Simulates trading operations for testing without MT5

## Usage Examples

### Creating a Strategy via Web Interface

1. Navigate to the Strategies page
2. Click "Create New Strategy"
3. Configure parameters:
   - Strategy Name: "My Martingale BTCUSD"
   - Symbol: BTCUSD
   - Initial Lot Size: 0.01
   - Recovery Step: 50 pips
   - Take Profit: 100 pips
   - Stop Loss: 500 pips
4. Click "Create Strategy"

### Starting a Strategy

1. Find your strategy in the strategies list
2. Click the Play button
3. Enter a session name (optional)
4. The strategy will start running and placing trades automatically

### Monitoring Performance

- View real-time dashboard with key metrics
- Monitor active positions and recent trades
- Analyze performance charts and statistics
- Review system logs for troubleshooting

## Development

### Adding New Strategies

1. Create a new service class in `app/services/`
2. Implement the strategy logic
3. Add strategy type to the database models
4. Update the API endpoints to handle the new strategy type

### Extending the API

1. Add new endpoints to appropriate routers
2. Update database models if needed
3. Test using the interactive API documentation at `/docs`

### Customizing the UI

1. Modify templates in the `templates/` directory
2. Update CSS styles in `static/css/style.css`
3. Add JavaScript functionality in `static/js/`

## Security Considerations

- Never commit real MT5 credentials to version control
- Use environment variables for sensitive configuration
- Implement proper authentication for production use
- Validate all user inputs and API parameters
- Use HTTPS in production environments

## Troubleshooting

### MT5 Connection Issues
- Ensure MT5 is installed and running (Windows only)
- Check credentials in .env file
- Verify server settings
- On non-Windows systems, mock mode will be used automatically

### Database Issues
- Delete `algotrading.db` to reset the database
- Check file permissions in the project directory
- Verify SQLite is available

### API Issues
- Check the FastAPI logs in the terminal
- Use the `/docs` endpoint to test API calls
- Verify request headers and JSON format

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]