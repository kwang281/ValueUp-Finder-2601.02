import FinanceDataReader as fdr
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

@st.cache_data(ttl=3600) # 1시간 캐시
def get_krx_listing():
    """
    KRX 전체 상장 종목 리스트를 가져옵니다 (캐싱됨).
    포함 정보: Code, Name, Market, Sector, Close, Marcap, Stocks, etc.
    """
    try:
        df = fdr.StockListing('KRX')
        return df
    except Exception as e:
        print(f"Error fetching KRX listing: {e}")
        return pd.DataFrame()

def get_market_metrics(ticker):
    """
    특정 종목의 시가총액, 현재가, 주식수 등을 반환합니다.
    """
    df_listing = get_krx_listing()
    
    if df_listing.empty:
        return None
    
    # Ticker 검색
    row = df_listing[df_listing['Code'] == ticker]
    if row.empty:
        return None
    
    row = row.iloc[0]
    
    return {
        "Code": row['Code'],
        "Name": row['Name'],
        "Close": int(row['Close']) if not pd.isna(row['Close']) else 0,
        "Marcap": int(row['Marcap']) if not pd.isna(row['Marcap']) else 0, # 시가총액
        "Stocks": int(row['Stocks']) if not pd.isna(row['Stocks']) else 0, # 상장주식수
        "Market": row['Market']
    }


def get_stock_history(code, days=365):
    """
    특정 종목의 일별 주가 데이터를 가져옵니다.
    기본값: 최근 1년 (365일)
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # FinanceDataReader format: fdr.DataReader(symbol, start, end)
        df = fdr.DataReader(code, start_date, end_date)
        
        if df.empty:
            return pd.DataFrame()
            
        # Index is Date, so reset index to make it a column
        df = df.reset_index()
        
        # Ensure column names are standard (fdr usually returns Date, Open, High, Low, Close, Volume, Change)
        # We need Date, Open, High, Low, Close, Volume
        
        return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].sort_values(by='Date', ascending=False)
        
    except Exception as e:
        print(f"Error fetching stock history for {code}: {e}")
        return pd.DataFrame()

