from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Type, Hashable, Optional
from math import nan, isnan
import pandas as pd

from .trading import Position, Trade
from .result import Result
from .broker import Broker


class Strategy(ABC):

    @abstractmethod
    def init(self):
        """
        策略初始化
        """

    @abstractmethod
    def next(self, i: int, record: Dict[Hashable, Any]):
        """
        策略逻辑部分
        """

    def __init__(self):
        # 这部分参数是靠Backtest传进来的
        self.broker: Broker = None # 控制仓位的功能
        self.data = pd.DataFrame()
        self.date = None
        self.symbols: List[str] = []
        self.records: List[Dict[Hashable, Any]] = []
        self.index: List[datetime] = []

        # 这些全部交给broker处理
        #self.cash = .0
        #self.commission = .0
        #self.returns: List[float] = []
        #self.trades: List[Trade] = [] # 成交的订单
        #self.open_positions: List[Position] = [] # 激活的订单
        #self.cumulative_return = self.cash
        #self.assets_value = .0 # 资产价值/头寸价值

    def open(self, price: float, size: Optional[float] = None, symbol: Optional[str] = None, short=False):
        '''
        开仓的接口,需要指定symbol以及size,size可以使用分数或者整数
        如果size使用分数则会按照目前可用现金来计算开仓大小
        '''
        self.broker.open(price, size, symbol, short)    

    # 这个关仓写的很简单，就是用来关闭open的Position
    def close(self, price: float, symbol: Optional[str] = None, position: Optional[Position] = None):
        '''
        关仓的接口,关闭指定symbol的仓位
        '''
        self.broker.close(price, symbol, position)

    def __eval(self, *args, **kwargs):
        '''
        策略回测的实现
        '''
        self.cumulative_return = self.broker.cash
        self.assets_value = .0 # 头寸价值

        self.init(*args, **kwargs) # 先进行初始化

        # 对历史数据按时间序列进行遍历
        for i, record in enumerate(self.records):
            self.date = self.index[i]
            self.broker.date = self.index[i]

            # 例如：
            '''
            0, {('AAA', 'Open'): 100.0, ('AAA', 'High'): 100.0...}
            '''
            self.next(i, record) # 将记录与索引作为参数传入

            # 对于在next里激活的所有订单
            for position in self.broker.open_positions:
                # 找到该标的的last_price
                last_price = record[(position.symbol, 'Close')] if (position.symbol, 'Close') in record else record['Close']
                if last_price > 0:
                    # 该position进行更新
                    position.update(last_date=self.date, last_price=last_price)

            self.assets_value = sum(position.current_value for position in self.broker.open_positions)
            self.broker.returns.append(self.broker.cash + self.assets_value)

        # 返回该策略的回测结果
        return Result(
            returns=pd.Series(index=self.index, data=self.broker.returns, dtype=float),
            trades=self.broker.trades,
            open_positions=self.broker.open_positions
        )

class Backtest:

    def __init__(self,
                 strategy: Type[Strategy],
                 data: pd.DataFrame,
                 cash: float = 10_000,
                 commission: float = .0
                 ):

        self.strategy = strategy
        self.data = data
        self.cash = cash
        self.commission = commission

        columns = data.columns
        self.symbols = columns.get_level_values(0).unique().tolist() if isinstance(columns, pd.MultiIndex) else []

        self.records = data.to_dict('records') 
        # 一个列表，每一个元素是一个字典
        '''
        {('AAA', 'Open'): 200.0,
        ...
         ('BBB', 'Volume'): 1700000}
        '''
        self.index = data.index.tolist()

    def run(self, *args, **kwargs):
        strategy = self.strategy()

        # 这里把backtest的参数传过去了
        strategy.data = self.data
        strategy.symbols = self.symbols
        strategy.records = self.records
        strategy.index = self.index

        # 给strategy绑定一个broker进行仓位管理，这样让strategy和交易的功能分割开来
        strategy.broker = Broker(cash=self.cash, commission=self.commission)

        # name mangling调用回测方法
        return strategy._Strategy__eval(*args, **kwargs)