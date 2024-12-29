from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Type, Hashable, Optional
from decimal import Decimal
import pandas as pd

from .trading import Position, Trade, PrecisionConfig
from .result import Result
from .broker import Broker

import logging
from .log_config import setup_logging

setup_logging()

class Strategy(ABC):
    """策略基类"""

    @abstractmethod
    def init(self):
        """策略初始化"""
        pass

    @abstractmethod
    def next(self, i: int, record: Dict[Hashable, Any]):
        """策略逻辑部分"""
        pass

    def __init__(self):
        self.broker: Broker = None  
        self.data = pd.DataFrame()  
        self.date = None
        self.symbols: List[str] = []
        self.records: List[Dict[Hashable, Any]] = []  
        self.index: List[datetime] = []
        self.benchmark = pd.DataFrame()  

    def open(self, price: float, size: Optional[float] = None, 
             symbol: Optional[str] = None, short=False, is_fractional=False):
        '''开仓接口'''
        return self.broker.open(price, size, symbol, short, is_fractional)    

    def close(self, price: float, symbol: Optional[str] = None, 
             position: Optional[Position] = None, size: Optional[float] = None):
        '''关仓接口'''
        return self.broker.close(price, symbol, position, size)
    
    def order_target_percent(self, symbol: str, target_percent: float, 
                           price: float, short=False):
        '''按目标百分比调仓接口'''
        return self.broker.order_target_percent(symbol, target_percent, price, short)

    def __eval(self, *args, **kwargs):
        '''策略评估方法'''
        self.cumulative_return = self.broker.cash
        self.assets_value = PrecisionConfig.round_value(Decimal('0'))

        # 初始化策略
        self.init(*args, **kwargs)

        # 遍历历史数据
        for i, record in enumerate(self.records):
            self.date = self.index[i]
            self.broker.date = self.index[i]

            logging.info(f"时间: {self.date}")
            logging.info(f"可用资金: {self.broker.cash:.2f}")
            logging.info(f"持仓价值: {self.broker.assets_value:.2f}")
            logging.info("\n")

            # 执行策略逻辑
            self.next(i, record)

            # 更新持仓状态
            for position in self.broker.open_positions:
                last_price = record.get(
                    (position.symbol, 'Close'),
                    record.get('Close', 0)
                )
                if last_price > 0:
                    position.update(last_date=self.date, last_price=last_price)

            # 合并同向持仓
            self.merge_positions()

            # 更新资产价值
            self.broker.assets_value = PrecisionConfig.round_value(
                sum((Decimal(str(position.current_value)) 
                     for position in self.broker.open_positions), 
                    Decimal('0'))
            )
            self.broker.returns.append(float(self.broker.cash + self.broker.assets_value))

            # 更新多空收益
            self.broker.update_seperate_long_short_returns()

            logging.info("持仓：")
            for position in self.broker.open_positions:
                logging.info(position)
            logging.info("-----------------------\n")
        
        # 回测结束处理
        self.close_all_positions()

        final_total_value = PrecisionConfig.round_value(
            self.broker.cash + Decimal(str(self.broker.assets_value))
        )
        print(f"回测结束，总资金: {final_total_value:.2f}")
        logging.info(f"回测结束，总资金: {final_total_value:.2f}")

        # 计算回测结果
        returns_series = pd.Series(
            index=self.index, 
            data=self.broker.returns, 
            dtype=float
        )
        long_returns_series = pd.Series(
            index=self.index, 
            data=self.broker.long_returns, 
            dtype=float
        )
        short_returns_series = pd.Series(
            index=self.index, 
            data=self.broker.short_returns, 
            dtype=float
        )

        initial_cash = float(self.broker.returns[0])
        net_value_series = returns_series / initial_cash

        return Result(
            returns=returns_series,
            long_returns=long_returns_series,
            short_returns=short_returns_series,
            net_value=net_value_series,
            trades=self.broker.trades,
            open_positions=self.broker.open_positions,
            benchmark=self.benchmark
        )
    
    def close_all_positions(self):
        """清算所有未平仓持仓"""
        for position in self.broker.open_positions[:]:
            last_price = self.records[-1].get(
                (position.symbol, 'Close'),
                self.records[-1].get('Close', 0)
            )
                
            if last_price > 0:
                self.broker.close(price=last_price, position=position)
            else:
                print(f"无法清算 {position.symbol}, 缺失有效价格！")

        if not self.broker.open_positions:
            print("所有未平仓持仓已经清算完毕！")
        else:
            print(f"仍存在未清算持仓: {self.broker.open_positions}")
        
        self.broker.assets_value = PrecisionConfig.round_value(Decimal('0'))
    
    def merge_positions(self):
        '''合并同向持仓'''
        merged_positions = []
        merged_map = {}

        for position in self.broker.open_positions:
            key = (position.symbol, position.is_short)
            if key not in merged_map:
                merged_map[key] = {
                    "symbol": position.symbol,
                    "open_date": position.open_date,
                    "last_date": position.last_date,
                    "is_short": position.is_short,
                    "last_price": position.last_price,
                    "position_size": Decimal('0'),
                    "current_value": Decimal('0'),
                    "weighted_open_price": Decimal('0'),
                    "open_commission": Decimal('0'),
                }

            merged_entry = merged_map[key]
            total_size = PrecisionConfig.round_size(
                merged_entry["position_size"] + Decimal(str(position.position_size))
            )

            if total_size > 0:
                merged_entry["weighted_open_price"] = PrecisionConfig.round_price(
                    (merged_entry["position_size"] * merged_entry["weighted_open_price"] +
                     Decimal(str(position.position_size)) * Decimal(str(position.open_price)))
                    / total_size
                )
            else:
                merged_entry["weighted_open_price"] = position.open_price

            merged_entry["position_size"] = total_size
            merged_entry["current_value"] = PrecisionConfig.round_value(
                merged_entry["current_value"] + Decimal(str(position.current_value))
            )
            merged_entry["open_commission"] = PrecisionConfig.round_commission(
                merged_entry["open_commission"] + Decimal(str(position.open_commission))
            )

            merged_entry["last_date"] = max(merged_entry["last_date"], position.last_date)
            merged_entry["last_price"] = position.last_price

        # 创建合并后的Position对象
        for key, merged_entry in merged_map.items():
            new_position = Position(
                symbol=merged_entry["symbol"],
                open_date=merged_entry["open_date"],
                open_price=float(merged_entry["weighted_open_price"]),
                position_size=float(merged_entry["position_size"]),
                is_short=merged_entry["is_short"]
            )
            new_position.open_commission = float(merged_entry["open_commission"])
            new_position.update(
                last_date=merged_entry["last_date"],
                last_price=float(merged_entry["last_price"])
            )
            merged_positions.append(new_position)

        self.broker.open_positions = merged_positions


