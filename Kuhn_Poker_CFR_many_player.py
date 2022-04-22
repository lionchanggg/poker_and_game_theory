#ライブラリ

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import random
import itertools
from collections import defaultdict
import sys
from tqdm import tqdm
import time
import doctest
import copy


#Node Class

#information set node class definition
class Node:
  #Kuhn_node_definitions
  def __init__(self, NUM_ACTIONS):
    self.NUM_ACTIONS = NUM_ACTIONS
    self.infoSet = None
    self.c = 0
    self.regretSum = np.array([0 for _ in range(self.NUM_ACTIONS)], dtype=float)
    self.strategy = np.array([0 for _ in range(self.NUM_ACTIONS)], dtype=float)
    self.strategySum = np.array([0 for _ in range(self.NUM_ACTIONS)], dtype=float)
    self.Get_strategy_through_regret_matching()

  #regret-matching
  def Get_strategy_through_regret_matching(self):
    self.normalizingSum = 0
    for a in range(self.NUM_ACTIONS):
      self.strategy[a] = self.regretSum[a] if self.regretSum[a]>0 else 0
      self.normalizingSum += self.strategy[a]

    for a in range(self.NUM_ACTIONS):
      if self.normalizingSum >0 :
        self.strategy[a] /= self.normalizingSum
      else:
        self.strategy[a] = 1/self.NUM_ACTIONS

  # calculate average-strategy
  def Get_average_information_set_mixed_strategy(self):
    self.avgStrategy = np.array([0 for _ in range(self.NUM_ACTIONS)], dtype=float)
    self.normalizingSum = 0
    for a in range(self.NUM_ACTIONS):
      self.normalizingSum += self.strategySum[a]

    for a in range(self.NUM_ACTIONS):
      if self.normalizingSum >0 :
        self.avgStrategy[a] = self.strategySum[a] / self.normalizingSum
      else:
        self.avgStrategy[a] = 1/ self.NUM_ACTIONS

    return self.avgStrategy

#Trainer class

