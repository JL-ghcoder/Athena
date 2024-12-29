import pandas as pd
import rqdatac as rq
import tushare as ts
import time
import os

SINGLE_ASSET_TEST_DATA = pd.DataFrame(
    index=['2023-10-18', '2023-10-19', '2023-10-20'],
    data={
        'Open': [100.0, 200.0, 300.0],
        'High': [100.0, 200.0, 300.0],
        'Low': [100.0, 200.0, 300.0],
        'Close': [100.0, 200.0, 300.0],
        'Volume': [2000000, 2500000, 3000000]
    }
)

MULTIPLE_ASSETS_TEST_DATA = pd.DataFrame(
    index=['2023-10-18', '2023-10-19', '2023-10-20'],
    data={
        ('AAA','Open'): [100.0, 200.0, 300.0],
        ('AAA','High'): [100.0, 200.0, 300.0],
        ('AAA','Low'): [100.0, 200.0, 300.0],
        ('AAA','Close'): [100.0, 200.0, 300.0],
        ('AAA','Volume'): [2000000, 2500000, 3000000],
        ('BBB','Open'): [2850.0, 2835.0, 2820.0],
        ('BBB','High'): [2860.0, 2835.0, 2825.0],
        ('BBB','Low'): [2840.0, 2805.0, 2800.0],
        ('BBB','Close'): [2840.0, 2815.0, 2810.0],
        ('BBB','Volume'): [1500000, 1700000, 1600000]
    }
)


class RiceQuantDataHandler:
    def __init__(self, start_date, end_date, frequency='1d'):
        self.start_date = start_date
        self.end_date = end_date
        self.frequency = frequency
    
    def auth(self, user, pwd):
        rq.init(user, pwd) 
        #pass
    
    def get_index_list(self, index):
        return rq.index_components(index, self.end_date)
        
    def get_prices_from_ricequant(self, list, fields=['close']):
        # 需要先验证rqdatac: rq.init('','')
        print("开始获取数据")
        asset_prices = rq.get_price(list, start_date=self.start_date, end_date=self.end_date, frequency=self.frequency, fields=fields)
        print("数据获取完成")

        asset_prices.reset_index(inplace=True)
        asset_prices['date'] = pd.to_datetime(asset_prices['date'])

        # 保留原始字段名称映射
        field_mapping = {field: field.capitalize() for field in fields}
        # 更新DataFrame的列名
        asset_prices.rename(columns=field_mapping, inplace=True)
        
        asset_prices.set_index('date', inplace=True)

        # 根据order_book_id和field循环创建新结构的数据字典
        new_structure_data = {}
        print("开始转换数据结构")

        for order_book_id in asset_prices['order_book_id'].unique():
            for _, new_field in field_mapping.items():
            #for field in fields:
                key = (order_book_id, new_field)

                series = asset_prices.loc[asset_prices['order_book_id'] == order_book_id, new_field]
                # 使用reindex来确保时间序列与主索引长度相同，并用合适的方法填充缺失数据
                series = series.reindex(asset_prices.index.unique())  #保持长度一致，填充空值
                new_structure_data[key] = series.values

                #new_structure_data[key] = asset_prices.loc[asset_prices['order_book_id'] == order_book_id, new_field].values
                    
        new_structure_df = pd.DataFrame(new_structure_data, index=asset_prices.index.unique())
    
        return new_structure_df

    def get_factors_from_ricequant(self, list, factors=['market_cap']):

        print("开始获取数据")
        factor_data = rq.get_factor(list, factors, self.start_date, self.end_date)

        print("数据获取完成")

        factor_data.reset_index(inplace=True)
        factor_data['date'] = pd.to_datetime(factor_data['date'])
        
        factor_data.set_index('date', inplace=True)

        # 根据order_book_id和field循环创建新结构的数据字典
        new_structure_data = {}
        print("开始转换数据结构")

        for order_book_id in factor_data['order_book_id'].unique():
            for field in factors:
            #for field in fields:
                key = (order_book_id, field)

                series = factor_data.loc[factor_data['order_book_id'] == order_book_id, field]
                # 使用reindex来确保时间序列与主索引长度相同，并用合适的方法填充缺失数据
                series = series.reindex(factor_data.index.unique())  #保持长度一致，填充空值
                new_structure_data[key] = series.values

                #new_structure_data[key] = factor_data.loc[factor_data['order_book_id'] == order_book_id, field].values
                    
        new_structure_df = pd.DataFrame(new_structure_data, index=factor_data.index.unique())
    
        return new_structure_df


