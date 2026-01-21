from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional
import uuid
from datetime import datetime, timezone
import asyncio
import httpx
import random
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WeatherData(BaseModel):
    timestamp: datetime
    ghi: float
    temperature: float
    forecast_ghi: List[float]

class AgentState(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    solar_capacity_kw: float
    battery_capacity_kwh: float
    battery_level_kwh: float
    current_solar_output_kw: float
    consumption_kw: float
    money_balance: float
    total_energy_bought_kwh: float
    total_energy_sold_kwh: float
    status: str

class Transaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime
    buyer_id: str
    seller_id: str
    energy_kwh: float
    price_per_kwh: float
    total_cost: float

class MarketState(BaseModel):
    timestamp: datetime
    current_price: float
    total_supply_kw: float
    total_demand_kw: float
    base_price: float

class SimulationState(BaseModel):
    is_running: bool
    speed: int
    tick: int
    weather: WeatherData
    market: MarketState
    agents: List[AgentState]
    recent_transactions: List[Transaction]

class HomeAgent:
    def __init__(self, agent_id: str, name: str):
        self.id = agent_id
        self.name = name
        self.solar_capacity_kw = random.uniform(3.0, 8.0)
        self.battery_capacity_kwh = random.uniform(8.0, 15.0)
        self.battery_level_kwh = random.uniform(4.0, 10.0)
        self.current_solar_output_kw = 0.0
        self.consumption_kw = random.uniform(0.5, 2.5)
        self.money_balance = random.uniform(80.0, 150.0)
        self.total_energy_bought_kwh = 0.0
        self.total_energy_sold_kwh = 0.0
        self.forecast_ghi = []
        
    def update_solar_output(self, ghi: float):
        efficiency = 0.18
        self.current_solar_output_kw = (ghi / 1000.0) * self.solar_capacity_kw * efficiency
        
    def update_consumption(self):
        hour = datetime.now().hour
        if 6 <= hour < 9 or 17 <= hour < 22:
            base = random.uniform(1.5, 3.0)
        elif 9 <= hour < 17:
            base = random.uniform(0.5, 1.5)
        else:
            base = random.uniform(0.3, 0.8)
        self.consumption_kw = base + random.uniform(-0.2, 0.2)
        
    def forecast_tomorrow_solar(self, forecast_ghi: List[float]) -> float:
        self.forecast_ghi = forecast_ghi
        avg_ghi = sum(forecast_ghi) / len(forecast_ghi) if forecast_ghi else 400
        efficiency = 0.18
        return (avg_ghi / 1000.0) * self.solar_capacity_kw * efficiency
        
    def decide_action(self, market_price: float, tick: int) -> Dict:
        net_energy = self.current_solar_output_kw - self.consumption_kw
        battery_pct = self.battery_level_kwh / self.battery_capacity_kwh
        
        forecast_solar_avg = self.forecast_tomorrow_solar(self.forecast_ghi)
        
        if net_energy > 0:
            if battery_pct < 0.8:
                charge_amount = min(net_energy * 0.1, self.battery_capacity_kwh - self.battery_level_kwh)
                self.battery_level_kwh += charge_amount
                net_energy -= charge_amount
                
            if net_energy > 0.1 and (market_price > 0.15 or battery_pct > 0.7):
                return {'action': 'sell', 'amount': net_energy * 0.1, 'price': market_price}
        else:
            deficit = abs(net_energy)
            
            if battery_pct > 0.2 and deficit < self.battery_level_kwh:
                discharge_amount = min(deficit * 0.1, self.battery_level_kwh * 0.3)
                self.battery_level_kwh -= discharge_amount
                deficit -= discharge_amount
                
            if deficit > 0.05:
                if forecast_solar_avg > self.consumption_kw and market_price < 0.25:
                    return {'action': 'buy', 'amount': deficit * 0.1, 'price': market_price}
                elif battery_pct < 0.15 or market_price < 0.18:
                    return {'action': 'buy', 'amount': deficit * 0.1, 'price': market_price}
                    
        return {'action': 'hold', 'amount': 0, 'price': 0}
        
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'solar_capacity_kw': round(self.solar_capacity_kw, 2),
            'battery_capacity_kwh': round(self.battery_capacity_kwh, 2),
            'battery_level_kwh': round(self.battery_level_kwh, 2),
            'current_solar_output_kw': round(self.current_solar_output_kw, 2),
            'consumption_kw': round(self.consumption_kw, 2),
            'money_balance': round(self.money_balance, 2),
            'total_energy_bought_kwh': round(self.total_energy_bought_kwh, 2),
            'total_energy_sold_kwh': round(self.total_energy_sold_kwh, 2),
            'status': self.get_status()
        }
        
    def get_status(self) -> str:
        battery_pct = self.battery_level_kwh / self.battery_capacity_kwh
        if battery_pct > 0.7:
            return 'surplus'
        elif battery_pct < 0.3:
            return 'deficit'
        return 'balanced'

