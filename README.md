# Athena

<div align="center">
    <img src="pics/logo.png" alt="athena logo" style="width:150px;">
    <p></p>
    <p><strong>基于多资产的因子回测框架</strong></p>
</div>


## 概览
Athena是一款简单的多资产回测工具，基于事件型回测框架，拥有非常简单的程序结构，易于上手。

Athena简化了订单的处理，只考虑订单open和close两种情况：所有资产都通过open来开仓（指定多空），通过close关仓（可以部分关仓）。这对于追踪因子在不同标的上的表现至关重要，而SL，TP这种更适合单标的交易的订单结构该框架没有提供支持。

Athena主要由3个模块组成：
1. **Strategy**：策略模块，继承自Strategy基类，实现了策略的初始化和每一个bar的处理
2. **Backtest**：回测模块，实现了回测的初始化，运行，结果的输出
3. **Broker**: 交易模块，实现了交易的初始化，订单的生成，撮合，成交的记录

除此之外我构造了3个典型的数据结构来做订单管理:
1. **Position**：记录了每一个资产的仓位信息，包括当前仓位，开仓价格，最新价值，盈亏等。只要open，就会创建一个Position
2. **Trade**：记录了每一次交易的成交信息，包括开仓价格，平仓价格，最终盈亏等。只要open并且成功close，就会创建一个Trade
3. **Result**：记录了每一个策略的最终回测结果。

这个框架的特点：
1. 封装简单，修改容易
2. 事件驱动，易于扩展
3. 可以支持多资产的回测

**欢迎任何方式的contribution!**

## 更新
2024.12.29
- 增加PrecisionConfig做完整的精度控制

------------------------
2024.12.27
- 增加对数字精度的管理, 以避免在使用order_target_percent时出现累积误差的情况
- 在进行金额计算时, 所有的数值都使用Decimal类型, 并且在必要时使用 Decimal(str()) 来转换浮点数, 以避免精度损失
- 对于order_target_percent方法,将总资产的比例修复为总资产-总仓位潜在关仓手续费的比例,避免多次调仓后最后一个仓位无法开仓的情况 (不建议使用)
- 同时我提供了一个更为简单粗暴的方法:TOLERANCE(运行资金可能为负),buffer(可以预留资金作为缓冲)

------------------------
2024.12.09
- 增加对Crypto数据的支持(还不够完善)
- 加密货币动量因子的例子
- 增加long/short交易量变化的可视化 

-----------------------
2024.12.06
- 完善策略回测评价指标
- 支持多空收益分层
- 支持因子的分层回测
- 给Position加上open_commission字段以支持多空收益分层的统计
- 有关手续费处理的细节优化(为了保持数据结构的简洁，我尽可能的优化了调仓手续费的处理，在精度上100万有1000左右的偏差)

-----------------------
2024.12.05
- 新增对tushare的支持（目前数据指出tushare与rqdatac）
- 支持了日志功能

-----------------------
2024.12.04
- 支持对单标的重复多次开仓并且合并为一个仓位
- 修改了open close方法以支持部分平仓（重新完善了固定仓与分数仓的逻辑）
- 新增了order_target_percent以支持按资金比例进行调仓
- 完整的开关仓测试

-----------------------
2024.10.21
- 封装了Broker模块，实现了Strategy和交易功能的分离，使得结构更为清晰
- 实现了因子投资的滚仓操作
- 实现了run_weekly和run_monthly的修饰符

-----------------------
2024.10.20
- 这个项目的主要功能是我想用来代替alphalens这种工具帮助我进行更全面的因子研究，因此我设计的思想就是怎么简单怎么来，不去过多考虑设计模式，不去考虑不同的订单的处理，保持框架的极简。

-----------------------

## 开始使用
和其他常用事件型回测框架一样，我们需要先创建一个策略类，然后实例化一个回测类，并传入策略类以及回测参数。

需要注意的是如果要使用rqdatac或者tushare这种第三方接口获取数据，需要自己创建个.env，通过dotenv来读取你的账号和密码进行验证。接口详情可以参考athena/data.py
```python
RQDATA_USERNAME = xxx
RQDATA_PASSWORD = xxx

tushare_token = xxx

# 同时配置好环境变量与log path
global_path = "/Users/xxx/Desktop/Athena V3/"
log_path = "/Users/xxx/Desktop/Athena V3/athena/log/backtest_log.txt"

# 我同时优化了图片的现实(用于研报的统一排版)
regular_font = '/System/Library/Fonts/Supplemental/Arial.ttf'
legend_font = '/System/Library/Fonts/Supplemental/Arial.ttf'
bold_font = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
italics_font = '/System/Library/Fonts/Supplemental/Arial Italic.ttf'
```

类似的，用户新建的策略需要继承自Strategy基类，并且重写init和next方法

```python
from athena import Strategy, Backtest

class SingleAssetStrategy(Strategy):
    def init(self):
        # run once at the beginning of the backtest
        pass

    def next(self, i, record):
        # run every time a new bar is processed
        # i is the index of the bar
        # record is a dictionary data
        pass

backtest = Backtest(SingleAssetStrategy, MULTIPLE_ASSETS_DATA, commission=.001, cash=1000000)

backtest.run()
```

## TODO
- [x] 完成测试板块/稳健性测试
- [x] 完成对一些数据接口的支持
    - A股
        - [x] rqdatac
        - [x] tushare
    - Crypto
        - [x] crypto_data_center(自制的一个币安下载脚本) 
    - 美股
        - [ ] databento
- [ ] 基于框架梳理所有常见因子研究方法
    - [x] 简单排序法因子选股
    - [x] 多重排序法因子选股
    - [ ] 多因子模型的回归检验
- [x] 完整的日志功能支持
