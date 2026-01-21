import { useEffect, useState, useRef } from 'react';
import '@/App.css';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Play, Pause, RotateCcw, Zap, Battery, TrendingUp, Sun, CloudRain } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { Toaster, toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const WS_URL = BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://');

const AgentCard = ({ agent }) => {
  const batteryPct = (agent.battery_level_kwh / agent.battery_capacity_kwh) * 100;
  
  return (
    <div data-testid={`agent-card-${agent.id}`} className="metric-card p-3">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`status-dot ${agent.status} animate-pulse`}></span>
          <span className="text-xs font-bold uppercase tracking-wide text-slate-700">{agent.name}</span>
        </div>
      </div>
      
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1 text-xs text-slate-500">
            <Sun className="w-3 h-3" style={{color: '#F59E0B'}} />
            <span>Solar</span>
          </div>
          <span className="font-data text-xs" style={{color: '#F59E0B'}}>
            {agent.current_solar_output_kw.toFixed(2)} kW
          </span>
        </div>
        
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1 text-xs text-slate-500">
            <Battery className="w-3 h-3" style={{color: '#10B981'}} />
            <span>Battery</span>
          </div>
          <span className="font-data text-xs" style={{color: '#10B981'}}>
            {batteryPct.toFixed(0)}%
          </span>
        </div>
        
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1 text-xs text-slate-500">
            <TrendingUp className="w-3 h-3" style={{color: '#3B82F6'}} />
            <span>Balance</span>
          </div>
          <span className="font-data text-xs" style={{color: '#0F172A'}}>
            €{agent.money_balance.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  );
};

const MarketPriceChart = ({ priceHistory }) => {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={priceHistory}>
        <defs>
          <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
            <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
        <XAxis 
          dataKey="tick" 
          stroke="#64748B" 
          style={{fontSize: '10px', fontFamily: 'JetBrains Mono'}}
        />
        <YAxis 
          stroke="#64748B" 
          style={{fontSize: '10px', fontFamily: 'JetBrains Mono'}}
          domain={[0, 'auto']}
        />
        <Tooltip 
          contentStyle={{
            background: '#0F172A',
            border: 'none',
            borderRadius: '0.125rem',
            color: 'white',
            fontFamily: 'JetBrains Mono',
            fontSize: '11px'
          }}
        />
        <Area 
          type="monotone" 
          dataKey="price" 
          stroke="#3B82F6" 
          strokeWidth={2}
          fill="url(#priceGradient)" 
        />
      </AreaChart>
    </ResponsiveContainer>
  );
};

