import MonsterCarlo
import subprocess
import random
import os
import json
import pickle

def make_factory(settings):
    def create_game_process(addr, port, nonce):
        env = os.environ.copy()
        env['MONSTERCARLO_DRIVER_ADDR'] = addr
        env['MONSTERCARLO_DRIVER_PORT'] = str(port)
        env['MONSTERCARLO_DRIVER_NONCE'] = nonce
        env['MONSTERCARLO_EXPERIMENT_SETTINGS'] = settings
        return subprocess.Popen(['./mlMonster2.app/Contents/MacOS/mlMonster2'], env=env)#,'-batchmode'],env=env) #your app name here
    return create_game_process

def on_progress_1(tree):
    print(".",end='') # do what you want here

print("running experiment")

results_var_1 = []

for experiment in range(1):
    result_1 = MonsterCarlo.run(
        make_factory("die_trying"), # your own setting specificatio here
        num_samples=100,
        num_workers=4,
        num_games = 8,
        callback=on_progress_1,
        UCT_constant = 150,
        terminal_treatment = "NONE",
        decision_limit = 10) # CUT_OFF will avoid traveling down the same paths
    results_var_1.append(result_1)
    print(" writing results?")
    file_name = "new_result_" + str(experiment) + ".picke" #any file name you choose
    with open(file_name, "wb") as f:
        pickle.dump(result_1,f) 
print("all done")