class EnergyMarket:
    def __init__(self):
        self.base_price = 0.20
        self.current_price = self.base_price
        self.total_supply_kw = 0.0
        self.total_demand_kw = 0.0
        self.price_history = []
        
    def update_price(self, total_supply: float, total_demand: float):
        self.total_supply_kw = total_supply
        self.total_demand_kw = total_demand
        
        if total_supply > 0:
            supply_demand_ratio = total_demand / total_supply
        else:
            supply_demand_ratio = 2.0
            
        price_multiplier = 0.5 + (supply_demand_ratio * 0.8)
        price_multiplier = max(0.3, min(price_multiplier, 3.0))
        
        self.current_price = self.base_price * price_multiplier
        self.current_price = round(self.current_price, 4)
        
        self.price_history.append({
            'timestamp': datetime.now(timezone.utc),
            'price': self.current_price
        })
        
        if len(self.price_history) > 100:
            self.price_history = self.price_history[-100:]
            
    def get_state(self) -> Dict:
        return {
            'current_price': self.current_price,
            'total_supply_kw': round(self.total_supply_kw, 2),
            'total_demand_kw': round(self.total_demand_kw, 2),
            'base_price': self.base_price,
            'timestamp': datetime.now(timezone.utc)
        }

class Simulation:
    def __init__(self):
        self.agents: List[HomeAgent] = []
        self.market = EnergyMarket()
        self.is_running = False
        self.speed = 1
        self.tick = 0
        self.transactions: List[Dict] = []
        self.weather_data = None
        self.websocket_connections: List[WebSocket] = []
        self.initialize_agents()
        
    def initialize_agents(self):
        for i in range(25):
            agent_id = f"home_{i+1:03d}"
            name = f"Home {i+1}"
            self.agents.append(HomeAgent(agent_id, name))
            
    async def fetch_weather(self):
        lat, lon = 48.4914, 9.2103
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = "https://api.open-meteo.com/v1/forecast"
                params = {
                    'latitude': lat,
                    'longitude': lon,
                    'hourly': 'shortwave_radiation,temperature_2m',
                    'forecast_days': 2,
                    'timezone': 'Europe/Berlin'
                }
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                current_hour = datetime.now().hour
                ghi_values = data['hourly']['shortwave_radiation']
                current_ghi = ghi_values[current_hour] if current_hour < len(ghi_values) else 0
                
                forecast_ghi = ghi_values[current_hour:current_hour+24] if current_hour+24 < len(ghi_values) else ghi_values[current_hour:]
                
                temp_values = data['hourly']['temperature_2m']
                current_temp = temp_values[current_hour] if current_hour < len(temp_values) else 15
                
                self.weather_data = {
                    'timestamp': datetime.now(timezone.utc),
                    'ghi': float(current_ghi),
                    'temperature': float(current_temp),
                    'forecast_ghi': [float(x) for x in forecast_ghi]
                }
                
                return self.weather_data
        except Exception as e:
            logger.error(f"Weather fetch error: {e}")
            self.weather_data = {
                'timestamp': datetime.now(timezone.utc),
                'ghi': 600.0,
                'temperature': 15.0,
                'forecast_ghi': [400.0] * 24
            }
            return self.weather_data
            
    async def simulation_loop(self):
        while True:
            if self.is_running:
                await self.tick_simulation()
                await asyncio.sleep(2.0 / self.speed)
            else:
                await asyncio.sleep(0.5)
                
    async def tick_simulation(self):
        self.tick += 1
        
        if self.tick % 10 == 0:
            await self.fetch_weather()
            
        if not self.weather_data:
            await self.fetch_weather()
            
        for agent in self.agents:
            agent.update_solar_output(self.weather_data['ghi'])
            agent.update_consumption()
            agent.forecast_tomorrow_solar(self.weather_data['forecast_ghi'])
            
        actions = []
        for agent in self.agents:
            action = agent.decide_action(self.market.current_price, self.tick)
            if action['action'] != 'hold':
                actions.append({'agent': agent, 'action': action})
                
        buyers = [a for a in actions if a['action']['action'] == 'buy']
        sellers = [a for a in actions if a['action']['action'] == 'sell']
        
        total_supply = sum(a['action']['amount'] for a in sellers)
        total_demand = sum(a['action']['amount'] for a in buyers)
        
        self.market.update_price(total_supply, total_demand)
        
        new_transactions = []
        for buyer_action in buyers:
            for seller_action in sellers:
                if buyer_action['action']['amount'] > 0 and seller_action['action']['amount'] > 0:
                    trade_amount = min(buyer_action['action']['amount'], seller_action['action']['amount'])
                    price = self.market.current_price
                    cost = trade_amount * price
                    
                    buyer_action['agent'].money_balance -= cost
                    buyer_action['agent'].total_energy_bought_kwh += trade_amount
                    seller_action['agent'].money_balance += cost
                    seller_action['agent'].total_energy_sold_kwh += trade_amount
                    
                    buyer_action['action']['amount'] -= trade_amount
                    seller_action['action']['amount'] -= trade_amount
                    
                    transaction = {
                        'id': str(uuid.uuid4()),
                        'timestamp': datetime.now(timezone.utc),
                        'buyer_id': buyer_action['agent'].id,
                        'seller_id': seller_action['agent'].id,
                        'energy_kwh': round(trade_amount, 2),
                        'price_per_kwh': round(price, 4),
                        'total_cost': round(cost, 2)
                    }
                    new_transactions.append(transaction)
                    
        self.transactions.extend(new_transactions)
        if len(self.transactions) > 50:
            self.transactions = self.transactions[-50:]
            
        await self.broadcast_state()
        
    async def broadcast_state(self):
        state = self.get_state()
        state_json = json.dumps(state, default=str)
        
        disconnected = []
        for ws in self.websocket_connections:
            try:
                await ws.send_text(state_json)
            except:
                disconnected.append(ws)
                
        for ws in disconnected:
            self.websocket_connections.remove(ws)
            
    def get_state(self) -> Dict:
        return {
            'is_running': self.is_running,
            'speed': self.speed,
            'tick': self.tick,
            'weather': self.weather_data,
            'market': self.market.get_state(),
            'agents': [agent.to_dict() for agent in self.agents],
            'recent_transactions': self.transactions[-20:]
        }

simulation = Simulation()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(simulation.simulation_loop())
    await simulation.fetch_weather()

@api_router.get("/simulation/state")
async def get_simulation_state():
    return simulation.get_state()

@api_router.post("/simulation/start")
async def start_simulation():
    simulation.is_running = True
    return {"status": "started"}

@api_router.post("/simulation/pause")
async def pause_simulation():
    simulation.is_running = False
    return {"status": "paused"}

@api_router.post("/simulation/reset")
async def reset_simulation():
    simulation.is_running = False
    simulation.tick = 0
    simulation.transactions = []
    simulation.agents = []
    simulation.initialize_agents()
    await simulation.fetch_weather()
    return {"status": "reset"}

@api_router.post("/simulation/speed")
async def set_speed(speed: int):
    simulation.speed = max(1, min(speed, 5))
    return {"speed": simulation.speed}

@api_router.websocket("/ws/simulation")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    simulation.websocket_connections.append(websocket)
    
    try:
        state = simulation.get_state()
        await websocket.send_text(json.dumps(state, default=str))
        
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in simulation.websocket_connections:
            simulation.websocket_connections.remove(websocket)

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()