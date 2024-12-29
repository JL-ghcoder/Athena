import pandas as pd
import numpy as np

from .backtesting import Strategy, Backtest
from .lib import run_monthly, sort_the_factor

# 分层跑因子的第n个bucket收益
def run_strategy_with_buckets(
    data: pd.DataFrame,
    factors_df: pd.DataFrame,
    factor_name: str = 'total_mv',  # 因子名称，例如 'total_mv'
    num_buckets: int = 5, # 分组数量，每一天都要先把因子值分成指定区间，然后买指定区间的标的
    target_buckets: int = 1, # 指定区间
):
    """
    封装回测策略逻辑为一个可调用函数
    :param strategy: 策略类
    :param data: 市场行情数据
    :param factors_df: 因子数据
    :param factor_name: 用于计算的因子字段名称
    :param num_long_short: 多头和空头分别持有的标的数量
    :param target_percent: 每个标的的仓位百分比
    """
    class FactorInvestStrategy(Strategy):
        def init(self):
            pass

        @run_monthly  # 调仓频率默认为月度
        def next(self, i, record):
            date = self.data.index[i]

            # 获取当天因子数据并排序
            day_factors = factors_df.loc[date]
            sorted_factor_series = sort_the_factor(day_factors, factor_name)  # 排序
            sorted_factor_series = sorted_factor_series.iloc[:, 0]
            # 移除因子值为NaN和0的标的(这里是以防0太多干扰我们分桶的结果)
            sorted_factor_series = sorted_factor_series[sorted_factor_series != 0].dropna()

            #print(sorted_factor_series)

            # 将因子值分为 num_buckets 组，每组分配到对应 bucket
            # 默认行为是从低到高对数据进行分桶（bucket）操作
            buckets = pd.qcut(sorted_factor_series, num_buckets, labels=False) + 1  # [1, num_buckets]
            target_stocks = sorted_factor_series[buckets == target_buckets].index.tolist()

            # 获取当前持仓
            current_long_positions, _ = self.broker.current_position_status()

            # 平仓逻辑
            for stock in current_long_positions:
                if stock not in target_stocks:
                    self.close(symbol=stock, price=record[(stock, 'Open')])
                        
            # 调仓逻辑
            if len(target_stocks) > 0:
                # 平分资金到目标区间内的所有股票
                stock_target_percent = 1 / len(target_stocks)

                for stock in target_stocks:
                    self.order_target_percent(
                        symbol=stock,
                        target_percent=stock_target_percent,  # 平分到每个标的
                        price=record[(stock, "Close")],
                        short=False
                    )


    # 运行业务逻辑，调用回测框架
    backtest = Backtest(FactorInvestStrategy, data, commission=0.001, cash=100_0000)
    res = backtest.run()

    return res

# 因子分层收益
def run_factor_multiple_returns(data, factors_df, factor_name, num_buckets=5):
    """
    针对指定因子进行分层收益测试。
    :param factor_name: 因子名称
    :param num_buckets: 分层数量 (默认为5组)
    """
    all_results = {}
    
    # 遍历分层
    for bucket_idx in range(1, num_buckets + 1):

        print(f"因子分层测回测 {factor_name}, Bucket {bucket_idx}/{num_buckets}...")
                
        # 运行策略
        result = run_strategy_with_buckets(
            data=data,
            factors_df=factors_df,
            factor_name=factor_name,
            num_buckets=num_buckets,
            target_buckets=bucket_idx
        )
        
        all_results[f"Bucket {bucket_idx}"] = result.net_value
    
    return all_results