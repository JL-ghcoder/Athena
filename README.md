# Athena
<div align="center">
    <img src="pics/logo.png" alt="athena logo" style="width:150px;">
    <p></p>
    <p><strong>基于多资产的因子回测框架</strong></p>
</div>


## 概览
Athena是一款简单的多资产回测工具，基于事件型回测框架，拥有非常简单的程序结构，易于上手。

Athena简化了订单的处理，只考虑订单open和close两种情况：所有资产都通过open来开仓（指定多空），通过close关仓。这对于追踪因子在不同标的上的表现至关重要，而SL，TP这种更适合单标的交易的订单结构该框架没有提供支持。

Athena主要由3个模块组成：
1. Strategy：策略模块，继承自Strategy基类，实现了策略的初始化和每一个bar的处理。
2. Backtest：回测模块，实现了回测的初始化，运行，结果的输出。
3. Broker: 交易模块，实现了交易的初始化，订单的生成，撮合，成交的记录。

除此之外我构造了3个典型的数据结构来做订单管理:
1. Position：记录了每一个资产的仓位信息，包括当前仓位，开仓价格，最新价值，盈亏等。只要open，就会创建一个Position
2. Trade：记录了每一次交易的成交信息，包括开仓价格，平仓价格，最终盈亏等。只要open并且成功close，就会创建一个Trade
3. Result：记录了每一个策略的最终回测结果。

特点：
1. 封装简单，修改容易
2. 事件驱动，易于扩展
3. 可以支持多资产的回测

## 更新

2024.10.21
- 封装了Broker模块，实现了Strategy和交易功能的分离，使得结构更为清晰
- 实现了因子投资的滚仓操作
- 实现了run_weekly和run_monthly的修饰符

-----------------------
2024.10.20
- 这个项目的主要功能是我想用来代替alphalens这种工具帮助我进行更全面的因子研究，因此我设计的思想就是怎么简单怎么来，不去过多考虑设计模式，不去考虑不同的订单的处理，保持框架的极简。

## 开始使用
和其他常用事件型回测框架一样，我们需要先创建一个策略类，然后实例化一个回测类，并传入策略类以及回测参数。

需要注意的是如果要使用rqdatac这种第三方接口获取数据，需要自己创建个.env，通过dotenv来读取你的账号和密码进行验证。接口详情可以参考athena/data.py
```python
RQDATA_USERNAME = xxx
RQDATA_PASSWORD = xxx
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
- [x] 完成测试板块
- [x] 完成对一些数据接口的支持
    - [x] rqdatac
    - [ ] tushare
- [ ] 基于这个框架梳理所有常见因子研究
    - [x] 排序法因子选股
- [ ] MODE的开发