class TushareDataHandler:
    def __init__(self, start_date, end_date, frequency='D', token=None):
        """
        :param start_date: 开始日期，格式 YYYYMMDD
        :param end_date: 结束日期，格式 YYYYMMDD
        :param frequency: 数据频率，默认为日线 'D'
        :param token: Tushare 的个人认证 Token
        """
        self.start_date = start_date
        self.end_date = end_date
        self.frequency = frequency
        
        if token:
            ts.set_token(token)
        self.pro = ts.pro_api()
        self.pro._DataApi__http_url = 'http://tsapi.majors.ltd:7000'

    def get_index_list(self, index_code):
        """
        获取指定指数的成分股列表。
        :param index_code: 指数代码，例如 '000016.SH'（上证50）
        :return: 成分股代码列表
        """
        index_weights = self.pro.index_weight(index_code=index_code, start_date=self.start_date, end_date=self.end_date)
        unique_stock_list = list(set(index_weights['con_code'].tolist()))  # 使用 set 去重
        
        return unique_stock_list
    
    def get_index_prices_from_tushare(self, index_code):
        """
        获取指定指数的日线行情数据，重新整理为多重索引的 DataFrame。
        :param index_code: 指数代码，例如 '000016.SH'（上证50）
        :param fields: 需要获取的字段，例如 ['open', 'high', 'low', 'close', 'vol']。
        :return: 多重索引结构的价格数据 DataFrame
        """

        benchmark_data = self.pro.index_daily(ts_code=index_code, start_date=self.start_date, end_date=self.end_date)
        
        # 按日期排序（通常从最新日期到过去，需要升序计算净值变化）
        benchmark_data['trade_date'] = pd.to_datetime(benchmark_data['trade_date'])
        benchmark_data = benchmark_data.sort_values(by='trade_date')

        benchmark_data.set_index('trade_date', inplace=True)

        # 计算累积净值变化
        benchmark_data['benchmark_net_value'] = (1 + benchmark_data['pct_chg'] / 100).cumprod()  # 累积乘积
        benchmark_data.loc[benchmark_data.index[0], 'benchmark_net_value'] = 1.0

        return benchmark_data[['ts_code', 'benchmark_net_value']]
    
    
    def get_prices_from_tushare(self, stock_list, fields=['close'], sleep_time=0):
        """
        获取多只股票的日线行情数据，重新整理为多重索引的 DataFrame。
        :param stock_list: 股票列表（个股 TS 代码列表，例如 ['600000.SH', '000001.SZ']）
        :param fields: 需要获取的字段，例如 ['open', 'high', 'low', 'close', 'vol']。
        :return: 多重索引结构的价格数据 DataFrame
        """
        
        field_mapping = {
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'vol': 'Volume',
        }
        mapped_fields = [field_mapping[field] for field in fields]  # 将字段名称映射为规范的大写形式
        
        all_data = []
        print("开始获取行情数据...")
        # 遍历股票列表
        for stock in stock_list:
            # 获取单只股票的日线数据
            df = self.pro.daily(ts_code=stock, start_date=self.start_date, end_date=self.end_date)
            df['ts_code'] = stock
            all_data.append(df)

            if sleep_time > 0:
                time.sleep(sleep_time)
        print("数据获取完成！")

        # 合并所有股票的数据
        combined_data = pd.concat(all_data)
        combined_data['trade_date'] = pd.to_datetime(combined_data['trade_date'])
        combined_data.set_index(['trade_date', 'ts_code'], inplace=True)

        # 选择需要的字段
        combined_data = combined_data[fields]
        combined_data.rename(columns=field_mapping, inplace=True)

        # 转换为多重索引结构，列为 (Symbol, 属性)
        new_structure_data = {}
        for stock in combined_data.index.get_level_values('ts_code').unique():
            for field in mapped_fields:
                key = (stock, field)
                series = combined_data.loc[combined_data.index.get_level_values('ts_code') == stock, field]
                series = series.droplevel('ts_code')  # 移除 ts_code，只有日期作为索引
                new_structure_data[key] = series

        # 转换为 DataFrame
        new_structure_df = pd.DataFrame(new_structure_data)

        new_structure_df = new_structure_df.sort_index(ascending=True)  # 按日期升序排列

        return new_structure_df
    
    # 直接调取数据会有个问题，就是可能会不让一次性拉太多数据，尤其是在跑全市场的话
    def get_prices_from_tushare_parallel(self, stock_list, fields=['close']):
        """
        获取多只股票的日线行情数据，重新整理为多重索引的 DataFrame。
        :param stock_list: 股票列表（个股 TS 代码列表，例如 ['600000.SH', '000001.SZ']）
        :param fields: 需要获取的字段，例如 ['open', 'high', 'low', 'close', 'vol']。
        :return: 多重索引结构的价格数据 DataFrame
        """
        
        field_mapping = {
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'vol': 'Volume',
        }
        mapped_fields = [field_mapping[field] for field in fields]  # 将字段名称映射为规范的大写形式
        
        print("开始获取行情数据...")
        # 一次性读取所有股票数据
        df_all = self.pro.daily(ts_code=','.join(stock_list), start_date=self.start_date, end_date=self.end_date)

        if df_all.empty:
            print("API 未返回任何数据，请检查输入参数！")
            return None

        print("数据获取完成！")
        
        # 处理数据
        df_all['trade_date'] = pd.to_datetime(df_all['trade_date'])
        df_all.set_index(['trade_date', 'ts_code'], inplace=True)
        # 选择需要的字段
        df_all = df_all[fields]
        df_all.rename(columns=field_mapping, inplace=True)

        # 转换为多重索引结构，列为 (Symbol, 属性)
        new_structure_data = {}
        for stock in df_all.index.get_level_values('ts_code').unique():
            for field in mapped_fields:
                key = (stock, field)
                series = df_all.loc[df_all.index.get_level_values('ts_code') == stock, field]
                series = series.droplevel('ts_code')  # 移除 ts_code，只有日期作为索引
                new_structure_data[key] = series
        # 转换为 DataFrame
        new_structure_df = pd.DataFrame(new_structure_data)
        new_structure_df = new_structure_df.sort_index(ascending=True)  # 按日期升序排列

        return new_structure_df

    def get_factors_from_tushare(self, stock_list, factors=['total_mv'], sleep_time=0):
        """
        获取多只股票的指定因子数据，重新整理为多重索引的 DataFrame。
        :param stock_list: 股票列表（个股 TS 代码列表）
        :param factors: 因子字段列表，例如 ['pe_ttm', 'pb', 'market_cap']。
        :return: 多重索引结构的因子数据 DataFrame
        """

        all_data = []
        factors_with_date = factors + ['trade_date'] # 得加上时间
        print("开始获取因子数据...")

        for stock in stock_list:
            # tushare提供的财务接口: income, balancesheet, cashflow, forecast, express
            # 每日数据（非离散）: daily_basic
            df = self.pro.daily_basic(ts_code=stock, start_date=self.start_date, end_date=self.end_date, fields=factors_with_date)
            df['ts_code'] = stock
            all_data.append(df)

            if sleep_time > 0:
                time.sleep(sleep_time)
                
        print("数据获取完成！")

        combined_data = pd.concat(all_data)

        combined_data['trade_date'] = pd.to_datetime(combined_data['trade_date'])

        combined_data.set_index(['trade_date', 'ts_code'], inplace=True)

        # 选择需要的因子字段
        combined_data = combined_data[factors]

        new_structure_data = {}
        for stock in combined_data.index.get_level_values('ts_code').unique():
            for field in factors:
                key = (stock, field)
                series = combined_data.loc[combined_data.index.get_level_values('ts_code') == stock, field]
                series = series.droplevel('ts_code')
                new_structure_data[key] = series

        # 转换为 DataFrame
        new_structure_df = pd.DataFrame(new_structure_data)
        new_structure_df = new_structure_df.sort_index(ascending=True)  # 按日期升序排列

        return new_structure_df
    
    def get_factors_from_tushare_parallel(self, stock_list, factors=['total_mv']):
        """
        获取多只股票的指定因子数据，重新整理为多重索引的 DataFrame。
        :param stock_list: 股票列表（个股 TS 代码列表）。
        :param factors: 因子字段列表，例如 ['pe_ttm', 'pb', 'market_cap']。
        :return: 多重索引结构的因子数据 DataFrame。
        """
        
        factors_with_date = factors + ['trade_date', 'ts_code']  # 确保返回因子的同时包含交易日期
        print("开始获取因子数据...")
        
        # 一次性读取所有股票的因子数据
        df_all = self.pro.daily_basic(ts_code=','.join(stock_list), start_date=self.start_date, end_date=self.end_date, fields=factors_with_date)

        if df_all.empty:
            print("API 未返回任何数据，请检查输入参数！")
            return None

        print("数据获取完成！")
        
        # 数据处理
        df_all['trade_date'] = pd.to_datetime(df_all['trade_date'])
        df_all.set_index(['trade_date', 'ts_code'], inplace=True)
        # 选择需要的因子字段
        df_all = df_all[factors]
        
        # 转换为多重索引结构，列为 (Symbol, 因子)
        new_structure_data = {}
        for stock in df_all.index.get_level_values('ts_code').unique():
            for factor in factors:
                key = (stock, factor)  # 多重索引的列格式 (Symbol, 因子)
                series = df_all.loc[df_all.index.get_level_values('ts_code') == stock, factor]
                series = series.droplevel('ts_code')  # 移除 ts_code，只保留日期索引
                new_structure_data[key] = series

        # 转换为 DataFrame
        new_structure_df = pd.DataFrame(new_structure_data)
        new_structure_df = new_structure_df.sort_index(ascending=True)  # 按日期升序排列

        return new_structure_df


