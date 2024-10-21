from dataclasses import dataclass
from typing import List, Dict, Any, Type, Hashable, Optional
from datetime import datetime
from math import nan, isnan

@dataclass
class Position:
    '''
    订单相关的数据结构，记录每一个订单的基础信息
    每次next运行完会调用一次update方法来更新Position的last_date与last_price
    '''

    symbol: Optional[str] = None
    open_date: Optional[datetime] = None
    last_date: Optional[datetime] = None
    open_price: float = nan
    last_price: float = nan
    position_size: float = nan
    profit_loss: float = nan
    change_pct: float = nan
    current_value: float = nan

    is_short: bool = False  # 新增属性，标识是否为做空头寸

    def update(self, last_date: datetime, last_price: float):
        self.last_date = last_date
        self.last_price = last_price

        if self.is_short:
            # 做空仓位
            self.profit_loss = (self.open_price - self.last_price) * self.position_size
            self.change_pct = (1 - self.last_price / self.open_price) * 100
            self.current_value = self.open_price * self.position_size + self.profit_loss
        else:
            self.profit_loss = (self.last_price - self.open_price) * self.position_size
            self.change_pct = (self.last_price / self.open_price - 1) * 100
            self.current_value = self.open_price * self.position_size + self.profit_loss

@dataclass
class Trade:
    '''
    订单被关闭后就会创造一个Trade的数据结构
    它是一个完整交易的信息
    '''
    symbol: Optional[str] = None
    short: bool = False
    open_date: Optional[datetime] = None
    close_date: Optional[datetime] = None
    open_price: float = nan
    close_price: float = nan
    position_size: float = nan
    profit_loss: float = nan
    change_pct: float = nan
    trade_commission: float = nan
    cumulative_return: float = nan