import socket
import json
import math
import uuid
import random
import time

from threading import Thread, Lock
from enum import Enum

class TerminalTreatment(Enum):
    CUT_OFF = 1
    NONE = 2

class Tree(object):
    
    def __init__(self, uct_const, terminal_treatment = TerminalTreatment.NONE, tree_seed = 0, decision_limit = 0):
        self.root = Node()
        self.samples = []
        self.best_score = 0
        self.best_score_history = []
        self.best_path = None
        self.rollout_durations = []
        self.latest_request = None
        self.node_count = 0
        self.uct_const = uct_const
        self.terminal_treatment = terminal_treatment
        self.tree_seed = tree_seed
        self.decision_limit = decision_limit
        self.game_sequence = ""
        
    def select_next_prefix_to_explore(self):
        
        if self.root.terminal:
            return {"prefix" : None}
        
        path = []
        current_node = self.root
        
        while True:           
            got_chosen = False 
            time_to_choose = False
            if self.decision_limit and current_node.visits > self.decision_limit:
                time_to_choose = True 
            if not current_node.children:
                if current_node.chosen:
                    path = None
                return {"prefix" : path, 
                        "terminal" : current_node.terminal, 
                        "score" : current_node.best_score}
            
            untried_children = []
            non_terminal_children = []
            
            for i in range(len(current_node.children)):
                if current_node.children[i] is None:
                    untried_children.append(i)
                elif current_node.children[i].chosen:
                    path.append({"a" : i, "c" : len(current_node.children)})
                    current_node = current_node.children[i]
                    got_chosen = True
                    break
                elif not current_node.children[i].terminal:
                    non_terminal_children.append(i)
            
            if got_chosen:
                continue
            if len(untried_children) > 0:
                child_index = random.choice(untried_children)
                path.append({"a" : child_index, "c" : len(current_node.children)})
                """if time_to_choose:
                    #current_node.children[child_index] = Node()
                    current_node.children[child_index].chosen = True"""
                return {"prefix" : path,
                        "terminal" : False}
            
            def ucb(child):
                return child.total_score / child.visits + math.sqrt(self.uct_const*math.log(current_node.visits)/child.visits)

            best_index = 0
            best_ucb = 0

            if self.terminal_treatment == TerminalTreatment.NONE:
                for i in range(len(current_node.children)):
                    child_ucb = ucb(current_node.children[i])
                    if child_ucb > best_ucb:
                        best_ucb = child_ucb
                        best_index = i

            elif self.terminal_treatment == TerminalTreatment.CUT_OFF:
                if len(non_terminal_children) > 0:
                    for i in non_terminal_children:
                        child_ucb = ucb(current_node.children[i])
                        if child_ucb > best_ucb:
                            best_ucb = child_ucb
                            best_index = i
                else:
                    return {"prefix" : path, 
                            "terminal" : True,
                            "score" : current_node.best_score}
           
            path.append({"a" : best_index, "c" : len(current_node.children)})
            if time_to_choose:
                current_node.children[best_index].chosen = True
            current_node = current_node.children[best_index]
    
    def update(self, path, score, duration = 0, terminal = False, game_sequence = ""):
        
        if self.game_sequence == "":
            self.game_sequence = game_sequence
        if self.terminal_treatment == TerminalTreatment.CUT_OFF and terminal:
            #marking nodes with all terminal children
            current_node = self.root
            for step in path:
                move = step["a"]
                num_moves = step["c"]
                assert num_moves == len(current_node.children)
                current_node = current_node.children[move]
            current_node.terminal = True
            return

        self.samples.append((path, score))
        self.rollout_durations.append(duration)
        
        current_node = self.root
        self.root.total_score += score
        self.root.visits += 1
        node_depth = 0
        
        for step in path:
            move = step["a"]
            num_moves = step["c"]
            assert move < num_moves
            node_depth += 1
            
            added_new = False
            
            if current_node.children:
                assert num_moves == len(current_node.children)
                if current_node.children[move] is None:
                    added_new = True
                    current_node.children[move] = Node()
                    self.node_count += 1
            else :
                added_new = True
                current_node.children = []
                for i in range(num_moves):                    
                    current_node.children.append(None)
                current_node.children[move] = Node()
                self.node_count += 1
            
            current_node = current_node.children[move]
            if node_depth == len(path):
                current_node.terminal = True
            current_node.total_score += score
            current_node.visits += 1
            if score > current_node.best_score:
                current_node.best_score = score
            if score < self.best_score and added_new:
                break 
        if terminal:
            current_node.terminal = True 

                
        if score >= self.best_score :
            self.best_score = score
            self.best_path = path            
        
        self.best_score_history.append(self.best_score)        
        return

