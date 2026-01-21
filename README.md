/*
# Overview:
This project is an Autonomous Microgrid Energy Trading Platform designed for decentralized energy markets. It simulates a P2P (Peer-to-Peer) economy where 25 autonomous "Prosumer" agents trade solar energy in real-time based on supply and demand.
2. Technical Stack
 * Backend: Python 3.x for agent-based modeling and market logic.
 * Frontend: React.js with Tailwind CSS for real-time telemetry.
 * API: Integration with weather services to fetch real-time GHI (Global Horizontal Irradiance) data for Reutlingen, Germany.
3. Key Features
 * Dynamic Pricing Engine: Implements a Market Clearing Price (MCP) algorithm where prices fluctuate (e.g., €0.42/kWh) based on the local grid's supply/demand ratio.
 * Agent Intelligence: 25 independent agents manage their own PV production, battery State-of-Charge (SoC), and household consumption.
 * Physics-Based Modeling: Calculates solar yield using real-time irradiance and temperature coefficients to adjust for efficiency losses.
4. How to Run
 * Navigate to /backend and install dependencies: pip install -r requirements.txt.
 * Start the simulation server.
 * Navigate to /frontend, run npm install, and then npm start.ns