class Backtest:
    """回测类"""
    def __init__(
        self,
        strategy: Type[Strategy],
        data: pd.DataFrame,
        cash: float = 10_000,
        commission: float = .0,
        benchmark: pd.DataFrame = None, # 这里传入的benchmark得是net value
        start_date: str = None,
        end_date: str = None
    ):
        self.strategy = strategy

        # 日期筛选
        if start_date or end_date:
            start_date = pd.to_datetime(start_date) if start_date else data.index[0]
            end_date = pd.to_datetime(end_date) if end_date else data.index[-1]
            data = data.loc[start_date:end_date]
            if benchmark is not None:
                benchmark = benchmark.loc[start_date:end_date]

        self.data = data
        self.cash = PrecisionConfig.round_value(Decimal(str(cash)))
        self.commission = PrecisionConfig.round_commission(Decimal(str(commission)))
        self.benchmark = benchmark

        columns = data.columns
        self.symbols = (columns.get_level_values(0).unique().tolist() 
                       if isinstance(columns, pd.MultiIndex) else [])
        self.records = data.to_dict('records')
        self.index = data.index.tolist()

    def run(self, *args, **kwargs):
        '''运行回测'''
        strategy = self.strategy()

        strategy.data = self.data
        strategy.symbols = self.symbols
        strategy.records = self.records
        strategy.index = self.index
        strategy.benchmark = self.benchmark
        strategy.broker = Broker(cash=float(self.cash), commission=float(self.commission))

        return strategy._Strategy__eval(*args, **kwargs)