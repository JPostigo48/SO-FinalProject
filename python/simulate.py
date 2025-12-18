import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

@dataclass
class Task:
    pid: int
    nombre: str
    t_llegada: int
    burst: int
    utime: int
    stime: int
    cpu_total: int
    muestras: int
    estado: str

    remaining: int = field(init=False)
    start_time: Optional[int] = field(default=None, init=False)
    finish_time: Optional[int] = field(default=None, init=False)
    context_switches: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self.remaining = self.burst


@dataclass
class TimelineSegment:
    pid: int
    start: int
    end: int

def parse_stat_file(pid: str) -> Tuple[str, int, int, str]:
    try:
        with open(f"/proc/{pid}/stat", "r", encoding="utf-8", errors="ignore") as f:
            data = f.read().split()
        comm = data[1].strip("()")
        state = data[2]
        utime = int(data[13])
        stime = int(data[14])
        return comm, utime, stime, state
    except Exception:
        raise


def sample_processes(num_procs: int, sample_interval: float = 0.1) -> List[Task]:
    tasks: List[Task] = []
    observed: Dict[int, Tuple[str, int, int, str]] = {}
    arrival_index: Dict[int, int] = {}

    sample_count = 0
    while len(tasks) < num_procs:
        current: Dict[int, Tuple[str, int, int, str]] = {}
        for pid_str in os.listdir("/proc"):
            if not pid_str.isdigit():
                continue
            pid = int(pid_str)
            try:
                comm, utime, stime, state = parse_stat_file(pid_str)
            except Exception:
                continue
            current[pid] = (comm, utime, stime, state)
            if pid not in arrival_index:
                arrival_index[pid] = sample_count
        time.sleep(sample_interval)
        for pid, (comm, utime0, stime0, state0) in current.items():
            if len(tasks) >= num_procs:
                break
            try:
                comm2, utime1, stime1, state1 = parse_stat_file(str(pid))
            except Exception:
                continue
            if comm.startswith("kworker") or comm.startswith("rcu") or comm.startswith("kthreadd"):
                continue
            if state1 == 'I':
                continue
            delta = (utime1 + stime1) - (utime0 + stime0)
            if delta <= 0:
                continue
            if any(t.pid == pid for t in tasks):
                continue
            t_llegada = arrival_index.get(pid, sample_count)
            task = Task(
                pid=pid,
                nombre=comm,
                t_llegada=t_llegada,
                burst=delta,
                utime=utime1,
                stime=stime1,
                cpu_total=utime1 + stime1,
                muestras=2,
                estado=state1,
            )
            tasks.append(task)
        sample_count += 1
    tasks.sort(key=lambda x: (x.t_llegada, x.pid))
    return tasks

def simulate_rr(tasks: List[Task], quantum: int) -> Tuple[List[TimelineSegment], List[Task], Dict[str, float]]:
    from copy import deepcopy
    ready = deepcopy(tasks)
    for t in ready:
        t.remaining = t.burst
        t.start_time = None
        t.finish_time = None
        t.context_switches = 0
    timeline: List[TimelineSegment] = []
    time_now = 0
    ready.sort(key=lambda x: (x.t_llegada, x.pid))
    queue: List[Task] = []
    queue.extend(ready)
    context_switches = 0
    while queue:
        task = queue.pop(0)
        if task.start_time is None:
            task.start_time = time_now
        run_time = min(quantum, task.remaining)
        start = time_now
        time_now += run_time
        end = time_now
        timeline.append(TimelineSegment(task.pid, start, end))
        task.remaining -= run_time
        if task.remaining <= 0:
            task.finish_time = time_now
        else:
            task.context_switches += 1
            context_switches += 1
            queue.append(task)
    finished_tasks = ready
    total_wait = 0
    total_turnaround = 0
    total_response = 0
    n = len(finished_tasks)
    for t in finished_tasks:
        t_wait = (t.finish_time or 0) - t.t_llegada - t.burst
        t_turn = (t.finish_time or 0) - t.t_llegada
        t_resp = (t.start_time or 0) - t.t_llegada
        total_wait += t_wait
        total_turnaround += t_turn
        total_response += t_resp
    total_time = timeline[-1].end if timeline else 0
    throughput = n / total_time if total_time > 0 else 0
    metrics = {
        "espera_promedio": total_wait / n if n else 0,
        "turnaround_promedio": total_turnaround / n if n else 0,
        "finalizacion_total": total_time,
        "throughput": throughput,
        "respuesta_promedio": total_response / n if n else 0,
        "context_switches": context_switches,
        "cpu_idle_time": 0 
    }
    return timeline, finished_tasks, metrics


