from dataclasses import dataclass
from typing import List, Dict, Any, Type, Hashable, Optional
import pandas as pd
from .trading import Trade, Position

@dataclass
class Result:

    returns: pd.Series
    trades: List[Trade]
    open_positions: List[Position]