class Node():
    
    def __init__(self):
        self.children = None
        self.visits = 0
        self.terminal = False
        self.total_score = 0
        self.best_score = 0
        self.chosen = False
    
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4)

def run(process_factory,
        num_samples=None,
        num_workers=1,
        num_games=None,
        callback=None,
        UCT_constant=2,
        decision_limit=0,
        terminal_treatment = None):

    tree = None
    results = []
    if terminal_treatment == "CUT_OFF":
        tree = Tree(UCT_constant, TerminalTreatment.CUT_OFF)
    else:
        tree = Tree(UCT_constant)
    num_samples_remaining = [num_samples]
    num_games_remaining = [num_games]
    lock = Lock()
    
    class RolloutWorker(Thread):
        def run(self):
            
            nonce = str(uuid.uuid4())
            
            s = socket.socket()
            s.bind(('localhost', 0))
            s.listen(1)
            addr, port = s.getsockname()
            
            process = process_factory(addr, port, nonce)
            connection, _ = s.accept()
            reader = connection.makefile('r')
            writer = connection.makefile('w')
            incoming_nonce = reader.readline()
            assert incoming_nonce.strip() == nonce
     
            interval = 0
            print_delay = 0

            while True:           
                with lock:
                    work_available = num_samples_remaining[0] is None or num_samples_remaining[0] > 0
        
                    if work_available:
                        path = tree.select_next_prefix_to_explore()
                        if path["prefix"] is None:
                            break
                        elif path["terminal"]: 
                            tree.update(path["prefix"],path["score"], terminal = True)
                            continue
                        if num_samples_remaining[0] is not None:
                            num_samples_remaining[0] -= 1
                    else:
                        break
 
                writer.write(json.dumps({'prefix': path["prefix"]}))
                writer.write("\n")
                writer.flush()
                
                start = time.time()

                result = reader.readline()
                if not result:
                    break

                stop = time.time()
                duration = stop - start
                response = json.loads(result)
                path, score = response['path'], response['score']
                
                
                with lock:
                    tree.update(path, score, duration)
                    if callback and print_delay >= 100:
                        print_delay = 0
                        callback(tree)
                    print_delay += 1

            connection.shutdown(socket.SHUT_WR)
            process.wait()

    class GameWorker(Thread):
        def run(self):
            print("started worker?")
            
            nonce = str(uuid.uuid4())
            s = socket.socket()
            s.bind(('localhost', 0))
            s.listen(1)
            addr, port = s.getsockname()
            process = process_factory(addr, port, nonce)
            connection, _ = s.accept()
            reader = connection.makefile('r')
            writer = connection.makefile('w')
            incoming_nonce = reader.readline()
            assert incoming_nonce.strip() == nonce
     
            interval = 0
            print_delay = 0

            while True:           
                with lock:
                    work_available = num_games_remaining[0] is None or num_games_remaining[0] > 0
                    if num_games_remaining[0] is not None:
                        num_games_remaining[0] -= 1
                    print(work_available, " ", num_games_remaining[0])
                    if not work_available:
                        print("should be quitting")
                        writer.write("\ndone")
                        writer.write("\n")
                        writer.flush()
                        break

                tree_seed = random.randint(0, 1000000)
                tree = Tree(UCT_constant,TerminalTreatment.NONE,tree_seed,decision_limit)
                while True:
                    path = tree.select_next_prefix_to_explore()
                    if path["prefix"] is None:
                        break
                    elif path["terminal"]: 
                        tree.update(path["prefix"],path["score"], terminal = True)
 
                    writer.write(json.dumps({'prefix': path["prefix"], 'random_seed': tree_seed}))
                    writer.write("\n")
                    writer.flush()
                    
                    start = time.time()

                    result = reader.readline()
                    if not result:
                        break

                    stop = time.time()
                    duration = stop - start
                    
                    response = json.loads(result)
                    path, score, game_sequence = response['path'], response['score'], response['game_sequence']
                    
                    tree.update(path, score, duration,game_sequence = game_sequence)
                    if callback and print_delay >= 100:
                        print_delay = 0
                        callback(tree)
                    print_delay += 1

                with lock:
                    #print(tree.game_sequence)
                    results.append({"path": tree.best_path, "random_seed": tree_seed,"score": tree.best_score,"blocks":tree.game_sequence})
            print("done working")
            connection.shutdown(socket.SHUT_WR)
            process.wait()
        
    workers = []
    for i in range(num_workers):
        #w = RolloutWorker()
        w = GameWorker()
        w.start()
        workers.append(w)
    print("workers done?")
    
    for w in workers:
        print("joining?")
        try:
            w.join()
        except KeyboardInterrupt:
            print("Interrupted! Telling workers to stop.")
            with lock:
                num_games_remaining[0] = 0
                #num_samples_remaining[0] = 0
            w.join()
    
    return results