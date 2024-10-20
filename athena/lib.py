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
    # 移除含有空值的行，这些股票不能参与排序
    selected_factor_series = selected_factor_series.dropna()

    sorted_factor_series = selected_factor_series.sort_values(by=selected_factor_series.columns[0], ascending=ascending)
    return sorted_factor_series

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