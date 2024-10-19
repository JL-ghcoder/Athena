# Athena

## 概览
Athena是一款简单的多资产回测工具，基于事件型回测框架，拥有非常简单的程序结构，易于上手。

特点：
1. 封装简单，修改容易
2. 事件驱动，易于扩展
3. 可以支持多资产的回测

## 申明
这个项目的主要功能是我想用来代替alphalens这种工具帮助我进行更全面的因子研究，因此我设计的思想就是怎么简单怎么来，不去过多考虑设计模式，不去考虑不同的订单的处理，保持框架的极简。

## 开始使用
和其他常用事件型回测框架一样，我们需要先创建一个策略类，然后实例化一个回测类，并传入策略类以及回测参数。

类似的，用户新建的策略需要继承自Strategy基类，并且重写init和next方法。

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
1. 完成测试板块
2. 完成对一些数据接口的支持
3. 基于这个框架梳理所有常见因子研究
4. MODE的开发