class CryptoDataHandler:
    def __init__(self, start_date, end_date):
        """
        :param start_date: 开始日期，格式 YYYYMMDD
        :param end_date: 结束日期，格式 YYYYMMDD
        :param frequency: 数据频率，默认为日线 'D'
        :param token: Tushare 的个人认证 Token
        """
        self.start_date = start_date
        self.end_date = end_date

    def create_prices_dataframe(self, data_dir, fields=['Open', 'Close']):
        """
        从指定的目录中提取所有 pkl 文件并生成多索引大表。
        
        :param data_dir: 本地文件夹路径，包含以 pkl 格式存储的各标的数据。
        :param start_date: 数据的开始日期，格式为 "yyyy-mm-dd" (字符串类型或 None)。
        :param end_date: 数据的结束日期，格式为 "yyyy-mm-dd" (字符串类型或 None)。
        :param fields: 要提取的字段列表，默认 ['Open', 'Close']。
        :return: 格式化后的 Pandas DataFrame。
        """
        # 初始化一个空的字典，用于拼接数据
        data_dict = {}

        # 遍历目录中的所有 pkl 文件
        for file_name in os.listdir(data_dir):
            # 检查仅处理以 .pkl 结尾的文件
            if file_name.endswith(".pkl"):
                # 提取 symbol 名称
                symbol = file_name.split("_")[0]

                # 读取 pkl 文件
                file_path = os.path.join(data_dir, file_name)
                try:
                    df = pd.read_pickle(file_path)
                except Exception as e:
                    print(f"[错误] 无法读取文件 {file_path}: {e}")
                    continue

                # 检查所需字段是否在文件中存在
                missing_fields = [field for field in fields if field not in df.columns]
                if missing_fields:
                    print(f"[警告] 文件 {file_name} 缺失必要字段 {missing_fields}，跳过处理！")
                    continue

                # 保留索引为时间列，并重命名为 trade_date
                if "Open time" not in df.columns:
                    print(f"[警告] 文件 {file_name} 缺失 'Open time' 列，跳过处理！")
                    continue

                df.rename(columns={"Open time": "trade_date"}, inplace=True)
                df["trade_date"] = pd.to_datetime(df["trade_date"])
                df.set_index("trade_date", inplace=True)

                # 按时间范围过滤数据
                if self.start_date:
                    start_date_ts = pd.to_datetime(self.start_date)
                    df = df[df.index >= start_date_ts]
                if self.end_date:
                    end_date_ts = pd.to_datetime(self.end_date)
                    df = df[df.index <= end_date_ts]

                # 提取指定字段并加入字典
                data_dict[symbol] = df[fields]

        # 合并所有标的数据
        if data_dict:
            prices_df = pd.concat(data_dict, axis=1)  # 将字典按列（symbol）合并
            prices_df.sort_index(inplace=True)       # 按时间排序索引

        else:
            print("[警告] 未发现有效数据文件！")
            return pd.DataFrame()  # 返回空 DataFrame
        
        # 遍历并清洗 `prices_df` 的数据框
        for symbol in prices_df.columns.levels[0]:  # 遍历第一级列索引（交易标的）
            for field in prices_df[symbol].columns:  # 遍历第二级列索引（Open, Close 等字段）
                # 提取每一列
                column_data = prices_df[(symbol, field)]
                
                # 清洗数据：将非数值型数据替换为 NaN
                prices_df[(symbol, field)] = pd.to_numeric(column_data, errors="coerce")

        return prices_df

