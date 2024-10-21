from datetime import datetime
from typing import List, Dict, Any, Type, Hashable, Optional
from math import nan, isnan
import pandas as pd

from .trading import Position, Trade
from .result import Result

# 定义Broker类的目的是把Strategy和交易功能分割开来进行管理
class Broker:
    '''
    Broker类负责管理与交易相关的所有功能
    '''
    def __init__(self, cash: float, commission: float):
        self.cash = cash
        self.commission = commission
        self.date = None

        self.open_positions = []
        self.trades = []
        self.assets_value = .0
        self.cumulative_return = cash
        self.returns: List[float] = []

    def open(self, price: float, size: Optional[float] = None, symbol: Optional[str] = None, short=False):
        '''
        开仓方法,需要指定price, size, symbol以及持仓方向short
        '''

        if isnan(price) or price <= 0 or (size is not None and (isnan(size) or size <= .0)):
            return False

        if size > 0 and size <= 1: # 分数仓
            # 可用现金*分数/价格
            size = size * self.cash / (price * (1 + self.commission))
            open_cost = size * price * (1 + self.commission)
        if size is None: # 全仓
            size = self.cash / (price * (1 + self.commission))
            open_cost = self.cash
        else: # 固定仓位
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
            self.assets_value -= position.current_value # 这里其实可以忽视，assets_value真正的逻辑其实是在外部实现的
            position.update(last_date=self.date, last_price=price)
            trade_commission = (position.open_price + position.last_price) * position.position_size * self.commission
            self.cumulative_return += position.profit_loss - trade_commission

            trade = Trade(position.symbol, position.is_short, position.open_date, position.last_date, position.open_price,
            position.last_price, position.position_size, position.profit_loss, position.change_pct,
            trade_commission, self.cumulative_return)

            self.trades.extend([trade])
            self.open_positions.remove(position) # 关闭仓位

            close_cost = position.last_price * position.position_size * self.commission
            self.cash += position.current_value - close_cost

        return True

    def current_position_status(self):
        '''
        统计当前仓位多/空分别有哪些标的(需要注意position它update的时机)
        '''
        long_positions = []
        short_positions = []
        for position in self.open_positions:
            if position.is_short == False:
                long_positions.append(position.symbol)
            else:
                short_positions.append(position.symbol)
    
        return long_positions, short_positions

    def current_position_count(self):
        '''
        统计当前仓位多/空仓位的数量(需要注意position它update的时机)
        '''
        long_c = 0
        short_c = 0
        
        for position in self.open_positions:
            # 多头仓位
            if position.is_short == False:
                long_c += 1
            else:
                short_c += 1
                
        return long_c, short_c