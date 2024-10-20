import pandas as pd
import rqdatac as rq

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


    