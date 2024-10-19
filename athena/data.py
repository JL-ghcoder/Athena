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
    def __init__(self, list, start_date, end_date, frequency='1d', fields=['close']):
        self.list = list
        self.start_date = start_date
        self.end_date = end_date
        self.frequency = frequency
        self.fields = fields
    
    def auth(self, user, pwd):
        rq.init(user, pwd) 
        #pass
        
    def get_data_from_ricequant(self):
        # 需要先验证rqdatac: rq.init('','')
        print("开始获取数据")
        asset_prices = rq.get_price(self.list, start_date=self.start_date, end_date=self.end_date, frequency=self.frequency, fields=self.fields)
        print("数据获取完成")

        asset_prices.reset_index(inplace=True)
        asset_prices['date'] = pd.to_datetime(asset_prices['date'])

        # 保留原始字段名称映射
        field_mapping = {field: field.capitalize() for field in self.fields}
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
                new_structure_data[key] = asset_prices.loc[asset_prices['order_book_id'] == order_book_id, new_field].values
                    
        new_structure_df = pd.DataFrame(new_structure_data, index=asset_prices.index.unique())
    
        return new_structure_df


    