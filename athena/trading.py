from dataclasses import dataclass
from typing import List, Dict, Any, Type, Hashable, Optional
from datetime import datetime
from decimal import Decimal, getcontext, ROUND_DOWN
from math import nan, isnan

getcontext().rounding = ROUND_DOWN  # 设置全局舍入模式为向下取整

class PrecisionConfig:
    """精度配置类"""
    PRICE_PRECISION = 8  # 价格精度
    SIZE_PRECISION = 8   # 数量精度
    VALUE_PRECISION = 2  # 金额精度(profit_loss, cumulative_return等)
    PCT_PRECISION = 4    # 百分比精度(change_pct等)
    COMMISSION_PRECISION = 8  # 手续费精度（需要更高精度）

    @classmethod
    def round_commission(cls, value: Decimal) -> Decimal:
        """处理手续费精度"""
        return value.quantize(Decimal(f"0.{'0' * cls.COMMISSION_PRECISION}"))

    @classmethod
    def round_price(cls, value: Decimal) -> Decimal:
        """处理价格精度"""
        return value.quantize(Decimal(f"0.{'0' * cls.PRICE_PRECISION}"))
    
    @classmethod
    def round_size(cls, value: Decimal) -> Decimal:
        """处理数量精度"""
        return value.quantize(Decimal(f"0.{'0' * cls.SIZE_PRECISION}"))
    
    @classmethod
    def round_value(cls, value: Decimal) -> Decimal:
        """处理金额精度"""
        return value.quantize(Decimal(f"0.{'0' * cls.VALUE_PRECISION}"))
    
    @classmethod
    def round_percentage(cls, value: Decimal) -> Decimal:
        """处理百分比精度"""
        return value.quantize(Decimal(f"0.{'0' * cls.PCT_PRECISION}"))

@dataclass
class Position:
    '''
    与订单相关的数据结构,记录每一个订单的基础信息
    每一次调用open,close方法都会更新仓位信息,包括新增一个Position或者关闭已经存在的Position对象
    '''
    symbol: Optional[str] = None
    open_date: Optional[datetime] = None
    last_date: Optional[datetime] = None
    open_price: Decimal = Decimal('0')
    last_price: Decimal = Decimal('0')
    position_size: Decimal = Decimal('0')
    profit_loss: Decimal = Decimal('0')
    change_pct: Decimal = Decimal('0')
    current_value: Decimal = Decimal('0')
    is_short: bool = False  
    open_commission: Decimal = Decimal('0')  

    def __post_init__(self):
        # 将构造函数传入的float值转换为Decimal并应用相应的精度
        if isinstance(self.open_price, float):
            self.open_price = PrecisionConfig.round_price(
                Decimal(str(self.open_price)) if not isnan(self.open_price) else Decimal('0')
            )
        if isinstance(self.last_price, float):
            self.last_price = PrecisionConfig.round_price(
                Decimal(str(self.last_price)) if not isnan(self.last_price) else Decimal('0')
            )
        if isinstance(self.position_size, float):
            self.position_size = PrecisionConfig.round_size(
                Decimal(str(self.position_size)) if not isnan(self.position_size) else Decimal('0')
            )
        if isinstance(self.open_commission, float):
            self.open_commission = PrecisionConfig.round_commission(Decimal(str(self.open_commission)))
    
    def update(self, last_date: datetime, last_price: float):
        '''更新仓位信息'''
        self.last_date = last_date
        self.last_price = PrecisionConfig.round_price(Decimal(str(last_price)))

        if self.is_short:
            self.profit_loss = PrecisionConfig.round_value(
                (self.open_price - self.last_price) * self.position_size
            )
            self.change_pct = PrecisionConfig.round_percentage(
                (Decimal('1') - self.last_price / self.open_price) * Decimal('100')
            )
            self.current_value = PrecisionConfig.round_value(
                self.open_price * self.position_size + self.profit_loss
            )
        else:
            self.profit_loss = PrecisionConfig.round_value(
                (self.last_price - self.open_price) * self.position_size
            )
            self.change_pct = PrecisionConfig.round_percentage(
                (self.last_price / self.open_price - Decimal('1')) * Decimal('100')
            )
            self.current_value = PrecisionConfig.round_value(
                self.open_price * self.position_size + self.profit_loss
            )

    def __str__(self):
        """美化输出格式"""
        return (
            f"Symbol: {self.symbol}, "
            f"Price: {self.last_price:.8f}, "
            f"Size: {self.position_size:.8f}, "
            f"P/L: {self.profit_loss:.2f}, "
            f"Change: {self.change_pct:.4f}%, "
            f"Value: {self.current_value:.2f}, "
            f"Open Commission: {self.open_commission:.8f}"
        )

@dataclass
class Trade:
    '''
    当订单被关闭后就会创造一个Trade的数据结构
    它代表的是一个完整交易的信息,从开仓到关仓全过程
    '''
    symbol: Optional[str] = None
    short: bool = False
    open_date: Optional[datetime] = None
    close_date: Optional[datetime] = None
    open_price: Decimal = Decimal('0')
    close_price: Decimal = Decimal('0')
    position_size: Decimal = Decimal('0')
    profit_loss: Decimal = Decimal('0')
    change_pct: Decimal = Decimal('0')
    trade_commission: Decimal = Decimal('0')
    cumulative_return: Decimal = Decimal('0')

    def __post_init__(self):
        # 将构造函数传入的float值转换为Decimal并应用相应的精度
        if isinstance(self.open_price, float):
            self.open_price = PrecisionConfig.round_price(
                Decimal(str(self.open_price)) if not isnan(self.open_price) else Decimal('0')
            )
        if isinstance(self.close_price, float):
            self.close_price = PrecisionConfig.round_price(
                Decimal(str(self.close_price)) if not isnan(self.close_price) else Decimal('0')
            )
        if isinstance(self.position_size, float):
            self.position_size = PrecisionConfig.round_size(
                Decimal(str(self.position_size)) if not isnan(self.position_size) else Decimal('0')
            )
        if isinstance(self.profit_loss, float):
            self.profit_loss = PrecisionConfig.round_value(
                Decimal(str(self.profit_loss)) if not isnan(self.profit_loss) else Decimal('0')
            )
        if isinstance(self.change_pct, float):
            self.change_pct = PrecisionConfig.round_percentage(
                Decimal(str(self.change_pct)) if not isnan(self.change_pct) else Decimal('0')
            )
        if isinstance(self.trade_commission, float):
            self.trade_commission = PrecisionConfig.round_commission(Decimal(str(self.trade_commission)))
        if isinstance(self.cumulative_return, float):
            self.cumulative_return = PrecisionConfig.round_value(Decimal(str(self.cumulative_return)))

    def __str__(self):
        """美化输出格式"""
        return (
            f"Symbol: {self.symbol}, "
            f"Open Price: {self.open_price:.8f}, "
            f"Close Price: {self.close_price:.8f}, "
            f"Size: {self.position_size:.8f}, "
            f"P/L: {self.profit_loss:.2f}, "
            f"Change: {self.change_pct:.4f}%, "
            f"Trade Commission: {self.trade_commission:.8f}"
        )