def simulate_srtf(tasks: List[Task]) -> Tuple[List[TimelineSegment], List[Task], Dict[str, float]]:
    from copy import deepcopy
    ready = deepcopy(tasks)
    for t in ready:
        t.remaining = t.burst
        t.start_time = None
        t.finish_time = None
        t.context_switches = 0
    timeline: List[TimelineSegment] = []
    time_now = 0
    context_switches = 0
    remaining_tasks = [t for t in ready]
    current_task: Optional[Task] = None
    while any(t.remaining > 0 for t in remaining_tasks):
        candidates = [t for t in remaining_tasks if t.remaining > 0]
        if not candidates:
            time_now += 1
            continue
        next_task = min(candidates, key=lambda x: x.remaining)
        if current_task and current_task.pid != next_task.pid:
            context_switches += 1
            next_task.context_switches += 1
        if next_task.start_time is None:
            next_task.start_time = time_now
        start = time_now
        time_now += 1
        next_task.remaining -= 1
        end = time_now
        timeline.append(TimelineSegment(next_task.pid, start, end))
        current_task = next_task
        if next_task.remaining == 0:
            next_task.finish_time = time_now
    n = len(ready)
    total_wait = 0
    total_turnaround = 0
    total_response = 0
    for t in ready:
        t_wait = (t.finish_time or 0) - t.t_llegada - t.burst
        t_turn = (t.finish_time or 0) - t.t_llegada
        t_resp = (t.start_time or 0) - t.t_llegada
        total_wait += t_wait
        total_turnaround += t_turn
        total_response += t_resp
    total_time = timeline[-1].end if timeline else 0
    throughput = n / total_time if total_time > 0 else 0
    metrics = {
        "espera_promedio": total_wait / n if n else 0,
        "turnaround_promedio": total_turnaround / n if n else 0,
        "finalizacion_total": total_time,
        "throughput": throughput,
        "respuesta_promedio": total_response / n if n else 0,
        "context_switches": context_switches,
        "cpu_idle_time": 0  # no idle time assumed
    }
    return timeline, ready, metrics

def main(argv: List[str]) -> None:
    if len(argv) < 2:
        print("Usage: simulate.py <num_processes> [quantum]", file=sys.stderr)
        sys.exit(1)
    try:
        num_procs = int(argv[1])
    except ValueError:
        print("Invalid number of processes", file=sys.stderr)
        sys.exit(1)
    quantum = 10
    if len(argv) >= 3:
        try:
            quantum = int(argv[2])
        except ValueError:
            pass
    tasks = sample_processes(num_procs)
    timeline_rr, finished_rr, metrics_rr = simulate_rr(tasks, quantum)
    timeline_srtf, finished_srtf, metrics_srtf = simulate_srtf(tasks)
    procesos_entrada = [
        {
            "pid": t.pid,
            "nombre": t.nombre,
            "t_llegada": t.t_llegada,
            "utime": t.utime,
            "stime": t.stime,
            "cpu_total": t.cpu_total,
            "burst_obs": t.burst,
            "muestras": t.muestras,
            "estado": t.estado,
        }
        for t in tasks
    ]
    def serialize_finished(finished_list: List[Task]) -> List[Dict[str, object]]:
        res = []
        for t in finished_list:
            res.append({
                "pid": t.pid,
                "nombre": t.nombre,
                "t_llegada": t.t_llegada,
                "burst": t.burst,
                "t_inicio": t.start_time,
                "t_fin": t.finish_time,
                "turnaround": (t.finish_time or 0) - t.t_llegada,
                "waiting_time": (t.finish_time or 0) - t.t_llegada - t.burst,
                "response_time": (t.start_time or 0) - t.t_llegada,
                "n_contextos": t.context_switches,
            })
        return res
    def serialize_timeline(tl: List[TimelineSegment]) -> List[Dict[str, int]]:
        return [ { "pid": seg.pid, "inicio": seg.start, "fin": seg.end } for seg in tl ]
    output = {
        "procesos_entrada": procesos_entrada,
        "rr": {
            "timeline": serialize_timeline(timeline_rr),
            "procesos_salida": serialize_finished(finished_rr),
            "metricas": metrics_rr,
        },
        "srtf": {
            "timeline": serialize_timeline(timeline_srtf),
            "procesos_salida": serialize_finished(finished_srtf),
            "metricas": metrics_srtf,
        },
    }
    json.dump(output, sys.stdout)


if __name__ == "__main__":
    main(sys.argv)