import Population
import Assets
import MarketMechanics
import Agents
import Specialist
import ForecastParams
import Conditions
import csv
import pandas as pd
from itertools import *
import sys
import random
import numpy as np

# IMPLEMENT CHANGING RISK ADVERSENESS
#     Generate normal distribution of numbers ranging from
#         0.31--> risk doesnt matter, .5--> risk neutral, .99--> risk matters a lot  ----------MAX---------- Holdings beyond 3.2
#         0.16--> risk doesnt matter, .35--> risk neutral, .84--> risk matters a lot  ----------MID---------- Holdings between 1.6 and 3.2 -.15
#         0.01--> risk doesnt matter, .2--> risk neutral, .69--> risk matters a lot  ----------MIN---------- Holdings up to 1.6 -.3

#     Calculate risk aversion based on holdings


# Graph
#     agent cash,
class Market(object):
    def __init__(self):
        # Initialize storage for market performance
        self.div_ratio, self.pr_ratio = [], []
        self.div_periods, self.pr_periods = [[], [], [], [], []], [[], [], [], [], []]
        self.div_mas, self.pr_mas = [[], [], [], []], [[], [], [], []]

        # Initialize model parameters
        self.model_params = {}
        self.__load_model_params__()
        self.prob_int_rate_change = self.model_params.get('prob_int_rate')
        self.int_rate = self.model_params.get('int_rate')
        self.min_int_rate = self.model_params.get("min_rate")
        self.max_int_rate = self.model_params.get("max_rate")

        # Initialize conditions
        self.conditions = Conditions.ConditionList()
        self.__load_conditions__()

        # Initialize forecast parameters
        self.forecast_params = {}
        self.__load_forecast_params__()

        # Initialize market mechanics
        self.Mechanics = MarketMechanics.Mechanics(self.model_params, self.conditions)
        self.__set_world_values__()
        self.__set_dividend_values__()

        # Store initial dividend and price
        self.init_dividend = self.Mechanics.__get_dividend__
        self.init_asset_price = self.Mechanics.__get_price__
        self.dividend_value = self.init_dividend
        self.price = self.init_asset_price

        # Initialize population space
        self.population = []
        self.risk_aversion_list = self.__gen_risk_dist__()
        self.__set_agent_values__()

        # Initialize market-maker
        self.specialist = Specialist.MarketClearer()
        self.__set_specialist_values__()

        # Clock
        self.curr_time = 0
        self.time_duration = 5000
        self.warm_up_time = 501

        # Warm-Up and run
        self.warm_up()
        self.run_market()
        self.populate_records()

    @property
    def __get_agent_size__(self):
        return self.population.__sizeof__

    @property
    def __get_population__(self):
        return self.population

    @property
    def __get_agent_init_cash__(self):
        return self.model_params['initial_cash']

    @property
    def __get_mechanics__(self):
        return self.Mechanics

    @property
    def __get_specialist__(self):
        return self.Mechanics

    @property
    def __get_time__(self):
        return self.curr_time

    @property
    def __gen_agent_risk__(self):
        risk_preference = random.choice(self.risk_aversion_list)
        del self.risk_aversion_list[self.risk_aversion_list.index(risk_preference)]
        return risk_preference

    # generates normal distribution ranging from -1 to 1
    @staticmethod
    def __gen_risk_dist__():
        x = list(np.linspace(.31, .99, 100))
        return x

    def __load_model_params__(self):
        with open("model_params.txt", mode='r') as in_file:
            for line in in_file:
                if '=' not in line:
                    continue
                if line == "Forecast Parameters":
                    break

                parameter = line.split()
                param_var = parameter[0]

                if param_var == "ratios":
                    param_value = [float(value) for value in parameter[2:]]
                else:
                    param_value = float(parameter[2])

                self.model_params[param_var] = param_value

    def __load_forecast_params__(self):
        flag = False

        with open("model_params.txt", mode='r') as in_file:
            for line in in_file:
                if '=' not in line or line == 'Forecast Parameters':
                    flag = True
                    continue

                if flag:
                    parameter = line.split()
                    param_var = parameter[0]
                    param_value = float(parameter[2])

                    self.forecast_params[param_var] = param_value

        self.forecast_params['cond_words'] = int((self.forecast_params['cond_bits'] + 15) / 16)
        self.forecast_params['a_range'] = self.forecast_params["a_max"] - self.forecast_params["a_min"]
        self.forecast_params['b_range'] = self.forecast_params["b_max"] - self.forecast_params["b_min"]
        self.forecast_params['c_range'] = self.forecast_params["c_max"] - self.forecast_params["c_min"]
        self.forecast_params['ga_prob'] = 1 / self.forecast_params['ga_freq']

        self.forecast_params['n_pool'] = self.forecast_params['num_forecasts'] * self.forecast_params['pool_fraction']
        self.forecast_params['n_new'] = self.forecast_params['num_forecasts'] * self.forecast_params['new_fraction']

        self.forecast_params['prob_list'] = [self.forecast_params['bit_prob'] for i in range(int(self.forecast_params['cond_bits']))]

    def __load_conditions__(self):
        with open('conditions.txt') as infile:
            index = 0
            for condition in infile:
                try:
                    name, description, *rest = condition.replace("{", '').replace("}", "").replace('"', '').split(',')
                except Exception as e:
                    pass
                new_cond = Conditions.Condition(index, name, description)
                self.conditions.__add__(new_cond)
                index += 1

    def __set_dividend_values__(self):
        baseline = self.model_params["baseline"]
        min_dividend = self.model_params["min_dividend"]
        max_dividend = self.model_params["max_dividend"]
        amplitude = self.model_params["amplitude"]
        period = self.model_params["period"]

        self.Mechanics.__set_dividend_vals__(baseline=baseline, min_dividend=min_dividend, max_dividend=max_dividend,
                                             amplitude=amplitude, period=period)

    def __set_world_values__(self):
        int_rate = self.model_params["int_rate"]
        self.Mechanics.__set_int_rate__(int_rate)

    def __set_specialist_values__(self):
        max_price = self.model_params["max_price"]
        min_price = self.model_params["min_price"]
        taup = self.model_params["taup"]
        sp_type = self.model_params["sp_type"]
        max_iterations = self.model_params["max_iterations"]
        min_excess = self.model_params["min_excess"]
        eta = self.model_params["eta"]
        rea = self.model_params["rea"]
        reb = self.model_params["reb"]
        self.specialist.__set_vals__(max_price=max_price, min_price=min_price, taup=taup, sp_type=sp_type,
                                     max_iterations=max_iterations, min_excess=min_excess, eta=eta, rea=rea, reb=reb,
                                     agents=self.population)

    def __set_agent_values__(self):
        int_rate = self.model_params["int_rate"]
        min_holding = self.model_params['min_holding']
        init_cash = self.model_params['init_cash']
        position = self.model_params['init_holding']
        min_cash = self.model_params['min_cash']

        for i in range(int(self.model_params['num_agents'])):
            agent = Agents.Agent(id=i, name='Agent '+str(i), int_rate=int_rate, min_holding=min_holding, 
                                 init_cash=init_cash, position=position, forecast_params=self.forecast_params, 
                                 dividend=self.init_dividend, price=self.init_asset_price, conditions=self.conditions, 
                                 min_cash=min_cash, risk_aversion=self.__gen_agent_risk__)
            agent.__set_holdings__()
            self.population.append(agent)

    def catch_market_states(self):
        price_history, div_history = self.Mechanics.__get_histories__
        price_ma, div_ma = self.Mechanics.__get_mas__

        # Dividend to mean dividend ratio
        self.div_ratio.append(self.Mechanics.__get_div_ratio__)

        # Price * interest to dividend dividend ratio
        self.pr_ratio.append(self.Mechanics.__get_price_ratio__)

        # Dividend and Price for the 5 most recent periods
        for i in range(5):
            self.div_periods[i].append(div_history[-i])
            self.pr_periods[i].append(price_history[-i])

        # Dividend moving average
        for i, ma in enumerate(div_ma):
            self.div_mas[i].append(ma.__get_ma__())

        # Price moving average
        for i, ma in enumerate(price_ma):
            self.pr_mas[i].append(ma.__get_ma__())

    def populate_records(self):
        data = {
            "Dividend Ratio": self.div_ratio,
            "Price ratio": self.pr_ratio,

            # 'Recent Div 1 period ago': self.div_periods[0],
            # 'Recent Div 2 periods ago': self.div_periods[1],
            # 'Recent Div 3 periods ago': self.div_periods[2],
            # 'Recent Div 4 periods ago': self.div_periods[3],
            # 'Recent Div 5 periods ago': self.div_periods[4],
            #
            # 'Recent Price 1 period': self.pr_periods[0],
            # 'Recent Price 2 periods ago': self.pr_periods[1],
            # 'Recent Price 3 periods ago': self.pr_periods[2],
            # 'Recent Price 4 periods ago': self.pr_periods[3],
            # 'Recent Price 5 periods ago': self.pr_periods[4],

            '5 Day Div Moving Average': self.div_mas[0],
            '20 Day Div Moving Average': self.div_mas[1],
            '100 Day Div Moving Average': self.div_mas[2],
            '500 Day Div Moving Average': self.div_mas[3],

            '5 Day Price Moving Average': self.pr_mas[0],
            '20 Day Price Moving Average': self.pr_mas[1],
            '100 Day Price Moving Average': self.pr_mas[2],
            '500 Day Price Moving Average': self.pr_mas[3]
        }
        df = pd.DataFrame(data)
        df.to_csv('market_states.csv')

    def warm_up(self):
        for i in range(self.warm_up_time):
            self.dividend_value = self.Mechanics.__update_dividend__()
            self.conditions = self.Mechanics.__update_market__()
            self.catch_market_states()
            condition_str = self.condition_string()

            self.price = self.dividend_value / self.model_params['int_rate']
            self.Mechanics.__set_price__(self.price)
        print("WARM UP COMPLETE")

    def condition_string(self):
        output = ''
        for condition in self.conditions:
            string = str(condition.__get__) + "\n"
            output += string
        return output

    def run_market(self):
        div = []
        price = []
        volumes = []
        buy = []
        sell = []
        attempt_buys = []
        attempt_sells = []
        matches = []
        time = []
        for i in range(self.time_duration):
            print("TIME", self.curr_time)
            
            # CHANGE INT RATE
            # chance_new_int_rate = random.randint(0, 10)/100
            # if i >= 2500 and chance_new_int_rate < self.prob_int_rate_change:
            #     self.change_int_rate()

            # Give agents their information
            self.give_info()

            # New Dividend
            self.new_dividend()

            # Credit earnings and pay taxes
            if self.curr_time > 1:
                self.credits_and_taxes()

            # Update the Market
            self.conditions = self.Mechanics.__update_market__()

            # Prepare agents for trades
            self.prepare_trades()

            # Calculate the new price and perform trades
            self.price, curr_matches = self.specialist.perform_trades()
            self.Mechanics.__set_price__(self.price)

            # Complete the trades
            self.specialist.__set_agents__(self.population)
            buys, sells, at_sells, at_buys, self.population = self.specialist.complete_trades()
            volume = self.specialist.__get_volume__

            # Update agent performance
            self.update_performances()

            div.append(self.dividend_value)
            price.append(self.price)
            volumes.append(volume)
            buy.append(buys)
            sell.append(sells)
            attempt_buys.append(at_buys)
            attempt_sells.append(at_sells)
            time.append(i)
            matches.append(curr_matches)
            
            self.curr_time += 1
            # print("---------------------------")
            # break
        data = {"Price": price, "Dividend": div, "Volume": volumes, "Matches": matches, "Attempt Buys": attempt_buys,
                "Attempt Sells": attempt_sells}
        df = pd.DataFrame(data=data)
        df.to_csv('output.txt', sep='\t')

        
    def change_int_rate(self):
        choice = random.randint(1,2)
        if choice == 1:
            new_int_rate = self.int_rate - 0.01
        elif choice == 2:
            new_int_rate = self.int_rate + 0.01
        # new_int_rate = self.int_rate - .01

        if new_int_rate <= self.min_int_rate:
            new_int_rate = self.min_int_rate
        elif new_int_rate >= self.max_int_rate:
            new_int_rate = self.max_int_rate
        self.int_rate = new_int_rate

        self.Mechanics.__set_int_rate__(self.int_rate)
        self.specialist.__set_int_rate__(self.int_rate)
        for agent in self.population:
            agent.__set_int_rate__(self.int_rate)

        print("NEW INTEREST RATE", self.int_rate)
        # wait = input("WAITING: ")

    def new_dividend(self):
        self.dividend_value = self.Mechanics.__update_dividend__()

    def credits_and_taxes(self):
        for agent in self.population:
            agent.credit_earnings_and_taxes()

    def prepare_trades(self):
        for agent in self.population:
            agent.prepare_trading()

    def update_performances(self):
        for agent in self.population:
            agent.update_performance()

    def give_info(self):
        for agent in self.population:
            agent.__set_price__(self.price)
            agent.__set_dividend__(self.dividend_value)
            agent.__set_conditions__(self.conditions)
            agent.__set_time__(self.curr_time)
            # if agent.__get_id__ == 0:
            #     print("MARKET TIME: ", time)
            #     print("MARKET CONDITIONS: ")
            #     self.print(conditions)
            #     print("AGENT TIME: ", agent.__get_time__)
            #     print("AGENT CONDITIONS:", agent.__get_conditions__)
            #     # agent.update_active_list()
            #     # agent.activate_ga()
            #     print("-------------------")

        self.specialist.__set_world_price__(self.price)
        self.specialist.__set_world_dividend__(self.dividend_value)
        self.specialist.__set_profit_per_unit__(self.Mechanics.__get_profit_per_unit__)
        self.specialist.__set_agents__(self.population)



def test():
    test_market = Market()

    # test_agents = test_market.__get_population__
    # agent = test_agents[0]
    # print(agent.__get_cash__)
    # mechanics.__update_market__()
    # mechanics.__see_conditions__()
    #
    # agent = test_market.__get_agents__(0)
    # agent.update_active_list()
    #
    # print("#############################")
    # print("FORECAST PARAMS")
    # params = mechanics.__get_forecast_params__
    # print(params)



test()
