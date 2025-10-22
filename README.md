# 🚗 AutonomousAI — Intelligent Vehicle Simulation

## 🧠 Introduction
**AutonomousAI** is a modular AI simulation project developed for the *ISE315 – Introduction to Artificial Intelligence* course.  
It visualizes how an autonomous vehicle can perceive its surroundings, follow traffic rules, and plan routes using classical AI algorithms such as **DFS, BFS, Dijkstra, Greedy Best-First, and A\***.

The goal is to create a miniature digital city where vehicles, pedestrians, and lights all coexist — showing how search algorithms and reactive decision-making work in real time.

---

## 👥 Project Overview
This project is developed **in series** by a team of 9 students.  
Each phase builds on the previous one to ensure smooth integration and stability.

---

### 🗓️ Development Phases

#### **Phase 1 – Map and Environment (Team 1)**
- Files: `map.py`, `/images`
- Tasks:
  - Build a complete map with roads, intersections, crosswalks, and optional buildings.
  - Implement traffic lights with countdowns and automatic state switching.
  - Provide a function callable from `main.py` to display the static map.
- Deliverable:
  - Running `main.py` should show the entire city map with animated traffic lights.

---

#### **Phase 2 – Vehicles (Team 2)**
- Files: `car.py`, `agent.py`
- Tasks:
  - Add moving “blue” cars that follow lanes, stop at red lights, and avoid collisions.
  - Add an *agent car* controlled temporarily with arrow keys.
  - Ensure both integrate smoothly with the existing map.
  - Implement anything written in `main.py`.

---

#### **Phase 3 – Pedestrians (Team 3)**
- File: `pedestrian.py`
- Tasks:
  - Add pedestrians who cross only at designated crosswalks.
  - Stop cars when pedestrians are passing.
  - Integrate natural pedestrian flow into the existing simulation.

---

#### **Phase 4 – User Interface (Team 4)**
- File: `interface.py`
- Tasks:
  - Add buttons and an information panel:
    - **Add Car**, **Add Pedestrian**, **Pause**, **Resume**, **Start**, **Run**
  - Display algorithm name, simulation status, and light timers.
  - Provide reset functionality while preserving start/end points.

---

#### **Phase 5 – Algorithms and Final Integration (1 Person)**
- File: `algorithm.py`
- Tasks:
  - Implement pathfinding algorithms: DFS, BFS, Greedy, A*, and Dijkstra.
  - Visualize search paths:
    - Yellow = exploration  
    - Green = final optimal route
  - Add automatic re-planning when a route becomes blocked.
- Deliverable:
  - Fully functioning interactive simulation where the agent drives autonomously using chosen algorithms.

---

## 🗂️ Repository Structure

```
AutonomousAI/
│
├── images/              # .png files for roads, cars, crosswalks, lights, etc.
│
├── map.py               # City layout (roads, intersections, crosswalks, lights)
├── car.py               # Blue cars following traffic rules
├── agent.py             # Smart agent car (inherits from car)
├── pedestrian.py        # Pedestrian logic and movement
├── algorithm.py         # Pathfinding algorithms
├── interface.py         # UI buttons, info screen, and visuals
├── main.py              # Main entry point (runs everything)
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🧩 Data Flow

```
main.py
├── map.py          → defines environment
├── car.py          → defines car behavior
├── agent.py        → intelligent car logic
├── pedestrian.py   → pedestrian control
├── algorithm.py    → pathfinding and route calculation
└── interface.py    → buttons, info, and rendering
```

Each file works independently but communicates through shared objects created in `main.py`.  
This will keep the code modular and avoid dependency conflicts.

---

## ▶️ Running the Project
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Launch the simulation:

   ```bash
   python main.py
   ```

3. Use the on-screen buttons to:

   * Add cars and pedestrians
   * Select an algorithm
   * Start / pause / resume the simulation

---

## 🧠 Tips for Contributors

* Every module must be self-contained: no cross-importing logic.
* Use consistent coordinate systems `(row, col)` across all files.
* All files should include a detailed docstring describing:

  * What data they expect to receive,
  * What data they output,
  * How `main.py` interacts with them.
* Always test integration through `main.py` before handing off to the next team.

