
# _________________________________ Library _________________________________

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import random
import itertools
import time
import doctest
import copy
import wandb
import datetime

from collections import defaultdict
from tqdm import tqdm
from collections import deque

import NFSP_Leduc_Poker_trainer
import NFSP_Leduc_Poker_supervised_learning
import NFSP_Leduc_Poker_reinforcement_learning
import NFSP_Leduc_Poker_generate_data


# _________________________________ config _________________________________

config = dict(
  random_seed = [42, 1000, 10000][0],
  iterations = 10**7,
  num_players = 2,
  wandb_save = [True, False][0],


  #train
  eta = 0.1,
  memory_size_rl = 2*(10**5),
  memory_size_sl = 2*(10**6),

  #sl
  sl_hidden_units_num= 64,
  sl_lr = 0.001,
  sl_epochs = 2,
  sl_sampling_num =128,

  #rl
  rl_hidden_units_num= 64,
  rl_lr = 0.1,
  rl_epochs = 2,
  rl_sampling_num = 128,
  rl_gamma = 1.0,
  rl_tau = 0.1,
  rl_update_frequency = 300,
  sl_algo = ["cnt", "mlp"][1],
  rl_algo = ["dfs", "dqn", "ddqn"][1]
)



if config["wandb_save"]:
  wandb.init(project="Leduc_Poker_{}players".format(config["num_players"]), name="{}_{}_NFSP".format(config["rl_algo"], config["sl_algo"]))
  wandb.config.update(config)
  wandb.define_metric("exploitability", summary="last")
  wandb.define_metric("avg_utility", summary="last")


# _________________________________ train _________________________________

leduc_trainer = NFSP_Leduc_Poker_trainer.LeducTrainer(
  random_seed = config["random_seed"],
  train_iterations = config["iterations"],
  num_players= config["num_players"],
  wandb_save = config["wandb_save"]
  )


leduc_RL = NFSP_Leduc_Poker_reinforcement_learning.ReinforcementLearning(
  random_seed = config["random_seed"],
  train_iterations = config["iterations"],
  num_players= config["num_players"],
  hidden_units_num = config["rl_hidden_units_num"],
  lr = config["rl_lr"],
  epochs = config["rl_epochs"],
  sampling_num = config["rl_sampling_num"],
  gamma = config["rl_gamma"],
  tau = config["rl_tau"],
  update_frequency = config["rl_update_frequency"],
  leduc_trainer_for_rl = leduc_trainer
  )




leduc_SL = NFSP_Leduc_Poker_supervised_learning.SupervisedLearning(
  random_seed = config["random_seed"],
  train_iterations = config["iterations"],
  num_players= config["num_players"],
  hidden_units_num= config["sl_hidden_units_num"],
  lr = config["sl_lr"],
  epochs = config["sl_epochs"],
  sampling_num = config["sl_sampling_num"],
  leduc_trainer_for_sl = leduc_trainer
  )




leduc_GD = NFSP_Leduc_Poker_generate_data.GenerateData(
  random_seed = config["random_seed"],
  num_players= config["num_players"],
  leduc_trainer_for_gd= leduc_trainer
  )


leduc_trainer.train(
  eta = config["eta"],
  memory_size_rl = config["memory_size_rl"],
  memory_size_sl = config["memory_size_sl"],
  rl_algo = config["rl_algo"],
  sl_algo = config["sl_algo"],
  rl_module= leduc_RL,
  sl_module= leduc_SL,
  gd_module= leduc_GD
  )


# _________________________________ result _________________________________

if not config["wandb_save"]:
  print("avg_utility", list(leduc_trainer.avg_utility_list.items())[-1])
  print("final_exploitability", list(leduc_trainer.exploitability_list.items())[-1])


result_dict_avg = {}
for key, value in sorted(leduc_trainer.avg_strategy.items()):
  result_dict_avg[key] = value
df = pd.DataFrame(result_dict_avg.values(), index=result_dict_avg.keys(), columns=["Fold_avg", "Call_avg", "Raise_avg"])
df.index.name = "Node"

result_dict_br = {}
for key, value in sorted(leduc_trainer.epsilon_greedy_q_learning_strategy.items()):
  result_dict_br[key] = value
df1 = pd.DataFrame(result_dict_br.values(), index=result_dict_br.keys(), columns=["Fold_br", "Call_br", "Raise_br"])
df1.index.name = "Node"

df2 = pd.concat([df, df1], axis=1)


if config["wandb_save"]:
  tbl = wandb.Table(data=df2)
  tbl.add_column("Node", [i for i in df2.index])
  wandb.log({"table:":tbl})
  wandb.save()
else:
  print(df2)

#追加 matplotlibで図を書くため
#df = pd.DataFrame(leduc_trainer.database_for_plot)
#df = df.set_index('iteration')
#df.to_csv('../../../Make_png/output/database_for_plot_NFSP.csv')


doctest.testmod()
