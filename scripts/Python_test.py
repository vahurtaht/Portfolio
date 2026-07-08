import pandas as pd
df = pd.read_csv("data/sales_data.csv")
# df.info() #annab ülevaate veergude nimedest, andmetüüpidest ja sellest, kas veergudes on tühje väärtusi
df.describe() #annab ülevaate numbrilistest veergudest (keskväärtus, mediaan jne)
df.isna().sum() #annab ülevaate sellest, kui palju on tühje väärtusi igas veerus
df = df.dropna(axis=1, how='all') #eemaldab veerud, mis tühjad
print(df.isna().sum())