const TransactionLog = ({ transactions }) => {
  return (
    <div className="metric-card p-3">
      <div className="border-b border-slate-100 pb-2 mb-2">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">Recent Transactions</h3>
      </div>
      <div className="space-y-1 max-h-64 overflow-y-auto" data-testid="transaction-log">
        {transactions.length === 0 ? (
          <p className="text-xs text-slate-400">No transactions yet</p>
        ) : (
          transactions.map((tx) => (
            <div key={tx.id} className="text-xs border-b border-slate-50 pb-1">
              <div className="flex justify-between items-center">
                <span className="text-slate-600">
                  {tx.buyer_id} ← {tx.seller_id}
                </span>
                <span className="font-data text-slate-900">
                  {tx.energy_kwh.toFixed(2)} kWh
                </span>
              </div>
              <div className="flex justify-between items-center text-slate-400">
                <span>@€{tx.price_per_kwh.toFixed(4)}/kWh</span>
                <span className="font-data">€{tx.total_cost.toFixed(2)}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

const WeatherPanel = ({ weather }) => {
  if (!weather) return null;
  
  return (
    <div className="metric-card p-4" data-testid="weather-panel">
      <div className="border-b border-slate-100 pb-2 mb-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">Weather - Reutlingen</h3>
      </div>
      
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {weather.ghi > 400 ? (
              <Sun className="w-5 h-5" style={{color: '#F59E0B'}} />
            ) : (
              <CloudRain className="w-5 h-5" style={{color: '#64748B'}} />
            )}
            <span className="text-sm text-slate-600">Solar Irradiation (GHI)</span>
          </div>
          <span className="font-data text-lg" style={{color: '#F59E0B'}}>
            {weather.ghi.toFixed(0)} W/m²
          </span>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-600">Temperature</span>
          <span className="font-data text-lg text-slate-900">
            {weather.temperature.toFixed(1)}°C
          </span>
        </div>
      </div>
    </div>
  );
};

const Dashboard = () => {
  const [state, setState] = useState(null);
  const [priceHistory, setPriceHistory] = useState([]);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const connectWebSocket = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_URL}/api/ws/simulation`);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setState(data);
      
      if (data.market) {
        setPriceHistory(prev => {
          const newHistory = [...prev, {
            tick: data.tick,
            price: data.market.current_price
          }];
          return newHistory.slice(-50);
        });
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
      reconnectTimeoutRef.current = setTimeout(() => {
        connectWebSocket();
      }, 3000);
    };
    
    wsRef.current = ws;
  };

  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleStart = async () => {
    try {
      await fetch(`${API}/simulation/start`, { method: 'POST' });
      toast.success('Simulation started');
    } catch (e) {
      toast.error('Failed to start simulation');
    }
  };

  const handlePause = async () => {
    try {
      await fetch(`${API}/simulation/pause`, { method: 'POST' });
      toast.success('Simulation paused');
    } catch (e) {
      toast.error('Failed to pause simulation');
    }
  };

  const handleReset = async () => {
    try {
      await fetch(`${API}/simulation/reset`, { method: 'POST' });
      setPriceHistory([]);
      
      const response = await fetch(`${API}/simulation/state`);
      const data = await response.json();
      setState(data);
      
      toast.success('Simulation reset');
    } catch (e) {
      toast.error('Failed to reset simulation');
    }
  };

  if (!state) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <Zap className="w-12 h-12 mx-auto mb-4 animate-pulse" style={{color: '#F59E0B'}} />
          <p className="text-sm text-slate-600">Connecting to simulation...</p>
        </div>
      </div>
    );
  }

  const totalSupply = state.agents.reduce((sum, a) => sum + a.current_solar_output_kw, 0);
  const totalDemand = state.agents.reduce((sum, a) => sum + a.consumption_kw, 0);

  return (
    <div className="max-w-[1600px] mx-auto p-6">
      <Toaster position="top-right" />
      
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-slate-900 mb-1">Solar Energy Trading Simulation</h1>
        <p className="text-sm text-slate-600">Agent-based microgrid with dynamic pricing • Reutlingen, Germany</p>
      </div>

      {/* Controls */}
      <div className="metric-card p-4 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              data-testid="start-button"
              onClick={handleStart}
              disabled={state.is_running}
              className="bg-slate-900 text-white hover:bg-slate-800 disabled:bg-slate-300 disabled:cursor-not-allowed px-4 py-2 rounded-sm uppercase text-xs tracking-wider font-bold flex items-center gap-2"
            >
              <Play className="w-3 h-3" />
              Start
            </button>
            <button
              data-testid="pause-button"
              onClick={handlePause}
              disabled={!state.is_running}
              className="border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 disabled:bg-slate-100 disabled:cursor-not-allowed px-4 py-2 rounded-sm uppercase text-xs tracking-wider font-bold flex items-center gap-2"
            >
              <Pause className="w-3 h-3" />
              Pause
            </button>
            <button
              data-testid="reset-button"
              onClick={handleReset}
              className="border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 px-4 py-2 rounded-sm uppercase text-xs tracking-wider font-bold flex items-center gap-2"
            >
              <RotateCcw className="w-3 h-3" />
              Reset
            </button>
          </div>
          
          <div className="flex items-center gap-6">
            <div className="text-right">
              <div className="text-xs text-slate-500 uppercase tracking-wide">Tick</div>
              <div className="font-data text-lg text-slate-900">{state.tick}</div>
            </div>
            <div className="text-right">
              <div className="text-xs text-slate-500 uppercase tracking-wide">Status</div>
              <div className="text-sm font-bold" style={{color: state.is_running ? '#10B981' : '#64748B'}}>
                {state.is_running ? 'RUNNING' : 'PAUSED'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Global Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="metric-card p-4" data-testid="market-price-card">
          <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Market Price</div>
          <div className="font-data text-2xl" style={{color: '#3B82F6'}}>
            €{state.market.current_price.toFixed(4)}/kWh
          </div>
        </div>
        
        <div className="metric-card p-4" data-testid="total-supply-card">
          <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Total Supply</div>
          <div className="font-data text-2xl" style={{color: '#10B981'}}>
            {totalSupply.toFixed(2)} kW
          </div>
        </div>
        
        <div className="metric-card p-4" data-testid="total-demand-card">
          <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Total Demand</div>
          <div className="font-data text-2xl" style={{color: '#EF4444'}}>
            {totalDemand.toFixed(2)} kW
          </div>
        </div>
        
        <div className="metric-card p-4" data-testid="active-agents-card">
          <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Active Agents</div>
          <div className="font-data text-2xl text-slate-900">
            {state.agents.length}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-[1fr_400px] gap-6">
        {/* Left: Agents Grid */}
        <div>
          <div className="mb-3">
            <h2 className="text-lg font-bold text-slate-900">Home Agents</h2>
          </div>
          <div className="simulation-grid">
            {state.agents.map(agent => (
              <AgentCard key={agent.id} agent={agent} />
            ))}
          </div>
        </div>

        {/* Right: Analytics */}
        <div className="space-y-4">
          <WeatherPanel weather={state.weather} />
          
          <div className="metric-card p-4">
            <div className="border-b border-slate-100 pb-2 mb-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">Market Price History</h3>
            </div>
            <MarketPriceChart priceHistory={priceHistory} />
          </div>
          
          <TransactionLog transactions={state.recent_transactions} />
        </div>
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;