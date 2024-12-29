from datetime import datetime
from typing import List, Dict, Any, Type, Hashable, Optional
from math import nan, isnan
from decimal import Decimal, getcontext, ROUND_DOWN

getcontext().rounding = ROUND_DOWN

import pandas as pd
import logging
from .log_config import setup_logging
from .trading import Position, Trade, PrecisionConfig

class Broker:
    '''
    Broker类负责管理与交易相关的所有功能
    包括开仓,关仓以及按比例进行调仓
    同时它还能做一些中间数据的记录,例如每日新增多/空头收益
    '''
    def __init__(self, cash: float, commission: float):
        self.cash = PrecisionConfig.round_value(Decimal(str(cash)))
        self.commission = PrecisionConfig.round_commission(Decimal(str(commission)))
        self.date = None

        self.open_positions = []
        self.trades = []
        self.assets_value = PrecisionConfig.round_value(Decimal('0'))
        self.cumulative_return = self.cash
        self.returns: List[float] = []

        # 新增多/空头每日收益记录
        self.long_returns = []
        self.short_returns = []

    def open(self, price: float, size: Optional[float] = None, symbol: Optional[str] = None, 
            short=False, is_fractional=False):
        '''开仓方法'''
        price = PrecisionConfig.round_price(Decimal(str(price)))
        
        if isnan(float(price)) or price <= 0 or (size is not None and (isnan(size) or size <= .0)):
            print("参数错误，请检查价格和仓位大小是否正确")
            logging.info("参数错误，请检查价格和仓位大小是否正确")
            return False

        # 计算开仓数量
        if is_fractional and size > 0 and size <= 1:  # 分数仓
            size = PrecisionConfig.round_size(
                (Decimal(size) * self.cash) / (price * (Decimal(1) + self.commission))
            )
        elif size is not None:  # 固定仓位
            size = PrecisionConfig.round_size(Decimal(str(size)))
        else:  # 全仓
            size = PrecisionConfig.round_size(
                self.cash / (price * (Decimal(1) + self.commission))
            )

        # 计算开仓成本和手续费
        open_commission = PrecisionConfig.round_commission(size * price * self.commission)
        open_cost = PrecisionConfig.round_value(size * price * (Decimal(1) + self.commission))

        # 判断资金是否充足
        TOLERANCE = Decimal('100')
        if isnan(float(size)) or size <= 0 or (self.cash + TOLERANCE) < open_cost:
            print(f"开仓失败，可用资金不足或仓位大小无效")
            print(f"可用资金: {self.cash:.2f}, 开仓成本: {open_cost:.2f}")
            logging.info("开仓失败，可用资金不足或仓位大小无效")
            logging.info(f"可用资金: {self.cash:.2f}, 开仓成本: {open_cost:.2f}")
            return False

        # 建立仓位
        position = Position(
            symbol=symbol,
            open_date=self.date,
            open_price=float(price),
            position_size=float(size),
            is_short=short,
            open_commission=float(open_commission)
        )
        position.update(last_date=self.date, last_price=float(price))

        # 更新账户状态
        self.cash = PrecisionConfig.round_value(self.cash - open_cost)
        self.assets_value = PrecisionConfig.round_value(
            self.assets_value + Decimal(str(position.current_value))
        )
        self.open_positions.extend([position])

        logging.info(f"开仓: {position}")
        return True

    def close(self, price: float, symbol: Optional[str] = None, 
             position: Optional[Position] = None, size: Optional[float] = None):
        '''关仓方法'''
        price = PrecisionConfig.round_price(Decimal(str(price)))
        if size is not None:
            size = PrecisionConfig.round_size(Decimal(str(size)))

        if isnan(float(price)) or price <= 0:
            return False

        if position is None:
            for pos in self.open_positions[:]:
                if pos.symbol == symbol:
                    if size is not None:
                        self.close(price=price, position=pos, size=size)
                    else:
                        self.close(price=price, position=pos)
        else:
            if size is None or size >= position.position_size:
                # 全部平仓
                position.update(last_date=self.date, last_price=float(price))
                trade_commission = PrecisionConfig.round_commission(  # 使用 round_commission 而不是 round_value
                    position.last_price * position.position_size * self.commission
                )  

                self.cumulative_return = PrecisionConfig.round_value(
                    self.cumulative_return + position.profit_loss - trade_commission
                )

                # 创建交易记录
                trade = Trade(
                    position.symbol, position.is_short, position.open_date, position.last_date,
                    float(position.open_price), float(position.last_price), 
                    float(position.position_size), float(position.profit_loss),
                    position.change_pct, float(trade_commission), float(self.cumulative_return)
                )
                self.trades.extend([trade])

                # 更新账户状态
                self.assets_value = PrecisionConfig.round_value(
                    self.assets_value - position.current_value
                )
                self.cash = PrecisionConfig.round_value(
                    self.cash + position.current_value - trade_commission
                )
                self.open_positions.remove(position)

                logging.info(f"清仓: {trade}")
            else:
                # 部分平仓
                position.update(last_date=self.date, last_price=float(price))
                partial_ratio = size / position.position_size
                closed_value = PrecisionConfig.round_value(
                    position.current_value * partial_ratio
                )
                closed_profit_loss = PrecisionConfig.round_value(
                    position.profit_loss * partial_ratio
                )
                trade_commission = PrecisionConfig.round_commission(
                    price * size * self.commission
                )

                # 更新剩余仓位
                position.position_size = PrecisionConfig.round_size(
                    position.position_size - size
                )
                position.current_value = PrecisionConfig.round_value(
                    position.current_value - closed_value
                )
                position.update(last_date=self.date, last_price=float(price))

                self.cumulative_return = PrecisionConfig.round_value(
                    self.cumulative_return + closed_profit_loss - trade_commission
                )

                # 创建交易记录
                trade = Trade(
                    position.symbol, position.is_short, position.open_date, self.date,
                    float(position.open_price), float(price), float(size),
                    float(closed_profit_loss),
                    float((price - position.open_price) / position.open_price),
                    float(trade_commission), float(self.cumulative_return)
                )
                self.trades.extend([trade])

                # 更新账户状态
                self.assets_value = PrecisionConfig.round_value(
                    self.assets_value - closed_value
                )
                self.cash = PrecisionConfig.round_value(
                    self.cash + closed_value - trade_commission
                )

                logging.info(f"部分清仓: {trade}")

        return True

    def order_target_percent(self, symbol: str, target_percent: float, price: float, short=False):
        '''按目标百分比调整仓位'''
        price = PrecisionConfig.round_price(Decimal(str(price)))
        
        if isnan(float(price)) or price <= 0 or isnan(target_percent) or target_percent < 0 or target_percent > 1:
            print("参数错误，请检查价格和仓位比例是否正确")
            return False

        # 计算目标价值和可用资产
        buffer = Decimal('0.01')
        total_assets = PrecisionConfig.round_value(
            (self.cash + self.assets_value) * (Decimal('1') - buffer)
        )
        target_value = PrecisionConfig.round_value(
            total_assets * Decimal(str(target_percent))
        )

        # 查找现有仓位
        existing_position = None
        for position in self.open_positions:
            if position.symbol == symbol:
                existing_position = position
                break

        # 处理目标仓位为0的情况
        if target_percent == 0:
            if existing_position:
                logging.info("调仓比例为0, 直接关闭仓位")
                return self.close(price=float(price), position=existing_position)
            return True

        # 处理新开仓的情况
        if existing_position is None:
            logging.info("没有持仓,直接开仓")
            size = PrecisionConfig.round_size(
                target_value / (price * (Decimal(1) + self.commission))
            )
            return self.open(price=float(price), size=float(size), symbol=symbol, short=short)

        # 调整现有仓位
        current_value = existing_position.current_value
        if abs(target_value - current_value) <= Decimal('1e-6'):
            return True

        if target_value > current_value:
            # 增加仓位
            additional_value = target_value - current_value
            size = PrecisionConfig.round_size(
                additional_value / (price * (Decimal(1) + self.commission))
            )
            logging.info("增加仓位")
            return self.open(price=float(price), size=float(size), symbol=symbol, short=short)
        else:
            # 减少仓位
            reduce_value = current_value - target_value
            size_to_reduce = PrecisionConfig.round_size(reduce_value / price)
            if existing_position.position_size > size_to_reduce:
                logging.info("减少仓位")
                return self.close(
                    price=float(price),
                    position=existing_position,
                    size=float(size_to_reduce)
                )
            else:
                logging.info("要减少的仓位大于现有仓位,直接关闭仓位")
                return self.close(price=float(price), position=existing_position)

    def update_seperate_long_short_returns(self):
        '''更新多空头收益'''
        long_profit = Decimal('0')
        short_profit = Decimal('0')

        # 计算未平仓收益
        for position in self.open_positions:
            if position.is_short:
                short_profit = PrecisionConfig.round_value(
                    short_profit + position.profit_loss
                )
            else:
                long_profit = PrecisionConfig.round_value(
                    long_profit + position.profit_loss
                )

        # 计算已平仓收益
        for trade in self.trades:
            if trade.short:
                short_profit = PrecisionConfig.round_value(
                    short_profit + trade.profit_loss - trade.trade_commission
                )
            else:
                long_profit = PrecisionConfig.round_value(
                    long_profit + trade.profit_loss - trade.trade_commission
                )

        # 记录收益
        self.long_returns.append(float(long_profit))
        self.short_returns.append(float(short_profit))

    def current_position_status(self):
        '''获取当前持仓状态'''
        long_positions = []
        short_positions = []
        for position in self.open_positions:
            if position.is_short:
                short_positions.append(position.symbol)
            else:
                long_positions.append(position.symbol)
        return long_positions, short_positions

    def current_position_count(self):
        '''获取当前持仓数量'''
        long_c = 0
        short_c = 0
        for position in self.open_positions:
            if position.is_short:
                short_c += 1
            else:
                long_c += 1
        return long_c, short_c