class KuhnTrainer:
  def __init__(self, train_iterations=10**4):
    self.train_iterations = train_iterations
    self.NUM_PLAYERS = 2
    self.PASS = 0
    self.BET = 1
    self.NUM_ACTIONS = 2
    self.nodeMap = defaultdict(list)
    self.rank = {"J":1, "Q":2, "K":3}
    self.eval = False


  #return util for terminal state
  def Return_payoff_for_terminal_states(self, history, target_player_i):
    """return int
    >>> KuhnTrainer().Return_payoff_for_terminal_states("JKpp", 0)
    -1
    >>> KuhnTrainer().Return_payoff_for_terminal_states("QKpp", 1)
    1
    """
    plays = len(history)
    player = plays % 2
    opponent = 1 - player
    terminal_utility = 0

    if plays > 3:
      terminalPass = (history[plays-1] == "p")
      doubleBet = (history[plays-2 : plays] == "bb")
      isPlayerCardHigher = (self.rank[history[player]] > self.rank[history[opponent]])

      if terminalPass:
        if history[-2:] == "pp":
          if isPlayerCardHigher:
            terminal_utility = 1
          else:
            terminal_utility = -1
        else:
            terminal_utility = 1
      elif doubleBet: #bb
          if isPlayerCardHigher:
            terminal_utility = 2
          else:
            terminal_utility = -2

    if player == target_player_i:
      return terminal_utility
    else:
      return -terminal_utility



  #terminal stateかどうかを判定
  def whether_terminal_states(self, history):
    """return string
    >>> KuhnTrainer().whether_terminal_states("")
    False
    >>> KuhnTrainer().whether_terminal_states("JK")
    False
    >>> KuhnTrainer().whether_terminal_states("JQpp")
    True
    >>> KuhnTrainer().whether_terminal_states("QKpb")
    False
    >>> KuhnTrainer().whether_terminal_states("JKbb")
    True
    >>> KuhnTrainer().whether_terminal_states("QKpbb")
    True
    """
    plays = len(history)
    if plays > 3:
      terminalPass = (history[plays-1] == "p")
      doubleBet = (history[plays-2 : plays] == "bb")

      return terminalPass or doubleBet
    else:
      return False

   #terminal stateかどうかを判定
  def whether_chance_node(self, history):
    """return string
    >>> KuhnTrainer().whether_chance_node("")
    True
    >>> KuhnTrainer().whether_chance_node("p")
    False
    """
    if history == "":
      return True
    else:
      return False


  # make node or get node
  def Get_information_set_node_or_create_it_if_nonexistant(self, infoSet):
    node = self.nodeMap.get(infoSet)
    if node == None:
      node = Node(self.NUM_ACTIONS)
      self.nodeMap[infoSet] = node
    return node


  def Get_strategy(self, node):
    if not self.eval:
      strategy =  node.strategy
    else:
      if self.eval:
        strategy = node.Get_average_information_set_mixed_strategy()
    return strategy


  #chance sampling CFR
  def chance_sampling_CFR(self, history, target_player_i, iteration_t, p0, p1):
    plays = len(history)
    player = plays % 2
    opponent = 1 - player

    if self.whether_terminal_states(history):
      return self.Return_payoff_for_terminal_states(history, target_player_i)

    elif self.whether_chance_node(history):
      cards = np.array(["J", "Q", "K"])
      random.shuffle(cards)
      nextHistory = cards[0] + cards[1]
      return self.chance_sampling_CFR(nextHistory, target_player_i, iteration_t, p0, p1)

    infoSet = history[player] + history[2:]
    node = self.Get_information_set_node_or_create_it_if_nonexistant(infoSet)
    util_list = np.array([0 for _ in range(self.NUM_ACTIONS)], dtype=float)
    nodeUtil = 0
    node.Get_strategy_through_regret_matching()
    strategy = self.Get_strategy(node)

    for ai in range(self.NUM_ACTIONS):
      nextHistory = history + ("p" if ai == 0 else "b")
      if player == 0:
        util_list[ai] = self.chance_sampling_CFR(nextHistory, target_player_i, iteration_t, p0 * strategy[ai], p1)
      else:
        util_list[ai] = self.chance_sampling_CFR(nextHistory, target_player_i, iteration_t, p0, p1 * strategy[ai])
      nodeUtil += strategy[ai] * util_list[ai]

    if (not self.eval) and  player == target_player_i:
      for ai in range(self.NUM_ACTIONS):
        regret = util_list[ai] - nodeUtil
        node.regretSum[ai] += (p1 if player==0 else p0) * regret
        node.strategySum[ai] += strategy[ai] * (p0 if player==0 else p1)


    return nodeUtil


  def vanilla_CFR(self, history, target_player_i, iteration_t, p0, p1):
    plays = len(history)
    player = plays % 2
    opponent = 1 - player

    if self.whether_terminal_states(history):
      return self.Return_payoff_for_terminal_states(history, target_player_i)

    elif self.whether_chance_node(history):
      cards = np.array(["J", "Q", "K"])
      cards_candicates = [cards_candicate for cards_candicate in itertools.permutations(cards)]
      utility_sum = 0
      for cards_i in cards_candicates:
        nextHistory = cards_i[0] + cards_i[1]
        #regret　strategy 重み どのカードでも同じ確率
        utility_sum += (1/len(cards_candicates))* self.vanilla_CFR(nextHistory, target_player_i, iteration_t, p0, p1)
      return utility_sum

    infoSet = history[player] + history[2:]
    node = self.Get_information_set_node_or_create_it_if_nonexistant(infoSet)
    node.Get_strategy_through_regret_matching()

    strategy = self.Get_strategy(node)

    util_list = np.array([0 for _ in range(self.NUM_ACTIONS)], dtype=float)
    nodeUtil = 0

    for ai in range(self.NUM_ACTIONS):
      nextHistory = history + ("p" if ai == 0 else "b")
      if player == 0:
        util_list[ai] = self.vanilla_CFR(nextHistory, target_player_i, iteration_t, p0 * strategy[ai], p1)
      else:
        util_list[ai] = self.vanilla_CFR(nextHistory, target_player_i, iteration_t, p0, p1 * strategy[ai])
      nodeUtil += strategy[ai] * util_list[ai]

    if (not self.eval) and  player == target_player_i:
      for ai in range(self.NUM_ACTIONS):
        regret = util_list[ai] - nodeUtil
        node.regretSum[ai] += (p1 if player==0 else p0) * regret
        node.strategySum[ai] += strategy[ai] * (p0 if player==0 else p1)


    return nodeUtil


  #external sampling MCCFR
  def external_sampling_MCCFR(self, history, target_player_i):
    plays = len(history)
    player = plays % 2
    opponent = 1 - player

    if self.whether_terminal_states(history):
      return self.Return_payoff_for_terminal_states(history, target_player_i)

    elif self.whether_chance_node(history):
      cards = np.array(["J", "Q", "K"])
      random.shuffle(cards)
      nextHistory = cards[0] + cards[1]
      return self.external_sampling_MCCFR(nextHistory, target_player_i)

    infoSet = history[player] + history[2:]
    node = self.Get_information_set_node_or_create_it_if_nonexistant(infoSet)
    node.Get_strategy_through_regret_matching()

    if player == target_player_i:
      util_list = np.array([0 for _ in range(self.NUM_ACTIONS)], dtype=float)
      nodeUtil = 0

      for ai in range(self.NUM_ACTIONS):
        nextHistory = history + ("p" if ai == 0 else "b")
        util_list[ai] = self.external_sampling_MCCFR(nextHistory, target_player_i)
        nodeUtil += node.strategy[ai] * util_list[ai]

      for ai in range(self.NUM_ACTIONS):
        regret = util_list[ai] - nodeUtil
        node.regretSum[ai] += regret

    else:
      sampling_action = np.random.choice(list(range(self.NUM_ACTIONS)), p= node.strategy)
      nextHistory = history + ("p" if sampling_action == 0 else "b")
      nodeUtil= self.external_sampling_MCCFR(nextHistory, target_player_i)

      for ai in range(self.NUM_ACTIONS):
        node.strategySum[ai] += node.strategy[ai]

    return nodeUtil


  #outcome sampling MCCFR
  def outcome_sampling_MCCFR(self, history, target_player_i, iteration_t, p0, p1,s):
    plays = len(history)
    player = plays % 2
    opponent = 1 - player

    if self.whether_terminal_states(history):
      return self.Return_payoff_for_terminal_states(history, target_player_i) / s, 1

    elif self.whether_chance_node(history):
      cards = np.array(["J", "Q", "K"])
      random.shuffle(cards)
      nextHistory = cards[0] + cards[1]
      return self.outcome_sampling_MCCFR(nextHistory, target_player_i, iteration_t, p0, p1, s)

    infoSet = history[player] + history[2:]
    node = self.Get_information_set_node_or_create_it_if_nonexistant(infoSet)
    node.Get_strategy_through_regret_matching()
    probability =  np.array([0 for _ in range(self.NUM_ACTIONS)], dtype=float)

    if player == target_player_i:
      for ai in range(self.NUM_ACTIONS):
        probability[ai] =  self.epsilon/self.NUM_ACTIONS + (1-self.epsilon)* node.strategy[ai]
    else:
      for ai in range(self.NUM_ACTIONS):
        probability[ai] = node.strategy[ai]

    sampling_action = np.random.choice(list(range(self.NUM_ACTIONS)), p=probability)
    nextHistory = history + ("p" if sampling_action == 0 else "b")

    if player == target_player_i:
      util, p_tail = self.outcome_sampling_MCCFR(nextHistory, target_player_i, iteration_t, p0*node.strategy[sampling_action], p1, s*probability[sampling_action])

      w = util * p1
      for ai in range(self.NUM_ACTIONS):
        if sampling_action == ai:
          regret = w*(1- node.strategy[sampling_action])*p_tail
        else:
          regret = -w*p_tail * node.strategy[sampling_action]
        node.regretSum[ai] +=  regret

    else:
        util, p_tail = self.outcome_sampling_MCCFR(nextHistory, target_player_i, iteration_t, p0, p1*node.strategy[sampling_action], s*probability[sampling_action])

        for ai in range(self.NUM_ACTIONS):
          node.strategySum[ai] += (iteration_t - node.c)*p1*node.strategy[ai]
        node.c = iteration_t
        #node.strategySum[ai] += (p1/s)*node.strategy[ai]

    return util, p_tail*node.strategy[sampling_action]



  #KuhnTrainer main method
  def train(self, method):
    self.exploitability_list = {}
    for iteration_t in tqdm(range(int(self.train_iterations))):
      for target_player_i in range(self.NUM_PLAYERS):

        if method == "vanilla_CFR":
          self.vanilla_CFR("", target_player_i, iteration_t, 1, 1)
        elif method == "chance_sampling_CFR":
          self.chance_sampling_CFR("", target_player_i, iteration_t, 1, 1)
        elif method == "external_sampling_MCCFR":
          self.external_sampling_MCCFR("", target_player_i)
        elif method == "outcome_sampling_MCCFR":
          self.epsilon = 0.6
          self.outcome_sampling_MCCFR("", target_player_i, iteration_t, 1, 1, 1)

      #calculate expolitability
      if iteration_t in [int(j)-1 for j in np.logspace(1, len(str(self.train_iterations))-1, (len(str(self.train_iterations))-1)*3)] :
        self.exploitability_list[iteration_t] = self.get_exploitability_dfs()

    self.show_plot(method)


  def show_plot(self, method):
    plt.scatter(list(self.exploitability_list.keys()), list(self.exploitability_list.values()), label=method)
    plt.plot(list(self.exploitability_list.keys()), list(self.exploitability_list.values()))
    plt.xscale('log')
    plt.yscale('log')
    plt.xlabel("iterations")
    plt.ylabel("exploitability")
    plt.legend(loc = "lower left")


  # evaluate average strategy
  def eval_strategy(self, target_player_i):
    self.eval = True
    average_utility = self.vanilla_CFR("", target_player_i, 0, 1, 1)
    self.eval = False
    return average_utility



  def calc_best_response_value(self, best_response_strategy, best_response_player, history, prob):
      plays = len(history)
      player = plays % 2
      opponent = 1 - player

      if self.whether_terminal_states(history):
        return self.Return_payoff_for_terminal_states(history, best_response_player)

      elif self.whether_chance_node(history):
        cards = np.array(["J", "Q", "K"])
        cards_candicates = [cards_candicate for cards_candicate in itertools.permutations(cards)]
        utility_sum = 0
        for cards_i in cards_candicates:
          nextHistory = cards_i[0] + cards_i[1]
          utility_sum +=  (1/len(cards_candicates))* self.calc_best_response_value(best_response_strategy, best_response_player, nextHistory, prob)
        return utility_sum


      infoSet = history[player] + history[2:]
      node = self.Get_information_set_node_or_create_it_if_nonexistant(infoSet)


      if player == best_response_player:
        if infoSet not in best_response_strategy:
          action_value = np.array([0 for _ in range(self.NUM_ACTIONS)], dtype=float)
          br_value = np.array([0 for _ in range(self.NUM_ACTIONS)], dtype=float)


          for assume_history, po_ in self.infoSets_dict[infoSet]:
            for ai in range(self.NUM_ACTIONS):
              nextHistory =  assume_history + ("p" if ai == 0 else "b")
              br_value[ai] = self.calc_best_response_value(best_response_strategy, best_response_player, nextHistory, po_)
              action_value[ai] += br_value[ai] * po_


          br_action = 0
          for ai in range(self.NUM_ACTIONS):
            if action_value[ai] > action_value[br_action]:
              br_action = ai
          best_response_strategy[infoSet] = np.array([0 for _ in range(self.NUM_ACTIONS)], dtype=float)
          best_response_strategy[infoSet][br_action] = 1.0


        node_util = np.array([0 for _ in range(self.NUM_ACTIONS)], dtype=float)
        for ai in range(self.NUM_ACTIONS):
          nextHistory =  history + ("p" if ai == 0 else "b")
          node_util[ai] = self.calc_best_response_value(best_response_strategy, best_response_player, nextHistory, prob)
        best_response_util = 0
        for ai in range(self.NUM_ACTIONS):
          best_response_util += node_util[ai] * best_response_strategy[infoSet][ai]

        return best_response_util


      else:
        avg_strategy = node.Get_average_information_set_mixed_strategy()
        nodeUtil = 0
        action_value_list = np.array([0 for _ in range(self.NUM_ACTIONS)], dtype=float)
        for ai in range(self.NUM_ACTIONS):
          nextHistory =  history + ("p" if ai == 0 else "b")
          action_value_list[ai] = self.calc_best_response_value(best_response_strategy, best_response_player, nextHistory, prob*avg_strategy[ai])
          nodeUtil += avg_strategy[ai] * action_value_list[ai]
        return nodeUtil


  def create_infoSets(self, history, target_player, po):
    plays = len(history)
    player = plays % 2
    opponent = 1 - player

    if self.whether_terminal_states(history):
      return

    elif self.whether_chance_node(history):
      cards = np.array(["J", "Q", "K"])
      cards_candicates = [cards_candicate for cards_candicate in itertools.permutations(cards)]
      for cards_i in cards_candicates:
        nextHistory = cards_i[0] + cards_i[1]
        self.create_infoSets(nextHistory, target_player, po)
      return

    infoSet = history[player] + history[2:]
    if player == target_player:
      if self.infoSets_dict.get(infoSet) is None:
        self.infoSets_dict[infoSet] = []
      self.infoSets_dict[infoSet].append((history, po))

    for ai in range(self.NUM_ACTIONS):
      nextHistory = history + ("p" if ai == 0 else "b")
      if player == target_player:
        self.create_infoSets(nextHistory, target_player, po)
      else:
        node = self.Get_information_set_node_or_create_it_if_nonexistant(infoSet)
        actionProb = node.Get_average_information_set_mixed_strategy()[ai]
        self.create_infoSets(nextHistory, target_player, po*actionProb)



  def get_exploitability_dfs(self):

    # 各information setを作成 & reach_probabilityを計算
    self.infoSets_dict = {}
    for target_player in range(self.NUM_PLAYERS):
      self.create_infoSets("", target_player, 1.0)

    exploitability = 0
    best_response_strategy = {}
    for best_response_player_i in range(self.NUM_PLAYERS):
        exploitability += self.calc_best_response_value(best_response_strategy, best_response_player_i, "", 1)

    if exploitability < 0:
      return 1e-7
    #assert exploitability >= 0
    return exploitability

#Excute

kuhn_trainer = KuhnTrainer(train_iterations=10**2)
#kuhn_trainer.train("vanilla_CFR")
kuhn_trainer.train("chance_sampling_CFR")
#kuhn_trainer.train("external_sampling_MCCFR")
#kuhn_trainer.train("outcome_sampling_MCCFR")

"""
plt.figure(figsize=(12, 8))
plt.rcParams["font.size"] = 20
for method in ["vanilla_CFR", "chance_sampling_CFR", "external_sampling_MCCFR", "outcome_sampling_MCCFR"]:
  kuhn_trainer = KuhnTrainer(train_iterations=10**5)
  kuhn_trainer.train(method)
"""

print("average eval util:", kuhn_trainer.eval_strategy(0))

result_dict = {}

for key, value in sorted(kuhn_trainer.nodeMap.items()):
  result_dict[key] = value.Get_average_information_set_mixed_strategy()

df = pd.DataFrame(result_dict.values(), index=result_dict.keys(), columns=['Pass', "Bet"])
df = df.reindex(["J", "Jp", "Jb", "Jpb", "Q", "Qp", "Qb", "Qpb", "K", "Kp", "Kb", "Kpb"], axis="index")
df.index.name = "Node"

print(df)

doctest.testmod()
