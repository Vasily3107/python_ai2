import numpy as np
import pandas as pd
from sqlite3 import connect as sqlconnect
from os import system
from config import MAP_PATH

class TrafficType:
    LOW  = 0
    MID  = 1
    HIGH = 2

class RoadDifficulty:
    LOW  = 0
    MID  = 1
    HIGH = 2

cost_multiplier = {
    0: 0.8,
    1: 1.0,
    2: 1.2
}

class Vertex():
    total = 0

    def __init__(self, location_type: str, adjacent_edges: list = []):
        self.type = location_type.lower()
        self.edges = [] + adjacent_edges

        self.dist = float('inf')
        self.visited = False
        self.prev = None
        self.edge_to_next = None

        self.id = Vertex.total
        Vertex.total += 1

    def __repr__(self):
        return f't={self.type.upper()} d={self.dist} v={self.visited} e={self.edges}'

class Edge():
    def __init__(self, to: Vertex, distance_km: float, time_min: float, traffic: TrafficType, difficulty: RoadDifficulty):
        self.to = to
        self.dist = distance_km
        self.time = time_min
        self.traffic = traffic
        self.difficulty = difficulty
        self.cost = distance_km * cost_multiplier[traffic] * cost_multiplier[difficulty]

    def __repr__(self):
        return f'->{self.to.type.upper()} ({self.dist}, {self.time}, {self.traffic}, {self.difficulty})'
    
class Route():
    def __init__(self, start, target, route, dist, time, actual_time):
        self.start = start
        self.target = target
        self.route = route
        self.dist = dist
        self.time = time
        self.actual_time = actual_time

    def __iter__(self):
        yield self.start 
        yield self.target
        yield self.route 
        yield self.dist
        yield self.time
        yield self.actual_time

    def __getitem__(self, index):
        return list(self.__dict__.values())[index]

locations = {
    'a': 'Center',
    'b': 'University',
    'c': 'Hospital',
    'd': 'Park',
    'e': 'Railway Station',
    'f': 'Shopping Mall',
    'g': 'Airport'
}


MAP = pd.read_csv(MAP_PATH)
MATRIX: list[Vertex] = []
def init_matrix():
    global MAP, MATRIX
    MATRIX = [Vertex(i) for i in set(MAP['v1'].unique()) | set(MAP['v2'].unique())]
    for v in MATRIX:
        for row in MAP[MAP['v1'] == v.type].itertuples():
            v.edges.append(Edge(
                next((i for i in MATRIX if i.type == row.v2)),
                *(row.dist, row.time, row.traffic, row.difficulty)
            ))

def dijkstra(start: str, target: str) -> list[Vertex]:
    global MAP, MATRIX

    next((i for i in MATRIX if i.type == start)).dist = 0

    while len([i for i in MATRIX if not i.visited]):

        current = min((i for i in MATRIX if not i.visited), key = lambda i: i.dist)
        if current.type == target: break

        for edge in current.edges:
            if edge.to.dist > current.dist + edge.cost:
                edge.to.dist = current.dist + edge.cost
                edge.to.prev = current
                current.edge_to_next = edge

        current.visited = True

    path: list[Vertex] = []
    current = next((i for i in MATRIX if i.type == target))
    while current is not None:
        path.append(current)
        current = current.prev
    return path[::-1]

def pretty_print_table(headers: list, data: list[Route], is_custom_object_datatype: bool = True):
    l = np.array(data)
    q = []
    for i in range(len(headers)):
        q.append(max(
            len(headers[i]),
            len(str(max(l, key=lambda e: len(str(e[i])))[i]))
        ))
    for i, e in enumerate(headers):
        print(end=str(e).ljust(q[i]) + (' | ' if i < len(headers)-1 else '\n'))
    for row in l:
        for i, e in enumerate(row.__dict__.values() if is_custom_object_datatype else row):
            print(end=str(e).ljust(q[i]) + (' | ' if i < len(headers)-1 else '\n'))


