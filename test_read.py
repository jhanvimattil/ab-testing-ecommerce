import pandas as pd
import time

file_path = "/Users/jhanvimattil/Downloads/archive (1)/2019-Oct.csv"

start_time = time.time()
print("Reading first 5,000,000 rows...")
df = pd.read_csv(file_path, nrows=5000000, usecols=['user_id', 'event_type', 'price', 'user_session'])
end_time = time.time()

print(f"Loaded 5M rows in {end_time - start_time:.2f} seconds.")
print(df.info())
print("\nEvent type counts:")
print(df['event_type'].value_counts())
print("\nUnique users:", df['user_id'].nunique())
print("Unique sessions:", df['user_session'].nunique())
