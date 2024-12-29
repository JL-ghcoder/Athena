import pandas as pd
from datetime import timedelta

def sort_the_factor(factor_data, factor, ascending=False):
    # 排序截面因子数据，默认从高到低
    # 这里的factor_data得是当天的因子截面数据
    '''
    输入:
    000651.XSHE  market_cap              3.726144e+11
                debt_to_equity_ratio    1.357076e+00
    600000.XSHG  market_cap              2.841287e+11
                debt_to_equity_ratio    1.222372e+01

    返回"
                   2020-01-02
    000651.XSHE  4.084681e+11
    600000.XSHG  3.660204e+11
    '''
    factor_data = pd.DataFrame(factor_data)
    selected_factor_series = factor_data.xs(factor, level=1, axis=0)

    # 去掉因子值为 0 的行
    selected_factor_series = selected_factor_series[selected_factor_series.iloc[:, 0] != 0]
    
    # 移除含有空值的行，这些股票不能参与排序
    selected_factor_series = selected_factor_series.dropna()

    sorted_factor_series = selected_factor_series.sort_values(by=selected_factor_series.columns[0], ascending=ascending)
    
    return sorted_factor_series

# 从低到高的顺序进行分桶 
def classify_factors_into_buckets(factor_data, buckets: int = 5, ascending: bool = True):
    sorted_factor_series = factor_data.iloc[:, 0] # 改成一维数据以便于分桶

    # 如果是降序，将数据取反再分桶
    if not ascending:
        sorted_factor_series = -sorted_factor_series
        
    buckets = pd.qcut(sorted_factor_series, buckets, labels=False) + 1 
    return buckets


def calculate_benchmark_net_value(benchmark_df, start_date=None, end_date=None):
    """
    根据每日的开盘价和收盘价计算benchmark的净值,可以指定起始和结束日期
    
    :param benchmark_df: 包含 `Close` 列的 DataFrame, Index 为 `trade_date`
    :param start_date: 起始日期，格式为 'YYYY-MM-DD'，可选
    :param end_date: 结束日期，格式为 'YYYY-MM-DD'，可选
    :return: 带有 `net_value` 列的新 DataFrame,表示每日基准的累计净值
    """
    # 日期过滤
    if start_date or end_date:
        start_date = pd.to_datetime(start_date) if start_date else benchmark_df.index[0]
        end_date = pd.to_datetime(end_date) if end_date else benchmark_df.index[-1]
        benchmark_df = benchmark_df.loc[start_date:end_date].copy()
    else:
        benchmark_df = benchmark_df.copy()

    # 计算日收益率
    benchmark_df['daily_return'] = benchmark_df['Close'].pct_change()
    
    # 计算累计净值（起始净值为 1.0）
    benchmark_df['benchmark_net_value'] = (1 + benchmark_df['daily_return']).cumprod()
    benchmark_df['benchmark_net_value'].iloc[0] = 1  # 起始净值设置为 1.0
    
    return benchmark_df[['benchmark_net_value']]


# 修饰符
def run_weekly(method):
    def wrapper(self, i, record):
        # 获取当前日期
        date = self.data.index[i]
        
        # 检查是否达到下次运行时间
        if not hasattr(self, '_next_run_date') or date >= self._next_run_date:
            # 执行被装饰的方法
            result = method(self, i, record)
            
            self._next_run_date = date + timedelta(days=7)
            
            return result
        
    return wrapper

def run_monthly(method):
    def wrapper(self, i, record):
        # 获取当前日期
        date = self.data.index[i]
        
        # 检查是否达到下次运行时间
        if not hasattr(self, '_next_run_date') or date >= self._next_run_date:
            # 执行被装饰的方法
            result = method(self, i, record)
            
            self._next_run_date = date + timedelta(days=30)
            
            return result
        
    return wrapper


def resample_to_higher_freq(df, target_freq='1D'):
    """
    将低级别 K线数据合并成高级别数据
    :param df: 低级别的K线数据，包含列 ["Open time", "Close time", "Open", "High", "Low", "Close", "Volume", ...]
    :param target_freq: 目标频率，例如 "1D" 表示合并成日级别数据
    :return: 合并后的 DataFrame
    """

    # 确保 Open time 为 datetime 类型
    df['Open time'] = pd.to_datetime(df['Open time'])

    # 设置 Open time 为索引，以便 resample 操作
    df = df.set_index('Open time')

    # 定义合并逻辑
    resampled = df.resample(target_freq).agg({
        'Open': 'first',              # 第一个 Open 值
        'High': 'max',                # 最高价
        'Low': 'min',                 # 最低价
        'Close': 'last',              # 最后一个 Close 值
        'Volume': 'sum',              # 成交量总和
        'Quote asset volume': 'sum',  # Quote asset volume 总和
        'Number of trades': 'sum',    # 成交笔数总和
        'Taker buy base asset volume': 'sum',  # 主动买入成交量总和
        'Taker buy quote asset volume': 'sum'  # 主动买入成交额总和
    })

    # 重新创建 Close time 列，表示每个周期的结束时间
    resampled['Close time'] = resampled.index + pd.to_timedelta(target_freq) - pd.Timedelta(milliseconds=1)

    # 将索引重置为普通列
    resampled = resampled.reset_index().rename(columns={"Open time": "Open time"})

    # 调整列顺序
    resampled = resampled[[
        'Open time', 'Close time', 'Open', 'High', 'Low', 'Close',
        'Volume', 'Quote asset volume', 'Number of trades',
        'Taker buy base asset volume', 'Taker buy quote asset volume'
    ]]

    return resampled