import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd
import os
import warnings
import numpy as np
warnings.filterwarnings('ignore')

from typing import Type
from .result import Result  # 导入定义 Result 的模块
from .factor_research import run_factor_multiple_returns

from dotenv import load_dotenv
load_dotenv()

# 配色方案
color_map = plt.get_cmap('Set1')
color_map_alpha = plt.get_cmap('Pastel1')
plt.rc('font', family='Arial')

# 绘图标准用Arial字体，标题用regular_font，其他用italics_font
# size全部为12
# pad为12
# figsize为7,5
regular_font_path = os.getenv('regular_font')
legend_font_path = os.getenv('legend_font')
bold_font_path = os.getenv('bold_font')
italics_font_path = os.getenv('italics_font')

regular_font = fm.FontProperties(fname=regular_font_path, size=12)
legend_font = fm.FontProperties(fname=legend_font_path, size=10)
bold_font = fm.FontProperties(fname=bold_font_path, size=12)
italics_font = fm.FontProperties(fname=italics_font_path, size=12)

class Visualization:
    def __init__(self, res: Result):
        # 传入Result对象
        self.result = res

    def plot_portfolio_returns(self, use_benchmark: bool = True):

        plt.figure(figsize=(10, 5))
        plt.plot(self.result.net_value.index, self.result.net_value, color = color_map(0), lw=2, label='Portfolio Returns')
        
        if use_benchmark:
            plt.plot(self.result.benchmark.index, self.result.benchmark['benchmark_net_value'], color = color_map(1), lw=2, label='Benchmark Returns')
        
        plt.title('Portfolio Returns and Benchmark', pad=12, fontproperties=bold_font)
        plt.xlabel('Time', labelpad=12, fontproperties=regular_font)
        plt.ylabel('Returns', labelpad=12, fontproperties=regular_font)
        plt.legend(loc='best', prop=legend_font)
        plt.grid(True)
        plt.show()
    
    def plot_long_short_portfolio_returns(self):

        long_returns = self.result.long_returns + self.result.returns[0]
        short_returns = self.result.short_returns + self.result.returns[0]

        long_net_value = long_returns / self.result.returns[0]
        short_net_value = short_returns / self.result.returns[0]
        
        plt.figure(figsize=(10, 5))
        plt.plot(long_net_value.index, long_net_value, color=color_map(0), lw=2, label='Long Net Value')
        plt.plot(short_net_value.index, short_net_value, color=color_map(1), lw=2, label='Short Net Value')
        plt.plot(self.result.net_value.index, self.result.net_value, color = color_map(2), lw=2, label='Long and Short Returns')
        
        plt.title('Long and Short Portfolio Returns', pad=12, fontproperties=bold_font)
        plt.xlabel('Time', labelpad=12, fontproperties=regular_font)
        plt.ylabel('Returns', labelpad=12, fontproperties=regular_font)
        plt.legend(loc='best', prop=legend_font)
        plt.grid(True)
        plt.show()
    
    def plot_factor_multiple_returns(self, layered_results, long_and_short=None, label='Long and Short Portfolio'):
        # 可视化各层收益差异
        plt.figure(figsize=(10, 5))
        
        for bucket, returns in layered_results.items():
            plt.plot(returns.index, returns, lw=2, label=bucket)

        if long_and_short is not None:
            plt.plot(long_and_short.index, long_and_short, lw=2, label=label)

        plt.title('Multi-Layer Factor Returns', pad=12, fontproperties=bold_font)
        plt.xlabel('Time', labelpad=12, fontproperties=regular_font)
        plt.ylabel('Returns', labelpad=12, fontproperties=regular_font)
        plt.legend(loc='best', prop=legend_font)
        plt.grid(True)
        plt.show()

    def calculate_metrics(self):
        """
        计算回测指标：
        - 年化收益率
        - 年化波动率
        - 最大回撤
        - 夏普比率
        - 收益基准超额
        """
        metrics = {}
        net_value = self.result.net_value  # 策略净值
        returns = net_value.pct_change().dropna()  # 策略每日收益率
        benchmark_net_value = self.result.benchmark['benchmark_net_value']  # 基准净值
        benchmark_returns = benchmark_net_value.pct_change().dropna()  # 基准每日收益率
        
        # 策略年化收益率
        strategy_total_return = net_value.iloc[-1] / net_value.iloc[0] - 1
        strategy_annualized_return = (1 + strategy_total_return) ** (252 / len(net_value)) - 1  # 假设每年252个交易日
        metrics['strategy_annualized_return'] = self.format_as_percentage(strategy_annualized_return)

        # 基准年化收益率
        benchmark_total_return = benchmark_net_value.iloc[-1] / benchmark_net_value.iloc[0] - 1
        benchmark_annualized_return = (1 + benchmark_total_return) ** (252 / len(benchmark_net_value)) - 1  # 假设每年252个交易日
        metrics['benchmark_annualized_return'] = self.format_as_percentage(benchmark_annualized_return)

        # 策略年化波动率
        strategy_annualized_volatility = returns.std() * np.sqrt(252)
        metrics['strategy_annualized_volatility'] = self.format_as_percentage(strategy_annualized_volatility)

        # 基准年化波动率
        benchmark_returns = benchmark_net_value.pct_change().dropna()  # 使用每日收益率
        benchmark_annualized_volatility = benchmark_returns.std() * np.sqrt(252)
        metrics['benchmark_annualized_volatility'] = self.format_as_percentage(benchmark_annualized_volatility)
        
        # 策略最大回撤 (Maximum Drawdown)
        rolling_max = net_value.cummax()
        drawdown = net_value / rolling_max - 1
        strategy_max_drawdown = drawdown.min()
        metrics['strategy_max_drawdown'] = self.format_as_percentage(strategy_max_drawdown)
        
        # 基准最大回撤 (Maximum Drawdown)
        rolling_max = benchmark_net_value.cummax()
        drawdown = benchmark_net_value / rolling_max - 1
        benchmark_max_drawdown = drawdown.min()
        metrics['benchmark_max_drawdown'] = self.format_as_percentage(benchmark_max_drawdown)

        # 夏普比率 (Sharpe Ratio)
        risk_free_rate = 0.02  # 假设年化无风险收益为 2%
        sharpe_ratio = (strategy_annualized_return - risk_free_rate) / strategy_annualized_volatility
        metrics['sharpe_ratio'] = self.format_as_float(sharpe_ratio)
        
        # 收益基准超额 (Alpha/Excess Return)
        benchmark_total_return = benchmark_net_value.iloc[-1] / benchmark_net_value.iloc[0] - 1
        alpha = strategy_annualized_return - benchmark_total_return
        metrics['alpha'] = self.format_as_percentage(alpha)

        return metrics

    def format_as_percentage(self, value):
        return f"{value * 100:.2f}%"  # 转为百分数格式

    def format_as_float(self, value):
        return f"{value:.2f}"  # 浮点值保留两位小数
    
    def calculate_and_plot_open_close_volumes(self):
        """
        基于开仓和平仓时间分别计算并可视化多头与空头每日换手率。
        :param res: 回测结果对象 (Result)
        :return: (多头每日开仓金额, 多头每日平仓金额, 空头每日开仓金额, 空头每日平仓金额)
        """
        # 1. 记录每日开仓和平仓的成交金额，并区分多空头
        trade_data_long_open = []  # 多头开仓数据
        trade_data_long_close = []  # 多头平仓数据
        trade_data_short_open = []  # 空头开仓数据
        trade_data_short_close = []  # 空头平仓数据

        for trade in self.result.trades:
            if trade.short:  # 空头
                # 记录空头开仓金额（按保证金）
                trade_data_short_open.append({'date': trade.open_date, 'amount': trade.position_size * trade.open_price})
                # 记录空头平仓金额
                trade_data_short_close.append({'date': trade.close_date, 'amount': trade.position_size * trade.close_price - trade.trade_commission})
            else:  # 多头
                # 记录多头开仓金额
                trade_data_long_open.append({'date': trade.open_date, 'amount': trade.position_size * trade.open_price})
                # 记录多头平仓金额
                trade_data_long_close.append({'date': trade.close_date, 'amount': trade.position_size * trade.close_price - trade.trade_commission})

        # 2. 构造成交金额 DataFrame，并按日期汇总
        # 多头开仓与平仓
        trades_long_open_df = pd.DataFrame(trade_data_long_open)
        trades_long_close_df = pd.DataFrame(trade_data_long_close)
        daily_trade_amount_long_open = trades_long_open_df.groupby('date')['amount'].sum()
        daily_trade_amount_long_close = trades_long_close_df.groupby('date')['amount'].sum()

        # 空头开仓与平仓
        trades_short_open_df = pd.DataFrame(trade_data_short_open)
        trades_short_close_df = pd.DataFrame(trade_data_short_close)
        daily_trade_amount_short_open = trades_short_open_df.groupby('date')['amount'].sum()
        daily_trade_amount_short_close = trades_short_close_df.groupby('date')['amount'].sum()

        # 3. 确保日期索引与策略时间对齐，填补缺失日期
        dates = self.result.returns.index  # 策略的时间索引（假设res.returns已经处理为开盘前的数据）
        daily_trade_amount_long_open = daily_trade_amount_long_open.reindex(dates, fill_value=0)
        daily_trade_amount_long_close = daily_trade_amount_long_close.reindex(dates, fill_value=0)
        daily_trade_amount_short_open = daily_trade_amount_short_open.reindex(dates, fill_value=0)
        daily_trade_amount_short_close = daily_trade_amount_short_close.reindex(dates, fill_value=0)

        # 4. 可视化多头和空头的每日开仓/平仓金额
        plt.figure(figsize=(10, 5))

        # 多头开仓和平仓金额
        plt.bar(daily_trade_amount_long_close.index, daily_trade_amount_long_close.values, color='green', alpha=0.6, label='Long Close', width=15, zorder=3)
        plt.bar(daily_trade_amount_long_open.index, daily_trade_amount_long_open.values, color='red', alpha=0.6, label='Long Open', width=15, zorder=2)

        plt.title("Long Open and Close", pad=12, fontproperties=bold_font)
        plt.xlabel("Date", labelpad=12, fontproperties=regular_font)
        plt.ylabel("Amount", labelpad=12, fontproperties=regular_font)
        plt.legend(loc='best', prop=legend_font)
        plt.grid(True)

        plt.tight_layout()
        plt.show()

        plt.figure(figsize=(10, 5))

        # 多头开仓和平仓金额
        plt.bar(daily_trade_amount_short_close.index, daily_trade_amount_short_close.values, color='green', alpha=0.6, label='Short Close', width=15, zorder=3)
        plt.bar(daily_trade_amount_short_open.index, daily_trade_amount_short_open.values, color='red', alpha=0.6, label='Short Open', width=15, zorder=2)

        plt.title("Short Open and Close", pad=12, fontproperties=bold_font)
        plt.xlabel("Date", labelpad=12, fontproperties=regular_font)
        plt.ylabel("Amount", labelpad=12, fontproperties=regular_font)
        plt.legend(loc='best', prop=legend_font)
        plt.grid(True)

        plt.tight_layout()
        plt.show()

        #return (daily_trade_amount_long_open, daily_trade_amount_long_close, daily_trade_amount_short_open, daily_trade_amount_short_close)