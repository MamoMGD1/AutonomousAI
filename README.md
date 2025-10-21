# 🚗 AutonomousAI — Simple Autonomous Vehicle Simulation

## 🧠 Introduction
**AutonomousAI** is a simplified artificial-intelligence simulation project developed for the *ISE315 – Introduction to Artificial Intelligence* course.  
It demonstrates how an autonomous vehicle can perceive its environment, make decisions, and move safely through a city map with **roads, traffic lights, pedestrians, and dynamic obstacles**.

The system focuses on **path-finding and real-time decision-making**, showing how classical AI algorithms (BFS, DFS, Dijkstra, Greedy, A*) can be used to plan optimal routes and adapt when the environment changes.

---

## 👥 For Collaborators

### 🗂️ Project Structure
```

AutonomousAI/
│
├── images/             # .png files for roads, cars, crosswalks, lights, etc.
│
├── world.py            # Main environment (heart of the simulation)
├── map.py              # Road & crosswalk logic + traffic lights
├── car.py              # Base car movement and lane logic
├── agent.py            # Smart car (inherits from Car) + decision making
├── pedestrian.py       # Pedestrian behavior and crossing control
├── algorithm.py        # Pathfinding algorithms (BFS, DFS, A*, Dijkstra, Greedy)
├── interface.py        # Game window, buttons, and info panel (Pygame)
├── main.py             # Entry point — runs the whole simulation
│
├── requirements.txt
├── .gitignore
└── README.md

```

---

### 🌍 `world.py` — The Core of Everything
`world.py` is the **central controller** that connects every other part of the project.  
It manages all simulation data and coordinates how each object interacts with the environment.

#### Responsibilities
- **Stores references** to all entities:
  - Map, roads, lights → from `map.py`
  - Cars & agent → from `car.py` / `agent.py`
  - Pedestrians → from `pedestrian.py`
- **Handles updates per frame**: moves vehicles, updates lights, triggers re-planning, checks collisions, etc.
- **Communicates with the interface**:
  - Sends visual states (positions, colors, etc.) to `interface.py`
  - Receives user actions (add car, add pedestrian, pause, resume, etc.)
- **Provides environment data** to other classes:
  - `car` and `agent` ask `world` for nearby lights, cars, or obstacles.
  - `algorithm` receives the map structure directly from `world`.

#### Simple Data Flow
```

interface.py  →  world.py  ←  map.py
↑
car.py / agent.py
↑
algorithm.py (path planning)
↑
pedestrian.py (obstacles)

````

Every class only needs to talk **to the world**, not directly to each other — keeping the code clean and easy to debug.

---

### 🧩 Development Tips
- Use **Pygame** for visualization.
- Keep every entity’s update inside its own `.update()` method.
- The `world` object should call these updates in each simulation tick.
- Avoid circular imports — if two classes need shared data, let the world mediate.

---

### ▶️ Running the Project
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the simulator:

   ```bash
   python main.py
   ```
3. Use the UI buttons to:

   * Add a car and a target,
   * Select an algorithm,
   * Start / Run the simulation,
   * Pause / Resume or add pedestrians dynamically.


