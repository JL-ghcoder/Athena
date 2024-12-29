import logging
import os
from dotenv import load_dotenv
load_dotenv()

log_path = os.getenv('log_path')

def setup_logging():
    logging.basicConfig(
        filename=log_path,
        filemode='w',  
        level=logging.INFO, 
        format='%(message)s'
    )