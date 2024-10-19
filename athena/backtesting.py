from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Type, Hashable, Optional
from math import nan, isnan
import pandas as pd

from .trading import Position, Trade
from .result import Result


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
        self.data = pd.DataFrame()
        self.date = None
        self.cash = .0
        self.commission = .0
        self.symbols: List[str] = []
        self.records: List[Dict[Hashable, Any]] = []
        self.index: List[datetime] = []

        # 这部分参数是用来统计的
        self.returns: List[float] = []
        self.trades: List[Trade] = [] # 成交的订单
        self.open_positions: List[Position] = [] # 激活的订单
        self.cumulative_return = self.cash
        self.assets_value = .0 # 资产价值/头寸价值

    def open(self, price: float, size: Optional[float] = None, symbol: Optional[str] = None, short=False):

        if isnan(price) or price <= 0 or (size is not None and (isnan(size) or size <= .0)):
            return False

        if size is None: # 全仓
            size = self.cash / (price * (1 + self.commission))
            open_cost = self.cash
        else:
            open_cost = size * price * (1 + self.commission)

        if isnan(size) or size <= .0 or self.cash < open_cost:
            return False

        # 建立一个仓位
        # 注意：建立仓位的时候需要确认仓位的多空美方向
        position = Position(symbol=symbol, open_date=self.date, open_price=price, position_size=size, is_short=short)
        # 初始化last_date和last_price
        position.update(last_date=self.date, last_price=price)

        self.assets_value += position.current_value
        self.cash -= open_cost

        self.open_positions.extend([position])
        return True

    # 这个关仓写的很简单，就是用来关闭open的Position
    def close(self, price: float, symbol: Optional[str] = None, position: Optional[Position] = None):

        if isnan(price) or price <= 0:
            return False

        # 如果说没有指定position，就遍历所有的position，找到symbol相同的position
        if position is None:
            for position in self.open_positions[:]:
                if position.symbol == symbol:
                    self.close(position=position, price=price)
        
        # 指定要关闭的position时
        else:
            # 无论是多还是空，都是在关闭仓位
            self.assets_value -= position.current_value # TODO: 这个地方需要注意下
            position.update(last_date=self.date, last_price=price)
            trade_commission = (position.open_price + position.last_price) * position.position_size * self.commission
            self.cumulative_return += position.profit_loss - trade_commission # TODO: 仓位里有关空头的计算也得修改

            trade = Trade(position.symbol, position.is_short, position.open_date, position.last_date, position.open_price,
            position.last_price, position.position_size, position.profit_loss, position.change_pct,
            trade_commission, self.cumulative_return)

            self.trades.extend([trade])
            self.open_positions.remove(position) # 关闭仓位

            close_cost = position.last_price * position.position_size * self.commission
            self.cash += position.current_value - close_cost

        return True

    def __eval(self, *args, **kwargs):
        self.cumulative_return = self.cash
        self.assets_value = .0

        self.init(*args, **kwargs) # 先进行初始化

        # 对历史数据按时间序列进行遍历
        for i, record in enumerate(self.records):
            self.date = self.index[i]

            # 例如：
            '''
            0, {('AAA', 'Open'): 100.0, ('AAA', 'High'): 100.0...}
            '''
            self.next(i, record) # 将记录与索引作为参数传入

            # 对于在next里激活的所有订单
            for position in self.open_positions:
                # 找到该标的的last_price
                last_price = record[(position.symbol, 'Close')] if (position.symbol, 'Close') in record else record['Close']
                if last_price > 0:
                    # 该position进行更新
                    position.update(last_date=self.date, last_price=last_price)

            self.assets_value = sum(position.current_value for position in self.open_positions)
            self.returns.append(self.cash + self.assets_value)

        return Result(
            returns=pd.Series(index=self.index, data=self.returns, dtype=float),
            trades=self.trades,
            open_positions=self.open_positions
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
        strategy.cash = self.cash
        strategy.commission = self.commission
        strategy.symbols = self.symbols
        strategy.records = self.records
        strategy.index = self.index

        # name mangling方法
        return strategy._Strategy__eval(*args, **kwargs)