conn = sqlconnect('navigation.db')
cur = conn.cursor()
cur.execute('''
CREATE TABLE IF NOT EXISTS routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start TEXT,
    target TEXT,
    route TEXT,
    dist_km REAL,
    time_min REAL,
    actual_time REAL
)''')
conn.commit()

def cls(): system('cls')
def wait(): input('\nPress "ENTER" to continue...')
while True:
    cls()
    init_matrix()
    print('Main menu:')
    print(' 1 - Find shortest route')
    print(' 2 - View route history')
    print(' 3 - Statistics')
    print(' 0 - Exit \n')

    match choice := input('Enter choice: '):
        case '1':
            cls()
            print('Map locations:')

            for i in MATRIX:
                print(f' {i.type.upper()} - {locations[i.type[0].lower()]} ' + (i.type[1:] if len(i.type) > 1 else ''))
            print()

            while (v1 := input('Enter start location (type "/back" to return): ').lower()) not in (i.type for i in MATRIX) and v1 not in ('/back', ''):
                print(f'ERROR: Invalid location option "{v1}" \n')
            if v1 in ('/back', ''): continue

            while (v2 := input('Enter target location (type "/back" to return): ').lower()) not in (i.type for i in MATRIX) or v2 == v1 and v2 not in ('/back', ''):
                print(f'ERROR: Invalid location option "{v2}" (Can\'t type start location again) \n')
            if v2 == ('/back', ''): continue

            path: list[Vertex] = dijkstra(v1, v2)
            cls()
            print(end=f'Route from "{v1}" to "{v2}": ')
            for i in path[:-1]: print(end=f'{i.type} -> ')
            print(path[-1].type + '\n')

            print(f'Distance (km): {(d:=sum((i.edge_to_next.dist for i in path[:-1])))}')
            print(f'   Time (min): {(t:=sum((i.edge_to_next.time for i in path[:-1])))}\n')

            def is_valid_positive_float(x: str) -> bool:
                import math
                try: val = float(x)
                except: return False
                if math.isnan(val) or math.isinf(val) or val <= 0 or 'e' in x.lower():
                    return False
                return True
            while not is_valid_positive_float(actual_time := input('Enter actual time in minutes: ')):
                print('ERROR: Not a valid number. Please enter a positive floating point number. \n')

            try: cur.execute('INSERT INTO routes (start, target, route, dist_km, time_min, actual_time) VALUES (?, ?, ?, ?, ?, ?)',
                             (v1, v2, '->'.join(i.type for i in path), d, t, actual_time))
            except: conn.rollback()
            conn.commit()
            wait()

        case '2':
            cls()
            cur.execute('SELECT * FROM routes')
            rows = [Route(*i[1:]) for i in cur.fetchall()]
            if not len(rows):
                print('No routes yet...')
                wait()
                continue
            pretty_print_table(['start', 'target', 'route', 'distance (km)', 'time (min)', 'actual time (min)'], rows)
            wait()

        case '3':
            cls()
            cur.execute('SELECT * FROM routes')
            rows = [Route(*i[1:]) for i in cur.fetchall()]

            fast = min(rows, key=lambda i: i.time)
            slow = max(rows, key=lambda i: i.time)

            print(f'Fastest route: {fast.route} ({fast.time} minutes)')
            print(f'Slowest route: {slow.route} ({slow.time} minutes)\n')

            counts = []
            for i in set(i.route for i in rows):
                counts.append([i, sum(1 for r in rows if r.route == i)])

            counts.sort(key=lambda i: i[-1], reverse=True)
            print('Top 10 most polular routes:')

            pretty_print_table(['Place #', 'Route', 'Times'], list((i, *e) for i, e in enumerate(counts, start=1)), False)
            wait()

        case 'cleardb':
            cur.execute('DELETE FROM routes')
            conn.commit()
        case '0':
            cls()
            conn.close()
            print('Closed')
            exit()
        case _:
            cls()
            print(f'ERROR: Invalid option: "{choice}"')
            wait()