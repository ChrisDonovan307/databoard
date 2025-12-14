import pandas as pd
import os

print(os.getcwd())

df = pd.read_csv('../data/installations/installations.csv')
df.columns
df.info()

continents = list(df.continent.unique())
type(continents)
continents.append('All')

continents = ['All'] += df.continent.unique()
type(continents)
print(continents)

first_list = ['a', 'b']
first_list.append('c')
# second_list = [first_list, 'c']
print(first_list)
print(second_list)