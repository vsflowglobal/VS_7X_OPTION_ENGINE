import streamlit as st
import pandas as pd
import numpy as np
import requests, time, math
from pathlib import Path
from datetime import datetime, timezone

st.set_page_config(page_title='VS 7X Option Engine', page_icon='vs_7x_logo.png', layout='wide', initial_sidebar_state='expanded')
LOGO = Path(__file__).with_name('vs_7x_logo.png')

st.markdown('''<style>
.stApp{background:radial-gradient(circle at 50% -20%,#14283b 0%,#070b10 43%,#030507 100%);color:#f4f6f8}
[data-testid="stSidebar"]{background:#070b10;border-right:1px solid #26333e}
.block-container{padding-top:1rem;padding-bottom:2rem;max-width:1600px}
.card{background:linear-gradient(145deg,#101820,#080c11);border:1px solid #26333e;border-radius:14px;padding:16px;box-shadow:0 8px 30px rgba(0,0,0,.25)}
.gold{color:#e8bd58}.green{color:#22d68a}.red{color:#ff5964}.blue{color:#4ca8ff}.muted{color:#8e9aa6}
.metric{font-size:24px;font-weight:800}.label{font-size:11px;text-transform:uppercase;letter-spacing:1.2px;color:#8e9aa6}
.small{font-size:12px;color:#8e9aa6} hr{border-color:#25313c}
</style>''', unsafe_allow_html=True)

if LOGO.exists(): st.sidebar.image(str(LOGO), use_container_width=True)
st.sidebar.markdown('### VS 7X OPTION ENGINE')
page=st.sidebar.radio('Navigation',['Dashboard','Index Intelligence','Option Chain','Top CE / PE','Swing Options','Scalping','Expiry Radar','Hero Zero','SMC + S/R Map','Trade Plans','Watchlist','Settings'])
st.sidebar.divider(); st.sidebar.caption('Fresh engine • live-data adapters • UI reference only from legacy VS FLOW')

@st.cache_data(ttl=45, show_spinner=False)
def yf_history(ticker, period='6mo', interval='1d'):
    try:
        import yfinance as yf
        df=yf.download(ticker,period=period,interval=interval,auto_adjust=False,progress=False,threads=False)
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        return df.dropna()
    except Exception:
        return pd.DataFrame()

def last_price(df):
    if df.empty:return None
    return float(df['Close'].iloc[-1])

def change(df):
    if len(df)<2:return (None,None)
    a=float(df['Close'].iloc[-2]); b=float(df['Close'].iloc[-1]); return b-a,(b/a-1)*100

def fmt(x,dec=2): return '—' if x is None or (isinstance(x,float) and math.isnan(x)) else f'{x:,.{dec}f}'

def metric_row(items):
    cols=st.columns(len(items))
    for c,(label,value,cls) in zip(cols,items): c.markdown(f'<div class="card"><div class="label">{label}</div><div class="metric {cls}">{value}</div></div>',unsafe_allow_html=True)

def header(title,subtitle): st.markdown(f'<div class="card"><h1 style="margin:0">{title}</h1><p class="muted" style="margin:6px 0 0">{subtitle}</p></div>',unsafe_allow_html=True)

def tech(df):
    if df.empty:return {}
    x=df.copy(); x['EMA9']=x.Close.ewm(span=9,adjust=False).mean(); x['EMA20']=x.Close.ewm(span=20,adjust=False).mean(); x['SMA18']=x.Close.rolling(18).mean(); x['SMA50']=x.Close.rolling(50).mean(); x['SMA200']=x.Close.rolling(200).mean();
    tp=(x.High+x.Low+x.Close)/3; x['VWAP']= (tp*x.Volume).cumsum()/x.Volume.cumsum() if 'Volume' in x else np.nan
    return x

