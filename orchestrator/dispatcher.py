# orchestrator/dispatcher.py

import time
from typing import Dict, Callable
from orchestrator.state import AgentState


EXECUTION_ORDER = {
    "knowledge_lookup": 1,
    "research_agent": 2,
    "image_generator": 3,
    "caption_generator": 4,
}


class Dispatcher:
    def __init__(self, subsystem_map: Dict[str, Callable]):
        self.subsystem_map = subsystem_map

    def execute(self, plan: dict, state: AgentState) -> AgentState:
        subsystems = plan.get("required_subsystems", [])

        subsystems = sorted(
            subsystems,
            key=lambda item: EXECUTION_ORDER.get(item["name"], 999)
        )

        state.logs.append(f"Executing {len(subsystems)} subsystems")

        subsystem_times = state.metrics.setdefault("subsystem_times_sec", {})
        selected_names = state.metrics.setdefault("subsystems_selected", [])
        plan_errors = 0

        for item in subsystems:
            name = item.get("name")

            if name not in self.subsystem_map:
                plan_errors += 1

                if "|" in name or "/" in name:
                    state.errors.append({
                        "agent": "dispatcher",
                        "error": (
                            f"Planner returned invalid combined subsystem name: '{name}'. "
                            "Fix SYSTEM_PROMPT in planner.py."
                        )
                    })
                else:
                    state.errors.append({
                        "agent": name,
                        "error": f"Unknown subsystem '{name}'"
                    })
                continue

            try:
                state.logs.append(f"Running {name}: {item.get('reason')}")

                start_time = time.perf_counter()
                state = self.subsystem_map[name](state)
                subsystem_times[name] = time.perf_counter() - start_time
                selected_names.append(name)

            except Exception as error:
                plan_errors += 1
                state.errors.append({
                    "agent": name,
                    "error": str(error)
                })

        state.metrics["plan_errors"] = (
            state.metrics.get("plan_errors", 0) + plan_errors
        )

        return state