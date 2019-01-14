import subprocess
import random
import os
import json
import pickle
import socket
import math
import uuid
import time


"""def make_factory(settings):
    def create_game_process(addr, port, nonce):
        env = os.environ.copy()
        env['MONSTERCARLO_DRIVER_ADDR'] = "localhost"
        env['MONSTERCARLO_DRIVER_PORT'] = str(15259)
        env['MONSTERCARLO_DRIVER_NONCE'] = nonce
        env['MONSTERCARLO_EXPERIMENT_SETTINGS'] = settings
        return subprocess.Popen(['./mlMonster2.app/Contents/MacOS/mlMonster2'], env=env)#,'-batchmode'],env=env) #your app name here
    return create_game_process"""

results = 0
with open("mcts_no_model_0.pickle", "rb") as f:
    results = pickle.load(f)

nonce = "12345"#str(uuid.uuid4())
s = socket.socket()
s.bind(('localhost', 15259))
s.listen(1)
addr, port = s.getsockname()

#my_process = make_factory("die trying")
#process = my_process(addr, port, nonce)
connection, _ = s.accept()
reader = connection.makefile('r')
writer = connection.makefile('w')
incoming_nonce = reader.readline()
assert incoming_nonce.strip() == nonce

start = time.time()
for i in range (1):
    k = 0;
    for result in results:
        print("run ", k)
        k += 1
        score = result["score"]
        if score == 0 :#or (k < 20):
            print("zero score")
            continue;
        tree_seed = result["random_seed"]
        path = result["path"]
        writer.write(json.dumps({'prefix': path, 'random_seed': tree_seed}))
        writer.write("\n")
        writer.flush()
        response_in = reader.readline()
        response = json.loads(response_in)
        got_path, got_score, got_blocks = response['path'], response['score'], response['game_sequence']#, response['random_seed']
        if got_path != path or result["score"] != got_score:# or result["blocks"] != got_blocks:
            print("disagreements!")
            print(result)
            print(response)
        else:
            print("all good!")
    #if tree_seed != got_seed:
    #    print("random seeds don't agree!")"""
    #print(result)
    #print(response)
stop = time.time()
duration = stop - start
print("Time taken: ", duration)
connection.shutdown(socket.SHUT_WR)
#process.wait()
    

print("********** ENDING?2 *************")

"""for experiment in range(1):
    result_1 = MonsterCarlo.run(
        make_factory("die_trying"), # your own setting specificatio here
        num_samples=100,
        num_workers=4,
        num_games = 12,
        callback=on_progress_1,
        UCT_constant = 150,
        terminal_treatment = "NONE",
        decision_limit = 10) # CUT_OFF will avoid traveling down the same paths
    results_var_1.append(result_1)
    file_name = "result_" + str(experiment) + ".picke" #any file name you choose
    with open(file_name, "wb") as f:
        pickle.dump(result_1,f) 
print("all done")"""