# 这是针对单表的聚合方法
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

# 这是针对多表的聚合方法
def resample_multi_index_dataframe(prices_df, target_freq='1D'):
    """
    将多标的大表按指定的频率进行重采样，例如将15min数据合并成1D。
    
    :param prices_df: 包含多索引的K线数据大表，索引为日期，columns为多级索引 (symbol, fields)
    :param target_freq: 目标频率，例如 '1D' 表示日级别
    :return: 重采样后的 DataFrame
    """
    # 检查索引是否是 DatetimeIndex
    if not isinstance(prices_df.index, pd.DatetimeIndex):
        raise ValueError("输入的 DataFrame 必须以时间作为索引 (DatetimeIndex)")

    # 定义基础聚合逻辑（包含常见字段）
    default_agg_funcs = {
        'Open': 'first',                             # 第一个 Open 值
        'High': 'max',                               # 最高价
        'Low': 'min',                                # 最低价
        'Close': 'last',                             # 最后一个 Close 值
        'Volume': 'sum',                             # 成交量总和
        'Quote asset volume': 'sum',                 # Quote asset volume 总和
        'Number of trades': 'sum',                   # 成交笔数总和
        'Taker buy base asset volume': 'sum',        # 主动买入成交量总和
        'Taker buy quote asset volume': 'sum',       # 主动买入成交额总和
    }

    # 初始化一个空的列表，用于存储重采样后的数据
    resampled_data = []

    # 遍历每个标的 (symbol) 并进行重采样
    for symbol in prices_df.columns.levels[0]:  # 遍历第一级多索引（symbol）
        symbol_data = prices_df[symbol]  # 提取该 symbol 的数据

        # 筛选出当前 symbol 中存在的字段
        available_fields = [field for field in default_agg_funcs.keys() if field in symbol_data.columns]
        symbol_agg_funcs = {field: default_agg_funcs[field] for field in available_fields}

        # 如果没有可用字段，跳过
        if not symbol_agg_funcs:
            print(f"[警告] {symbol} 缺少可重采样的字段，已跳过！")
            continue

        # 重采样数据，应用聚合逻辑
        resampled_symbol_data = symbol_data.resample(target_freq).agg(symbol_agg_funcs)

        # 为当前 symbol 数据加上多索引
        resampled_symbol_data.columns = pd.MultiIndex.from_product([[symbol], resampled_symbol_data.columns])

        # 将重采样后的数据保存到列表中
        resampled_data.append(resampled_symbol_data)

    # 合并所有标的重采样后的数据
    if resampled_data:
        resampled_df = pd.concat(resampled_data, axis=1)
        resampled_df.sort_index(inplace=True)  # 按时间索引排序
    else:
        print("[警告] 未找到可重采样的数据！")
        resampled_df = pd.DataFrame()  # 返回空 DataFrame

    return resampled_df