def structure(df):
    if len(df)<30:return ('WAIT','—','—','—')
    x=tech(df); p=float(x.Close.iloc[-1]); e9=float(x.EMA9.iloc[-1]); e20=float(x.EMA20.iloc[-1]); s50=float(x.SMA50.iloc[-1]) if not pd.isna(x.SMA50.iloc[-1]) else p
    bias='BULLISH' if p>e20 and e9>e20 else 'BEARISH' if p<e20 and e9<e20 else 'RANGE'
    hi=float(x.High.tail(20).max()); lo=float(x.Low.tail(20).min()); loc='PREMIUM' if p>(hi+lo)/2 else 'DISCOUNT'
    smc='BOS↑' if p>float(x.High.tail(10).iloc[:-1].max()) else 'BOS↓' if p<float(x.Low.tail(10).iloc[:-1].min()) else 'RANGE'
    return bias,loc,smc,f'{lo:,.0f} – {hi:,.0f}'

TICKERS={'NIFTY 50':'^NSEI','BANK NIFTY':'^NSEBANK','SENSEX':'^BSESN','INDIA VIX':'^INDIAVIX','FINNIFTY':'NIFTY_FIN_SERVICE.NS','NIFTY NEXT 50':'^NSMIDCP'}

def nse_session():
    s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36','Accept':'application/json,text/plain,*/*','Accept-Language':'en-US,en;q=0.9','Referer':'https://www.nseindia.com/option-chain'}); 
    try:s.get('https://www.nseindia.com',timeout=8)
    except Exception:pass
    return s

@st.cache_data(ttl=30,show_spinner=False)
def nse_chain(symbol, equity=False):
    try:
        s=nse_session(); endpoint='option-chain-equities' if equity else 'option-chain-indices'; r=s.get(f'https://www.nseindia.com/api/{endpoint}?symbol={symbol}',timeout=12); r.raise_for_status(); return r.json()
    except Exception:return {}

def chain_df(data):
    rows=[]
    for item in data.get('records',{}).get('data',[]):
        strike=item.get('strikePrice'); ce=item.get('CE',{}); pe=item.get('PE',{})
        if strike is None: continue
        rows.append({'Strike':strike,'CE OI':ce.get('openInterest'),'CE ΔOI':ce.get('changeinOpenInterest'),'CE IV':ce.get('impliedVolatility'),'CE LTP':ce.get('lastPrice'),'CE Vol':ce.get('totalTradedVolume'),'PE LTP':pe.get('lastPrice'),'PE IV':pe.get('impliedVolatility'),'PE Vol':pe.get('totalTradedVolume'),'PE ΔOI':pe.get('changeinOpenInterest'),'PE OI':pe.get('openInterest')})
    return pd.DataFrame(rows)

def option_stats(df, spot):
    if df.empty:return None,None,None,None
    pcr=df['PE OI'].fillna(0).sum()/max(df['CE OI'].fillna(0).sum(),1)
    maxpain=None; best=10**30
    strikes=df.Strike.dropna().unique()
    for k in strikes:
        call=np.maximum(k-df.Strike,0)*df['CE OI'].fillna(0); put=np.maximum(df.Strike-k,0)*df['PE OI'].fillna(0); pain=float(call.sum()+put.sum())
        if pain<best:best=pain;maxpain=k
    atm=float(df.loc[(df.Strike-spot).abs().idxmin(),'Strike']) if spot else None
    return pcr,maxpain,atm,df.loc[(df.Strike-atm).abs()<=max(500,abs(atm)*.02)] if atm else df

if page=='Dashboard':
    header('VS 7X • OPTION ENGINE','Live market workspace • multi-timeframe structure + options intelligence')
    vals=[]
    for n in ['NIFTY 50','BANK NIFTY','SENSEX','INDIA VIX']:
        d=yf_history(TICKERS[n],period='5d',interval='1d'); p=last_price(d); ch,pct=change(d); vals.append((n,fmt(p),'green' if pct and pct>=0 else 'red'))
    nifty=yf_history(TICKERS['NIFTY 50'],period='5d',interval='1d'); spot=last_price(nifty); chain=nse_chain('NIFTY'); cdf=chain_df(chain); pcr,maxpain,atm,_=option_stats(cdf,spot)
    metric_row(vals+[('PCR',fmt(pcr,2),'gold'),('MAX PAIN',fmt(maxpain,0),'gold')])
    c1,c2=st.columns([1.5,1]);
    with c1:
        st.markdown('### Market Intelligence'); rows=[]
        for n in ['NIFTY 50','BANK NIFTY','SENSEX']:
            d=yf_history(TICKERS[n],period='6mo'); b,loc,smc,sr=structure(d); rows.append({'Index':n,'Price':fmt(last_price(d)),'Bias':b,'Location':loc,'SMC':smc,'20D Range':sr})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        st.markdown('### NIFTY price structure');
        if not nifty.empty: st.line_chart(nifty['Close'].tail(90))
    with c2:
        st.markdown('### Live feed status'); st.success('Price feed: yfinance adapter') if not nifty.empty else st.error('Price feed unavailable')
        st.success('NSE option-chain adapter connected') if not cdf.empty else st.warning('NSE option-chain unavailable right now')
        st.markdown('### Workflow'); st.markdown('**LOCATION → DIRECTION → ZONE → TRIGGER → ENTRY → RISK**')
        st.caption(f'Last refresh: {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}')

elif page=='Index Intelligence':
    header('Index Intelligence','Live OHLC structure across the VS 7X timeframe stack')
    idx=st.selectbox('Index',list(TICKERS.keys())[:6]); ticker=TICKERS[idx]; d=yf_history(ticker,period='1y',interval='1d'); p=last_price(d); ch,pct=change(d); b,loc,smc,sr=structure(d)
    metric_row([('Price',fmt(p),'gold'),('Change',f'{fmt(ch)} ({fmt(pct)}%)','green' if pct and pct>=0 else 'red'),('Bias',b,'green' if b=='BULLISH' else 'red' if b=='BEARISH' else 'gold'),('Location',loc,'gold')])
    if not d.empty: st.line_chart(d['Close'])
    x=tech(d); rows=[]
    for tf,window in [('1W',100),('1D',1),('4H',20),('1H',10),('15M',5),('5M',3)]:
        rows.append({'TF':tf,'Structure':b,'SMC':smc,'S/R':sr,'EMA9':fmt(x.EMA9.iloc[-1]),'EMA20':fmt(x.EMA20.iloc[-1])})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

elif page=='Option Chain':
    header('Option Chain','NSE option-chain data: OI, ΔOI, IV, LTP, volume and strike structure')
    idx=st.selectbox('Underlying',['NIFTY 50','BANK NIFTY','FINNIFTY','SENSEX']); sym={'NIFTY 50':'NIFTY','BANK NIFTY':'BANKNIFTY','FINNIFTY':'FINNIFTY','SENSEX':'SENSEX'}[idx]
    d=yf_history(TICKERS[idx],period='5d'); spot=last_price(d); data=nse_chain(sym); cdf=chain_df(data); pcr,maxpain,atm,view=option_stats(cdf,spot)
    metric_row([('Spot',fmt(spot),'gold'),('PCR',fmt(pcr,2),'blue'),('ATM',fmt(atm,0),'gold'),('Max Pain',fmt(maxpain,0),'gold')])
    if not cdf.empty:
        st.dataframe(view.sort_values('Strike'),use_container_width=True,hide_index=True)
        st.caption('Source: NSE option-chain endpoint. NSE notes that IV is reference/dynamic and its site terms apply.')
    else: st.error('NSE option-chain data could not be fetched. Check again during market hours or use a licensed derivatives feed.')

elif page=='Top CE / PE':
    header('Top CE / PE','Candidate ranking from live OI/volume/IV after underlying structure check')
    idx=st.selectbox('Underlying',['NIFTY 50','BANK NIFTY','FINNIFTY','SENSEX']); sym={'NIFTY 50':'NIFTY','BANK NIFTY':'BANKNIFTY','FINNIFTY':'FINNIFTY','SENSEX':'SENSEX'}[idx]; d=yf_history(TICKERS[idx],period='5d'); spot=last_price(d); cdf=chain_df(nse_chain(sym))
    if not cdf.empty and spot:
        near=cdf.iloc[(cdf.Strike-spot).abs().argsort()[:30]]; ce=near.sort_values(['CE Vol','CE OI'],ascending=False).head(5); pe=near.sort_values(['PE Vol','PE OI'],ascending=False).head(5)
        metric_row([('CE Candidates',str(len(ce)),'green'),('PE Candidates',str(len(pe)),'red'),('ATM',fmt(spot),'gold'),('IV',fmt(pd.concat([ce['CE IV'],pe['PE IV']]).median()),'blue')])
        a,b=st.columns(2); 
        with a: st.markdown('### CE'); st.dataframe(ce[['Strike','CE LTP','CE IV','CE OI','CE ΔOI','CE Vol']],use_container_width=True,hide_index=True)
        with b: st.markdown('### PE'); st.dataframe(pe[['Strike','PE LTP','PE IV','PE OI','PE ΔOI','PE Vol']],use_container_width=True,hide_index=True)
    else: st.warning('Live option data unavailable.')

elif page=='Swing Options':
    header('Swing Options','Underlying-first F&O swing radar using price structure, trend and volume')
    universe=['RELIANCE.NS','HDFCBANK.NS','ICICIBANK.NS','SBIN.NS','INFY.NS','TCS.NS','AXISBANK.NS','LT.NS','BHARTIARTL.NS','ITC.NS']
    rows=[]
    for t in universe:
        d=yf_history(t,period='6mo'); b,loc,smc,sr=structure(d); p=last_price(d); rows.append({'Stock':t.replace('.NS',''),'Price':fmt(p),'Bias':b,'Location':loc,'SMC':smc,'S/R':sr,'Setup':'WATCH' if b!='RANGE' else 'WAIT'})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

elif page=='Scalping':
    header('Scalping','Fast execution dashboard: 15M → 5M → 3M → 1M')
    d=yf_history('^NSEI',period='5d',interval='15m'); p=last_price(d); b,loc,smc,sr=structure(d)
    metric_row([('NIFTY',fmt(p),'gold'),('Bias',b,'green' if b=='BULLISH' else 'red' if b=='BEARISH' else 'gold'),('Location',loc,'gold'),('SMC',smc,'blue')])
    if not d.empty: st.line_chart(d['Close'])
    st.info('Scalp candidate requires HTF location + liquidity event + BOS/CHoCH + entry-zone reaction. This page does not fabricate a trade.')

elif page=='Expiry Radar':
    header('Expiry Radar','Live option positioning and market structure')
    d=yf_history('^NSEI',period='5d'); spot=last_price(d); cdf=chain_df(nse_chain('NIFTY')); pcr,maxpain,atm,_=option_stats(cdf,spot)
    metric_row([('Spot',fmt(spot),'gold'),('PCR',fmt(pcr,2),'blue'),('Max Pain',fmt(maxpain,0),'gold'),('ATM',fmt(atm,0),'gold')])
    if not cdf.empty: st.dataframe(cdf.sort_values('PE OI',ascending=False).head(15),use_container_width=True,hide_index=True)

elif page=='Hero Zero':
    header('Hero Zero','High-risk option-premium research module')
    st.error('High risk. Candidate data only; no automatic trade recommendation.')
    idx=st.selectbox('Underlying',['NIFTY 50','BANK NIFTY']); sym='NIFTY' if idx=='NIFTY 50' else 'BANKNIFTY'; d=yf_history(TICKERS[idx],period='5d'); spot=last_price(d); cdf=chain_df(nse_chain(sym))
    if not cdf.empty and spot:
        near=cdf.iloc[(cdf.Strike-spot).abs().argsort()[:20]].copy(); near['CE Premium']=near['CE LTP']; near['PE Premium']=near['PE LTP']; st.dataframe(near[['Strike','CE Premium','CE IV','CE Vol','PE Premium','PE IV','PE Vol']],use_container_width=True,hide_index=True)

elif page=='SMC + S/R Map':
    header('SMC + S/R Map','Fresh structure engine using recent highs/lows and trend state')
    idx=st.selectbox('Index',['NIFTY 50','BANK NIFTY','SENSEX']); d=yf_history(TICKERS[idx],period='6mo'); b,loc,smc,sr=structure(d); x=tech(d); p=last_price(d)
    hi=float(d.High.tail(50).max()); lo=float(d.Low.tail(50).min()); mid=(hi+lo)/2
    metric_row([('Price',fmt(p),'gold'),('Demand',fmt(lo),'green'),('Mid Range',fmt(mid),'gold'),('Supply',fmt(hi),'red')])
    rows=[{'Level':lo,'Type':'Demand / swing low','TF':'Daily','Status':'WATCH'},{'Level':mid,'Type':'Equilibrium','TF':'Daily','Status':'MIDDLE'},{'Level':hi,'Type':'Supply / swing high','TF':'Daily','Status':'WATCH'}]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

elif page=='Trade Plans':
    header('Trade Plans','VFTC-style research card populated from live structure')
    idx=st.selectbox('Underlying',['NIFTY 50','BANK NIFTY','SENSEX']); d=yf_history(TICKERS[idx],period='6mo'); p=last_price(d); b,loc,smc,sr=structure(d)
    result='WATCH' if b=='RANGE' or loc=='PREMIUM' and b=='BULLISH' else 'WAIT'
    plan=[('Analysis Overview',f'{idx} live structure study'),('Bias',b),('Confidence','Research only'),('Entry Zone',sr),('Stop Loss','Structure dependent'),('TP1 / TP2 / TP3','To be calculated after trigger'),('Risk:Reward','Not set'),('Market Context',f'{loc} • {smc}'),('Setup Status',result),('Invalidation','Break of structural level'),('Final Result',result)]
    st.dataframe(pd.DataFrame(plan,columns=['Field','Value']),use_container_width=True,hide_index=True)

elif page=='Watchlist':
    header('Watchlist','Live F&O stock research queue')
    symbols=st.text_area('Symbols','RELIANCE\nHDFCBANK\nICICIBANK\nSBIN\nINFY\nTCS\nLT').splitlines(); rows=[]
    for s in symbols:
        s=s.strip().upper();
        if not s:continue
        d=yf_history(s+'.NS',period='6mo'); b,loc,smc,sr=structure(d); rows.append({'Symbol':s,'Price':fmt(last_price(d)),'HTF':b,'SMC':smc,'Location':loc,'S/R':sr,'Final':'WATCH' if not d.empty else 'DATA'} )
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

else:
    header('Settings','VS 7X engine controls')
    st.selectbox('Analysis Mode',['Position','Intraday','Scalp','Expiry']); st.selectbox('Primary timeframe',['4H','1H','15M','5M']); st.checkbox('Require Wave + GTI + OI confirmation',True); st.checkbox('Require SMC + S/R confirmation',True); st.checkbox('Block middle-of-range setups',True)
    st.info('Live price data uses yfinance. Indian derivatives data uses the NSE option-chain endpoint. For production/commercial use, use a licensed market-data provider and observe exchange terms.')

st.divider(); st.caption('VS 7X • Analyze • Scan • Trade • Grow | All Markets • One Vision | Research tool — trade only after your own analysis.')
