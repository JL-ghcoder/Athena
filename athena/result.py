from dataclasses import dataclass
from typing import List, Dict, Any, Type, Hashable, Optional
import pandas as pd
from .trading import Trade, Position

@dataclass
class Result:

    returns: pd.Series # 总收益
    long_returns: pd.Series # 多头收益
    short_returns: pd.Series # 空头收益


    net_value: pd.Series # 净值
    trades: List[Trade] # 交易列表
    open_positions: List[Position]
    benchmark: pd.DataFrame