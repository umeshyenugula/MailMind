import pandas as pd
df = pd.read_csv('your_file.csv')
df_cut = df.iloc[:2000]
df_cut.to_csv('processed.csv', index=False)
